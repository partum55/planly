"""Health check routes"""
from fastapi import APIRouter, HTTPException
from database.client import get_supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "ok", "service": "planly-api"}


@router.get("/health/db")
async def database_health():
    """Check database connectivity and schema"""
    try:
        supabase = get_supabase()

        # Try to query users table
        try:
            response = supabase.table('users').select('id').limit(1).execute()
            users_table_exists = True
            users_count = len(response.data) if response.data else 0
        except Exception as e:
            users_table_exists = False
            users_count = 0
            logger.error(f"Users table error: {e}")

        # Try to query conversations table
        try:
            response = supabase.table('conversations').select('id').limit(1).execute()
            conversations_table_exists = True
        except Exception as e:
            conversations_table_exists = False
            logger.error(f"Conversations table error: {e}")

        # Check if schema is set up
        schema_ready = users_table_exists and conversations_table_exists

        return {
            "status": "ok" if schema_ready else "degraded",
            "database": {
                "connected": True,
                "schema_ready": schema_ready,
                "tables": {
                    "users": users_table_exists,
                    "conversations": conversations_table_exists
                },
                "users_count": users_count
            },
            "message": "Database schema ready" if schema_ready else "Database tables not found. Please run server/database/supabase_schema.sql"
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "database": {
                "connected": False,
                "error": str(e)
            },
            "message": "Database connection failed. Check SUPABASE_URL and SUPABASE_KEY in .env"
        }
