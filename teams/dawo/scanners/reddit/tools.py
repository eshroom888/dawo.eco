"""Reddit API client and tools for the Reddit Research Scanner.

Provides authenticated access to Reddit's OAuth2 API with:
    - OAuth2 "script" type authentication
    - Subreddit search functionality
    - Post detail retrieval
    - Built-in rate limiting (60 requests/minute)
    - Retry middleware integration

ALL API calls go through retry middleware - NEVER make direct calls.

Usage:
    config = RedditClientConfig(...)
    retry = RetryMiddleware(RetryConfig())
    client = RedditClient(config, retry)

    posts = await client.search_subreddit("Nootropics", "lion's mane")
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Any

import httpx

from teams.dawo.middleware.retry import RetryMiddleware, RetryResult

from .config import RedditClientConfig


# Module logger
logger = logging.getLogger(__name__)

# Reddit API endpoints
REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE = "https://oauth.reddit.com"

# Rate limiting constants
DEFAULT_RATE_LIMIT = 60  # requests per minute
RATE_LIMIT_WINDOW = 60.0  # seconds


class RedditAPIError(Exception):
    """Exception raised for Reddit API errors.

    Attributes:
        message: Error description
        status_code: HTTP status code (if available)
        response_body: Raw response body (if available)
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class RedditAuthError(RedditAPIError):
    """Exception raised for authentication failures."""

    pass


class RedditRateLimitError(RedditAPIError):
    """Exception raised when rate limit is exceeded."""

    pass


class RedditClient:
    """Reddit API client with OAuth2 authentication.

    Accepts credentials via dependency injection - NEVER loads from file.
    All API calls go through retry middleware for resilience.

    Features:
        - OAuth2 "script" type authentication
        - Automatic token refresh
        - Rate limiting (60 requests/minute)
        - Retry middleware integration

    Attributes:
        _config: Reddit API credentials
        _retry: Retry middleware for resilient API calls
        _client: HTTPX async client
        _access_token: Current OAuth2 access token
        _token_expires: Token expiration timestamp
        _request_timestamps: Recent request times for rate limiting
    """

    def __init__(
        self,
        config: RedditClientConfig,
        retry_middleware: RetryMiddleware,
    ):
        """Initialize Reddit client with injected dependencies.

        Args:
            config: Reddit API credentials (from environment)
            retry_middleware: Retry middleware for API calls
        """
        self._config = config
        self._retry = retry_middleware
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._request_timestamps: list[float] = []
        self._rate_limit = DEFAULT_RATE_LIMIT

    async def __aenter__(self) -> "RedditClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token.

        Refreshes token if expired or not yet obtained.

        Raises:
            RedditAuthError: If authentication fails
        """
        now = datetime.now(timezone.utc)

        # Check if token is still valid (with 60s buffer)
        if (
            self._access_token
            and self._token_expires
            and self._token_expires > now.timestamp() + 60
        ):
            return

        logger.debug("Authenticating with Reddit API")

        try:
            auth = httpx.BasicAuth(
                self._config.client_id,
                self._config.client_secret,
            )
            data = {
                "grant_type": "password",
                "username": self._config.username,
                "password": self._config.password,
            }
            headers = {"User-Agent": self._config.user_agent}

            if not self._client:
                raise RedditAuthError("Client not initialized - use async context manager")

            response = await self._client.post(
                REDDIT_AUTH_URL,
                auth=auth,
                data=data,
                headers=headers,
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Reddit auth error: {error_msg}")
                raise RedditAuthError(f"Authentication failed: {error_msg}")

            self._access_token = result["access_token"]
            expires_in = result.get("expires_in", 3600)
            self._token_expires = now.timestamp() + expires_in

            logger.info("Reddit authentication successful, token expires in %ds", expires_in)

        except httpx.HTTPStatusError as e:
            logger.error(f"Reddit auth HTTP error: {e.response.status_code}")
            raise RedditAuthError(
                f"Authentication failed: HTTP {e.response.status_code}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Reddit auth request error: {e}")
            raise RedditAuthError(f"Authentication failed: {e}") from e

    async def _rate_limit_wait(self) -> None:
        """Wait if necessary to respect rate limits.

        Implements sliding window rate limiting (60 requests/minute).

        Note: Uses asyncio event loop time (monotonic) rather than wall clock time.
        Monotonic time is preferred for rate limiting because:
        - It's immune to system clock adjustments
        - It provides consistent intervals for API compliance
        - asyncio.sleep() uses the same time source for accuracy
        """
        # Use monotonic time for rate limiting - immune to clock drift/adjustments
        now = asyncio.get_event_loop().time()
        cutoff = now - RATE_LIMIT_WINDOW

        # Remove old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > cutoff
        ]

        # If at limit, wait until oldest request falls out of window
        if len(self._request_timestamps) >= self._rate_limit:
            oldest = self._request_timestamps[0]
            wait_time = oldest + RATE_LIMIT_WINDOW - now
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

        # Record this request
        self._request_timestamps.append(now)

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Make authenticated API request with retry.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (without base URL)
            params: Query parameters

        Returns:
            JSON response as dict

        Raises:
            RedditAPIError: If request fails after retries
        """
        await self._ensure_authenticated()
        await self._rate_limit_wait()

        if not self._client:
            raise RedditAPIError("Client not initialized - use async context manager")

        url = f"{REDDIT_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": self._config.user_agent,
        }

        async def make_request() -> dict:
            response = await self._client.request(
                method,
                url,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

        result: RetryResult = await self._retry.execute_with_retry(
            make_request,
            context=f"reddit_{endpoint}",
        )

        if not result.success:
            if result.is_incomplete:
                logger.error(f"Reddit API call incomplete after retries: {result.last_error}")
                raise RedditAPIError(
                    f"API call failed after retries: {result.last_error}",
                )
            else:
                logger.error(f"Reddit API call failed: {result.last_error}")
                raise RedditAPIError(f"API call failed: {result.last_error}")

        return result.response

    async def search_subreddit(
        self,
        subreddit: str,
        query: str,
        time_filter: str = "day",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search subreddit for posts matching query.

        Args:
            subreddit: Subreddit name (without r/)
            query: Search keywords
            time_filter: "hour", "day", "week", "month", "year", "all"
            limit: Max results (Reddit caps at 100)

        Returns:
            List of post data dicts from Reddit API

        Raises:
            RedditAPIError: If search fails
        """
        logger.debug(
            f"Searching r/{subreddit} for '{query}' (time={time_filter}, limit={limit})"
        )

        params = {
            "q": query,
            "restrict_sr": "true",
            "sort": "hot",
            "t": time_filter,
            "limit": min(limit, 100),  # Reddit caps at 100
        }

        response = await self._api_request(
            "GET",
            f"/r/{subreddit}/search",
            params=params,
        )

        # Extract posts from Reddit API response format
        children = response.get("data", {}).get("children", [])
        posts = [child.get("data", {}) for child in children]

        logger.debug(f"Search returned {len(posts)} posts from r/{subreddit}")
        return posts

    async def get_post_details(self, post_id: str) -> dict[str, Any]:
        """Get full details for a specific post.

        Args:
            post_id: Reddit post ID (e.g., "abc123")

        Returns:
            Post data dict with full details

        Raises:
            RedditAPIError: If request fails
        """
        logger.debug(f"Fetching details for post {post_id}")

        # Reddit API returns [post_listing, comments_listing]
        response = await self._api_request(
            "GET",
            f"/comments/{post_id}",
            params={"limit": 0},  # Don't need comments
        )

        # First element is the post listing
        if isinstance(response, list) and len(response) > 0:
            children = response[0].get("data", {}).get("children", [])
            if children:
                return children[0].get("data", {})

        logger.warning(f"No details found for post {post_id}")
        return {}
