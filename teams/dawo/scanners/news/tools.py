"""Tools for Industry News Scanner.

Provides:
    - NewsFeedClient: RSS/Atom feed client for news aggregation
    - FeedFetchError: Exception for feed fetch failures
    - FeedParseError: Exception for feed parse failures

Feed client wraps all HTTP calls with retry middleware (Story 1.5).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol

import aiohttp
import feedparser
from bs4 import BeautifulSoup

from .config import FeedSource, NewsFeedClientConfig, DEFAULT_FETCH_TIMEOUT
from .schemas import RawNewsArticle

logger = logging.getLogger(__name__)


class FeedFetchError(Exception):
    """Raised when feed fetch fails after retries."""

    pass


class FeedParseError(Exception):
    """Raised when feed content cannot be parsed."""

    pass


class RetryMiddlewareProtocol(Protocol):
    """Protocol for retry middleware dependency injection."""

    async def execute(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute function with retry logic."""
        ...


class NewsFeedClient:
    """RSS/Atom feed client for news aggregation.

    Accepts configuration via dependency injection - NEVER loads files directly.
    Wraps all fetches with retry middleware (Story 1.5).

    Attributes:
        _config: Feed client configuration
        _retry: Retry middleware for HTTP calls
    """

    def __init__(
        self,
        config: NewsFeedClientConfig,
        retry_middleware: RetryMiddlewareProtocol,
    ) -> None:
        """Initialize feed client.

        Args:
            config: Feed client configuration
            retry_middleware: Retry middleware for HTTP requests (required per project-context.md)
        """
        self._config = config
        self._retry = retry_middleware

    async def fetch_feed(
        self,
        feed: FeedSource,
        hours_back: int = 24,
        keywords: Optional[list[str]] = None,
    ) -> list[RawNewsArticle]:
        """Fetch and parse RSS/Atom feed.

        Args:
            feed: Feed source configuration
            hours_back: Only include articles from last N hours
            keywords: Optional keyword filter (any match)

        Returns:
            List of RawNewsArticle objects matching filters

        Raises:
            FeedFetchError: On connection/timeout failure
            FeedParseError: On feed parsing failure
        """
        try:
            content = await self._fetch_content(feed.url)
            return self._parse_feed(
                content=content,
                feed=feed,
                hours_back=hours_back,
                keywords=keywords,
            )
        except FeedFetchError:
            raise
        except FeedParseError:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching feed %s: %s", feed.name, e)
            raise FeedFetchError(f"Failed to fetch {feed.name}: {e}") from e

    async def _fetch_content(self, url: str) -> str:
        """Fetch raw content from URL.

        Uses retry middleware (Story 1.5 integration).

        Args:
            url: Feed URL to fetch

        Returns:
            Raw feed content as string

        Raises:
            FeedFetchError: On HTTP error or timeout (after retries exhausted)
        """
        # Wrap with retry middleware per project-context.md requirement
        return await self._retry.execute(self._fetch_content_raw, url)

    async def _fetch_content_raw(self, url: str) -> str:
        """Raw HTTP fetch without retry wrapper.

        Args:
            url: Feed URL to fetch

        Returns:
            Raw feed content as string

        Raises:
            FeedFetchError: On HTTP error or timeout
        """
        timeout = aiohttp.ClientTimeout(total=self._config.fetch_timeout)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error("Feed fetch failed: %s returned %d", url, response.status)
                        raise FeedFetchError(f"HTTP {response.status} from {url}")
                    return await response.text()
        except aiohttp.ClientError as e:
            logger.error("Connection error fetching %s: %s", url, e)
            raise FeedFetchError(f"Connection error: {e}") from e
        except TimeoutError as e:
            logger.error("Timeout fetching %s", url)
            raise FeedFetchError(f"Timeout fetching {url}") from e

    def _parse_feed(
        self,
        content: str,
        feed: FeedSource,
        hours_back: int,
        keywords: Optional[list[str]],
    ) -> list[RawNewsArticle]:
        """Parse feed content into articles.

        Args:
            content: Raw feed XML content
            feed: Feed source configuration
            hours_back: Time filter in hours
            keywords: Optional keyword filter

        Returns:
            List of RawNewsArticle objects

        Raises:
            FeedParseError: If feed cannot be parsed
        """
        parsed = feedparser.parse(content)

        if parsed.bozo and parsed.bozo_exception:
            logger.warning("Feed parse warning for %s: %s", feed.name, parsed.bozo_exception)

        if not parsed.entries:
            logger.info("No entries found in feed %s", feed.name)
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        articles: list[RawNewsArticle] = []

        for entry in parsed.entries:
            pub_date = self._parse_date(entry)

            # Skip if too old
            if pub_date and pub_date < cutoff:
                continue

            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")

            # Keyword filter
            if keywords:
                text = f"{title} {summary}".lower()
                if not any(kw.lower() in text for kw in keywords):
                    continue

            # Clean HTML from summary
            cleaned_summary = self._clean_html(summary)

            articles.append(
                RawNewsArticle(
                    title=title,
                    summary=cleaned_summary,
                    url=entry.get("link", ""),
                    published=pub_date,
                    source_name=feed.name,
                    is_tier_1=feed.is_tier_1,
                )
            )

        logger.info(
            "Parsed %d articles from %s (after filters)",
            len(articles),
            feed.name,
        )
        return articles

    def _parse_date(self, entry: dict[str, Any]) -> Optional[datetime]:
        """Parse publication date from feed entry.

        Args:
            entry: Feed entry dictionary

        Returns:
            Parsed datetime in UTC, or None if unparseable
        """
        # feedparser normalizes to published_parsed or updated_parsed
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError) as e:
                logger.warning("Failed to parse date from entry: %s", e)
        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text.

        Args:
            text: Text potentially containing HTML

        Returns:
            Plain text with HTML removed
        """
        if not text:
            return ""
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text(separator=" ").strip()
