"""Application configuration settings."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List, Optional

# Get the server directory path
SERVER_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_DB_URL: Optional[str] = None

    # LLM Configuration
    USE_CLOUD_LLM: bool = False
    OLLAMA_ENDPOINT: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    LLM_API_KEY: Optional[str] = None

    # Per-phase LLM timeouts (seconds)
    LLM_INTENT_TIMEOUT: int = 20
    LLM_PLANNING_TIMEOUT: int = 15
    LLM_RESPONSE_TIMEOUT: int = 15

    # Google Calendar
    GOOGLE_CALENDAR_ID: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "./integrations/google_calendar/service_account.json"

    # External APIs
    YELP_API_KEY: Optional[str] = None
    GOOGLE_PLACES_API_KEY: Optional[str] = None

    # Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # CORS — explicit list of allowed origins
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # Telegram webhook secret (only needed if using webhook mode, not polling)
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Context Management
    CONTEXT_WINDOW_MINUTES: int = 60

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if self.TELEGRAM_WEBHOOK_SECRET and len(self.TELEGRAM_WEBHOOK_SECRET) < 8:
            raise ValueError(
                "TELEGRAM_WEBHOOK_SECRET must be at least 8 characters when set. "
                "Without it, the /telegram/webhook endpoint will reject all requests."
            )
        return self

    class Config:
        env_file = str(SERVER_DIR / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
