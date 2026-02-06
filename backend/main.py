"""
AppAdvice System - FastAPI Backend
Main application entry point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.apps import router as apps_router
from api.users import router as users_router
from api.recommendations import router as recommendations_router
from api.alerts import router as alerts_router
from core.config import settings
from core.database import init_db
from services.scheduler import start_scheduler, stop_scheduler
from services.pinecone_client import init_pinecone


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    await init_pinecone()
    await start_scheduler()
    
    yield
    
    # Shutdown
    await stop_scheduler()


app = FastAPI(
    title="AppAdvice API",
    description="AI-powered iOS app discovery platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(apps_router, prefix="/api/v1/apps", tags=["apps"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(recommendations_router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["alerts"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
