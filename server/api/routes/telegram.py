"""Telegram webhook API route"""
from fastapi import APIRouter, HTTPException, status
from uuid import UUID
from datetime import datetime
import logging

from api.schemas.request_schemas import TelegramWebhookRequest
from api.schemas.response_schemas import TelegramWebhookResponse
from database.client import get_supabase
from database.repositories.conversation_repo import ConversationRepository
from database.repositories.event_repo import EventRepository
from core.agent import TelegramAgent
from core.context_manager import ContextManager
from core.reasoning_engine import ReasoningEngine
from integrations.ollama.client import OllamaClient
from tools.base import ToolRegistry
from tools.calendar_tool import CalendarTool
from tools.restaurant_tool import RestaurantSearchTool
from tools.cinema_tool import CinemaSearchTool
from integrations.google_calendar.client import GoogleCalendarClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_agent() -> TelegramAgent:
    """Initialize and return agent"""
    supabase = get_supabase()
    conversation_repo = ConversationRepository(supabase)
    event_repo = EventRepository(supabase)

    ollama_client = OllamaClient()

    tool_registry = ToolRegistry()
    calendar_client = GoogleCalendarClient()
    tool_registry.register(CalendarTool(calendar_client))
    tool_registry.register(RestaurantSearchTool())
    tool_registry.register(CinemaSearchTool())

    context_manager = ContextManager(conversation_repo)
    reasoning_engine = ReasoningEngine(ollama_client, tool_registry)

    agent = TelegramAgent(
        context_manager=context_manager,
        reasoning_engine=reasoning_engine,
        tool_registry=tool_registry,
        event_repo=event_repo
    )

    return agent


@router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(request: TelegramWebhookRequest):
    """
    Receive messages from Telegram bot client

    This endpoint:
    1. Stores message in database
    2. If bot is mentioned: runs full ORPLAR loop and returns response
    3. Otherwise: just stores message and returns None
    """
    try:
        supabase = get_supabase()
        conversation_repo = ConversationRepository(supabase)

        # Get or create conversation for this Telegram group
        conversation = await conversation_repo.get_or_create_conversation(
            conversation_type='telegram_group',
            telegram_group_id=request.group_id,
            telegram_group_title=request.group_title
        )
        conversation_id = UUID(conversation['id'])

        # Store message
        message_data = {
            'message_id': request.message_id,
            'user_id': request.user_id,
            'username': request.username,
            'first_name': request.first_name,
            'last_name': request.last_name,
            'text': request.text,
            'timestamp': request.timestamp,
            'source': 'telegram',
            'is_bot_mention': request.is_bot_mention
        }

        await conversation_repo.insert_message(conversation_id, message_data)

        # If bot is mentioned, process and respond
        if request.is_bot_mention:
            logger.info(f"Bot mentioned in group {request.group_id}, processing...")

            agent = get_agent()

            # Run full ORPLAR loop
            response_text = await agent.process_mention(
                conversation_id=conversation_id,
                user_id=None  # For Telegram, we don't have user account mapping yet
            )

            logger.info(f"Response: {response_text}")

            return TelegramWebhookResponse(response_text=response_text)

        # Not mentioned, just acknowledge
        return TelegramWebhookResponse(response_text=None)

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}", exc_info=True)
        # Don't raise HTTPException - we don't want to break the bot
        # Just return empty response
        return TelegramWebhookResponse(response_text=None)
