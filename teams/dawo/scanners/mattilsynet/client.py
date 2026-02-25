"""Mattilsynet HTTP client with retry middleware.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 4: HTTP client for fetching RSS feeds and pages.

Uses RetryMiddleware for resilient HTTP requests with rate limiting.
"""

import asyncio
import logging
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

from teams.dawo.scanners.mattilsynet.config import (
    FeedConfig,
    MattilsynetMonitorConfig,
    MonitoredPageConfig,
)

logger = logging.getLogger(__name__)


class MattilsynetClientError(Exception):
    """Error fetching data from Mattilsynet."""


@runtime_checkable
class RetryResultProtocol(Protocol):
    """Protocol for retry middleware result."""

    @property
    def success(self) -> bool: ...

    @property
    def response(self) -> Any: ...

    @property
    def last_error(self) -> Optional[str]: ...


@runtime_checkable
class RetryMiddlewareProtocol(Protocol):
    """Protocol for retry middleware."""

    async def execute_with_retry(
        self, func: Any, context: str = ""
    ) -> RetryResultProtocol: ...


class MattilsynetClient:
    """HTTP client for Mattilsynet RSS feeds and pages.

    Fetches RSS/Atom feeds and HTML pages with retry middleware
    and rate limiting between requests.

    Attributes:
        _client: httpx async HTTP client
        _retry: Retry middleware for resilient requests
        _config: Monitor configuration
        _headers: Default request headers
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        retry: RetryMiddlewareProtocol,
        config: MattilsynetMonitorConfig,
    ) -> None:
        """Initialize client with dependencies.

        Args:
            http_client: httpx AsyncClient instance
            retry: Retry middleware for resilient requests
            config: Monitor configuration
        """
        self._client = http_client
        self._retry = retry
        self._config = config
        self._headers = {
            "Accept-Language": "no, nb, nn, en;q=0.5",
            "User-Agent": config.user_agent,
        }

    async def fetch_feed(self, feed_url: str) -> bytes:
        """Fetch RSS/Atom feed content.

        Args:
            feed_url: URL of the feed to fetch

        Returns:
            Raw feed content as bytes

        Raises:
            MattilsynetClientError: If fetch fails after retries
        """
        async def _fetch() -> bytes:
            resp = await self._client.get(
                feed_url,
                headers=self._headers,
                timeout=self._config.timeout_seconds,
                follow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content

        result = await self._retry.execute_with_retry(
            _fetch, context=f"mattilsynet_feed_{feed_url}"
        )
        if not result.success:
            raise MattilsynetClientError(
                f"Feed fetch failed for '{feed_url}' after retries: {result.last_error}"
            )
        return result.response

    async def fetch_page(self, page_url: str) -> bytes:
        """Fetch HTML page content.

        Args:
            page_url: URL of the page to fetch

        Returns:
            Raw page content as bytes

        Raises:
            MattilsynetClientError: If fetch fails after retries
        """
        async def _fetch() -> bytes:
            resp = await self._client.get(
                page_url,
                headers=self._headers,
                timeout=self._config.timeout_seconds,
                follow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content

        result = await self._retry.execute_with_retry(
            _fetch, context=f"mattilsynet_page_{page_url}"
        )
        if not result.success:
            raise MattilsynetClientError(
                f"Page fetch failed for '{page_url}' after retries: {result.last_error}"
            )
        return result.response

    async def fetch_all_feeds(
        self, feeds: list[FeedConfig]
    ) -> dict[str, bytes]:
        """Fetch all configured RSS feeds with rate limiting.

        Args:
            feeds: List of feed configurations

        Returns:
            Dict mapping feed name to raw content bytes.
            Failed feeds are omitted with a warning log.
        """
        results: dict[str, bytes] = {}
        for i, feed in enumerate(feeds):
            try:
                data = await self.fetch_feed(feed.url)
                results[feed.name] = data
                logger.debug("Fetched feed '%s' (%d bytes)", feed.name, len(data))
            except MattilsynetClientError as e:
                logger.warning("Failed to fetch feed '%s': %s", feed.name, e)

            if i < len(feeds) - 1:
                await asyncio.sleep(self._config.request_delay_seconds)

        return results

    async def fetch_all_pages(
        self, pages: list[MonitoredPageConfig]
    ) -> dict[str, bytes]:
        """Fetch all monitored pages with rate limiting.

        Args:
            pages: List of page configurations

        Returns:
            Dict mapping page name to raw content bytes.
            Failed pages are omitted with a warning log.
        """
        results: dict[str, bytes] = {}
        for i, page in enumerate(pages):
            try:
                data = await self.fetch_page(page.url)
                results[page.name] = data
                logger.debug("Fetched page '%s' (%d bytes)", page.name, len(data))
            except MattilsynetClientError as e:
                logger.warning("Failed to fetch page '%s': %s", page.name, e)

            if i < len(pages) - 1:
                await asyncio.sleep(self._config.request_delay_seconds)

        return results


__all__ = [
    "MattilsynetClient",
    "MattilsynetClientError",
    "RetryMiddlewareProtocol",
    "RetryResultProtocol",
]
