"""Reasoning Engine - LLM integration for intent extraction and planning"""
import json
import logging
from typing import Optional
from datetime import datetime
import dateparser

from models.intent import Intent
from models.action import ActionPlan, ToolCall
from models.message import ConversationContext
from integrations.ollama.client import OllamaClient
from integrations.ollama.prompts import (
    INTENT_EXTRACTION_PROMPT,
    TOOL_PLANNING_PROMPT,
    RESPONSE_COMPOSITION_PROMPT
)

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
        Extract structured intent from conversation context

        Returns Intent with:
        - activity_type
        - participants who consented
        - datetime (parsed or inferred)
        - location
        - requirements
        - confidence level
        - clarification if needed
        """
        try:
            # Format conversation for LLM
            conversation_text = self._format_conversation(context)

            # Create prompt
            prompt = INTENT_EXTRACTION_PROMPT.format(
                conversation=conversation_text
            )

            # Get structured response from LLM
            try:
                intent_response = await self.ollama.generate_structured(
                    prompt=prompt,
                    schema=Intent
                )
            except Exception as e:
                logger.error(f"LLM intent extraction failed: {e}")
                # Fallback to basic intent
                return self._create_fallback_intent(context)

            # Filter participants by consent
            consenting_participants = []
            for participant in intent_response.participants:
                # Check if this participant is in the consent signals
                for user_id, signal in context.consent_signals.items():
                    if signal == 'accepted':
                        # Match by username
                        user = context.participants.get(user_id)
                        if user and (user.get('username') == participant or
                                   user.get('first_name') == participant):
                            consenting_participants.append(participant)
                            break

            intent_response.participants = list(set(consenting_participants))

            # Parse datetime if string
            if isinstance(intent_response.datetime, str):
                parsed_time = dateparser.parse(intent_response.datetime)
                intent_response.datetime = parsed_time

            # Check if critical info is missing
            if not intent_response.participants:
                intent_response.missing_fields.append('participants')
                intent_response.clarification_needed = "Who's joining this activity?"

            if not intent_response.datetime and 'time' not in intent_response.missing_fields:
                intent_response.missing_fields.append('time')
                if not intent_response.clarification_needed:
                    intent_response.clarification_needed = "What time works for everyone?"

            logger.info(f"Extracted intent: {intent_response.activity_type}, "
                       f"{len(intent_response.participants)} participants, "
                       f"confidence: {intent_response.confidence}")

            return intent_response

        except Exception as e:
            logger.error(f"Intent extraction error: {e}")
            return self._create_fallback_intent(context)

    async def create_action_plan(self, intent: Intent) -> ActionPlan:
        """
        Determine which tools to invoke and in what order

        Returns ActionPlan with:
        - List of ToolCall objects
        - Reasoning for the approach
        """
        try:
            # Get tool schemas
            tool_schemas = self.tool_registry.get_schemas()

            # Format for LLM
            schemas_text = json.dumps([schema.dict() for schema in tool_schemas], indent=2)

            prompt = TOOL_PLANNING_PROMPT.format(
                intent=intent.model_dump_json(indent=2),
                tool_schemas=schemas_text
            )

            response_text = await self.ollama.generate(prompt=prompt, temperature=0.5)

            # Parse JSON response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            plan_data = json.loads(json_str)

            # Create ToolCall objects
            tool_calls = []
            for tool_data in plan_data.get('tools', []):
                tool_call = ToolCall(
                    tool_name=tool_data['tool_name'],
                    description=tool_data.get('description', ''),
                    parameters=tool_data.get('parameters', {})
                )
                tool_calls.append(tool_call)

            action_plan = ActionPlan(
                tools=tool_calls,
                reasoning=plan_data.get('reasoning', '')
            )

            logger.info(f"Created action plan with {len(tool_calls)} tools")
            return action_plan

        except Exception as e:
            logger.error(f"Action planning error: {e}")
            # Fallback: create basic plan
            return self._create_fallback_plan(intent)

    async def compose_response(
        self,
        intent: Intent,
        results: list[dict]
    ) -> str:
        """Generate natural response based on action results"""
        try:
            prompt = RESPONSE_COMPOSITION_PROMPT.format(
                intent=intent.model_dump_json(indent=2),
                results=json.dumps(results, indent=2)
            )

            response = await self.ollama.generate(prompt=prompt, temperature=0.7)

            # Clean up response
            response = response.strip()

            logger.info("Composed response")
            return response

        except Exception as e:
            logger.error(f"Response composition error: {e}")
            return self._create_fallback_response(intent, results)

    def _format_conversation(self, context: ConversationContext) -> str:
        """Format conversation context for LLM"""
        lines = []

        for msg in context.messages:
            sender = msg.username or msg.first_name or f"User{msg.user_id}"
            lines.append(f"{sender}: {msg.text}")

        return "\n".join(lines)

    def _create_fallback_intent(self, context: ConversationContext) -> Intent:
        """Create basic intent when LLM fails"""
        participants = [
            user.get('username') or user.get('first_name', f"User{uid}")
            for uid, user in context.participants.items()
            if context.consent_signals.get(uid) == 'accepted'
        ]

        return Intent(
            activity_type='other',
            participants=participants,
            confidence=0.3,
            missing_fields=['activity_type', 'datetime'],
            clarification_needed="What would you like to do and when?"
        )

    def _create_fallback_plan(self, intent: Intent) -> ActionPlan:
        """Create basic action plan when LLM fails"""
        # Default: just create calendar event
        tool_call = ToolCall(
            tool_name='calendar_create_event',
            description=f"Create calendar event for {intent.activity_type}",
            parameters={
                'title': f"{intent.activity_type.title()} with {', '.join(intent.participants[:3])}",
                'datetime': intent.datetime.isoformat() if intent.datetime else datetime.now().isoformat(),
                'duration_minutes': 120
            }
        )

        return ActionPlan(
            tools=[tool_call],
            reasoning="Creating calendar event for the activity"
        )

    def _create_fallback_response(self, intent: Intent, results: list) -> str:
        """Create basic response when LLM fails"""
        successful = sum(1 for r in results if r.get('success'))
        return f"I've completed {successful} out of {len(results)} actions for your {intent.activity_type}."
