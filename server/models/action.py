"""Action and tool call data models"""
from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID, uuid4


class ToolCall(BaseModel):
    """Tool call model"""
    action_id: str = ""
    tool_name: str
    description: str
    parameters: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    success: bool = False
    error: Optional[str] = None
    execution_time_ms: int = 0

    def __init__(self, **data):
        if 'action_id' not in data or not data['action_id']:
            data['action_id'] = str(uuid4())
        super().__init__(**data)


class ActionPlan(BaseModel):
    """Action plan with tools to execute"""
    conversation_id: Optional[UUID] = None
    tools: list[ToolCall]
    reasoning: str = ""
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
