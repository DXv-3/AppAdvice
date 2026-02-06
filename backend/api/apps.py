"""App API endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel

from core.database import get_db
from models.app import App, PriceHistory
from services.pinecone_client import search_similar_apps

router = APIRouter()


class AppResponse(BaseModel):
    id: str
    name: str
    developer: str
    category: str
    price: float
    original_price: float
    is_free: bool
    rating: Optional[float]
    rating_count: int
    icon_url: str
    description: str
    app_store_url: str
    last_updated: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[AppResponse])
async def list_apps(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    max_price: Optional[float] = Query(None, ge=0),
    is_free: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: str = Query("last_updated", regex="^(last_updated|price|rating|name)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List apps with filters and pagination"""
    
    query = select(App).where(App.is_active == True)
    
    # Apply filters
    if category:
        query = query.where(App.category == category)
    if min_rating:
        query = query.where(App.rating >= min_rating)
    if max_price is not None:
        query = query.where(App.price <= max_price)
    if is_free is not None:
        query = query.where(App.is_free == is_free)
    if search:
        query = query.where(
            App.name.ilike(f"%{search}%") | 
            App.description.ilike(f"%{search}%")
        )
    
    # Sorting
    if sort_by == "price":
        query = query.order_by(App.price)
    elif sort_by == "rating":
        query = query.order_by(desc(App.rating))
    elif sort_by == "name":
        query = query.order_by(App.name)
    else:
        query = query.order_by(desc(App.last_updated))
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    apps = result.scalars().all()
    
    return apps


@router.get("/deals", response_model=List[AppResponse])
async def get_deals(
    deal_type: str = Query("all", regex="^(all|free|price_drop)$"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get current deals - free apps or price drops"""
    
    query = select(App).where(App.is_active == True)
    
    if deal_type == "free":
        query = query.where(App.is_free == True, App.original_price > 0)
    elif deal_type == "price_drop":
        query = query.where(App.price < App.original_price)
    else:
        query = query.where(
            (App.is_free == True) | (App.price < App.original_price)
        )
    
    query = query.order_by(desc(App.price_changed_at)).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(app_id: str, db: AsyncSession = Depends(get_db)):
    """Get single app details"""
    result = await db.execute(select(App).where(App.id == app_id))
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    return app


@router.get("/{app_id}/price-history")
async def get_price_history(
    app_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get price history for an app"""
    from datetime import datetime, timedelta
    
    since = datetime.utcnow() - timedelta(days=days)
    
    query = select(PriceHistory).where(
        PriceHistory.app_id == app_id,
        PriceHistory.recorded_at >= since
    ).order_by(PriceHistory.recorded_at)
    
    result = await db.execute(query)
    history = result.scalars().all()
    
    return {
        "app_id": app_id,
        "data": [
            {
                "old_price": h.old_price,
                "new_price": h.new_price,
                "change_percentage": h.change_percentage,
                "date": h.recorded_at.isoformat()
            }
            for h in history
        ]
    }


@router.get("/categories/list")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Get all app categories with counts"""
    
    query = select(App.category, func.count(App.id)).where(
        App.is_active == True
    ).group_by(App.category).order_by(desc(func.count(App.id)))
    
    result = await db.execute(query)
    categories = result.all()
    
    return [
        {"name": cat, "count": count}
        for cat, count in categories
    ]
