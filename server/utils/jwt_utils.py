"""JWT token utilities"""
import jwt
from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional
from config.settings import settings
import secrets
import logging

logger = logging.getLogger(__name__)


def generate_access_token(user_id: UUID) -> str:
    """Generate JWT access token"""
    payload = {
        'user_id': str(user_id),
        'exp': datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        'iat': datetime.utcnow(),
        'type': 'access'
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return token


def generate_refresh_token() -> str:
    """Generate secure refresh token"""
    return secrets.token_urlsafe(32)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate access token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get('type') != 'access':
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
