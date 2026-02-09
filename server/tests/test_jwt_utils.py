"""Tests for JWT token generation and decoding."""
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from utils.jwt_utils import generate_access_token, decode_access_token, generate_refresh_token


# Use a fixed secret for deterministic tests
TEST_JWT_SECRET = "test-secret-key-for-unit-tests"
TEST_JWT_ALGO = "HS256"


@pytest.fixture(autouse=True)
def _mock_settings():
    with patch("utils.jwt_utils.settings") as mock:
        mock.JWT_SECRET_KEY = TEST_JWT_SECRET
        mock.JWT_ALGORITHM = TEST_JWT_ALGO
        mock.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        yield mock


class TestGenerateAccessToken:
    def test_returns_string(self):
        token = generate_access_token(uuid4())
        assert isinstance(token, str)
        assert len(token) > 10

    def test_decodes_correctly(self):
        uid = uuid4()
        token = generate_access_token(uid)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["user_id"] == str(uid)
        assert payload["type"] == "access"

    def test_contains_iat_and_exp(self):
        token = generate_access_token(uuid4())
        payload = decode_access_token(token)
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_exp_is_30_minutes_ahead(self):
        uid = uuid4()
        before = datetime.now(timezone.utc)
        token = generate_access_token(uid)
        payload = decode_access_token(token)
        # exp should be approximately 30 minutes after iat
        diff = payload["exp"] - payload["iat"]
        assert diff == 30 * 60  # 1800 seconds


class TestDecodeAccessToken:
    def test_invalid_token_returns_none(self):
        assert decode_access_token("not-a-jwt") is None

    def test_wrong_secret_returns_none(self):
        token = generate_access_token(uuid4())
        with patch("utils.jwt_utils.settings") as mock:
            mock.JWT_SECRET_KEY = "wrong-secret"
            mock.JWT_ALGORITHM = TEST_JWT_ALGO
            assert decode_access_token(token) is None

    def test_expired_token_returns_none(self):
        import jwt
        payload = {
            "user_id": str(uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "type": "access",
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGO)
        assert decode_access_token(token) is None

    def test_wrong_type_returns_none(self):
        """Token with type != 'access' should be rejected."""
        import jwt
        payload = {
            "user_id": str(uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGO)
        assert decode_access_token(token) is None


class TestGenerateRefreshToken:
    def test_returns_string(self):
        token = generate_refresh_token()
        assert isinstance(token, str)

    def test_unique(self):
        tokens = {generate_refresh_token() for _ in range(50)}
        assert len(tokens) == 50  # All unique

    def test_sufficient_entropy(self):
        token = generate_refresh_token()
        assert len(token) >= 32
