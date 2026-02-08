"""Supabase database client"""
from supabase import create_client, Client
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

_supabase_client: Client = None


def init_supabase() -> Client:
    """Initialize Supabase client"""
    global _supabase_client

    if _supabase_client is None:
        logger.info("Initializing Supabase client...")
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        logger.info("✓ Supabase client initialized")

    return _supabase_client


def get_supabase() -> Client:
    """Get Supabase client instance"""
    if _supabase_client is None:
        return init_supabase()
    return _supabase_client
