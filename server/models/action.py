"""Action and tool call data models"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from uuid import UUID, uuid4


def _new_action_id() -> str:
    return str(uuid4())


class ToolCall(BaseModel):
    """Tool call model"""
    action_id: str = Field(default_factory=_new_action_id)
    tool_name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    success: bool = False
    error: Optional[str] = None
    execution_time_ms: int = 0


class ActionPlan(BaseModel):
    """Action plan with tools to execute"""
    conversation_id: Optional[UUID] = None
    tools: list[ToolCall]
    reasoning: str = ""
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
