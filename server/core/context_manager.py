"""Context Manager — maintains rolling conversation window."""
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID
import logging
import re

from models.message import Message, ConversationContext
from database.repositories.conversation_repo import ConversationRepository

logger = logging.getLogger(__name__)


def _compile_word_patterns(keywords: List[str]) -> re.Pattern:
    """
    Build a single compiled regex that matches any of the keywords
    on word boundaries.  This prevents "ok" from matching inside
    "booking" and "sorry" from matching inside "not sorry at all, I'm coming".
    """
    escaped = [re.escape(kw) for kw in keywords]
    pattern = r"\b(?:" + "|".join(escaped) + r")\b"
    return re.compile(pattern, re.IGNORECASE)


class ContextManager:
    """
    Manages conversation context:
    - Maintains rolling 1-hour window
    - Detects consent signals (word-boundary matching)
    - Extracts time references
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        window_minutes: int = 60,
    ):
        self.conversation_repo = conversation_repo
        self.window_minutes = window_minutes

        # Consent detection keywords — matched on word boundaries.
        # Avoid short ambiguous words that commonly appear in non-consent
        # contexts (e.g. "pass" in "pass by", "ok" in isolation can be
        # acknowledgement rather than commitment).
        self._accept_keywords = [
            "yes", "sure", "i'm in", "count me in", "+1",
            "sounds good", "im in", "yeah", "okay",
            "definitely", "absolutely", "for sure",
            "let's do it", "i'll be there", "i'll come",
        ]
        self._decline_keywords = [
            "can't make it", "cannot", "not available", "-1",
            "unable", "won't make it", "i'm busy",
            "have plans", "i'll pass", "count me out",
            "can't come", "not coming",
        ]

        self._accept_re = _compile_word_patterns(self._accept_keywords)
        self._decline_re = _compile_word_patterns(self._decline_keywords)

    async def add_message(self, conversation_id: UUID, message_data: dict):
        """Store a new message"""
        await self.conversation_repo.insert_message(conversation_id, message_data)

    async def get_context(self, conversation_id: UUID) -> ConversationContext:
        """
        Get conversation context for the rolling window

        Returns structured context with:
        - messages (last hour)
        - consent signals
        - time references
        """
        # Get messages from last hour
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=self.window_minutes)
        messages_data = await self.conversation_repo.get_messages_since(
            conversation_id, cutoff_time
        )

        # Convert to Message models
        messages = []
        for msg_data in messages_data:
            messages.append(Message(
                message_id=msg_data.get('message_id'),
                user_id=msg_data.get('user_id'),
                username=msg_data.get('username'),
                first_name=msg_data.get('first_name'),
                last_name=msg_data.get('last_name'),
                text=msg_data['text'],
                timestamp=datetime.fromisoformat(msg_data['timestamp'].replace('Z', '+00:00')),
                source=msg_data.get('source', 'telegram'),
                is_bot_mention=msg_data.get('is_bot_mention', False)
            ))

        # Build context
        context = ConversationContext(
            messages=messages,
            participants=self._extract_participants(messages),
            consent_signals=self._detect_consent_signals(messages),
            time_references=self._extract_time_references(messages),
            mention_message=self._get_mention_message(messages)
        )

        return context

    def _extract_participants(self, messages: List[Message]) -> dict:
        """Extract unique participants from messages."""
        participants = {}

        for msg in messages:
            # Use str(user_id) when available, fall back to username
            key = str(msg.user_id) if msg.user_id is not None else msg.username
            if key and key not in participants:
                participants[key] = {
                    'user_id': msg.user_id,
                    'username': msg.username,
                    'first_name': msg.first_name,
                    'last_name': msg.last_name,
                }

        return participants

    def _detect_consent_signals(self, messages: List[Message]) -> dict:
        """Detect who agreed or declined using word-boundary matching."""
        consent_signals = {}

        for msg in messages:
            key = str(msg.user_id) if msg.user_id is not None else msg.username
            if not key:
                continue

            text = msg.text

            # Check for acceptance (word-boundary regex)
            if self._accept_re.search(text):
                consent_signals[key] = "accepted"

            # Check for decline (overrides acceptance)
            if self._decline_re.search(text):
                consent_signals[key] = "declined"

        return consent_signals

    def _extract_time_references(self, messages: List[Message]) -> List[str]:
        """Extract time-related phrases from messages"""
        time_keywords = [
            'tomorrow', 'today', 'tonight', 'this evening',
            'next week', 'next month', 'monday', 'tuesday',
            'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'am', 'pm', 'morning', 'afternoon', 'evening', 'night'
        ]

        time_refs = []

        for msg in messages:
            text_lower = msg.text.lower()
            for keyword in time_keywords:
                if keyword in text_lower:
                    # Extract the sentence containing the time reference
                    sentences = msg.text.split('.')
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            time_refs.append(sentence.strip())
                            break

        return list(set(time_refs))  # Remove duplicates

    def _get_mention_message(self, messages: List[Message]) -> str:
        """Get the message that mentioned the bot"""
        for msg in reversed(messages):
            if msg.is_bot_mention:
                return msg.text
        return ""

    async def cleanup_old_messages(self, conversation_id: UUID):
        """Remove messages older than the window"""
        await self.conversation_repo.cleanup_old_messages(conversation_id)
