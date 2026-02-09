"""Tests for PlanlyAgent — the core ORPLAR loop.

Covers:
- process_conversation: O→R→P flow (no side-effects)
- execute_actions: A→R flow
- process_mention: full Telegram flow with destructive-tool hold-back
- Error handling and retry classification
- Backward-compatible TelegramAgent alias
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from core.agent import PlanlyAgent, TelegramAgent, AgentError, _is_retryable, _classify_error
from models.intent import Intent
from models.action import ActionPlan, ToolCall
from models.message import ConversationContext, Message
from tools.base import ToolSchema, ToolParameter, ToolMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(messages=None, participants=None, consent=None):
    """Build a minimal ConversationContext for testing."""
    if messages is None:
        messages = [
            Message(
                message_id=1,
                user_id=42,
                username="alice",
                first_name="Alice",
                text="Let's go to dinner tomorrow at 7pm",
                timestamp=datetime.now(timezone.utc),
                source="telegram",
                is_bot_mention=True,
            ),
            Message(
                message_id=2,
                user_id=43,
                username="bob",
                first_name="Bob",
                text="sure, count me in!",
                timestamp=datetime.now(timezone.utc),
                source="telegram",
                is_bot_mention=False,
            ),
        ]
    return ConversationContext(
        messages=messages,
        participants=participants or {"42": {"username": "alice"}, "43": {"username": "bob"}},
        consent_signals=consent or {"43": "accepted"},
    )


def _make_intent(**overrides):
    """Build a minimal Intent for testing."""
    defaults = dict(
        activity_type="restaurant",
        participants=["alice", "bob"],
        datetime=None,
        location="downtown",
        confidence=0.9,
    )
    defaults.update(overrides)
    return Intent(**defaults)


def _make_action_plan(tool_names=None):
    """Build a minimal ActionPlan for testing."""
    if tool_names is None:
        tool_names = ["restaurant_search", "calendar_create_event"]
    tools = [
        ToolCall(
            tool_name=name,
            description=f"Execute {name}",
            parameters={"location": "downtown"},
        )
        for name in tool_names
    ]
    return ActionPlan(tools=tools, reasoning="Test plan")


def _make_tool_mock(name, *, destructive=False, result=None):
    """Create a mock tool that returns a given result."""
    tool = MagicMock()
    tool.schema = ToolSchema(
        name=name,
        description=f"Mock {name}",
        parameters=[],
        metadata=ToolMetadata(destructive_hint=destructive, read_only_hint=not destructive),
    )
    tool.execute = AsyncMock(return_value=result or {"success": True, "data": "ok"})
    return tool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def context_manager():
    cm = MagicMock()
    cm.get_context = AsyncMock(return_value=_make_context())
    return cm


@pytest.fixture
def reasoning_engine():
    re = MagicMock()
    re.extract_intent = AsyncMock(return_value=_make_intent())
    re.create_action_plan = AsyncMock(return_value=_make_action_plan())
    re.compose_response = AsyncMock(return_value="All done!")
    return re


@pytest.fixture
def tool_registry():
    registry = MagicMock()

    search_tool = _make_tool_mock("restaurant_search", destructive=False)
    calendar_tool = _make_tool_mock("calendar_create_event", destructive=True)

    def _get(name):
        return {"restaurant_search": search_tool, "calendar_create_event": calendar_tool}.get(name)

    registry.get_tool = MagicMock(side_effect=_get)
    registry._tools_map = {"restaurant_search": search_tool, "calendar_create_event": calendar_tool}
    return registry


@pytest.fixture
def event_repo():
    repo = MagicMock()
    repo.log_action = AsyncMock()
    return repo


@pytest.fixture
def agent(context_manager, reasoning_engine, tool_registry, event_repo):
    return PlanlyAgent(
        context_manager=context_manager,
        reasoning_engine=reasoning_engine,
        tool_registry=tool_registry,
        event_repo=event_repo,
    )


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    def test_telegram_agent_alias(self):
        """TelegramAgent should be the same class as PlanlyAgent."""
        assert TelegramAgent is PlanlyAgent


# ---------------------------------------------------------------------------
# AgentError
# ---------------------------------------------------------------------------

class TestAgentError:
    def test_retryable_flag(self):
        err = AgentError("boom", retryable=True)
        assert err.retryable is True
        assert str(err) == "boom"

    def test_default_not_retryable(self):
        err = AgentError("permanent")
        assert err.retryable is False


# ---------------------------------------------------------------------------
# process_conversation (O→R→P)
# ---------------------------------------------------------------------------

class TestProcessConversation:
    @pytest.mark.asyncio
    async def test_happy_path(self, agent, reasoning_engine):
        """Normal flow returns proposed actions without executing them."""
        result = await agent.process_conversation(
            conversation_id=uuid4(),
            user_id=uuid4(),
            trigger_source="desktop_keybind",
        )
        assert result["status"] == "ok"
        assert result["requires_clarification"] is False
        assert len(result["proposed_actions"]) == 2
        # Tools should NOT have been executed
        reasoning_engine.compose_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_messages_returns_clarification(self, agent, context_manager):
        """When there are no messages, agent asks for clarification."""
        context_manager.get_context.return_value = _make_context(messages=[])
        result = await agent.process_conversation(conversation_id=uuid4())
        assert result["status"] == "needs_clarification"
        assert result["requires_clarification"] is True
        assert "messages" in result["clarification_question"].lower()

    @pytest.mark.asyncio
    async def test_clarification_needed(self, agent, reasoning_engine):
        """When intent needs clarification, return it without planning."""
        reasoning_engine.extract_intent.return_value = _make_intent(
            clarification_needed="What time works for everyone?"
        )
        result = await agent.process_conversation(conversation_id=uuid4())
        assert result["status"] == "needs_clarification"
        assert "time" in result["clarification_question"].lower()
        # create_action_plan should NOT have been called
        reasoning_engine.create_action_plan.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_error(self, agent, reasoning_engine):
        """Timeout during intent extraction is classified as retryable error."""
        reasoning_engine.extract_intent.side_effect = TimeoutError("LLM timed out")
        result = await agent.process_conversation(conversation_id=uuid4())
        assert result["status"] == "error"
        assert result["error_retryable"] is True

    @pytest.mark.asyncio
    async def test_connection_error_returns_error(self, agent, reasoning_engine):
        """Connection error is classified as retryable."""
        reasoning_engine.extract_intent.side_effect = ConnectionError("refused")
        result = await agent.process_conversation(conversation_id=uuid4())
        assert result["status"] == "error"
        assert result["error_retryable"] is True

    @pytest.mark.asyncio
    async def test_generic_error_non_retryable(self, agent, reasoning_engine):
        """Generic exceptions are classified as non-retryable."""
        reasoning_engine.extract_intent.side_effect = ValueError("bad data")
        result = await agent.process_conversation(conversation_id=uuid4())
        assert result["status"] == "error"
        assert result["error_retryable"] is False

    @pytest.mark.asyncio
    async def test_proposed_actions_have_action_ids(self, agent):
        """Each proposed action must have a unique action_id."""
        result = await agent.process_conversation(conversation_id=uuid4())
        ids = [a["action_id"] for a in result["proposed_actions"]]
        assert len(ids) == len(set(ids))  # all unique
        assert all(len(aid) > 0 for aid in ids)


# ---------------------------------------------------------------------------
# execute_actions (A→R)
# ---------------------------------------------------------------------------

class TestExecuteActions:
    @pytest.mark.asyncio
    async def test_execute_confirmed_actions(self, agent, tool_registry):
        """Only confirmed action_ids are executed."""
        plan = _make_action_plan(["restaurant_search", "calendar_create_event"])
        confirmed_ids = [plan.tools[0].action_id]  # only the first one

        result = await agent.execute_actions(
            conversation_id=uuid4(),
            user_id=uuid4(),
            action_ids=confirmed_ids,
            action_plan=plan,
            intent={"activity_type": "restaurant"},
        )

        assert "results" in result
        assert "formatted_response" in result
        # Only 1 tool should have been executed
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_execute_all_actions(self, agent, tool_registry):
        """When all action_ids are confirmed, all tools execute."""
        plan = _make_action_plan(["restaurant_search"])
        all_ids = [t.action_id for t in plan.tools]

        result = await agent.execute_actions(
            conversation_id=uuid4(),
            user_id=uuid4(),
            action_ids=all_ids,
            action_plan=plan,
        )

        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_failure(self, agent, tool_registry):
        """If a tool is not found in registry, the result is a failure."""
        plan = _make_action_plan(["nonexistent_tool"])
        all_ids = [t.action_id for t in plan.tools]

        tool_registry.get_tool.return_value = None

        result = await agent.execute_actions(
            conversation_id=uuid4(),
            user_id=uuid4(),
            action_ids=all_ids,
            action_plan=plan,
        )

        assert result["results"][0]["success"] is False
        assert "not found" in result["results"][0]["error"]

    @pytest.mark.asyncio
    async def test_tool_exception_isolated(self, agent, tool_registry):
        """Exception in one tool doesn't crash the whole execution."""
        failing_tool = _make_tool_mock("restaurant_search")
        failing_tool.execute.side_effect = RuntimeError("API down")
        tool_registry.get_tool.side_effect = lambda name: failing_tool

        plan = _make_action_plan(["restaurant_search"])
        all_ids = [t.action_id for t in plan.tools]

        result = await agent.execute_actions(
            conversation_id=uuid4(),
            user_id=uuid4(),
            action_ids=all_ids,
            action_plan=plan,
        )

        assert result["results"][0]["success"] is False
        assert result["formatted_response"]  # still got a response


# ---------------------------------------------------------------------------
# process_mention (full Telegram ORPLAR)
# ---------------------------------------------------------------------------

class TestProcessMention:
    @pytest.mark.asyncio
    async def test_read_only_tools_execute_immediately(self, agent, tool_registry):
        """Read-only tools should execute without confirmation."""
        agent.reasoning_engine.create_action_plan.return_value = _make_action_plan(
            ["restaurant_search"]
        )
        response = await agent.process_mention(conversation_id=uuid4())
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_destructive_tools_held_back(self, agent, tool_registry):
        """Destructive tools should not auto-execute in Telegram flow."""
        agent.reasoning_engine.create_action_plan.return_value = _make_action_plan(
            ["calendar_create_event"]
        )
        response = await agent.process_mention(conversation_id=uuid4())
        # The compose_response should be called with a "pending_confirmation" result
        call_args = agent.reasoning_engine.compose_response.call_args
        results = call_args.kwargs.get("results") or call_args[1].get("results", [])
        pending = [r for r in results if r.get("action_id") == "pending_confirmation"]
        assert len(pending) == 1
        assert "confirmation" in pending[0]["result"]["note"].lower()

    @pytest.mark.asyncio
    async def test_clarification_returns_question(self, agent, reasoning_engine):
        """When intent needs clarification, return the question directly."""
        reasoning_engine.extract_intent.return_value = _make_intent(
            clarification_needed="When do you want to go?"
        )
        response = await agent.process_mention(conversation_id=uuid4())
        assert response == "When do you want to go?"

    @pytest.mark.asyncio
    async def test_error_returns_user_friendly_message(self, agent, reasoning_engine):
        """Unhandled exception returns a generic user-friendly string."""
        reasoning_engine.extract_intent.side_effect = Exception("unexpected")
        response = await agent.process_mention(conversation_id=uuid4())
        assert "error" in response.lower()
        assert "try again" in response.lower()


# ---------------------------------------------------------------------------
# Error classification helpers
# ---------------------------------------------------------------------------

class TestErrorClassification:
    def test_timeout_is_retryable(self):
        assert _is_retryable(TimeoutError("slow")) is True

    def test_connection_is_retryable(self):
        assert _is_retryable(ConnectionError("refused")) is True

    def test_os_error_is_retryable(self):
        assert _is_retryable(OSError("network unreachable")) is True

    def test_value_error_not_retryable(self):
        assert _is_retryable(ValueError("bad data")) is False

    def test_classify_timeout(self):
        assert _classify_error(TimeoutError("slow")) == "llm_timeout"

    def test_classify_connection(self):
        assert _classify_error(ConnectionError("refused")) == "connection_error"

    def test_classify_json_parse(self):
        assert _classify_error(ValueError("invalid json at pos 0")) == "parse_error"

    def test_classify_generic(self):
        assert _classify_error(RuntimeError("something weird")) == "internal_error"

    def test_classify_timeout_in_message(self):
        """Even non-TimeoutError with 'timeout' in message is classified correctly."""
        assert _classify_error(RuntimeError("request timeout after 30s")) == "llm_timeout"


# ---------------------------------------------------------------------------
# PlanlyAgent construction
# ---------------------------------------------------------------------------

class TestAgentConstruction:
    def test_agent_takes_all_dependencies(self, context_manager, reasoning_engine, tool_registry, event_repo):
        """Agent can be constructed with all required dependencies."""
        agent = PlanlyAgent(
            context_manager=context_manager,
            reasoning_engine=reasoning_engine,
            tool_registry=tool_registry,
            event_repo=event_repo,
        )
        assert agent.context_manager is context_manager
        assert agent.reasoning_engine is reasoning_engine
        assert agent.tool_registry is tool_registry
        assert agent.event_repo is event_repo
