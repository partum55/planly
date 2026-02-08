"""Main Agent - implements ORPLAR loop"""
import time
import logging
from uuid import UUID
from typing import Optional

from models.action import ActionPlan
from core.context_manager import ContextManager
from core.reasoning_engine import ReasoningEngine
from database.repositories.event_repo import EventRepository

logger = logging.getLogger(__name__)


class TelegramAgent:
    """
    Main agent orchestrator implementing:
    Observe → Reason → Plan → Act → Respond (ORPLAR)
    """

    def __init__(
        self,
        context_manager: ContextManager,
        reasoning_engine: ReasoningEngine,
        tool_registry,
        event_repo: EventRepository
    ):
        self.context_manager = context_manager
        self.reasoning_engine = reasoning_engine
        self.tool_registry = tool_registry
        self.event_repo = event_repo

    async def process_conversation(
        self,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        trigger_source: str = "telegram_mention"
    ) -> dict:
        """
        Main entry point - process conversation and return proposed actions

        This is the first part of the ORPLAR loop: O→R→P
        Returns proposed actions for user confirmation (desktop app flow)

        Returns:
        {
            'intent': Intent,
            'proposed_actions': [ToolCall],
            'requires_clarification': bool,
            'clarification_question': str | None
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
                    'intent': None,
                    'proposed_actions': [],
                    'requires_clarification': True,
                    'clarification_question': "I don't see any messages. What would you like to do?"
                }

            # 2. REASON: Extract intent from conversation
            logger.info("REASON: Extracting intent from conversation")
            intent = await self.reasoning_engine.extract_intent(context)

            # Check if clarification is needed
            if intent.clarification_needed:
                logger.info(f"Clarification needed: {intent.clarification_needed}")
                return {
                    'intent': intent.dict(),
                    'proposed_actions': [],
                    'requires_clarification': True,
                    'clarification_question': intent.clarification_needed
                }

            # 3. PLAN: Determine which tools to use
            logger.info("PLAN: Creating action plan")
            action_plan = await self.reasoning_engine.create_action_plan(intent)

            # Log the planning phase
            execution_time = int((time.time() - start_time) * 1000)
            logger.info(f"Planning completed in {execution_time}ms")

            # Return proposed actions (don't execute yet - desktop app needs confirmation)
            return {
                'intent': intent.dict(),
                'proposed_actions': [
                    {
                        'action_id': tool.action_id,
                        'tool': tool.tool_name,
                        'description': tool.description,
                        'parameters': tool.parameters
                    }
                    for tool in action_plan.tools
                ],
                'requires_clarification': False,
                'clarification_question': None
            }

        except Exception as e:
            logger.error(f"Error in process_conversation: {e}", exc_info=True)
            return {
                'intent': None,
                'proposed_actions': [],
                'requires_clarification': True,
                'clarification_question': "I encountered an error processing your request. Could you try rephrasing?"
            }

    async def execute_actions(
        self,
        conversation_id: UUID,
        user_id: UUID,
        action_ids: list[str],
        action_plan: ActionPlan
    ) -> dict:
        """
        Execute confirmed actions

        This is the second part of the ORPLAR loop: A→R

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

            # 4. ACT: Execute tools
            results = await self._execute_plan(tools_to_execute)

            # 5. RESPOND: Format response
            logger.info("RESPOND: Composing response")
            intent = action_plan.tools[0].parameters.get('intent')  # Hack: pass intent through
            response = await self.reasoning_engine.compose_response(
                intent=intent if intent else None,
                results=results
            )

            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            await self.event_repo.log_action(
                conversation_id=conversation_id,
                user_id=user_id,
                trigger_source="desktop_keybind",
                action_type="execute_tools",
                intent_data=intent.dict() if intent else {},
                tool_calls=[tool.dict() for tool in tools_to_execute],
                response_text=response,
                success=all(r['success'] for r in results),
                execution_time_ms=execution_time
            )

            logger.info(f"Execution completed in {execution_time}ms")

            return {
                'results': results,
                'formatted_response': response
            }

        except Exception as e:
            logger.error(f"Error executing actions: {e}", exc_info=True)
            return {
                'results': [],
                'formatted_response': "I encountered an error while executing actions. Please try again."
            }

    async def process_mention(
        self,
        conversation_id: UUID,
        user_id: Optional[UUID] = None
    ) -> str:
        """
        Complete ORPLAR loop for immediate execution (Telegram bot flow)

        Used when we want to execute immediately without confirmation

        Returns: response text
        """
        start_time = time.time()

        try:
            # 1. OBSERVE: Get conversation context
            logger.info(f"OBSERVE: Getting context for conversation {conversation_id}")
            context = await self.context_manager.get_context(conversation_id)

            # 2. REASON: Extract intent
            logger.info("REASON: Extracting intent")
            intent = await self.reasoning_engine.extract_intent(context)

            # Check if clarification needed
            if intent.clarification_needed:
                return intent.clarification_needed

            # 3. PLAN: Create action plan
            logger.info("PLAN: Creating action plan")
            action_plan = await self.reasoning_engine.create_action_plan(intent)

            # 4. ACT: Execute tools
            logger.info(f"ACT: Executing {len(action_plan.tools)} tools")
            results = await self._execute_plan(action_plan.tools)

            # 5. RESPOND: Compose response
            logger.info("RESPOND: Composing response")
            response = await self.reasoning_engine.compose_response(intent, results)

            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            await self.event_repo.log_action(
                conversation_id=conversation_id,
                user_id=user_id,
                trigger_source="telegram_mention",
                action_type="full_orplar",
                intent_data=intent.dict(),
                tool_calls=[tool.dict() for tool in action_plan.tools],
                response_text=response,
                success=all(r.get('success') for r in results),
                execution_time_ms=execution_time
            )

            logger.info(f"ORPLAR loop completed in {execution_time}ms")
            return response

        except Exception as e:
            logger.error(f"Error in process_mention: {e}", exc_info=True)
            return "I encountered an error processing your request. Please try again."

    async def _execute_plan(self, tools: list) -> list[dict]:
        """Execute tools and return results"""
        results = []

        for tool_call in tools:
            tool_start = time.time()

            try:
                # Get tool from registry
                tool = self.tool_registry.get_tool(tool_call.tool_name)

                if not tool:
                    logger.error(f"Tool not found: {tool_call.tool_name}")
                    results.append({
                        'action_id': tool_call.action_id,
                        'tool': tool_call.tool_name,
                        'success': False,
                        'error': f"Tool {tool_call.tool_name} not found"
                    })
                    continue

                # Execute tool
                logger.info(f"Executing tool: {tool_call.tool_name}")
                result = await tool.execute(**tool_call.parameters)

                tool_call.result = result
                tool_call.success = result.get('success', False)
                tool_call.execution_time_ms = int((time.time() - tool_start) * 1000)

                results.append({
                    'action_id': tool_call.action_id,
                    'tool': tool_call.tool_name,
                    'success': tool_call.success,
                    'result': result
                })

                logger.info(f"Tool {tool_call.tool_name} completed: {tool_call.success}")

            except Exception as e:
                logger.error(f"Tool execution error ({tool_call.tool_name}): {e}")
                tool_call.success = False
                tool_call.error = str(e)

                results.append({
                    'action_id': tool_call.action_id,
                    'tool': tool_call.tool_name,
                    'success': False,
                    'error': str(e)
                })

        return results
