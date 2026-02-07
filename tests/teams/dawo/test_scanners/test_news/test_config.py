"""Tests for news scanner configuration."""

import pytest

from teams.dawo.scanners.news.config import (
    FeedSource,
    NewsFeedClientConfig,
    NewsScannerConfig,
    DEFAULT_FETCH_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_HOURS_BACK,
    DEFAULT_KEYWORDS,
)


class TestFeedSource:
    """Tests for FeedSource configuration."""

    def test_create_feed_source(self) -> None:
        """Test creating a feed source."""
        feed = FeedSource(
            name="NutraIngredients",
            url="https://www.nutraingredients.com/rss/",
            is_tier_1=True,
        )
        assert feed.name == "NutraIngredients"
        assert feed.url == "https://www.nutraingredients.com/rss/"
        assert feed.is_tier_1 is True

    def test_feed_source_defaults(self) -> None:
        """Test feed source default values."""
        feed = FeedSource(
            name="TestFeed",
            url="https://test.com/rss",
        )
        assert feed.is_tier_1 is False

    def test_feed_source_empty_name_fails(self) -> None:
        """Test that empty name raises error."""
        with pytest.raises(ValueError, match="Feed name is required"):
            FeedSource(name="", url="https://test.com/rss")

    def test_feed_source_empty_url_fails(self) -> None:
        """Test that empty URL raises error."""
        with pytest.raises(ValueError, match="Feed URL is required"):
            FeedSource(name="TestFeed", url="")


class TestNewsFeedClientConfig:
    """Tests for NewsFeedClientConfig."""

    def test_create_client_config(self) -> None:
        """Test creating client config."""
        config = NewsFeedClientConfig(
            fetch_timeout=60,
            max_retries=5,
        )
        assert config.fetch_timeout == 60
        assert config.max_retries == 5

    def test_client_config_defaults(self) -> None:
        """Test client config defaults."""
        config = NewsFeedClientConfig()
        assert config.fetch_timeout == DEFAULT_FETCH_TIMEOUT
        assert config.max_retries == DEFAULT_MAX_RETRIES

    def test_client_config_invalid_timeout(self) -> None:
        """Test that invalid timeout raises error."""
        with pytest.raises(ValueError, match="fetch_timeout must be >= 1"):
            NewsFeedClientConfig(fetch_timeout=0)

    def test_client_config_invalid_retries(self) -> None:
        """Test that invalid retries raises error."""
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            NewsFeedClientConfig(max_retries=-1)


class TestNewsScannerConfig:
    """Tests for NewsScannerConfig."""

    def test_create_scanner_config(self) -> None:
        """Test creating scanner config."""
        feeds = [
            FeedSource("Feed1", "https://feed1.com/rss", is_tier_1=True),
            FeedSource("Feed2", "https://feed2.com/rss"),
        ]
        config = NewsScannerConfig(
            feeds=feeds,
            keywords=["mushrooms", "supplements"],
            competitor_brands=["Competitor1"],
            hours_back=48,
        )
        assert len(config.feeds) == 2
        assert config.keywords == ["mushrooms", "supplements"]
        assert config.competitor_brands == ["Competitor1"]
        assert config.hours_back == 48

    def test_scanner_config_empty_feeds_fails(self) -> None:
        """Test that empty feeds list raises error."""
        with pytest.raises(ValueError, match="feeds list cannot be empty"):
            NewsScannerConfig(feeds=[])

    def test_scanner_config_invalid_hours_back(self) -> None:
        """Test that invalid hours_back raises error."""
        feeds = [FeedSource("Feed", "https://feed.com/rss")]
        with pytest.raises(ValueError, match="hours_back must be >= 1"):
            NewsScannerConfig(feeds=feeds, hours_back=0)

    def test_scanner_config_defaults(self) -> None:
        """Test scanner config defaults."""
        feeds = [FeedSource("Feed", "https://feed.com/rss")]
        config = NewsScannerConfig(feeds=feeds)
        assert config.keywords == DEFAULT_KEYWORDS
        assert config.competitor_brands == []
        assert config.hours_back == DEFAULT_HOURS_BACK
