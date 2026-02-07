"""Tests for news scanner agent."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from teams.dawo.scanners.news.agent import NewsScanner, NewsScanError
from teams.dawo.scanners.news.schemas import RawNewsArticle
from teams.dawo.scanners.news.config import FeedSource, NewsScannerConfig
from teams.dawo.scanners.news.tools import NewsFeedClient, FeedFetchError


class TestNewsScanner:
    """Tests for NewsScanner agent."""

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        """Create mock feed client."""
        client = AsyncMock(spec=NewsFeedClient)
        return client

    @pytest.fixture
    def scanner_config(self) -> NewsScannerConfig:
        """Create scanner config."""
        return NewsScannerConfig(
            feeds=[
                FeedSource("Feed1", "https://feed1.com/rss", is_tier_1=True),
                FeedSource("Feed2", "https://feed2.com/rss"),
            ],
            keywords=["mushrooms", "supplements"],
            hours_back=24,
        )

    @pytest.fixture
    def scanner(
        self,
        scanner_config: NewsScannerConfig,
        mock_client: AsyncMock,
    ) -> NewsScanner:
        """Create scanner instance."""
        return NewsScanner(scanner_config, mock_client)

    def _make_raw_article(
        self,
        title: str = "Test Article",
        url: str = "https://example.com/article",
    ) -> RawNewsArticle:
        """Helper to create raw article."""
        return RawNewsArticle(
            title=title,
            summary="Test summary",
            url=url,
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=False,
        )

    @pytest.mark.asyncio
    async def test_scan_success(
        self,
        scanner: NewsScanner,
        mock_client: AsyncMock,
    ) -> None:
        """Test successful scan across multiple feeds."""
        mock_client.fetch_feed.side_effect = [
            [self._make_raw_article(title="Article 1", url="https://ex.com/1")],
            [self._make_raw_article(title="Article 2", url="https://ex.com/2")],
        ]

        result = await scanner.scan()

        assert len(result.articles) == 2
        assert result.statistics.feeds_processed == 2
        assert result.statistics.feeds_failed == 0
        assert result.statistics.total_articles_found == 2

    @pytest.mark.asyncio
    async def test_scan_deduplicates_by_url(
        self,
        scanner: NewsScanner,
        mock_client: AsyncMock,
    ) -> None:
        """Test that duplicate URLs are removed."""
        # Both feeds return same article
        article = self._make_raw_article()
        mock_client.fetch_feed.side_effect = [
            [article],
            [article],
        ]

        result = await scanner.scan()

        assert len(result.articles) == 1
        assert result.statistics.duplicates_removed == 1

    @pytest.mark.asyncio
    async def test_scan_handles_partial_failure(
        self,
        scanner: NewsScanner,
        mock_client: AsyncMock,
    ) -> None:
        """Test that scan continues when some feeds fail."""
        mock_client.fetch_feed.side_effect = [
            [self._make_raw_article()],  # First feed succeeds
            FeedFetchError("Connection error"),  # Second feed fails
        ]

        result = await scanner.scan()

        assert len(result.articles) == 1
        assert result.statistics.feeds_processed == 1
        assert result.statistics.feeds_failed == 1
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_scan_raises_when_all_feeds_fail(
        self,
        scanner: NewsScanner,
        mock_client: AsyncMock,
    ) -> None:
        """Test that NewsScanError is raised when all feeds fail."""
        mock_client.fetch_feed.side_effect = [
            FeedFetchError("Error 1"),
            FeedFetchError("Error 2"),
        ]

        with pytest.raises(NewsScanError, match="All feeds failed"):
            await scanner.scan()

    @pytest.mark.asyncio
    async def test_scan_returns_empty_when_no_articles(
        self,
        scanner: NewsScanner,
        mock_client: AsyncMock,
    ) -> None:
        """Test scan with no articles found."""
        mock_client.fetch_feed.side_effect = [[], []]

        result = await scanner.scan()

        assert result.articles == []
        assert result.statistics.total_articles_found == 0
        assert result.statistics.feeds_processed == 2

    @pytest.mark.asyncio
    async def test_scan_statistics_accuracy(
        self,
        scanner: NewsScanner,
        mock_client: AsyncMock,
    ) -> None:
        """Test that statistics are accurate."""
        mock_client.fetch_feed.side_effect = [
            [
                self._make_raw_article(url="https://ex.com/1"),
                self._make_raw_article(url="https://ex.com/2"),
            ],
            [
                self._make_raw_article(url="https://ex.com/2"),  # Duplicate
                self._make_raw_article(url="https://ex.com/3"),
            ],
        ]

        result = await scanner.scan()

        assert result.statistics.total_articles_found == 4
        assert result.statistics.articles_after_filter == 3  # After dedup
        assert result.statistics.duplicates_removed == 1

    def test_deduplicate_preserves_first_occurrence(
        self,
        scanner: NewsScanner,
    ) -> None:
        """Test that deduplication keeps first occurrence."""
        articles = [
            self._make_raw_article(title="First", url="https://ex.com/same"),
            self._make_raw_article(title="Second", url="https://ex.com/same"),
        ]

        result = scanner._deduplicate(articles)

        assert len(result) == 1
        assert result[0].title == "First"
