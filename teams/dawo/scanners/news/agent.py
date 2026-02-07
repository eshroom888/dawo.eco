"""NewsScanner agent for Industry News research.

Implements the scanner stage of the Harvester Framework for news feeds.
Fetches and filters news from configured RSS/Atom feeds.

UNIQUE to News Scanner:
    - Fully rule-based: NO LLM stages
    - Uses tier="scan" (but no actual LLM calls - pure Python)
    - Processes RSS/Atom feeds from industry news sources

Usage:
    scanner = NewsScanner(config, feed_client)
    result = await scanner.scan()
"""

import logging
from typing import Optional

from .config import NewsScannerConfig, FeedSource
from .schemas import RawNewsArticle, ScanResult, ScanStatistics
from .tools import NewsFeedClient, FeedFetchError

logger = logging.getLogger(__name__)


class NewsScanError(Exception):
    """Raised when news scanning fails critically."""

    pass


class NewsScanner:
    """Scanner agent for news research.

    Fetches news from configured RSS/Atom feeds, filters by keywords
    and date, and deduplicates by URL.

    Attributes:
        _config: Scanner configuration
        _client: Feed client for fetching
    """

    def __init__(
        self,
        config: NewsScannerConfig,
        feed_client: NewsFeedClient,
    ) -> None:
        """Initialize news scanner.

        Args:
            config: Scanner configuration
            feed_client: Feed client for HTTP requests
        """
        self._config = config
        self._client = feed_client

    async def scan(self) -> ScanResult:
        """Execute news scan across all configured feeds.

        Returns:
            ScanResult with articles and statistics

        Raises:
            NewsScanError: If all feeds fail
        """
        all_articles: list[RawNewsArticle] = []
        errors: list[str] = []
        statistics = ScanStatistics()

        for feed in self._config.feeds:
            try:
                articles = await self._scan_feed(feed)
                all_articles.extend(articles)
                statistics.feeds_processed += 1
                statistics.total_articles_found += len(articles)
                logger.info("Fetched %d articles from %s", len(articles), feed.name)
            except FeedFetchError as e:
                statistics.feeds_failed += 1
                errors.append(f"Feed {feed.name}: {e}")
                logger.error("Failed to fetch feed %s: %s", feed.name, e)

        # Deduplicate by URL
        unique_articles = self._deduplicate(all_articles)
        statistics.duplicates_removed = len(all_articles) - len(unique_articles)
        statistics.articles_after_filter = len(unique_articles)

        logger.info(
            "Scan complete: %d feeds processed, %d failed, %d articles, %d duplicates removed",
            statistics.feeds_processed,
            statistics.feeds_failed,
            statistics.articles_after_filter,
            statistics.duplicates_removed,
        )

        # If all feeds failed, raise error
        if statistics.feeds_processed == 0 and statistics.feeds_failed > 0:
            raise NewsScanError(f"All feeds failed: {'; '.join(errors)}")

        return ScanResult(
            articles=unique_articles,
            statistics=statistics,
            errors=errors,
        )

    async def _scan_feed(self, feed: FeedSource) -> list[RawNewsArticle]:
        """Scan a single feed.

        Args:
            feed: Feed source to scan

        Returns:
            List of articles from this feed

        Raises:
            FeedFetchError: On fetch failure
        """
        return await self._client.fetch_feed(
            feed=feed,
            hours_back=self._config.hours_back,
            keywords=self._config.keywords,
        )

    def _deduplicate(self, articles: list[RawNewsArticle]) -> list[RawNewsArticle]:
        """Remove duplicate articles by URL.

        Args:
            articles: List of articles to deduplicate

        Returns:
            Deduplicated list (first occurrence kept)
        """
        seen_urls: set[str] = set()
        unique: list[RawNewsArticle] = []

        for article in articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique.append(article)

        return unique
