"""Event repository for database operations."""
from asyncio import to_thread
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class EventRepository:
    """Handle event database operations."""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def create_event(
        self,
        conversation_id: UUID,
        user_id: UUID,
        activity_type: str,
        event_time: datetime,
        participants: list,
        activity_name: Optional[str] = None,
        location: Optional[str] = None,
        calendar_event_id: Optional[str] = None,
        activity_details: Optional[dict] = None,
    ) -> dict:
        """Create a new event."""
        try:
            data = {
                "conversation_id": str(conversation_id),
                "created_by_user_id": str(user_id),
                "activity_type": activity_type,
                "activity_name": activity_name,
                "activity_details": activity_details or {},
                "participants": participants,
                "event_time": event_time.isoformat(),
                "location": location,
                "calendar_event_id": calendar_event_id,
                "status": "active",
            }

            response = await to_thread(
                lambda: self.supabase.table("events").insert(data).execute()
            )
            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Error creating event: {e}")
            raise

    async def get_events_by_conversation(
        self,
        conversation_id: UUID,
    ) -> List[dict]:
        """Get all events for a conversation."""
        try:
            response = await to_thread(
                lambda: self.supabase.table("events")
                .select("*")
                .eq("conversation_id", str(conversation_id))
                .order("event_time", desc=True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []

    async def get_events_by_user(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[dict]:
        """Get events created by or including a user."""
        try:
            def _query():
                q = self.supabase.table("events").select("*").eq(
                    "created_by_user_id", str(user_id)
                )
                if start_date:
                    q = q.gte("event_time", start_date.isoformat())
                if end_date:
                    q = q.lte("event_time", end_date.isoformat())
                return q.order("event_time").execute()

            response = await to_thread(_query)
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting user events: {e}")
            return []

    async def log_action(
        self,
        conversation_id: UUID,
        user_id: Optional[UUID],
        trigger_source: str,
        action_type: str,
        intent_data: dict,
        tool_calls: list,
        response_text: Optional[str],
        success: bool,
        execution_time_ms: int,
        error_message: Optional[str] = None,
    ):
        """Log an agent action."""
        try:
            data = {
                "conversation_id": str(conversation_id),
                "user_id": str(user_id) if user_id else None,
                "trigger_source": trigger_source,
                "action_type": action_type,
                "intent_data": intent_data,
                "tool_calls": tool_calls,
                "response_text": response_text,
                "success": success,
                "error_message": error_message,
                "execution_time_ms": execution_time_ms,
            }

            await to_thread(
                lambda: self.supabase.table("agent_actions").insert(data).execute()
            )
        except Exception as e:
            logger.error(f"Error logging action: {e}")
