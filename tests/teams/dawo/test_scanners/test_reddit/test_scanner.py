"""Tests for Reddit Scanner agent.

Tests:
    - Scanner initialization
    - Scan stage execution
    - Filtering by upvotes and time
    - Deduplication
    - Error handling
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from teams.dawo.scanners.reddit import (
    RedditScanner,
    RedditScannerConfig,
    RawRedditPost,
    ScanResult,
    RedditAPIError,
)


class TestRedditScannerInit:
    """Tests for RedditScanner initialization."""

    def test_scanner_creation(
        self,
        scanner_config: RedditScannerConfig,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Scanner should be created with injected dependencies."""
        scanner = RedditScanner(scanner_config, mock_reddit_client)

        assert scanner._config == scanner_config
        assert scanner._client == mock_reddit_client


class TestRedditScannerScan:
    """Tests for scan() method."""

    @pytest.mark.asyncio
    async def test_scan_returns_result(
        self,
        scanner_config: RedditScannerConfig,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Scan should return ScanResult with posts."""
        scanner = RedditScanner(scanner_config, mock_reddit_client)
        result = await scanner.scan()

        assert isinstance(result, ScanResult)
        assert result.statistics.subreddits_scanned == 1
        assert result.statistics.keywords_searched == 1

    @pytest.mark.asyncio
    async def test_scan_filters_low_upvotes(
        self,
        scanner_config: RedditScannerConfig,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Posts below min_upvotes should be filtered out."""
        # The mock response has a post with score=5 (below threshold of 10)
        scanner = RedditScanner(scanner_config, mock_reddit_client)
        result = await scanner.scan()

        # Should have filtered out the low upvote post
        for post in result.posts:
            assert post.score >= scanner_config.min_upvotes

    @pytest.mark.asyncio
    async def test_scan_deduplicates_posts(
        self,
        scanner_config: RedditScannerConfig,
    ) -> None:
        """Duplicate posts should be removed by ID."""
        # Create mock client that returns same post for different keywords
        mock_client = AsyncMock()
        now = datetime.now(timezone.utc).timestamp()

        # Return same post ID for both searches
        mock_client.search_subreddit.return_value = [
            {
                "id": "duplicate123",
                "subreddit": "Nootropics",
                "title": "Duplicate post",
                "score": 100,
                "created_utc": now - 3600,
                "permalink": "/r/Nootropics/comments/duplicate123/",
                "is_self": True,
            }
        ]

        # Config with multiple keywords to trigger deduplication
        config = RedditScannerConfig(
            subreddits=["Nootropics"],
            keywords=["lion's mane", "chaga"],  # Two keywords
            min_upvotes=10,
        )

        scanner = RedditScanner(config, mock_client)
        result = await scanner.scan()

        # Should only have 1 post despite 2 keyword searches returning same ID
        assert len(result.posts) == 1
        assert result.posts[0].id == "duplicate123"
        assert result.statistics.duplicates_removed >= 1

    @pytest.mark.asyncio
    async def test_scan_handles_api_errors_gracefully(
        self,
        scanner_config: RedditScannerConfig,
    ) -> None:
        """API errors should be logged but not stop the scan."""
        mock_client = AsyncMock()
        mock_client.search_subreddit.side_effect = RedditAPIError("API unavailable")

        scanner = RedditScanner(scanner_config, mock_client)
        result = await scanner.scan()

        # Should return result with errors logged
        assert len(result.errors) > 0
        assert "API unavailable" in result.errors[0]
        assert result.posts == []

    @pytest.mark.asyncio
    async def test_scan_multiple_subreddits(self) -> None:
        """Scan should process all configured subreddits."""
        mock_client = AsyncMock()
        now = datetime.now(timezone.utc).timestamp()

        # Return different posts for different subreddits
        def mock_search(subreddit, **kwargs):
            return [
                {
                    "id": f"{subreddit}_post",
                    "subreddit": subreddit,
                    "title": f"Post from {subreddit}",
                    "score": 100,
                    "created_utc": now - 1800,
                    "permalink": f"/r/{subreddit}/comments/test/",
                    "is_self": True,
                }
            ]

        mock_client.search_subreddit.side_effect = mock_search

        config = RedditScannerConfig(
            subreddits=["Nootropics", "Supplements"],
            keywords=["test"],
            min_upvotes=10,
        )

        scanner = RedditScanner(config, mock_client)
        result = await scanner.scan()

        assert result.statistics.subreddits_scanned == 2
        assert len(result.posts) == 2

    @pytest.mark.asyncio
    async def test_scan_statistics_accuracy(
        self,
        scanner_config: RedditScannerConfig,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Scan statistics should accurately reflect processing."""
        scanner = RedditScanner(scanner_config, mock_reddit_client)
        result = await scanner.scan()

        stats = result.statistics
        assert stats.subreddits_scanned == len(scanner_config.subreddits)
        assert stats.keywords_searched == len(scanner_config.keywords)
        assert stats.total_posts_found >= 0
        assert stats.posts_after_filter >= 0
        assert stats.posts_after_filter <= stats.total_posts_found


class TestRedditScannerFiltering:
    """Tests for post filtering logic."""

    @pytest.mark.asyncio
    async def test_filter_by_time(self) -> None:
        """Posts older than time window should be filtered."""
        mock_client = AsyncMock()
        now = datetime.now(timezone.utc).timestamp()

        # One recent post, one old post
        mock_client.search_subreddit.return_value = [
            {
                "id": "recent",
                "subreddit": "Test",
                "title": "Recent post",
                "score": 100,
                "created_utc": now - 3600,  # 1 hour ago
                "permalink": "/r/Test/comments/recent/",
                "is_self": True,
            },
            {
                "id": "old",
                "subreddit": "Test",
                "title": "Old post",
                "score": 100,
                "created_utc": now - 172800,  # 2 days ago
                "permalink": "/r/Test/comments/old/",
                "is_self": True,
            },
        ]

        config = RedditScannerConfig(
            subreddits=["Test"],
            keywords=["test"],
            min_upvotes=10,
            time_filter="day",  # Last 24 hours
        )

        scanner = RedditScanner(config, mock_client)
        result = await scanner.scan()

        # Should only have the recent post
        assert len(result.posts) == 1
        assert result.posts[0].id == "recent"

    @pytest.mark.asyncio
    async def test_filter_by_upvotes(self) -> None:
        """Posts below upvote threshold should be filtered."""
        mock_client = AsyncMock()
        now = datetime.now(timezone.utc).timestamp()

        mock_client.search_subreddit.return_value = [
            {
                "id": "high_score",
                "subreddit": "Test",
                "title": "Popular post",
                "score": 50,
                "created_utc": now - 3600,
                "permalink": "/r/Test/comments/high/",
                "is_self": True,
            },
            {
                "id": "low_score",
                "subreddit": "Test",
                "title": "Unpopular post",
                "score": 5,  # Below threshold
                "created_utc": now - 3600,
                "permalink": "/r/Test/comments/low/",
                "is_self": True,
            },
        ]

        config = RedditScannerConfig(
            subreddits=["Test"],
            keywords=["test"],
            min_upvotes=10,
        )

        scanner = RedditScanner(config, mock_client)
        result = await scanner.scan()

        # Should only have the high score post
        assert len(result.posts) == 1
        assert result.posts[0].id == "high_score"
        assert result.posts[0].score == 50
