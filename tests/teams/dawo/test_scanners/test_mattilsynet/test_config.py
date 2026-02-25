"""Tests for Mattilsynet config.

Epic 6, Story 6-3: Task 13.36.
"""

import pytest

from teams.dawo.scanners.mattilsynet.config import (
    FeedConfig,
    MattilsynetMonitorConfig,
    MonitoredPageConfig,
    build_mattilsynet_config,
)


class TestMattilsynetMonitorConfig:
    """Test MattilsynetMonitorConfig validation."""

    def test_valid_config_with_feeds(self) -> None:
        config = MattilsynetMonitorConfig(
            feeds=(FeedConfig(name="test", url="https://example.com/rss"),),
            keywords_tier_1=("kosttilskudd",),
        )
        assert config.schedule_cron == "0 7 * * *"
        assert len(config.feeds) == 1

    def test_valid_config_with_pages(self) -> None:
        config = MattilsynetMonitorConfig(
            monitored_pages=(MonitoredPageConfig(name="page", url="https://example.com"),),
            keywords_tier_1=("kosttilskudd",),
        )
        assert len(config.monitored_pages) == 1

    def test_rejects_empty_keywords(self) -> None:
        with pytest.raises(ValueError, match="keywords_tier_1 must not be empty"):
            MattilsynetMonitorConfig(
                feeds=(FeedConfig(name="test", url="https://example.com/rss"),),
                keywords_tier_1=(),
            )

    def test_rejects_no_feeds_or_pages(self) -> None:
        with pytest.raises(ValueError, match="At least one feed or monitored page"):
            MattilsynetMonitorConfig(
                feeds=(),
                monitored_pages=(),
                keywords_tier_1=("kosttilskudd",),
            )

    def test_frozen(self) -> None:
        config = MattilsynetMonitorConfig(
            feeds=(FeedConfig(name="test", url="https://example.com/rss"),),
            keywords_tier_1=("kosttilskudd",),
        )
        with pytest.raises(AttributeError):
            config.schedule_cron = "0 8 * * *"  # type: ignore[misc]


class TestBuildMattilsynetConfig:
    """Test build_mattilsynet_config builder function."""

    def test_builds_from_json_dict(self) -> None:
        data = {
            "monitor": {
                "schedule_cron": "0 6 * * *",
                "request_delay_seconds": 10,
                "max_retries": 5,
                "timeout_seconds": 60,
                "user_agent": "Test/1.0",
            },
            "feeds": [
                {"name": "Feed1", "url": "https://example.com/rss", "is_primary": True}
            ],
            "monitored_pages": [
                {"name": "Page1", "url": "https://example.com/page"}
            ],
            "keywords_tier_1": ["keyword1"],
            "keywords_tier_2": ["keyword2"],
            "enforcement_keywords": ["enforce1"],
        }
        config = build_mattilsynet_config(data)
        assert config.schedule_cron == "0 6 * * *"
        assert config.request_delay_seconds == 10
        assert len(config.feeds) == 1
        assert config.feeds[0].name == "Feed1"
        assert config.feeds[0].is_primary is True
        assert len(config.monitored_pages) == 1
        assert config.keywords_tier_1 == ("keyword1",)
        assert config.enforcement_keywords == ("enforce1",)

    def test_builds_with_defaults(self) -> None:
        data = {
            "feeds": [{"name": "F", "url": "https://example.com/rss"}],
            "keywords_tier_1": ["k"],
        }
        config = build_mattilsynet_config(data)
        assert config.schedule_cron == "0 7 * * *"
        assert config.request_delay_seconds == 5
        assert config.max_retries == 3
        assert config.timeout_seconds == 30


class TestFeedConfig:
    """Test FeedConfig frozen dataclass."""

    def test_default_is_primary(self) -> None:
        fc = FeedConfig(name="test", url="https://example.com")
        assert fc.is_primary is False

    def test_frozen(self) -> None:
        fc = FeedConfig(name="test", url="https://example.com")
        with pytest.raises(AttributeError):
            fc.name = "changed"  # type: ignore[misc]
