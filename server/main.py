"""Main application entry point."""
import uvicorn
import logging
from api.app import create_app
from config.settings import settings

logger = logging.getLogger(__name__)

# Create FastAPI app — lifespan handler in app.py manages startup/shutdown
app = create_app()


def main():
    """Start the application."""
    logger.info(f"""
    ╔════════════════════════════════════════╗
    ║         Planly Server Starting         ║
    ╠════════════════════════════════════════╣
    ║  Address: http://{settings.HOST}:{settings.PORT}     ║
    ║  Docs: http://{settings.HOST}:{settings.PORT}/docs    ║
    ║  LLM: {settings.OLLAMA_MODEL:32s} ║
    ╚════════════════════════════════════════╝
    """)

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
