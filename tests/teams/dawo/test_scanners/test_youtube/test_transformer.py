"""Tests for YouTube Transformer.

Tests Task 7: YouTubeTransformer implementation that converts HarvestedVideo
objects with InsightResults to TransformedResearch for the Research Pool.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


class TestYouTubeTransformer:
    """Tests for YouTubeTransformer class."""

    def test_can_import_youtube_transformer(self):
        """Test that YouTubeTransformer can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeTransformer

        assert YouTubeTransformer is not None

    def test_transformer_accepts_insight_extractor_injection(self):
        """Test that YouTubeTransformer accepts KeyInsightExtractor via constructor."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer

        insight_extractor = MagicMock()

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        assert transformer._insight_extractor is insight_extractor


class TestYouTubeTransformerTransform:
    """Tests for YouTubeTransformer.transform method."""

    @pytest.fixture
    def sample_harvested_video(self):
        """Create a sample HarvestedVideo for testing."""
        from teams.dawo.scanners.youtube import HarvestedVideo

        return HarvestedVideo(
            video_id="abc123xyz",
            title="Lion's Mane Benefits: What Science Actually Says",
            channel_id="UCxxxxxxx",
            channel_title="Health Science Channel",
            published_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
            description="In this video we explore lion's mane benefits...",
            view_count=15234,
            like_count=1200,
            comment_count=89,
            duration_seconds=930,  # 15:30
            thumbnail_url="https://i.ytimg.com/vi/abc123xyz/default.jpg",
            transcript="Today we're talking about lion's mane mushroom benefits...",
            transcript_available=True,
            transcript_language="en",
            is_auto_generated=False,
        )

    @pytest.fixture
    def mock_insight_result(self):
        """Create a mock InsightResult."""
        from teams.dawo.scanners.youtube import InsightResult, QuotableInsight

        return InsightResult(
            main_summary="This video explores lion's mane mushroom cognitive benefits.",
            quotable_insights=[
                QuotableInsight(
                    text="Lion's mane stimulates nerve growth factor production.",
                    context="Discussing NGF mechanism",
                    topic="lions_mane cognition",
                    is_claim=True,
                ),
            ],
            key_topics=["lions_mane", "cognition", "research"],
            confidence_score=0.85,
        )

    @pytest.mark.asyncio
    async def test_transform_returns_transformed_research_list(
        self, sample_harvested_video, mock_insight_result
    ):
        """Test transform returns list of TransformedResearch."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer
        from teams.dawo.research import TransformedResearch

        insight_extractor = AsyncMock()
        insight_extractor.extract_insights = AsyncMock(return_value=mock_insight_result)

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        results = await transformer.transform([sample_harvested_video])

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], TransformedResearch)

    @pytest.mark.asyncio
    async def test_transform_maps_youtube_fields_correctly(
        self, sample_harvested_video, mock_insight_result
    ):
        """Test that transform maps YouTube fields to Research Pool schema."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer
        from teams.dawo.research import ResearchSource

        insight_extractor = AsyncMock()
        insight_extractor.extract_insights = AsyncMock(return_value=mock_insight_result)

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        results = await transformer.transform([sample_harvested_video])

        item = results[0]
        assert item.source == ResearchSource.YOUTUBE
        assert item.title == sample_harvested_video.title
        assert item.url == "https://youtube.com/watch?v=abc123xyz"
        assert item.created_at == sample_harvested_video.published_at

    @pytest.mark.asyncio
    async def test_transform_includes_source_metadata(
        self, sample_harvested_video, mock_insight_result
    ):
        """Test that transform includes YouTube-specific metadata."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer

        insight_extractor = AsyncMock()
        insight_extractor.extract_insights = AsyncMock(return_value=mock_insight_result)

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        results = await transformer.transform([sample_harvested_video])

        metadata = results[0].source_metadata
        assert metadata["channel"] == "Health Science Channel"
        assert metadata["views"] == 15234
        assert metadata["video_id"] == "abc123xyz"
        assert metadata["has_transcript"] is True
        assert metadata["insight_count"] == 1

    @pytest.mark.asyncio
    async def test_transform_combines_summary_and_insights_in_content(
        self, sample_harvested_video, mock_insight_result
    ):
        """Test that content includes summary and quotable insights."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer

        insight_extractor = AsyncMock()
        insight_extractor.extract_insights = AsyncMock(return_value=mock_insight_result)

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        results = await transformer.transform([sample_harvested_video])

        content = results[0].content
        assert "lion's mane mushroom cognitive benefits" in content.lower()
        assert "nerve growth factor" in content.lower()

    @pytest.mark.asyncio
    async def test_transform_generates_tags_from_topics(
        self, sample_harvested_video, mock_insight_result
    ):
        """Test that tags are generated from key topics."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer

        insight_extractor = AsyncMock()
        insight_extractor.extract_insights = AsyncMock(return_value=mock_insight_result)

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        results = await transformer.transform([sample_harvested_video])

        tags = results[0].tags
        assert "lions_mane" in tags
        assert "cognition" in tags

    @pytest.mark.asyncio
    async def test_transform_calls_insight_extractor_for_transcripts(
        self, sample_harvested_video, mock_insight_result
    ):
        """Test that transform calls insight extractor for videos with transcripts."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer

        insight_extractor = AsyncMock()
        insight_extractor.extract_insights = AsyncMock(return_value=mock_insight_result)

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        await transformer.transform([sample_harvested_video])

        insight_extractor.extract_insights.assert_called_once_with(
            transcript=sample_harvested_video.transcript,
            title=sample_harvested_video.title,
            channel_name=sample_harvested_video.channel_title,
        )

    @pytest.mark.asyncio
    async def test_transform_handles_videos_without_transcript(
        self, sample_harvested_video
    ):
        """Test that transform handles videos without transcripts."""
        from teams.dawo.scanners.youtube import HarvestedVideo
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer

        # Create video without transcript
        video_no_transcript = HarvestedVideo(
            video_id="def456uvw",
            title="Quick Tips Video",
            channel_id="UCyyyyyyy",
            channel_title="Tips Channel",
            published_at=datetime(2026, 2, 2, 15, 0, 0, tzinfo=timezone.utc),
            description="Some tips...",
            view_count=5000,
            like_count=300,
            comment_count=20,
            duration_seconds=120,
            transcript="",  # No transcript
            transcript_available=False,
        )

        insight_extractor = AsyncMock()
        # Should not be called for videos without transcript
        insight_extractor.extract_insights = AsyncMock()

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        results = await transformer.transform([video_no_transcript])

        # Should still produce a result but without insights
        assert len(results) == 1
        assert results[0].source_metadata["has_transcript"] is False
        # Insight extractor should NOT be called
        insight_extractor.extract_insights.assert_not_called()

    @pytest.mark.asyncio
    async def test_transform_handles_empty_list(self):
        """Test transform handles empty input list."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer

        insight_extractor = AsyncMock()
        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        results = await transformer.transform([])

        assert results == []

    @pytest.mark.asyncio
    async def test_transform_truncates_long_content(
        self, sample_harvested_video, mock_insight_result
    ):
        """Test that transform truncates content exceeding max length."""
        from teams.dawo.scanners.youtube.transformer import YouTubeTransformer
        from teams.dawo.scanners.youtube import InsightResult
        from teams.dawo.scanners.youtube.config import MAX_CONTENT_LENGTH

        # Create insight with very long summary
        long_summary = "A" * (MAX_CONTENT_LENGTH + 1000)
        long_insight = InsightResult(
            main_summary=long_summary,
            quotable_insights=[],
            key_topics=["test"],
            confidence_score=0.5,
        )

        insight_extractor = AsyncMock()
        insight_extractor.extract_insights = AsyncMock(return_value=long_insight)

        transformer = YouTubeTransformer(insight_extractor=insight_extractor)

        results = await transformer.transform([sample_harvested_video])

        assert len(results[0].content) <= MAX_CONTENT_LENGTH


class TestTransformerError:
    """Tests for TransformerError exception."""

    def test_can_import_transformer_error(self):
        """Test that TransformerError can be imported."""
        from teams.dawo.scanners.youtube import TransformerError

        assert TransformerError is not None

    def test_transformer_error_with_video_context(self):
        """Test TransformerError stores video context."""
        from teams.dawo.scanners.youtube.transformer import TransformerError

        error = TransformerError(
            message="Failed to extract insights",
            video_id="abc123",
        )

        assert error.message == "Failed to extract insights"
        assert error.video_id == "abc123"
