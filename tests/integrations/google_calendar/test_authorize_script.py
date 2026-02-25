"""Tests for calendar authorization setup script.

Story 7-9, Task 8.2: Tests for scripts/authorize_calendar.py.
Target: 3+ tests.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGetCalendarCredentials:
    """Tests for get_calendar_credentials function."""

    def test_creates_token_via_oauth_flow(self, tmp_path):
        """Script runs OAuth flow and saves token when no token exists."""
        from scripts.authorize_calendar import SCOPES

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "test"}'

        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds

        with (
            patch(
                "scripts.authorize_calendar.TOKEN_PATH",
                tmp_path / "calendar_token.json",
            ),
            patch(
                "scripts.authorize_calendar.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            ),
        ):
            from scripts.authorize_calendar import get_calendar_credentials

            result = get_calendar_credentials()

        assert result == mock_creds
        mock_flow.run_local_server.assert_called_once_with(port=0)

    def test_refreshes_expired_token(self, tmp_path):
        """Script refreshes token when expired but has refresh_token."""
        token_file = tmp_path / "calendar_token.json"
        token_file.write_text('{"token": "old"}')

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_abc"
        mock_creds.to_json.return_value = '{"token": "refreshed"}'

        with (
            patch(
                "scripts.authorize_calendar.TOKEN_PATH", token_file,
            ),
            patch(
                "scripts.authorize_calendar.Credentials.from_authorized_user_file",
                return_value=mock_creds,
            ),
        ):
            from scripts.authorize_calendar import get_calendar_credentials

            result = get_calendar_credentials()

        mock_creds.refresh.assert_called_once()

    def test_handles_already_authenticated(self, tmp_path):
        """Script uses existing valid token without re-auth."""
        token_file = tmp_path / "calendar_token.json"
        token_file.write_text('{"token": "valid"}')

        mock_creds = MagicMock()
        mock_creds.valid = True

        with (
            patch(
                "scripts.authorize_calendar.TOKEN_PATH", token_file,
            ),
            patch(
                "scripts.authorize_calendar.Credentials.from_authorized_user_file",
                return_value=mock_creds,
            ),
        ):
            from scripts.authorize_calendar import get_calendar_credentials

            result = get_calendar_credentials()

        assert result == mock_creds
        # No refresh or OAuth flow needed
        mock_creds.refresh.assert_not_called()


class TestVerifyCalendarAccess:
    """Tests for verify_calendar_access function."""

    def test_verifies_with_api_call(self):
        """Script verifies token by listing calendars."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expiry = "2026-12-31"

        mock_service = MagicMock()
        mock_calendar_list = {
            "items": [
                {"summary": "Primary", "id": "primary", "primary": True},
                {"summary": "DAWO Content Schedule", "id": "cal_123"},
            ]
        }
        mock_service.calendarList().list().execute.return_value = mock_calendar_list

        with patch(
            "scripts.authorize_calendar.build", return_value=mock_service
        ):
            from scripts.authorize_calendar import verify_calendar_access

            result = verify_calendar_access(mock_creds)

        assert result is True
