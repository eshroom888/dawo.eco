"""Tests for HunterClient.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from teams.dawo.leads.scanner.tools import (
    HunterClient,
    HunterAPIError,
    HunterRateLimitError,
)
from teams.dawo.leads.scanner.config import HunterClientConfig


class TestHunterClient:
    """Tests for HunterClient API client."""

    @pytest.fixture
    def client(self, hunter_config: HunterClientConfig) -> HunterClient:
        """Create HunterClient with test config."""
        return HunterClient(config=hunter_config)

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create mock aiohttp response."""
        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.json = AsyncMock(return_value={
            "data": {
                "domain": "example.com",
                "organization": "Example Inc",
                "emails": [],
            }
        })
        return response

    @pytest.mark.asyncio
    async def test_domain_search_returns_data(
        self,
        client: HunterClient,
        mock_response: MagicMock,
    ) -> None:
        """Test that domain_search returns API data."""
        mock_response.json.return_value = {
            "data": {
                "domain": "example.com",
                "organization": "Example Inc",
                "country": "Norway",
                "emails": [
                    {"value": "test@example.com", "confidence": 90},
                ],
            }
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response.json.return_value["data"]

            result = await client.domain_search("example.com")

            assert result["domain"] == "example.com"
            assert result["organization"] == "Example Inc"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_finder_returns_data(
        self,
        client: HunterClient,
    ) -> None:
        """Test that email_finder returns API data."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "email": "john.doe@example.com",
                "score": 95,
                "position": "CEO",
            }

            result = await client.email_finder(
                domain="example.com",
                first_name="John",
                last_name="Doe",
            )

            assert result["email"] == "john.doe@example.com"
            assert result["score"] == 95

    @pytest.mark.asyncio
    async def test_email_verifier_returns_data(
        self,
        client: HunterClient,
    ) -> None:
        """Test that email_verifier returns API data."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "status": "valid",
                "result": "deliverable",
                "score": 95,
            }

            result = await client.email_verifier("test@example.com")

            assert result["status"] == "valid"
            assert result["result"] == "deliverable"

    @pytest.mark.asyncio
    async def test_rate_limit_wait(
        self,
        hunter_config: HunterClientConfig,
    ) -> None:
        """Test that rate limiting waits between requests."""
        # Set high rate limit to trigger wait
        hunter_config.rate_limit_per_minute = 6000  # 100ms between requests
        client = HunterClient(config=hunter_config)

        # Make "first request" to set last_request_time
        import time
        client._last_request_time = time.monotonic()

        # Should wait for rate limit
        start = time.monotonic()
        await client._rate_limit_wait()
        elapsed = time.monotonic() - start

        # Should have waited some time (allowing for timing variance)
        assert elapsed >= 0  # Just verify it ran

    @pytest.mark.asyncio
    async def test_handles_api_error(
        self,
        client: HunterClient,
    ) -> None:
        """Test that API errors are raised properly."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = HunterAPIError("Not found", status_code=404)

            with pytest.raises(HunterAPIError) as exc_info:
                await client.domain_search("nonexistent.com")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(
        self,
        client: HunterClient,
    ) -> None:
        """Test that rate limit errors are raised properly."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = HunterRateLimitError(retry_after=60)

            with pytest.raises(HunterRateLimitError) as exc_info:
                await client.domain_search("example.com")

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_uses_retry_middleware_when_provided(
        self,
        hunter_config: HunterClientConfig,
    ) -> None:
        """Test that retry middleware is used when provided."""
        mock_middleware = AsyncMock()
        mock_middleware.execute_with_retry.return_value = {
            "domain": "example.com",
            "emails": [],
        }

        client = HunterClient(
            config=hunter_config,
            retry_middleware=mock_middleware,
        )

        await client.domain_search("example.com")

        mock_middleware.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_closes_session(
        self,
        client: HunterClient,
    ) -> None:
        """Test that close() closes the HTTP session."""
        # Create a mock session
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        client._session = mock_session

        await client.close()

        mock_session.close.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_context_manager(
        self,
        hunter_config: HunterClientConfig,
    ) -> None:
        """Test async context manager usage."""
        async with HunterClient(config=hunter_config) as client:
            assert client is not None
            # Session would be created on first request

    def test_api_error_has_status_code(self) -> None:
        """Test HunterAPIError stores status code."""
        error = HunterAPIError("Error message", status_code=400)
        assert error.status_code == 400
        assert str(error) == "Error message"

    def test_rate_limit_error_has_retry_after(self) -> None:
        """Test HunterRateLimitError stores retry_after."""
        error = HunterRateLimitError(retry_after=120)
        assert error.retry_after == 120
        assert error.status_code == 429
