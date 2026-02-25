"""Tests for AttributionConfig and related configuration.

Story 7-3, Task 7.5: Config validation tests.
"""

import pytest

from core.config import AttributionConfig, Config, get_config, reload_config


class TestAttributionConfig:
    """Tests for AttributionConfig frozen dataclass."""

    def test_defaults(self) -> None:
        config = AttributionConfig()
        assert config.webhook_secret == ""
        assert config.polling_interval_hours == 1
        assert config.attribution_window_days == 30
        assert config.max_touchpoints == 50

    def test_custom_values(self) -> None:
        config = AttributionConfig(
            webhook_secret="secret_123",
            polling_interval_hours=2,
            attribution_window_days=14,
            max_touchpoints=100,
        )
        assert config.webhook_secret == "secret_123"
        assert config.polling_interval_hours == 2
        assert config.attribution_window_days == 14
        assert config.max_touchpoints == 100

    def test_frozen(self) -> None:
        config = AttributionConfig()
        with pytest.raises(AttributeError):
            config.webhook_secret = "changed"  # type: ignore[misc]

    def test_config_has_attribution(self) -> None:
        config = Config()
        assert isinstance(config.attribution, AttributionConfig)

    def test_get_config_has_attribution(self) -> None:
        reload_config()  # Clear cache
        config = get_config()
        assert isinstance(config.attribution, AttributionConfig)
        assert config.attribution.attribution_window_days == 30


class TestAttributionConfigFromJson:
    """Tests for config loading from dawo_analytics.json."""

    def test_attribution_section_loaded(self) -> None:
        reload_config()
        config = get_config()
        # From config/dawo_analytics.json attribution section
        assert config.attribution.attribution_window_days == 30
        assert config.attribution.max_touchpoints == 50
        assert config.attribution.polling_interval_hours == 1
