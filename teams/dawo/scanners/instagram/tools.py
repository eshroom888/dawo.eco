"""Instagram API clients and tools for the Instagram Trend Scanner.

Provides access to Instagram Graph API with:
    - InstagramClient: Instagram Graph API client
    - RateLimitTracker: Hourly rate limit management

ALL API calls go through retry middleware - NEVER make direct calls.

CRITICAL: Instagram Graph API Limitations:
    - Hashtag Search requires Business Discovery or approved use case
    - Cannot access personal accounts (only Business/Creator)
    - Cannot download/store media (only metadata and text)
    - Must comply with Meta Platform Terms of Service

Usage:
    config = InstagramClientConfig(access_token="...", business_account_id="...")
    retry = RetryMiddleware(RetryConfig())
    client = InstagramClient(config, retry)

    posts = await client.search_hashtag("lionsmane", limit=25)
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Protocol, runtime_checkable

from .config import (
    InstagramClientConfig,
    INSTAGRAM_RATE_LIMIT_PER_HOUR,
    INSTAGRAM_MAX_RESULTS_PER_CALL,
)


# Module logger
logger = logging.getLogger(__name__)

# Instagram Graph API base URL
INSTAGRAM_API_BASE = "https://graph.facebook.com/v19.0"


@runtime_checkable
class RetryResultProtocol(Protocol):
    """Protocol for retry middleware result."""

    @property
    def success(self) -> bool:
        """Whether the operation succeeded."""
        ...

    @property
    def response(self) -> dict:
        """The response data if successful."""
        ...

    @property
    def last_error(self) -> Optional[str]:
        """The last error message if failed."""
        ...


@runtime_checkable
class RetryMiddlewareProtocol(Protocol):
    """Protocol for retry middleware dependency.

    Defines the interface required by InstagramClient.
    Allows for type-safe dependency injection.
    """

    async def execute_with_retry(
        self,
        func,
        context: Optional[str] = None,
    ) -> RetryResultProtocol:
        """Execute function with retry logic."""
        ...


class InstagramAPIError(Exception):
    """Exception raised for Instagram API errors.

    Attributes:
        message: Error description
        status_code: HTTP status code (if available)
        error_code: Instagram error code (if available)
        response_body: Raw response body (if available)
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.response_body = response_body


class RateLimitError(InstagramAPIError):
    """Exception raised when Instagram rate limit is exceeded."""

    pass


class InstagramScanError(Exception):
    """Exception raised for scanner-level errors.

    Attributes:
        message: Error description
        partial_results: Any posts collected before error
    """

    def __init__(
        self,
        message: str,
        partial_results: Optional[list] = None,
    ):
        super().__init__(message)
        self.message = message
        self.partial_results = partial_results or []


class RateLimitTracker:
    """Track Instagram API rate limit usage.

    Instagram Business accounts have a limit of 200 calls per hour.
    This class tracks usage and prevents exceeding the limit.

    Attributes:
        _calls_this_hour: Calls made in current hour
        _hour_start: Start of current tracking hour
    """

    HOURLY_LIMIT = INSTAGRAM_RATE_LIMIT_PER_HOUR

    def __init__(self) -> None:
        """Initialize rate limit tracker."""
        self._calls_this_hour = 0
        self._hour_start = datetime.now(timezone.utc)

    def check_and_use(self, calls: int = 1) -> None:
        """Check if rate limit available and consume it.

        Args:
            calls: Number of API calls to consume

        Raises:
            RateLimitError: If operation would exceed hourly limit
        """
        self._maybe_reset()

        if self._calls_this_hour + calls > self.HOURLY_LIMIT:
            raise RateLimitError(
                f"Would exceed hourly rate limit: {self._calls_this_hour + calls} > {self.HOURLY_LIMIT}",
            )

        self._calls_this_hour += calls
        logger.debug(f"Rate limit used: {self._calls_this_hour}/{self.HOURLY_LIMIT}")

    def get_remaining(self) -> int:
        """Get remaining API calls for this hour."""
        self._maybe_reset()
        return self.HOURLY_LIMIT - self._calls_this_hour

    def get_reset_time(self) -> datetime:
        """Get timestamp when rate limit resets."""
        return self._hour_start + timedelta(hours=1)

    def _maybe_reset(self) -> None:
        """Reset counter if new hour has started."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self._hour_start).total_seconds()

        if elapsed >= 3600:  # 1 hour in seconds
            logger.info(f"Rate limit reset: new hour started")
            self._calls_this_hour = 0
            self._hour_start = now


class InstagramClient:
    """Instagram Graph API client.

    Accepts access token via dependency injection - NEVER loads from file.
    CRITICAL: Requires Business/Creator account permissions.

    All API calls go through retry middleware for resilience.

    Features:
        - Hashtag search via Hashtag Search API
        - Competitor account media retrieval via Business Discovery
        - Rate limit tracking and management
        - Retry middleware integration

    Attributes:
        _config: Instagram API credentials
        _retry: Retry middleware for API calls
        _rate_limit: Rate limit tracking instance
        _session: HTTPX async client
    """

    BASE_URL = INSTAGRAM_API_BASE
    MAX_RESULTS = INSTAGRAM_MAX_RESULTS_PER_CALL

    def __init__(
        self,
        config: InstagramClientConfig,
        retry_middleware: RetryMiddlewareProtocol,
        rate_limit_tracker: Optional[RateLimitTracker] = None,
    ):
        """Initialize Instagram client with injected dependencies.

        Args:
            config: Instagram API credentials (from environment)
            retry_middleware: Retry middleware for API calls (Story 1.5)
            rate_limit_tracker: Optional shared rate limit tracker
        """
        self._config = config
        self._retry = retry_middleware
        self._rate_limit = rate_limit_tracker or RateLimitTracker()
        # httpx.AsyncClient - imported at runtime to avoid hard dependency
        self._session = None

    async def __aenter__(self) -> "InstagramClient":
        """Async context manager entry."""
        import httpx
        self._session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.aclose()
            self._session = None

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is available."""
        if not self._session:
            import httpx
            self._session = httpx.AsyncClient(timeout=30.0)

    async def _api_call(self, url: str, params: dict) -> dict:
        """Make an API call with retry middleware.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            InstagramAPIError: If API call fails after retries
        """
        await self._ensure_session()

        async def make_request() -> dict:
            response = await self._session.get(url, params=params)

            # Check for rate limit errors
            if response.status_code == 429:
                raise RateLimitError(
                    "Instagram API rate limit exceeded",
                    status_code=429,
                )

            # Check for other errors
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                raise InstagramAPIError(
                    f"Instagram API error: {error_msg}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            return response.json()

        result = await self._retry.execute_with_retry(
            make_request,
            context=f"instagram_api_{url.split('/')[-1][:20]}",
        )

        if not result.success:
            logger.error(f"Instagram API failed: {result.last_error}")
            raise InstagramAPIError(f"API call failed after retries: {result.last_error}")

        return result.response

    async def search_hashtag(
        self,
        hashtag: str,
        limit: int = 25,
    ) -> list[dict]:
        """Search for recent media with hashtag.

        Uses Instagram Hashtag Search API to find posts.
        Requires Business/Creator account with proper permissions.

        Args:
            hashtag: Hashtag without # (e.g., "lionsmane")
            limit: Max results (Instagram caps at 30)

        Returns:
            List of media objects with caption, metrics

        Raises:
            RateLimitError: If hourly limit exceeded
            InstagramAPIError: If search fails
        """
        logger.debug(f"Searching Instagram for hashtag '{hashtag}' (limit={limit})")

        # Check rate limit (2 calls: hashtag lookup + media fetch)
        self._rate_limit.check_and_use(2)

        # Step 1: Get hashtag ID
        hashtag_url = f"{self.BASE_URL}/ig_hashtag_search"
        hashtag_params = {
            "user_id": self._config.business_account_id,
            "q": hashtag.lower().strip("#"),
            "access_token": self._config.access_token,
        }

        hashtag_data = await self._api_call(hashtag_url, hashtag_params)

        if not hashtag_data.get("data"):
            logger.warning(f"No hashtag found for '{hashtag}'")
            return []

        hashtag_id = hashtag_data["data"][0]["id"]

        # Step 2: Get recent media for hashtag
        media_url = f"{self.BASE_URL}/{hashtag_id}/recent_media"
        media_params = {
            "user_id": self._config.business_account_id,
            "fields": "id,caption,permalink,timestamp,like_count,comments_count,media_type",
            "limit": min(limit, self.MAX_RESULTS),
            "access_token": self._config.access_token,
        }

        media_data = await self._api_call(media_url, media_params)
        items = media_data.get("data", [])

        logger.debug(f"Hashtag search returned {len(items)} posts for '{hashtag}'")
        return items

    async def get_user_media(
        self,
        username: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get recent media from a business/creator account.

        Uses Business Discovery to access other business accounts.
        Only works for public Business/Creator accounts.

        Args:
            username: Instagram username (without @)
            limit: Max posts to retrieve

        Returns:
            List of media objects with caption, metrics

        Raises:
            RateLimitError: If hourly limit exceeded
            InstagramAPIError: If request fails
        """
        logger.debug(f"Getting media for user '@{username}' (limit={limit})")

        # Check rate limit
        self._rate_limit.check_and_use(1)

        url = f"{self.BASE_URL}/{self._config.business_account_id}"
        params = {
            "fields": f"business_discovery.username({username}){{media.limit({min(limit, self.MAX_RESULTS)}){{id,caption,permalink,timestamp,like_count,comments_count,media_type}}}}",
            "access_token": self._config.access_token,
        }

        data = await self._api_call(url, params)

        # Extract media from nested structure
        business_discovery = data.get("business_discovery", {})
        media = business_discovery.get("media", {})
        items = media.get("data", [])

        logger.debug(f"User media returned {len(items)} posts for '@{username}'")
        return items

    async def get_media_details(
        self,
        media_id: str,
    ) -> dict:
        """Get detailed information for a specific media item.

        Args:
            media_id: Instagram media ID

        Returns:
            Dict with full media details

        Raises:
            RateLimitError: If hourly limit exceeded
            InstagramAPIError: If request fails
        """
        logger.debug(f"Getting details for media {media_id}")

        # Check rate limit
        self._rate_limit.check_and_use(1)

        url = f"{self.BASE_URL}/{media_id}"
        params = {
            "fields": "id,caption,permalink,timestamp,like_count,comments_count,media_type,username",
            "access_token": self._config.access_token,
        }

        return await self._api_call(url, params)

    @property
    def rate_limit_remaining(self) -> int:
        """Get remaining API calls for this hour."""
        return self._rate_limit.get_remaining()

    @property
    def rate_limit_reset(self) -> datetime:
        """Get timestamp when rate limit resets."""
        return self._rate_limit.get_reset_time()


def extract_hashtags(caption: str) -> list[str]:
    """Extract hashtags from caption text.

    Args:
        caption: Instagram caption text

    Returns:
        List of hashtags (without #)
    """
    if not caption:
        return []

    # Match hashtags - word characters after #
    pattern = r"#(\w+)"
    matches = re.findall(pattern, caption.lower())

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for tag in matches:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)

    return unique
