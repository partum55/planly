"""Intent data models"""
from pydantic import BaseModel
from typing import Optional, Any


class Intent(BaseModel):
    """Extracted intent from conversation"""
    activity_type: str  # restaurant, cinema, meeting, other
    participants: list[str] = []  # Usernames who agreed
    datetime: Optional[Any] = None  # str from LLM, converted to datetime by reasoning engine
    location: Optional[str] = None
    requirements: dict[str, Any] = {}  # cuisine, price_range, etc.
    confidence: float = 0.0
    missing_fields: list[str] = []
    clarification_needed: Optional[str] = None
    raw_context: Optional[str] = None
