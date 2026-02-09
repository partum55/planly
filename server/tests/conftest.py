"""Shared test fixtures and configuration."""
import sys
import os

# Ensure the server package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required environment variables BEFORE any application module is imported.
# These are dummy values used only in tests — no real connections are made.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key-for-unit-tests")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-unit-tests")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-webhook-secret-for-unit-tests")
