"""Tests for AuthService — register, login, OAuth, and token refresh."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_repo():
    repo = MagicMock()
    # Make all methods async
    repo.get_by_email = AsyncMock(return_value=None)
    repo.create_user = AsyncMock(return_value={"id": str(uuid4()), "email": "a@b.com"})
    repo.create_session = AsyncMock()
    repo.update_last_login = AsyncMock()
    repo.get_session_by_token = AsyncMock()
    repo.link_telegram = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def auth_service(user_repo):
    return AuthService(user_repo)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegister:
    @pytest.mark.asyncio
    async def test_register_with_password(self, auth_service, user_repo):
        user, access, refresh = await auth_service.register_user("a@b.com", "password123")
        assert user["email"] == "a@b.com"
        assert isinstance(access, str)
        assert isinstance(refresh, str)
        # create_user called with a hash, not the raw password
        call_kwargs = user_repo.create_user.call_args.kwargs
        assert call_kwargs["password_hash"] is not None
        assert call_kwargs["password_hash"] != "password123"

    @pytest.mark.asyncio
    async def test_register_without_password_oauth(self, auth_service, user_repo):
        """OAuth users register without a password."""
        user, access, refresh = await auth_service.register_user(
            "o@auth.com", password=None, oauth_provider="google"
        )
        call_kwargs = user_repo.create_user.call_args.kwargs
        assert call_kwargs["password_hash"] is None
        assert call_kwargs["oauth_provider"] == "google"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = {"id": "existing"}
        with pytest.raises(ValueError, match="already exists"):
            await auth_service.register_user("dup@b.com", "pass")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_unknown_user_raises(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = None
        with pytest.raises(ValueError, match="Invalid email"):
            await auth_service.login_user("x@y.com", "pass")

    @pytest.mark.asyncio
    async def test_login_inactive_user_raises(self, auth_service, user_repo):
        user_repo.get_by_email.return_value = {"id": "u1", "is_active": False}
        with pytest.raises(ValueError, match="disabled"):
            await auth_service.login_user("x@y.com", "pass")

    @pytest.mark.asyncio
    async def test_login_oauth_user_no_password_raises(self, auth_service, user_repo):
        """OAuth-only user (no password_hash) must not be able to password-login."""
        user_repo.get_by_email.return_value = {
            "id": "u1",
            "is_active": True,
            "password_hash": None,
        }
        with pytest.raises(ValueError, match="OAuth"):
            await auth_service.login_user("x@y.com", "pass")

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(self, auth_service, user_repo):
        import bcrypt
        correct_hash = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()
        user_repo.get_by_email.return_value = {
            "id": str(uuid4()),
            "is_active": True,
            "password_hash": correct_hash,
        }
        with pytest.raises(ValueError, match="Invalid email"):
            await auth_service.login_user("x@y.com", "wrong")

    @pytest.mark.asyncio
    async def test_login_correct_password(self, auth_service, user_repo):
        import bcrypt
        correct_hash = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()
        uid = str(uuid4())
        user_repo.get_by_email.return_value = {
            "id": uid,
            "is_active": True,
            "password_hash": correct_hash,
        }
        user, access, refresh = await auth_service.login_user("x@y.com", "correct")
        assert user["id"] == uid


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_invalid_refresh_token_raises(self, auth_service, user_repo):
        user_repo.get_session_by_token.return_value = None
        with pytest.raises(ValueError, match="Invalid refresh token"):
            await auth_service.refresh_access_token("bad-token")

    @pytest.mark.asyncio
    async def test_expired_refresh_token_raises(self, auth_service, user_repo):
        user_repo.get_session_by_token.return_value = {
            "user_id": str(uuid4()),
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        }
        with pytest.raises(ValueError, match="expired"):
            await auth_service.refresh_access_token("expired-tok")

    @pytest.mark.asyncio
    async def test_valid_refresh_token(self, auth_service, user_repo):
        uid = str(uuid4())
        user_repo.get_session_by_token.return_value = {
            "user_id": uid,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }
        new_token = await auth_service.refresh_access_token("good-tok")
        assert isinstance(new_token, str)
        assert len(new_token) > 10


# ---------------------------------------------------------------------------
# Link Telegram
# ---------------------------------------------------------------------------

class TestLinkTelegram:
    @pytest.mark.asyncio
    async def test_link_telegram(self, auth_service, user_repo):
        uid = uuid4()
        result = await auth_service.link_telegram_account(uid, 12345, "johndoe")
        assert result is True
        user_repo.link_telegram.assert_awaited_once_with(
            user_id=uid,
            telegram_id=12345,
            telegram_username="johndoe",
        )
