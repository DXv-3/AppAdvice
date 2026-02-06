"""SQLAlchemy models for Apps"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base


class App(Base):
    """iOS App model"""
    __tablename__ = "apps"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # App Store ID
    name: Mapped[str] = mapped_column(String(255), index=True)
    developer: Mapped[str] = mapped_column(String(255), index=True)
    developer_id: Mapped[str] = mapped_column(String(50), index=True)
    
    # App Store metadata
    bundle_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Pricing
    price: Mapped[float] = mapped_column(Float, default=0.0)
    original_price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    has_in_app_purchases: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Ratings
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Media
    icon_url: Mapped[str] = mapped_column(Text)
    screenshots: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Content
    description: Mapped[str] = mapped_column(Text)
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # App Store URLs
    app_store_url: Mapped[str] = mapped_column(Text)
    affiliate_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    release_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_rating: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    languages: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # System
    minimum_os_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    supported_devices: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Tracking
    price_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    price_history: Mapped[List["PriceHistory"]] = relationship(back_populates="app", lazy="selectin")
    
    # Indexes
    __table_args__ = (
        Index('ix_apps_price_drop', 'is_free', 'original_price', 'price'),
        Index('ix_apps_category_rating', 'category', 'rating'),
        Index('ix_apps_last_updated', 'last_updated'),
    )


class PriceHistory(Base):
    """Price change history for apps"""
    __tablename__ = "price_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    
    old_price: Mapped[float] = mapped_column(Float)
    new_price: Mapped[float] = mapped_column(Float)
    change_percentage: Mapped[float] = mapped_column(Float)
    
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    app: Mapped["App"] = relationship(back_populates="price_history")
