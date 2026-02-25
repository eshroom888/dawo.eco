"""Tests for Gmail Credentials Manager.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 2: Gmail Credentials Manager
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from teams.dawo.leads.gmail.credentials_manager import (
    GmailCredentialsManager,
    GmailAuthError,
)
from teams.dawo.leads.gmail.config import GmailConfig


@pytest.fixture
def gmail_config() -> GmailConfig:
    """Provide Gmail config for testing."""
    return GmailConfig(
        token_path="credentials/gmail_token.json",
        credentials_path="credentials/gmail_credentials.json",
        sender_email="test@dawo.no",
    )


@pytest.fixture
def mock_valid_credentials() -> MagicMock:
    """Provide mock valid credentials."""
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "refresh_token_123"
    return creds


@pytest.fixture
def mock_expired_credentials() -> MagicMock:
    """Provide mock expired credentials with refresh token."""
    creds = MagicMock()
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "refresh_token_123"
    return creds


class TestGmailCredentialsManager:
    """Tests for GmailCredentialsManager."""

    def test_init_with_config(
        self, gmail_config: GmailConfig
    ) -> None:
        """Test initialization accepts GmailConfig via injection."""
        manager = GmailCredentialsManager(
            config=gmail_config,
        )
        assert manager._config == gmail_config

    @patch("teams.dawo.leads.gmail.credentials_manager.Credentials")
    def test_get_credentials_valid(
        self,
        mock_creds_class: MagicMock,
        gmail_config: GmailConfig,
        mock_valid_credentials: MagicMock,
    ) -> None:
        """Test get_credentials returns valid credentials."""
        mock_creds_class.from_authorized_user_file.return_value = mock_valid_credentials

        manager = GmailCredentialsManager(
            config=gmail_config,
        )
        creds = manager.get_credentials()

        assert creds == mock_valid_credentials
        mock_creds_class.from_authorized_user_file.assert_called_once_with(
            gmail_config.token_path, gmail_config.scopes
        )

    @patch("teams.dawo.leads.gmail.credentials_manager.Credentials")
    def test_get_credentials_missing_token_raises(
        self,
        mock_creds_class: MagicMock,
        gmail_config: GmailConfig,
    ) -> None:
        """Test get_credentials raises GmailAuthError on missing token."""
        mock_creds_class.from_authorized_user_file.side_effect = FileNotFoundError(
            "Token not found"
        )

        manager = GmailCredentialsManager(
            config=gmail_config,
        )
        with pytest.raises(GmailAuthError, match="Token file not found"):
            manager.get_credentials()

    @patch("teams.dawo.leads.gmail.credentials_manager.Request")
    @patch("teams.dawo.leads.gmail.credentials_manager.Credentials")
    def test_refresh_if_needed_refreshes_expired(
        self,
        mock_creds_class: MagicMock,
        mock_request_class: MagicMock,
        gmail_config: GmailConfig,
        mock_expired_credentials: MagicMock,
    ) -> None:
        """Test refresh_if_needed refreshes expired credentials."""
        mock_creds_class.from_authorized_user_file.return_value = mock_expired_credentials

        manager = GmailCredentialsManager(
            config=gmail_config,
        )
        creds = manager.refresh_if_needed(mock_expired_credentials)

        mock_expired_credentials.refresh.assert_called_once()

    @patch("teams.dawo.leads.gmail.credentials_manager.Credentials")
    def test_refresh_if_needed_no_refresh_token_raises(
        self,
        mock_creds_class: MagicMock,
        gmail_config: GmailConfig,
    ) -> None:
        """Test refresh_if_needed raises when no refresh token."""
        creds = MagicMock()
        creds.valid = False
        creds.expired = True
        creds.refresh_token = None

        manager = GmailCredentialsManager(
            config=gmail_config,
        )
        with pytest.raises(GmailAuthError, match="No refresh token"):
            manager.refresh_if_needed(creds)

    @patch("teams.dawo.leads.gmail.credentials_manager.Credentials")
    def test_is_authenticated_valid(
        self,
        mock_creds_class: MagicMock,
        gmail_config: GmailConfig,
        mock_valid_credentials: MagicMock,
    ) -> None:
        """Test is_authenticated returns True for valid credentials."""
        mock_creds_class.from_authorized_user_file.return_value = mock_valid_credentials

        manager = GmailCredentialsManager(
            config=gmail_config,
        )
        assert manager.is_authenticated() is True

    @patch("teams.dawo.leads.gmail.credentials_manager.Credentials")
    def test_is_authenticated_missing_token(
        self,
        mock_creds_class: MagicMock,
        gmail_config: GmailConfig,
    ) -> None:
        """Test is_authenticated returns False when token is missing."""
        mock_creds_class.from_authorized_user_file.side_effect = FileNotFoundError()

        manager = GmailCredentialsManager(
            config=gmail_config,
        )
        assert manager.is_authenticated() is False

    @patch("teams.dawo.leads.gmail.credentials_manager.Request")
    @patch("teams.dawo.leads.gmail.credentials_manager.Credentials")
    def test_refresh_failure_raises_auth_error(
        self,
        mock_creds_class: MagicMock,
        mock_request_class: MagicMock,
        gmail_config: GmailConfig,
        mock_expired_credentials: MagicMock,
    ) -> None:
        """Test refresh failure raises GmailAuthError."""
        mock_expired_credentials.refresh.side_effect = Exception("Refresh failed")

        manager = GmailCredentialsManager(
            config=gmail_config,
        )
        with pytest.raises(GmailAuthError, match="Token refresh failed"):
            manager.refresh_if_needed(mock_expired_credentials)

    def test_never_hardcodes_credential_paths(
        self, gmail_config: GmailConfig
    ) -> None:
        """Test that credential paths come from config, not hardcoded."""
        custom_config = GmailConfig(
            token_path="/custom/path/token.json",
            credentials_path="/custom/path/creds.json",
        )
        manager = GmailCredentialsManager(
            config=custom_config,
        )
        assert manager._config.token_path == "/custom/path/token.json"
        assert manager._config.credentials_path == "/custom/path/creds.json"
