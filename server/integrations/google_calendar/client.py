"""Google Calendar API client"""
import asyncio
import os
from datetime import datetime
from typing import Optional
import logging

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config.settings import settings

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """Wrapper for Google Calendar API"""

    def __init__(self):
        self.service = None
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self._initialize()

    def _initialize(self):
        """Initialize Google Calendar service"""
        try:
            # Check if service account file exists
            if not os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_FILE):
                logger.warning(f"Service account file not found: {settings.GOOGLE_SERVICE_ACCOUNT_FILE}")
                logger.warning("Calendar tool will return mock events")
                return

            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=['https://www.googleapis.com/auth/calendar']
            )

            # Build service
            self.service = build('calendar', 'v3', credentials=credentials)

            logger.info("✓ Google Calendar client initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar client: {e}")
            logger.warning("Calendar tool will return mock events")

    async def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        description: Optional[str] = None,
        attendees: Optional[list] = None
    ) -> dict:
        """Create a calendar event"""
        if not self.service:
            raise Exception("Google Calendar service not initialized")

        event = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        # Google API client is synchronous — run in a thread to avoid
        # blocking the asyncio event loop.
        created_event = await asyncio.to_thread(
            self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute
        )

        return created_event

    async def list_events(self, max_results: int = 10) -> list:
        """List upcoming events"""
        if not self.service:
            return []

        events_result = await asyncio.to_thread(
            self.service.events().list(
                calendarId=self.calendar_id,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute
        )

        return events_result.get('items', [])
