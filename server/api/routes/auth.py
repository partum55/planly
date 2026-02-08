"""Authentication API routes"""
from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID
import logging

from api.schemas.request_schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    LinkTelegramRequest
)
from api.schemas.response_schemas import TokenResponse, UserResponse
from api.middleware.auth_middleware import get_current_user
from database.client import get_supabase
from database.repositories.user_repo import UserRepository
from services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Register a new user"""
    try:
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        auth_service = AuthService(user_repo)

        user, access_token, refresh_token = await auth_service.register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )

        return TokenResponse(
            user_id=UUID(user['id']),
            access_token=access_token,
            refresh_token=refresh_token
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login user"""
    try:
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        auth_service = AuthService(user_repo)

        user, access_token, refresh_token = await auth_service.login_user(
            email=request.email,
            password=request.password
        )

        return TokenResponse(
            user_id=UUID(user['id']),
            access_token=access_token,
            refresh_token=refresh_token
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token"""
    try:
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        auth_service = AuthService(user_repo)

        new_access_token = await auth_service.refresh_access_token(request.refresh_token)

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token refresh failed")


@router.post("/link-telegram")
async def link_telegram(
    request: LinkTelegramRequest,
    current_user: dict = Depends(get_current_user)
):
    """Link Telegram account to user"""
    try:
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        auth_service = AuthService(user_repo)

        success = await auth_service.link_telegram_account(
            user_id=UUID(current_user['id']),
            telegram_id=request.telegram_id,
            telegram_username=request.telegram_username
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to link Telegram account")

        return {"success": True, "message": "Telegram account linked successfully"}

    except Exception as e:
        logger.error(f"Link Telegram error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to link Telegram account")


@router.get("/verify", response_model=UserResponse)
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify token and return user info"""
    return UserResponse(
        id=UUID(current_user['id']),
        email=current_user['email'],
        full_name=current_user.get('full_name'),
        telegram_id=current_user.get('telegram_id'),
        telegram_username=current_user.get('telegram_username')
    )
