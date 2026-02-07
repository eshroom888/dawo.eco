"""Tests for news feed client."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Any

import pytest

from teams.dawo.scanners.news.tools import (
    NewsFeedClient,
    FeedFetchError,
)
from teams.dawo.scanners.news.config import (
    FeedSource,
    NewsFeedClientConfig,
)


class TestNewsFeedClient:
    """Tests for NewsFeedClient."""

    @pytest.fixture
    def client_config(self) -> NewsFeedClientConfig:
        """Create client config."""
        return NewsFeedClientConfig(fetch_timeout=30, max_retries=3)

    @pytest.fixture
    def client(self, client_config: NewsFeedClientConfig) -> NewsFeedClient:
        """Create client instance."""
        return NewsFeedClient(client_config)

    @pytest.fixture
    def feed_source(self) -> FeedSource:
        """Create feed source."""
        return FeedSource(
            name="TestFeed",
            url="https://test.com/rss",
            is_tier_1=True,
        )

    @pytest.fixture
    def mock_feed_response(self) -> dict[str, Any]:
        """Mock feedparser response."""
        now = datetime.now(timezone.utc)
        return {
            "entries": [
                {
                    "title": "Article 1",
                    "summary": "<p>Summary 1</p>",
                    "link": "https://test.com/article1",
                    "published_parsed": now.timetuple()[:6],
                },
                {
                    "title": "Article 2",
                    "summary": "Summary 2",
                    "link": "https://test.com/article2",
                    "published_parsed": (now - timedelta(hours=12)).timetuple()[:6],
                },
            ],
            "bozo": False,
            "bozo_exception": None,
        }

    @pytest.mark.asyncio
    async def test_fetch_feed_success(
        self,
        client: NewsFeedClient,
        feed_source: FeedSource,
        mock_feed_response: dict,
    ) -> None:
        """Test successful feed fetch."""
        with patch.object(
            client, "_fetch_content", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = "<rss>content</rss>"

            with patch(
                "teams.dawo.scanners.news.tools.feedparser.parse"
            ) as mock_parse:
                mock_parse.return_value = MagicMock(**mock_feed_response)

                result = await client.fetch_feed(feed_source)

        assert len(result) == 2
        assert result[0].title == "Article 1"
        assert result[0].source_name == "TestFeed"
        assert result[0].is_tier_1 is True

    @pytest.mark.asyncio
    async def test_fetch_feed_filters_by_date(
        self,
        client: NewsFeedClient,
        feed_source: FeedSource,
    ) -> None:
        """Test that old articles are filtered out."""
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(hours=48)).timetuple()[:6]  # 48 hours ago

        mock_response = {
            "entries": [
                {
                    "title": "Old Article",
                    "summary": "Old",
                    "link": "https://test.com/old",
                    "published_parsed": old_date,
                },
            ],
            "bozo": False,
            "bozo_exception": None,
        }

        with patch.object(
            client, "_fetch_content", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = "<rss>content</rss>"

            with patch(
                "teams.dawo.scanners.news.tools.feedparser.parse"
            ) as mock_parse:
                mock_parse.return_value = MagicMock(**mock_response)

                result = await client.fetch_feed(
                    feed_source, hours_back=24
                )

        # Should be empty - article is older than 24 hours
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_feed_filters_by_keywords(
        self,
        client: NewsFeedClient,
        feed_source: FeedSource,
    ) -> None:
        """Test keyword filtering."""
        now = datetime.now(timezone.utc)

        mock_response = {
            "entries": [
                {
                    "title": "Mushroom Article",
                    "summary": "About functional mushrooms",
                    "link": "https://test.com/mushrooms",
                    "published_parsed": now.timetuple()[:6],
                },
                {
                    "title": "Unrelated Article",
                    "summary": "About something else",
                    "link": "https://test.com/other",
                    "published_parsed": now.timetuple()[:6],
                },
            ],
            "bozo": False,
            "bozo_exception": None,
        }

        with patch.object(
            client, "_fetch_content", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = "<rss>content</rss>"

            with patch(
                "teams.dawo.scanners.news.tools.feedparser.parse"
            ) as mock_parse:
                mock_parse.return_value = MagicMock(**mock_response)

                result = await client.fetch_feed(
                    feed_source, keywords=["mushroom"]
                )

        # Should only return the mushroom article
        assert len(result) == 1
        assert "mushroom" in result[0].title.lower()

    @pytest.mark.asyncio
    async def test_fetch_feed_cleans_html(
        self,
        client: NewsFeedClient,
        feed_source: FeedSource,
    ) -> None:
        """Test that HTML is cleaned from summary."""
        now = datetime.now(timezone.utc)

        mock_response = {
            "entries": [
                {
                    "title": "Test Article",
                    "summary": "<p><strong>Bold</strong> text</p>",
                    "link": "https://test.com/article",
                    "published_parsed": now.timetuple()[:6],
                },
            ],
            "bozo": False,
            "bozo_exception": None,
        }

        with patch.object(
            client, "_fetch_content", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = "<rss>content</rss>"

            with patch(
                "teams.dawo.scanners.news.tools.feedparser.parse"
            ) as mock_parse:
                mock_parse.return_value = MagicMock(**mock_response)

                result = await client.fetch_feed(feed_source)

        assert len(result) == 1
        assert "<p>" not in result[0].summary
        assert "<strong>" not in result[0].summary

    @pytest.mark.asyncio
    async def test_fetch_feed_handles_empty_feed(
        self,
        client: NewsFeedClient,
        feed_source: FeedSource,
    ) -> None:
        """Test handling of empty feed."""
        mock_response = {
            "entries": [],
            "bozo": False,
            "bozo_exception": None,
        }

        with patch.object(
            client, "_fetch_content", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = "<rss></rss>"

            with patch(
                "teams.dawo.scanners.news.tools.feedparser.parse"
            ) as mock_parse:
                mock_parse.return_value = MagicMock(**mock_response)

                result = await client.fetch_feed(feed_source)

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_feed_http_error(
        self,
        client: NewsFeedClient,
        feed_source: FeedSource,
    ) -> None:
        """Test handling of HTTP error."""
        with patch.object(
            client, "_fetch_content", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = FeedFetchError("HTTP 500")

            with pytest.raises(FeedFetchError, match="HTTP 500"):
                await client.fetch_feed(feed_source)

    def test_clean_html(
        self,
        client: NewsFeedClient,
    ) -> None:
        """Test HTML cleaning utility."""
        html = "<p><strong>Bold</strong> and <em>italic</em></p>"

        result = client._clean_html(html)

        assert "<p>" not in result
        assert "<strong>" not in result
        assert "Bold" in result
        assert "italic" in result

    def test_clean_html_empty(
        self,
        client: NewsFeedClient,
    ) -> None:
        """Test HTML cleaning with empty string."""
        assert client._clean_html("") == ""

    def test_parse_date_valid(
        self,
        client: NewsFeedClient,
    ) -> None:
        """Test date parsing with valid date."""
        now = datetime.now(timezone.utc)
        entry = {"published_parsed": now.timetuple()[:6]}

        result = client._parse_date(entry)

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parse_date_missing(
        self,
        client: NewsFeedClient,
    ) -> None:
        """Test date parsing with missing date."""
        entry = {}

        result = client._parse_date(entry)

        assert result is None
