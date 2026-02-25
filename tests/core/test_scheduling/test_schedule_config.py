"""Tests for AgentSchedulerConfig.

Story 7-6, Task 6.3: Configuration tests.
Target: 8+ tests.
"""

import pytest
from unittest.mock import patch

from core.config import (
    AgentSchedulerConfig,
    _build_agent_scheduler_config,
)


class TestAgentSchedulerConfig:
    """Tests for AgentSchedulerConfig frozen dataclass."""

    def test_defaults(self):
        """Default values are sensible."""
        config = AgentSchedulerConfig()
        assert config.enabled is True
        assert config.check_interval_seconds == 60
        assert config.max_concurrent_agents == 5
        assert config.default_timezone == "UTC"
        assert config.seed_on_startup is True

    def test_frozen(self):
        """Config is immutable."""
        config = AgentSchedulerConfig()
        with pytest.raises(AttributeError):
            config.enabled = False

    def test_custom_values(self):
        """Accepts custom values."""
        config = AgentSchedulerConfig(
            enabled=False,
            check_interval_seconds=120,
            max_concurrent_agents=3,
            default_timezone="Europe/Oslo",
            seed_on_startup=False,
        )
        assert config.enabled is False
        assert config.check_interval_seconds == 120
        assert config.max_concurrent_agents == 3
        assert config.default_timezone == "Europe/Oslo"
        assert config.seed_on_startup is False


class TestBuildAgentSchedulerConfig:
    """Tests for the builder function."""

    def test_builds_from_json_data(self):
        """Builds config from analytics JSON data."""
        data = {
            "agent_scheduler": {
                "enabled": True,
                "check_interval_seconds": 60,
                "max_concurrent_agents": 5,
                "default_timezone": "UTC",
                "seed_on_startup": True,
            }
        }
        config = _build_agent_scheduler_config(data)
        assert config.enabled is True
        assert config.check_interval_seconds == 60

    def test_defaults_when_missing(self):
        """Uses defaults when section is missing."""
        config = _build_agent_scheduler_config({})
        assert config.enabled is True
        assert config.default_timezone == "UTC"

    def test_partial_data(self):
        """Handles partial data with defaults for missing fields."""
        data = {
            "agent_scheduler": {
                "enabled": False,
            }
        }
        config = _build_agent_scheduler_config(data)
        assert config.enabled is False
        assert config.check_interval_seconds == 60


class TestConfigIntegration:
    """Tests for Config class integration."""

    def test_config_has_agent_scheduler(self):
        """Main Config class has agent_scheduler field."""
        from core.config import Config

        config = Config()
        assert hasattr(config, "agent_scheduler")
        assert isinstance(config.agent_scheduler, AgentSchedulerConfig)

    def test_get_config_returns_agent_scheduler(self):
        """get_config() returns config with agent_scheduler."""
        from core.config import get_config, reload_config

        # Force reload to pick up changes
        config = reload_config()
        assert hasattr(config, "agent_scheduler")
