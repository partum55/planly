"""Base tool interface and registry"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str  # "string", "integer", "datetime", "array", "object"
    description: str
    required: bool = False
    default: Any = None


class ToolSchema(BaseModel):
    """Tool schema for LLM function calling"""
    name: str
    description: str
    parameters: List[ToolParameter]


class BaseTool(ABC):
    """Base class for all tools"""

    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """Return tool schema for LLM"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with given parameters

        Should return:
        {
            'success': bool,
            'result': Any,
            'error': str | None
        }
        """
        pass

    async def validate_parameters(self, **kwargs) -> bool:
        """Validate parameters before execution"""
        required_params = [p.name for p in self.schema.parameters if p.required]

        for param in required_params:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: {param}")

        return True


class ToolRegistry:
    """Central registry of available tools"""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        logger.info("Tool registry initialized")

    def register(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.schema.name] = tool
        logger.info(f"Registered tool: {tool.schema.name}")

    def get_tool(self, name: str) -> BaseTool:
        """Get tool by name"""
        return self.tools.get(name)

    def get_schemas(self) -> List[ToolSchema]:
        """Get all tool schemas for LLM"""
        return [tool.schema for tool in self.tools.values()]

    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self.tools.keys())
