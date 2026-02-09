"""API response schemas"""
from pydantic import BaseModel, Field
from typing import Annotated, Optional, List, Dict, Any, Union, Literal
from uuid import UUID


class TokenResponse(BaseModel):
    user_id: str  # Changed to str to match AGENT_1_TASKS spec
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    telegram_id: Optional[int]
    telegram_username: Optional[str]


class ProposedAction(BaseModel):
    action_id: str
    tool_name: str
    description: str
    parameters: Dict[str, Any]


# Block types for agent response (AGENT_1_TASKS spec)
class TextBlock(BaseModel):
    type: Literal["text"]
    content: str


class ActionCardsBlock(BaseModel):
    type: Literal["action_cards"]
    actions: List[ProposedAction]


class ErrorBlock(BaseModel):
    type: Literal["error"]
    message: str
    error_code: Optional[str] = None
    retryable: bool = False


# CalendarPickerBlock and TimePickerBlock are planned but not yet emitted by any
# code path.  They are excluded from ResponseBlock until the backend actually
# produces them, so that agents don't build UI for capabilities that don't exist.

ResponseBlock = Annotated[
    Union[TextBlock, ActionCardsBlock, ErrorBlock],
    Field(discriminator='type'),
]


class AgentProcessResponse(BaseModel):
    """Response format matching AGENT_1_TASKS spec"""
    conversation_id: str
    blocks: List[ResponseBlock]


class ActionResult(BaseModel):
    action_id: str
    tool_name: str
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
