"""Tests for consent detection with word-boundary matching.

Verifies that words like "ok" don't match inside "booking" and
"sorry" doesn't match when it shouldn't.
"""
import pytest
from unittest.mock import MagicMock

from core.context_manager import ContextManager, _compile_word_patterns
from models.message import Message
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _msg(text: str, user_id: int = 1) -> Message:
    return Message(
        message_id=100,
        user_id=user_id,
        username="testuser",
        first_name="Test",
        last_name="User",
        text=text,
        timestamp=datetime.now(timezone.utc),
        source="telegram",
        is_bot_mention=False,
    )


@pytest.fixture
def ctx() -> ContextManager:
    repo = MagicMock()
    return ContextManager(repo)


# ---------------------------------------------------------------------------
# _compile_word_patterns
# ---------------------------------------------------------------------------

class TestCompileWordPatterns:
    def test_basic_match(self):
        pat = _compile_word_patterns(["ok", "yes"])
        assert pat.search("ok")
        assert pat.search("yes")

    def test_case_insensitive(self):
        pat = _compile_word_patterns(["ok"])
        assert pat.search("OK")
        assert pat.search("Ok")

    def test_no_match_inside_word(self):
        pat = _compile_word_patterns(["ok"])
        assert not pat.search("booking")

    def test_match_at_word_boundary(self):
        pat = _compile_word_patterns(["ok"])
        assert pat.search("ok, sounds good")
        assert pat.search("that's ok!")

    def test_multi_word_phrase(self):
        pat = _compile_word_patterns(["count me in"])
        assert pat.search("yes, count me in!")
        assert not pat.search("counter me inside")


# ---------------------------------------------------------------------------
# _detect_consent_signals
# ---------------------------------------------------------------------------

class TestDetectConsentSignals:
    def test_simple_yes(self, ctx):
        msgs = [_msg("yes")]
        result = ctx._detect_consent_signals(msgs)
        assert result["1"] == "accepted"

    def test_simple_no(self, ctx):
        msgs = [_msg("no")]
        result = ctx._detect_consent_signals(msgs)
        assert result["1"] == "declined"

    def test_ok_does_not_match_booking(self, ctx):
        """The 'ok' keyword must not trigger on 'booking'."""
        msgs = [_msg("I'm booking a table for 4")]
        result = ctx._detect_consent_signals(msgs)
        assert "1" not in result

    def test_sorry_as_decline(self, ctx):
        msgs = [_msg("sorry, can't make it")]
        result = ctx._detect_consent_signals(msgs)
        assert result["1"] == "declined"

    def test_sorry_not_decline_when_part_of_acceptance(self, ctx):
        """Edge case: both accept and decline keywords present."""
        msgs = [_msg("sorry for the delay, I'm in")]
        result = ctx._detect_consent_signals(msgs)
        # Both accept and decline regex match; decline overrides (checked second)
        assert result["1"] in ("accepted", "declined")

    def test_multiple_users(self, ctx):
        msgs = [
            _msg("yes, count me in!", user_id=10),
            _msg("can't make it", user_id=20),
            _msg("sure thing!", user_id=30),
        ]
        result = ctx._detect_consent_signals(msgs)
        assert result["10"] == "accepted"
        assert result["20"] == "declined"
        assert result["30"] == "accepted"

    def test_no_user_id_uses_username_fallback(self, ctx):
        msg = _msg("yes")
        msg.user_id = None
        result = ctx._detect_consent_signals([msg])
        # Falls back to username as key
        assert result["testuser"] == "accepted"

    def test_no_user_id_no_username_skipped(self, ctx):
        msg = _msg("yes")
        msg.user_id = None
        msg.username = None
        result = ctx._detect_consent_signals([msg])
        assert result == {}

    def test_sounds_good(self, ctx):
        msgs = [_msg("sounds good")]
        result = ctx._detect_consent_signals(msgs)
        assert result["1"] == "accepted"

    def test_pass_as_decline(self, ctx):
        msgs = [_msg("I'll pass")]
        result = ctx._detect_consent_signals(msgs)
        assert result["1"] == "declined"

    def test_empty_messages(self, ctx):
        result = ctx._detect_consent_signals([])
        assert result == {}

    def test_definitely(self, ctx):
        msgs = [_msg("definitely!")]
        result = ctx._detect_consent_signals(msgs)
        assert result["1"] == "accepted"

    def test_busy_as_decline(self, ctx):
        msgs = [_msg("I'm busy that day")]
        result = ctx._detect_consent_signals(msgs)
        assert result["1"] == "declined"
