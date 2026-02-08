"""Google Calendar tool"""
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from tools.base import BaseTool, ToolSchema, ToolParameter
from integrations.google_calendar.client import GoogleCalendarClient

logger = logging.getLogger(__name__)


class CalendarTool(BaseTool):
    """Google Calendar event creation tool"""

    def __init__(self, calendar_client: GoogleCalendarClient = None):
        self.calendar_client = calendar_client

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="calendar_create_event",
            description="Create a calendar event for a group activity",
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

            # If calendar client is not initialized (for testing), return mock
            if not self.calendar_client:
                logger.warning("Calendar client not initialized, returning mock event")
                return {
                    'success': True,
                    'event_id': 'mock_event_123',
                    'event_link': 'https://calendar.google.com/event?eid=mock_event_123',
                    'event_details': {
                        'title': title,
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat(),
                        'location': location,
                        'description': description
                    }
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
            logger.error(f"Calendar tool error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
