"""Hunter.io API client for B2B Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Provides async HTTP client for Hunter.io API with:
- Domain search (find emails at a company)
- Email finder (find specific person's email)
- Email verification
- Rate limiting and retry support
"""

import asyncio
import logging
from datetime import datetime, UTC
from time import monotonic
from typing import Any, Optional, Protocol

import aiohttp

from teams.dawo.leads.scanner.config import HunterClientConfig


logger = logging.getLogger(__name__)


# API response constants
HUNTER_SUCCESS_STATUS = 200
HUNTER_RATE_LIMIT_STATUS = 429
HUNTER_NOT_FOUND_STATUS = 404


class RetryMiddlewareProtocol(Protocol):
    """Protocol for retry middleware integration."""

    async def execute_with_retry(
        self,
        operation: str,
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry logic."""
        ...


class HunterAPIError(Exception):
    """Base exception for Hunter.io API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class HunterRateLimitError(HunterAPIError):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__("Rate limit exceeded", status_code=HUNTER_RATE_LIMIT_STATUS)
        self.retry_after = retry_after


class HunterClient:
    """Hunter.io API client with rate limiting.

    Accepts configuration via dependency injection.
    NEVER loads credentials from files directly.

    Attributes:
        _config: API configuration
        _session: aiohttp session (created on first use)
        _retry_middleware: Optional retry middleware for resilience
        _last_request_time: Timestamp of last request (for rate limiting)
        _min_request_interval: Minimum seconds between requests
    """

    def __init__(
        self,
        config: HunterClientConfig,
        retry_middleware: Optional[RetryMiddlewareProtocol] = None,
    ) -> None:
        """Initialize Hunter.io client.

        Args:
            config: API configuration with credentials
            retry_middleware: Optional retry middleware for resilience
        """
        self._config = config
        self._retry_middleware = retry_middleware
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: float = 0.0
        self._min_request_interval = 60.0 / config.rate_limit_per_minute

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _rate_limit_wait(self) -> None:
        """Wait if needed to respect rate limits.

        Uses monotonic time for accurate interval calculation
        regardless of system clock changes.
        """
        now = monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            wait_time = self._min_request_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self._last_request_time = monotonic()

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make API request with rate limiting.

        Args:
            endpoint: API endpoint (e.g., "domain-search")
            params: Query parameters

        Returns:
            API response data

        Raises:
            HunterAPIError: On API error
            HunterRateLimitError: On rate limit exceeded
        """
        await self._rate_limit_wait()

        session = await self._get_session()
        url = f"{self._config.base_url}/{endpoint}"

        # Add API key to params
        request_params = params or {}
        request_params["api_key"] = self._config.api_key

        try:
            async with session.get(url, params=request_params) as response:
                data = await response.json()

                if response.status == HUNTER_RATE_LIMIT_STATUS:
                    retry_after = response.headers.get("Retry-After")
                    raise HunterRateLimitError(
                        retry_after=int(retry_after) if retry_after else None
                    )

                if response.status != HUNTER_SUCCESS_STATUS:
                    error_msg = data.get("errors", [{}])[0].get(
                        "details", f"HTTP {response.status}"
                    )
                    raise HunterAPIError(error_msg, status_code=response.status)

                return data.get("data", {})

        except aiohttp.ClientError as e:
            logger.error(f"Hunter.io API request failed: {e}")
            raise HunterAPIError(f"Request failed: {e}") from e

    async def domain_search(
        self,
        domain: str,
        department: Optional[str] = None,
        seniority: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search for emails at a domain.

        Args:
            domain: Company domain (e.g., "example.com")
            department: Filter by department (e.g., "management")
            seniority: Filter by seniority (e.g., "senior")
            limit: Maximum results (default 10)

        Returns:
            Dict with domain info and emails:
            {
                "domain": "example.com",
                "company": "Example Inc",
                "organization": "Example Inc",
                "country": "Norway",
                "emails": [
                    {
                        "value": "john@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "position": "CEO",
                        "confidence": 95,
                        ...
                    }
                ],
                ...
            }

        Raises:
            HunterAPIError: On API error
        """
        params: dict[str, Any] = {
            "domain": domain,
            "limit": limit,
        }
        if department:
            params["department"] = department
        if seniority:
            params["seniority"] = seniority

        logger.debug(f"Domain search: {domain}")

        if self._retry_middleware:
            return await self._retry_middleware.execute_with_retry(
                f"hunter_domain_search:{domain}",
                self._make_request,
                "domain-search",
                params,
            )
        return await self._make_request("domain-search", params)

    async def email_finder(
        self,
        domain: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Find email for a specific person at a company.

        Args:
            domain: Company domain
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (alternative to first/last)

        Returns:
            Dict with email data:
            {
                "email": "john.doe@example.com",
                "score": 95,
                "position": "CEO",
                ...
            }

        Raises:
            HunterAPIError: On API error
        """
        params: dict[str, Any] = {"domain": domain}

        if full_name:
            params["full_name"] = full_name
        else:
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name

        logger.debug(f"Email finder: {domain} - {first_name} {last_name}")

        if self._retry_middleware:
            return await self._retry_middleware.execute_with_retry(
                f"hunter_email_finder:{domain}",
                self._make_request,
                "email-finder",
                params,
            )
        return await self._make_request("email-finder", params)

    async def email_verifier(self, email: str) -> dict[str, Any]:
        """Verify if an email address is deliverable.

        Args:
            email: Email address to verify

        Returns:
            Dict with verification status:
            {
                "status": "valid|invalid|accept_all|webmail|disposable|unknown",
                "result": "deliverable|undeliverable|risky|unknown",
                "score": 95,
                ...
            }

        Raises:
            HunterAPIError: On API error
        """
        params = {"email": email}

        logger.debug(f"Email verifier: {email}")

        if self._retry_middleware:
            return await self._retry_middleware.execute_with_retry(
                f"hunter_email_verifier:{email}",
                self._make_request,
                "email-verifier",
                params,
            )
        return await self._make_request("email-verifier", params)

    async def account_info(self) -> dict[str, Any]:
        """Get account information and remaining credits.

        Returns:
            Dict with account info:
            {
                "email": "user@company.com",
                "plan_name": "Starter",
                "requests": {
                    "searches": {"used": 50, "available": 500},
                    "verifications": {"used": 10, "available": 100}
                }
            }

        Raises:
            HunterAPIError: On API error
        """
        # Account endpoint doesn't need retry - it's for diagnostics
        return await self._make_request("account")

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "HunterClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
