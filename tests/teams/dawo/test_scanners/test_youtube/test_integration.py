"""Integration tests for YouTube Research Scanner.

Tests Task 15: Integration tests verifying complete pipeline execution
with all components working together.

Test coverage:
    - 15.1 Full pipeline with mocked YouTube API
    - 15.2 Research Pool insertion (with mock repository)
    - 15.3 Scoring integration
    - 15.4 Retry middleware integration
    - 15.5 LLM insight extraction with mock responses
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestFullPipelineIntegration:
    """Integration tests for full YouTube Research Pipeline (Task 15.1)."""

    @pytest.fixture
    def mock_youtube_api_response(self):
        """Mock YouTube Data API search response."""
        return {
            "items": [
                {
                    "kind": "youtube#searchResult",
                    "id": {"videoId": "integration_test_1"},
                    "snippet": {
                        "publishedAt": "2026-02-01T10:00:00Z",
                        "channelId": "UCintegration",
                        "title": "Lion's Mane Benefits: Integration Test Video",
                        "description": "Testing the full pipeline...",
                        "channelTitle": "Integration Test Channel",
                    },
                },
                {
                    "kind": "youtube#searchResult",
                    "id": {"videoId": "integration_test_2"},
                    "snippet": {
                        "publishedAt": "2026-02-02T10:00:00Z",
                        "channelId": "UCintegration",
                        "title": "Cordyceps Review: Another Test",
                        "description": "More testing...",
                        "channelTitle": "Integration Test Channel",
                    },
                },
            ]
        }

    @pytest.fixture
    def mock_video_statistics(self):
        """Mock YouTube video statistics response."""
        return {
            "integration_test_1": {
                "id": "integration_test_1",
                "statistics": {
                    "viewCount": "15000",
                    "likeCount": "500",
                    "commentCount": "50",
                },
                "contentDetails": {"duration": "PT10M30S"},
            },
            "integration_test_2": {
                "id": "integration_test_2",
                "statistics": {
                    "viewCount": "8000",
                    "likeCount": "200",
                    "commentCount": "20",
                },
                "contentDetails": {"duration": "PT5M15S"},
            },
        }

    @pytest.fixture
    def mock_transcript_text(self):
        """Mock transcript text for testing."""
        return """
        Today we're discussing lion's mane mushroom and its potential cognitive benefits.
        Research has shown that lion's mane may support nerve growth factor production.
        The typical dosage ranges from 500mg to 3000mg daily.
        Let's explore the scientific studies behind these claims.
        """

    @pytest.mark.asyncio
    async def test_full_pipeline_executes_all_stages(
        self, mock_youtube_api_response, mock_video_statistics, mock_transcript_text
    ):
        """Test that pipeline executes scan -> harvest -> transform -> validate -> score -> publish."""
        from teams.dawo.scanners.youtube import (
            YouTubeScanner,
            YouTubeClient,
            TranscriptClient,
            YouTubeHarvester,
            YouTubeTransformer,
            YouTubeValidator,
            YouTubeResearchPipeline,
            YouTubeScannerConfig,
            YouTubeClientConfig,
            TranscriptConfig,
            TranscriptResult,
            PipelineStatus,
        )

        # Create mock clients
        mock_youtube_client = AsyncMock(spec=YouTubeClient)
        mock_youtube_client.search_videos.return_value = mock_youtube_api_response["items"]
        mock_youtube_client.get_video_statistics.return_value = mock_video_statistics

        mock_transcript_client = AsyncMock(spec=TranscriptClient)
        mock_transcript_client.get_transcript.return_value = TranscriptResult(
            text=mock_transcript_text,
            language="en",
            is_auto_generated=False,
            available=True,
            duration_seconds=630,
        )

        # Create mock insight extractor
        mock_insight_extractor = AsyncMock()
        mock_insight_extractor.extract_insights.return_value = MagicMock(
            main_summary="Test summary about lion's mane benefits.",
            quotable_insights=[],
            key_topics=["lions_mane", "cognition"],
            confidence_score=0.85,
        )

        # Create mock compliance checker
        mock_compliance_checker = AsyncMock()
        mock_compliance_checker.check_content.return_value = MagicMock(
            overall_status=MagicMock(value="COMPLIANT")
        )

        # Create mock scorer
        mock_scorer = MagicMock()
        mock_scorer.calculate_score.return_value = MagicMock(final_score=7.5)

        # Create mock publisher
        mock_publisher = AsyncMock()
        mock_publisher.publish_batch.return_value = 2

        # Create config
        config = YouTubeScannerConfig(
            search_queries=["lion's mane benefits"],
            min_views=1000,
            days_back=7,
            max_videos_per_query=10,
        )

        # Create pipeline components
        scanner = YouTubeScanner(config=config, client=mock_youtube_client)
        harvester = YouTubeHarvester(
            youtube_client=mock_youtube_client,
            transcript_client=mock_transcript_client,
            config=config,
        )
        transformer = YouTubeTransformer(insight_extractor=mock_insight_extractor)

        # Mock the validator's compliance checker
        validator = YouTubeValidator(compliance_checker=mock_compliance_checker)

        # Create pipeline
        pipeline = YouTubeResearchPipeline(
            scanner=scanner,
            harvester=harvester,
            transformer=transformer,
            validator=validator,
            scorer=mock_scorer,
            publisher=mock_publisher,
        )

        # Execute pipeline
        result = await pipeline.execute()

        # Verify all stages executed
        assert result.status in [PipelineStatus.COMPLETE, PipelineStatus.PARTIAL]
        assert result.statistics.total_found > 0
        assert result.statistics.harvested > 0
        assert result.statistics.transformed > 0
        assert result.statistics.validated > 0

        # Verify mocks were called
        mock_youtube_client.search_videos.assert_called()
        mock_youtube_client.get_video_statistics.assert_called()
        mock_transcript_client.get_transcript.assert_called()

    @pytest.mark.asyncio
    async def test_pipeline_handles_empty_search_results(self):
        """Test pipeline completes gracefully with no videos found."""
        from teams.dawo.scanners.youtube import (
            YouTubeScanner,
            YouTubeHarvester,
            YouTubeTransformer,
            YouTubeValidator,
            YouTubeResearchPipeline,
            YouTubeScannerConfig,
            PipelineStatus,
        )

        # Create mock client returning empty results
        mock_youtube_client = AsyncMock()
        mock_youtube_client.search_videos.return_value = []

        config = YouTubeScannerConfig(search_queries=["nonexistent query"])

        scanner = YouTubeScanner(config=config, client=mock_youtube_client)
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

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 0


class TestResearchPoolIntegration:
    """Integration tests for Research Pool insertion (Task 15.2)."""

    @pytest.mark.asyncio
    async def test_publisher_receives_transformed_research(self):
        """Test that publisher receives properly formatted TransformedResearch items."""
        from teams.dawo.scanners.youtube import (
            YouTubeTransformer,
            HarvestedVideo,
        )
        from teams.dawo.research import TransformedResearch, ResearchSource

        # Create mock insight extractor
        mock_insight_extractor = AsyncMock()
        mock_insight_extractor.extract_insights.return_value = MagicMock(
            main_summary="Research summary for pool.",
            quotable_insights=[],
            key_topics=["research", "lions_mane"],
            confidence_score=0.9,
        )

        transformer = YouTubeTransformer(insight_extractor=mock_insight_extractor)

        # Create harvested video
        harvested = [
            HarvestedVideo(
                video_id="pool_test_1",
                title="Research Pool Integration Test",
                channel_id="UCtest",
                channel_title="Test Channel",
                published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                description="Testing pool insertion",
                view_count=5000,
                like_count=100,
                comment_count=10,
                duration_seconds=300,
                transcript="Test transcript content",
                transcript_available=True,
                transcript_language="en",
                is_auto_generated=False,
            )
        ]

        # Transform
        result = await transformer.transform(harvested)

        # Verify output format
        assert len(result) == 1
        item = result[0]
        assert isinstance(item, TransformedResearch)
        assert item.source == ResearchSource.YOUTUBE
        assert item.title == "Research Pool Integration Test"
        assert "youtube.com/watch?v=pool_test_1" in item.url
        assert item.source_metadata["video_id"] == "pool_test_1"
        assert item.source_metadata["views"] == 5000

    @pytest.mark.asyncio
    async def test_batch_publish_integration(self):
        """Test batch publishing to Research Pool."""
        from teams.dawo.scanners.youtube.pipeline import YouTubeResearchPipeline

        # Create mock publisher
        mock_publisher = AsyncMock()
        mock_publisher.publish_batch.return_value = 3

        pipeline = YouTubeResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=MagicMock(),
            publisher=mock_publisher,
        )

        # Create mock items
        from teams.dawo.research import TransformedResearch, ResearchSource

        items = [
            MagicMock(spec=TransformedResearch, title=f"Test {i}")
            for i in range(3)
        ]

        # Call internal publish method
        count, ids = await pipeline._publish_items(items)

        assert count == 3
        mock_publisher.publish_batch.assert_called_once_with(items)


class TestScoringIntegration:
    """Integration tests for scoring integration (Task 15.3)."""

    @pytest.mark.asyncio
    async def test_scorer_receives_validated_items(self):
        """Test that scorer receives ValidatedResearch and returns scores."""
        from teams.dawo.scanners.youtube import ValidatedResearch
        from teams.dawo.scanners.youtube.pipeline import YouTubeResearchPipeline

        # Create mock scorer
        mock_scorer = MagicMock()
        mock_scorer.calculate_score.return_value = MagicMock(final_score=8.5)

        pipeline = YouTubeResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=mock_scorer,
            publisher=MagicMock(),
        )

        # Create validated items
        validated = [
            ValidatedResearch(
                source="youtube",
                title="Scoring Test Video",
                content="Test content for scoring",
                url="https://youtube.com/watch?v=score_test",
                tags=["lions_mane", "research"],
                source_metadata={"views": 10000, "video_id": "score_test"},
                created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                compliance_status="COMPLIANT",
                score=0.0,
            )
        ]

        # Call internal score method
        scored = await pipeline._score_items(validated)

        assert len(scored) == 1
        mock_scorer.calculate_score.assert_called_once()

    @pytest.mark.asyncio
    async def test_score_passed_to_publisher(self):
        """Test that scored items retain their scores through publishing."""
        from teams.dawo.scanners.youtube import ValidatedResearch
        from teams.dawo.scanners.youtube.pipeline import YouTubeResearchPipeline

        mock_scorer = MagicMock()
        mock_scorer.calculate_score.return_value = MagicMock(final_score=7.2)

        pipeline = YouTubeResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=mock_scorer,
            publisher=MagicMock(),
        )

        validated = [
            ValidatedResearch(
                source="youtube",
                title="Score Retention Test",
                content="Content",
                url="https://youtube.com/watch?v=retain",
                tags=["test"],
                source_metadata={"video_id": "retain"},
                created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                compliance_status="COMPLIANT",
                score=0.0,
            )
        ]

        scored = await pipeline._score_items(validated)

        # Verify score was applied
        assert scored[0].score == 7.2


class TestRetryMiddlewareIntegration:
    """Integration tests for retry middleware (Task 15.4)."""

    @pytest.mark.asyncio
    async def test_youtube_client_uses_retry_middleware(self):
        """Test that YouTubeClient calls through retry middleware."""
        from teams.dawo.scanners.youtube import (
            YouTubeClient,
            YouTubeClientConfig,
        )

        # Create mock retry middleware
        mock_retry = MagicMock()
        mock_retry.execute_with_retry = AsyncMock(
            return_value=MagicMock(
                success=True,
                response={"items": []},
                last_error=None,
            )
        )

        config = YouTubeClientConfig(api_key="test_api_key")
        client = YouTubeClient(config=config, retry_middleware=mock_retry)

        # Execute search
        from datetime import datetime, timezone

        await client.search_videos(
            query="test query",
            published_after=datetime.now(timezone.utc),
            max_results=10,
        )

        # Verify retry middleware was called
        mock_retry.execute_with_retry.assert_called_once()
        call_args = mock_retry.execute_with_retry.call_args
        assert "youtube_search" in call_args.kwargs.get("context", "")

    @pytest.mark.asyncio
    async def test_retry_middleware_handles_api_failure(self):
        """Test that retry middleware handles YouTube API failures."""
        from teams.dawo.scanners.youtube import (
            YouTubeClient,
            YouTubeClientConfig,
            YouTubeAPIError,
        )

        # Create mock retry that returns failure
        mock_retry = MagicMock()
        mock_retry.execute_with_retry = AsyncMock(
            return_value=MagicMock(
                success=False,
                response=None,
                last_error="API rate limit exceeded",
            )
        )

        config = YouTubeClientConfig(api_key="test_api_key")
        client = YouTubeClient(config=config, retry_middleware=mock_retry)

        # Execute search - should raise YouTubeAPIError
        from datetime import datetime, timezone

        with pytest.raises(YouTubeAPIError) as exc_info:
            await client.search_videos(
                query="test",
                published_after=datetime.now(timezone.utc),
            )

        assert "retries" in str(exc_info.value).lower()


class TestLLMInsightExtractionIntegration:
    """Integration tests for LLM insight extraction (Task 15.5)."""

    @pytest.mark.asyncio
    async def test_insight_extractor_parses_llm_json_response(self):
        """Test that KeyInsightExtractor correctly parses JSON from LLM."""
        from teams.dawo.scanners.youtube import KeyInsightExtractor, InsightResult

        # Create mock LLM client returning valid JSON
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = '''```json
{
    "main_summary": "This video explores lion's mane mushroom benefits for cognitive health.",
    "quotable_insights": [
        {
            "text": "Lion's mane may support nerve growth factor production",
            "context": "Research reference from university study",
            "topic": "lions_mane cognition",
            "is_claim": true
        }
    ],
    "key_topics": ["lions_mane", "cognition", "research"],
    "confidence_score": 0.85
}
```'''

        extractor = KeyInsightExtractor(llm_client=mock_llm)

        result = await extractor.extract_insights(
            transcript="Test transcript about lion's mane mushroom benefits...",
            title="Lion's Mane Benefits Video",
            channel_name="Health Science Channel",
        )

        assert isinstance(result, InsightResult)
        assert "lion's mane" in result.main_summary.lower()
        assert len(result.quotable_insights) == 1
        assert result.quotable_insights[0].is_claim is True
        assert "lions_mane" in result.key_topics
        assert result.confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_insight_extractor_handles_markdown_wrapped_json(self):
        """Test that extractor handles LLM responses with markdown code blocks."""
        from teams.dawo.scanners.youtube import KeyInsightExtractor

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = '''Here's the analysis:

```json
{
    "main_summary": "Summary with markdown wrapper",
    "quotable_insights": [],
    "key_topics": ["test"],
    "confidence_score": 0.7
}
```

Hope this helps!'''

        extractor = KeyInsightExtractor(llm_client=mock_llm)

        result = await extractor.extract_insights(
            transcript="Short transcript",
            title="Test",
            channel_name="Test Channel",
        )

        assert result.main_summary == "Summary with markdown wrapper"
        assert result.confidence_score == 0.7

    @pytest.mark.asyncio
    async def test_transformer_calls_insight_extractor_for_transcripts(self):
        """Test that transformer uses insight extractor for videos with transcripts."""
        from teams.dawo.scanners.youtube import (
            YouTubeTransformer,
            HarvestedVideo,
            InsightResult,
            QuotableInsight,
        )

        # Create mock insight extractor
        mock_extractor = AsyncMock()
        mock_extractor.extract_insights.return_value = InsightResult(
            main_summary="LLM generated summary",
            quotable_insights=[
                QuotableInsight(
                    text="Important quote",
                    context="Context here",
                    topic="test_topic",
                    is_claim=False,
                )
            ],
            key_topics=["test", "integration"],
            confidence_score=0.9,
        )

        transformer = YouTubeTransformer(insight_extractor=mock_extractor)

        harvested = [
            HarvestedVideo(
                video_id="llm_test",
                title="LLM Integration Test",
                channel_id="UCtest",
                channel_title="Test",
                published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                view_count=5000,
                transcript="Long transcript content here that needs LLM analysis...",
                transcript_available=True,
            )
        ]

        result = await transformer.transform(harvested)

        # Verify extractor was called
        mock_extractor.extract_insights.assert_called_once()
        call_args = mock_extractor.extract_insights.call_args

        assert call_args.kwargs["title"] == "LLM Integration Test"
        assert "transcript" in call_args.kwargs["transcript"].lower()

        # Verify content includes LLM output
        assert "LLM generated summary" in result[0].content
