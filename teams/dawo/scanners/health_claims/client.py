"""Health Claims Register HTTP client.

Epic 6, Story 6-1, Task 4: Health claims client.

Downloads the EU Health Claims Register from the EU Open Data Portal.
Uses RetryMiddleware for resilient HTTP requests.
"""

import logging
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

logger = logging.getLogger(__name__)


class HealthClaimsClientError(Exception):
    """Raised when health claims download fails after retries."""


@runtime_checkable
class RetryResultProtocol(Protocol):
    """Protocol for RetryMiddleware result object."""

    success: bool
    response: Any
    last_error: Optional[str]


@runtime_checkable
class RetryMiddlewareProtocol(Protocol):
    """Protocol for RetryMiddleware dependency injection."""

    async def execute_with_retry(self, func: Any, context: str = "") -> RetryResultProtocol: ...


class HealthClaimsClient:
    """HTTP client for downloading EU Health Claims Register.

    Story 6-1, Task 4: Download XLS from EU Open Data Portal.

    Accepts httpx.AsyncClient and RetryMiddleware via constructor.
    All HTTP requests go through retry middleware.

    Attributes:
        _client: Async HTTP client for making requests
        _retry: Retry middleware for resilient requests
        _download_url: Direct download URL for register file
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        retry: RetryMiddlewareProtocol,
        download_url: str,
    ) -> None:
        """Initialize health claims client.

        Args:
            http_client: Async HTTP client
            retry: Retry middleware instance
            download_url: Direct XLS download URL
        """
        self._client = http_client
        self._retry = retry
        self._download_url = download_url

    async def download_register(self) -> bytes:
        """Download the EU Health Claims Register.

        Downloads the XLS file from the EU Open Data Portal using
        RetryMiddleware for resilient HTTP requests.

        Returns:
            Raw bytes of downloaded register file

        Raises:
            HealthClaimsClientError: If download fails after retries
        """
        async def _download() -> bytes:
            resp = await self._client.get(
                self._download_url,
                follow_redirects=True,
            )
            resp.raise_for_status()
            if not resp.content:
                raise HealthClaimsClientError("Empty response body")
            return resp.content

        result = await self._retry.execute_with_retry(
            _download, context="eu_health_claims_download"
        )
        if not result.success:
            raise HealthClaimsClientError(
                f"Download failed after retries: {result.last_error}"
            )
        logger.info(
            "Downloaded EU Health Claims Register: %d bytes",
            len(result.response),
        )
        return result.response


__all__ = [
    "HealthClaimsClient",
    "HealthClaimsClientError",
]
