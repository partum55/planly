"""Base tool interface and registry with JSON Schema support."""
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ToolMetadata(BaseModel):
    """Annotations signalling tool behaviour to the planning LLM."""
    destructive_hint: bool = False   # True if the tool mutates external state
    read_only_hint: bool = False     # True if the tool only reads data
    idempotent_hint: bool = False    # True if repeated calls have no extra effect
    open_world_hint: bool = True     # True if the tool interacts with external services
    requires_auth_hint: bool = False # True if the tool needs external credentials configured
    mock_mode: bool = False          # True if the tool is currently returning placeholder data


class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str
    type: str  # JSON Schema types: "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = False
    default: Any = None
    enum: Optional[List[str]] = None


class ToolSchema(BaseModel):
    """Tool schema for LLM function calling."""
    name: str
    description: str
    parameters: List[ToolParameter]
    metadata: ToolMetadata = ToolMetadata()

    def to_json_schema(self) -> dict:
        """
        Convert to standard JSON Schema format compatible with
        OpenAI function calling / MCP tool definitions.
        """
        properties: Dict[str, Any] = {}
        required_list: List[str] = []

        for param in self.parameters:
            prop: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                prop["default"] = param.default
            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop
            if param.required:
                required_list.append(param.name)

        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required_list:
            schema["required"] = required_list

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": schema,
            "metadata": self.metadata.model_dump(),
        }


class BaseTool(ABC):
    """Base class for all tools."""

    @cached_property
    def schema(self) -> ToolSchema:
        """
        Return tool schema for LLM. Cached after first access so schema
        objects are not reconstructed on every call.
        """
        return self._build_schema()

    @abstractmethod
    def _build_schema(self) -> ToolSchema:
        """Subclasses implement this to define their schema."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with given parameters.

        Must return:
        {
            'success': bool,
            'result': Any,       # on success
            'error': str | None  # on failure
        }
        """
        ...

    async def validate_parameters(self, **kwargs) -> bool:
        """Validate parameters before execution."""
        required_params = [p.name for p in self.schema.parameters if p.required]

        missing = [p for p in required_params if p not in kwargs]
        if missing:
            raise ValueError(f"Missing required parameter(s): {', '.join(missing)}")

        return True


class ToolRegistry:
    """Central registry of available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        logger.info("Tool registry initialized")

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        name = tool.schema.name
        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool by name."""
        return self._tools.get(name)

    def get_schemas(self) -> List[ToolSchema]:
        """Get all tool schemas for LLM."""
        return [tool.schema for tool in self._tools.values()]

    def get_json_schemas(self) -> List[dict]:
        """Get all tool schemas in standard JSON Schema format."""
        return [tool.schema.to_json_schema() for tool in self._tools.values()]

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tools_status(self) -> List[dict]:
        """Return operational status for each tool (mock vs real, auth required)."""
        statuses = []
        for name, tool in self._tools.items():
            meta = tool.schema.metadata
            statuses.append({
                "name": name,
                "mock_mode": meta.mock_mode,
                "requires_auth": meta.requires_auth_hint,
                "destructive": meta.destructive_hint,
                "read_only": meta.read_only_hint,
            })
        return statuses
