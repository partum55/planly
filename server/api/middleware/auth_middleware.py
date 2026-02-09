"""Authentication middleware for JWT validation with TTL-cached user lookups."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID
from typing import Optional
import logging
import time

from utils.jwt_utils import decode_access_token
from database.client import get_supabase
from database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Simple TTL cache for user lookups to avoid a DB round-trip on every request.
# The JWT already guarantees identity; this check is only to verify is_active
# and existence, which change rarely.
_USER_CACHE: dict[str, tuple[dict, float]] = {}
_USER_CACHE_TTL_S = 60  # seconds
_USER_CACHE_MAX = 5_000


def _get_cached_user(user_id: str) -> Optional[dict]:
    entry = _USER_CACHE.get(user_id)
    if entry is None:
        return None
    user, ts = entry
    if time.time() - ts > _USER_CACHE_TTL_S:
        del _USER_CACHE[user_id]
        return None
    return user


def _set_cached_user(user_id: str, user: dict) -> None:
    # Evict oldest entries if cache is too large
    if len(_USER_CACHE) >= _USER_CACHE_MAX:
        oldest_key = min(_USER_CACHE, key=lambda k: _USER_CACHE[k][1])
        del _USER_CACHE[oldest_key]
    _USER_CACHE[user_id] = (user, time.time())


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate JWT and return current user.

    Uses a short-lived in-memory cache to avoid querying the database
    on every single authenticated request.

    Raises HTTPException if token is invalid or expired.
    """
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Check TTL cache first
    user = _get_cached_user(user_id)
    if user is None:
        # Cache miss — fetch from database
        supabase = get_supabase()
        user_repo = UserRepository(supabase)
        user = await user_repo.get_by_id(UUID(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        _set_cached_user(user_id, user)

    if not user.get('is_active'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """Get current user if token provided, otherwise return None"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
