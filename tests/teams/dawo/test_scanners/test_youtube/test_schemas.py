"""Tests for YouTube scanner schemas.

Tests Task 1.7: Schema definitions for RawYouTubeVideo, HarvestedVideo,
QuotableInsight, InsightResult, TranscriptResult, and pipeline status.
"""

import pytest
from datetime import datetime, timezone


class TestRawYouTubeVideo:
    """Tests for RawYouTubeVideo schema."""

    def test_can_import_raw_youtube_video(self):
        """Test that RawYouTubeVideo can be imported from module."""
        from teams.dawo.scanners.youtube import RawYouTubeVideo

        assert RawYouTubeVideo is not None

    def test_raw_youtube_video_creation(self):
        """Test creating a RawYouTubeVideo with required fields."""
        from teams.dawo.scanners.youtube import RawYouTubeVideo

        video = RawYouTubeVideo(
            video_id="abc123xyz",
            title="Lion's Mane Benefits",
            channel_id="UCxxxxxxx",
            channel_title="Health Science Channel",
            published_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
            description="Video about lion's mane...",
        )

        assert video.video_id == "abc123xyz"
        assert video.title == "Lion's Mane Benefits"
        assert video.channel_id == "UCxxxxxxx"
        assert video.channel_title == "Health Science Channel"


class TestHarvestedVideo:
    """Tests for HarvestedVideo schema."""

    def test_can_import_harvested_video(self):
        """Test that HarvestedVideo can be imported from module."""
        from teams.dawo.scanners.youtube import HarvestedVideo

        assert HarvestedVideo is not None

    def test_harvested_video_includes_statistics(self):
        """Test that HarvestedVideo includes view count, likes, comments."""
        from teams.dawo.scanners.youtube import HarvestedVideo

        video = HarvestedVideo(
            video_id="abc123xyz",
            title="Lion's Mane Benefits",
            channel_id="UCxxxxxxx",
            channel_title="Health Science Channel",
            published_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
            description="Video description",
            view_count=15234,
            like_count=1200,
            comment_count=89,
            duration_seconds=930,
        )

        assert video.view_count == 15234
        assert video.like_count == 1200
        assert video.comment_count == 89
        assert video.duration_seconds == 930


class TestTranscriptResult:
    """Tests for TranscriptResult schema."""

    def test_can_import_transcript_result(self):
        """Test that TranscriptResult can be imported from module."""
        from teams.dawo.scanners.youtube import TranscriptResult

        assert TranscriptResult is not None

    def test_transcript_result_available(self):
        """Test TranscriptResult with available transcript."""
        from teams.dawo.scanners.youtube import TranscriptResult

        result = TranscriptResult(
            text="Today we're talking about lion's mane...",
            language="en",
            is_auto_generated=False,
            available=True,
            duration_seconds=930,
        )

        assert result.available is True
        assert result.is_auto_generated is False
        assert len(result.text) > 0

    def test_transcript_result_unavailable(self):
        """Test TranscriptResult when transcript is unavailable."""
        from teams.dawo.scanners.youtube import TranscriptResult

        result = TranscriptResult(
            text="",
            available=False,
            reason="disabled",
        )

        assert result.available is False
        assert result.reason == "disabled"
        assert result.text == ""


class TestQuotableInsight:
    """Tests for QuotableInsight schema."""

    def test_can_import_quotable_insight(self):
        """Test that QuotableInsight can be imported from module."""
        from teams.dawo.scanners.youtube import QuotableInsight

        assert QuotableInsight is not None

    def test_quotable_insight_creation(self):
        """Test creating QuotableInsight with all fields."""
        from teams.dawo.scanners.youtube import QuotableInsight

        insight = QuotableInsight(
            text="Studies show lion's mane may support nerve growth factor production",
            context="Research reference from scientific study",
            topic="lion's mane cognition",
            is_claim=True,
        )

        assert "nerve growth factor" in insight.text
        assert insight.is_claim is True
        assert insight.topic == "lion's mane cognition"


class TestInsightResult:
    """Tests for InsightResult schema."""

    def test_can_import_insight_result(self):
        """Test that InsightResult can be imported from module."""
        from teams.dawo.scanners.youtube import InsightResult

        assert InsightResult is not None

    def test_insight_result_with_insights(self):
        """Test InsightResult with summary and quotable insights."""
        from teams.dawo.scanners.youtube import InsightResult, QuotableInsight

        result = InsightResult(
            main_summary="This video explores the science behind lion's mane mushroom benefits...",
            quotable_insights=[
                QuotableInsight(
                    text="Studies show lion's mane supports cognition",
                    context="Research reference",
                    topic="cognition",
                    is_claim=True,
                ),
            ],
            key_topics=["lions_mane", "cognition", "research"],
            confidence_score=0.85,
        )

        assert len(result.quotable_insights) == 1
        assert len(result.key_topics) == 3
        assert 0.0 <= result.confidence_score <= 1.0


class TestPipelineStatus:
    """Tests for PipelineStatus enum."""

    def test_can_import_pipeline_status(self):
        """Test that PipelineStatus can be imported from module."""
        from teams.dawo.scanners.youtube import PipelineStatus

        assert PipelineStatus is not None

    def test_pipeline_status_values(self):
        """Test PipelineStatus enum values match expected states."""
        from teams.dawo.scanners.youtube import PipelineStatus

        assert PipelineStatus.COMPLETE.value == "COMPLETE"
        assert PipelineStatus.INCOMPLETE.value == "INCOMPLETE"
        assert PipelineStatus.PARTIAL.value == "PARTIAL"
        assert PipelineStatus.FAILED.value == "FAILED"
        # YouTube-specific status
        assert PipelineStatus.QUOTA_EXCEEDED.value == "QUOTA_EXCEEDED"
