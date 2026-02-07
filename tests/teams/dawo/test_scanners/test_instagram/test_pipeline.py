"""Tests for InstagramResearchPipeline.

Tests the full pipeline orchestration with mocked components.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.scanners.instagram import (
    InstagramResearchPipeline,
    PipelineError,
    InstagramScanner,
    InstagramHarvester,
    InstagramTransformer,
    InstagramValidator,
    PipelineResult,
    PipelineStatus,
    PipelineStatistics,
    ScanResult,
    ScanStatistics,
    RawInstagramPost,
    HarvestedPost,
    ValidatedResearch,
    RateLimitError,
    InstagramAPIError,
)


class TestInstagramResearchPipeline:
    """Test suite for InstagramResearchPipeline."""

    @pytest.fixture
    def mock_scanner(self):
        """Mock scanner that returns posts."""
        scanner = AsyncMock(spec=InstagramScanner)
        scanner.scan.return_value = ScanResult(
            posts=[
                RawInstagramPost(
                    media_id="post1",
                    permalink="https://instagram.com/p/1",
                    timestamp=datetime.now(timezone.utc),
                    caption="Lion's mane!",
                    media_type="IMAGE",
                    hashtag_source="lionsmane",
                    is_competitor=False,
                ),
            ],
            statistics=ScanStatistics(
                hashtags_searched=2,
                total_posts_found=1,
            ),
            errors=[],
        )
        return scanner

    @pytest.fixture
    def mock_harvester(self):
        """Mock harvester that returns harvested posts."""
        harvester = AsyncMock(spec=InstagramHarvester)
        harvester.harvest.return_value = [
            HarvestedPost(
                media_id="post1",
                permalink="https://instagram.com/p/1",
                caption="Lion's mane!",
                hashtags=["lionsmane"],
                likes=100,
                comments=10,
                media_type="IMAGE",
                account_name="user1",
                account_type="business",
                timestamp=datetime.now(timezone.utc),
                is_competitor=False,
            ),
        ]
        return harvester

    @pytest.fixture
    def mock_transformer(self):
        """Mock transformer that returns transformed items."""
        from teams.dawo.research import TransformedResearch, ResearchSource, ComplianceStatus

        transformer = AsyncMock(spec=InstagramTransformer)
        transformer.transform.return_value = [
            TransformedResearch(
                source=ResearchSource.INSTAGRAM,
                title="Lion's mane!",
                content="Content here",
                url="https://instagram.com/p/1",
                tags=["lionsmane"],
                source_metadata={"theme": {"content_type": "educational"}},
                created_at=datetime.now(timezone.utc),
                score=0.0,
                compliance_status=ComplianceStatus.COMPLIANT,
            ),
        ]
        return transformer

    @pytest.fixture
    def mock_validator(self):
        """Mock validator that returns validated items."""
        validator = AsyncMock(spec=InstagramValidator)
        validator.validate.return_value = [
            ValidatedResearch(
                source="instagram",
                title="Lion's mane!",
                content="Content here",
                url="https://instagram.com/p/1",
                tags=["lionsmane"],
                source_metadata={},
                created_at=datetime.now(timezone.utc),
                compliance_status="COMPLIANT",
                cleanmarket_flag=False,
                score=0.0,
            ),
        ]
        return validator

    @pytest.fixture
    def mock_scorer(self):
        """Mock scorer that returns scores."""
        scorer = MagicMock()
        scorer.calculate_score.return_value = MagicMock(final_score=7.5)
        return scorer

    @pytest.fixture
    def mock_publisher(self):
        """Mock publisher that returns success."""
        publisher = AsyncMock()
        publisher.publish_batch.return_value = 1
        return publisher

    @pytest.fixture
    def pipeline(self, mock_scanner, mock_harvester, mock_transformer, mock_validator, mock_scorer, mock_publisher):
        """Create pipeline with mocked components."""
        return InstagramResearchPipeline(
            scanner=mock_scanner,
            harvester=mock_harvester,
            transformer=mock_transformer,
            validator=mock_validator,
            scorer=mock_scorer,
            publisher=mock_publisher,
        )

    @pytest.mark.asyncio
    async def test_execute_returns_pipeline_result(self, pipeline):
        """Test that execute returns PipelineResult."""
        result = await pipeline.execute()

        assert isinstance(result, PipelineResult)
        assert isinstance(result.statistics, PipelineStatistics)

    @pytest.mark.asyncio
    async def test_execute_complete_status(self, pipeline):
        """Test successful pipeline returns COMPLETE status."""
        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_execute_tracks_statistics(self, pipeline):
        """Test that statistics are tracked through pipeline."""
        result = await pipeline.execute()

        assert result.statistics.total_found == 1
        assert result.statistics.harvested == 1
        assert result.statistics.published == 1

    @pytest.mark.asyncio
    async def test_execute_handles_rate_limit(self, pipeline, mock_scanner):
        """Test that rate limit error returns RATE_LIMITED status."""
        mock_scanner.scan.side_effect = RateLimitError("Rate limit exceeded")

        result = await pipeline.execute()

        assert result.status == PipelineStatus.RATE_LIMITED
        assert result.retry_scheduled == True
        assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_execute_handles_api_error(self, pipeline, mock_scanner):
        """Test that API error returns INCOMPLETE status."""
        mock_scanner.scan.side_effect = InstagramAPIError("API error")

        result = await pipeline.execute()

        assert result.status == PipelineStatus.INCOMPLETE
        assert result.retry_scheduled == True

    @pytest.mark.asyncio
    async def test_execute_no_posts_found(self, pipeline, mock_scanner):
        """Test that no posts returns COMPLETE status."""
        mock_scanner.scan.return_value = ScanResult(
            posts=[],
            statistics=ScanStatistics(),
            errors=[],
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 0

    @pytest.mark.asyncio
    async def test_execute_partial_status(self, pipeline, mock_publisher):
        """Test that some failures returns PARTIAL status."""
        # First item fails to publish
        mock_publisher.publish_batch.side_effect = Exception("Batch failed")
        mock_publisher.publish.side_effect = [
            Exception("Failed"),  # First fails
        ]

        result = await pipeline.execute()

        assert result.status in [PipelineStatus.PARTIAL, PipelineStatus.FAILED]


class TestPipelineStatistics:
    """Test suite for PipelineStatistics."""

    def test_default_values(self):
        """Test default statistic values."""
        stats = PipelineStatistics()

        assert stats.total_found == 0
        assert stats.harvested == 0
        assert stats.themes_extracted == 0
        assert stats.claims_detected == 0
        assert stats.cleanmarket_flagged == 0
        assert stats.published == 0


class TestPipelineStatus:
    """Test suite for PipelineStatus enum."""

    def test_status_values(self):
        """Test all expected status values exist."""
        assert PipelineStatus.COMPLETE.value == "COMPLETE"
        assert PipelineStatus.INCOMPLETE.value == "INCOMPLETE"
        assert PipelineStatus.PARTIAL.value == "PARTIAL"
        assert PipelineStatus.FAILED.value == "FAILED"
        assert PipelineStatus.RATE_LIMITED.value == "RATE_LIMITED"
