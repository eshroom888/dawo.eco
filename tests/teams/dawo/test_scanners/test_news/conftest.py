"""Pytest fixtures for News Scanner tests.

Provides mock data and fixtures for testing all stages of the news research pipeline.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_rss_feed_response() -> dict[str, Any]:
    """Mock RSS feed parsed response."""
    now = datetime.now(timezone.utc)
    return {
        "entries": [
            {
                "title": "EU Approves New Health Claim for Lion's Mane Extract",
                "summary": "<p>The European Commission has approved a new health claim...</p>",
                "link": "https://example.com/eu-lions-mane-claim",
                "published_parsed": now.timetuple()[:6],
            },
            {
                "title": "Study Shows Reishi Benefits for Immune Function",
                "summary": "New clinical research demonstrates significant immune benefits...",
                "link": "https://example.com/reishi-study",
                "published_parsed": (now - timedelta(hours=12)).timetuple()[:6],
            },
            {
                "title": "Supplement Company Launches New Mushroom Line",
                "summary": "XYZ Supplements announces new line of functional mushroom products...",
                "link": "https://example.com/new-product-launch",
                "published_parsed": (now - timedelta(hours=6)).timetuple()[:6],
            },
            {
                "title": "Mattilsynet Issues Warning on Health Claims Compliance",
                "summary": "Norwegian Food Safety Authority warns supplement companies about EU health claims regulation compliance...",
                "link": "https://example.com/mattilsynet-warning",
                "published_parsed": (now - timedelta(hours=2)).timetuple()[:6],
            },
        ],
        "bozo": False,
        "bozo_exception": None,
    }


@pytest.fixture
def mock_regulatory_article() -> dict[str, Any]:
    """Regulatory news article for testing high-priority flagging."""
    return {
        "title": "Mattilsynet Issues Warning on Health Claims Compliance",
        "summary": "Norwegian Food Safety Authority warns supplement companies about EU health claims regulation compliance for novel food products.",
        "url": "https://example.com/mattilsynet-warning",
        "source_name": "NutraIngredients",
        "is_tier_1": True,
        "published": datetime.now(timezone.utc) - timedelta(hours=2),
    }


@pytest.fixture
def mock_research_article() -> dict[str, Any]:
    """Research news article for testing research category."""
    return {
        "title": "Clinical Study Shows Lion's Mane Cognitive Benefits",
        "summary": "A new peer-reviewed study demonstrates significant cognitive enhancement from lion's mane mushroom extract in adults over 50.",
        "url": "https://example.com/lions-mane-study",
        "source_name": "NutritionInsight",
        "is_tier_1": False,
        "published": datetime.now(timezone.utc) - timedelta(hours=8),
    }


@pytest.fixture
def mock_product_article() -> dict[str, Any]:
    """Product news article for testing product category."""
    return {
        "title": "New Adaptogen Brand Launches Premium Mushroom Supplements",
        "summary": "Wellness startup announces launch of new premium line of adaptogenic mushroom supplements targeting health-conscious consumers.",
        "url": "https://example.com/product-launch",
        "source_name": "Nutraceuticals World",
        "is_tier_1": True,
        "published": datetime.now(timezone.utc) - timedelta(hours=4),
    }


@pytest.fixture
def mock_general_article() -> dict[str, Any]:
    """General industry news article."""
    return {
        "title": "Global Mushroom Market Expected to Grow",
        "summary": "Industry analysts project continued growth in the global functional mushroom market through 2027.",
        "url": "https://example.com/market-growth",
        "source_name": "NutritionInsight",
        "is_tier_1": False,
        "published": datetime.now(timezone.utc) - timedelta(hours=10),
    }


@pytest.fixture
def scanner_config() -> dict[str, Any]:
    """Test scanner configuration dictionary."""
    return {
        "feeds": [
            {"name": "TestFeed", "url": "https://test.com/rss", "is_tier_1": True},
            {"name": "TestFeed2", "url": "https://test2.com/rss", "is_tier_1": False},
        ],
        "keywords": ["mushrooms", "supplements", "EU regulations", "health claims"],
        "competitor_brands": ["CompetitorBrand", "RivalCo"],
        "hours_back": 24,
    }


@pytest.fixture
def mock_retry_middleware() -> MagicMock:
    """Mock retry middleware for testing."""
    middleware = MagicMock()
    middleware.execute = AsyncMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
    return middleware


@pytest.fixture
def mock_eu_compliance_checker() -> MagicMock:
    """Mock EU compliance checker."""
    checker = MagicMock()
    checker.check_compliance = MagicMock(
        return_value=MagicMock(
            is_compliant=True,
            compliance_status="COMPLIANT",
            issues=[],
        )
    )
    return checker


@pytest.fixture
def mock_research_publisher() -> AsyncMock:
    """Mock research publisher."""
    publisher = AsyncMock()
    publisher.publish = AsyncMock(return_value=MagicMock(id="test-uuid-123"))
    publisher.publish_batch = AsyncMock(
        return_value=[MagicMock(id=f"test-uuid-{i}") for i in range(3)]
    )
    return publisher


@pytest.fixture
def mock_research_item_scorer() -> MagicMock:
    """Mock research item scorer."""
    scorer = MagicMock()
    scorer.calculate_score = MagicMock(
        return_value=MagicMock(
            final_score=5.0,
            components={},
            adjustments=[],
        )
    )
    return scorer
