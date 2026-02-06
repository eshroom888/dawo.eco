"""Retryable HTTP client wrapper for external API calls.

This module provides a unified HTTP client that automatically applies
retry middleware to all external API requests.

Architecture Compliance:
- Configuration injected via constructor (NEVER load config directly)
- All external HTTP calls MUST go through this client
- Automatic retry with exponential backoff
- Timeout handling from config

Usage:
    config = RetryConfig(timeout=30.0, max_retries=3)
    client = RetryableHttpClient(config, api_name="instagram")
    result = await client.get("https://api.example.com/data")
"""

import logging
from typing import Any, Optional

import httpx

from teams.dawo.middleware.retry import RetryConfig, RetryResult, RetryMiddleware

logger = logging.getLogger(__name__)


class RetryableHttpClient:
    """HTTP client with automatic retry middleware.

    All external API calls should go through this client to ensure
    consistent retry behavior, timeout handling, and error logging.

    Attributes:
        _config: Retry configuration
        _api_name: Name of the API for logging context
        _httpx_client: Underlying httpx async client
        _middleware: RetryMiddleware instance
    """

    def __init__(self, config: RetryConfig, api_name: str) -> None:
        """Initialize HTTP client with injected config.

        Args:
            config: RetryConfig with timeout, retry settings
            api_name: API name for logging context (e.g., "instagram", "discord")
        """
        self._config = config
        self._api_name = api_name
        self._httpx_client = httpx.AsyncClient()
        self._middleware = RetryMiddleware(config)

    async def get(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> RetryResult:
        """Execute GET request with retry middleware.

        Args:
            url: Target URL
            headers: Optional request headers
            params: Optional query parameters

        Returns:
            RetryResult with response or error information
        """
        async def make_request() -> httpx.Response:
            response = await self._httpx_client.get(
                url,
                headers=headers,
                params=params,
                timeout=self._config.timeout,
            )
            # Check for error status codes (4xx/5xx)
            if response.status_code >= 400:
                request = getattr(response, "request", None) or httpx.Request("GET", url)
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=request,
                    response=response,
                )
            return response

        return await self._middleware.execute_with_retry(
            make_request,
            context=f"{self._api_name}_get",
        )

    async def post(
        self,
        url: str,
        *,
        json: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> RetryResult:
        """Execute POST request with retry middleware.

        Args:
            url: Target URL
            json: Optional JSON body
            data: Optional form data
            headers: Optional request headers

        Returns:
            RetryResult with response or error information
        """
        async def make_request() -> httpx.Response:
            response = await self._httpx_client.post(
                url,
                json=json,
                data=data,
                headers=headers,
                timeout=self._config.timeout,
            )
            # Check for error status codes (4xx/5xx)
            if response.status_code >= 400:
                request = getattr(response, "request", None) or httpx.Request("POST", url)
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=request,
                    response=response,
                )
            return response

        return await self._middleware.execute_with_retry(
            make_request,
            context=f"{self._api_name}_post",
        )

    async def put(
        self,
        url: str,
        *,
        json: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> RetryResult:
        """Execute PUT request with retry middleware.

        Args:
            url: Target URL
            json: Optional JSON body
            data: Optional form data
            headers: Optional request headers

        Returns:
            RetryResult with response or error information
        """
        async def make_request() -> httpx.Response:
            response = await self._httpx_client.put(
                url,
                json=json,
                data=data,
                headers=headers,
                timeout=self._config.timeout,
            )
            if response.status_code >= 400:
                request = getattr(response, "request", None) or httpx.Request("PUT", url)
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=request,
                    response=response,
                )
            return response

        return await self._middleware.execute_with_retry(
            make_request,
            context=f"{self._api_name}_put",
        )

    async def delete(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> RetryResult:
        """Execute DELETE request with retry middleware.

        Args:
            url: Target URL
            headers: Optional request headers
            params: Optional query parameters

        Returns:
            RetryResult with response or error information
        """
        async def make_request() -> httpx.Response:
            response = await self._httpx_client.delete(
                url,
                headers=headers,
                params=params,
                timeout=self._config.timeout,
            )
            if response.status_code >= 400:
                request = getattr(response, "request", None) or httpx.Request("DELETE", url)
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=request,
                    response=response,
                )
            return response

        return await self._middleware.execute_with_retry(
            make_request,
            context=f"{self._api_name}_delete",
        )

    async def patch(
        self,
        url: str,
        *,
        json: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> RetryResult:
        """Execute PATCH request with retry middleware.

        Args:
            url: Target URL
            json: Optional JSON body
            data: Optional form data
            headers: Optional request headers

        Returns:
            RetryResult with response or error information
        """
        async def make_request() -> httpx.Response:
            response = await self._httpx_client.patch(
                url,
                json=json,
                data=data,
                headers=headers,
                timeout=self._config.timeout,
            )
            if response.status_code >= 400:
                request = getattr(response, "request", None) or httpx.Request("PATCH", url)
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=request,
                    response=response,
                )
            return response

        return await self._middleware.execute_with_retry(
            make_request,
            context=f"{self._api_name}_patch",
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._httpx_client.aclose()

    async def __aenter__(self) -> "RetryableHttpClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - L2 fix: handle close errors."""
        try:
            await self.close()
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")
