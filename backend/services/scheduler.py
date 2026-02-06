"""Background task scheduler for scraping"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.database import async_session
from models.app import App, PriceHistory
from services.pinecone_client import upsert_app
from scrapers.app_store import scrape_popular_apps, update_app_prices

# Global scheduler
scheduler: AsyncIOScheduler | None = None


async def start_scheduler():
    """Start the background task scheduler"""
    global scheduler
    
    scheduler = AsyncIOScheduler()
    
    # Schedule price update job every 15 minutes
    scheduler.add_job(
        check_price_changes,
        IntervalTrigger(minutes=settings.SCRAPE_INTERVAL_MINUTES),
        id="price_check",
        replace_existing=True
    )
    
    # Schedule full scrape job daily
    scheduler.add_job(
        full_app_scrape,
        IntervalTrigger(hours=24),
        id="full_scrape",
        replace_existing=True
    )
    
    scheduler.start()
    print(f"Scheduler started. Price checks every {settings.SCRAPE_INTERVAL_MINUTES} minutes")


async def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("Scheduler stopped")


async def check_price_changes():
    """Check for price changes in tracked apps"""
    print("Running price check...")
    
    async with async_session() as db:
        # Get all active apps
        result = await db.execute(
            select(App).where(App.is_active == True).limit(500)
        )
        apps = result.scalars().all()
        
        app_ids = [app.id for app in apps]
        
        # Update prices
        updates = await update_app_prices(app_ids)
        
        # Process updates
        for update in updates:
            app = next((a for a in apps if a.id == update["id"]), None)
            if not app:
                continue
            
            # Check if price changed
            if app.price != update["price"]:
                # Record price history
                change_pct = ((update["price"] - app.price) / app.price * 100) if app.price > 0 else 0
                
                history = PriceHistory(
                    app_id=app.id,
                    old_price=app.price,
                    new_price=update["price"],
                    change_percentage=change_pct
                )
                db.add(history)
                
                # Update app
                app.price = update["price"]
                app.original_price = update["original_price"]
                app.is_free = update["is_free"]
                app.price_changed_at = datetime.utcnow()
                
                # Notify users if significant drop
                if change_pct < -20:  # 20% or more drop
                    await notify_price_drop(app, change_pct)
        
        await db.commit()
        print(f"Price check complete. Updated {len(updates)} apps")


async def full_app_scrape():
    """Full scrape of popular apps"""
    print("Running full app scrape...")
    
    # Scrape apps
    apps = await scrape_popular_apps(limit=500)
    
    async with async_session() as db:
        for app_data in apps:
            try:
                # Check if app exists
                result = await db.execute(
                    select(App).where(App.id == app_data["id"])
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing
                    for key, value in app_data.items():
                        setattr(existing, key, value)
                    existing.last_scraped_at = datetime.utcnow()
                else:
                    # Create new
                    new_app = App(**app_data)
                    new_app.last_scraped_at = datetime.utcnow()
                    db.add(new_app)
                
                # Update vector index
                await upsert_app(app_data["id"], app_data)
                
            except Exception as e:
                print(f"Error processing app {app_data['id']}: {e}")
        
        await db.commit()
    
    print(f"Full scrape complete. Processed {len(apps)} apps")


async def notify_price_drop(app: App, change_pct: float):
    """Notify users of price drop"""
    # TODO: Implement email/push notifications
    print(f"PRICE DROP: {app.name} is now ${app.price} ({change_pct:.0f}% off)")


from datetime import datetime
