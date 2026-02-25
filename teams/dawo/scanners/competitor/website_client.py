"""Website Scraper Client for competitor content scanning.

Epic 6, Story 6-5, Task 4: Fetch and parse competitor website pages
with robots.txt compliance.

Uses httpx + BeautifulSoup following the Mattilsynet client pattern.
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import Optional, Protocol, runtime_checkable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from teams.dawo.scanners.competitor.config import CompetitorConfig, WebsiteScanConfig
from teams.dawo.scanners.competitor.schemas import RobotsTxtResult, ScrapedPage

logger = logging.getLogger(__name__)


@runtime_checkable
class RetryResultProtocol(Protocol):
    """Protocol for retry middleware results."""

    @property
    def success(self) -> bool: ...

    @property
    def response(self) -> object: ...

    @property
    def last_error(self) -> Optional[str]: ...


@runtime_checkable
class RetryMiddlewareProtocol(Protocol):
    """Protocol for retry middleware.

    Mirrors project-level RetryMiddleware protocol for decoupled imports.
    """

    async def execute_with_retry(
        self,
        func: object,
        context: Optional[str] = None,
    ) -> RetryResultProtocol: ...


class WebsiteScraperClient:
    """Client for scraping competitor website pages.

    Respects robots.txt, handles errors gracefully, and extracts
    structured content from HTML pages.

    Args:
        http_client: httpx.AsyncClient for HTTP requests
        retry: RetryMiddlewareProtocol for retry logic
        config: WebsiteScanConfig with scraping parameters
        user_agent: User-agent string for robots.txt compliance
    """

    def __init__(
        self,
        http_client: object,
        retry: RetryMiddlewareProtocol,
        config: WebsiteScanConfig,
        user_agent: str = "DAWO-ECO-CompetitorMonitor/1.0",
    ) -> None:
        self._client = http_client
        self._retry = retry
        self._config = config
        self._user_agent = user_agent
        self._robots_cache: dict[str, RobotFileParser] = {}

    async def check_robots_txt(self, base_url: str) -> RobotsTxtResult:
        """Fetch and parse robots.txt for a domain.

        Results are cached per domain to avoid redundant fetches.

        Args:
            base_url: Base URL of the website

        Returns:
            RobotsTxtResult with allowed status
        """
        parsed = urlparse(base_url)
        domain = parsed.netloc
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"

        if domain not in self._robots_cache:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                retry_result = await self._retry.execute_with_retry(
                    lambda: self._client.get(
                        robots_url, timeout=30, follow_redirects=True,
                    ),
                    context=f"robots.txt:{domain}",
                )
                if retry_result.success:
                    retry_result.response.raise_for_status()
                    rp.parse(retry_result.response.text.splitlines())
                else:
                    logger.debug(
                        "Failed to fetch robots.txt from %s: %s",
                        robots_url, retry_result.last_error,
                    )
                    rp.parse([])
            except Exception as e:
                logger.debug("Failed to fetch robots.txt from %s: %s", robots_url, e)
                # If robots.txt is unavailable, allow all by default
                rp.parse([])

            self._robots_cache[domain] = rp

        rp = self._robots_cache[domain]
        allowed = rp.can_fetch(self._user_agent, base_url)

        return RobotsTxtResult(
            allowed=allowed,
            checked_at=datetime.now(UTC),
            robots_url=robots_url,
        )

    async def is_allowed(self, url: str) -> bool:
        """Check if a URL is allowed by robots.txt.

        Args:
            url: URL to check

        Returns:
            True if crawling is allowed
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        base_url = f"{parsed.scheme}://{domain}"

        if domain not in self._robots_cache:
            await self.check_robots_txt(base_url)

        rp = self._robots_cache[domain]
        return rp.can_fetch(self._user_agent, url)

    async def scrape_page(self, url: str) -> Optional[ScrapedPage]:
        """Fetch and parse a single web page.

        Extracts title, main content, meta description, and links.
        Returns None on any error (logged, never crashes).

        Args:
            url: URL of the page to scrape

        Returns:
            ScrapedPage with extracted content, or None on error
        """
        try:
            retry_result = await self._retry.execute_with_retry(
                lambda: self._client.get(
                    url, timeout=30, follow_redirects=True,
                ),
                context=f"scrape:{url}",
            )
            if not retry_result.success:
                logger.warning("Failed to fetch %s: %s", url, retry_result.last_error)
                return None
            response = retry_result.response
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            return None

        try:
            return self._parse_html(url, html)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", url, e)
            return None

    def _parse_html(self, url: str, html: str) -> ScrapedPage:
        """Parse HTML and extract structured content.

        Args:
            url: Source URL
            html: Raw HTML content

        Returns:
            ScrapedPage with extracted data
        """
        soup = BeautifulSoup(html, "lxml")

        # Extract LD+JSON structured data before removing scripts
        ld_json_text = self._extract_ld_json(soup)

        # Remove script and style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Extract meta description
        meta_description = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_description = meta_tag["content"]

        # Extract main content (prefer <main>, <article>, fall back to <body>)
        content_text = ""
        for selector in ["main", "article"]:
            container = soup.find(selector)
            if container:
                content_text = container.get_text(separator=" ", strip=True)
                break
        if not content_text:
            body = soup.find("body")
            if body:
                content_text = body.get_text(separator=" ", strip=True)

        # Append LD+JSON structured data to content
        if ld_json_text:
            content_text = f"{content_text} {ld_json_text}".strip()

        # Extract outbound links
        links: list[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("http"):
                links.append(href)

        return ScrapedPage(
            url=url,
            title=title,
            content_text=content_text,
            meta_description=meta_description,
            links=links,
            fetched_at=datetime.now(UTC),
        )

    def _extract_ld_json(self, soup: BeautifulSoup) -> str:
        """Extract text from LD+JSON structured data scripts.

        Args:
            soup: Parsed BeautifulSoup document

        Returns:
            Concatenated text from LD+JSON name/description/text fields
        """
        texts: list[str] = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    for key in ("name", "description", "text"):
                        if key in data and isinstance(data[key], str):
                            texts.append(data[key])
            except (json.JSONDecodeError, TypeError):
                continue
        return " ".join(texts)

    async def scrape_competitor_pages(
        self, competitor: CompetitorConfig
    ) -> list[ScrapedPage]:
        """Scrape all configured website pages for a competitor.

        Checks robots.txt before each page, respects delay between requests.

        Args:
            competitor: Competitor configuration with website URLs

        Returns:
            List of successfully scraped pages
        """
        pages: list[ScrapedPage] = []

        for url in competitor.website_urls:
            # Check robots.txt
            allowed = await self.is_allowed(url)
            if not allowed:
                logger.info(
                    "Skipping %s for %s — disallowed by robots.txt",
                    url, competitor.name,
                )
                continue

            page = await self.scrape_page(url)
            if page is not None:
                pages.append(page)

            # Respect delay between requests
            if self._config.request_delay_seconds > 0:
                await asyncio.sleep(self._config.request_delay_seconds)

        logger.info(
            "Scraped %d/%d pages for %s",
            len(pages), len(competitor.website_urls), competitor.name,
        )
        return pages


__all__ = [
    "WebsiteScraperClient",
    "RetryMiddlewareProtocol",
    "RetryResultProtocol",
]
