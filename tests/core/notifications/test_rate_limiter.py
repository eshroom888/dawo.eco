"""Tests for NotificationRateLimiter.

Tests the rate limiting functionality including:
- Cooldown period enforcement
- Last notification timestamp tracking
- Pending notification queuing
- Redis state management

Test Coverage:
- AC #2: Rate limiting to max 1 per hour
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.notifications.rate_limiter import NotificationRateLimiter
from core.notifications.approval_notifier import QueueStatus


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock()
    mock.delete = AsyncMock()
    mock.lpush = AsyncMock()
    mock.expire = AsyncMock()
    mock.llen = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def rate_limiter(mock_redis: AsyncMock) -> NotificationRateLimiter:
    """Create rate limiter with mock Redis."""
    return NotificationRateLimiter(
        redis_client=mock_redis,
        cooldown_minutes=60,
    )


@pytest.fixture
def sample_queue_status() -> QueueStatus:
    """Create sample queue status for testing."""
    return QueueStatus(
        total_pending=10,
        by_source_type={"instagram_post": 7, "b2b_email": 3},
        by_priority={1: 2, 3: 5, 4: 3},
        compliance_warnings=1,
        highest_priority_item="test-id-123",
    )


class TestNotificationRateLimiter:
    """Tests for rate limiter functionality."""

    @pytest.mark.asyncio
    async def test_not_rate_limited_when_no_previous_notification(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify not rate limited when no previous notification exists."""
        # Arrange: No last notification in Redis
        mock_redis.get = AsyncMock(return_value=None)

        # Act
        result = await rate_limiter.is_rate_limited()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_rate_limited_within_cooldown(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify rate limited when within cooldown period."""
        # Arrange: Last notification was 30 minutes ago (within 60 min cooldown)
        last_sent = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
        mock_redis.get = AsyncMock(return_value=last_sent.encode())

        # Act
        result = await rate_limiter.is_rate_limited()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_not_rate_limited_after_cooldown(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify not rate limited when cooldown has expired."""
        # Arrange: Last notification was 90 minutes ago (outside 60 min cooldown)
        last_sent = (datetime.now(UTC) - timedelta(minutes=90)).isoformat()
        mock_redis.get = AsyncMock(return_value=last_sent.encode())

        # Act
        result = await rate_limiter.is_rate_limited()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_record_notification_sets_timestamp(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify record_notification sets timestamp in Redis."""
        # Act
        await rate_limiter.record_notification()

        # Assert: setex called with key, TTL, and timestamp
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "approval:notification:last_sent"
        # TTL should be cooldown + 60 seconds
        assert call_args[0][1] == 3660  # 60 min * 60 sec + 60 buffer

    @pytest.mark.asyncio
    async def test_record_notification_clears_pending(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify record_notification clears pending queue."""
        # Act
        await rate_limiter.record_notification()

        # Assert
        mock_redis.delete.assert_called_once_with("approval:notification:pending")

    @pytest.mark.asyncio
    async def test_queue_pending_notification(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
        sample_queue_status: QueueStatus,
    ) -> None:
        """Verify queue_pending_notification stores status."""
        # Act
        await rate_limiter.queue_pending_notification(sample_queue_status)

        # Assert
        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == "approval:notification:pending"

    @pytest.mark.asyncio
    async def test_queue_pending_sets_expiry(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
        sample_queue_status: QueueStatus,
    ) -> None:
        """Verify pending queue has 24-hour TTL."""
        # Act
        await rate_limiter.queue_pending_notification(sample_queue_status)

        # Assert: 24 hours = 86400 seconds
        mock_redis.expire.assert_called_once_with(
            "approval:notification:pending",
            86400,
        )

    @pytest.mark.asyncio
    async def test_get_time_until_available_none_when_not_limited(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify returns None when not rate limited."""
        # Arrange
        mock_redis.get = AsyncMock(return_value=None)

        # Act
        result = await rate_limiter.get_time_until_available()

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_time_until_available_returns_remaining(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify returns remaining cooldown time."""
        # Arrange: Last notification was 30 minutes ago
        last_sent = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
        mock_redis.get = AsyncMock(return_value=last_sent.encode())

        # Act
        result = await rate_limiter.get_time_until_available()

        # Assert: Should have ~30 minutes remaining
        assert result is not None
        assert 25 <= result.total_seconds() / 60 <= 35

    @pytest.mark.asyncio
    async def test_get_pending_count(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify get_pending_count returns queue length."""
        # Arrange
        mock_redis.llen = AsyncMock(return_value=5)

        # Act
        result = await rate_limiter.get_pending_count()

        # Assert
        assert result == 5

    @pytest.mark.asyncio
    async def test_redis_error_allows_notification(
        self,
        rate_limiter: NotificationRateLimiter,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify Redis errors don't block notifications."""
        # Arrange: Redis raises exception
        mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))

        # Act
        result = await rate_limiter.is_rate_limited()

        # Assert: Should allow notification on error
        assert result is False


class TestRateLimiterConfiguration:
    """Tests for rate limiter configuration."""

    @pytest.mark.asyncio
    async def test_custom_cooldown_period(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify custom cooldown period is respected."""
        # Arrange: 30-minute cooldown
        rate_limiter = NotificationRateLimiter(
            redis_client=mock_redis,
            cooldown_minutes=30,
        )

        # Last notification was 20 minutes ago (within 30 min cooldown)
        last_sent = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()
        mock_redis.get = AsyncMock(return_value=last_sent.encode())

        # Act
        result = await rate_limiter.is_rate_limited()

        # Assert: Should be rate limited
        assert result is True

    @pytest.mark.asyncio
    async def test_custom_cooldown_expired(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify custom cooldown expiry is respected."""
        # Arrange: 30-minute cooldown
        rate_limiter = NotificationRateLimiter(
            redis_client=mock_redis,
            cooldown_minutes=30,
        )

        # Last notification was 40 minutes ago (outside 30 min cooldown)
        last_sent = (datetime.now(UTC) - timedelta(minutes=40)).isoformat()
        mock_redis.get = AsyncMock(return_value=last_sent.encode())

        # Act
        result = await rate_limiter.is_rate_limited()

        # Assert: Should NOT be rate limited
        assert result is False
