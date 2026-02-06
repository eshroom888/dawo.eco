"""Tests for retry configuration loading.

Tests verify:
- Load function parses JSON correctly
- Per-API overrides are applied
- Config injection pattern works (not direct file loading)
- Validation catches invalid config
"""

import pytest
import json
from pathlib import Path

from teams.dawo.middleware import (
    RetryConfig,
    load_retry_config,
    get_retry_config_for_api,
)


class TestLoadRetryConfig:
    """Test load_retry_config function."""

    def test_loads_from_valid_json(self, tmp_path: Path) -> None:
        """Should load config from valid JSON file."""
        config_data = {
            "version": "test",
            "default": {
                "max_retries": 5,
                "base_delay": 2.0,
                "max_delay": 120.0,
                "backoff_multiplier": 3.0,
                "timeout": 45.0,
                "max_rate_limit_wait": 600,
            },
            "api_overrides": {},
            "discord_alerts": {"enabled": True, "cooldown_seconds": 300},
        }
        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_retry_config(config_file)

        assert result["version"] == "test"
        assert result["default"]["max_retries"] == 5
        assert result["default"]["base_delay"] == 2.0

    def test_raises_file_not_found(self) -> None:
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Retry config not found"):
            load_retry_config(Path("/nonexistent/config.json"))

    def test_raises_json_error_for_invalid_json(self, tmp_path: Path) -> None:
        """Should raise JSONDecodeError for invalid JSON."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_retry_config(config_file)


class TestGetRetryConfigForApi:
    """Test get_retry_config_for_api function."""

    @pytest.fixture
    def sample_config(self) -> dict:
        """Sample configuration with overrides."""
        return {
            "version": "test",
            "default": {
                "max_retries": 3,
                "base_delay": 1.0,
                "max_delay": 60.0,
                "backoff_multiplier": 2.0,
                "timeout": 30.0,
                "max_rate_limit_wait": 300,
            },
            "api_overrides": {
                "instagram": {"timeout": 45.0, "max_rate_limit_wait": 600},
                "discord": {"max_retries": 2, "timeout": 10.0},
            },
            "discord_alerts": {"enabled": True, "cooldown_seconds": 300},
        }

    def test_returns_default_config_for_unknown_api(
        self, sample_config: dict
    ) -> None:
        """Unknown API should get default config."""
        config = get_retry_config_for_api(sample_config, "unknown_api")

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.timeout == 30.0

    def test_returns_retryconfig_instance(self, sample_config: dict) -> None:
        """Should return a RetryConfig dataclass instance."""
        config = get_retry_config_for_api(sample_config, "shopify")
        assert isinstance(config, RetryConfig)

    def test_applies_api_override_timeout(self, sample_config: dict) -> None:
        """Should apply API-specific timeout override."""
        config = get_retry_config_for_api(sample_config, "instagram")

        assert config.timeout == 45.0  # Override
        assert config.max_retries == 3  # From default

    def test_applies_api_override_max_retries(self, sample_config: dict) -> None:
        """Should apply API-specific max_retries override."""
        config = get_retry_config_for_api(sample_config, "discord")

        assert config.max_retries == 2  # Override
        assert config.timeout == 10.0  # Override

    def test_applies_api_override_rate_limit_wait(
        self, sample_config: dict
    ) -> None:
        """Should apply API-specific max_rate_limit_wait override."""
        config = get_retry_config_for_api(sample_config, "instagram")

        assert config.max_rate_limit_wait == 600  # Override

    def test_preserves_non_overridden_defaults(self, sample_config: dict) -> None:
        """Non-overridden values should come from defaults."""
        config = get_retry_config_for_api(sample_config, "instagram")

        # These should be from defaults
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.backoff_multiplier == 2.0


class TestActualConfigFile:
    """Integration tests for actual config file."""

    def test_actual_config_loads(self) -> None:
        """The actual config file should load successfully."""
        config_path = Path("config/dawo_retry_config.json")
        if not config_path.exists():
            pytest.skip("Config file not found - run from project root")

        config = load_retry_config(config_path)

        assert config["version"] is not None
        assert "default" in config
        assert "api_overrides" in config

    def test_actual_config_has_expected_apis(self) -> None:
        """Actual config should have overrides for expected APIs."""
        config_path = Path("config/dawo_retry_config.json")
        if not config_path.exists():
            pytest.skip("Config file not found - run from project root")

        config = load_retry_config(config_path)

        assert "instagram" in config["api_overrides"]
        assert "discord" in config["api_overrides"]
        assert "orshot" in config["api_overrides"]
        assert "shopify" in config["api_overrides"]

    def test_actual_config_creates_valid_retryconfig(self) -> None:
        """Actual config should create valid RetryConfig."""
        config_path = Path("config/dawo_retry_config.json")
        if not config_path.exists():
            pytest.skip("Config file not found - run from project root")

        raw_config = load_retry_config(config_path)
        retry_config = get_retry_config_for_api(raw_config, "instagram")

        assert retry_config.max_retries == 3
        assert retry_config.timeout == 45.0  # Instagram override


class TestModuleExports:
    """Test module exports."""

    def test_load_retry_config_exported(self) -> None:
        """load_retry_config should be importable."""
        from teams.dawo.middleware import load_retry_config
        assert load_retry_config is not None

    def test_get_retry_config_for_api_exported(self) -> None:
        """get_retry_config_for_api should be importable."""
        from teams.dawo.middleware import get_retry_config_for_api
        assert get_retry_config_for_api is not None
