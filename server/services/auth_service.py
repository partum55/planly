"""Authentication service."""
import bcrypt
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional, Tuple
from database.repositories.user_repo import UserRepository
from utils.jwt_utils import generate_access_token, generate_refresh_token
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Handle authentication operations."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(
        self,
        email: str,
        password: Optional[str],
        full_name: Optional[str] = None,
        oauth_provider: Optional[str] = None,
    ) -> Tuple[dict, str, str]:
        """
        Register a new user.

        ``password`` may be None for OAuth-only users.

        Returns: (user, access_token, refresh_token)
        """
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")

        # Hash password (None for OAuth users — they authenticate via provider)
        password_hash: Optional[str] = None
        if password:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")

        # Create user
        user = await self.user_repo.create_user(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            oauth_provider=oauth_provider,
        )

        # Generate tokens
        access_token, refresh_token = await self.generate_tokens(UUID(user["id"]))

        logger.info(f"User registered: {email}")
        return user, access_token, refresh_token

    async def login_user(
        self,
        email: str,
        password: str,
    ) -> Tuple[dict, str, str]:
        """
        Login user.

        Returns: (user, access_token, refresh_token)
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")

        if not user.get("is_active"):
            raise ValueError("Account is disabled")

        # Verify password
        password_hash = user.get("password_hash")
        if not password_hash:
            raise ValueError("This account uses OAuth login. Please sign in with Google.")

        if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
            raise ValueError("Invalid email or password")

        # Generate tokens
        access_token, refresh_token = await self.generate_tokens(UUID(user["id"]))

        # Update last login
        await self.user_repo.update_last_login(UUID(user["id"]))

        logger.info(f"User logged in: {email}")
        return user, access_token, refresh_token

    async def generate_tokens(self, user_id: UUID) -> Tuple[str, str]:
        """Generate access + refresh tokens and persist session."""
        access_token = generate_access_token(user_id)
        refresh_token = generate_refresh_token()

        await self.user_repo.create_session(
            user_id=user_id,
            refresh_token=refresh_token,
            client_type="web",
            expires_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )

        return access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate new access token from refresh token.

        Returns: new access_token
        """
        session = await self.user_repo.get_session_by_token(refresh_token)
        if not session:
            raise ValueError("Invalid refresh token")

        # Check expiration (timezone-aware comparison)
        expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_at:
            raise ValueError("Refresh token expired")

        return generate_access_token(UUID(session["user_id"]))

    async def link_telegram_account(
        self,
        user_id: UUID,
        telegram_id: int,
        telegram_username: Optional[str] = None,
    ) -> bool:
        """Link Telegram account to user."""
        return await self.user_repo.link_telegram(
            user_id=user_id,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
