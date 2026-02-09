"""Main Agent — implements ORPLAR loop with structured errors and parallel execution."""
import asyncio
import time
import logging
from uuid import UUID
from typing import Optional

from models.action import ActionPlan
from core.context_manager import ContextManager
from core.reasoning_engine import ReasoningEngine
from database.repositories.event_repo import EventRepository

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Typed agent errors so callers can distinguish transient from permanent failures."""
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class PlanlyAgent:
    """
    Main agent orchestrator implementing:
    Observe → Reason → Plan → Act → Respond (ORPLAR)
    """

    def __init__(
        self,
        context_manager: ContextManager,
        reasoning_engine: ReasoningEngine,
        tool_registry,
        event_repo: EventRepository,
    ):
        self.context_manager = context_manager
        self.reasoning_engine = reasoning_engine
        self.tool_registry = tool_registry
        self.event_repo = event_repo

    async def process_conversation(
        self,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        trigger_source: str = "telegram_mention",
    ) -> dict:
        """
        Main entry point — process conversation and return proposed actions.

        This is the first part of the ORPLAR loop: O→R→P
        Returns proposed actions for user confirmation (desktop app flow).

        Returns:
        {
            'status': 'ok' | 'needs_clarification' | 'error',
            'intent': Intent | None,
            'proposed_actions': [ToolCall],
            'requires_clarification': bool,
            'clarification_question': str | None,
            'error_retryable': bool,          # only when status == 'error'
        }
        """
        start_time = time.time()

        try:
            # 1. OBSERVE: Get conversation context
            logger.info(f"OBSERVE: Getting context for conversation {conversation_id}")
            context = await self.context_manager.get_context(conversation_id)

            if not context.messages:
                logger.warning("No messages in context")
                return {
                    'status': 'needs_clarification',
                    'intent': None,
                    'proposed_actions': [],
                    'requires_clarification': True,
                    'clarification_question': "I don't see any messages. What would you like to do?",
                }

            # 2. REASON: Extract intent from conversation
            logger.info("REASON: Extracting intent from conversation")
            intent = await self.reasoning_engine.extract_intent(context)

            # Check if clarification is needed
            if intent.clarification_needed:
                logger.info(f"Clarification needed: {intent.clarification_needed}")
                return {
                    'status': 'needs_clarification',
                    'intent': intent.dict(),
                    'proposed_actions': [],
                    'requires_clarification': True,
                    'clarification_question': intent.clarification_needed,
                }

            # 3. PLAN: Determine which tools to use
            logger.info("PLAN: Creating action plan")
            action_plan = await self.reasoning_engine.create_action_plan(intent)

            # Log the planning phase
            execution_time = int((time.time() - start_time) * 1000)
            logger.info(f"Planning completed in {execution_time}ms")

            return {
                'status': 'ok',
                'intent': intent.dict(),
                'proposed_actions': [
                    {
                        'action_id': tool.action_id,
                        'tool_name': tool.tool_name,
                        'description': tool.description,
                        'parameters': tool.parameters,
                    }
                    for tool in action_plan.tools
                ],
                'requires_clarification': False,
                'clarification_question': None,
            }

        except Exception as e:
            retryable = _is_retryable(e)
            error_code = _classify_error(e)
            logger.error(
                f"Error in process_conversation (code={error_code}, retryable={retryable}): {e}",
                exc_info=True,
            )
            return {
                'status': 'error',
                'intent': None,
                'proposed_actions': [],
                'requires_clarification': False,
                'clarification_question': None,
                'error_retryable': retryable,
                'error_code': error_code,
            }

    async def execute_actions(
        self,
        conversation_id: UUID,
        user_id: UUID,
        action_ids: list[str],
        action_plan: ActionPlan,
        intent: Optional[dict] = None,
    ) -> dict:
        """
        Execute confirmed actions.

        This is the second part of the ORPLAR loop: A→R

        Args:
            intent: The original intent dict, passed explicitly (not through tool params).

        Returns:
        {
            'results': [{'action_id': ..., 'success': ..., 'result': ...}],
            'formatted_response': str
        }
        """
        start_time = time.time()

        try:
            # Filter tools to only execute confirmed ones
            tools_to_execute = [
                tool for tool in action_plan.tools
                if tool.action_id in action_ids
            ]

            logger.info(f"ACT: Executing {len(tools_to_execute)} tools")

            # 4. ACT: Execute tools (in parallel where safe)
            results = await self._execute_plan(tools_to_execute)

            # 5. RESPOND: Format response
            logger.info("RESPOND: Composing response")
            response = await self.reasoning_engine.compose_response(
                intent=intent,
                results=results,
            )

            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            await self.event_repo.log_action(
                conversation_id=conversation_id,
                user_id=user_id,
                trigger_source="desktop_keybind",
                action_type="execute_tools",
                intent_data=intent if intent else {},
                tool_calls=[tool.dict() for tool in tools_to_execute],
                response_text=response,
                success=all(r['success'] for r in results),
                execution_time_ms=execution_time,
            )

            logger.info(f"Execution completed in {execution_time}ms")

            return {
                'results': results,
                'formatted_response': response,
            }

        except Exception as e:
            logger.error(f"Error executing actions: {e}", exc_info=True)
            return {
                'results': [],
                'formatted_response': "I encountered an error while executing actions. Please try again.",
            }

    async def process_mention(
        self,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> str:
        """
        Complete ORPLAR loop for immediate execution (Telegram bot flow).

        Destructive tools (calendar_create_event, etc.) are NOT executed
        automatically — only read-only tools run immediately. Destructive
        actions are reported back so the user can confirm them via the
        desktop app.

        Returns: response text
        """
        start_time = time.time()

        try:
            # 1. OBSERVE
            logger.info(f"OBSERVE: Getting context for conversation {conversation_id}")
            context = await self.context_manager.get_context(conversation_id)

            # 2. REASON
            logger.info("REASON: Extracting intent")
            intent = await self.reasoning_engine.extract_intent(context)

            if intent.clarification_needed:
                return intent.clarification_needed

            # 3. PLAN
            logger.info("PLAN: Creating action plan")
            action_plan = await self.reasoning_engine.create_action_plan(intent)

            # Separate safe (read-only) tools from destructive ones
            safe_tools = []
            destructive_tools = []
            for tc in action_plan.tools:
                tool = self.tool_registry.get_tool(tc.tool_name)
                if tool and tool.schema.metadata.destructive_hint:
                    destructive_tools.append(tc)
                else:
                    safe_tools.append(tc)

            # 4. ACT — only execute safe/read-only tools immediately
            results = []
            if safe_tools:
                logger.info(f"ACT: Executing {len(safe_tools)} read-only tools")
                results = await self._execute_plan(safe_tools)

            if destructive_tools:
                logger.info(
                    f"HELD BACK {len(destructive_tools)} destructive tool(s) "
                    "pending user confirmation"
                )
                held_names = [tc.tool_name for tc in destructive_tools]
                results.append({
                    'action_id': 'pending_confirmation',
                    'tool_name': ', '.join(held_names),
                    'success': True,
                    'result': {
                        'note': (
                            f"The following actions require confirmation before "
                            f"execution: {', '.join(held_names)}. "
                            f"Please confirm via the desktop app."
                        ),
                    },
                })

            # 5. RESPOND
            logger.info("RESPOND: Composing response")
            response = await self.reasoning_engine.compose_response(
                intent=intent.dict(),
                results=results,
            )

            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            await self.event_repo.log_action(
                conversation_id=conversation_id,
                user_id=user_id,
                trigger_source="telegram_mention",
                action_type="full_orplar",
                intent_data=intent.dict(),
                tool_calls=[tool.dict() for tool in safe_tools],
                response_text=response,
                success=all(r.get('success') for r in results),
                execution_time_ms=execution_time,
            )

            logger.info(f"ORPLAR loop completed in {execution_time}ms")
            return response

        except Exception as e:
            logger.error(f"Error in process_mention: {e}", exc_info=True)
            return "I encountered an error processing your request. Please try again."

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def _execute_plan(self, tools: list) -> list[dict]:
        """Execute tools with bounded concurrency and return results.

        Uses a semaphore to avoid overwhelming external APIs and
        return_exceptions=True so that a failure in one tool does not
        cancel or discard the results of the others.
        """
        if not tools:
            return []

        semaphore = asyncio.Semaphore(5)

        async def _guarded(tc):
            async with semaphore:
                return await self._execute_single_tool(tc)

        tasks = [_guarded(tc) for tc in tools]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[dict] = []
        for i, res in enumerate(raw_results):
            if isinstance(res, Exception):
                tc = tools[i]
                logger.error(f"Tool {tc.tool_name} raised unhandled exception: {res}")
                results.append({
                    'action_id': tc.action_id,
                    'tool_name': tc.tool_name,
                    'success': False,
                    'error': "An internal error occurred while executing this tool.",
                })
            else:
                results.append(res)
        return results

    async def _execute_single_tool(self, tool_call) -> dict:
        """Execute a single tool call with error isolation.

        Does NOT mutate the tool_call object — returns a standalone result dict.
        Validates parameters before execution via the tool's schema.
        """
        tool_start = time.time()

        try:
            tool = self.tool_registry.get_tool(tool_call.tool_name)

            if not tool:
                logger.error(f"Tool not found: {tool_call.tool_name}")
                return {
                    'action_id': tool_call.action_id,
                    'tool_name': tool_call.tool_name,
                    'success': False,
                    'error': f"Tool {tool_call.tool_name} not found",
                }

            # Validate parameters before execution
            await tool.validate_parameters(**tool_call.parameters)

            logger.info(f"Executing tool: {tool_call.tool_name}")
            result = await tool.execute(**tool_call.parameters)

            execution_time_ms = int((time.time() - tool_start) * 1000)
            logger.info(f"Tool {tool_call.tool_name} completed in {execution_time_ms}ms")

            return {
                'action_id': tool_call.action_id,
                'tool_name': tool_call.tool_name,
                'success': result.get('success', False),
                'result': result,
            }

        except ValueError as e:
            logger.error(f"Tool parameter validation failed ({tool_call.tool_name}): {e}")
            return {
                'action_id': tool_call.action_id,
                'tool_name': tool_call.tool_name,
                'success': False,
                'error': f"Invalid parameters for '{tool_call.tool_name}': {e}",
            }
        except Exception as e:
            logger.error(f"Tool execution error ({tool_call.tool_name}): {e}", exc_info=True)
            return {
                'action_id': tool_call.action_id,
                'tool_name': tool_call.tool_name,
                'success': False,
                'error': f"Tool '{tool_call.tool_name}' failed. Please try again.",
            }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def _is_retryable(exc: Exception) -> bool:
    """Classify an exception as transient (retryable) or permanent."""
    if isinstance(exc, _RETRYABLE_ERRORS):
        return True
    msg = str(exc).lower()
    if any(kw in msg for kw in ("timeout", "connection", "unreachable")):
        return True
    # LLM parse failures are often transient (model still loading, incomplete
    # generation, temporary malformed output).
    if any(kw in msg for kw in ("json", "parse", "no valid json")):
        return True
    return False


def _classify_error(exc: Exception) -> str:
    """Return a machine-readable error code for the exception."""
    if isinstance(exc, TimeoutError):
        return "llm_timeout"
    if isinstance(exc, (ConnectionError, OSError)):
        return "connection_error"
    msg = str(exc).lower()
    if "timeout" in msg:
        return "llm_timeout"
    if "connection" in msg or "unreachable" in msg:
        return "connection_error"
    if "json" in msg or "parse" in msg or "no valid json" in msg:
        return "llm_parse_error"
    return "internal_error"

