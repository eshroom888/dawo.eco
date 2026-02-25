"""Shared fixtures for competitor scanner tests.

Epic 6, Story 6-5, Task 12.2: Common test fixtures.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from teams.dawo.scanners.competitor.config import (
    CompetitorConfig,
    CompetitorScannerConfig,
    InstagramScanConfig,
    WebsiteScanConfig,
)
from teams.dawo.scanners.competitor.schemas import ParsedContent


@pytest.fixture
def competitor_a():
    """Primary competitor with Instagram and website."""
    return CompetitorConfig(
        name="CompetitorA",
        instagram_username="competitor_a",
        website_urls=("https://competitor-a.com/products/lions-mane",),
        is_primary=True,
    )


@pytest.fixture
def competitor_b():
    """Secondary competitor with website only."""
    return CompetitorConfig(
        name="CompetitorB",
        instagram_username=None,
        website_urls=("https://competitor-b.com/shop",),
        is_primary=False,
    )


@pytest.fixture
def health_keywords():
    """Health language keywords for testing."""
    return (
        "boost", "improve", "enhance", "treat", "cure",
        "prevent", "immunity", "cognitive", "styrker", "forbedrer",
    )


@pytest.fixture
def competitor_config(competitor_a, health_keywords):
    """Full scanner config with one competitor."""
    return CompetitorScannerConfig(
        competitors=(competitor_a,),
        health_language_keywords=health_keywords,
    )


@pytest.fixture
def multi_competitor_config(competitor_a, competitor_b, health_keywords):
    """Scanner config with multiple competitors."""
    return CompetitorScannerConfig(
        competitors=(competitor_a, competitor_b),
        health_language_keywords=health_keywords,
    )


@pytest.fixture
def sample_instagram_response():
    """Sample Instagram API response for get_user_media()."""
    return [
        {
            "id": "17895695668004550",
            "caption": "Our lion's mane extract boosts cognitive function! #nootropics #wellness",
            "permalink": "https://www.instagram.com/p/ABC123/",
            "timestamp": "2026-02-10T12:00:00+0000",
            "like_count": 150,
            "comments_count": 12,
            "media_type": "IMAGE",
        },
        {
            "id": "17895695668004551",
            "caption": "Beautiful mushroom harvest today #mushrooms #nature",
            "permalink": "https://www.instagram.com/p/DEF456/",
            "timestamp": "2026-02-11T09:30:00+0000",
            "like_count": 85,
            "comments_count": 5,
            "media_type": "IMAGE",
        },
    ]


@pytest.fixture
def sample_html_page():
    """Sample competitor website HTML."""
    return """
    <html><head><title>Product - Brain Boost</title>
    <meta name="description" content="Our mushroom supplement enhances cognitive function">
    </head><body><main>
    <h1>Brain Boost Lion's Mane</h1>
    <p>This supplement treats brain fog and improves memory naturally.</p>
    <a href="https://competitor-a.com/about">About Us</a>
    </main></body></html>
    """


@pytest.fixture
def sample_html_no_health():
    """HTML page without health language."""
    return """
    <html><head><title>About Us</title>
    <meta name="description" content="We are a mushroom company">
    </head><body><main>
    <h1>About Our Company</h1>
    <p>We grow organic mushrooms in Norway.</p>
    </main></body></html>
    """


@pytest.fixture
def sample_robots_txt():
    """Standard robots.txt content."""
    return """
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /products/
Allow: /blog/

User-agent: DAWO-ECO-CompetitorMonitor/1.0
Allow: /
"""


@pytest.fixture
def sample_parsed_content():
    """Sample ParsedContent for pipeline tests."""
    return ParsedContent(
        source_type="instagram",
        competitor_name="CompetitorA",
        source_url="https://www.instagram.com/p/ABC123/",
        content_text="Our lion's mane extract boosts cognitive function!",
        hashtags=["#nootropics", "#wellness"],
        account_or_domain="competitor_a",
        published_at=datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC),
        content_hash="a1b2c3d4e5f6",
        has_health_language=True,
        health_keywords_matched=["boost", "cognitive"],
    )


@pytest.fixture
def mock_retry_middleware():
    """Mock retry middleware matching RetryMiddlewareProtocol."""
    middleware = MagicMock()

    async def execute_with_retry(func, context=None):
        result = MagicMock()
        try:
            response = await func()
            result.success = True
            result.response = response
            result.last_error = None
        except Exception as e:
            result.success = False
            result.response = None
            result.last_error = str(e)
        return result

    middleware.execute_with_retry = execute_with_retry
    return middleware


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient for website scraping."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_instagram_client():
    """Mock InstagramClient."""
    client = AsyncMock()
    client.get_user_media = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_session():
    """Mock AsyncSession for DB operations."""
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session
