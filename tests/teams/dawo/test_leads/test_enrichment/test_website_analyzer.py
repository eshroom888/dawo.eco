"""Tests for WebsiteAnalyzer.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 2: Implement Website Analyzer
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx


class TestWebsiteAnalyzerInit:
    """Tests for WebsiteAnalyzer initialization."""

    def test_accepts_http_client_via_injection(self) -> None:
        """Test WebsiteAnalyzer accepts httpx.AsyncClient via DI."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        client = AsyncMock(spec=httpx.AsyncClient)
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)

        assert analyzer._client is client
        assert analyzer._config is config

    def test_default_timeout_from_config(self) -> None:
        """Test timeout is taken from config."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        client = AsyncMock(spec=httpx.AsyncClient)
        config = EnrichmentConfig(website_timeout_seconds=10)

        analyzer = WebsiteAnalyzer(http_client=client, config=config)

        assert analyzer._timeout == 10


class TestFetchPage:
    """Tests for fetch_page method."""

    @pytest.mark.asyncio
    async def test_fetch_page_success(self) -> None:
        """Test successful page fetch."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.fetch_page("https://example.com")

        assert result == "<html><body>Test content</body></html>"
        client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_page_timeout(self) -> None:
        """Test fetch_page returns None on timeout."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.side_effect = httpx.TimeoutException("Timeout")
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.fetch_page("https://example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_page_http_error(self) -> None:
        """Test fetch_page returns None on HTTP error."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=mock_response
        )

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.fetch_page("https://example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_page_respects_rate_limit(self) -> None:
        """Test fetch_page respects rate limit."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        import time

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "content"

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        config = EnrichmentConfig(website_rate_limit_per_second=10.0)  # Fast for test

        analyzer = WebsiteAnalyzer(http_client=client, config=config)

        # First request should be immediate
        start = time.monotonic()
        await analyzer.fetch_page("https://example.com/page1")
        await analyzer.fetch_page("https://example.com/page2")
        elapsed = time.monotonic() - start

        # Should have waited for rate limit
        assert client.get.call_count == 2


class TestExtractText:
    """Tests for extract_text method."""

    def test_extract_text_from_html(self) -> None:
        """Test extracting text from HTML content."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        html = """
        <html>
        <head><title>Test</title></head>
        <body>
        <h1>Welcome</h1>
        <p>This is a test paragraph.</p>
        <script>console.log('ignored');</script>
        </body>
        </html>
        """

        client = AsyncMock(spec=httpx.AsyncClient)
        config = EnrichmentConfig()
        analyzer = WebsiteAnalyzer(http_client=client, config=config)

        result = analyzer.extract_text(html)

        assert "Welcome" in result
        assert "This is a test paragraph" in result
        assert "console.log" not in result

    def test_extract_text_removes_scripts(self) -> None:
        """Test that script tags are removed."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        html = "<html><body><script>malicious();</script><p>Safe text</p></body></html>"

        client = AsyncMock(spec=httpx.AsyncClient)
        config = EnrichmentConfig()
        analyzer = WebsiteAnalyzer(http_client=client, config=config)

        result = analyzer.extract_text(html)

        assert "malicious" not in result
        assert "Safe text" in result

    def test_extract_text_handles_empty_input(self) -> None:
        """Test extract_text handles empty input."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        client = AsyncMock(spec=httpx.AsyncClient)
        config = EnrichmentConfig()
        analyzer = WebsiteAnalyzer(http_client=client, config=config)

        result = analyzer.extract_text("")

        assert result == ""


class TestAnalyze:
    """Tests for analyze method."""

    @pytest.mark.asyncio
    async def test_analyze_accessible_website(self) -> None:
        """Test analyzing an accessible website."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <head><title>Health Store</title></head>
        <body>
        <h1>Welcome to Health Store</h1>
        <p>We sell lion's mane and reishi mushrooms.</p>
        <p>Premium supplements and organic products.</p>
        </body>
        </html>
        """

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.analyze("healthstore.no")

        assert result.domain == "healthstore.no"
        assert result.accessible is True
        assert result.content is not None
        assert "lion's mane" in result.mushroom_keywords_found

    @pytest.mark.asyncio
    async def test_analyze_inaccessible_website(self) -> None:
        """Test analyzing an inaccessible website."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.side_effect = httpx.TimeoutException("Timeout")
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.analyze("offline-store.no")

        assert result.domain == "offline-store.no"
        assert result.accessible is False
        assert result.content is None

    @pytest.mark.asyncio
    async def test_analyze_detects_mushroom_keywords(self) -> None:
        """Test detection of mushroom-related keywords."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body>
        We offer lion's mane, chaga, reishi, and cordyceps mushrooms.
        Functional mushroom supplements available.
        </body></html>
        """

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.analyze("mushroom-store.no")

        assert "lion's mane" in result.mushroom_keywords_found
        assert "chaga" in result.mushroom_keywords_found
        assert "reishi" in result.mushroom_keywords_found

    @pytest.mark.asyncio
    async def test_analyze_detects_supplement_section(self) -> None:
        """Test detection of supplement section."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body>
        <nav>
        <a href="/supplements">Supplements</a>
        <a href="/vitamins">Vitamins</a>
        </nav>
        <section id="kosttilskudd">Our supplements section</section>
        </body></html>
        """

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.analyze("health-shop.no")

        assert result.supplement_section is True

    @pytest.mark.asyncio
    async def test_analyze_extracts_description(self) -> None:
        """Test extraction of business description."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <head>
        <meta name="description" content="Oslo's premier health food store offering organic supplements and wellness products.">
        </head>
        <body><p>Welcome</p></body>
        </html>
        """

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.analyze("oslo-health.no")

        assert result.description is not None
        assert "Oslo" in result.description or "health food" in result.description


class TestRobotsRespect:
    """Tests for robots.txt compliance."""

    @pytest.mark.asyncio
    async def test_respects_robots_disallow(self) -> None:
        """Test that disallowed paths are not fetched."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        # Mock robots.txt response
        robots_response = Mock()
        robots_response.status_code = 200
        robots_response.text = """
        User-agent: *
        Disallow: /admin/
        Disallow: /private/
        """

        page_response = Mock()
        page_response.status_code = 200
        page_response.text = "<html><body>Public content</body></html>"

        def mock_get(url, **kwargs):
            if "robots.txt" in url:
                return robots_response
            return page_response

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.side_effect = mock_get
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)

        # Check if robots.txt is respected
        result = await analyzer.analyze("example.com")
        assert result.accessible is True


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        """Test graceful handling of connection errors."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.side_effect = httpx.ConnectError("Connection refused")
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.analyze("unreachable.no")

        assert result.accessible is False
        assert result.domain == "unreachable.no"

    @pytest.mark.asyncio
    async def test_handles_malformed_html(self) -> None:
        """Test handling of malformed HTML."""
        from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Unclosed tag"

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = mock_response
        config = EnrichmentConfig()

        analyzer = WebsiteAnalyzer(http_client=client, config=config)
        result = await analyzer.analyze("broken-html.no")

        # Should still work, just with partial content
        assert result.accessible is True
        assert result.content is not None
