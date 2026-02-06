"""Daily digest task - Send daily email digests with app deals"""

from datetime import datetime, timedelta
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from models.app import App, PriceHistory
from services.email_service import email_service


async def get_daily_deals(db: AsyncSession):
    """Get apps that went free or had price drops in the last 24 hours"""
    
    since = datetime.utcnow() - timedelta(hours=24)
    
    # Get apps that went free (price was > 0, now is 0)
    free_apps_query = select(App).where(
        and_(
            App.is_free == True,
            App.original_price > 0,
            App.price_changed_at >= since
        )
    ).order_by(desc(App.price_changed_at)).limit(10)
    
    free_apps_result = await db.execute(free_apps_query)
    free_apps = free_apps_result.scalars().all()
    
    # Get apps with price drops
    price_drops_query = select(App).where(
        and_(
            App.price < App.original_price,
            App.price > 0,  # Not free, just discounted
            App.price_changed_at >= since
        )
    ).order_by(desc(App.original_price - App.price)).limit(10)
    
    price_drops_result = await db.execute(price_drops_query)
    price_drops = price_drops_result.scalars().all()
    
    return free_apps, price_drops


async def calculate_stats(free_apps, price_drops):
    """Calculate digest statistics"""
    
    total_savings = sum(app.original_price for app in free_apps)
    total_savings += sum(app.original_price - app.price for app in price_drops)
    
    return {
        "free_apps": len(free_apps),
        "price_drops": len(price_drops),
        "total_savings": f"${total_savings:.2f}"
    }


async def send_daily_digests():
    """
    Send daily digest emails to all subscribed users.
    This should be scheduled to run once per day (e.g., 9 AM).
    """
    
    async with async_session() as db:
        # Get daily deals
        free_apps, price_drops = await get_daily_deals(db)
        
        if not free_apps and not price_drops:
            print("No deals today, skipping digest")
            return
        
        # Calculate stats
        stats = await calculate_stats(free_apps, price_drops)
        
        # Format apps for email
        free_apps_data = [
            {
                "id": app.id,
                "name": app.name,
                "developer": app.developer,
                "icon_url": app.icon_url,
                "original_price": app.original_price,
                "category": app.category
            }
            for app in free_apps
        ]
        
        price_drops_data = [
            {
                "id": app.id,
                "name": app.name,
                "developer": app.developer,
                "icon_url": app.icon_url,
                "price": app.price,
                "original_price": app.original_price,
                "discount": round(((app.original_price - app.price) / app.original_price) * 100)
            }
            for app in price_drops
        ]
        
        # TODO: Get subscribed users from database
        # For now, just log what would be sent
        subscribed_users = [
            # "user@example.com",
        ]
        
        print(f"\n{'='*60}")
        print(f"📧 DAILY DIGEST - {datetime.now().strftime('%B %d, %Y')}")
        print(f"{'='*60}")
        print(f"Free apps: {len(free_apps_data)}")
        print(f"Price drops: {len(price_drops_data)}")
        print(f"Total savings: {stats['total_savings']}")
        print(f"Subscribed users: {len(subscribed_users)}")
        print(f"{'='*60}\n")
        
        # Send to each subscribed user
        for email in subscribed_users:
            await email_service.send_daily_digest(
                to_email=email,
                free_apps=free_apps_data,
                price_drops=price_drops_data,
                stats=stats
            )
        
        # Also log the deals for debugging
        if free_apps_data:
            print("\n🎉 Free Apps Today:")
            for app in free_apps_data:
                print(f"  - {app['name']} (was ${app['original_price']})")
        
        if price_drops_data:
            print("\n📉 Price Drops Today:")
            for app in price_drops_data:
                print(f"  - {app['name']}: ${app['original_price']} → ${app['price']} ({app['discount']}% off)")


async def send_immediate_alert(user_email: str, app_id: str, alert_type: str, db: AsyncSession):
    """Send immediate price alert to a specific user"""
    
    from models.app import App
    
    # Get app details
    result = await db.execute(select(App).where(App.id == app_id))
    app = result.scalar_one_or_none()
    
    if not app:
        return
    
    # Get price history for old price
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.app_id == app_id)
        .order_by(desc(PriceHistory.recorded_at))
        .limit(2)
    )
    history = result.scalars().all()
    
    old_price = history[1].new_price if len(history) > 1 else app.original_price
    new_price = app.price
    
    app_data = {
        "id": app.id,
        "name": app.name,
        "developer": app.developer,
        "icon_url": app.icon_url,
        "app_store_url": app.app_store_url
    }
    
    await email_service.send_price_alert(
        to_email=user_email,
        app=app_data,
        old_price=old_price,
        new_price=new_price,
        alert_type=alert_type
    )


# For testing
if __name__ == "__main__":
    import asyncio
    asyncio.run(send_daily_digests())
