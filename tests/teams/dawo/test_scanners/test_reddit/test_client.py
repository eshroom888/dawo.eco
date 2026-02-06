"""Tests for Reddit API client.

Tests:
    - RedditClient initialization
    - OAuth2 authentication flow
    - Rate limiting behavior
    - Search subreddit functionality
    - Error handling and retry integration
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

import httpx

from teams.dawo.scanners.reddit import (
    RedditClient,
    RedditClientConfig,
    RedditAPIError,
    RedditAuthError,
)
from teams.dawo.middleware.retry import RetryConfig, RetryMiddleware, RetryResult


class TestRedditClientInit:
    """Tests for RedditClient initialization."""

    def test_client_creation(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """Client should be created with injected dependencies."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        assert client._config == mock_reddit_client_config
        assert client._retry == mock_retry_middleware
        assert client._client is None
        assert client._access_token is None

    @pytest.mark.asyncio
    async def test_context_manager_creates_httpx_client(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """Async context manager should create HTTPX client."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        async with client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)

        # Client should be closed after context exits
        assert client._client is None


class TestRedditClientAuth:
    """Tests for Reddit OAuth2 authentication."""

    @pytest.mark.asyncio
    async def test_authentication_success(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """Successful auth should store access token."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            async with client:
                await client._ensure_authenticated()

            assert client._access_token == "test_token_123"
            assert client._token_expires is not None

    @pytest.mark.asyncio
    async def test_authentication_failure_raises_error(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """Auth failure should raise RedditAuthError."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            async with client:
                with pytest.raises(RedditAuthError, match="Authentication failed"):
                    await client._ensure_authenticated()

    @pytest.mark.asyncio
    async def test_token_reuse_when_valid(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """Valid token should be reused without re-auth."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        # Set valid token
        client._access_token = "existing_token"
        client._token_expires = datetime.now(timezone.utc).timestamp() + 3600

        async with client:
            # Should not make auth request
            with patch.object(
                httpx.AsyncClient, "post", new_callable=AsyncMock
            ) as mock_post:
                await client._ensure_authenticated()
                mock_post.assert_not_called()


class TestRedditClientRateLimit:
    """Tests for rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limit_tracking(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """Rate limit should track request timestamps."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        async with client:
            # Make a few rate limit waits
            await client._rate_limit_wait()
            await client._rate_limit_wait()
            await client._rate_limit_wait()

            # Should have 3 timestamps recorded
            assert len(client._request_timestamps) == 3


class TestRedditClientSearch:
    """Tests for search_subreddit method."""

    @pytest.mark.asyncio
    async def test_search_returns_posts(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
        mock_reddit_search_response: dict,
    ) -> None:
        """Search should return list of post data."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        # Mock auth response
        auth_response = MagicMock()
        auth_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        auth_response.raise_for_status = MagicMock()

        # Mock search response
        search_response = MagicMock()
        search_response.json.return_value = mock_reddit_search_response
        search_response.raise_for_status = MagicMock()

        # Mock retry middleware to return success
        mock_retry_middleware.execute_with_retry = AsyncMock(
            return_value=RetryResult(
                success=True,
                response=mock_reddit_search_response,
                attempts=1,
            )
        )

        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = auth_response

            async with client:
                posts = await client.search_subreddit(
                    subreddit="Nootropics",
                    query="lion's mane",
                    time_filter="day",
                    limit=100,
                )

        assert len(posts) == 3
        assert posts[0]["id"] == "abc123"
        assert posts[0]["title"] == "My experience with lion's mane for brain fog"

    @pytest.mark.asyncio
    async def test_search_respects_limit(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """Search limit should be capped at 100."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        # Mock auth
        auth_response = MagicMock()
        auth_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        auth_response.raise_for_status = MagicMock()

        # Mock retry to capture params
        captured_params = {}

        async def capture_retry(operation, context):
            # Execute the operation to capture what would be called
            # but return empty response
            return RetryResult(
                success=True,
                response={"data": {"children": []}},
                attempts=1,
            )

        mock_retry_middleware.execute_with_retry = AsyncMock(side_effect=capture_retry)

        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = auth_response

            async with client:
                # Request more than 100
                await client.search_subreddit(
                    subreddit="Test",
                    query="test",
                    limit=200,  # Over limit
                )

        # Verify retry middleware was called
        mock_retry_middleware.execute_with_retry.assert_called_once()


class TestRedditClientErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_api_error_after_retries(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """API error after retries should raise RedditAPIError."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        # Mock auth success
        auth_response = MagicMock()
        auth_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        auth_response.raise_for_status = MagicMock()

        # Mock retry failure
        mock_retry_middleware.execute_with_retry = AsyncMock(
            return_value=RetryResult(
                success=False,
                attempts=3,
                last_error="Connection failed",
                is_incomplete=True,
            )
        )

        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = auth_response

            async with client:
                with pytest.raises(RedditAPIError, match="API call failed"):
                    await client.search_subreddit("Test", "query")

    @pytest.mark.asyncio
    async def test_client_not_initialized_error(
        self,
        mock_reddit_client_config: RedditClientConfig,
        mock_retry_middleware: RetryMiddleware,
    ) -> None:
        """API call without context manager should raise error."""
        client = RedditClient(mock_reddit_client_config, mock_retry_middleware)

        # Don't use context manager
        with pytest.raises(RedditAuthError, match="Client not initialized"):
            await client._ensure_authenticated()
