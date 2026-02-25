"""Tests for Mattilsynet HTTP client.

Epic 6, Story 6-3: Tasks 13.19-13.22.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from teams.dawo.scanners.mattilsynet.client import (
    MattilsynetClient,
    MattilsynetClientError,
)
from teams.dawo.scanners.mattilsynet.config import (
    FeedConfig,
    MattilsynetMonitorConfig,
    MonitoredPageConfig,
)


@pytest.fixture
def config() -> MattilsynetMonitorConfig:
    return MattilsynetMonitorConfig(
        feeds=(FeedConfig(name="test", url="https://example.com/rss"),),
        keywords_tier_1=("kosttilskudd",),
        request_delay_seconds=0,  # No delay in tests
        timeout_seconds=5,
    )


@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    response = MagicMock()
    response.content = b"<rss>test content</rss>"
    response.raise_for_status = MagicMock()
    client.get.return_value = response
    return client


@pytest.fixture
def success_retry_result():
    result = MagicMock()
    result.success = True
    result.response = b"<rss>test content</rss>"
    result.last_error = None
    return result


@pytest.fixture
def failure_retry_result():
    result = MagicMock()
    result.success = False
    result.response = None
    result.last_error = "Connection timeout"
    return result


@pytest.fixture
def mock_retry(success_retry_result):
    retry = AsyncMock()
    retry.execute_with_retry.return_value = success_retry_result
    return retry


class TestFetchFeed:
    """Test fetch_feed method."""

    @pytest.mark.asyncio
    async def test_returns_feed_bytes(self, mock_http_client, mock_retry, config) -> None:
        client = MattilsynetClient(mock_http_client, mock_retry, config)
        data = await client.fetch_feed("https://example.com/rss")
        assert data == b"<rss>test content</rss>"

    @pytest.mark.asyncio
    async def test_uses_retry_middleware(self, mock_http_client, mock_retry, config) -> None:
        client = MattilsynetClient(mock_http_client, mock_retry, config)
        await client.fetch_feed("https://example.com/rss")
        mock_retry.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_failure(self, mock_http_client, failure_retry_result, config) -> None:
        retry = AsyncMock()
        retry.execute_with_retry.return_value = failure_retry_result
        client = MattilsynetClient(mock_http_client, retry, config)
        with pytest.raises(MattilsynetClientError, match="Feed fetch failed"):
            await client.fetch_feed("https://example.com/rss")


class TestFetchPage:
    """Test fetch_page method."""

    @pytest.mark.asyncio
    async def test_returns_page_bytes(self, mock_http_client, mock_retry, config) -> None:
        client = MattilsynetClient(mock_http_client, mock_retry, config)
        data = await client.fetch_page("https://example.com/page")
        assert data == b"<rss>test content</rss>"

    @pytest.mark.asyncio
    async def test_raises_on_failure(self, mock_http_client, failure_retry_result, config) -> None:
        retry = AsyncMock()
        retry.execute_with_retry.return_value = failure_retry_result
        client = MattilsynetClient(mock_http_client, retry, config)
        with pytest.raises(MattilsynetClientError, match="Page fetch failed"):
            await client.fetch_page("https://example.com/page")


class TestFetchAllFeeds:
    """Test fetch_all_feeds rate limiting."""

    @pytest.mark.asyncio
    async def test_returns_dict_of_feeds(self, mock_http_client, mock_retry, config) -> None:
        client = MattilsynetClient(mock_http_client, mock_retry, config)
        feeds = [
            FeedConfig(name="Feed1", url="https://example.com/rss1"),
            FeedConfig(name="Feed2", url="https://example.com/rss2"),
        ]
        result = await client.fetch_all_feeds(feeds)
        assert len(result) == 2
        assert "Feed1" in result
        assert "Feed2" in result

    @pytest.mark.asyncio
    async def test_rate_limiting_delay(self, mock_http_client, mock_retry) -> None:
        config = MattilsynetMonitorConfig(
            feeds=(FeedConfig(name="test", url="https://example.com/rss"),),
            keywords_tier_1=("kosttilskudd",),
            request_delay_seconds=0,  # Minimal delay for test speed
        )
        client = MattilsynetClient(mock_http_client, mock_retry, config)
        feeds = [
            FeedConfig(name="F1", url="https://a.com"),
            FeedConfig(name="F2", url="https://b.com"),
        ]
        with patch("teams.dawo.scanners.mattilsynet.client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client.fetch_all_feeds(feeds)
            # Should sleep between feeds, not after last
            mock_sleep.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_handles_failed_feeds(self, mock_http_client, config) -> None:
        failure_result = MagicMock()
        failure_result.success = False
        failure_result.response = None
        failure_result.last_error = "error"

        retry = AsyncMock()
        retry.execute_with_retry.return_value = failure_result

        client = MattilsynetClient(mock_http_client, retry, config)
        feeds = [FeedConfig(name="Bad", url="https://fail.com")]
        result = await client.fetch_all_feeds(feeds)
        assert len(result) == 0  # Failed feed omitted
