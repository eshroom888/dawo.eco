"""Tests for news research pipeline."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from teams.dawo.scanners.news.pipeline import NewsResearchPipeline
from teams.dawo.scanners.news.schemas import (
    PipelineStatus,
    RawNewsArticle,
    HarvestedArticle,
    ValidatedResearch,
    NewsCategory,
    PriorityLevel,
    CategoryResult,
    PriorityScore,
    ScanResult,
    ScanStatistics,
)
from teams.dawo.scanners.news.agent import NewsScanner, NewsScanError


class TestNewsResearchPipeline:
    """Tests for NewsResearchPipeline."""

    @pytest.fixture
    def mock_scanner(self) -> AsyncMock:
        """Create mock scanner."""
        scanner = AsyncMock(spec=NewsScanner)
        scanner.scan.return_value = ScanResult(
            articles=[
                RawNewsArticle(
                    title="Test Article",
                    summary="Summary",
                    url="https://example.com/article",
                    published=datetime.now(timezone.utc),
                    source_name="TestSource",
                    is_tier_1=False,
                )
            ],
            statistics=ScanStatistics(
                feeds_processed=2,
                feeds_failed=0,
                total_articles_found=1,
                articles_after_filter=1,
                duplicates_removed=0,
            ),
        )
        return scanner

    @pytest.fixture
    def mock_harvester(self) -> MagicMock:
        """Create mock harvester."""
        harvester = MagicMock()
        harvester.harvest.return_value = [
            HarvestedArticle(
                title="Test Article",
                summary="Cleaned summary",
                url="https://example.com/article",
                published=datetime.now(timezone.utc),
                source_name="TestSource",
                is_tier_1=False,
            )
        ]
        return harvester

    @pytest.fixture
    def mock_transformer(self) -> MagicMock:
        """Create mock transformer."""
        transformer = MagicMock()
        transformer.transform.return_value = [
            (
                ValidatedResearch(
                    source="news",
                    title="Test Article",
                    content="Content",
                    url="https://example.com/article",
                    tags=["news"],
                    source_metadata={},
                    created_at=datetime.now(timezone.utc),
                    compliance_status="PENDING",
                    score=5.0,
                ),
                CategoryResult(
                    category=NewsCategory.GENERAL,
                    confidence=0.7,
                    is_regulatory=False,
                    priority_level=PriorityLevel.LOW,
                ),
                PriorityScore(base_score=2.0, final_score=3.0),
            )
        ]
        return transformer

    @pytest.fixture
    def mock_validator(self) -> MagicMock:
        """Create mock validator."""
        validator = MagicMock()
        validator.validate.return_value = [
            ValidatedResearch(
                source="news",
                title="Test Article",
                content="Content",
                url="https://example.com/article",
                tags=["news"],
                source_metadata={},
                created_at=datetime.now(timezone.utc),
                compliance_status="COMPLIANT",
                score=5.0,
            )
        ]
        return validator

    @pytest.fixture
    def mock_scorer(self) -> MagicMock:
        """Create mock scorer."""
        scorer = MagicMock()
        scorer.calculate_score.return_value = MagicMock(final_score=5.0)
        return scorer

    @pytest.fixture
    def mock_publisher(self) -> AsyncMock:
        """Create mock publisher."""
        publisher = AsyncMock()
        publisher.publish_batch.return_value = [MagicMock(id=uuid4())]
        return publisher

    @pytest.fixture
    def pipeline(
        self,
        mock_scanner: AsyncMock,
        mock_harvester: MagicMock,
        mock_transformer: MagicMock,
        mock_validator: MagicMock,
        mock_scorer: MagicMock,
        mock_publisher: AsyncMock,
    ) -> NewsResearchPipeline:
        """Create pipeline instance."""
        return NewsResearchPipeline(
            scanner=mock_scanner,
            harvester=mock_harvester,
            transformer=mock_transformer,
            validator=mock_validator,
            scorer=mock_scorer,
            publisher=mock_publisher,
        )

    @pytest.mark.asyncio
    async def test_execute_complete_pipeline(
        self,
        pipeline: NewsResearchPipeline,
    ) -> None:
        """Test complete pipeline execution."""
        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 1
        assert result.statistics.published == 1
        assert len(result.published_ids) == 1

    @pytest.mark.asyncio
    async def test_execute_calls_all_stages(
        self,
        pipeline: NewsResearchPipeline,
        mock_scanner: AsyncMock,
        mock_harvester: MagicMock,
        mock_transformer: MagicMock,
        mock_validator: MagicMock,
        mock_publisher: AsyncMock,
    ) -> None:
        """Test that all pipeline stages are called."""
        await pipeline.execute()

        mock_scanner.scan.assert_called_once()
        mock_harvester.harvest.assert_called_once()
        mock_transformer.transform.assert_called_once()
        mock_validator.validate.assert_called_once()
        mock_publisher.publish_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scan_failure_returns_incomplete(
        self,
        pipeline: NewsResearchPipeline,
        mock_scanner: AsyncMock,
    ) -> None:
        """Test that scan failure returns INCOMPLETE status."""
        mock_scanner.scan.side_effect = NewsScanError("All feeds failed")

        result = await pipeline.execute()

        assert result.status == PipelineStatus.INCOMPLETE
        assert result.retry_scheduled is True
        assert "All feeds failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_no_articles_returns_complete(
        self,
        pipeline: NewsResearchPipeline,
        mock_scanner: AsyncMock,
    ) -> None:
        """Test that empty results return COMPLETE status."""
        mock_scanner.scan.return_value = ScanResult(
            articles=[],
            statistics=ScanStatistics(feeds_processed=2),
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 0

    @pytest.mark.asyncio
    async def test_execute_partial_feed_failure_returns_partial(
        self,
        pipeline: NewsResearchPipeline,
        mock_scanner: AsyncMock,
    ) -> None:
        """Test that partial feed failure returns PARTIAL status."""
        mock_scanner.scan.return_value = ScanResult(
            articles=[
                RawNewsArticle(
                    title="Test",
                    summary="Summary",
                    url="https://example.com",
                    published=datetime.now(timezone.utc),
                    source_name="Source",
                    is_tier_1=False,
                )
            ],
            statistics=ScanStatistics(
                feeds_processed=1,
                feeds_failed=1,  # One feed failed
                total_articles_found=1,
            ),
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.PARTIAL
        assert "feeds failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_tracks_regulatory_flagged(
        self,
        pipeline: NewsResearchPipeline,
        mock_transformer: MagicMock,
    ) -> None:
        """Test that regulatory flagged items are tracked."""
        mock_transformer.transform.return_value = [
            (
                ValidatedResearch(
                    source="news",
                    title="Regulatory Article",
                    content="Content",
                    url="https://example.com/regulatory",
                    tags=["news", "regulatory"],
                    source_metadata={},
                    created_at=datetime.now(timezone.utc),
                    compliance_status="PENDING",
                    score=8.0,
                ),
                CategoryResult(
                    category=NewsCategory.REGULATORY,
                    confidence=0.9,
                    is_regulatory=True,
                    priority_level=PriorityLevel.HIGH,
                ),
                PriorityScore(base_score=6.0, final_score=8.0),
            )
        ]

        result = await pipeline.execute()

        assert result.statistics.regulatory_flagged == 1

    @pytest.mark.asyncio
    async def test_execute_critical_failure_returns_failed(
        self,
        pipeline: NewsResearchPipeline,
        mock_scanner: AsyncMock,
    ) -> None:
        """Test that critical failure returns FAILED status."""
        mock_scanner.scan.side_effect = Exception("Critical error")

        result = await pipeline.execute()

        assert result.status == PipelineStatus.FAILED
        assert "Critical error" in result.error

    @pytest.mark.asyncio
    async def test_execute_falls_back_to_individual_publish(
        self,
        pipeline: NewsResearchPipeline,
        mock_publisher: AsyncMock,
    ) -> None:
        """Test fallback to individual publishing on batch failure."""
        mock_publisher.publish_batch.side_effect = Exception("Batch failed")
        mock_publisher.publish.return_value = MagicMock(id=uuid4())

        result = await pipeline.execute()

        # Should still succeed via individual publishing
        assert result.status == PipelineStatus.COMPLETE
        mock_publisher.publish.assert_called()

    @pytest.mark.asyncio
    async def test_execute_statistics_accuracy(
        self,
        pipeline: NewsResearchPipeline,
    ) -> None:
        """Test that pipeline statistics are accurate."""
        result = await pipeline.execute()

        assert result.statistics.total_found == 1
        assert result.statistics.harvested == 1
        assert result.statistics.categorized == 1
        assert result.statistics.transformed == 1
        assert result.statistics.validated == 1
        assert result.statistics.scored == 1
        assert result.statistics.published == 1
        assert result.statistics.failed == 0
        assert result.statistics.feeds_processed == 2
        assert result.statistics.feeds_failed == 0
