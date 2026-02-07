"""Integration tests for Reddit Research Scanner.

Tests the full pipeline with mocked external dependencies:
    - Full pipeline execution
    - Research Pool integration
    - Scoring integration
    - Retry middleware integration
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from teams.dawo.scanners.reddit import (
    RedditScanner,
    RedditClient,
    RedditScannerConfig,
    RedditClientConfig,
    RawRedditPost,
    HarvestedPost,
    PipelineStatus,
    RedditAPIError,
)
from teams.dawo.scanners.reddit.harvester import RedditHarvester
from teams.dawo.scanners.reddit.transformer import RedditTransformer
from teams.dawo.scanners.reddit.validator import RedditValidator
from teams.dawo.scanners.reddit.pipeline import RedditResearchPipeline
from teams.dawo.scanners.reddit.schemas import ScanResult, ScanStatistics
from teams.dawo.research import ResearchPublisher, ResearchSource
from teams.dawo.research.scoring import ResearchItemScorer
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    OverallStatus,
    ContentComplianceCheck,
)
from teams.dawo.validators.research_compliance import ResearchComplianceValidator
from teams.dawo.middleware.retry import RetryConfig, RetryMiddleware, RetryResult


class TestFullPipelineIntegration:
    """Tests for complete pipeline integration."""

    @pytest.fixture
    def mock_reddit_api_response(self) -> dict:
        """Mock Reddit API response for integration tests."""
        now = datetime.now(timezone.utc).timestamp()
        return {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "integration_test_1",
                            "title": "Lion's mane supplement experience",
                            "selftext": "Been taking lion's mane for 3 months. Great results for cognitive function and focus.",
                            "author": "test_user",
                            "subreddit": "Nootropics",
                            "score": 150,
                            "upvote_ratio": 0.95,
                            "num_comments": 45,
                            "permalink": "/r/Nootropics/comments/test1/lions_mane/",
                            "url": "https://reddit.com/r/Nootropics/comments/test1/lions_mane/",
                            "created_utc": now - 3600,
                            "is_self": True,
                        },
                    },
                    {
                        "kind": "t3",
                        "data": {
                            "id": "integration_test_2",
                            "title": "Chaga and reishi stack",
                            "selftext": "My daily mushroom stack includes chaga and reishi for immune support.",
                            "author": "mushroom_fan",
                            "subreddit": "Supplements",
                            "score": 75,
                            "upvote_ratio": 0.92,
                            "num_comments": 23,
                            "permalink": "/r/Supplements/comments/test2/chaga_reishi/",
                            "url": "https://reddit.com/r/Supplements/comments/test2/chaga_reishi/",
                            "created_utc": now - 7200,
                            "is_self": True,
                        },
                    },
                ],
            },
        }

    @pytest.mark.asyncio
    async def test_full_pipeline_mocked_reddit(
        self,
        mock_reddit_api_response: dict,
    ) -> None:
        """Test complete pipeline with mocked Reddit API."""
        now = datetime.now(timezone.utc).timestamp()

        # Setup mock Reddit client
        mock_client = AsyncMock(spec=RedditClient)
        mock_client.search_subreddit.return_value = [
            child["data"] for child in mock_reddit_api_response["data"]["children"]
        ]
        mock_client.get_post_details.side_effect = [
            mock_reddit_api_response["data"]["children"][0]["data"],
            mock_reddit_api_response["data"]["children"][1]["data"],
        ]

        # Setup mock compliance checker and wrap in ResearchComplianceValidator
        mock_checker = AsyncMock(spec=EUComplianceChecker)
        compliant_result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        mock_checker.check_content.return_value = compliant_result
        research_compliance = ResearchComplianceValidator(compliance_checker=mock_checker)

        # Setup mock scorer
        mock_scorer = MagicMock(spec=ResearchItemScorer)
        score_result = MagicMock()
        score_result.final_score = 7.5
        mock_scorer.calculate_score.return_value = score_result

        # Setup mock publisher
        mock_repository = AsyncMock()
        mock_publisher = AsyncMock(spec=ResearchPublisher)
        mock_publisher.publish_batch.return_value = 2
        mock_publisher.publish.return_value = MagicMock(id=uuid4())

        # Create pipeline components
        config = RedditScannerConfig(
            subreddits=["Nootropics"],
            keywords=["lion's mane"],
            min_upvotes=10,
        )
        scanner = RedditScanner(config, mock_client)
        harvester = RedditHarvester(mock_client)
        transformer = RedditTransformer()
        validator = RedditValidator(research_compliance)

        # Create and run pipeline
        pipeline = RedditResearchPipeline(
            scanner, harvester, transformer, validator, mock_scorer, mock_publisher
        )

        result = await pipeline.execute()

        # Verify pipeline completed successfully
        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 2
        assert result.statistics.harvested == 2
        assert result.statistics.transformed == 2
        assert result.statistics.validated == 2
        assert result.statistics.scored == 2
        assert result.statistics.published == 2

    @pytest.mark.asyncio
    async def test_pipeline_handles_partial_failures(
        self,
        mock_reddit_api_response: dict,
    ) -> None:
        """Test pipeline continues on individual item failures."""
        # Setup mock Reddit client
        mock_client = AsyncMock(spec=RedditClient)
        mock_client.search_subreddit.return_value = [
            child["data"] for child in mock_reddit_api_response["data"]["children"]
        ]
        # First post fails harvest, second succeeds
        mock_client.get_post_details.side_effect = [
            RedditAPIError("Post unavailable"),
            mock_reddit_api_response["data"]["children"][1]["data"],
        ]

        # Setup other mocks
        mock_checker = AsyncMock(spec=EUComplianceChecker)
        compliant_result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        mock_checker.check_content.return_value = compliant_result
        research_compliance = ResearchComplianceValidator(compliance_checker=mock_checker)

        mock_scorer = MagicMock(spec=ResearchItemScorer)
        score_result = MagicMock()
        score_result.final_score = 7.0
        mock_scorer.calculate_score.return_value = score_result

        mock_publisher = AsyncMock(spec=ResearchPublisher)
        mock_publisher.publish_batch.return_value = 1

        # Create pipeline
        config = RedditScannerConfig(
            subreddits=["Nootropics"],
            keywords=["lion's mane"],
            min_upvotes=10,
        )
        scanner = RedditScanner(config, mock_client)
        harvester = RedditHarvester(mock_client)
        transformer = RedditTransformer()
        validator = RedditValidator(research_compliance)

        pipeline = RedditResearchPipeline(
            scanner, harvester, transformer, validator, mock_scorer, mock_publisher
        )

        result = await pipeline.execute()

        # Should complete with partial results
        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 2
        assert result.statistics.harvested == 1  # One failed
        assert result.statistics.published == 1


class TestRetryMiddlewareIntegration:
    """Tests for retry middleware integration."""

    @pytest.mark.asyncio
    async def test_client_uses_retry_middleware(self) -> None:
        """Test that Reddit client properly integrates with retry middleware."""
        config = RedditClientConfig(
            client_id="test_id",
            client_secret="test_secret",
            username="test_user",
            password="test_pass",
        )

        retry_config = RetryConfig(
            max_retries=3,
            base_delay=0.1,
            max_delay=1.0,
        )
        retry_middleware = RetryMiddleware(retry_config)

        # Mock the retry middleware's execute_with_retry to track calls
        original_execute = retry_middleware.execute_with_retry
        call_count = 0

        async def mock_execute(operation, context):
            nonlocal call_count
            call_count += 1
            return RetryResult(
                success=True,
                response={"data": {"children": []}},
                attempts=1,
            )

        retry_middleware.execute_with_retry = mock_execute

        client = RedditClient(config, retry_middleware)

        # Mock authentication
        with patch.object(client, "_ensure_authenticated", new_callable=AsyncMock):
            with patch.object(client, "_rate_limit_wait", new_callable=AsyncMock):
                client._client = MagicMock()

                await client.search_subreddit("Test", "query")

        # Verify retry middleware was used
        assert call_count == 1


class TestResearchPoolIntegration:
    """Tests for Research Pool integration."""

    @pytest.mark.asyncio
    async def test_transformer_output_matches_research_schema(self) -> None:
        """Test that transformer output is compatible with Research Pool."""
        now = datetime.now(timezone.utc).timestamp()

        harvested = HarvestedPost(
            id="test123",
            subreddit="Nootropics",
            title="Lion's mane for cognitive support",
            selftext="My experience with lion's mane supplements...",
            author="test_user",
            score=100,
            upvote_ratio=0.95,
            num_comments=30,
            permalink="/r/Nootropics/comments/test123/",
            url="https://reddit.com/r/Nootropics/comments/test123/",
            created_utc=now - 3600,
        )

        transformer = RedditTransformer()
        result = await transformer.transform([harvested])

        assert len(result) == 1
        item = result[0]

        # Verify all required Research Pool fields are present
        assert item.source == ResearchSource.REDDIT
        assert item.title == harvested.title
        assert len(item.content) > 0
        assert item.url.startswith("https://")
        assert isinstance(item.tags, list)
        assert isinstance(item.source_metadata, dict)
        assert isinstance(item.created_at, datetime)

        # Verify source_metadata has Reddit-specific fields
        assert "subreddit" in item.source_metadata
        assert "author" in item.source_metadata
        assert "upvotes" in item.source_metadata

    @pytest.mark.asyncio
    async def test_validator_output_has_compliance_status(self) -> None:
        """Test that validator properly sets compliance status."""
        from teams.dawo.research import TransformedResearch

        item = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="Test research item",
            content="Content about lion's mane supplements",
            url="https://reddit.com/r/Test/comments/test/",
            tags=["lions_mane"],
            source_metadata={"subreddit": "Test"},
            created_at=datetime.now(timezone.utc),
        )

        # Mock compliance checker with WARNING result
        mock_checker = AsyncMock(spec=EUComplianceChecker)
        warning_result = ContentComplianceCheck(
            overall_status=OverallStatus.WARNING,
            flagged_phrases=[],
        )
        mock_checker.check_content.return_value = warning_result
        research_compliance = ResearchComplianceValidator(compliance_checker=mock_checker)

        validator = RedditValidator(research_compliance)
        result = await validator.validate([item])

        assert len(result) == 1
        assert result[0].compliance_status == "WARNING"


class TestScoringIntegration:
    """Tests for scoring engine integration."""

    @pytest.mark.asyncio
    async def test_scorer_receives_correct_input_format(self) -> None:
        """Test that pipeline passes correctly formatted data to scorer."""
        from teams.dawo.scanners.reddit.schemas import ValidatedResearch

        validated = ValidatedResearch(
            source="reddit",
            title="Test item",
            content="Test content",
            url="https://example.com/",
            tags=["test"],
            source_metadata={"subreddit": "Test", "upvotes": 100},
            created_at=datetime.now(timezone.utc),
            compliance_status="COMPLIANT",
        )

        # Track what scorer receives
        received_input = None

        mock_scorer = MagicMock(spec=ResearchItemScorer)

        def capture_input(item):
            nonlocal received_input
            received_input = item
            result = MagicMock()
            result.final_score = 7.5
            return result

        mock_scorer.calculate_score.side_effect = capture_input

        # Create minimal pipeline to test scorer integration
        mock_scanner = AsyncMock()
        mock_scanner.scan.return_value = ScanResult(posts=[])

        pipeline = RedditResearchPipeline(
            scanner=mock_scanner,
            harvester=AsyncMock(),
            transformer=AsyncMock(),
            validator=AsyncMock(),
            scorer=mock_scorer,
            publisher=AsyncMock(),
        )

        # Call _score_items directly to test
        await pipeline._score_items([validated])

        # Verify scorer received correct format
        assert received_input is not None
        assert "title" in received_input
        assert "content" in received_input
        assert "source" in received_input
        assert "source_metadata" in received_input
        assert "compliance_status" in received_input
