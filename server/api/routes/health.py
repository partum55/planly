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

        # Verify core tables are reachable (details logged server-side only)
        tables_ok = True
        for table in ("users", "conversations"):
            try:
                supabase.table(table).select("id").limit(1).execute()
            except Exception as e:
                tables_ok = False
                logger.error(f"Table check failed for '{table}': {e}")

        return {
            "status": "ok" if tables_ok else "degraded",
            "database_connected": True,
            "schema_ready": tables_ok,
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "database_connected": False,
            "schema_ready": False,
        }
