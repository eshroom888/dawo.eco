"""Tests for InstagramScanner agent.

Tests the scan stage of the Harvester Framework pipeline.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.instagram import (
    InstagramScanner,
    InstagramScannerConfig,
    RawInstagramPost,
    ScanResult,
    ScanStatistics,
)


class TestInstagramScanner:
    """Test suite for InstagramScanner."""

    @pytest.mark.asyncio
    async def test_scan_returns_scan_result(self, mock_instagram_client, scanner_config):
        """Test that scan() returns a ScanResult object."""
        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        result = await scanner.scan()

        assert isinstance(result, ScanResult)
        assert isinstance(result.statistics, ScanStatistics)
        assert isinstance(result.posts, list)
        assert isinstance(result.errors, list)

    @pytest.mark.asyncio
    async def test_scan_searches_all_hashtags(self, mock_instagram_client, scanner_config):
        """Test that scan() searches all configured hashtags."""
        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        await scanner.scan()

        # Should search both configured hashtags
        assert mock_instagram_client.search_hashtag.call_count == len(scanner_config.hashtags)

    @pytest.mark.asyncio
    async def test_scan_monitors_competitor_accounts(self, mock_instagram_client, scanner_config):
        """Test that scan() monitors all competitor accounts."""
        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        await scanner.scan()

        # Should check competitor accounts
        assert mock_instagram_client.get_user_media.call_count == len(scanner_config.competitor_accounts)

    @pytest.mark.asyncio
    async def test_scan_statistics_tracked(self, mock_instagram_client, scanner_config):
        """Test that scan statistics are properly tracked."""
        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        result = await scanner.scan()

        assert result.statistics.hashtags_searched == len(scanner_config.hashtags)
        assert result.statistics.accounts_monitored == len(scanner_config.competitor_accounts)
        assert result.statistics.total_posts_found > 0

    @pytest.mark.asyncio
    async def test_scan_deduplicates_posts(self, mock_instagram_client, scanner_config):
        """Test that duplicate posts are removed by media_id."""
        # Set up client to return same post from multiple sources
        duplicate_post = {
            "id": "duplicate_id_123",
            "caption": "Duplicate post",
            "permalink": "https://www.instagram.com/p/DUPLICATE/",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "media_type": "IMAGE",
        }
        mock_instagram_client.search_hashtag.return_value = [duplicate_post]
        mock_instagram_client.get_user_media.return_value = [duplicate_post]

        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        result = await scanner.scan()

        # Should only have 1 unique post despite appearing in multiple sources
        assert len(result.posts) == 1
        assert result.statistics.duplicates_removed > 0

    @pytest.mark.asyncio
    async def test_scan_filters_by_time(self, mock_instagram_client, scanner_config):
        """Test that posts older than hours_back are filtered."""
        # Set up client to return posts from different times
        old_post = {
            "id": "old_post_123",
            "caption": "Old post",
            "permalink": "https://www.instagram.com/p/OLD/",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(),
            "media_type": "IMAGE",
        }
        recent_post = {
            "id": "recent_post_123",
            "caption": "Recent post",
            "permalink": "https://www.instagram.com/p/RECENT/",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "media_type": "IMAGE",
        }
        mock_instagram_client.search_hashtag.return_value = [old_post, recent_post]
        mock_instagram_client.get_user_media.return_value = []

        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        result = await scanner.scan()

        # Only recent post should be in results
        assert len(result.posts) == 1
        assert result.posts[0].media_id == "recent_post_123"

    @pytest.mark.asyncio
    async def test_scan_marks_competitor_posts(self, mock_instagram_client, scanner_config):
        """Test that posts from competitors are marked is_competitor=True."""
        mock_instagram_client.search_hashtag.return_value = []

        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        result = await scanner.scan()

        # Find competitor posts
        competitor_posts = [p for p in result.posts if p.is_competitor]
        assert len(competitor_posts) > 0

    @pytest.mark.asyncio
    async def test_scan_marks_hashtag_source(self, mock_instagram_client, scanner_config):
        """Test that posts include the hashtag_source when found via hashtag search."""
        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        result = await scanner.scan()

        # Find posts with hashtag source
        posts_with_source = [p for p in result.posts if p.hashtag_source is not None]
        assert len(posts_with_source) > 0

    @pytest.mark.asyncio
    async def test_scan_continues_on_api_error(self, mock_instagram_client, scanner_config):
        """Test that scan continues even if one hashtag search fails."""
        from teams.dawo.scanners.instagram import InstagramAPIError

        # First hashtag fails, second succeeds
        mock_instagram_client.search_hashtag.side_effect = [
            InstagramAPIError("API error"),
            [{"id": "success_post", "caption": "Success", "permalink": "https://example.com", "timestamp": datetime.now(timezone.utc).isoformat(), "media_type": "IMAGE"}],
        ]

        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        result = await scanner.scan()

        # Should have errors logged but still have posts from successful search
        assert len(result.errors) > 0
        assert len(result.posts) > 0

    @pytest.mark.asyncio
    async def test_scan_returns_raw_instagram_posts(self, mock_instagram_client, scanner_config):
        """Test that scan returns list of RawInstagramPost objects."""
        scanner = InstagramScanner(config=scanner_config, client=mock_instagram_client)
        result = await scanner.scan()

        for post in result.posts:
            assert isinstance(post, RawInstagramPost)
            assert post.media_id
            assert post.permalink
            assert isinstance(post.timestamp, datetime)


class TestInstagramScannerConfig:
    """Test suite for InstagramScannerConfig validation."""

    def test_config_validates_empty_hashtags(self):
        """Test that empty hashtags list raises ValueError."""
        with pytest.raises(ValueError, match="hashtags list cannot be empty"):
            InstagramScannerConfig(hashtags=[])

    def test_config_validates_hours_back(self):
        """Test that hours_back < 1 raises ValueError."""
        with pytest.raises(ValueError, match="hours_back must be >= 1"):
            InstagramScannerConfig(hours_back=0)

    def test_config_validates_max_posts_per_hashtag(self):
        """Test that max_posts_per_hashtag > 30 raises ValueError."""
        with pytest.raises(ValueError, match="max_posts_per_hashtag must be 1-30"):
            InstagramScannerConfig(max_posts_per_hashtag=50)

    def test_config_validates_max_posts_per_account(self):
        """Test that max_posts_per_account > 30 raises ValueError."""
        with pytest.raises(ValueError, match="max_posts_per_account must be 1-30"):
            InstagramScannerConfig(max_posts_per_account=50)

    def test_config_default_values(self):
        """Test that default values are set correctly."""
        config = InstagramScannerConfig()

        assert len(config.hashtags) > 0
        assert config.hours_back == 24
        assert config.max_posts_per_hashtag == 25
        assert config.max_posts_per_account == 10
