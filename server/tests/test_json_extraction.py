"""Tests for the robust JSON extraction function used by OllamaClient."""
import pytest

from integrations.ollama.client import _extract_json_object


class TestExtractJsonObject:
    """Test _extract_json_object against various LLM output formats."""

    def test_clean_json(self):
        raw = '{"intent": "schedule", "confidence": 0.9}'
        result = _extract_json_object(raw)
        assert '"intent"' in result
        assert '"schedule"' in result

    def test_markdown_fence_json(self):
        raw = '```json\n{"intent": "schedule"}\n```'
        result = _extract_json_object(raw)
        assert '"schedule"' in result

    def test_markdown_fence_no_language(self):
        raw = '```\n{"intent": "schedule"}\n```'
        result = _extract_json_object(raw)
        assert '"schedule"' in result

    def test_prose_before_and_after(self):
        raw = 'Here is the analysis:\n{"intent": "schedule", "confidence": 0.9}\nI hope this helps!'
        result = _extract_json_object(raw)
        assert '"intent"' in result

    def test_nested_braces(self):
        raw = '{"action": {"name": "create_event", "params": {"title": "Meeting"}}}'
        result = _extract_json_object(raw)
        import json
        parsed = json.loads(result)
        assert parsed["action"]["params"]["title"] == "Meeting"

    def test_multiple_json_objects_takes_first(self):
        raw = '{"a": 1}\n{"b": 2}'
        result = _extract_json_object(raw)
        import json
        parsed = json.loads(result)
        assert "a" in parsed

    def test_no_json_raises_valueerror(self):
        raw = "I don't have any JSON for you, sorry!"
        with pytest.raises(ValueError, match="No valid JSON"):
            _extract_json_object(raw)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _extract_json_object("")

    def test_only_opening_brace_raises(self):
        with pytest.raises(ValueError):
            _extract_json_object('{"broken": ')

    def test_json_with_string_containing_braces(self):
        raw = '{"text": "use { and } in strings"}'
        result = _extract_json_object(raw)
        import json
        parsed = json.loads(result)
        assert "{" in parsed["text"]

    def test_markdown_fence_with_invalid_json_falls_through(self):
        """If the fence content is not valid JSON, fall through to brace matching."""
        raw = '```json\nnot valid json\n```\n\nBut here: {"valid": true}'
        result = _extract_json_object(raw)
        import json
        parsed = json.loads(result)
        assert parsed["valid"] is True

    def test_json_array_not_matched(self):
        """_extract_json_object is for objects only (starts with {)."""
        raw = '[1, 2, 3]'
        with pytest.raises(ValueError):
            _extract_json_object(raw)

    def test_complex_nested_structure(self):
        raw = """Here is my response:
```json
{
    "tools": [
        {
            "name": "create_calendar_event",
            "parameters": {
                "title": "Team lunch",
                "participants": ["alice", "bob"]
            }
        }
    ],
    "confidence": 0.95
}
```
"""
        result = _extract_json_object(raw)
        import json
        parsed = json.loads(result)
        assert len(parsed["tools"]) == 1
        assert parsed["tools"][0]["name"] == "create_calendar_event"

    def test_whitespace_around_json(self):
        raw = "   \n\n  {\"key\": \"value\"}  \n\n  "
        result = _extract_json_object(raw)
        import json
        parsed = json.loads(result)
        assert parsed["key"] == "value"
