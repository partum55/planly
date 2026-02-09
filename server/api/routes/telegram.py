"""Telegram webhook API route with secret-token validation."""
from fastapi import APIRouter, HTTPException, Header, status
from uuid import UUID
from typing import Optional
import logging

from api.schemas.request_schemas import TelegramWebhookRequest
from api.schemas.response_schemas import TelegramWebhookResponse
from database.client import get_supabase
from database.repositories.conversation_repo import ConversationRepository
from config.settings import settings
from core.dependencies import get_agent

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_telegram_secret(secret: Optional[str]) -> None:
    """
    Validate the X-Telegram-Bot-Api-Secret-Token header.

    Telegram sends this header on every webhook request if a secret_token
    was provided when calling setWebhook.  When TELEGRAM_WEBHOOK_SECRET is
    configured, validation is enforced to prevent prompt injection via
    forged webhook payloads.  When not configured, the webhook endpoint
    is disabled (the bot should use polling instead).
    """
    expected = settings.TELEGRAM_WEBHOOK_SECRET
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook endpoint disabled — TELEGRAM_WEBHOOK_SECRET not configured. "
                   "Use polling mode or set TELEGRAM_WEBHOOK_SECRET in .env.",
        )
    if secret != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret",
        )


@router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    request: TelegramWebhookRequest,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """
    Receive messages from Telegram bot client.

    1. Validates the webhook secret header.
    2. Stores message in database.
    3. If bot is mentioned: runs full ORPLAR loop and returns response.
    4. Otherwise: stores message and returns None.
    """
    _validate_telegram_secret(x_telegram_bot_api_secret_token)

    try:
        supabase = get_supabase()
        conversation_repo = ConversationRepository(supabase)

        # Get or create conversation for this Telegram group
        conversation = await conversation_repo.get_or_create_conversation(
            conversation_type="telegram_group",
            telegram_group_id=request.group_id,
            telegram_group_title=request.group_title,
        )
        conversation_id = UUID(conversation["id"])

        # Store message
        message_data = {
            "message_id": request.message_id,
            "user_id": request.user_id,
            "username": request.username,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "text": request.text,
            "timestamp": request.timestamp,
            "source": "telegram",
            "is_bot_mention": request.is_bot_mention,
        }

        await conversation_repo.insert_message(conversation_id, message_data)

        # If bot is mentioned, process and respond
        if request.is_bot_mention:
            logger.info(f"Bot mentioned in group {request.group_id}, processing...")

            agent = get_agent()

            response_text = await agent.process_mention(
                conversation_id=conversation_id,
                user_id=None,  # Telegram users not yet mapped to accounts
            )

            logger.info(f"Response generated for group {request.group_id}")
            return TelegramWebhookResponse(response_text=response_text)

        # Not mentioned — just acknowledge
        return TelegramWebhookResponse(response_text=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}", exc_info=True)
        # Don't raise — we don't want to break the bot
        return TelegramWebhookResponse(response_text=None)
