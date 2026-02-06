"""Tests for YouTube Transcript API client.

Tests Task 3: TranscriptClient implementation using youtube-transcript-api.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTranscriptClient:
    """Tests for TranscriptClient class."""

    def test_can_import_transcript_client(self):
        """Test that TranscriptClient can be imported from module."""
        from teams.dawo.scanners.youtube import TranscriptClient

        assert TranscriptClient is not None

    def test_transcript_client_accepts_config_injection(self):
        """Test that TranscriptClient accepts config via constructor."""
        from teams.dawo.scanners.youtube import TranscriptClient, TranscriptConfig

        config = TranscriptConfig(preferred_languages=["en", "no"])
        retry_middleware = MagicMock()

        client = TranscriptClient(config, retry_middleware)

        assert client._config.preferred_languages == ["en", "no"]


class TestTranscriptClientGetTranscript:
    """Tests for TranscriptClient.get_transcript method."""

    @pytest.fixture
    def mock_transcript_segments(self):
        """Mock transcript segments from youtube-transcript-api."""
        return [
            {"text": "Today we're talking about lion's mane mushroom.", "start": 0.0, "duration": 3.0},
            {"text": "Studies show it may support cognitive function.", "start": 3.0, "duration": 4.0},
            {"text": "The typical dosage ranges from 500mg to 3000mg.", "start": 7.0, "duration": 4.0},
        ]

    @pytest.fixture
    def mock_ytt_api(self, mock_transcript_segments):
        """Create mock YouTubeTranscriptApi instance."""
        mock_transcript = MagicMock()
        mock_transcript.language_code = "en"
        mock_transcript.fetch.return_value = mock_transcript_segments

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript

        mock_api = MagicMock()
        mock_api.list.return_value = mock_transcript_list

        return mock_api, mock_transcript_list, mock_transcript

    @pytest.mark.asyncio
    async def test_get_transcript_returns_transcript_result(self, mock_ytt_api):
        """Test get_transcript returns TranscriptResult."""
        from teams.dawo.scanners.youtube import (
            TranscriptClient,
            TranscriptConfig,
            TranscriptResult,
        )

        mock_api, _, _ = mock_ytt_api
        config = TranscriptConfig()
        retry_middleware = MagicMock()

        with patch(
            "teams.dawo.scanners.youtube.tools.YouTubeTranscriptApi",
            return_value=mock_api,
        ):
            client = TranscriptClient(config, retry_middleware)
            result = await client.get_transcript("abc123xyz")

        assert isinstance(result, TranscriptResult)
        assert result.available is True
        assert "lion's mane" in result.text
        assert "cognitive function" in result.text
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_get_transcript_prefers_manual_over_auto(self, mock_ytt_api):
        """Test that manual captions are preferred over auto-generated."""
        from teams.dawo.scanners.youtube import TranscriptClient, TranscriptConfig

        mock_api, mock_transcript_list, _ = mock_ytt_api
        config = TranscriptConfig()
        retry_middleware = MagicMock()

        with patch(
            "teams.dawo.scanners.youtube.tools.YouTubeTranscriptApi",
            return_value=mock_api,
        ):
            client = TranscriptClient(config, retry_middleware)
            result = await client.get_transcript("abc123xyz")

        # Should call manual first
        mock_transcript_list.find_manually_created_transcript.assert_called_once()
        assert result.is_auto_generated is False

    @pytest.mark.asyncio
    async def test_get_transcript_falls_back_to_auto_generated(self, mock_transcript_segments):
        """Test fallback to auto-generated when manual unavailable."""
        from teams.dawo.scanners.youtube import TranscriptClient, TranscriptConfig
        from youtube_transcript_api import NoTranscriptFound

        config = TranscriptConfig()
        retry_middleware = MagicMock()

        # Mock auto-generated transcript
        mock_auto = MagicMock()
        mock_auto.language_code = "en"
        mock_auto.fetch.return_value = mock_transcript_segments

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_manually_created_transcript.side_effect = NoTranscriptFound(
            "video_id", ["en"], None
        )
        mock_transcript_list.find_generated_transcript.return_value = mock_auto

        mock_api = MagicMock()
        mock_api.list.return_value = mock_transcript_list

        with patch(
            "teams.dawo.scanners.youtube.tools.YouTubeTranscriptApi",
            return_value=mock_api,
        ):
            client = TranscriptClient(config, retry_middleware)
            result = await client.get_transcript("abc123xyz")

        assert result.is_auto_generated is True
        assert result.available is True

    @pytest.mark.asyncio
    async def test_get_transcript_handles_disabled_transcripts(self):
        """Test handling when transcripts are disabled for video."""
        from teams.dawo.scanners.youtube import TranscriptClient, TranscriptConfig
        from youtube_transcript_api import TranscriptsDisabled

        config = TranscriptConfig()
        retry_middleware = MagicMock()

        mock_api = MagicMock()
        mock_api.list.side_effect = TranscriptsDisabled("abc123xyz")

        with patch(
            "teams.dawo.scanners.youtube.tools.YouTubeTranscriptApi",
            return_value=mock_api,
        ):
            client = TranscriptClient(config, retry_middleware)
            result = await client.get_transcript("abc123xyz")

        assert result.available is False
        assert result.reason == "disabled"
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_get_transcript_handles_no_transcript_found(self):
        """Test handling when no transcript exists for video."""
        from teams.dawo.scanners.youtube import TranscriptClient, TranscriptConfig
        from youtube_transcript_api import NoTranscriptFound

        config = TranscriptConfig()
        retry_middleware = MagicMock()

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_manually_created_transcript.side_effect = NoTranscriptFound(
            "abc123xyz", ["en"], None
        )
        mock_transcript_list.find_generated_transcript.side_effect = NoTranscriptFound(
            "abc123xyz", ["en"], None
        )

        mock_api = MagicMock()
        mock_api.list.return_value = mock_transcript_list

        with patch(
            "teams.dawo.scanners.youtube.tools.YouTubeTranscriptApi",
            return_value=mock_api,
        ):
            client = TranscriptClient(config, retry_middleware)
            result = await client.get_transcript("abc123xyz")

        assert result.available is False
        assert result.reason == "not_found"

    @pytest.mark.asyncio
    async def test_get_transcript_concatenates_segments(self, mock_ytt_api):
        """Test that transcript segments are concatenated into full text."""
        from teams.dawo.scanners.youtube import TranscriptClient, TranscriptConfig

        mock_api, _, _ = mock_ytt_api
        config = TranscriptConfig()
        retry_middleware = MagicMock()

        with patch(
            "teams.dawo.scanners.youtube.tools.YouTubeTranscriptApi",
            return_value=mock_api,
        ):
            client = TranscriptClient(config, retry_middleware)
            result = await client.get_transcript("abc123xyz")

        # All segments should be concatenated
        assert "lion's mane" in result.text
        assert "cognitive function" in result.text
        assert "500mg to 3000mg" in result.text

    @pytest.mark.asyncio
    async def test_get_transcript_calculates_duration(self, mock_ytt_api):
        """Test that duration is calculated from transcript segments."""
        from teams.dawo.scanners.youtube import TranscriptClient, TranscriptConfig

        mock_api, _, _ = mock_ytt_api
        config = TranscriptConfig()
        retry_middleware = MagicMock()

        with patch(
            "teams.dawo.scanners.youtube.tools.YouTubeTranscriptApi",
            return_value=mock_api,
        ):
            client = TranscriptClient(config, retry_middleware)
            result = await client.get_transcript("abc123xyz")

        # Last segment: start=7.0, duration=4.0, total=11.0
        assert result.duration_seconds == 11


class TestTranscriptError:
    """Tests for TranscriptError exception."""

    def test_can_import_transcript_error(self):
        """Test that TranscriptError can be imported."""
        from teams.dawo.scanners.youtube import TranscriptError

        assert TranscriptError is not None
