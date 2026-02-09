"""Authentication API routes"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import RedirectResponse
from uuid import UUID
from urllib.parse import urlencode, urlparse
import base64
import json
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


@router.get("/google/login")
async def google_oauth_login(redirect: str = Query(..., description="Desktop app callback URL")):
    """
    Browser-based Google OAuth flow for desktop app.

    Opens Google consent screen and redirects back to the desktop app's
    local callback server with tokens after authentication.

    The `redirect` param must be a localhost/127.0.0.1 URL (the desktop
    app's temporary HTTP callback server).
    """
    try:
        from config.settings import settings
        from services.oauth_service import GoogleOAuthService

        oauth_service = GoogleOAuthService()

        if not oauth_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured",
            )

        # Security: only allow redirects to localhost
        parsed = urlparse(redirect)
        if parsed.hostname not in ("127.0.0.1", "localhost"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="redirect must be a localhost URL",
            )

        # Encode desktop redirect into state so we can recover it in the callback
        state_payload = json.dumps({"redirect": redirect})
        state = base64.urlsafe_b64encode(state_payload.encode()).decode()

        # Google will redirect back to the backend's own GET callback
        backend_callback = settings.OAUTH_REDIRECT_URI
        auth_url = oauth_service.get_authorization_url(backend_callback, state=state)

        return RedirectResponse(url=auth_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Google OAuth flow",
        )


@router.get("/google/callback")
async def google_oauth_callback_get(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
):
    """
    Google OAuth GET callback — handles the browser redirect from Google.

    Exchanges the authorization code for tokens, creates/finds the user,
    then redirects the browser to the desktop app's local callback server
    with access_token and refresh_token as query params.
    """
    # If Google returned an error, try to redirect with error
    if error:
        if state:
            try:
                state_data = json.loads(base64.urlsafe_b64decode(state).decode())
                desktop_redirect = state_data.get("redirect", "")
                if desktop_redirect:
                    return RedirectResponse(
                        url=f"{desktop_redirect}?error={error}",
                        status_code=302,
                    )
            except Exception:
                pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Google OAuth error: {error}")

    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state parameter")

    try:
        # Decode state to get desktop redirect URL
        state_data = json.loads(base64.urlsafe_b64decode(state).decode())
        desktop_redirect = state_data.get("redirect")
        if not desktop_redirect:
            raise ValueError("No redirect in state")

        # Validate redirect is still localhost
        parsed = urlparse(desktop_redirect)
        if parsed.hostname not in ("127.0.0.1", "localhost"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid redirect in state",
            )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid OAuth state: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter")

    try:
        from config.settings import settings
        from services.oauth_service import GoogleOAuthService

        oauth_service = GoogleOAuthService()

        if not oauth_service.is_configured():
            return RedirectResponse(
                url=f"{desktop_redirect}?error=oauth_not_configured",
                status_code=302,
            )

        backend_callback = settings.OAUTH_REDIRECT_URI
        auth_result = await oauth_service.authenticate_user(code, backend_callback)
        user_info = auth_result["user_info"]

        # Find or create user
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        auth_service = AuthService(user_repo)

        user = await user_repo.get_by_email(user_info["email"])

        if not user:
            user, access_token, refresh_token = await auth_service.register_user(
                email=user_info["email"],
                password=None,
                full_name=user_info.get("name"),
                oauth_provider="google",
            )
            logger.info(f"Created new user via Google OAuth (browser flow): {user_info['email']}")
        else:
            access_token, refresh_token = await auth_service.generate_tokens(UUID(user["id"]))
            logger.info(f"Existing user logged in via Google OAuth (browser flow): {user_info['email']}")

        # Redirect browser to desktop app's local callback with tokens
        params = urlencode({"access_token": access_token, "refresh_token": refresh_token})
        return RedirectResponse(url=f"{desktop_redirect}?{params}", status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth callback (browser) error: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{desktop_redirect}?error=authentication_failed",
            status_code=302,
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
