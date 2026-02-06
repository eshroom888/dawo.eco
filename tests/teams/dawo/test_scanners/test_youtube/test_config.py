"""Tests for YouTube scanner configuration.

Tests Task 1.6: YouTubeClientConfig, TranscriptConfig, YouTubeScannerConfig.
"""

import pytest


class TestYouTubeClientConfig:
    """Tests for YouTubeClientConfig dataclass."""

    def test_can_import_youtube_client_config(self):
        """Test that YouTubeClientConfig can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeClientConfig

        assert YouTubeClientConfig is not None

    def test_youtube_client_config_valid(self):
        """Test creating YouTubeClientConfig with valid API key."""
        from teams.dawo.scanners.youtube import YouTubeClientConfig

        config = YouTubeClientConfig(api_key="test_api_key_123")

        assert config.api_key == "test_api_key_123"

    def test_youtube_client_config_validates_api_key(self):
        """Test that empty API key raises ValueError."""
        from teams.dawo.scanners.youtube import YouTubeClientConfig

        with pytest.raises(ValueError, match="api_key"):
            YouTubeClientConfig(api_key="")


class TestTranscriptConfig:
    """Tests for TranscriptConfig dataclass."""

    def test_can_import_transcript_config(self):
        """Test that TranscriptConfig can be imported from module."""
        from teams.dawo.scanners.youtube import TranscriptConfig

        assert TranscriptConfig is not None

    def test_transcript_config_defaults(self):
        """Test TranscriptConfig has sensible defaults."""
        from teams.dawo.scanners.youtube import TranscriptConfig

        config = TranscriptConfig()

        assert "en" in config.preferred_languages
        assert config.max_transcript_length > 0

    def test_transcript_config_custom_languages(self):
        """Test TranscriptConfig accepts custom language list."""
        from teams.dawo.scanners.youtube import TranscriptConfig

        config = TranscriptConfig(preferred_languages=["no", "en"])

        assert config.preferred_languages == ["no", "en"]


class TestYouTubeScannerConfig:
    """Tests for YouTubeScannerConfig dataclass."""

    def test_can_import_youtube_scanner_config(self):
        """Test that YouTubeScannerConfig can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeScannerConfig

        assert YouTubeScannerConfig is not None

    def test_youtube_scanner_config_defaults(self):
        """Test YouTubeScannerConfig has sensible defaults."""
        from teams.dawo.scanners.youtube import YouTubeScannerConfig

        config = YouTubeScannerConfig()

        assert len(config.search_queries) > 0
        assert "mushroom supplements" in config.search_queries
        assert config.min_views == 1000
        assert config.days_back == 7
        assert config.max_videos_per_query == 50

    def test_youtube_scanner_config_validates_min_views(self):
        """Test that negative min_views raises ValueError."""
        from teams.dawo.scanners.youtube import YouTubeScannerConfig

        with pytest.raises(ValueError, match="min_views"):
            YouTubeScannerConfig(min_views=-1)

    def test_youtube_scanner_config_validates_days_back(self):
        """Test that days_back must be positive."""
        from teams.dawo.scanners.youtube import YouTubeScannerConfig

        with pytest.raises(ValueError, match="days_back"):
            YouTubeScannerConfig(days_back=0)

    def test_youtube_scanner_config_validates_search_queries(self):
        """Test that empty search_queries raises ValueError."""
        from teams.dawo.scanners.youtube import YouTubeScannerConfig

        with pytest.raises(ValueError, match="search_queries"):
            YouTubeScannerConfig(search_queries=[])
