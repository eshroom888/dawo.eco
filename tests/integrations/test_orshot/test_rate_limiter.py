"""Tests for Orshot rate limiter.

Tests the OrshotRateLimiter token bucket implementation per FR10.
"""

import pytest
import time
from unittest.mock import AsyncMock

from integrations.orshot import OrshotRateLimiter, RateLimitConfig


@pytest.fixture
def mock_redis():
    """Mock Redis client for rate limiter tests."""
    client = AsyncMock()
    client.get.return_value = None
    client.incr.return_value = 1
    client.expire.return_value = True
    client.set.return_value = True
    return client


@pytest.fixture
def rate_config():
    """Test rate limit configuration."""
    return RateLimitConfig(
        requests_per_minute=60,
        backoff_base=0.01,  # Fast for tests
        max_backoff=1.0,
        max_queue_size=10,
    )


@pytest.fixture
def rate_limiter(rate_config):
    """Create rate limiter without Redis (local mode)."""
    return OrshotRateLimiter(config=rate_config)


@pytest.fixture
def rate_limiter_with_redis(mock_redis, rate_config):
    """Create rate limiter with mock Redis."""
    return OrshotRateLimiter(redis_client=mock_redis, config=rate_config)


class TestRateLimiterInit:
    """Tests for rate limiter initialization."""

    def test_init_with_defaults(self):
        """Should initialize with default config."""
        limiter = OrshotRateLimiter()

        assert limiter._config.requests_per_minute == 60
        assert limiter._config.backoff_base == 1.0

    def test_init_with_custom_config(self, rate_config):
        """Should accept custom configuration."""
        limiter = OrshotRateLimiter(config=rate_config)

        assert limiter._config.requests_per_minute == 60
        assert limiter._config.backoff_base == 0.01

    def test_init_without_redis(self, rate_config):
        """Should work without Redis (local mode)."""
        limiter = OrshotRateLimiter(config=rate_config)

        assert limiter._redis is None

    def test_init_with_redis(self, mock_redis, rate_config):
        """Should accept Redis client."""
        limiter = OrshotRateLimiter(redis_client=mock_redis, config=rate_config)

        assert limiter._redis is mock_redis


class TestAcquire:
    """Tests for acquiring rate limit permission."""

    @pytest.mark.asyncio
    async def test_acquire_under_limit(self, rate_limiter):
        """Should acquire immediately under limit."""
        result = await rate_limiter.acquire(timeout=1.0)

        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_multiple_under_limit(self, rate_limiter):
        """Should allow multiple requests under limit."""
        for _ in range(10):
            result = await rate_limiter.acquire(timeout=1.0)
            assert result is True

    @pytest.mark.asyncio
    async def test_acquire_with_redis_under_limit(
        self, rate_limiter_with_redis, mock_redis
    ):
        """Should acquire using Redis when under limit."""
        mock_redis.get.return_value = b"10"

        result = await rate_limiter_with_redis.acquire(timeout=1.0)

        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_timeout_when_at_limit(self, rate_config):
        """Should timeout when at rate limit."""
        # Create limiter with very low limit
        config = RateLimitConfig(
            requests_per_minute=1,
            backoff_base=0.01,
            max_backoff=0.1,
        )
        limiter = OrshotRateLimiter(config=config)

        # First request should succeed
        await limiter.acquire(timeout=0.5)

        # Second request should timeout quickly
        result = await limiter.acquire(timeout=0.2)

        assert result is False

    @pytest.mark.asyncio
    async def test_acquire_respects_backoff(self, rate_limiter):
        """Should wait during backoff period."""
        # Set backoff
        rate_limiter._backoff_until = time.time() + 0.1

        start = time.time()
        await rate_limiter.acquire(timeout=1.0)
        elapsed = time.time() - start

        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_acquire_returns_false_when_backoff_exceeds_timeout(
        self, rate_limiter
    ):
        """Should return False if backoff exceeds timeout."""
        rate_limiter._backoff_until = time.time() + 10.0

        result = await rate_limiter.acquire(timeout=0.1)

        assert result is False


class TestRecordResponses:
    """Tests for recording API responses."""

    def test_record_429_increases_backoff(self, rate_limiter):
        """Should increase backoff on 429 response."""
        initial_backoff = rate_limiter._backoff_until

        rate_limiter.record_429_response()

        assert rate_limiter._backoff_until > initial_backoff
        assert rate_limiter._consecutive_429s == 1

    def test_record_429_exponential_backoff(self, rate_limiter):
        """Should use exponential backoff for consecutive 429s."""
        rate_limiter.record_429_response()
        first_backoff = rate_limiter._backoff_until

        rate_limiter.record_429_response()
        second_backoff = rate_limiter._backoff_until

        # Second backoff should be longer
        assert second_backoff > first_backoff
        assert rate_limiter._consecutive_429s == 2

    def test_record_429_with_retry_after(self):
        """Should use Retry-After header when provided."""
        # Use config with high max_backoff to not cap the retry_after value
        config = RateLimitConfig(max_backoff=60.0)
        limiter = OrshotRateLimiter(config=config)

        before = time.time()
        limiter.record_429_response(retry_after=5)

        expected_min = before + 4.9
        assert limiter._backoff_until >= expected_min

    def test_record_429_respects_max_backoff(self, rate_config):
        """Should cap backoff at max_backoff."""
        limiter = OrshotRateLimiter(config=rate_config)

        # Simulate many 429s
        for _ in range(20):
            limiter.record_429_response()

        # Backoff should not exceed max
        max_expected = time.time() + rate_config.max_backoff + 0.1
        assert limiter._backoff_until <= max_expected

    def test_record_success_resets_consecutive_429s(self, rate_limiter):
        """Should reset 429 counter on success."""
        rate_limiter._consecutive_429s = 5

        rate_limiter.record_success()

        assert rate_limiter._consecutive_429s == 0


class TestBackoffState:
    """Tests for backoff state properties."""

    def test_is_in_backoff_true(self, rate_limiter):
        """Should return True during backoff."""
        rate_limiter._backoff_until = time.time() + 10.0

        assert rate_limiter.is_in_backoff is True

    def test_is_in_backoff_false(self, rate_limiter):
        """Should return False when not in backoff."""
        rate_limiter._backoff_until = time.time() - 1.0

        assert rate_limiter.is_in_backoff is False

    def test_backoff_remaining(self, rate_limiter):
        """Should return remaining backoff time."""
        rate_limiter._backoff_until = time.time() + 5.0

        remaining = rate_limiter.backoff_remaining

        assert 4.9 <= remaining <= 5.1

    def test_backoff_remaining_zero_when_not_in_backoff(self, rate_limiter):
        """Should return 0 when not in backoff."""
        rate_limiter._backoff_until = time.time() - 1.0

        assert rate_limiter.backoff_remaining == 0


class TestGetCurrentUsage:
    """Tests for getting current usage stats."""

    @pytest.mark.asyncio
    async def test_get_current_usage_local(self, rate_limiter):
        """Should return local usage stats."""
        # Make some requests
        await rate_limiter.acquire(timeout=1.0)
        await rate_limiter.acquire(timeout=1.0)

        count, limit = await rate_limiter.get_current_usage()

        assert count == 2
        assert limit == 60

    @pytest.mark.asyncio
    async def test_get_current_usage_redis(
        self, rate_limiter_with_redis, mock_redis
    ):
        """Should return Redis usage stats."""
        mock_redis.get.return_value = b"25"

        count, limit = await rate_limiter_with_redis.get_current_usage()

        assert count == 25
        assert limit == 60

    @pytest.mark.asyncio
    async def test_get_current_usage_redis_error_fallback(
        self, rate_limiter_with_redis, mock_redis
    ):
        """Should fallback to local on Redis error."""
        mock_redis.get.side_effect = Exception("Redis error")

        count, limit = await rate_limiter_with_redis.get_current_usage()

        # Should return local stats (0 since no requests made)
        assert count == 0
        assert limit == 60


class TestMinuteKeyGeneration:
    """Tests for minute key generation."""

    def test_minute_key_format(self, rate_limiter):
        """Should generate key with timestamp format."""
        key = rate_limiter._get_minute_key()

        assert key.startswith("orshot:ratelimit:")
        # Key format: orshot:ratelimit:2026-02-07T12:30
        # Contains date with T separator for time
        assert "T" in key
        # Has YYYY-MM-DD format
        assert "-" in key


class TestLocalRateLimiting:
    """Tests for local (in-memory) rate limiting."""

    @pytest.mark.asyncio
    async def test_local_cleans_old_requests(self, rate_limiter):
        """Should clean requests older than 1 minute."""
        # Add some old requests
        rate_limiter._request_times = [time.time() - 120]  # 2 minutes ago

        can_request = rate_limiter._can_request_local()

        assert can_request is True
        assert len(rate_limiter._request_times) == 0

    def test_local_record_request(self, rate_limiter):
        """Should record request time."""
        initial_count = len(rate_limiter._request_times)

        rate_limiter._record_request_local()

        assert len(rate_limiter._request_times) == initial_count + 1


class TestRedisRateLimiting:
    """Tests for Redis-based rate limiting."""

    @pytest.mark.asyncio
    async def test_redis_can_request(self, rate_limiter_with_redis, mock_redis):
        """Should check Redis for rate limit."""
        mock_redis.get.return_value = b"30"

        can_request = await rate_limiter_with_redis._can_request_redis()

        assert can_request is True
        mock_redis.get.assert_called()

    @pytest.mark.asyncio
    async def test_redis_can_request_at_limit(
        self, rate_limiter_with_redis, mock_redis
    ):
        """Should deny when at Redis limit."""
        mock_redis.get.return_value = b"60"

        can_request = await rate_limiter_with_redis._can_request_redis()

        assert can_request is False

    @pytest.mark.asyncio
    async def test_redis_record_sets_expiry(
        self, rate_limiter_with_redis, mock_redis
    ):
        """Should set expiry on first request in minute."""
        mock_redis.incr.return_value = 1

        await rate_limiter_with_redis._record_request_redis()

        mock_redis.expire.assert_called()

    @pytest.mark.asyncio
    async def test_redis_error_fallback(
        self, rate_limiter_with_redis, mock_redis
    ):
        """Should fallback to local on Redis error."""
        mock_redis.get.side_effect = Exception("Redis connection failed")

        # Should not raise, should use local
        can_request = await rate_limiter_with_redis._can_request()

        assert can_request is True  # Local allows (no requests yet)
