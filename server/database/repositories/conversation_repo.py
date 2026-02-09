"""Conversation repository for database operations."""
from asyncio import to_thread
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta, timezone
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Handle conversation and message database operations."""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_or_create_conversation(
        self,
        conversation_type: str,
        telegram_group_id: Optional[int] = None,
        telegram_group_title: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> dict:
        """Get existing conversation or create new one."""
        try:
            if telegram_group_id:
                response = await to_thread(
                    lambda: self.supabase.table("conversations")
                    .select("*")
                    .eq("telegram_group_id", telegram_group_id)
                    .execute()
                )
                if response.data:
                    return response.data[0]

            data = {
                "conversation_type": conversation_type,
                "telegram_group_id": telegram_group_id,
                "telegram_group_title": telegram_group_title,
                "user_id": str(user_id) if user_id else None,
            }

            response = await to_thread(
                lambda: self.supabase.table("conversations").insert(data).execute()
            )
            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Error getting/creating conversation: {e}")
            raise

    async def insert_message(self, conversation_id: UUID, message_data: dict) -> bool:
        """Insert a message. Returns True on success, False on failure."""
        try:
            data = {
                "conversation_id": str(conversation_id),
                **message_data,
            }
            await to_thread(
                lambda: self.supabase.table("messages").insert(data).execute()
            )
            return True
        except Exception as e:
            logger.error(f"Error inserting message: {e}", exc_info=True)
            return False

    async def insert_messages_batch(
        self, conversation_id: UUID, messages: List[dict]
    ) -> bool:
        """Insert multiple messages in a single DB round-trip."""
        if not messages:
            return True
        try:
            rows = [
                {"conversation_id": str(conversation_id), **msg}
                for msg in messages
            ]
            await to_thread(
                lambda: self.supabase.table("messages").insert(rows).execute()
            )
            return True
        except Exception as e:
            logger.error(f"Error batch-inserting messages: {e}", exc_info=True)
            return False

    async def get_messages_since(
        self,
        conversation_id: UUID,
        cutoff_time: datetime,
    ) -> List[dict]:
        """Get messages since a specific time.

        Raises on database errors so callers can distinguish 'no messages'
        from 'database is down'.
        """
        try:
            response = await to_thread(
                lambda: self.supabase.table("messages")
                .select("*")
                .eq("conversation_id", str(conversation_id))
                .gte("timestamp", cutoff_time.isoformat())
                .order("timestamp")
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise

    async def cleanup_old_messages(self, conversation_id: Optional[UUID] = None):
        """Delete messages older than 1 hour."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)

            def _do_delete():
                query = self.supabase.table("messages").delete().lt(
                    "timestamp", cutoff_time.isoformat()
                )
                if conversation_id:
                    query = query.eq("conversation_id", str(conversation_id))
                query.execute()

            await to_thread(_do_delete)
            logger.info("Cleaned up old messages")
        except Exception as e:
            logger.error(f"Error cleaning up messages: {e}")

    async def get_conversation_by_id(self, conversation_id: UUID) -> Optional[dict]:
        """Get conversation by ID.

        Returns None if not found. Raises on database errors.
        """
        try:
            response = await to_thread(
                lambda: self.supabase.table("conversations")
                .select("*")
                .eq("id", str(conversation_id))
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            raise
