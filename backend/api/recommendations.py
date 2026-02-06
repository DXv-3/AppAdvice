"""AI Recommendation API endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from services.pinecone_client import search_similar_apps

router = APIRouter()


class RecommendationResponse(BaseModel):
    id: str
    name: str
    developer: str
    category: str
    price: float
    rating: float
    icon_url: str
    description: str
    relevance_score: float


@router.get("/semantic", response_model=List[RecommendationResponse])
async def semantic_search(
    query: str = Query(..., description="Natural language query"),
    category: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(0.0),
    limit: int = Query(10, ge=1, le=50)
):
    """
    AI-powered semantic search for apps.
    
    Examples:
    - "photo editing with filters"
    - "fitness tracker for running"
    - "meditation app with sleep sounds"
    """
    
    filters = {}
    if category:
        filters["category"] = category
    if max_price is not None:
        filters["max_price"] = max_price
    if min_rating:
        filters["min_rating"] = min_rating
    
    results = await search_similar_apps(
        query=query,
        top_k=limit,
        filters=filters if filters else None
    )
    
    return [
        RecommendationResponse(
            id=r["id"],
            name=r["name"],
            developer=r["developer"],
            category=r["category"],
            price=r["price"],
            rating=r.get("rating", 0) or 0,
            icon_url=r["icon_url"],
            description=r["description"][:200] + "...",
            relevance_score=r["score"]
        )
        for r in results
    ]


@router.get("/similar/{app_id}", response_model=List[RecommendationResponse])
async def find_similar_apps(
    app_id: str,
    limit: int = Query(10, ge=1, le=20)
):
    """Find apps similar to a given app"""
    
    # Get the app's description from database
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Depends
    from core.database import get_db
    from models.app import App
    from sqlalchemy import select
    
    db: AsyncSession = Depends(get_db)
    
    result = await db.execute(select(App).where(App.id == app_id))
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Use app description as query
    query = f"{app.name} {app.description}"
    
    results = await search_similar_apps(
        query=query,
        top_k=limit + 1  # +1 to filter out the app itself
    )
    
    # Filter out the source app
    results = [r for r in results if r["id"] != app_id][:limit]
    
    return [
        RecommendationResponse(
            id=r["id"],
            name=r["name"],
            developer=r["developer"],
            category=r["category"],
            price=r["price"],
            rating=r.get("rating", 0) or 0,
            icon_url=r["icon_url"],
            description=r["description"][:200] + "...",
            relevance_score=r["score"]
        )
        for r in results
    ]


@router.get("/for-you")
async def personalized_recommendations(
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get personalized app recommendations.
    Requires authentication (coming soon).
    """
    # TODO: Implement user preference-based recommendations
    # For now, return trending apps
    
    return {
        "message": "Personalized recommendations coming soon!",
        "note": "This will use your watch history and preferences"
    }
