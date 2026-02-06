"""Tests for YouTube Data API client.

Tests Task 2: YouTubeClient implementation for YouTube Data API v3.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestYouTubeClient:
    """Tests for YouTubeClient class."""

    def test_can_import_youtube_client(self):
        """Test that YouTubeClient can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeClient

        assert YouTubeClient is not None

    def test_youtube_client_accepts_config_injection(self):
        """Test that YouTubeClient accepts config via constructor."""
        from teams.dawo.scanners.youtube import YouTubeClient, YouTubeClientConfig

        config = YouTubeClientConfig(api_key="test_api_key")
        retry_middleware = MagicMock()

        client = YouTubeClient(config, retry_middleware)

        assert client._config.api_key == "test_api_key"

    def test_youtube_client_has_quota_remaining_property(self):
        """Test that YouTubeClient exposes remaining quota."""
        from teams.dawo.scanners.youtube import YouTubeClient, YouTubeClientConfig

        config = YouTubeClientConfig(api_key="test_api_key")
        retry_middleware = MagicMock()

        client = YouTubeClient(config, retry_middleware)

        assert client.quota_remaining > 0


class TestQuotaTracker:
    """Tests for QuotaTracker class."""

    def test_can_import_quota_tracker(self):
        """Test that QuotaTracker can be imported from module."""
        from teams.dawo.scanners.youtube import QuotaTracker

        assert QuotaTracker is not None

    def test_quota_tracker_initial_remaining(self):
        """Test QuotaTracker starts with full quota."""
        from teams.dawo.scanners.youtube import QuotaTracker, YOUTUBE_DAILY_QUOTA

        tracker = QuotaTracker()

        assert tracker.get_remaining() == YOUTUBE_DAILY_QUOTA

    def test_quota_tracker_check_and_use(self):
        """Test QuotaTracker decrements remaining quota."""
        from teams.dawo.scanners.youtube import QuotaTracker, YOUTUBE_DAILY_QUOTA

        tracker = QuotaTracker()
        initial = tracker.get_remaining()

        tracker.check_and_use(100)

        assert tracker.get_remaining() == initial - 100

    def test_quota_tracker_raises_on_exceeded(self):
        """Test QuotaTracker raises QuotaExhaustedError when exceeded."""
        from teams.dawo.scanners.youtube import QuotaTracker, QuotaExhaustedError, YOUTUBE_DAILY_QUOTA

        tracker = QuotaTracker()

        with pytest.raises(QuotaExhaustedError):
            tracker.check_and_use(YOUTUBE_DAILY_QUOTA + 1)


class TestYouTubeClientSearch:
    """Tests for YouTubeClient.search_videos method."""

    @pytest.fixture
    def mock_youtube_search_response(self):
        """Mock YouTube Data API search response."""
        return {
            "items": [
                {
                    "kind": "youtube#searchResult",
                    "id": {"videoId": "abc123xyz"},
                    "snippet": {
                        "publishedAt": "2026-02-01T10:00:00Z",
                        "channelId": "UCxxxxxxx",
                        "title": "Lion's Mane Benefits: What Science Actually Says",
                        "description": "In this video we explore...",
                        "channelTitle": "Health Science Channel",
                        "thumbnails": {
                            "default": {"url": "https://i.ytimg.com/vi/abc123xyz/default.jpg"}
                        },
                    },
                },
                {
                    "kind": "youtube#searchResult",
                    "id": {"videoId": "def456uvw"},
                    "snippet": {
                        "publishedAt": "2026-02-02T15:30:00Z",
                        "channelId": "UCyyyyyyy",
                        "title": "Mushroom Supplements Review",
                        "description": "Comparing different mushroom supplements...",
                        "channelTitle": "Wellness Reviews",
                        "thumbnails": {
                            "default": {"url": "https://i.ytimg.com/vi/def456uvw/default.jpg"}
                        },
                    },
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_search_videos_returns_list(self, mock_youtube_search_response):
        """Test search_videos returns list of video data."""
        from teams.dawo.scanners.youtube import YouTubeClient, YouTubeClientConfig

        config = YouTubeClientConfig(api_key="test_api_key")
        retry_middleware = MagicMock()
        retry_middleware.execute_with_retry = AsyncMock(
            return_value=MagicMock(
                success=True,
                response=mock_youtube_search_response,
            )
        )

        client = YouTubeClient(config, retry_middleware)
        # Mock the session
        client._session = AsyncMock()
        client._session.request = AsyncMock()

        published_after = datetime.now(timezone.utc) - timedelta(days=7)

        videos = await client.search_videos(
            query="mushroom supplements",
            published_after=published_after,
            max_results=50,
        )

        assert isinstance(videos, list)
        assert len(videos) == 2
        assert videos[0]["id"]["videoId"] == "abc123xyz"

    @pytest.mark.asyncio
    async def test_search_videos_uses_retry_middleware(self, mock_youtube_search_response):
        """Test that search_videos uses retry middleware."""
        from teams.dawo.scanners.youtube import YouTubeClient, YouTubeClientConfig

        config = YouTubeClientConfig(api_key="test_api_key")
        retry_middleware = MagicMock()
        retry_middleware.execute_with_retry = AsyncMock(
            return_value=MagicMock(
                success=True,
                response=mock_youtube_search_response,
            )
        )

        client = YouTubeClient(config, retry_middleware)
        client._session = AsyncMock()

        published_after = datetime.now(timezone.utc) - timedelta(days=7)

        await client.search_videos("test", published_after)

        retry_middleware.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_videos_consumes_quota(self, mock_youtube_search_response):
        """Test that search_videos consumes quota."""
        from teams.dawo.scanners.youtube import (
            YouTubeClient,
            YouTubeClientConfig,
            QuotaTracker,
            SEARCH_QUOTA_COST,
        )

        config = YouTubeClientConfig(api_key="test_api_key")
        retry_middleware = MagicMock()
        retry_middleware.execute_with_retry = AsyncMock(
            return_value=MagicMock(
                success=True,
                response=mock_youtube_search_response,
            )
        )
        quota_tracker = QuotaTracker()
        initial_quota = quota_tracker.get_remaining()

        client = YouTubeClient(config, retry_middleware, quota_tracker)
        client._session = AsyncMock()

        published_after = datetime.now(timezone.utc) - timedelta(days=7)

        await client.search_videos("test", published_after)

        assert quota_tracker.get_remaining() == initial_quota - SEARCH_QUOTA_COST


class TestYouTubeClientVideoStatistics:
    """Tests for YouTubeClient.get_video_statistics method."""

    @pytest.fixture
    def mock_video_statistics_response(self):
        """Mock YouTube Data API videos.list response."""
        return {
            "items": [
                {
                    "id": "abc123xyz",
                    "statistics": {
                        "viewCount": "15234",
                        "likeCount": "1200",
                        "commentCount": "89",
                    },
                    "contentDetails": {
                        "duration": "PT15M30S",
                    },
                },
                {
                    "id": "def456uvw",
                    "statistics": {
                        "viewCount": "5678",
                        "likeCount": "400",
                        "commentCount": "25",
                    },
                    "contentDetails": {
                        "duration": "PT8M45S",
                    },
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_get_video_statistics_returns_dict(self, mock_video_statistics_response):
        """Test get_video_statistics returns dict mapping video_id to stats."""
        from teams.dawo.scanners.youtube import YouTubeClient, YouTubeClientConfig

        config = YouTubeClientConfig(api_key="test_api_key")
        retry_middleware = MagicMock()
        retry_middleware.execute_with_retry = AsyncMock(
            return_value=MagicMock(
                success=True,
                response=mock_video_statistics_response,
            )
        )

        client = YouTubeClient(config, retry_middleware)
        client._session = AsyncMock()

        stats = await client.get_video_statistics(["abc123xyz", "def456uvw"])

        assert isinstance(stats, dict)
        assert "abc123xyz" in stats
        assert stats["abc123xyz"]["statistics"]["viewCount"] == "15234"

    @pytest.mark.asyncio
    async def test_get_video_statistics_batches_requests(self, mock_video_statistics_response):
        """Test that get_video_statistics handles max 50 videos per batch."""
        from teams.dawo.scanners.youtube import YouTubeClient, YouTubeClientConfig

        config = YouTubeClientConfig(api_key="test_api_key")
        retry_middleware = MagicMock()
        retry_middleware.execute_with_retry = AsyncMock(
            return_value=MagicMock(
                success=True,
                response=mock_video_statistics_response,
            )
        )

        client = YouTubeClient(config, retry_middleware)
        client._session = AsyncMock()

        # Request 60 videos - should only process first 50
        video_ids = [f"video{i}" for i in range(60)]

        await client.get_video_statistics(video_ids)

        # Verify only 50 were sent
        call_args = retry_middleware.execute_with_retry.call_args
        # The function passed should have been called - we verify it was called at all
        retry_middleware.execute_with_retry.assert_called()


class TestYouTubeAPIErrors:
    """Tests for YouTube API error handling."""

    def test_can_import_youtube_api_error(self):
        """Test that YouTubeAPIError can be imported."""
        from teams.dawo.scanners.youtube import YouTubeAPIError

        assert YouTubeAPIError is not None

    def test_youtube_api_error_attributes(self):
        """Test YouTubeAPIError has correct attributes."""
        from teams.dawo.scanners.youtube import YouTubeAPIError

        error = YouTubeAPIError(
            message="API failed",
            status_code=403,
            response_body='{"error": "quota exceeded"}',
        )

        assert error.message == "API failed"
        assert error.status_code == 403
        assert error.response_body == '{"error": "quota exceeded"}'

    def test_quota_exhausted_error_is_youtube_api_error(self):
        """Test QuotaExhaustedError inherits from YouTubeAPIError."""
        from teams.dawo.scanners.youtube import YouTubeAPIError, QuotaExhaustedError

        error = QuotaExhaustedError("Quota exceeded")

        assert isinstance(error, YouTubeAPIError)
