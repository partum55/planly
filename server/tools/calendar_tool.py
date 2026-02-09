"""Google Calendar tool"""
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from tools.base import BaseTool, ToolSchema, ToolParameter, ToolMetadata
from integrations.google_calendar.client import GoogleCalendarClient

logger = logging.getLogger(__name__)


class CalendarTool(BaseTool):
    """Google Calendar event creation tool"""

    def __init__(self, calendar_client: GoogleCalendarClient = None):
        self.calendar_client = calendar_client

    @property
    def _is_configured(self) -> bool:
        return self.calendar_client is not None

    def _build_schema(self) -> ToolSchema:
        return ToolSchema(
            name="calendar_create_event",
            description=(
                "Create a new Google Calendar event. This is a WRITE operation that "
                "permanently adds an event to the linked calendar. Requires title and "
                "datetime at minimum. Returns the event ID and a direct link to the "
                "created event. Cannot be undone via this tool."
            ),
            metadata=ToolMetadata(
                destructive_hint=True,
                read_only_hint=False,
                idempotent_hint=False,
                open_world_hint=True,
                requires_auth_hint=True,
                mock_mode=not self._is_configured,
            ),
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="Event title/name",
                    required=True
                ),
                ToolParameter(
                    name="datetime",
                    type="string",
                    description="Event start time in ISO8601 format",
                    required=True
                ),
                ToolParameter(
                    name="duration_minutes",
                    type="integer",
                    description="Event duration in minutes",
                    required=False,
                    default=120
                ),
                ToolParameter(
                    name="location",
                    type="string",
                    description="Event location",
                    required=False
                ),
                ToolParameter(
                    name="description",
                    type="string",
                    description="Event description/notes",
                    required=False
                )
            ]
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Create a Google Calendar event

        Returns:
        {
            'success': bool,
            'event_id': str,
            'event_link': str,
            'event_details': dict
        }
        """
        try:
            await self.validate_parameters(**kwargs)

            title = kwargs['title']
            datetime_str = kwargs['datetime']
            duration_minutes = kwargs.get('duration_minutes', 120)
            location = kwargs.get('location')
            description = kwargs.get('description')

            # Parse datetime
            if isinstance(datetime_str, str):
                start_time = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            else:
                start_time = datetime_str

            end_time = start_time + timedelta(minutes=duration_minutes)

            # Fail explicitly when calendar client is not configured
            if not self.calendar_client:
                logger.error("Calendar client not configured — cannot create event")
                return {
                    'success': False,
                    'error': (
                        "Google Calendar is not configured. "
                        "Please link your Google account before creating events."
                    ),
                }

            # Create event via Google Calendar API
            event = await self.calendar_client.create_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                location=location,
                description=description
            )

            logger.info(f"Created calendar event: {title} at {start_time}")

            return {
                'success': True,
                'event_id': event['id'],
                'event_link': event.get('htmlLink', ''),
                'event_details': event
            }

        except Exception as e:
            logger.error(f"Calendar tool error: {e}", exc_info=True)
            return {
                'success': False,
                'error': "Failed to create calendar event. Please try again.",
            }
