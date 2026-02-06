"""Tests for YouTube Scanner agent.

Tests Task 4: YouTubeScanner implementation for scan stage of Harvester Framework.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestYouTubeScanner:
    """Tests for YouTubeScanner class."""

    def test_can_import_youtube_scanner(self):
        """Test that YouTubeScanner can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeScanner

        assert YouTubeScanner is not None

    def test_youtube_scanner_accepts_config_injection(self):
        """Test that YouTubeScanner accepts config via constructor."""
        from teams.dawo.scanners.youtube import (
            YouTubeScanner,
            YouTubeScannerConfig,
            YouTubeClient,
            YouTubeClientConfig,
        )

        config = YouTubeScannerConfig(
            search_queries=["test query"],
            min_views=500,
        )
        client_config = YouTubeClientConfig(api_key="test_key")
        mock_retry = MagicMock()
        client = YouTubeClient(client_config, mock_retry)

        scanner = YouTubeScanner(config, client)

        assert scanner._config.min_views == 500
        assert scanner._config.search_queries == ["test query"]


class TestYouTubeScannerScan:
    """Tests for YouTubeScanner.scan method."""

    @pytest.fixture
    def mock_search_response(self):
        """Mock YouTube search API response."""
        return [
            {
                "kind": "youtube#searchResult",
                "id": {"videoId": "abc123xyz"},
                "snippet": {
                    "publishedAt": "2026-02-01T10:00:00Z",
                    "channelId": "UCxxxxxxx",
                    "title": "Lion's Mane Benefits",
                    "description": "Video about lion's mane...",
                    "channelTitle": "Health Science Channel",
                    "thumbnails": {"default": {"url": "https://i.ytimg.com/abc.jpg"}},
                },
            },
            {
                "kind": "youtube#searchResult",
                "id": {"videoId": "def456uvw"},
                "snippet": {
                    "publishedAt": "2026-02-02T15:30:00Z",
                    "channelId": "UCyyyyyyy",
                    "title": "Mushroom Supplements Review",
                    "description": "Comparing supplements...",
                    "channelTitle": "Wellness Reviews",
                    "thumbnails": {"default": {"url": "https://i.ytimg.com/def.jpg"}},
                },
            },
        ]

    @pytest.fixture
    def scanner_with_mock_client(self, mock_search_response):
        """Create scanner with mocked client."""
        from teams.dawo.scanners.youtube import (
            YouTubeScanner,
            YouTubeScannerConfig,
            YouTubeClient,
            YouTubeClientConfig,
        )

        config = YouTubeScannerConfig(
            search_queries=["mushroom supplements"],
            min_views=1000,
            days_back=7,
            max_videos_per_query=50,
        )

        client_config = YouTubeClientConfig(api_key="test_key")
        mock_retry = MagicMock()
        client = YouTubeClient(client_config, mock_retry)

        # Mock search_videos method
        client.search_videos = AsyncMock(return_value=mock_search_response)

        return YouTubeScanner(config, client)

    @pytest.mark.asyncio
    async def test_scan_returns_scan_result(self, scanner_with_mock_client):
        """Test scan returns ScanResult with videos."""
        from teams.dawo.scanners.youtube import ScanResult

        result = await scanner_with_mock_client.scan()

        assert isinstance(result, ScanResult)
        assert len(result.videos) == 2

    @pytest.mark.asyncio
    async def test_scan_converts_to_raw_youtube_video(self, scanner_with_mock_client):
        """Test scan converts API response to RawYouTubeVideo objects."""
        from teams.dawo.scanners.youtube import RawYouTubeVideo

        result = await scanner_with_mock_client.scan()

        assert all(isinstance(v, RawYouTubeVideo) for v in result.videos)
        assert result.videos[0].video_id == "abc123xyz"
        assert result.videos[0].title == "Lion's Mane Benefits"
        assert result.videos[0].channel_title == "Health Science Channel"

    @pytest.mark.asyncio
    async def test_scan_searches_all_queries(self):
        """Test scan searches all configured queries."""
        from teams.dawo.scanners.youtube import (
            YouTubeScanner,
            YouTubeScannerConfig,
            YouTubeClient,
            YouTubeClientConfig,
        )

        config = YouTubeScannerConfig(
            search_queries=["query1", "query2", "query3"],
            min_views=1000,
        )

        client_config = YouTubeClientConfig(api_key="test_key")
        mock_retry = MagicMock()
        client = YouTubeClient(client_config, mock_retry)
        client.search_videos = AsyncMock(return_value=[])

        scanner = YouTubeScanner(config, client)
        await scanner.scan()

        # Should call search_videos 3 times (one per query)
        assert client.search_videos.call_count == 3

    @pytest.mark.asyncio
    async def test_scan_deduplicates_by_video_id(self):
        """Test scan removes duplicate videos by ID."""
        from teams.dawo.scanners.youtube import (
            YouTubeScanner,
            YouTubeScannerConfig,
            YouTubeClient,
            YouTubeClientConfig,
        )

        # Same video appearing in two different search results
        duplicate_response = [
            {
                "id": {"videoId": "same_video_id"},
                "snippet": {
                    "publishedAt": "2026-02-01T10:00:00Z",
                    "channelId": "UCxxx",
                    "title": "Same Video",
                    "description": "",
                    "channelTitle": "Channel",
                },
            }
        ]

        config = YouTubeScannerConfig(
            search_queries=["query1", "query2"],  # Two queries returning same video
            min_views=1000,
        )

        client_config = YouTubeClientConfig(api_key="test_key")
        mock_retry = MagicMock()
        client = YouTubeClient(client_config, mock_retry)
        client.search_videos = AsyncMock(return_value=duplicate_response)

        scanner = YouTubeScanner(config, client)
        result = await scanner.scan()

        # Should only have 1 unique video despite 2 queries
        assert len(result.videos) == 1
        assert result.statistics.duplicates_removed == 1

    @pytest.mark.asyncio
    async def test_scan_tracks_statistics(self, scanner_with_mock_client):
        """Test scan tracks query and video statistics."""
        result = await scanner_with_mock_client.scan()

        assert result.statistics.queries_searched == 1
        assert result.statistics.total_videos_found == 2
        assert result.statistics.videos_after_filter == 2

    @pytest.mark.asyncio
    async def test_scan_handles_api_errors_gracefully(self):
        """Test scan continues on API errors and collects them."""
        from teams.dawo.scanners.youtube import (
            YouTubeScanner,
            YouTubeScannerConfig,
            YouTubeClient,
            YouTubeClientConfig,
            YouTubeAPIError,
        )

        config = YouTubeScannerConfig(
            search_queries=["failing_query", "working_query"],
            min_views=1000,
        )

        client_config = YouTubeClientConfig(api_key="test_key")
        mock_retry = MagicMock()
        client = YouTubeClient(client_config, mock_retry)

        # First query fails, second succeeds
        client.search_videos = AsyncMock(
            side_effect=[
                YouTubeAPIError("API error"),
                [
                    {
                        "id": {"videoId": "video1"},
                        "snippet": {
                            "publishedAt": "2026-02-01T10:00:00Z",
                            "channelId": "UCxxx",
                            "title": "Video",
                            "description": "",
                            "channelTitle": "Channel",
                        },
                    }
                ],
            ]
        )

        scanner = YouTubeScanner(config, client)
        result = await scanner.scan()

        # Should still have video from working query
        assert len(result.videos) == 1
        # Should have recorded the error
        assert len(result.errors) == 1
        assert "failing_query" in result.errors[0]

    @pytest.mark.asyncio
    async def test_scan_parses_publish_date(self, scanner_with_mock_client):
        """Test scan correctly parses video publish date."""
        result = await scanner_with_mock_client.scan()

        video = result.videos[0]
        assert video.published_at.year == 2026
        assert video.published_at.month == 2
        assert video.published_at.day == 1


class TestYouTubeScannerHealthChannelDetection:
    """Tests for health channel detection."""

    def test_is_health_channel_detects_keywords(self):
        """Test _is_health_channel detects health-related keywords."""
        from teams.dawo.scanners.youtube import (
            YouTubeScanner,
            YouTubeScannerConfig,
            YouTubeClient,
            YouTubeClientConfig,
        )

        config = YouTubeScannerConfig()
        client_config = YouTubeClientConfig(api_key="test_key")
        mock_retry = MagicMock()
        client = YouTubeClient(client_config, mock_retry)

        scanner = YouTubeScanner(config, client)

        assert scanner._is_health_channel("Health Science Channel") is True
        assert scanner._is_health_channel("Dr. Wellness Reviews") is True
        assert scanner._is_health_channel("Medical Research Today") is True
        assert scanner._is_health_channel("Random Gaming Channel") is False
