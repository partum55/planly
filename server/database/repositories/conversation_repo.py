"""Conversation repository for database operations"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Handle conversation and message database operations"""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_or_create_conversation(
        self,
        conversation_type: str,
        telegram_group_id: Optional[int] = None,
        telegram_group_title: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> dict:
        """Get existing conversation or create new one"""
        try:
            # Try to find existing conversation
            if telegram_group_id:
                response = self.supabase.table('conversations').select('*').eq(
                    'telegram_group_id', telegram_group_id
                ).execute()

                if response.data:
                    return response.data[0]

            # Create new conversation
            data = {
                'conversation_type': conversation_type,
                'telegram_group_id': telegram_group_id,
                'telegram_group_title': telegram_group_title,
                'user_id': str(user_id) if user_id else None
            }

            response = self.supabase.table('conversations').insert(data).execute()
            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Error getting/creating conversation: {e}")
            raise

    async def insert_message(self, conversation_id: UUID, message_data: dict):
        """Insert a message"""
        try:
            data = {
                'conversation_id': str(conversation_id),
                **message_data
            }

            self.supabase.table('messages').insert(data).execute()
        except Exception as e:
            logger.error(f"Error inserting message: {e}")
            # Don't raise - message insertion shouldn't break the flow

    async def get_messages_since(
        self,
        conversation_id: UUID,
        cutoff_time: datetime
    ) -> List[dict]:
        """Get messages since a specific time"""
        try:
            response = self.supabase.table('messages').select('*').eq(
                'conversation_id', str(conversation_id)
            ).gte(
                'timestamp', cutoff_time.isoformat()
            ).order('timestamp').execute()

            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

    async def cleanup_old_messages(self, conversation_id: Optional[UUID] = None):
        """Delete messages older than 1 hour"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=1)

            query = self.supabase.table('messages').delete().lt(
                'timestamp', cutoff_time.isoformat()
            )

            if conversation_id:
                query = query.eq('conversation_id', str(conversation_id))

            query.execute()
            logger.info("Cleaned up old messages")
        except Exception as e:
            logger.error(f"Error cleaning up messages: {e}")

    async def get_conversation_by_id(self, conversation_id: UUID) -> Optional[dict]:
        """Get conversation by ID"""
        try:
            response = self.supabase.table('conversations').select('*').eq(
                'id', str(conversation_id)
            ).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None
