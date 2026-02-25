"""Tests for DegradationConfig.

Story 7-10, Task 1.6: DegradationConfig frozen dataclass and get_config integration.
"""

import pytest

from core.config import DegradationConfig, get_config, reload_config


class TestDegradationConfig:
    """Tests for DegradationConfig frozen dataclass."""

    def test_defaults(self):
        """DegradationConfig has expected defaults."""
        config = DegradationConfig()
        assert config.failure_threshold == 3
        assert config.unhealthy_threshold == 10
        assert config.recovery_check_interval_seconds == 300
        assert config.max_recovery_batch_size == 20
        assert config.alert_cooldown_seconds == 300
        assert config.stale_cache_ttl_hours == 24
        assert "instagram" in config.monitored_services
        assert "shopify" in config.monitored_services
        assert "discord" in config.monitored_services
        assert "google_calendar" in config.monitored_services

    def test_frozen_immutability(self):
        """DegradationConfig is frozen — cannot mutate."""
        config = DegradationConfig()
        with pytest.raises(AttributeError):
            config.failure_threshold = 99

    def test_in_get_config(self):
        """DegradationConfig is accessible via get_config()."""
        reload_config()  # Clear cache
        config = get_config()
        assert hasattr(config, "degradation")
        assert isinstance(config.degradation, DegradationConfig)
        assert config.degradation.failure_threshold == 3

    def test_monitored_services_is_tuple(self):
        """monitored_services is a tuple (immutable)."""
        config = DegradationConfig()
        assert isinstance(config.monitored_services, tuple)
