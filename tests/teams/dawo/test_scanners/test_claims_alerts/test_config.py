"""Tests for ClaimsAlertConfig.

Story 6-4, Task 1: Config validation tests.
"""

import pytest

from teams.dawo.scanners.claims_alerts.config import (
    ClaimsAlertConfig,
    build_claims_alert_config,
)


class TestClaimsAlertConfig:
    """Tests for ClaimsAlertConfig frozen dataclass."""

    def test_valid_config_creation(self) -> None:
        """Valid config creates without error."""
        config = ClaimsAlertConfig(
            enabled=True,
            webhook_url="https://discord.com/api/webhooks/test/test",
            batch_window_seconds=300,
            dawo_product_keywords=("lion's mane", "chaga"),
        )
        assert config.enabled is True
        assert config.webhook_url == "https://discord.com/api/webhooks/test/test"
        assert config.batch_window_seconds == 300
        assert config.dawo_product_keywords == ("lion's mane", "chaga")

    def test_frozen_immutability(self) -> None:
        """Config is frozen — cannot mutate."""
        config = ClaimsAlertConfig(
            webhook_url="https://discord.com/api/webhooks/test/test",
            dawo_product_keywords=("chaga",),
        )
        with pytest.raises(AttributeError):
            config.enabled = False  # type: ignore[misc]

    def test_empty_webhook_url_when_enabled_raises(self) -> None:
        """Empty webhook_url when enabled raises ValueError."""
        with pytest.raises(ValueError, match="webhook_url must not be empty"):
            ClaimsAlertConfig(
                enabled=True,
                webhook_url="",
                dawo_product_keywords=("chaga",),
            )

    def test_empty_webhook_url_when_disabled_ok(self) -> None:
        """Empty webhook_url when disabled is allowed."""
        config = ClaimsAlertConfig(
            enabled=False,
            webhook_url="",
            dawo_product_keywords=("chaga",),
        )
        assert config.enabled is False

    def test_empty_product_keywords_raises(self) -> None:
        """Empty dawo_product_keywords raises ValueError."""
        with pytest.raises(ValueError, match="dawo_product_keywords must not be empty"):
            ClaimsAlertConfig(
                webhook_url="https://discord.com/api/webhooks/test/test",
                dawo_product_keywords=(),
            )

    def test_zero_batch_window_raises(self) -> None:
        """Zero batch_window_seconds raises ValueError."""
        with pytest.raises(ValueError, match="batch_window_seconds must be positive"):
            ClaimsAlertConfig(
                webhook_url="https://discord.com/api/webhooks/test/test",
                dawo_product_keywords=("chaga",),
                batch_window_seconds=0,
            )

    def test_negative_batch_window_raises(self) -> None:
        """Negative batch_window_seconds raises ValueError."""
        with pytest.raises(ValueError, match="batch_window_seconds must be positive"):
            ClaimsAlertConfig(
                webhook_url="https://discord.com/api/webhooks/test/test",
                dawo_product_keywords=("chaga",),
                batch_window_seconds=-1,
            )

    def test_default_values(self) -> None:
        """Default values are correct."""
        config = ClaimsAlertConfig(
            webhook_url="https://discord.com/api/webhooks/test/test",
            dawo_product_keywords=("chaga",),
        )
        assert config.enabled is True
        assert config.batch_window_seconds == 300
        assert config.dashboard_url == ""
        assert config.max_retry_attempts == 5
        assert config.backoff_schedule == (60, 300, 900, 3600)
        assert config.severity_emoji_map == {}


class TestBuildClaimsAlertConfig:
    """Tests for build_claims_alert_config builder function."""

    def test_build_from_json_data(self) -> None:
        """Build config from parsed JSON dict."""
        data = {
            "enabled": True,
            "webhook_url": "https://discord.com/api/webhooks/test/test",
            "batch_window_seconds": 300,
            "dashboard_url": "https://app.imagoeco.com/dawo/regulatory",
            "max_retry_attempts": 5,
            "backoff_schedule": [60, 300, 900, 3600],
            "dawo_product_keywords": ["lion's mane", "chaga", "reishi"],
            "severity_emoji_map": {"critical": "red_circle", "high": "orange_circle"},
        }
        config = build_claims_alert_config(data)
        assert config.enabled is True
        assert config.webhook_url == "https://discord.com/api/webhooks/test/test"
        assert config.dawo_product_keywords == ("lion's mane", "chaga", "reishi")
        assert config.backoff_schedule == (60, 300, 900, 3600)
        assert config.severity_emoji_map == {"critical": "red_circle", "high": "orange_circle"}

    def test_build_with_minimal_data(self) -> None:
        """Build with only required fields."""
        data = {
            "webhook_url": "https://discord.com/api/webhooks/test/test",
            "dawo_product_keywords": ["chaga"],
        }
        config = build_claims_alert_config(data)
        assert config.webhook_url == "https://discord.com/api/webhooks/test/test"
        assert config.dawo_product_keywords == ("chaga",)
