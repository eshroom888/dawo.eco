"""Tests for UTMConfig frozen dataclass and loader.

Story 7-2, Task 7.4: Config validation tests.
Tests UTMConfig defaults, builder, and JSON loading.
"""

import json
from unittest.mock import patch

import pytest

from core.config import UTMConfig, _build_utm_config, Config, reload_config


class TestUTMConfig:
    """Tests for UTMConfig frozen dataclass."""

    def test_defaults(self) -> None:
        """UTMConfig has correct default values."""
        config = UTMConfig()
        assert config.short_link_base_url == ""
        assert config.default_attribution_window_days == 30
        assert config.code_length == 8

    def test_custom_values(self) -> None:
        """UTMConfig accepts custom values."""
        config = UTMConfig(
            short_link_base_url="https://dawo.no",
            default_attribution_window_days=60,
            code_length=10,
        )
        assert config.short_link_base_url == "https://dawo.no"
        assert config.default_attribution_window_days == 60
        assert config.code_length == 10

    def test_frozen(self) -> None:
        """UTMConfig is immutable."""
        config = UTMConfig()
        with pytest.raises(AttributeError):
            config.short_link_base_url = "https://changed.com"


class TestBuildUTMConfig:
    """Tests for _build_utm_config builder function."""

    def test_builds_from_utm_config_section(self) -> None:
        """Builds UTMConfig from utm_config section of analytics data."""
        data = {
            "utm_config": {
                "short_link_base_url": "https://test.dawo.no",
                "default_attribution_window_days": 45,
                "code_length": 12,
            }
        }
        config = _build_utm_config(data)
        assert config.short_link_base_url == "https://test.dawo.no"
        assert config.default_attribution_window_days == 45
        assert config.code_length == 12

    def test_builds_with_defaults_when_empty(self) -> None:
        """Uses defaults when utm_config section is missing."""
        config = _build_utm_config({})
        assert config.short_link_base_url == ""
        assert config.default_attribution_window_days == 30
        assert config.code_length == 8

    def test_partial_config_uses_defaults(self) -> None:
        """Uses defaults for missing fields."""
        data = {
            "utm_config": {
                "short_link_base_url": "https://dawo.no",
            }
        }
        config = _build_utm_config(data)
        assert config.short_link_base_url == "https://dawo.no"
        assert config.default_attribution_window_days == 30
        assert config.code_length == 8


class TestConfigIntegration:
    """Tests for UTMConfig integration in main Config."""

    def test_config_has_utm_field(self) -> None:
        """Main Config has utm field."""
        config = Config()
        assert hasattr(config, "utm")
        assert isinstance(config.utm, UTMConfig)

    def test_utm_config_in_all_exports(self) -> None:
        """UTMConfig is in core.config __all__ exports."""
        from core import config as config_module

        assert "UTMConfig" in config_module.__all__
