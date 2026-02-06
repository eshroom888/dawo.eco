"""Tests for YouTube Harvester.

Tests Task 5: YouTubeHarvester implementation for harvest stage.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


class TestYouTubeHarvester:
    """Tests for YouTubeHarvester class."""

    def test_can_import_youtube_harvester(self):
        """Test that YouTubeHarvester can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeHarvester

        assert YouTubeHarvester is not None

    def test_harvester_accepts_dependencies(self):
        """Test that YouTubeHarvester accepts dependencies via constructor."""
        from teams.dawo.scanners.youtube import (
            YouTubeHarvester,
            YouTubeScannerConfig,
        )

        mock_youtube_client = MagicMock()
        mock_transcript_client = MagicMock()
        config = YouTubeScannerConfig()

        harvester = YouTubeHarvester(
            youtube_client=mock_youtube_client,
            transcript_client=mock_transcript_client,
            config=config,
        )

        assert harvester._youtube_client is mock_youtube_client
        assert harvester._transcript_client is mock_transcript_client


class TestYouTubeHarvesterHarvest:
    """Tests for YouTubeHarvester.harvest method."""

    @pytest.fixture
    def mock_video_stats(self):
        """Mock video statistics response."""
        return {
            "abc123": {
                "id": "abc123",
                "statistics": {
                    "viewCount": "15234",
                    "likeCount": "1200",
                    "commentCount": "89",
                },
                "contentDetails": {
                    "duration": "PT15M30S",
                },
            },
            "def456": {
                "id": "def456",
                "statistics": {
                    "viewCount": "500",  # Below min_views threshold
                    "likeCount": "50",
                    "commentCount": "10",
                },
                "contentDetails": {
                    "duration": "PT5M0S",
                },
            },
        }

    @pytest.fixture
    def mock_transcript_result(self):
        """Mock transcript result."""
        from teams.dawo.scanners.youtube import TranscriptResult

        return TranscriptResult(
            text="Video transcript text about lion's mane benefits...",
            language="en",
            is_auto_generated=False,
            available=True,
            duration_seconds=930,
        )

    @pytest.fixture
    def raw_videos(self):
        """Create raw videos for testing."""
        from teams.dawo.scanners.youtube import RawYouTubeVideo

        return [
            RawYouTubeVideo(
                video_id="abc123",
                title="Lion's Mane Benefits",
                channel_id="UCxxx",
                channel_title="Health Channel",
                published_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
                description="Video description",
            ),
            RawYouTubeVideo(
                video_id="def456",
                title="Low View Video",
                channel_id="UCyyy",
                channel_title="Small Channel",
                published_at=datetime(2026, 2, 2, 10, 0, 0, tzinfo=timezone.utc),
                description="Video with low views",
            ),
        ]

    @pytest.fixture
    def harvester(self, mock_video_stats, mock_transcript_result):
        """Create harvester with mocked dependencies."""
        from teams.dawo.scanners.youtube import (
            YouTubeHarvester,
            YouTubeScannerConfig,
        )

        mock_youtube_client = MagicMock()
        mock_youtube_client.get_video_statistics = AsyncMock(return_value=mock_video_stats)

        mock_transcript_client = MagicMock()
        mock_transcript_client.get_transcript = AsyncMock(return_value=mock_transcript_result)

        config = YouTubeScannerConfig(min_views=1000)

        return YouTubeHarvester(
            youtube_client=mock_youtube_client,
            transcript_client=mock_transcript_client,
            config=config,
        )

    @pytest.mark.asyncio
    async def test_harvest_returns_harvested_videos(self, harvester, raw_videos):
        """Test harvest returns list of HarvestedVideo objects."""
        from teams.dawo.scanners.youtube import HarvestedVideo

        result = await harvester.harvest(raw_videos)

        assert isinstance(result, list)
        assert all(isinstance(v, HarvestedVideo) for v in result)

    @pytest.mark.asyncio
    async def test_harvest_filters_by_min_views(self, harvester, raw_videos):
        """Test harvest filters out videos below min_views threshold."""
        result = await harvester.harvest(raw_videos)

        # Only abc123 has 15234 views (above 1000)
        # def456 has 500 views (below 1000)
        assert len(result) == 1
        assert result[0].video_id == "abc123"

    @pytest.mark.asyncio
    async def test_harvest_includes_statistics(self, harvester, raw_videos):
        """Test harvested videos include view count, likes, comments."""
        result = await harvester.harvest(raw_videos)

        video = result[0]
        assert video.view_count == 15234
        assert video.like_count == 1200
        assert video.comment_count == 89

    @pytest.mark.asyncio
    async def test_harvest_includes_transcript(self, harvester, raw_videos):
        """Test harvested videos include transcript text."""
        result = await harvester.harvest(raw_videos)

        video = result[0]
        assert video.transcript_available is True
        assert "lion's mane" in video.transcript
        assert video.transcript_language == "en"

    @pytest.mark.asyncio
    async def test_harvest_parses_duration(self, harvester, raw_videos):
        """Test harvester correctly parses video duration."""
        result = await harvester.harvest(raw_videos)

        video = result[0]
        # PT15M30S = 15*60 + 30 = 930 seconds
        assert video.duration_seconds == 930

    @pytest.mark.asyncio
    async def test_harvest_handles_empty_list(self, harvester):
        """Test harvest handles empty input list."""
        result = await harvester.harvest([])

        assert result == []

    @pytest.mark.asyncio
    async def test_harvest_handles_missing_transcript(self, raw_videos):
        """Test harvest handles videos without transcripts."""
        from teams.dawo.scanners.youtube import (
            YouTubeHarvester,
            YouTubeScannerConfig,
            TranscriptResult,
        )

        mock_youtube_client = MagicMock()
        mock_youtube_client.get_video_statistics = AsyncMock(
            return_value={
                "abc123": {
                    "statistics": {"viewCount": "5000", "likeCount": "100", "commentCount": "10"},
                    "contentDetails": {"duration": "PT10M0S"},
                }
            }
        )

        # Transcript unavailable
        mock_transcript_client = MagicMock()
        mock_transcript_client.get_transcript = AsyncMock(
            return_value=TranscriptResult(
                text="",
                available=False,
                reason="disabled",
            )
        )

        config = YouTubeScannerConfig(min_views=1000)
        harvester = YouTubeHarvester(mock_youtube_client, mock_transcript_client, config)

        result = await harvester.harvest([raw_videos[0]])

        assert len(result) == 1
        assert result[0].transcript_available is False
        assert result[0].transcript == ""


class TestHarvesterError:
    """Tests for HarvesterError exception."""

    def test_can_import_harvester_error(self):
        """Test that HarvesterError can be imported."""
        from teams.dawo.scanners.youtube import HarvesterError

        assert HarvesterError is not None

    def test_harvester_error_with_partial_results(self):
        """Test HarvesterError stores partial results."""
        from teams.dawo.scanners.youtube import HarvesterError

        error = HarvesterError(
            message="API failed",
            partial_results=[MagicMock()],
        )

        assert error.message == "API failed"
        assert len(error.partial_results) == 1


class TestDurationParsing:
    """Tests for duration parsing."""

    def test_parse_duration_minutes_and_seconds(self):
        """Test parsing PT15M30S format."""
        from teams.dawo.scanners.youtube import YouTubeHarvester, YouTubeScannerConfig

        harvester = YouTubeHarvester(MagicMock(), MagicMock(), YouTubeScannerConfig())

        stats = {"contentDetails": {"duration": "PT15M30S"}}
        assert harvester._parse_duration(stats) == 930

    def test_parse_duration_hours(self):
        """Test parsing PT1H30M0S format."""
        from teams.dawo.scanners.youtube import YouTubeHarvester, YouTubeScannerConfig

        harvester = YouTubeHarvester(MagicMock(), MagicMock(), YouTubeScannerConfig())

        stats = {"contentDetails": {"duration": "PT1H30M0S"}}
        assert harvester._parse_duration(stats) == 5400

    def test_parse_duration_seconds_only(self):
        """Test parsing PT45S format."""
        from teams.dawo.scanners.youtube import YouTubeHarvester, YouTubeScannerConfig

        harvester = YouTubeHarvester(MagicMock(), MagicMock(), YouTubeScannerConfig())

        stats = {"contentDetails": {"duration": "PT45S"}}
        assert harvester._parse_duration(stats) == 45

    def test_parse_duration_empty(self):
        """Test parsing empty duration returns 0."""
        from teams.dawo.scanners.youtube import YouTubeHarvester, YouTubeScannerConfig

        harvester = YouTubeHarvester(MagicMock(), MagicMock(), YouTubeScannerConfig())

        stats = {"contentDetails": {"duration": ""}}
        assert harvester._parse_duration(stats) == 0
