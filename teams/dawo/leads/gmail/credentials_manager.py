"""Gmail OAuth2 Credentials Manager.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Manages Gmail API OAuth2 credentials:
- Load token from file
- Auto-refresh expired tokens
- Validate credential state

Configuration is injected via GmailConfig — NEVER hardcode paths.
"""

import logging
from typing import Protocol, runtime_checkable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from teams.dawo.leads.gmail.config import GmailConfig

logger = logging.getLogger(__name__)


class GmailAuthError(Exception):
    """Raised when Gmail authentication fails."""

    pass


@runtime_checkable
class DiscordAlertProtocol(Protocol):
    """Protocol for Discord alert integration."""

    async def send_api_error_alert(
        self,
        api_name: str,
        error: str,
        attempts: int,
        queued_for_retry: bool,
    ) -> bool:
        """Send an API error alert."""
        ...


class GmailCredentialsManager:
    """Manages Gmail API OAuth2 credentials.

    Loads, validates, and refreshes OAuth2 tokens for Gmail API access.
    All paths come from injected GmailConfig — never hardcoded.

    Attributes:
        _config: Gmail configuration (injected)
    """

    def __init__(
        self,
        config: GmailConfig,
    ) -> None:
        """Initialize with injected configuration.

        Args:
            config: Gmail API configuration
        """
        self._config = config

    def get_credentials(self) -> Credentials:
        """Load and return valid credentials.

        Loads token from configured path. If expired, attempts refresh.

        Returns:
            Valid Google OAuth2 Credentials

        Raises:
            GmailAuthError: If token file missing or invalid
        """
        try:
            creds = Credentials.from_authorized_user_file(
                self._config.token_path, self._config.scopes
            )
        except FileNotFoundError:
            logger.error(f"Gmail token file not found: {self._config.token_path}")
            raise GmailAuthError(
                f"Token file not found: {self._config.token_path}"
            )
        except Exception as e:
            logger.error(f"Failed to load Gmail credentials: {e}")
            raise GmailAuthError(f"Failed to load credentials: {e}")

        if not creds.valid:
            creds = self.refresh_if_needed(creds)

        return creds

    def is_authenticated(self) -> bool:
        """Check if valid credentials are available.

        Returns:
            True if token exists and is valid or refreshable
        """
        try:
            creds = Credentials.from_authorized_user_file(
                self._config.token_path, self._config.scopes
            )
            return creds.valid or (creds.expired and creds.refresh_token is not None)
        except (FileNotFoundError, Exception):
            return False

    def refresh_if_needed(self, creds: Credentials) -> Credentials:
        """Refresh credentials if expired.

        Args:
            creds: Potentially expired credentials

        Returns:
            Refreshed credentials

        Raises:
            GmailAuthError: If refresh fails or no refresh token
        """
        if creds.valid:
            return creds

        if not creds.refresh_token:
            logger.error("No refresh token available for Gmail credentials")
            raise GmailAuthError(
                "No refresh token available. Re-authenticate Gmail API."
            )

        try:
            creds.refresh(Request())
            self._save_token(creds)
            logger.info("Gmail token refreshed successfully")
            return creds
        except Exception as e:
            logger.error(f"Gmail token refresh failed: {e}")
            raise GmailAuthError(f"Token refresh failed: {e}")

    def _save_token(self, creds: Credentials) -> None:
        """Save refreshed token to file.

        Args:
            creds: Refreshed credentials to save
        """
        try:
            with open(self._config.token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            logger.debug(f"Gmail token saved to {self._config.token_path}")
        except Exception as e:
            logger.warning(f"Failed to save Gmail token: {e}")


__all__ = [
    "GmailCredentialsManager",
    "GmailAuthError",
    "DiscordAlertProtocol",
]
