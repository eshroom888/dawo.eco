"""Tests for CalendarCredentialsManager.

Story 7-9: Google Calendar Sync
Task 1.4: Config + credentials tests (target: 10+)
"""

import json
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, mock_open, patch

import pytest

from core.config import CalendarConfig, get_config, reload_config
from integrations.google_calendar.credentials_manager import (
    CalendarAuthError,
    CalendarCredentialsManager,
    CalendarSyncError,
)


# === CalendarConfig Tests ===


class TestCalendarConfig:
    """Tests for CalendarConfig frozen dataclass."""

    def test_frozen_immutability(self) -> None:
        """CalendarConfig is frozen — cannot mutate fields."""
        config = CalendarConfig()
        with pytest.raises(FrozenInstanceError):
            config.sync_enabled = False  # type: ignore[misc]

    def test_default_max_title_length(self) -> None:
        """Default max_title_length is 60."""
        config = CalendarConfig()
        assert config.max_title_length == 60

    def test_default_calendar_name(self) -> None:
        """Default calendar_name is 'DAWO Content Schedule'."""
        config = CalendarConfig()
        assert config.calendar_name == "DAWO Content Schedule"

    def test_default_scopes(self) -> None:
        """Default scopes include calendar scope."""
        config = CalendarConfig()
        assert "https://www.googleapis.com/auth/calendar" in config.scopes

    def test_default_color_ids(self) -> None:
        """Default color_ids map status to Google Calendar colors."""
        config = CalendarConfig()
        assert config.color_ids == {
            "scheduled": "10",
            "published": "9",
            "failed": "11",
        }

    def test_calendar_id_empty_by_default(self) -> None:
        """Calendar ID is empty by default (populated at runtime)."""
        config = CalendarConfig()
        assert config.calendar_id == ""

    def test_custom_values(self) -> None:
        """CalendarConfig accepts custom values."""
        config = CalendarConfig(
            token_path="/custom/token.json",
            calendar_name="Custom Calendar",
            max_title_length=100,
            sync_enabled=False,
        )
        assert config.token_path == "/custom/token.json"
        assert config.calendar_name == "Custom Calendar"
        assert config.max_title_length == 100
        assert config.sync_enabled is False

    def test_in_get_config_return(self) -> None:
        """CalendarConfig is accessible via get_config().calendar."""
        reload_config()
        config = get_config()
        assert hasattr(config, "calendar")
        assert isinstance(config.calendar, CalendarConfig)


# === CalendarCredentialsManager Tests ===


class TestCalendarCredentialsManager:
    """Tests for CalendarCredentialsManager."""

    def _make_config(self, **overrides) -> CalendarConfig:
        """Create CalendarConfig with optional overrides."""
        defaults = {
            "token_path": "credentials/calendar_token.json",
            "credentials_path": "credentials/google-oauth.json",
            "scopes": ("https://www.googleapis.com/auth/calendar",),
        }
        defaults.update(overrides)
        return CalendarConfig(**defaults)

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    def test_get_credentials_loads_token(self, mock_from_file: MagicMock) -> None:
        """get_credentials loads token from configured path."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_from_file.return_value = mock_creds

        config = self._make_config()
        manager = CalendarCredentialsManager(config)
        result = manager.get_credentials()

        mock_from_file.assert_called_once_with(
            config.token_path, list(config.scopes)
        )
        assert result == mock_creds

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    @patch("integrations.google_calendar.credentials_manager.Request")
    def test_get_credentials_refreshes_expired_token(
        self, mock_request_cls: MagicMock, mock_from_file: MagicMock
    ) -> None:
        """get_credentials auto-refreshes expired token."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token"
        mock_from_file.return_value = mock_creds

        # After refresh, creds become valid
        def refresh_side_effect(request):
            mock_creds.valid = True

        mock_creds.refresh.side_effect = refresh_side_effect

        config = self._make_config()
        manager = CalendarCredentialsManager(config)

        with patch("builtins.open", mock_open()):
            result = manager.get_credentials()

        mock_creds.refresh.assert_called_once()
        assert result == mock_creds

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    def test_get_credentials_raises_on_missing_token(
        self, mock_from_file: MagicMock
    ) -> None:
        """get_credentials raises CalendarAuthError if token file missing."""
        mock_from_file.side_effect = FileNotFoundError("Not found")

        config = self._make_config()
        manager = CalendarCredentialsManager(config)

        with pytest.raises(CalendarAuthError, match="Token file not found"):
            manager.get_credentials()

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    def test_get_credentials_raises_on_invalid_token(
        self, mock_from_file: MagicMock
    ) -> None:
        """get_credentials raises CalendarAuthError on invalid token data."""
        mock_from_file.side_effect = ValueError("Invalid JSON")

        config = self._make_config()
        manager = CalendarCredentialsManager(config)

        with pytest.raises(CalendarAuthError, match="Failed to load credentials"):
            manager.get_credentials()

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    def test_get_credentials_raises_no_refresh_token(
        self, mock_from_file: MagicMock
    ) -> None:
        """get_credentials raises CalendarAuthError when no refresh token."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.refresh_token = None
        mock_from_file.return_value = mock_creds

        config = self._make_config()
        manager = CalendarCredentialsManager(config)

        with pytest.raises(CalendarAuthError, match="No refresh token"):
            manager.get_credentials()

    @patch(
        "integrations.google_calendar.credentials_manager.build"
    )
    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    def test_get_service_returns_resource(
        self, mock_from_file: MagicMock, mock_build: MagicMock
    ) -> None:
        """get_service returns Google Calendar API service resource."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_from_file.return_value = mock_creds

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        config = self._make_config()
        manager = CalendarCredentialsManager(config)
        result = manager.get_service()

        mock_build.assert_called_once_with("calendar", "v3", credentials=mock_creds)
        assert result == mock_service

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    def test_is_authenticated_valid_token(self, mock_from_file: MagicMock) -> None:
        """is_authenticated returns True for valid token."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_from_file.return_value = mock_creds

        config = self._make_config()
        manager = CalendarCredentialsManager(config)
        assert manager.is_authenticated() is True

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    def test_is_authenticated_expired_refreshable(
        self, mock_from_file: MagicMock
    ) -> None:
        """is_authenticated returns True for expired token with refresh_token."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token"
        mock_from_file.return_value = mock_creds

        config = self._make_config()
        manager = CalendarCredentialsManager(config)
        assert manager.is_authenticated() is True

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    def test_is_authenticated_missing_file(self, mock_from_file: MagicMock) -> None:
        """is_authenticated returns False when token file missing."""
        mock_from_file.side_effect = FileNotFoundError()

        config = self._make_config()
        manager = CalendarCredentialsManager(config)
        assert manager.is_authenticated() is False

    @patch(
        "integrations.google_calendar.credentials_manager.Credentials.from_authorized_user_file"
    )
    @patch("integrations.google_calendar.credentials_manager.Request")
    def test_refresh_failure_raises_auth_error(
        self, mock_request_cls: MagicMock, mock_from_file: MagicMock
    ) -> None:
        """CalendarAuthError raised when token refresh fails."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.refresh_token = "refresh-token"
        mock_creds.refresh.side_effect = Exception("Network error")
        mock_from_file.return_value = mock_creds

        config = self._make_config()
        manager = CalendarCredentialsManager(config)

        with pytest.raises(CalendarAuthError, match="Token refresh failed"):
            manager.get_credentials()


class TestCalendarSyncError:
    """Tests for CalendarSyncError exception."""

    def test_sync_error_is_exception(self) -> None:
        """CalendarSyncError is a proper Exception subclass."""
        error = CalendarSyncError("Sync failed")
        assert isinstance(error, Exception)
        assert str(error) == "Sync failed"
