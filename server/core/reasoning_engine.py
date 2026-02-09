"""Reasoning Engine — LLM integration for intent extraction and planning."""
import json
import logging
from typing import Optional, Union
from datetime import datetime
import dateparser

from models.intent import Intent
from models.action import ActionPlan, ToolCall
from models.message import ConversationContext
from integrations.ollama.client import OllamaClient, _extract_json_object
from integrations.ollama.prompts import (
    INTENT_EXTRACTION_PROMPT,
    TOOL_PLANNING_PROMPT,
    RESPONSE_COMPOSITION_PROMPT,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    Interfaces with LLM for:
    - Intent extraction from conversation
    - Action planning (which tools to use)
    - Response composition
    """

    def __init__(self, ollama_client: OllamaClient, tool_registry):
        self.ollama = ollama_client
        self.tool_registry = tool_registry

    async def extract_intent(self, context: ConversationContext) -> Intent:
        """
        Extract structured intent from conversation context.

        Uses a per-phase timeout from settings so that one slow LLM call
        doesn't block the entire request for minutes.
        """
        try:
            conversation_text = self._format_conversation(context)

            prompt = INTENT_EXTRACTION_PROMPT.format(
                conversation=conversation_text,
            )

            try:
                intent_response = await self.ollama.generate_structured(
                    prompt=prompt,
                    schema=Intent,
                    timeout_s=settings.LLM_INTENT_TIMEOUT,
                )
            except (TimeoutError, ConnectionError, OSError) as e:
                # Infrastructure failure — propagate so the caller can report
                # a retryable error instead of returning a silent fallback.
                logger.error(f"LLM infrastructure error during intent extraction: {e}")
                raise
            except Exception as e:
                logger.error(f"LLM intent parsing failed (non-retryable): {e}")
                return self._create_fallback_intent(context)

            # Filter participants by consent
            consenting_participants = []
            for participant in intent_response.participants:
                for user_id, signal in context.consent_signals.items():
                    if signal == "accepted":
                        user = context.participants.get(user_id)
                        if user and (
                            user.get("username") == participant
                            or user.get("first_name") == participant
                        ):
                            consenting_participants.append(participant)
                            break

            intent_response.participants = list(set(consenting_participants))

            # Parse datetime if string
            if isinstance(intent_response.datetime, str):
                parsed_time = dateparser.parse(intent_response.datetime)
                intent_response.datetime = parsed_time

            # Check if critical info is missing
            if not intent_response.participants:
                intent_response.missing_fields.append("participants")
                intent_response.clarification_needed = "Who's joining this activity?"

            if (
                not intent_response.datetime
                and "time" not in intent_response.missing_fields
            ):
                intent_response.missing_fields.append("time")
                if not intent_response.clarification_needed:
                    intent_response.clarification_needed = (
                        "What time works for everyone?"
                    )

            logger.info(
                f"Extracted intent: {intent_response.activity_type}, "
                f"{len(intent_response.participants)} participants, "
                f"confidence: {intent_response.confidence}"
            )

            return intent_response

        except Exception as e:
            logger.error(f"Intent extraction error: {e}")
            return self._create_fallback_intent(context)

    async def create_action_plan(self, intent: Intent) -> ActionPlan:
        """
        Determine which tools to invoke and in what order.

        Uses JSON mode and robust extraction to handle messy LLM output.
        """
        try:
            tool_schemas = self.tool_registry.get_json_schemas()
            schemas_text = json.dumps(tool_schemas, indent=2)

            prompt = TOOL_PLANNING_PROMPT.format(
                intent=intent.model_dump_json(indent=2),
                tool_schemas=schemas_text,
            )

            response_text = await self.ollama.generate(
                prompt=prompt,
                temperature=0.5,
                timeout_s=settings.LLM_PLANNING_TIMEOUT,
                json_mode=True,
            )

            # Robust JSON extraction
            json_str = _extract_json_object(response_text)
            plan_data = json.loads(json_str)

            tool_calls = []
            for tool_data in plan_data.get("tools", []):
                tool_call = ToolCall(
                    tool_name=tool_data["tool_name"],
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("parameters", {}),
                )
                tool_calls.append(tool_call)

            action_plan = ActionPlan(
                tools=tool_calls,
                reasoning=plan_data.get("reasoning", ""),
            )

            logger.info(f"Created action plan with {len(tool_calls)} tools")
            return action_plan

        except (TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"LLM infrastructure error during action planning: {e}")
            raise
        except Exception as e:
            logger.error(f"Action planning error (non-retryable): {e}")
            return self._create_fallback_plan(intent)

    async def compose_response(
        self,
        intent: Union[Intent, dict, None],
        results: list[dict],
    ) -> str:
        """Generate natural response based on action results.

        ``intent`` can be an Intent object, a dict, or None.
        """
        try:
            # Normalise intent to JSON string
            if intent is None:
                intent_json = "{}"
            elif isinstance(intent, dict):
                intent_json = json.dumps(intent, indent=2, default=str)
            else:
                intent_json = intent.model_dump_json(indent=2)

            prompt = RESPONSE_COMPOSITION_PROMPT.format(
                intent=intent_json,
                results=json.dumps(results, indent=2, default=str),
            )

            response = await self.ollama.generate(
                prompt=prompt,
                temperature=0.7,
                timeout_s=settings.LLM_RESPONSE_TIMEOUT,
            )

            return response.strip()

        except (TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"LLM infrastructure error during response composition: {e}")
            raise
        except Exception as e:
            logger.error(f"Response composition error (non-retryable): {e}")
            return self._create_fallback_response(intent, results)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _format_conversation(self, context: ConversationContext) -> str:
        """Format conversation context for LLM with XML delimiters to reduce prompt injection."""
        lines = []
        for msg in context.messages:
            sender = msg.username or msg.first_name or f"User{msg.user_id}"
            # Escape any XML-like tags in user text
            safe_text = msg.text.replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f'<message sender="{sender}">{safe_text}</message>')
        return "\n".join(lines)

    def _create_fallback_intent(self, context: ConversationContext) -> Intent:
        """Create basic intent when LLM fails."""
        participants = [
            user.get("username") or user.get("first_name", f"User{uid}")
            for uid, user in context.participants.items()
            if context.consent_signals.get(uid) == "accepted"
        ]

        return Intent(
            activity_type="other",
            participants=participants,
            confidence=0.3,
            missing_fields=["activity_type", "datetime"],
            clarification_needed="What would you like to do and when?",
        )

    def _create_fallback_plan(self, intent: Intent) -> ActionPlan:
        """Create a safe fallback when LLM planning fails.

        Instead of blindly creating a calendar event (which would be a
        side-effecting action with potentially wrong data), we return an
        empty plan with a clarification request so the user can confirm.
        """
        logger.warning("LLM planning failed — returning clarification instead of fallback action")
        return ActionPlan(
            tools=[],
            reasoning="LLM planning failed. Requesting user clarification instead of guessing.",
            requires_clarification=True,
            clarification_question=(
                "I wasn't able to fully plan your request. "
                "Could you confirm the activity, time, and who's joining?"
            ),
        )

    def _create_fallback_response(
        self,
        intent: Union[Intent, dict, None],
        results: list,
    ) -> str:
        """Create basic response when LLM fails."""
        successful = sum(1 for r in results if r.get("success"))
        activity = "activity"
        if isinstance(intent, Intent):
            activity = intent.activity_type
        elif isinstance(intent, dict):
            activity = intent.get("activity_type", "activity")
        return f"I've completed {successful} out of {len(results)} actions for your {activity}."
