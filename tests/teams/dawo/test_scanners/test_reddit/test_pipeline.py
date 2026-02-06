"""Tests for Reddit Research Pipeline.

Tests:
    - Pipeline initialization
    - Full pipeline execution
    - Graceful degradation
    - Statistics tracking
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.scanners.reddit import (
    RedditScanner,
    RedditScannerConfig,
    RawRedditPost,
    HarvestedPost,
    ScanResult,
    PipelineStatus,
    RedditAPIError,
)
from teams.dawo.scanners.reddit.harvester import RedditHarvester
from teams.dawo.scanners.reddit.transformer import RedditTransformer
from teams.dawo.scanners.reddit.validator import RedditValidator
from teams.dawo.scanners.reddit.schemas import ValidatedResearch, ScanStatistics
from teams.dawo.scanners.reddit.pipeline import RedditResearchPipeline, PipelineError
from teams.dawo.research import ResearchPublisher, TransformedResearch, ResearchSource
from teams.dawo.research.scoring import ResearchItemScorer


@pytest.fixture
def mock_scanner() -> AsyncMock:
    """Mock RedditScanner."""
    scanner = AsyncMock(spec=RedditScanner)
    now = datetime.now(timezone.utc).timestamp()

    scanner.scan.return_value = ScanResult(
        posts=[
            RawRedditPost(
                id="abc123",
                subreddit="Nootropics",
                title="Test post",
                score=100,
                created_utc=now - 3600,
                permalink="/r/Nootropics/comments/abc123/",
            )
        ],
        statistics=ScanStatistics(total_posts_found=1, posts_after_filter=1),
    )
    return scanner


@pytest.fixture
def mock_harvester() -> AsyncMock:
    """Mock RedditHarvester."""
    harvester = AsyncMock(spec=RedditHarvester)
    now = datetime.now(timezone.utc).timestamp()

    harvester.harvest.return_value = [
        HarvestedPost(
            id="abc123",
            subreddit="Nootropics",
            title="Test post",
            selftext="Test content about lion's mane",
            author="user123",
            score=100,
            upvote_ratio=0.95,
            num_comments=50,
            permalink="/r/Nootropics/comments/abc123/",
            url="https://reddit.com/r/Nootropics/comments/abc123/",
            created_utc=now - 3600,
        )
    ]
    return harvester


@pytest.fixture
def mock_transformer() -> AsyncMock:
    """Mock RedditTransformer."""
    transformer = AsyncMock(spec=RedditTransformer)

    transformer.transform.return_value = [
        TransformedResearch(
            source=ResearchSource.REDDIT,
            title="Test post",
            content="Test content about lion's mane",
            url="https://reddit.com/r/Nootropics/comments/abc123/",
            tags=["lions_mane"],
            source_metadata={"subreddit": "Nootropics"},
            created_at=datetime.now(timezone.utc),
        )
    ]
    return transformer


@pytest.fixture
def mock_validator() -> AsyncMock:
    """Mock RedditValidator."""
    validator = AsyncMock(spec=RedditValidator)

    validator.validate.return_value = [
        ValidatedResearch(
            source="reddit",
            title="Test post",
            content="Test content about lion's mane",
            url="https://reddit.com/r/Nootropics/comments/abc123/",
            tags=["lions_mane"],
            source_metadata={"subreddit": "Nootropics"},
            created_at=datetime.now(timezone.utc),
            compliance_status="COMPLIANT",
        )
    ]
    return validator


@pytest.fixture
def mock_scorer() -> MagicMock:
    """Mock ResearchItemScorer."""
    scorer = MagicMock(spec=ResearchItemScorer)

    result = MagicMock()
    result.final_score = 7.5
    scorer.calculate_score.return_value = result

    return scorer


@pytest.fixture
def mock_publisher() -> AsyncMock:
    """Mock ResearchPublisher."""
    publisher = AsyncMock(spec=ResearchPublisher)

    result = MagicMock()
    result.id = uuid4()
    publisher.publish.return_value = result
    publisher.publish_batch.return_value = 1

    return publisher


class TestRedditResearchPipelineInit:
    """Tests for pipeline initialization."""

    def test_pipeline_creation(
        self,
        mock_scanner: AsyncMock,
        mock_harvester: AsyncMock,
        mock_transformer: AsyncMock,
        mock_validator: AsyncMock,
        mock_scorer: AsyncMock,
        mock_publisher: AsyncMock,
    ) -> None:
        """Pipeline should be created with all stage components."""
        pipeline = RedditResearchPipeline(
            mock_scanner,
            mock_harvester,
            mock_transformer,
            mock_validator,
            mock_scorer,
            mock_publisher,
        )

        assert pipeline._scanner == mock_scanner
        assert pipeline._harvester == mock_harvester
        assert pipeline._transformer == mock_transformer
        assert pipeline._validator == mock_validator
        assert pipeline._scorer == mock_scorer
        assert pipeline._publisher == mock_publisher


class TestRedditResearchPipelineExecute:
    """Tests for pipeline execution."""

    @pytest.mark.asyncio
    async def test_execute_returns_result(
        self,
        mock_scanner: AsyncMock,
        mock_harvester: AsyncMock,
        mock_transformer: AsyncMock,
        mock_validator: AsyncMock,
        mock_scorer: AsyncMock,
        mock_publisher: AsyncMock,
    ) -> None:
        """Execute should return PipelineResult."""
        pipeline = RedditResearchPipeline(
            mock_scanner,
            mock_harvester,
            mock_transformer,
            mock_validator,
            mock_scorer,
            mock_publisher,
        )

        result = await pipeline.execute()

        assert result.status in PipelineStatus
        assert result.statistics is not None

    @pytest.mark.asyncio
    async def test_execute_calls_all_stages(
        self,
        mock_scanner: AsyncMock,
        mock_harvester: AsyncMock,
        mock_transformer: AsyncMock,
        mock_validator: AsyncMock,
        mock_scorer: AsyncMock,
        mock_publisher: AsyncMock,
    ) -> None:
        """Execute should call all pipeline stages in order."""
        pipeline = RedditResearchPipeline(
            mock_scanner,
            mock_harvester,
            mock_transformer,
            mock_validator,
            mock_scorer,
            mock_publisher,
        )

        await pipeline.execute()

        mock_scanner.scan.assert_called_once()
        mock_harvester.harvest.assert_called_once()
        mock_transformer.transform.assert_called_once()
        mock_validator.validate.assert_called_once()
        mock_scorer.calculate_score.assert_called()

    @pytest.mark.asyncio
    async def test_execute_tracks_statistics(
        self,
        mock_scanner: AsyncMock,
        mock_harvester: AsyncMock,
        mock_transformer: AsyncMock,
        mock_validator: AsyncMock,
        mock_scorer: AsyncMock,
        mock_publisher: AsyncMock,
    ) -> None:
        """Execute should track statistics through each stage."""
        pipeline = RedditResearchPipeline(
            mock_scanner,
            mock_harvester,
            mock_transformer,
            mock_validator,
            mock_scorer,
            mock_publisher,
        )

        result = await pipeline.execute()

        stats = result.statistics
        assert stats.total_found >= 0
        assert stats.harvested >= 0
        assert stats.transformed >= 0
        assert stats.validated >= 0
        assert stats.scored >= 0


class TestRedditResearchPipelineGracefulDegradation:
    """Tests for graceful degradation on failures."""

    @pytest.mark.asyncio
    async def test_api_error_returns_incomplete(
        self,
        mock_harvester: AsyncMock,
        mock_transformer: AsyncMock,
        mock_validator: AsyncMock,
        mock_scorer: AsyncMock,
        mock_publisher: AsyncMock,
    ) -> None:
        """Reddit API error should return INCOMPLETE status."""
        mock_scanner = AsyncMock(spec=RedditScanner)
        mock_scanner.scan.side_effect = RedditAPIError("API unavailable")

        pipeline = RedditResearchPipeline(
            mock_scanner,
            mock_harvester,
            mock_transformer,
            mock_validator,
            mock_scorer,
            mock_publisher,
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.INCOMPLETE
        assert result.retry_scheduled is True
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_empty_scan_returns_complete(
        self,
        mock_harvester: AsyncMock,
        mock_transformer: AsyncMock,
        mock_validator: AsyncMock,
        mock_scorer: AsyncMock,
        mock_publisher: AsyncMock,
    ) -> None:
        """Empty scan result should return COMPLETE (nothing to process)."""
        mock_scanner = AsyncMock(spec=RedditScanner)
        mock_scanner.scan.return_value = ScanResult(posts=[], statistics=ScanStatistics())

        pipeline = RedditResearchPipeline(
            mock_scanner,
            mock_harvester,
            mock_transformer,
            mock_validator,
            mock_scorer,
            mock_publisher,
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 0


class TestRedditResearchPipelineStatuses:
    """Tests for pipeline status determination."""

    @pytest.mark.asyncio
    async def test_complete_status_on_success(
        self,
        mock_scanner: AsyncMock,
        mock_harvester: AsyncMock,
        mock_transformer: AsyncMock,
        mock_validator: AsyncMock,
        mock_scorer: AsyncMock,
        mock_publisher: AsyncMock,
    ) -> None:
        """Successful execution should return COMPLETE."""
        pipeline = RedditResearchPipeline(
            mock_scanner,
            mock_harvester,
            mock_transformer,
            mock_validator,
            mock_scorer,
            mock_publisher,
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_partial_status_on_item_failures(
        self,
        mock_scanner: AsyncMock,
        mock_harvester: AsyncMock,
        mock_transformer: AsyncMock,
        mock_validator: AsyncMock,
        mock_scorer: AsyncMock,
    ) -> None:
        """Some item failures should return PARTIAL."""
        # Publisher that fails some items
        mock_publisher = AsyncMock(spec=ResearchPublisher)
        mock_publisher.publish_batch.side_effect = Exception("Batch failed")
        mock_publisher.publish.side_effect = [
            MagicMock(id=uuid4()),  # First succeeds
            Exception("Publish failed"),  # Second fails
        ]

        # Add second item to validate
        mock_validator.validate.return_value = [
            ValidatedResearch(
                source="reddit",
                title="Test 1",
                content="Content 1",
                url="https://example.com/1",
                created_at=datetime.now(timezone.utc),
            ),
            ValidatedResearch(
                source="reddit",
                title="Test 2",
                content="Content 2",
                url="https://example.com/2",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        pipeline = RedditResearchPipeline(
            mock_scanner,
            mock_harvester,
            mock_transformer,
            mock_validator,
            mock_scorer,
            mock_publisher,
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.PARTIAL
        assert result.statistics.failed > 0
