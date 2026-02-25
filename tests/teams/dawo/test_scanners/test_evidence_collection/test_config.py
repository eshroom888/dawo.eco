"""Tests for EvidenceCollectionConfig (Story 6-8, Task 1).

Tests config creation, validation, immutability, and builder function.
"""

import pytest

from teams.dawo.scanners.evidence_collection.config import (
    EvidenceCollectionConfig,
    build_evidence_collection_config,
)


class TestEvidenceCollectionConfig:
    """Tests for EvidenceCollectionConfig frozen dataclass."""

    def test_valid_config_creation(self) -> None:
        """Config with valid defaults creates successfully."""
        config = EvidenceCollectionConfig()
        assert config.enabled is True
        assert config.batch_size == 20
        assert config.viewport_width == 1280
        assert config.viewport_height == 900
        assert config.timeout_seconds == 30
        assert config.max_concurrent_captures == 3
        assert config.full_page is True
        assert config.screenshot_format == "png"
        assert config.storage_base_path == "evidence/screenshots"
        assert config.timestamp_banner_enabled is True
        assert config.wait_until == "networkidle"
        assert isinstance(config.chromium_args, list)
        assert config.instagram_embed_template == "https://www.instagram.com/p/{shortcode}/embed/"

    def test_non_positive_batch_size_raises(self) -> None:
        """batch_size <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="batch_size"):
            EvidenceCollectionConfig(batch_size=0)
        with pytest.raises(ValueError, match="batch_size"):
            EvidenceCollectionConfig(batch_size=-1)

    def test_non_positive_viewport_width_raises(self) -> None:
        """viewport_width <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="viewport_width"):
            EvidenceCollectionConfig(viewport_width=0)

    def test_non_positive_viewport_height_raises(self) -> None:
        """viewport_height <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="viewport_height"):
            EvidenceCollectionConfig(viewport_height=-10)

    def test_zero_timeout_raises(self) -> None:
        """timeout_seconds <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds"):
            EvidenceCollectionConfig(timeout_seconds=0)

    def test_max_concurrent_out_of_range_raises(self) -> None:
        """max_concurrent_captures outside 1-10 raises ValueError."""
        with pytest.raises(ValueError, match="max_concurrent_captures"):
            EvidenceCollectionConfig(max_concurrent_captures=0)
        with pytest.raises(ValueError, match="max_concurrent_captures"):
            EvidenceCollectionConfig(max_concurrent_captures=11)

    def test_invalid_screenshot_format_raises(self) -> None:
        """screenshot_format not in ('png', 'jpeg') raises ValueError."""
        with pytest.raises(ValueError, match="screenshot_format"):
            EvidenceCollectionConfig(screenshot_format="gif")

    def test_empty_storage_base_path_raises(self) -> None:
        """Empty storage_base_path raises ValueError."""
        with pytest.raises(ValueError, match="storage_base_path"):
            EvidenceCollectionConfig(storage_base_path="")

    def test_frozen_immutability(self) -> None:
        """Config is frozen — cannot mutate attributes."""
        config = EvidenceCollectionConfig()
        with pytest.raises(AttributeError):
            config.batch_size = 50  # type: ignore[misc]


class TestBuildEvidenceCollectionConfig:
    """Tests for build_evidence_collection_config builder function."""

    def test_build_from_json_dict(self) -> None:
        """Builder creates config from a JSON-compatible dict."""
        data = {
            "enabled": False,
            "batch_size": 10,
            "viewport_width": 1920,
            "viewport_height": 1080,
            "timeout_seconds": 60,
            "max_concurrent_captures": 5,
            "full_page": False,
            "screenshot_format": "jpeg",
            "storage_base_path": "custom/path",
            "chromium_args": ["--no-sandbox"],
            "instagram_embed_template": "https://example.com/{shortcode}/",
            "timestamp_banner_enabled": False,
            "wait_until": "load",
        }
        config = build_evidence_collection_config(data)
        assert config.enabled is False
        assert config.batch_size == 10
        assert config.viewport_width == 1920
        assert config.screenshot_format == "jpeg"
        assert config.storage_base_path == "custom/path"

    def test_build_with_defaults(self) -> None:
        """Builder uses defaults for missing keys."""
        config = build_evidence_collection_config({})
        assert config.batch_size == 20
        assert config.viewport_width == 1280
