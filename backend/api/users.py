"""User API endpoints - Authentication, favorites, and user management"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from jose import jwt, JWTError
from passlib.context import CryptContext

from core.database import get_db
from core.config import settings
from models.app import App

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()
security = HTTPBearer()


# --- Pydantic Models ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: str
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class FavoriteAdd(BaseModel):
    app_id: str


class FavoriteResponse(BaseModel):
    id: str
    app_id: str
    app_name: str
    app_icon: str
    price: float
    added_at: str


# --- In-Memory User Store (Replace with database model in production) ---
# For now, using a simple dict. In production, create a proper User model
_users = {}
_favorites = {}  # user_id -> list of favorites
_id_counter = 0


def _generate_id():
    global _id_counter
    _id_counter += 1
    return f"user_{_id_counter}"


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Validate JWT token and return current user"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id or user_id not in _users:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return _users[user_id]
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


# --- Authentication Endpoints ---

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    # Check if email already exists
    for user in _users.values():
        if user["email"] == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    user_id = _generate_id()
    user = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": _hash_password(user_data.password),
        "created_at": datetime.utcnow().isoformat()
    }
    
    _users[user_id] = user
    _favorites[user_id] = []
    
    token = _create_token(user_id)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user_id,
            email=user.email,
            name=user.name,
            created_at=user.created_at
        )
    }


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get access token"""
    # Find user by email
    user = None
    for u in _users.values():
        if u["email"] == login_data.email:
            user = u
            break
    
    if not user or not _verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    token = _create_token(user["id"])
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            created_at=user["created_at"]
        )
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(_get_current_user)):
    """Get current user profile"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        created_at=current_user["created_at"]
    )


# --- Favorites Endpoints ---

@router.post("/favorites", response_model=FavoriteResponse)
async def add_favorite(
    favorite: FavoriteAdd,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add an app to favorites"""
    user_id = current_user["id"]
    
    # Check if app exists
    result = await db.execute(select(App).where(App.id == favorite.app_id))
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Check if already in favorites
    existing = [f for f in _favorites.get(user_id, []) if f["app_id"] == favorite.app_id]
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="App already in favorites"
        )
    
    favorite_item = {
        "id": f"fav_{len(_favorites.get(user_id, [])) + 1}",
        "app_id": favorite.app_id,
        "app_name": app.name,
        "app_icon": app.icon_url,
        "price": app.price,
        "added_at": datetime.utcnow().isoformat()
    }
    
    if user_id not in _favorites:
        _favorites[user_id] = []
    _favorites[user_id].append(favorite_item)
    
    return FavoriteResponse(**favorite_item)


@router.get("/favorites", response_model=List[FavoriteResponse])
async def get_favorites(current_user: dict = Depends(_get_current_user)):
    """Get user's favorite apps"""
    user_id = current_user["id"]
    favorites = _favorites.get(user_id, [])
    return [FavoriteResponse(**f) for f in favorites]


@router.delete("/favorites/{app_id}")
async def remove_favorite(
    app_id: str,
    current_user: dict = Depends(_get_current_user)
):
    """Remove an app from favorites"""
    user_id = current_user["id"]
    
    if user_id not in _favorites:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No favorites found"
        )
    
    original_count = len(_favorites[user_id])
    _favorites[user_id] = [f for f in _favorites[user_id] if f["app_id"] != app_id]
    
    if len(_favorites[user_id]) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not in favorites"
        )
    
    return {"message": "Removed from favorites"}


# --- Watchlist / Price Alerts (User-specific) ---

@router.get("/watchlist")
async def get_watchlist(current_user: dict = Depends(_get_current_user)):
    """Get apps the user is watching for price drops"""
    # This could be a separate table in production
    # For now, return favorites as watchlist
    user_id = current_user["id"]
    favorites = _favorites.get(user_id, [])
    return {
        "watchlist": [
            {
                "app_id": f["app_id"],
                "app_name": f["app_name"],
                "current_price": f["price"],
                "target_price": None,  # User could set target price
                "added_at": f["added_at"]
            }
            for f in favorites
        ]
    }
