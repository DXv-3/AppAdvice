"""Application configuration"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AppAdvice API"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/appadvice"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "app-advice"
    PINECONE_NAMESPACE: str = "apps"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Auth
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://appadvice.vercel.app"]
    
    # Scraping
    SCRAPE_INTERVAL_MINUTES: int = 15
    MAX_CONCURRENT_SCRAPES: int = 5
    
    # Email
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "alerts@appadvice.com"
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_PREMIUM: str = ""
    
    class Config:
        env_file = ".env"


settings = Settings()
