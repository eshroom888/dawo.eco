"""Tests for RetryableHttpClient wrapper.

Tests verify:
- All external HTTP calls go through this client
- Automatically applies retry middleware to all requests
- Includes request timeout handling
- Config injection pattern
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from teams.dawo.middleware import (
    RetryConfig,
    RetryableHttpClient,
)


@pytest.fixture
def default_config() -> RetryConfig:
    """Create default retry configuration."""
    return RetryConfig()


@pytest.fixture
def client(default_config: RetryConfig) -> RetryableHttpClient:
    """Create RetryableHttpClient with default config."""
    return RetryableHttpClient(default_config, api_name="test")


class TestRetryableHttpClientInit:
    """Test RetryableHttpClient initialization."""

    def test_accepts_config_via_injection(self, default_config: RetryConfig) -> None:
        """Should accept config via constructor injection."""
        client = RetryableHttpClient(default_config, api_name="instagram")
        assert client is not None

    def test_accepts_api_name_for_context(self, default_config: RetryConfig) -> None:
        """Should accept api_name for logging context."""
        client = RetryableHttpClient(default_config, api_name="discord")
        assert client._api_name == "discord"


class TestGetRequest:
    """Test GET request method."""

    @pytest.mark.asyncio
    async def test_successful_get_returns_response(self, client: RetryableHttpClient) -> None:
        """Successful GET should return response data."""
        mock_response = httpx.Response(200, json={"data": "test"})

        with patch.object(client._httpx_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.get("http://example.com/api")

        assert result.success is True
        assert result.response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_uses_timeout_from_config(
        self, default_config: RetryConfig
    ) -> None:
        """GET should use timeout from config."""
        config = RetryConfig(timeout=45.0)
        client = RetryableHttpClient(config, api_name="test")

        mock_response = httpx.Response(200)

        with patch.object(client._httpx_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await client.get("http://example.com")

            # Verify timeout was passed
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs.get("timeout") == 45.0

    @pytest.mark.asyncio
    async def test_get_retries_on_5xx_error(self, client: RetryableHttpClient) -> None:
        """GET should retry on 5xx errors."""
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = httpx.Response(500)
                response.request = httpx.Request("GET", "http://test")
                raise httpx.HTTPStatusError("Server error", request=response.request, response=response)
            return httpx.Response(200, json={"ok": True})

        with patch.object(client._httpx_client, "get", side_effect=mock_get):
            with patch("asyncio.sleep", return_value=None):
                result = await client.get("http://example.com")

        assert result.success is True
        assert call_count == 3


class TestPostRequest:
    """Test POST request method."""

    @pytest.mark.asyncio
    async def test_successful_post_returns_response(self, client: RetryableHttpClient) -> None:
        """Successful POST should return response data."""
        mock_response = httpx.Response(201, json={"id": "123"})

        with patch.object(client._httpx_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.post("http://example.com/api", json={"name": "test"})

        assert result.success is True
        assert result.response.status_code == 201

    @pytest.mark.asyncio
    async def test_post_sends_json_payload(self, client: RetryableHttpClient) -> None:
        """POST should send JSON payload."""
        mock_response = httpx.Response(200)

        with patch.object(client._httpx_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client.post("http://example.com", json={"key": "value"})

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs.get("json") == {"key": "value"}


class TestTimeoutHandling:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_handled_gracefully(self, client: RetryableHttpClient) -> None:
        """Timeout errors should be handled gracefully."""
        with patch.object(client._httpx_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            with patch("asyncio.sleep", return_value=None):
                result = await client.get("http://slow.example.com")

        # Should return failure result, not raise exception
        assert result.success is False
        assert result.is_incomplete is True


class TestRetryIntegration:
    """Test integration with retry middleware."""

    @pytest.mark.asyncio
    async def test_respects_max_retries(self, default_config: RetryConfig) -> None:
        """Should respect max_retries from config."""
        config = RetryConfig(max_retries=2)
        client = RetryableHttpClient(config, api_name="test")

        call_count = 0

        async def always_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = httpx.Response(500)
            response.request = httpx.Request("GET", "http://test")
            raise httpx.HTTPStatusError("Server error", request=response.request, response=response)

        with patch.object(client._httpx_client, "get", side_effect=always_fail):
            with patch("asyncio.sleep", return_value=None):
                result = await client.get("http://example.com")

        assert result.success is False
        assert result.is_incomplete is True
        assert call_count == 2  # max_retries


class TestModuleExports:
    """Test module exports."""

    def test_retryable_http_client_exported(self) -> None:
        """RetryableHttpClient should be importable from middleware."""
        from teams.dawo.middleware import RetryableHttpClient
        assert RetryableHttpClient is not None
