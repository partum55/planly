"""API request schemas"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from uuid import UUID


# Auth schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class GoogleOAuthCallbackRequest(BaseModel):
    code: str  # Authorization code from Google OAuth


class LinkTelegramRequest(BaseModel):
    email: EmailStr  # Added per AGENT_1_TASKS spec
    telegram_id: int
    telegram_username: Optional[str] = None


# Agent schemas
class MessageInput(BaseModel):
    username: str
    text: str
    timestamp: str  # ISO8601


class ScreenshotMetadata(BaseModel):
    window_title: Optional[str] = None
    app_name: Optional[str] = None
    ocr_confidence: Optional[float] = None
    raw_text: Optional[str] = None  # Full OCR dump for validation


class ConversationContext(BaseModel):
    messages: List[MessageInput]
    screenshot_metadata: Optional[ScreenshotMetadata] = None


class AgentProcessRequest(BaseModel):
    """Request format matching AGENT_1_TASKS spec"""
    user_prompt: str  # What the user typed (required per spec)
    conversation_id: Optional[str] = None  # Changed to str to match spec
    source: str = "desktop_screenshot"  # 'desktop_screenshot' or 'telegram'
    context: ConversationContext


class ConfirmActionsRequest(BaseModel):
    conversation_id: str  # Changed to str to match AGENT_1_TASKS spec
    action_ids: List[str]


# Telegram webhook schema
class TelegramWebhookRequest(BaseModel):
    group_id: int
    group_title: Optional[str] = None
    message_id: int
    user_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    text: str
    timestamp: str
    is_bot_mention: bool = False
