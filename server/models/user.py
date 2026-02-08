"""User data models"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class User(BaseModel):
    """User model"""
    id: UUID
    email: EmailStr
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    oauth_provider: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    preferences: dict = {}

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation model"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID


class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str
