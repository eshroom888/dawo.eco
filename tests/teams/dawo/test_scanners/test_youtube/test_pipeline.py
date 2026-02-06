"""Tests for YouTube Research Pipeline.

Tests Tasks 9-10: YouTubeResearchPipeline implementation that orchestrates
the complete Harvester Framework pipeline with publisher integration.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestYouTubeResearchPipeline:
    """Tests for YouTubeResearchPipeline class."""

    def test_can_import_youtube_research_pipeline(self):
        """Test that YouTubeResearchPipeline can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeResearchPipeline

        assert YouTubeResearchPipeline is not None

    def test_pipeline_accepts_all_dependencies(self):
        """Test that YouTubeResearchPipeline accepts all stage components."""
        from teams.dawo.scanners.youtube.pipeline import YouTubeResearchPipeline

        scanner = MagicMock()
        harvester = MagicMock()
        transformer = MagicMock()
        validator = MagicMock()
        scorer = MagicMock()
        publisher = MagicMock()

        pipeline = YouTubeResearchPipeline(
            scanner=scanner,
            harvester=harvester,
            transformer=transformer,
            validator=validator,
            scorer=scorer,
            publisher=publisher,
        )

        assert pipeline._scanner is scanner
        assert pipeline._harvester is harvester
        assert pipeline._transformer is transformer
        assert pipeline._validator is validator
        assert pipeline._scorer is scorer
        assert pipeline._publisher is publisher


class TestYouTubeResearchPipelineExecute:
    """Tests for YouTubeResearchPipeline.execute method."""

    @pytest.fixture
    def mock_scan_result(self):
        """Create mock ScanResult."""
        from teams.dawo.scanners.youtube import ScanResult, RawYouTubeVideo, ScanStatistics

        return ScanResult(
            videos=[
                RawYouTubeVideo(
                    video_id="abc123xyz",
                    title="Lion's Mane Benefits",
                    channel_id="UCxxxxxxx",
                    channel_title="Health Science Channel",
                    published_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
                    description="In this video...",
                ),
            ],
            statistics=ScanStatistics(queries_searched=3, total_videos_found=1),
        )

    @pytest.fixture
    def mock_harvested_videos(self):
        """Create mock HarvestedVideo list."""
        from teams.dawo.scanners.youtube import HarvestedVideo

        return [
            HarvestedVideo(
                video_id="abc123xyz",
                title="Lion's Mane Benefits",
                channel_id="UCxxxxxxx",
                channel_title="Health Science Channel",
                published_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
                description="In this video...",
                view_count=15000,
                like_count=1000,
                comment_count=50,
                duration_seconds=600,
                transcript="This video discusses lion's mane...",
                transcript_available=True,
            ),
        ]

    @pytest.fixture
    def mock_transformed_research(self):
        """Create mock TransformedResearch list."""
        from teams.dawo.research import TransformedResearch, ResearchSource

        return [
            TransformedResearch(
                source=ResearchSource.YOUTUBE,
                title="Lion's Mane Benefits",
                content="Summary: This video discusses lion's mane...",
                url="https://youtube.com/watch?v=abc123xyz",
                tags=["lions_mane", "cognition"],
                source_metadata={"channel": "Health Science Channel", "views": 15000},
                created_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

    @pytest.fixture
    def mock_validated_research(self):
        """Create mock ValidatedResearch list."""
        from teams.dawo.scanners.youtube import ValidatedResearch

        return [
            ValidatedResearch(
                source="youtube",
                title="Lion's Mane Benefits",
                content="Summary: This video discusses lion's mane...",
                url="https://youtube.com/watch?v=abc123xyz",
                tags=["lions_mane", "cognition"],
                source_metadata={"channel": "Health Science Channel", "views": 15000},
                created_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
                compliance_status="COMPLIANT",
            ),
        ]

    @pytest.mark.asyncio
    async def test_execute_returns_pipeline_result(
        self,
        mock_scan_result,
        mock_harvested_videos,
        mock_transformed_research,
        mock_validated_research,
    ):
        """Test execute returns PipelineResult."""
        from teams.dawo.scanners.youtube.pipeline import YouTubeResearchPipeline
        from teams.dawo.scanners.youtube import PipelineResult, PipelineStatus

        scanner = AsyncMock()
        scanner.scan = AsyncMock(return_value=mock_scan_result)

        harvester = AsyncMock()
        harvester.harvest = AsyncMock(return_value=mock_harvested_videos)

        transformer = AsyncMock()
        transformer.transform = AsyncMock(return_value=mock_transformed_research)

        validator = AsyncMock()
        validator.validate = AsyncMock(return_value=mock_validated_research)

        scorer = MagicMock()
        scorer.calculate_score = MagicMock(
            return_value=MagicMock(final_score=7.5)
        )

        publisher = AsyncMock()
        publisher.publish_batch = AsyncMock(return_value=1)

        pipeline = YouTubeResearchPipeline(
            scanner=scanner,
            harvester=harvester,
            transformer=transformer,
            validator=validator,
            scorer=scorer,
            publisher=publisher,
        )

        result = await pipeline.execute()

        assert isinstance(result, PipelineResult)
        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 1
        assert result.statistics.published == 1

    @pytest.mark.asyncio
    async def test_execute_handles_no_videos_found(self):
        """Test execute handles case with no videos found."""
        from teams.dawo.scanners.youtube.pipeline import YouTubeResearchPipeline
        from teams.dawo.scanners.youtube import ScanResult, ScanStatistics, PipelineStatus

        scanner = AsyncMock()
        scanner.scan = AsyncMock(
            return_value=ScanResult(videos=[], statistics=ScanStatistics())
        )

        pipeline = YouTubeResearchPipeline(
            scanner=scanner,
            harvester=AsyncMock(),
            transformer=AsyncMock(),
            validator=AsyncMock(),
            scorer=MagicMock(),
            publisher=AsyncMock(),
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 0

    @pytest.mark.asyncio
    async def test_execute_tracks_statistics(
        self,
        mock_scan_result,
        mock_harvested_videos,
        mock_transformed_research,
        mock_validated_research,
    ):
        """Test execute tracks statistics through each stage."""
        from teams.dawo.scanners.youtube.pipeline import YouTubeResearchPipeline

        scanner = AsyncMock()
        scanner.scan = AsyncMock(return_value=mock_scan_result)

        harvester = AsyncMock()
        harvester.harvest = AsyncMock(return_value=mock_harvested_videos)

        transformer = AsyncMock()
        transformer.transform = AsyncMock(return_value=mock_transformed_research)

        validator = AsyncMock()
        validator.validate = AsyncMock(return_value=mock_validated_research)

        scorer = MagicMock()
        scorer.calculate_score = MagicMock(
            return_value=MagicMock(final_score=7.5)
        )

        publisher = AsyncMock()
        publisher.publish_batch = AsyncMock(return_value=1)

        pipeline = YouTubeResearchPipeline(
            scanner=scanner,
            harvester=harvester,
            transformer=transformer,
            validator=validator,
            scorer=scorer,
            publisher=publisher,
        )

        result = await pipeline.execute()

        stats = result.statistics
        assert stats.total_found == 1
        assert stats.harvested == 1
        assert stats.transformed == 1
        assert stats.validated == 1
        assert stats.scored == 1
        assert stats.published == 1

    @pytest.mark.asyncio
    async def test_execute_handles_quota_exhausted(self, mock_scan_result):
        """Test execute handles quota exhausted gracefully."""
        from teams.dawo.scanners.youtube.pipeline import YouTubeResearchPipeline
        from teams.dawo.scanners.youtube import PipelineStatus, QuotaExhaustedError

        scanner = AsyncMock()
        scanner.scan = AsyncMock(side_effect=QuotaExhaustedError("Daily quota exceeded"))

        pipeline = YouTubeResearchPipeline(
            scanner=scanner,
            harvester=AsyncMock(),
            transformer=AsyncMock(),
            validator=AsyncMock(),
            scorer=MagicMock(),
            publisher=AsyncMock(),
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.QUOTA_EXCEEDED
        assert result.retry_after is not None


class TestPipelineError:
    """Tests for PipelineError exception."""

    def test_can_import_pipeline_error(self):
        """Test that PipelineError can be imported."""
        from teams.dawo.scanners.youtube import PipelineError

        assert PipelineError is not None

    def test_pipeline_error_with_statistics(self):
        """Test PipelineError stores statistics."""
        from teams.dawo.scanners.youtube.pipeline import PipelineError
        from teams.dawo.scanners.youtube import PipelineStatistics

        stats = PipelineStatistics(total_found=10, failed=5)
        error = PipelineError("Pipeline failed", statistics=stats)

        assert error.message == "Pipeline failed"
        assert error.statistics.total_found == 10
        assert error.statistics.failed == 5
