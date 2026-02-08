"""Agent API routes - main endpoints for processing conversations"""
from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID
from datetime import datetime
import logging

from api.schemas.request_schemas import AgentProcessRequest, ConfirmActionsRequest
from api.schemas.response_schemas import (
    AgentProcessResponse,
    ConfirmActionsResponse,
    ProposedAction,
    ActionResult
)
from api.middleware.auth_middleware import get_current_user
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

# Temporary storage for action plans (in production, use Redis or database)
_action_plans_cache = {}


def get_agent() -> TelegramAgent:
    """Initialize and return agent with dependencies"""
    supabase = get_supabase()
    conversation_repo = ConversationRepository(supabase)
    event_repo = EventRepository(supabase)

    # Initialize Ollama
    ollama_client = OllamaClient()

    # Initialize tool registry
    tool_registry = ToolRegistry()
    calendar_client = GoogleCalendarClient()
    tool_registry.register(CalendarTool(calendar_client))
    tool_registry.register(RestaurantSearchTool())
    tool_registry.register(CinemaSearchTool())

    # Initialize core components
    context_manager = ContextManager(conversation_repo)
    reasoning_engine = ReasoningEngine(ollama_client, tool_registry)

    # Create agent
    agent = TelegramAgent(
        context_manager=context_manager,
        reasoning_engine=reasoning_engine,
        tool_registry=tool_registry,
        event_repo=event_repo
    )

    return agent


@router.post("/process", response_model=AgentProcessResponse)
async def process_conversation(
    request: AgentProcessRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process conversation and return proposed actions

    This endpoint:
    1. Stores messages in database
    2. Runs Observe→Reason→Plan phases
    3. Returns proposed actions for user confirmation
    """
    try:
        agent = get_agent()
        supabase = get_supabase()
        conversation_repo = ConversationRepository(supabase)

        # Get or create conversation
        if request.conversation_id:
            conversation = await conversation_repo.get_conversation_by_id(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            conversation_id = UUID(conversation['id'])
        else:
            # Create new conversation
            conversation = await conversation_repo.get_or_create_conversation(
                conversation_type=request.source,
                user_id=UUID(current_user['id'])
            )
            conversation_id = UUID(conversation['id'])

        # Store messages
        for msg in request.context.messages:
            await conversation_repo.insert_message(conversation_id, {
                'text': msg.text,
                'username': msg.username,
                'timestamp': msg.timestamp,
                'source': request.source,
                'is_bot_mention': False
            })

        # Process conversation (O→R→P)
        result = await agent.process_conversation(
            conversation_id=conversation_id,
            user_id=UUID(current_user['id']),
            trigger_source=request.source
        )

        # Cache action plan for later execution
        if result.get('proposed_actions'):
            _action_plans_cache[str(conversation_id)] = {
                'intent': result['intent'],
                'tools': result['proposed_actions']
            }

        return AgentProcessResponse(
            conversation_id=conversation_id,
            intent=result.get('intent'),
            proposed_actions=[
                ProposedAction(**action)
                for action in result.get('proposed_actions', [])
            ],
            requires_clarification=result.get('requires_clarification', False),
            clarification_question=result.get('clarification_question')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process conversation: {str(e)}"
        )


@router.post("/confirm-actions", response_model=ConfirmActionsResponse)
async def confirm_actions(
    request: ConfirmActionsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Execute confirmed actions

    This endpoint:
    1. Retrieves the cached action plan
    2. Executes selected tools (Act phase)
    3. Composes and returns response (Respond phase)
    """
    try:
        agent = get_agent()

        # Get cached action plan
        plan_data = _action_plans_cache.get(str(request.conversation_id))
        if not plan_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action plan not found. Please process the conversation first."
            )

        # TODO: Convert plan_data to ActionPlan properly
        # For now, execute tools directly
        from models.action import ActionPlan, ToolCall

        tool_calls = [
            ToolCall(**tool_data)
            for tool_data in plan_data['tools']
            if tool_data['action_id'] in request.action_ids
        ]

        action_plan = ActionPlan(tools=tool_calls)

        # Execute actions (A→R)
        result = await agent.execute_actions(
            conversation_id=request.conversation_id,
            user_id=UUID(current_user['id']),
            action_ids=request.action_ids,
            action_plan=action_plan
        )

        # Clear cache
        _action_plans_cache.pop(str(request.conversation_id), None)

        return ConfirmActionsResponse(
            success=all(r.get('success') for r in result.get('results', [])),
            results=[
                ActionResult(**r)
                for r in result.get('results', [])
            ],
            formatted_response=result.get('formatted_response', '')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming actions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute actions: {str(e)}"
        )
