"""Tests for Gmail configuration.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 1: Module structure - config
"""

import pytest

from teams.dawo.leads.gmail.config import GmailConfig, GmailRateLimitConfig


class TestGmailConfig:
    """Tests for GmailConfig dataclass."""

    def test_default_config(self) -> None:
        """Test GmailConfig default values."""
        config = GmailConfig()
        assert config.token_path == "credentials/gmail_token.json"
        assert config.credentials_path == "credentials/gmail_credentials.json"
        assert config.scopes == ["https://www.googleapis.com/auth/gmail.send"]
        assert config.sender_email == ""
        assert config.sender_name == "DAWO Team"
        assert config.sender_role == "B2B Sales"
        assert config.company_name == "ImagoEco AS"
        assert config.company_address == ""

    def test_custom_config(self) -> None:
        """Test GmailConfig with custom values."""
        config = GmailConfig(
            token_path="/custom/token.json",
            credentials_path="/custom/creds.json",
            sender_email="sales@dawo.no",
            company_address="Oslo, Norway",
        )
        assert config.token_path == "/custom/token.json"
        assert config.credentials_path == "/custom/creds.json"
        assert config.sender_email == "sales@dawo.no"
        assert config.company_address == "Oslo, Norway"

    def test_config_is_frozen(self) -> None:
        """Test GmailConfig is immutable."""
        config = GmailConfig()
        with pytest.raises(AttributeError):
            config.sender_email = "new@email.com"  # type: ignore[misc]


class TestGmailRateLimitConfig:
    """Tests for GmailRateLimitConfig dataclass."""

    def test_default_rate_limit_config(self) -> None:
        """Test GmailRateLimitConfig default values."""
        config = GmailRateLimitConfig()
        assert config.max_per_minute == 20
        assert config.max_per_day == 500
        assert config.burst_size == 5
        assert config.business_hours_start == 8
        assert config.business_hours_end == 17
        assert config.timezone == "Europe/Oslo"

    def test_custom_rate_limit_config(self) -> None:
        """Test GmailRateLimitConfig with custom values."""
        config = GmailRateLimitConfig(
            max_per_minute=10,
            max_per_day=200,
            burst_size=3,
        )
        assert config.max_per_minute == 10
        assert config.max_per_day == 200
        assert config.burst_size == 3

    def test_rate_limit_config_is_frozen(self) -> None:
        """Test GmailRateLimitConfig is immutable."""
        config = GmailRateLimitConfig()
        with pytest.raises(AttributeError):
            config.max_per_minute = 10  # type: ignore[misc]
