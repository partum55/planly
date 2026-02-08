"""Main application entry point"""
import uvicorn
import logging
from api.app import create_app
from database.client import init_supabase
from config.settings import settings

logger = logging.getLogger(__name__)


def main():
    """Start the application"""

    # Initialize database
    logger.info("Initializing database connection...")
    init_supabase()

    # Create FastAPI app
    app = create_app()

    logger.info(f"""
    ╔════════════════════════════════════════╗
    ║         Planly Server Starting         ║
    ╠════════════════════════════════════════╣
    ║  Address: http://{settings.HOST}:{settings.PORT}     ║
    ║  Docs: http://{settings.HOST}:{settings.PORT}/docs    ║
    ║  LLM: {settings.OLLAMA_MODEL:32s} ║
    ╚════════════════════════════════════════╝
    """)

    # Run server
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
