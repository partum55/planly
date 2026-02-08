"""API response schemas"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID


class TokenResponse(BaseModel):
    user_id: UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    telegram_id: Optional[int]
    telegram_username: Optional[str]


class ProposedAction(BaseModel):
    action_id: str
    tool: str
    description: str
    parameters: Dict[str, Any]


class AgentProcessResponse(BaseModel):
    conversation_id: UUID
    intent: Optional[Dict[str, Any]]
    proposed_actions: List[ProposedAction]
    requires_clarification: bool
    clarification_question: Optional[str] = None


class ActionResult(BaseModel):
    action_id: str
    tool: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ConfirmActionsResponse(BaseModel):
    success: bool
    results: List[ActionResult]
    formatted_response: str


class TelegramWebhookResponse(BaseModel):
    response_text: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
