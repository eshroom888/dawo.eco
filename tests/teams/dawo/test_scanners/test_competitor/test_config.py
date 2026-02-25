"""Tests for CompetitorScannerConfig.

Epic 6, Story 6-5, Task 1: Frozen dataclass config with validation.
"""

import pytest

from teams.dawo.scanners.competitor.config import (
    CompetitorScannerConfig,
    CompetitorConfig,
    InstagramScanConfig,
    WebsiteScanConfig,
    build_competitor_scanner_config,
)


@pytest.fixture
def valid_competitor():
    """Single valid competitor entry."""
    return CompetitorConfig(
        name="CompetitorA",
        instagram_username="competitor_a",
        website_urls=("https://competitor-a.com/products",),
        is_primary=True,
    )


@pytest.fixture
def valid_keywords():
    """Minimal valid keywords tuple."""
    return ("boost", "improve", "enhance", "styrker", "forbedrer")


@pytest.fixture
def valid_config(valid_competitor, valid_keywords):
    """Fully valid CompetitorScannerConfig."""
    return CompetitorScannerConfig(
        competitors=(valid_competitor,),
        health_language_keywords=valid_keywords,
    )


class TestCompetitorConfig:
    """Tests for CompetitorConfig nested frozen dataclass."""

    def test_creation_with_all_fields(self):
        config = CompetitorConfig(
            name="TestComp",
            instagram_username="testcomp",
            website_urls=("https://test.com",),
            is_primary=True,
        )
        assert config.name == "TestComp"
        assert config.instagram_username == "testcomp"
        assert config.website_urls == ("https://test.com",)
        assert config.is_primary is True

    def test_defaults(self):
        config = CompetitorConfig(name="Minimal")
        assert config.instagram_username is None
        assert config.website_urls == ()
        assert config.is_primary is False

    def test_frozen_immutability(self):
        config = CompetitorConfig(name="Frozen")
        with pytest.raises(AttributeError):
            config.name = "Changed"


class TestInstagramScanConfig:
    """Tests for InstagramScanConfig nested frozen dataclass."""

    def test_defaults(self):
        config = InstagramScanConfig()
        assert config.enabled is True
        assert config.scan_window_days == 7
        assert config.max_posts_per_competitor == 25

    def test_frozen_immutability(self):
        config = InstagramScanConfig()
        with pytest.raises(AttributeError):
            config.enabled = False


class TestWebsiteScanConfig:
    """Tests for WebsiteScanConfig nested frozen dataclass."""

    def test_defaults(self):
        config = WebsiteScanConfig()
        assert config.enabled is True
        assert config.request_delay_seconds == 5
        assert config.max_pages_per_domain == 20

    def test_frozen_immutability(self):
        config = WebsiteScanConfig()
        with pytest.raises(AttributeError):
            config.enabled = False


class TestCompetitorScannerConfig:
    """Tests for CompetitorScannerConfig frozen dataclass with validation."""

    def test_valid_config_creation(self, valid_config):
        assert valid_config.enabled is True
        assert valid_config.schedule_cron == "0 3 * * *"
        assert len(valid_config.competitors) == 1
        assert len(valid_config.health_language_keywords) == 5
        assert valid_config.request_delay_seconds == 3
        assert valid_config.max_retries == 3
        assert valid_config.timeout_seconds == 30

    def test_empty_competitors_raises_value_error(self, valid_keywords):
        with pytest.raises(ValueError, match="At least one competitor"):
            CompetitorScannerConfig(
                competitors=(),
                health_language_keywords=valid_keywords,
            )

    def test_empty_keywords_raises_value_error(self, valid_competitor):
        with pytest.raises(ValueError, match="health_language_keywords must not be empty"):
            CompetitorScannerConfig(
                competitors=(valid_competitor,),
                health_language_keywords=(),
            )

    def test_negative_delay_raises_value_error(self, valid_competitor, valid_keywords):
        with pytest.raises(ValueError, match="request_delay_seconds must be non-negative"):
            CompetitorScannerConfig(
                competitors=(valid_competitor,),
                health_language_keywords=valid_keywords,
                request_delay_seconds=-1,
            )

    def test_frozen_immutability(self, valid_config):
        with pytest.raises(AttributeError):
            valid_config.enabled = False

    def test_default_values(self, valid_competitor, valid_keywords):
        config = CompetitorScannerConfig(
            competitors=(valid_competitor,),
            health_language_keywords=valid_keywords,
        )
        assert config.enabled is True
        assert config.schedule_cron == "0 3 * * *"
        assert config.request_delay_seconds == 3
        assert config.max_retries == 3
        assert config.timeout_seconds == 30
        assert config.user_agent == "DAWO-ECO-CompetitorMonitor/1.0 (+https://imagoeco.com/bot)"

    def test_nested_instagram_config(self, valid_config):
        assert valid_config.instagram.enabled is True
        assert valid_config.instagram.scan_window_days == 7

    def test_nested_website_config(self, valid_config):
        assert valid_config.websites.enabled is True
        assert valid_config.websites.request_delay_seconds == 5


class TestBuildCompetitorScannerConfig:
    """Tests for build_competitor_scanner_config factory function."""

    def test_build_from_json_dict(self):
        data = {
            "enabled": True,
            "schedule_cron": "0 3 * * *",
            "competitors": [
                {
                    "name": "CompA",
                    "instagram_username": "compa",
                    "website_urls": ["https://compa.com"],
                    "is_primary": True,
                }
            ],
            "health_language_keywords": ["boost", "improve"],
            "instagram": {
                "enabled": True,
                "scan_window_days": 7,
                "max_posts_per_competitor": 25,
            },
            "websites": {
                "enabled": True,
                "request_delay_seconds": 5,
                "max_pages_per_domain": 20,
            },
            "request_delay_seconds": 3,
            "max_retries": 3,
            "timeout_seconds": 30,
            "user_agent": "DAWO-ECO-CompetitorMonitor/1.0 (+https://imagoeco.com/bot)",
        }
        config = build_competitor_scanner_config(data)
        assert isinstance(config, CompetitorScannerConfig)
        assert config.enabled is True
        assert len(config.competitors) == 1
        assert config.competitors[0].name == "CompA"
        assert config.competitors[0].instagram_username == "compa"
        assert config.competitors[0].website_urls == ("https://compa.com",)
        assert config.health_language_keywords == ("boost", "improve")
        assert config.instagram.enabled is True
        assert config.websites.enabled is True
