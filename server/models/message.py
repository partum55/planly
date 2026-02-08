"""Message data models"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TelegramUser(BaseModel):
    """Telegram user info"""
    user_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None


class Message(BaseModel):
    """Message model"""
    message_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    text: str
    timestamp: datetime
    source: str = "telegram"  # 'telegram' or 'desktop_ocr'
    is_bot_mention: bool = False


class ConversationContext(BaseModel):
    """Conversation context with parsed information"""
    messages: list[Message]
    participants: dict[int, TelegramUser] = {}
    consent_signals: dict[int, str] = {}  # user_id -> 'accepted' | 'declined'
    time_references: list[str] = []
    mention_message: Optional[str] = None
