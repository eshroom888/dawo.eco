"""Website Analyzer for Lead Enrichment.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 2: Implement Website Analyzer

Fetches and analyzes company websites to extract:
- Business description
- Product categories
- Mushroom/supplement presence
- General content for LLM analysis
"""

import asyncio
import logging
import re
from time import monotonic
from typing import Optional, Protocol
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from teams.dawo.leads.enrichment.config import EnrichmentConfig
from teams.dawo.leads.enrichment.schemas import WebsiteAnalysis


logger = logging.getLogger(__name__)


# Mushroom-related keywords to detect
MUSHROOM_KEYWORDS = [
    "lion's mane",
    "lions mane",
    "løvemanke",  # Norwegian
    "chaga",
    "reishi",
    "cordyceps",
    "turkey tail",
    "maitake",
    "shiitake",
    "functional mushroom",
    "adaptogen",
    "medicinal mushroom",
]

# Supplement section indicators
SUPPLEMENT_INDICATORS = [
    "supplement",
    "kosttilskudd",  # Norwegian
    "tilskudd",  # Norwegian
    "vitamin",
    "mineral",
    "health product",
    "helsekost",  # Norwegian
]


class HttpClientProtocol(Protocol):
    """Protocol for HTTP client dependency injection."""

    async def get(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> httpx.Response:
        """Make GET request."""
        ...


class WebsiteAnalyzer:
    """Analyzes company websites for lead enrichment.

    Fetches website content, extracts text, and identifies
    relevant business information.

    Accepts HTTP client via dependency injection.
    Respects rate limits and handles failures gracefully.

    Attributes:
        _client: HTTP client for making requests
        _config: Enrichment configuration
        _timeout: Request timeout in seconds
        _last_request_time: Timestamp of last request (rate limiting)
        _min_request_interval: Minimum seconds between requests
    """

    def __init__(
        self,
        http_client: HttpClientProtocol,
        config: EnrichmentConfig,
    ) -> None:
        """Initialize the website analyzer.

        Args:
            http_client: HTTP client (httpx.AsyncClient)
            config: Enrichment configuration
        """
        self._client = http_client
        self._config = config
        self._timeout = config.website_timeout_seconds
        self._last_request_time: float = 0.0
        self._min_request_interval = 1.0 / config.website_rate_limit_per_second

    async def _rate_limit_wait(self) -> None:
        """Wait if needed to respect rate limits."""
        now = monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            wait_time = self._min_request_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self._last_request_time = monotonic()

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page.

        Args:
            url: Full URL to fetch

        Returns:
            HTML content as string, or None on failure
        """
        await self._rate_limit_wait()

        try:
            response = await self._client.get(
                url,
                timeout=float(self._timeout),
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching {url}")
            return None

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
            return None

        except httpx.ConnectError as e:
            logger.warning(f"Connection error fetching {url}: {e}")
            return None

        except httpx.RequestError as e:
            logger.warning(f"Request error fetching {url}: {e}")
            return None

    def extract_text(self, html: str) -> str:
        """Extract text content from HTML.

        Removes scripts, styles, and other non-content elements.

        Args:
            html: Raw HTML content

        Returns:
            Extracted text content
        """
        if not html:
            return ""

        try:
            soup = BeautifulSoup(html, "lxml")

            # Remove script and style elements
            for element in soup(["script", "style", "noscript", "iframe"]):
                element.decompose()

            # Get text
            text = soup.get_text(separator=" ", strip=True)

            # Clean up whitespace
            text = re.sub(r"\s+", " ", text)

            return text.strip()

        except Exception as e:
            logger.warning(f"Error extracting text from HTML: {e}")
            return ""

    def _extract_meta_description(self, html: str) -> Optional[str]:
        """Extract meta description from HTML.

        Args:
            html: Raw HTML content

        Returns:
            Meta description or None
        """
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")

            # Try meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                return str(meta_desc["content"])

            # Try og:description
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                return str(og_desc["content"])

            return None

        except Exception as e:
            logger.warning(f"Error extracting meta description: {e}")
            return None

    def _detect_mushroom_keywords(self, text: str) -> list[str]:
        """Detect mushroom-related keywords in text.

        Args:
            text: Text content to search

        Returns:
            List of found keywords
        """
        if not text:
            return []

        text_lower = text.lower()
        found = []

        for keyword in MUSHROOM_KEYWORDS:
            if keyword.lower() in text_lower:
                found.append(keyword)

        return found

    def _detect_supplement_section(self, html: str, text: str) -> bool:
        """Detect if website has a supplements section.

        Args:
            html: Raw HTML content
            text: Extracted text content

        Returns:
            True if supplement section detected
        """
        if not html and not text:
            return False

        combined = (html + " " + text).lower()

        for indicator in SUPPLEMENT_INDICATORS:
            if indicator.lower() in combined:
                return True

        return False

    async def _check_robots_txt(self, domain: str, path: str = "/") -> bool:
        """Check if path is allowed by robots.txt.

        Args:
            domain: Website domain
            path: Path to check

        Returns:
            True if path is allowed, False if disallowed

        Note:
            Defaults to True if robots.txt cannot be fetched.
        """
        robots_url = f"https://{domain}/robots.txt"

        try:
            html = await self.fetch_page(robots_url)
            if not html:
                return True  # No robots.txt, allow all

            # Simple robots.txt parsing
            # Full compliance would require robotexclusionrulesparser
            for line in html.split("\n"):
                line = line.strip().lower()
                if line.startswith("disallow:"):
                    disallowed_path = line.split(":", 1)[1].strip()
                    if disallowed_path and path.startswith(disallowed_path):
                        logger.debug(f"Path {path} disallowed by robots.txt")
                        return False

            return True

        except Exception as e:
            logger.debug(f"Could not check robots.txt for {domain}: {e}")
            return True  # Default to allow

    async def analyze(self, domain: str) -> WebsiteAnalysis:
        """Analyze a company website.

        Fetches homepage and extracts:
        - Business description
        - Content for LLM analysis
        - Mushroom keyword presence
        - Supplement section detection

        Args:
            domain: Company domain (e.g., "healthstore.no")

        Returns:
            WebsiteAnalysis with extracted data
        """
        # Normalize domain
        domain = domain.lower().strip()
        for prefix in ["https://", "http://", "www."]:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        domain = domain.rstrip("/")

        # Build URL
        homepage_url = f"https://{domain}"

        # Check robots.txt first
        allowed = await self._check_robots_txt(domain)
        if not allowed:
            logger.info(f"Skipping {domain} - disallowed by robots.txt")
            return WebsiteAnalysis(
                domain=domain,
                accessible=False,
            )

        # Fetch homepage
        html = await self.fetch_page(homepage_url)

        if html is None:
            # Try with www prefix
            html = await self.fetch_page(f"https://www.{domain}")

        if html is None:
            return WebsiteAnalysis(
                domain=domain,
                accessible=False,
            )

        # Extract content
        text = self.extract_text(html)
        description = self._extract_meta_description(html)
        mushroom_keywords = self._detect_mushroom_keywords(text)
        has_supplements = self._detect_supplement_section(html, text)

        # Try to fetch about page for more content
        about_pages = ["/about", "/om-oss", "/about-us", "/om"]
        for about_path in about_pages:
            about_url = urljoin(homepage_url, about_path)
            about_html = await self.fetch_page(about_url)
            if about_html:
                about_text = self.extract_text(about_html)
                text = text + " " + about_text

                # Check for more keywords in about page
                more_keywords = self._detect_mushroom_keywords(about_text)
                for kw in more_keywords:
                    if kw not in mushroom_keywords:
                        mushroom_keywords.append(kw)

                break  # Found about page, stop searching

        return WebsiteAnalysis(
            domain=domain,
            accessible=True,
            description=description,
            content=text[:10000] if text else None,  # Limit content size
            mushroom_keywords_found=mushroom_keywords,
            supplement_section=has_supplements,
        )
