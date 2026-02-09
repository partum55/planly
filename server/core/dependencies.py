"""
Shared singleton dependencies for the application.

All expensive objects (HTTP clients, tool registries, agent instances) are created
once at startup and reused across requests. This eliminates per-request object
construction, prevents resource leaks (e.g. unclosed httpx clients), and removes
the duplicated get_agent() factories that previously existed in each route module.
"""
import logging
from typing import Optional

from database.client import get_supabase
from database.repositories.conversation_repo import ConversationRepository
from database.repositories.event_repo import EventRepository
from core.context_manager import ContextManager
from core.reasoning_engine import ReasoningEngine
from integrations.ollama.client import OllamaClient
from integrations.google_calendar.client import GoogleCalendarClient
from tools.base import ToolRegistry
from tools.calendar_tool import CalendarTool
from tools.restaurant_tool import RestaurantSearchTool
from tools.cinema_tool import CinemaSearchTool
from core.agent import PlanlyAgent

logger = logging.getLogger(__name__)

# Module-level singletons — initialized once via init_dependencies()
_ollama_client: Optional[OllamaClient] = None
_tool_registry: Optional[ToolRegistry] = None
_calendar_client: Optional[GoogleCalendarClient] = None


def init_dependencies() -> None:
    """
    Initialize all shared singletons. Called once at application startup.
    """
    global _ollama_client, _tool_registry, _calendar_client

    logger.info("Initializing shared dependencies...")

    # LLM client — single httpx.AsyncClient, reused for all requests
    _ollama_client = OllamaClient()

    # Google Calendar — single service instance
    _calendar_client = GoogleCalendarClient()

    # Tool registry — register all tools once
    _tool_registry = ToolRegistry()
    _tool_registry.register(CalendarTool(_calendar_client))
    _tool_registry.register(RestaurantSearchTool())
    _tool_registry.register(CinemaSearchTool())

    logger.info(
        f"Dependencies initialized: {len(_tool_registry.list_tools())} tools registered"
    )


async def shutdown_dependencies() -> None:
    """Clean up resources on shutdown."""
    global _ollama_client
    if _ollama_client:
        await _ollama_client.close()
        logger.info("OllamaClient closed")


def get_ollama_client() -> OllamaClient:
    if _ollama_client is None:
        raise RuntimeError("Dependencies not initialized. Call init_dependencies() first.")
    return _ollama_client


def get_tool_registry() -> ToolRegistry:
    if _tool_registry is None:
        raise RuntimeError("Dependencies not initialized. Call init_dependencies() first.")
    return _tool_registry


def get_agent() -> PlanlyAgent:
    """
    Build a PlanlyAgent using shared singletons.

    Repositories are lightweight wrappers around the Supabase client,
    so creating them per-request is fine. The expensive objects
    (OllamaClient, ToolRegistry, GoogleCalendarClient) are shared.

    WARNING: ContextManager, ReasoningEngine, and repositories are created
    per-request and MUST remain stateless.  Do NOT add mutable instance
    state (caches, counters, etc.) to these classes — it will not be shared
    across requests and will silently break under concurrency.
    """
    supabase = get_supabase()
    conversation_repo = ConversationRepository(supabase)
    event_repo = EventRepository(supabase)

    context_manager = ContextManager(conversation_repo)
    reasoning_engine = ReasoningEngine(get_ollama_client(), get_tool_registry())

    return PlanlyAgent(
        context_manager=context_manager,
        reasoning_engine=reasoning_engine,
        tool_registry=get_tool_registry(),
        event_repo=event_repo,
    )
