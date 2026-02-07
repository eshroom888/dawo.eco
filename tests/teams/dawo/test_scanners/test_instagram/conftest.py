"""Shared test fixtures for Instagram Scanner tests.

Provides mock objects and sample data for testing without real API calls.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.instagram import (
    InstagramClient,
    InstagramClientConfig,
    InstagramScannerConfig,
    RawInstagramPost,
    HarvestedPost,
    ThemeResult,
    DetectedClaim,
    ClaimDetectionResult,
    ClaimCategory,
)


@pytest.fixture
def mock_hashtag_search_response():
    """Mock Instagram Graph API hashtag search response."""
    return {
        "data": [
            {
                "id": "17841563789012345",
                "caption": "Starting my morning with lion's mane coffee! #lionsmane #morningroutine #biohacking",
                "permalink": "https://www.instagram.com/p/ABC123/",
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                "like_count": 1500,
                "comments_count": 45,
                "media_type": "IMAGE",
            },
            {
                "id": "17841563789012346",
                "caption": "Adaptogens are amazing for stress! #adaptogens #wellness",
                "permalink": "https://www.instagram.com/p/ABC124/",
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
                "like_count": 800,
                "comments_count": 22,
                "media_type": "IMAGE",
            },
        ]
    }


@pytest.fixture
def mock_competitor_media_response():
    """Mock Instagram Business Discovery response."""
    return {
        "business_discovery": {
            "media": {
                "data": [
                    {
                        "id": "17841563789012347",
                        "caption": "Our lion's mane extract boosts your brain power! Shop now! #sponsored",
                        "permalink": "https://www.instagram.com/p/DEF456/",
                        "timestamp": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
                        "like_count": 3200,
                        "comments_count": 89,
                        "media_type": "IMAGE",
                    }
                ]
            }
        }
    }


@pytest.fixture
def client_config():
    """Test Instagram client configuration."""
    return InstagramClientConfig(
        access_token="test_access_token_12345",
        business_account_id="test_business_id_67890",
    )


@pytest.fixture
def scanner_config():
    """Test scanner configuration."""
    return InstagramScannerConfig(
        hashtags=["lionsmane", "adaptogens"],
        competitor_accounts=["competitor_brand"],
        hours_back=24,
        max_posts_per_hashtag=10,
        max_posts_per_account=5,
    )


@pytest.fixture
def mock_retry_middleware():
    """Mock retry middleware that returns success."""
    middleware = MagicMock()

    async def execute_with_retry(func, context=None):
        result = MagicMock()
        result.success = True
        result.response = await func()
        result.last_error = None
        return result

    middleware.execute_with_retry = execute_with_retry
    return middleware


@pytest.fixture
def mock_instagram_client(mock_hashtag_search_response, mock_competitor_media_response, mock_retry_middleware, client_config):
    """Mock InstagramClient for testing without API calls."""
    client = AsyncMock(spec=InstagramClient)
    client.search_hashtag.return_value = mock_hashtag_search_response["data"]
    client.get_user_media.return_value = mock_competitor_media_response["business_discovery"]["media"]["data"]
    client.rate_limit_remaining = 195
    return client


@pytest.fixture
def sample_raw_post():
    """Sample RawInstagramPost for testing."""
    return RawInstagramPost(
        media_id="17841563789012345",
        permalink="https://www.instagram.com/p/ABC123/",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        caption="Lion's mane for focus! #lionsmane #focus",
        media_type="IMAGE",
        hashtag_source="lionsmane",
        is_competitor=False,
    )


@pytest.fixture
def sample_harvested_post():
    """Sample HarvestedPost for testing."""
    return HarvestedPost(
        media_id="17841563789012345",
        permalink="https://www.instagram.com/p/ABC123/",
        caption="Lion's mane for focus! #lionsmane #focus",
        hashtags=["lionsmane", "focus"],
        likes=1500,
        comments=45,
        media_type="IMAGE",
        account_name="wellness_user",
        account_type="business",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        is_competitor=False,
        hashtag_source="lionsmane",
    )


@pytest.fixture
def sample_theme_result():
    """Sample ThemeResult for testing."""
    return ThemeResult(
        content_type="educational",
        messaging_patterns=["personal_story", "product_showcase"],
        detected_products=["lion's mane extract"],
        influencer_indicators=False,
        key_topics=["lions_mane", "focus", "cognition"],
        confidence_score=0.85,
    )


@pytest.fixture
def sample_claim_detection_result():
    """Sample ClaimDetectionResult for testing."""
    return ClaimDetectionResult(
        claims_detected=[
            DetectedClaim(
                claim_text="boosts your brain power",
                category=ClaimCategory.ENHANCEMENT,
                confidence=0.9,
                severity="medium",
            )
        ],
        requires_cleanmarket_review=True,
        overall_risk_level="medium",
        summary="Enhancement claim detected: 'boosts brain power'",
    )


@pytest.fixture
def sample_claim_detection_result_clean():
    """Sample ClaimDetectionResult with no claims for testing."""
    return ClaimDetectionResult(
        claims_detected=[],
        requires_cleanmarket_review=False,
        overall_risk_level="none",
        summary="",
    )


# Integration test fixtures


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for theme extraction and claim detection."""
    client = AsyncMock()

    # Default response for theme extraction
    theme_response = """
    {
        "content_type": "educational",
        "messaging_patterns": ["personal_story"],
        "detected_products": [],
        "influencer_indicators": false,
        "key_topics": ["lions_mane", "wellness"],
        "confidence_score": 0.8
    }
    """

    # Default response for claim detection
    claim_response = """
    {
        "claims_detected": [],
        "requires_cleanmarket_review": false,
        "overall_risk_level": "none",
        "summary": ""
    }
    """

    # Return theme response first, then claim response
    client.complete = AsyncMock(side_effect=[theme_response, claim_response] * 10)

    return client


@pytest.fixture
def mock_eu_compliance_checker():
    """Mock EU Compliance Checker for validation stage."""
    checker = AsyncMock()

    # Default to compliant
    result = MagicMock()
    result.status = "COMPLIANT"
    result.violations = []
    result.warnings = []

    checker.check = AsyncMock(return_value=result)
    return checker


@pytest.fixture
def mock_research_scorer():
    """Mock Research Item Scorer for scoring stage."""
    scorer = MagicMock()

    # Return moderate score
    result = MagicMock()
    result.final_score = 6.0
    result.component_scores = {"relevance": 7.0, "recency": 6.0, "engagement": 5.0}

    scorer.calculate_score = MagicMock(return_value=result)
    return scorer


@pytest.fixture
def mock_research_publisher():
    """Mock Research Publisher for publish stage."""
    from uuid import uuid4

    publisher = AsyncMock()

    # Batch publish returns count
    publisher.publish_batch = AsyncMock(return_value=5)

    # Individual publish returns item with ID
    async def publish_item(item):
        result = MagicMock()
        result.id = uuid4()
        return result

    publisher.publish = AsyncMock(side_effect=publish_item)

    return publisher
