"""Authentication API routes"""
from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID
import logging

from api.schemas.request_schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    GoogleOAuthCallbackRequest,
    LinkTelegramRequest
)
from api.schemas.response_schemas import TokenResponse, UserResponse, UserProfileResponse
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
            user_id=str(user['id']),
            access_token=access_token,
            refresh_token=refresh_token
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
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
            user_id=str(user['id']),
            access_token=access_token,
            refresh_token=refresh_token
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
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


@router.get("/google/auth-url")
async def get_google_auth_url():
    """
    Get Google OAuth authorization URL for desktop app

    Returns:
        Authorization URL that desktop app should open
    """
    try:
        from config.settings import settings
        from services.oauth_service import GoogleOAuthService

        oauth_service = GoogleOAuthService()

        if not oauth_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )

        redirect_uri = getattr(settings, 'OAUTH_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')
        auth_url = oauth_service.get_authorization_url(redirect_uri)

        return {
            "auth_url": auth_url,
            "redirect_uri": redirect_uri,
            "client_id": oauth_service.client_id
        }

    except Exception as e:
        logger.error(f"Error generating auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.post("/google/callback", response_model=TokenResponse)
async def google_oauth_callback(request: GoogleOAuthCallbackRequest):
    """
    Google OAuth callback - exchanges authorization code for tokens

    Desktop app flow:
    1. Opens Google OAuth consent window
    2. Captures authorization code
    3. POSTs code to this endpoint
    4. Receives JWT tokens
    """
    try:
        from config.settings import settings
        from services.oauth_service import GoogleOAuthService

        # Initialize OAuth service
        oauth_service = GoogleOAuthService()

        # Check if OAuth is configured
        if not oauth_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
            )

        # Determine redirect URI based on environment
        # For production, use settings.OAUTH_REDIRECT_URI if available
        redirect_uri = getattr(settings, 'OAUTH_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')

        # Authenticate user with Google
        auth_result = await oauth_service.authenticate_user(request.code, redirect_uri)
        user_info = auth_result['user_info']

        # Find or create user
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        auth_service = AuthService(user_repo)

        user = await user_repo.get_by_email(user_info['email'])

        if not user:
            # Create new user (no password for OAuth users)
            user, access_token, refresh_token = await auth_service.register_user(
                email=user_info['email'],
                password=None,  # No password for OAuth users
                full_name=user_info.get('name'),
                oauth_provider='google',
            )
            logger.info(f"Created new user via Google OAuth: {user_info['email']}")
        else:
            # Existing user - generate tokens
            access_token, refresh_token = await auth_service.generate_tokens(UUID(user['id']))
            logger.info(f"Existing user logged in via Google OAuth: {user_info['email']}")

        return TokenResponse(
            user_id=str(user['id']),
            access_token=access_token,
            refresh_token=refresh_token
        )

    except ValueError as e:
        logger.error(f"Google OAuth configuration error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OAuth configuration error")
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth authentication failed. Please try again."
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile (validates bearer token)
    Useful for 'Logged in as...' UI
    """
    return UserResponse(
        user_id=str(current_user['id']),
        email=current_user['email'],
        full_name=current_user.get('full_name'),
        avatar_url=current_user.get('avatar_url')
    )


@router.post("/link-telegram/code")
async def generate_link_code(current_user: dict = Depends(get_current_user)):
    """
    Generate a short-lived 6-character code for Telegram account linking.

    Requires a valid JWT (desktop app / web session).  The user then
    types ``/link <CODE>`` in Telegram to complete the binding.
    The code expires after 10 minutes and can only be used once.
    """
    try:
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        auth_service = AuthService(user_repo)

        code = await auth_service.generate_telegram_link_code(
            user_id=UUID(current_user["id"]),
        )

        return {
            "code": code,
            "expires_in_seconds": 600,
            "instruction": (
                f"Send this command in any Telegram chat with the Planly bot:\n"
                f"/link {code}"
            ),
        }

    except Exception as e:
        logger.error(f"Generate link code error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate link code",
        )


@router.post("/link-telegram")
async def link_telegram(request: LinkTelegramRequest):
    """
    Redeem a link code to bind a Telegram identity to a Planly account.

    No JWT required — called by the Telegram bot.  Security is enforced
    by the short-lived, single-use code that was generated from an
    authenticated session.
    """
    try:
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        auth_service = AuthService(user_repo)

        user = await auth_service.redeem_telegram_link_code(
            code=request.code,
            telegram_id=request.telegram_id,
            telegram_username=request.telegram_username,
        )

        return {
            "success": True,
            "user_id": str(user["id"]),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Link Telegram error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link Telegram account",
        )


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify token and return user info (legacy endpoint, use /auth/me instead)"""
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "full_name": current_user.get('full_name'),
        "telegram_id": current_user.get('telegram_id'),
        "telegram_username": current_user.get('telegram_username')
    }
