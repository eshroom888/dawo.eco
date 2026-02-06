"""Shared test fixtures for YouTube Research Scanner tests.

Provides common fixtures for mocking YouTube API, transcripts, and
pipeline components across all test modules.

Usage:
    # Fixtures are automatically available in test files
    def test_something(mock_youtube_client, scanner_config):
        scanner = YouTubeScanner(config=scanner_config, client=mock_youtube_client)
        ...
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def youtube_api_key():
    """Test YouTube API key."""
    return "test_youtube_api_key_12345"


@pytest.fixture
def scanner_config():
    """Standard YouTubeScannerConfig for testing."""
    from teams.dawo.scanners.youtube import YouTubeScannerConfig

    return YouTubeScannerConfig(
        search_queries=["lion's mane benefits", "mushroom supplements"],
        min_views=1000,
        days_back=7,
        max_videos_per_query=10,
    )


@pytest.fixture
def client_config(youtube_api_key):
    """YouTubeClientConfig with test API key."""
    from teams.dawo.scanners.youtube import YouTubeClientConfig

    return YouTubeClientConfig(api_key=youtube_api_key)


@pytest.fixture
def transcript_config():
    """Standard TranscriptConfig for testing."""
    from teams.dawo.scanners.youtube import TranscriptConfig

    return TranscriptConfig(
        preferred_languages=["en", "en-US"],
        max_transcript_length=50000,
    )


# =============================================================================
# Mock API Response Fixtures
# =============================================================================


@pytest.fixture
def mock_youtube_search_response():
    """Mock YouTube Data API search response."""
    return {
        "items": [
            {
                "kind": "youtube#searchResult",
                "id": {"videoId": "abc123xyz"},
                "snippet": {
                    "publishedAt": "2026-02-01T10:00:00Z",
                    "channelId": "UCxxxxxxx",
                    "title": "Lion's Mane Benefits: What Science Actually Says",
                    "description": "In this video we explore the scientific evidence...",
                    "channelTitle": "Health Science Channel",
                    "thumbnails": {
                        "default": {"url": "https://i.ytimg.com/vi/abc123xyz/default.jpg"}
                    },
                },
            },
            {
                "kind": "youtube#searchResult",
                "id": {"videoId": "def456uvw"},
                "snippet": {
                    "publishedAt": "2026-02-02T14:30:00Z",
                    "channelId": "UCyyyyyyy",
                    "title": "Cordyceps Review: Energy and Performance",
                    "description": "A comprehensive look at cordyceps mushroom...",
                    "channelTitle": "Supplement Reviews",
                    "thumbnails": {
                        "default": {"url": "https://i.ytimg.com/vi/def456uvw/default.jpg"}
                    },
                },
            },
        ]
    }


@pytest.fixture
def mock_video_statistics_response():
    """Mock YouTube Data API videos.list response with statistics."""
    return {
        "items": [
            {
                "id": "abc123xyz",
                "statistics": {
                    "viewCount": "15234",
                    "likeCount": "1200",
                    "commentCount": "89",
                },
                "contentDetails": {"duration": "PT15M30S"},
            },
            {
                "id": "def456uvw",
                "statistics": {
                    "viewCount": "8500",
                    "likeCount": "650",
                    "commentCount": "42",
                },
                "contentDetails": {"duration": "PT8M45S"},
            },
        ]
    }


@pytest.fixture
def mock_transcript():
    """Mock transcript text for testing."""
    return """
    Today we're talking about lion's mane mushroom and what the research actually shows.
    Studies indicate that lion's mane may support nerve growth factor production.
    The typical dosage ranges from 500mg to 3000mg daily, depending on the form.
    Let's look at the key studies and what they found about cognitive benefits.
    Some researchers have noted improvements in memory and focus.
    However, more clinical trials are needed to confirm these effects.
    """


# =============================================================================
# Mock Client Fixtures
# =============================================================================


@pytest.fixture
def mock_retry_middleware():
    """Mock retry middleware that succeeds immediately."""
    mock = MagicMock()
    mock.execute_with_retry = AsyncMock(
        return_value=MagicMock(
            success=True,
            response={"items": []},
            last_error=None,
        )
    )
    return mock


@pytest.fixture
def mock_youtube_client(mock_youtube_search_response, mock_video_statistics_response):
    """Mock YouTubeClient for testing without API calls."""
    from teams.dawo.scanners.youtube import YouTubeClient

    client = AsyncMock(spec=YouTubeClient)
    client.search_videos.return_value = mock_youtube_search_response["items"]
    client.get_video_statistics.return_value = {
        item["id"]: item for item in mock_video_statistics_response["items"]
    }
    client.quota_remaining = 9000
    return client


@pytest.fixture
def mock_transcript_client(mock_transcript):
    """Mock TranscriptClient for testing."""
    from teams.dawo.scanners.youtube import TranscriptClient, TranscriptResult

    client = AsyncMock(spec=TranscriptClient)
    client.get_transcript.return_value = TranscriptResult(
        text=mock_transcript,
        language="en",
        is_auto_generated=False,
        available=True,
        duration_seconds=930,
    )
    return client


# =============================================================================
# Mock Pipeline Component Fixtures
# =============================================================================


@pytest.fixture
def mock_insight_extractor():
    """Mock KeyInsightExtractor for testing."""
    from teams.dawo.scanners.youtube import InsightResult, QuotableInsight

    extractor = AsyncMock()
    extractor.extract_insights.return_value = InsightResult(
        main_summary="This video explores the scientific evidence behind lion's mane mushroom benefits for cognitive health.",
        quotable_insights=[
            QuotableInsight(
                text="Studies show lion's mane may support nerve growth factor production",
                context="Research reference from university study",
                topic="lions_mane cognition",
                is_claim=True,
            ),
            QuotableInsight(
                text="Typical dosage ranges from 500mg to 3000mg daily",
                context="Dosage information",
                topic="dosage",
                is_claim=False,
            ),
        ],
        key_topics=["lions_mane", "cognition", "research", "dosage"],
        confidence_score=0.85,
    )
    return extractor


@pytest.fixture
def mock_compliance_checker():
    """Mock EUComplianceChecker for testing."""
    from teams.dawo.validators.eu_compliance import OverallStatus

    checker = AsyncMock()
    checker.check_content.return_value = MagicMock(
        overall_status=OverallStatus.COMPLIANT,
        issues=[],
        suggestions=[],
    )
    return checker


@pytest.fixture
def mock_scorer():
    """Mock ResearchItemScorer for testing."""
    scorer = MagicMock()
    scorer.calculate_score.return_value = MagicMock(
        final_score=7.5,
        breakdown={"relevance": 8.0, "quality": 7.0},
    )
    return scorer


@pytest.fixture
def mock_publisher():
    """Mock ResearchPublisher for testing."""
    from uuid import uuid4

    publisher = AsyncMock()
    publisher.publish.return_value = MagicMock(id=uuid4())
    publisher.publish_batch.return_value = 2
    return publisher


# =============================================================================
# Schema Fixtures
# =============================================================================


@pytest.fixture
def raw_youtube_video():
    """Sample RawYouTubeVideo for testing."""
    from teams.dawo.scanners.youtube import RawYouTubeVideo

    return RawYouTubeVideo(
        video_id="abc123xyz",
        title="Lion's Mane Benefits: What Science Actually Says",
        channel_id="UCxxxxxxx",
        channel_title="Health Science Channel",
        published_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
        description="In this video we explore the scientific evidence...",
        thumbnail_url="https://i.ytimg.com/vi/abc123xyz/default.jpg",
    )


@pytest.fixture
def harvested_video(mock_transcript):
    """Sample HarvestedVideo for testing."""
    from teams.dawo.scanners.youtube import HarvestedVideo

    return HarvestedVideo(
        video_id="abc123xyz",
        title="Lion's Mane Benefits: What Science Actually Says",
        channel_id="UCxxxxxxx",
        channel_title="Health Science Channel",
        published_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
        description="In this video we explore the scientific evidence...",
        view_count=15234,
        like_count=1200,
        comment_count=89,
        duration_seconds=930,
        thumbnail_url="https://i.ytimg.com/vi/abc123xyz/default.jpg",
        transcript=mock_transcript,
        transcript_available=True,
        transcript_language="en",
        is_auto_generated=False,
    )


@pytest.fixture
def validated_research():
    """Sample ValidatedResearch for testing."""
    from teams.dawo.scanners.youtube import ValidatedResearch

    return ValidatedResearch(
        source="youtube",
        title="Lion's Mane Benefits: What Science Actually Says",
        content="Summary: This video explores lion's mane benefits...\n\nKey Insights:\n1. \"Studies show...\"",
        url="https://youtube.com/watch?v=abc123xyz",
        tags=["lions_mane", "cognition", "research"],
        source_metadata={
            "channel": "Health Science Channel",
            "channel_id": "UCxxxxxxx",
            "video_id": "abc123xyz",
            "views": 15234,
            "likes": 1200,
            "comments": 89,
            "duration_seconds": 930,
            "has_transcript": True,
            "transcript_language": "en",
            "is_auto_generated": False,
            "insight_count": 2,
            "confidence_score": 0.85,
        },
        created_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
        compliance_status="COMPLIANT",
        score=7.5,
    )
