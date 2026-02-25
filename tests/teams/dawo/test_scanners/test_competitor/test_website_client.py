"""Tests for WebsiteScraperClient.

Epic 6, Story 6-5, Task 4: Website scraping with robots.txt compliance.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from teams.dawo.scanners.competitor.config import CompetitorConfig, WebsiteScanConfig
from teams.dawo.scanners.competitor.website_client import WebsiteScraperClient


@pytest.fixture
def website_config():
    return WebsiteScanConfig(enabled=True, request_delay_seconds=0, max_pages_per_domain=20)


@pytest.fixture
def client(mock_http_client, mock_retry_middleware, website_config):
    return WebsiteScraperClient(
        http_client=mock_http_client,
        retry=mock_retry_middleware,
        config=website_config,
    )


class TestScrapePageExtraction:
    """Tests for scrape_page() content extraction."""

    @pytest.mark.asyncio
    async def test_extracts_title_text_meta(self, client, mock_http_client, sample_html_page):
        response = MagicMock()
        response.status_code = 200
        response.text = sample_html_page
        response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=response)

        page = await client.scrape_page("https://competitor-a.com/products")

        assert page.title == "Product - Brain Boost"
        assert "supplement" in page.content_text.lower()
        assert page.meta_description == "Our mushroom supplement enhances cognitive function"

    @pytest.mark.asyncio
    async def test_strips_script_style_tags(self, client, mock_http_client):
        html = """
        <html><head><title>Test</title>
        <style>.hidden { display: none; }</style>
        <script>alert('xss');</script>
        </head><body><main>
        <p>Clean content here.</p>
        <script>var x = 1;</script>
        </main></body></html>
        """
        response = MagicMock()
        response.status_code = 200
        response.text = html
        response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=response)

        page = await client.scrape_page("https://example.com")

        assert "alert" not in page.content_text
        assert "hidden" not in page.content_text
        assert "Clean content here." in page.content_text


class TestRobotsTxt:
    """Tests for robots.txt handling."""

    @pytest.mark.asyncio
    async def test_check_robots_txt_parses(self, client, mock_http_client, sample_robots_txt):
        response = MagicMock()
        response.status_code = 200
        response.text = sample_robots_txt
        response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=response)

        result = await client.check_robots_txt("https://competitor-a.com")

        assert result.robots_url == "https://competitor-a.com/robots.txt"

    @pytest.mark.asyncio
    async def test_is_allowed_returns_false_for_disallowed(self, client, mock_http_client):
        robots_txt = "User-agent: *\nDisallow: /admin/\nDisallow: /private/"
        response = MagicMock()
        response.status_code = 200
        response.text = robots_txt
        response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=response)

        allowed = await client.is_allowed("https://competitor-a.com/admin/dashboard")
        assert allowed is False

    @pytest.mark.asyncio
    async def test_is_allowed_returns_true_for_allowed(self, client, mock_http_client):
        robots_txt = "User-agent: *\nDisallow: /admin/"
        response = MagicMock()
        response.status_code = 200
        response.text = robots_txt
        response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=response)

        allowed = await client.is_allowed("https://competitor-a.com/products")
        assert allowed is True


class TestScrapeCompetitorPages:
    """Tests for scrape_competitor_pages() orchestration."""

    @pytest.mark.asyncio
    async def test_skips_disallowed_urls(self, client, mock_http_client):
        robots_txt = "User-agent: *\nDisallow: /"
        robots_response = MagicMock()
        robots_response.status_code = 200
        robots_response.text = robots_txt
        robots_response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=robots_response)

        competitor = CompetitorConfig(
            name="Blocked",
            website_urls=("https://blocked.com/products",),
        )
        pages = await client.scrape_competitor_pages(competitor)
        assert len(pages) == 0


class TestErrorHandling:
    """Tests for graceful error handling."""

    @pytest.mark.asyncio
    async def test_connection_timeout_returns_none(self, client, mock_http_client):
        import httpx
        mock_http_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("Timeout"))

        page = await client.scrape_page("https://slow.com")
        assert page is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self, client, mock_http_client):
        import httpx
        response = MagicMock()
        response.status_code = 404
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=response)
        )
        mock_http_client.get = AsyncMock(return_value=response)

        page = await client.scrape_page("https://missing.com/page")
        assert page is None
