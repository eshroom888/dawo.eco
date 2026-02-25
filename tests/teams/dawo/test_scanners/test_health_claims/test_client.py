"""Tests for HealthClaimsClient.

Story 6-1, Task 12.14-12.15: Client tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import Optional

from teams.dawo.scanners.health_claims.client import HealthClaimsClient, HealthClaimsClientError


@dataclass
class MockRetryResult:
    success: bool = True
    response: object = None
    attempts: int = 1
    last_error: Optional[str] = None
    is_incomplete: bool = False


class TestHealthClaimsClientDownload:
    """Test 12.14: download_register with mocked httpx."""

    @pytest.mark.asyncio
    async def test_download_success(self):
        http_client = AsyncMock()
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=True,
            response=b"<xls data content>",
            attempts=1,
        )

        client = HealthClaimsClient(
            http_client=http_client,
            retry=retry,
            download_url="https://example.com/test.xls",
        )

        result = await client.download_register()
        assert result == b"<xls data content>"
        retry.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_returns_bytes(self):
        http_client = AsyncMock()
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=True,
            response=b"\x50\x4b\x03\x04",  # ZIP header (XLS is actually ZIP)
            attempts=1,
        )

        client = HealthClaimsClient(
            http_client=http_client,
            retry=retry,
            download_url="https://example.com/test.xls",
        )

        result = await client.download_register()
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestHealthClaimsClientRetry:
    """Test 12.15: download_register retry on failure."""

    @pytest.mark.asyncio
    async def test_download_failure_raises(self):
        http_client = AsyncMock()
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=False,
            response=None,
            attempts=3,
            last_error="Connection timed out",
        )

        client = HealthClaimsClient(
            http_client=http_client,
            retry=retry,
            download_url="https://example.com/test.xls",
        )

        with pytest.raises(HealthClaimsClientError, match="Download failed"):
            await client.download_register()

    @pytest.mark.asyncio
    async def test_retry_called_with_context(self):
        http_client = AsyncMock()
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=True,
            response=b"<data>",
        )

        client = HealthClaimsClient(
            http_client=http_client,
            retry=retry,
            download_url="https://example.com/test.xls",
        )

        await client.download_register()
        call_args = retry.execute_with_retry.call_args
        assert call_args.kwargs.get("context") == "eu_health_claims_download" or \
               (len(call_args.args) > 1 and call_args.args[1] == "eu_health_claims_download")
