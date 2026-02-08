"""User repository for database operations"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class UserRepository:
    """Handle user database operations"""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: Optional[str] = None
    ) -> dict:
        """Create a new user"""
        try:
            response = self.supabase.table('users').insert({
                'email': email,
                'password_hash': password_hash,
                'full_name': full_name,
                'is_active': True
            }).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    async def get_by_email(self, email: str) -> Optional[dict]:
        """Get user by email"""
        try:
            response = self.supabase.table('users').select('*').eq(
                'email', email
            ).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    async def get_by_id(self, user_id: UUID) -> Optional[dict]:
        """Get user by ID"""
        try:
            response = self.supabase.table('users').select('*').eq(
                'id', str(user_id)
            ).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Get user by Telegram ID"""
        try:
            response = self.supabase.table('users').select('*').eq(
                'telegram_id', telegram_id
            ).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting user by Telegram ID: {e}")
            return None

    async def link_telegram(
        self,
        user_id: UUID,
        telegram_id: int,
        telegram_username: Optional[str] = None
    ) -> bool:
        """Link Telegram account to user"""
        try:
            self.supabase.table('users').update({
                'telegram_id': telegram_id,
                'telegram_username': telegram_username
            }).eq('id', str(user_id)).execute()

            return True
        except Exception as e:
            logger.error(f"Error linking Telegram account: {e}")
            return False

    async def update_last_login(self, user_id: UUID):
        """Update user's last login timestamp"""
        try:
            self.supabase.table('users').update({
                'last_login': datetime.utcnow().isoformat()
            }).eq('id', str(user_id)).execute()
        except Exception as e:
            logger.error(f"Error updating last login: {e}")

    async def create_session(
        self,
        user_id: UUID,
        refresh_token: str,
        client_type: str,
        expires_days: int = 30
    ) -> dict:
        """Create a new user session"""
        try:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

            response = self.supabase.table('user_sessions').insert({
                'user_id': str(user_id),
                'refresh_token': refresh_token,
                'client_type': client_type,
                'expires_at': expires_at.isoformat()
            }).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    async def get_session_by_token(self, refresh_token: str) -> Optional[dict]:
        """Get session by refresh token"""
        try:
            response = self.supabase.table('user_sessions').select('*').eq(
                'refresh_token', refresh_token
            ).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    async def delete_session(self, refresh_token: str):
        """Delete a session"""
        try:
            self.supabase.table('user_sessions').delete().eq(
                'refresh_token', refresh_token
            ).execute()
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
