"""Google Calendar OAuth2 Credentials Manager.

Story 7-9: Google Calendar Sync
Task 1.3: CalendarCredentialsManager

Manages Google Calendar API OAuth2 credentials:
- Load token from file
- Auto-refresh expired tokens
- Build Calendar API service resource
- Validate credential state

Configuration is injected via CalendarConfig — NEVER hardcode paths.
Follows EXACT pattern from teams/dawo/leads/gmail/credentials_manager.py.
"""

import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource

from core.config import CalendarConfig

logger = logging.getLogger(__name__)


class CalendarAuthError(Exception):
    """Raised when Google Calendar authentication fails."""

    pass


class CalendarSyncError(Exception):
    """Raised when a Google Calendar sync operation fails."""

    pass


class CalendarCredentialsManager:
    """Manages Google Calendar API OAuth2 credentials.

    Loads, validates, and refreshes OAuth2 tokens for Calendar API access.
    All paths come from injected CalendarConfig — never hardcoded.

    Attributes:
        _config: Calendar configuration (injected)
    """

    def __init__(self, config: CalendarConfig) -> None:
        """Initialize with injected configuration.

        Args:
            config: Calendar API configuration
        """
        self._config = config

    def get_credentials(self) -> Credentials:
        """Load and return valid credentials.

        Loads token from configured path. If expired, attempts refresh.

        Returns:
            Valid Google OAuth2 Credentials

        Raises:
            CalendarAuthError: If token file missing or invalid
        """
        try:
            creds = Credentials.from_authorized_user_file(
                self._config.token_path, list(self._config.scopes)
            )
        except FileNotFoundError:
            logger.error(f"Calendar token file not found: {self._config.token_path}")
            raise CalendarAuthError(
                f"Token file not found: {self._config.token_path}"
            )
        except Exception as e:
            logger.error(f"Failed to load Calendar credentials: {e}")
            raise CalendarAuthError(f"Failed to load credentials: {e}")

        if not creds.valid:
            creds = self._refresh_if_needed(creds)

        return creds

    def get_service(self) -> Resource:
        """Build and return Google Calendar API service resource.

        Returns:
            Google Calendar API service (v3)

        Raises:
            CalendarAuthError: If credentials are invalid
        """
        creds = self.get_credentials()
        return build("calendar", "v3", credentials=creds)

    def is_authenticated(self) -> bool:
        """Check if valid credentials are available.

        Returns:
            True if token exists and is valid or refreshable
        """
        try:
            creds = Credentials.from_authorized_user_file(
                self._config.token_path, list(self._config.scopes)
            )
            return creds.valid or (creds.expired and creds.refresh_token is not None)
        except (FileNotFoundError, Exception):
            return False

    def _refresh_if_needed(self, creds: Credentials) -> Credentials:
        """Refresh credentials if expired.

        Args:
            creds: Potentially expired credentials

        Returns:
            Refreshed credentials

        Raises:
            CalendarAuthError: If refresh fails or no refresh token
        """
        if creds.valid:
            return creds

        if not creds.refresh_token:
            logger.error("No refresh token available for Calendar credentials")
            raise CalendarAuthError(
                "No refresh token available. Re-authenticate Calendar API."
            )

        try:
            creds.refresh(Request())
            self._save_token(creds)
            logger.info("Calendar token refreshed successfully")
            return creds
        except Exception as e:
            logger.error(f"Calendar token refresh failed: {e}")
            raise CalendarAuthError(f"Token refresh failed: {e}")

    def _save_token(self, creds: Credentials) -> None:
        """Save refreshed token to file.

        Args:
            creds: Refreshed credentials to save
        """
        try:
            with open(self._config.token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            logger.debug(f"Calendar token saved to {self._config.token_path}")
        except Exception as e:
            logger.warning(f"Failed to save Calendar token: {e}")


__all__ = [
    "CalendarCredentialsManager",
    "CalendarAuthError",
    "CalendarSyncError",
]
