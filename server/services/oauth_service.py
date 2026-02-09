"""OAuth service for Google authentication"""
import httpx
from typing import Dict, Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Handle Google OAuth2 authentication"""

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL

        Args:
            redirect_uri: Where Google should redirect after auth
            state: Optional state parameter for CSRF protection

        Returns:
            Full authorization URL for user to visit
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
        }

        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str
    ) -> Dict[str, str]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            code: Authorization code from Google
            redirect_uri: Same redirect_uri used in authorization request

        Returns:
            Dict with access_token, refresh_token (if available), expires_in, etc.

        Raises:
            Exception if exchange fails
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")

        token_data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.GOOGLE_TOKEN_URL, data=token_data)
                response.raise_for_status()
                tokens = response.json()

                logger.info("Successfully exchanged Google OAuth code for tokens")
                return tokens

        except httpx.HTTPStatusError as e:
            logger.error(f"Google token exchange failed: {e.response.text}")
            raise Exception(f"Failed to exchange authorization code: {e.response.text}")
        except Exception as e:
            logger.error(f"Google token exchange error: {e}")
            raise

    async def get_user_info(self, access_token: str) -> Dict[str, any]:
        """
        Get user information from Google using access token

        Args:
            access_token: Google access token

        Returns:
            Dict with user info (email, name, picture, etc.)

        Raises:
            Exception if request fails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(self.GOOGLE_USERINFO_URL, headers=headers)
                response.raise_for_status()
                user_info = response.json()

                logger.info(f"Retrieved Google user info for: {user_info.get('email')}")
                return user_info

        except httpx.HTTPStatusError as e:
            logger.error(f"Google userinfo request failed: {e.response.text}")
            raise Exception(f"Failed to get user info: {e.response.text}")
        except Exception as e:
            logger.error(f"Google userinfo error: {e}")
            raise

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a Google access or refresh token

        Args:
            token: Access or refresh token to revoke

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.GOOGLE_REVOKE_URL,
                    data={"token": token}
                )
                response.raise_for_status()

                logger.info("Successfully revoked Google token")
                return True

        except Exception as e:
            logger.error(f"Failed to revoke Google token: {e}")
            return False

    async def authenticate_user(
        self,
        code: str,
        redirect_uri: str
    ) -> Dict[str, any]:
        """
        Complete OAuth flow: exchange code for tokens and get user info

        Args:
            code: Authorization code from Google
            redirect_uri: Same redirect_uri used in authorization request

        Returns:
            Dict with user_info and tokens

        Raises:
            Exception if authentication fails
        """
        # Exchange code for tokens
        tokens = await self.exchange_code_for_tokens(code, redirect_uri)

        # Get user info
        user_info = await self.get_user_info(tokens['access_token'])

        return {
            "user_info": user_info,
            "tokens": tokens
        }

    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured"""
        return bool(self.client_id and self.client_secret)
