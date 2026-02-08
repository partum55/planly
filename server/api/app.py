"""FastAPI application setup"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.routes import auth, agent, telegram
from config.logging_config import setup_logging
from config.settings import settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    # Setup logging
    setup_logging(settings.LOG_LEVEL)

    # Create app
    app = FastAPI(
        title="Planly API",
        description="AI Agent for scheduling and event coordination",
        version="1.0.0"
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(agent.router, prefix="/agent", tags=["Agent"])
    app.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "version": "1.0.0",
            "service": "planly-api"
        }

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "Planly API - AI Agent for scheduling and coordination",
            "docs": "/docs",
            "health": "/health"
        }

    logger.info("FastAPI application created")
    return app
