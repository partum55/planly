"""API request schemas"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Literal, Optional, List, Dict, Any
from uuid import UUID
import re


# Auth schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class GoogleOAuthCallbackRequest(BaseModel):
    code: str  # Authorization code from Google OAuth


class LinkTelegramRequest(BaseModel):
    """Redeem a link code to bind Telegram to a Planly account.

    The user generates a code from an authenticated context (desktop app
    or web), then types /link <code> in Telegram.  The bot posts this
    request to complete the binding.
    """
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^[A-Z0-9]{6}$")
    telegram_id: int
    telegram_username: Optional[str] = None


# Agent schemas
class MessageInput(BaseModel):
    username: str = Field(..., max_length=256)
    text: str = Field(..., max_length=10000)
    timestamp: str  # ISO8601


class ScreenshotMetadata(BaseModel):
    window_title: Optional[str] = None
    app_name: Optional[str] = None
    ocr_confidence: Optional[float] = None
    raw_text: Optional[str] = None  # Full OCR dump for validation


class ConversationContextInput(BaseModel):
    """API-layer conversation context (distinct from models.message.ConversationContext)."""
    messages: List[MessageInput]
    screenshot_metadata: Optional[ScreenshotMetadata] = None


class AgentProcessRequest(BaseModel):
    """Request format matching AGENT_1_TASKS spec"""
    user_prompt: str = Field(..., max_length=5000)
    conversation_id: Optional[str] = None

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                UUID(v)
            except ValueError:
                raise ValueError("conversation_id must be a valid UUID")
        return v

    source: Literal["desktop_screenshot", "telegram"] = "desktop_screenshot"
    context: ConversationContextInput


class ConfirmActionsRequest(BaseModel):
    conversation_id: str
    action_ids: List[str] = Field(..., min_length=1)

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v: str) -> str:
        try:
            UUID(v)
        except ValueError:
            raise ValueError("conversation_id must be a valid UUID")
        return v


# Telegram webhook schema
class TelegramWebhookRequest(BaseModel):
    group_id: int
    group_title: Optional[str] = Field(None, max_length=256)
    message_id: int
    user_id: int
    username: Optional[str] = Field(None, max_length=256)
    first_name: str = Field(..., max_length=256)
    last_name: Optional[str] = Field(None, max_length=256)
    text: str = Field(..., max_length=10000)
    timestamp: str
    is_bot_mention: bool = False
