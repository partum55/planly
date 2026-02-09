"""Agent API routes — main endpoints for processing conversations."""
from asyncio import to_thread
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, status, Header
from uuid import UUID
from typing import Optional
import json
import hashlib
import logging

from api.schemas.request_schemas import AgentProcessRequest, ConfirmActionsRequest
from api.schemas.response_schemas import (
    AgentProcessResponse,
    ConfirmActionsResponse,
    ProposedAction,
    ActionResult,
    TextBlock,
    ActionCardsBlock,
    ErrorBlock,
)
from api.middleware.auth_middleware import get_current_user
from database.client import get_supabase
from database.repositories.conversation_repo import ConversationRepository
from models.action import ActionPlan, ToolCall
from core.dependencies import get_agent, get_tool_registry

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers: DB-backed action plan cache (replaces module-level dict)
# ---------------------------------------------------------------------------

async def _cache_action_plan(
    conversation_id: str,
    intent: Optional[dict],
    tools: list,
    idempotency_key: Optional[str] = None,
) -> None:
    """Store action plan in the database so it survives multi-worker / restarts."""
    supabase = get_supabase()
    data = {
        "conversation_id": conversation_id,
        "intent_data": intent or {},
        "tool_calls": tools,
        "idempotency_key": idempotency_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc).isoformat(),  # TTL handled on read
    }
    # Upsert — if the same conversation already has a cached plan, overwrite it
    await to_thread(
        lambda: supabase.table("action_plan_cache")
        .upsert(data, on_conflict="conversation_id")
        .execute()
    )


async def _get_cached_plan(conversation_id: str) -> Optional[dict]:
    """Retrieve a cached action plan.  Returns None if missing or expired (>15 min)."""
    supabase = get_supabase()
    resp = await to_thread(
        lambda: supabase.table("action_plan_cache")
        .select("*")
        .eq("conversation_id", conversation_id)
        .execute()
    )
    if not resp.data:
        return None

    row = resp.data[0]
    # TTL check — 15 minutes
    created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - created > timedelta(minutes=15):
        # Expired — clean up
        await to_thread(
            lambda: supabase.table("action_plan_cache")
            .delete()
            .eq("conversation_id", conversation_id)
            .execute()
        )
        return None
    return row


async def _delete_cached_plan(conversation_id: str) -> None:
    supabase = get_supabase()
    await to_thread(
        lambda: supabase.table("action_plan_cache")
        .delete()
        .eq("conversation_id", conversation_id)
        .execute()
    )


def _compute_idempotency_key(request: AgentProcessRequest) -> str:
    """Deterministic hash of the request payload for idempotency."""
    raw = json.dumps(
        {
            "prompt": request.user_prompt,
            "messages": [m.dict() for m in request.context.messages],
            "source": request.source,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Tool discovery endpoint
# ---------------------------------------------------------------------------

@router.get("/tools")
async def list_tools(current_user: dict = Depends(get_current_user)):
    """
    List all available tools with their JSON Schema definitions.

    This allows agents to discover capabilities at runtime.
    """
    registry = get_tool_registry()
    return {
        "tools": registry.get_json_schemas(),
    }


# ---------------------------------------------------------------------------
# Process conversation (O → R → P)
# ---------------------------------------------------------------------------

@router.post("/process", response_model=AgentProcessResponse)
async def process_conversation(
    request: AgentProcessRequest,
    current_user: dict = Depends(get_current_user),
    x_idempotency_key: Optional[str] = Header(None),
):
    """
    Process conversation and return proposed actions.

    Supports idempotency via the ``X-Idempotency-Key`` header — if the same
    key is sent again within the cache TTL, the cached result is returned
    without re-running the LLM pipeline.
    """
    try:
        agent = get_agent()
        supabase = get_supabase()
        conversation_repo = ConversationRepository(supabase)

        # Idempotency check
        idem_key = x_idempotency_key or _compute_idempotency_key(request)

        # Get or create conversation
        if request.conversation_id:
            conversation = await conversation_repo.get_conversation_by_id(
                UUID(request.conversation_id)
            )
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            # Ownership check: only the owner may access this conversation
            if conversation.get("user_id") and conversation["user_id"] != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this conversation",
                )
            conversation_id = UUID(conversation["id"])
        else:
            conversation = await conversation_repo.get_or_create_conversation(
                conversation_type=request.source,
                user_id=UUID(current_user["id"]),
            )
            conversation_id = UUID(conversation["id"])

        # Check for cached plan with same idempotency key
        cached = await _get_cached_plan(str(conversation_id))
        if cached and cached.get("idempotency_key") == idem_key:
            logger.info("Returning cached action plan (idempotent)")
            return _build_response(
                str(conversation_id),
                {
                    "status": "ok",
                    "proposed_actions": cached["tool_calls"],
                    "requires_clarification": False,
                    "clarification_question": None,
                },
            )

        # Store messages
        for msg in request.context.messages:
            await conversation_repo.insert_message(
                conversation_id,
                {
                    "text": msg.text,
                    "username": msg.username,
                    "timestamp": msg.timestamp,
                    "source": request.source,
                    "is_bot_mention": False,
                },
            )

        # Process conversation (O→R→P)
        result = await agent.process_conversation(
            conversation_id=conversation_id,
            user_id=UUID(current_user["id"]),
            trigger_source=request.source,
        )

        # Cache action plan for later execution
        if result.get("proposed_actions"):
            await _cache_action_plan(
                conversation_id=str(conversation_id),
                intent=result.get("intent"),
                tools=result["proposed_actions"],
                idempotency_key=idem_key,
            )

        return _build_response(str(conversation_id), result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing conversation: {e}", exc_info=True)
        cid = str(conversation_id) if "conversation_id" in dir() else "00000000-0000-0000-0000-000000000000"
        return AgentProcessResponse(
            conversation_id=cid,
            blocks=[
                ErrorBlock(
                    type="error",
                    message="An internal error occurred. Please try again later.",
                    error_code="internal_error",
                    retryable=True,
                )
            ],
        )


def _build_response(conversation_id: str, result: dict) -> AgentProcessResponse:
    """Translate internal result dict into the block-based API response."""
    blocks = []

    status = result.get("status", "ok")

    if status == "error":
        blocks.append(
            ErrorBlock(
                type="error",
                message="Something went wrong processing your request. Please try again.",
                error_code=result.get("error_code"),
                retryable=result.get("error_retryable", False),
            )
        )
    elif result.get("requires_clarification"):
        blocks.append(
            TextBlock(
                type="text",
                content=result.get(
                    "clarification_question", "Could you provide more details?"
                ),
            )
        )
    elif result.get("proposed_actions"):
        blocks.append(
            TextBlock(
                type="text",
                content="I see a plan taking shape. Let me help organize that.",
            )
        )
        blocks.append(
            ActionCardsBlock(
                type="action_cards",
                actions=[ProposedAction(**a) for a in result["proposed_actions"]],
            )
        )
    else:
        blocks.append(
            TextBlock(
                type="text",
                content="I couldn't identify any actionable plans from the conversation. Could you provide more details?",
            )
        )

    return AgentProcessResponse(conversation_id=conversation_id, blocks=blocks)


# ---------------------------------------------------------------------------
# Confirm & execute actions (A → R)
# ---------------------------------------------------------------------------

@router.post("/confirm-actions", response_model=ConfirmActionsResponse)
async def confirm_actions(
    request: ConfirmActionsRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Execute confirmed actions.

    Retrieves the DB-cached action plan, filters to selected action_ids,
    executes, and returns results.
    """
    try:
        agent = get_agent()

        # Get cached plan from DB
        plan_data = await _get_cached_plan(str(request.conversation_id))
        if not plan_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action plan not found or expired. Please process the conversation first.",
            )

        # Ownership check: verify the conversation belongs to this user
        supabase = get_supabase()
        conversation_repo = ConversationRepository(supabase)
        conversation = await conversation_repo.get_conversation_by_id(
            UUID(request.conversation_id)
        )
        if conversation and conversation.get("user_id") and conversation["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this conversation",
            )

        tool_calls = [
            ToolCall(**tool_data)
            for tool_data in plan_data["tool_calls"]
            if tool_data["action_id"] in request.action_ids
        ]

        action_plan = ActionPlan(tools=tool_calls)

        # Execute actions (A→R), passing intent explicitly
        result = await agent.execute_actions(
            conversation_id=UUID(request.conversation_id),
            user_id=UUID(current_user["id"]),
            action_ids=request.action_ids,
            action_plan=action_plan,
            intent=plan_data.get("intent_data"),
        )

        # Clear cache after successful execution
        await _delete_cached_plan(str(request.conversation_id))

        return ConfirmActionsResponse(
            success=all(r.get("success") for r in result.get("results", [])),
            results=[ActionResult(**r) for r in result.get("results", [])],
            formatted_response=result.get("formatted_response", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming actions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute actions. Please try again.",
        )
