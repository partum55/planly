"""Application configuration settings"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# Get the server directory path
SERVER_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_DB_URL: Optional[str] = None

    # LLM Configuration
    USE_CLOUD_LLM: bool = False  # True for cloud API, False for local Ollama
    OLLAMA_ENDPOINT: str = "http://localhost:11434"  # For local, or cloud API endpoint
    OLLAMA_MODEL: str = "llama3.1:8b"  # Model name
    LLM_API_KEY: Optional[str] = None  # API key for cloud providers

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

    # Google OAuth (for desktop app "Continue with Google" button)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Context Management
    CONTEXT_WINDOW_MINUTES: int = 60

    class Config:
        # Look for .env in the server directory
        env_file = str(SERVER_DIR / '.env')
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = 'ignore'


# Global settings instance
settings = Settings()
