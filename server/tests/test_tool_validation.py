"""Tests for tool parameter validation and schema generation."""
import pytest
from unittest.mock import MagicMock

from tools.base import BaseTool, ToolSchema, ToolParameter, ToolRegistry


# ---------------------------------------------------------------------------
# Concrete tool for testing
# ---------------------------------------------------------------------------

class DummyTool(BaseTool):
    def _build_schema(self) -> ToolSchema:
        return ToolSchema(
            name="dummy_tool",
            description="A test tool",
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="Event title",
                    required=True,
                ),
                ToolParameter(
                    name="count",
                    type="integer",
                    description="Number of items",
                    required=False,
                    default=1,
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Category",
                    required=False,
                    enum=["work", "personal", "other"],
                ),
            ],
        )

    async def execute(self, **kwargs):
        return {"success": True, "result": kwargs}


# ---------------------------------------------------------------------------
# ToolSchema
# ---------------------------------------------------------------------------

class TestToolSchema:
    def test_to_json_schema_structure(self):
        tool = DummyTool()
        js = tool.schema.to_json_schema()
        assert js["name"] == "dummy_tool"
        assert js["description"] == "A test tool"
        assert "inputSchema" in js

    def test_json_schema_properties(self):
        tool = DummyTool()
        js = tool.schema.to_json_schema()
        props = js["inputSchema"]["properties"]
        assert "title" in props
        assert props["title"]["type"] == "string"
        assert "count" in props
        assert props["count"]["default"] == 1
        assert "category" in props
        assert props["category"]["enum"] == ["work", "personal", "other"]

    def test_json_schema_required(self):
        tool = DummyTool()
        js = tool.schema.to_json_schema()
        assert js["inputSchema"]["required"] == ["title"]

    def test_schema_cached(self):
        tool = DummyTool()
        schema1 = tool.schema
        schema2 = tool.schema
        assert schema1 is schema2  # Same object — cached_property


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------

class TestParameterValidation:
    @pytest.mark.asyncio
    async def test_missing_required_param_raises(self):
        tool = DummyTool()
        with pytest.raises(ValueError, match="Missing required parameter"):
            await tool.validate_parameters(count=5)

    @pytest.mark.asyncio
    async def test_all_required_present_succeeds(self):
        tool = DummyTool()
        result = await tool.validate_parameters(title="Test Event")
        assert result is True

    @pytest.mark.asyncio
    async def test_extra_params_allowed(self):
        tool = DummyTool()
        result = await tool.validate_parameters(title="Test", extra_field="ignored")
        assert result is True


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        assert registry.get_tool("dummy_tool") is tool

    def test_get_unknown_returns_none(self):
        registry = ToolRegistry()
        assert registry.get_tool("nonexistent") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        assert "dummy_tool" in registry.list_tools()

    def test_get_schemas(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0].name == "dummy_tool"

    def test_get_json_schemas(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        json_schemas = registry.get_json_schemas()
        assert len(json_schemas) == 1
        assert json_schemas[0]["name"] == "dummy_tool"
        assert "inputSchema" in json_schemas[0]
