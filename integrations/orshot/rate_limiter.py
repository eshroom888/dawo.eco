"""Rate limiter for Orshot API requests.

Implements token bucket rate limiting to respect Orshot API limits.
Default: 60 requests/minute (assumed based on typical API limits).

Architecture Compliance:
- Redis client injected via constructor
- Async-first design
- Graceful degradation on Redis failures
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class RedisClientProtocol(Protocol):
    """Protocol for Redis client interface."""

    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        ...

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key value with optional expiration."""
        ...

    async def incr(self, key: str) -> int:
        """Increment key value."""
        ...

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration."""
        ...


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        requests_per_minute: Maximum requests per minute
        backoff_base: Base backoff time in seconds for 429 responses
        max_backoff: Maximum backoff time in seconds
        max_queue_size: Maximum pending requests before rejecting
    """

    requests_per_minute: int = 60
    backoff_base: float = 1.0
    max_backoff: float = 60.0
    max_queue_size: int = 100


class OrshotRateLimiter:
    """Token bucket rate limiter for Orshot API.

    Uses Redis for distributed rate limiting across instances.
    Implements exponential backoff for 429 responses.

    Attributes:
        KEY_PREFIX: Redis key prefix for rate limit tracking
    """

    KEY_PREFIX = "orshot:ratelimit"

    def __init__(
        self,
        redis_client: Optional[RedisClientProtocol] = None,
        config: Optional[RateLimitConfig] = None,
    ) -> None:
        """Initialize rate limiter.

        Args:
            redis_client: Optional Redis client for distributed limiting.
                         If None, uses in-memory tracking (single instance only).
            config: Rate limit configuration
        """
        self._redis = redis_client
        self._config = config or RateLimitConfig()

        # In-memory tracking (fallback if no Redis)
        self._request_times: list[float] = []
        self._queue: asyncio.Queue[asyncio.Future[None]] = asyncio.Queue(
            maxsize=self._config.max_queue_size
        )
        self._processing = False
        self._backoff_until: float = 0
        self._consecutive_429s: int = 0

    def _get_minute_key(self) -> str:
        """Get Redis key for current minute.

        Returns:
            Key in format: orshot:ratelimit:2026-02-07T12:30
        """
        # Truncate to minute
        timestamp = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
        return f"{self.KEY_PREFIX}:{timestamp}"

    async def acquire(self, timeout: float = 30.0) -> bool:
        """Acquire permission to make a request.

        Waits if rate limited, respects backoff from 429 responses.

        Args:
            timeout: Maximum seconds to wait for permission

        Returns:
            True if permission granted, False if timed out or rejected

        Raises:
            asyncio.TimeoutError: If wait exceeds timeout
        """
        start_time = time.time()

        # Check if in backoff period
        if time.time() < self._backoff_until:
            wait_time = self._backoff_until - time.time()
            if wait_time > timeout:
                logger.warning("Rate limit backoff exceeds timeout")
                return False

            logger.debug("Waiting %.1fs for backoff to complete", wait_time)
            await asyncio.sleep(wait_time)

        # Check rate limit
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning("Rate limit acquire timed out")
                return False

            if await self._can_request():
                await self._record_request()
                return True

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    async def _can_request(self) -> bool:
        """Check if a request is allowed under rate limit.

        Returns:
            True if under limit
        """
        if self._redis:
            return await self._can_request_redis()
        return self._can_request_local()

    async def _can_request_redis(self) -> bool:
        """Check rate limit using Redis (distributed).

        Returns:
            True if under limit
        """
        try:
            key = self._get_minute_key()
            count_bytes = await self._redis.get(key)
            count = int(count_bytes) if count_bytes else 0
            return count < self._config.requests_per_minute
        except Exception as e:
            logger.warning("Redis rate limit check failed, using local: %s", e)
            return self._can_request_local()

    def _can_request_local(self) -> bool:
        """Check rate limit using local memory.

        Returns:
            True if under limit
        """
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        self._request_times = [t for t in self._request_times if t > minute_ago]

        return len(self._request_times) < self._config.requests_per_minute

    async def _record_request(self) -> None:
        """Record a request for rate limiting."""
        if self._redis:
            await self._record_request_redis()
        else:
            self._record_request_local()

    async def _record_request_redis(self) -> None:
        """Record request in Redis."""
        try:
            key = self._get_minute_key()
            count = await self._redis.incr(key)
            if count == 1:
                # Set expiry on first request in this minute
                await self._redis.expire(key, 120)  # 2 minutes to handle edge cases
        except Exception as e:
            logger.warning("Redis rate limit record failed: %s", e)
            self._record_request_local()

    def _record_request_local(self) -> None:
        """Record request in local memory."""
        self._request_times.append(time.time())

    def record_429_response(self, retry_after: Optional[int] = None) -> None:
        """Record a 429 rate limit response.

        Calculates exponential backoff for future requests.

        Args:
            retry_after: Retry-After header value in seconds, if provided
        """
        self._consecutive_429s += 1

        if retry_after:
            # Use server-provided value
            backoff = min(retry_after, self._config.max_backoff)
        else:
            # Calculate exponential backoff
            backoff = self._config.backoff_base * (2 ** (self._consecutive_429s - 1))
            backoff = min(backoff, self._config.max_backoff)

        self._backoff_until = time.time() + backoff

        logger.warning(
            "Rate limit 429 received (consecutive: %d). Backing off for %.1fs",
            self._consecutive_429s,
            backoff,
        )

    def record_success(self) -> None:
        """Record a successful request.

        Resets consecutive 429 counter.
        """
        if self._consecutive_429s > 0:
            logger.debug("Rate limit recovered after %d consecutive 429s", self._consecutive_429s)
        self._consecutive_429s = 0

    async def get_current_usage(self) -> tuple[int, int]:
        """Get current rate limit usage.

        Returns:
            Tuple of (current_count, limit)
        """
        if self._redis:
            try:
                key = self._get_minute_key()
                count_bytes = await self._redis.get(key)
                count = int(count_bytes) if count_bytes else 0
                return count, self._config.requests_per_minute
            except Exception as e:
                logger.warning("Failed to get Redis rate limit usage: %s", e)

        # Fallback to local
        now = time.time()
        minute_ago = now - 60
        self._request_times = [t for t in self._request_times if t > minute_ago]
        return len(self._request_times), self._config.requests_per_minute

    @property
    def is_in_backoff(self) -> bool:
        """Check if currently in backoff period.

        Returns:
            True if in backoff
        """
        return time.time() < self._backoff_until

    @property
    def backoff_remaining(self) -> float:
        """Get remaining backoff time in seconds.

        Returns:
            Seconds remaining, 0 if not in backoff
        """
        return max(0, self._backoff_until - time.time())
