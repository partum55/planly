"""User repository for database operations."""
from asyncio import to_thread
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class UserRepository:
    """Handle user database operations."""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def create_user(
        self,
        email: str,
        password_hash: Optional[str],
        full_name: Optional[str] = None,
        oauth_provider: Optional[str] = None,
    ) -> dict:
        """Create a new user."""
        try:
            data: dict = {
                "email": email,
                "full_name": full_name,
                "is_active": True,
            }
            if password_hash:
                data["password_hash"] = password_hash
            if oauth_provider:
                data["oauth_provider"] = oauth_provider

            response = await to_thread(
                lambda: self.supabase.table("users").insert(data).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    async def get_by_email(self, email: str) -> Optional[dict]:
        """Get user by email."""
        try:
            response = await to_thread(
                lambda: self.supabase.table("users")
                .select("*")
                .eq("email", email)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    async def get_by_id(self, user_id: UUID) -> Optional[dict]:
        """Get user by ID."""
        try:
            response = await to_thread(
                lambda: self.supabase.table("users")
                .select("*")
                .eq("id", str(user_id))
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Get user by Telegram ID."""
        try:
            response = await to_thread(
                lambda: self.supabase.table("users")
                .select("*")
                .eq("telegram_id", telegram_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting user by Telegram ID: {e}")
            return None

    async def link_telegram(
        self,
        user_id: UUID,
        telegram_id: int,
        telegram_username: Optional[str] = None,
    ) -> bool:
        """Link Telegram account to user."""
        try:
            await to_thread(
                lambda: self.supabase.table("users")
                .update(
                    {
                        "telegram_id": telegram_id,
                        "telegram_username": telegram_username,
                    }
                )
                .eq("id", str(user_id))
                .execute()
            )
            return True
        except Exception as e:
            logger.error(f"Error linking Telegram account: {e}")
            return False

    async def update_last_login(self, user_id: UUID):
        """Update user's last login timestamp."""
        try:
            await to_thread(
                lambda: self.supabase.table("users")
                .update({"last_login": datetime.now(timezone.utc).isoformat()})
                .eq("id", str(user_id))
                .execute()
            )
        except Exception as e:
            logger.error(f"Error updating last login: {e}")

    async def create_session(
        self,
        user_id: UUID,
        refresh_token: str,
        client_type: str,
        expires_days: int = 30,
    ) -> dict:
        """Create a new user session."""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

            response = await to_thread(
                lambda: self.supabase.table("user_sessions")
                .insert(
                    {
                        "user_id": str(user_id),
                        "refresh_token": refresh_token,
                        "client_type": client_type,
                        "expires_at": expires_at.isoformat(),
                    }
                )
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    async def get_session_by_token(self, refresh_token: str) -> Optional[dict]:
        """Get session by refresh token."""
        try:
            response = await to_thread(
                lambda: self.supabase.table("user_sessions")
                .select("*")
                .eq("refresh_token", refresh_token)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    async def delete_session(self, refresh_token: str):
        """Delete a session."""
        try:
            await to_thread(
                lambda: self.supabase.table("user_sessions")
                .delete()
                .eq("refresh_token", refresh_token)
                .execute()
            )
        except Exception as e:
            logger.error(f"Error deleting session: {e}")

    # ------------------------------------------------------------------
    # Telegram link codes
    # ------------------------------------------------------------------

    async def create_link_code(
        self,
        user_id: UUID,
        code: str,
        expires_minutes: int = 10,
    ) -> Optional[dict]:
        """Store a new Telegram link code for the given user.

        Any existing unconsumed codes for this user are invalidated first
        so that only one active code exists at a time.
        """
        try:
            # Invalidate previous codes for this user
            await to_thread(
                lambda: self.supabase.table("telegram_link_codes")
                .update({"consumed": True})
                .eq("user_id", str(user_id))
                .eq("consumed", False)
                .execute()
            )

            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
            response = await to_thread(
                lambda: self.supabase.table("telegram_link_codes")
                .insert({
                    "user_id": str(user_id),
                    "code": code,
                    "expires_at": expires_at.isoformat(),
                })
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating link code: {e}")
            raise

    async def consume_link_code(self, code: str) -> Optional[dict]:
        """Atomically consume a link code and return the associated user_id.

        Uses UPDATE ... WHERE consumed=FALSE which serializes via row-level
        locking — only the first caller gets the row back.
        Returns None if the code is missing, expired, or already consumed.
        """
        try:
            resp = await to_thread(
                lambda: self.supabase.table("telegram_link_codes")
                .update({"consumed": True})
                .eq("code", code)
                .eq("consumed", False)
                .gte("expires_at", datetime.now(timezone.utc).isoformat())
                .execute()
            )
            if not resp.data:
                return None
            return resp.data[0]
        except Exception as e:
            logger.error(f"Error consuming link code: {e}")
            return None
