"""Tests for NotificationQueue.

Tests the notification retry queue including:
- Failed notification queuing
- Exponential backoff retry logic
- Max retry attempts
- Abandoned notification handling

Test Coverage:
- AC #4: Retry failed notifications with exponential backoff
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
import json

import pytest

from core.notifications.queue import (
    NotificationQueue,
    QueuedNotification,
    NotificationStatus,
)
from core.notifications.approval_notifier import QueueStatus


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.lpush = AsyncMock()
    mock.lrange = AsyncMock(return_value=[])
    mock.llen = AsyncMock(return_value=0)
    mock.delete = AsyncMock()
    mock.lrem = AsyncMock()
    mock.setex = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.expire = AsyncMock()
    return mock


@pytest.fixture
def mock_discord_client() -> AsyncMock:
    """Create mock Discord client."""
    mock = AsyncMock()
    mock.send_approval_notification = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def notification_queue(
    mock_redis: AsyncMock,
    mock_discord_client: AsyncMock,
) -> NotificationQueue:
    """Create notification queue with mock dependencies."""
    return NotificationQueue(
        redis_client=mock_redis,
        discord_client=mock_discord_client,
        dashboard_url="http://localhost:3000/approval",
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


class TestNotificationQueue:
    """Tests for notification queue functionality."""

    @pytest.mark.asyncio
    async def test_queue_failed_notification(
        self,
        notification_queue: NotificationQueue,
        mock_redis: AsyncMock,
        sample_queue_status: QueueStatus,
    ) -> None:
        """Verify failed notifications are queued."""
        # Act
        await notification_queue.queue_failed(sample_queue_status)

        # Assert
        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == "approval:notification:failed"

    @pytest.mark.asyncio
    async def test_get_failed_count(
        self,
        notification_queue: NotificationQueue,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify failed count returns queue length."""
        # Arrange
        mock_redis.llen = AsyncMock(return_value=5)

        # Act
        result = await notification_queue.get_failed_count()

        # Assert
        assert result == 5

    @pytest.mark.asyncio
    async def test_get_pending_count(
        self,
        notification_queue: NotificationQueue,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify pending count returns queue length."""
        # Arrange
        mock_redis.llen = AsyncMock(return_value=3)

        # Act
        result = await notification_queue.get_pending_count()

        # Assert
        assert result == 3

    @pytest.mark.asyncio
    async def test_retry_successful(
        self,
        notification_queue: NotificationQueue,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Verify successful retry removes notification from queue."""
        # Arrange: Queued notification
        queued = {
            "total_pending": 10,
            "high_priority_count": 2,
            "compliance_warnings": 1,
            "attempts": 1,
            "queued_at": datetime.now(UTC).isoformat(),
            "last_attempt": None,
        }
        mock_redis.lrange = AsyncMock(return_value=[json.dumps(queued).encode()])
        mock_discord_client.send_approval_notification = AsyncMock(return_value=True)

        # Act
        processed = await notification_queue.retry_failed()

        # Assert
        assert processed == 1
        mock_redis.lrem.assert_called()

    @pytest.mark.asyncio
    async def test_retry_increments_attempt(
        self,
        notification_queue: NotificationQueue,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Verify failed retry increments attempt counter."""
        # Arrange: Queued notification with 2 attempts
        queued = {
            "total_pending": 10,
            "high_priority_count": 2,
            "compliance_warnings": 1,
            "attempts": 2,
            "queued_at": datetime.now(UTC).isoformat(),
            "last_attempt": None,
        }
        mock_redis.lrange = AsyncMock(return_value=[json.dumps(queued).encode()])
        mock_discord_client.send_approval_notification = AsyncMock(return_value=False)

        # Act
        await notification_queue.retry_failed()

        # Assert: Should update with incremented attempts
        mock_redis.lpush.assert_called()

    @pytest.mark.asyncio
    async def test_max_retries_abandoned(
        self,
        notification_queue: NotificationQueue,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Verify notifications are abandoned after max retries."""
        # Arrange: Queued notification with 5 attempts (max)
        queued = {
            "total_pending": 10,
            "high_priority_count": 2,
            "compliance_warnings": 1,
            "attempts": 5,
            "queued_at": datetime.now(UTC).isoformat(),
            "last_attempt": None,
        }
        mock_redis.lrange = AsyncMock(return_value=[json.dumps(queued).encode()])
        mock_discord_client.send_approval_notification = AsyncMock(return_value=False)

        # Act
        with patch("core.notifications.queue.logger") as mock_logger:
            await notification_queue.retry_failed()

            # Assert: Should log abandonment
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_backoff_respected(
        self,
        notification_queue: NotificationQueue,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Verify backoff time is respected between retries."""
        # Arrange: Notification with recent attempt (within backoff)
        recent_attempt = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
        queued = {
            "total_pending": 10,
            "high_priority_count": 2,
            "compliance_warnings": 1,
            "attempts": 1,
            "queued_at": datetime.now(UTC).isoformat(),
            "last_attempt": recent_attempt,
        }
        mock_redis.lrange = AsyncMock(return_value=[json.dumps(queued).encode()])

        # Act
        processed = await notification_queue.retry_failed()

        # Assert: Should not process (still in backoff)
        assert processed == 0
        mock_discord_client.send_approval_notification.assert_not_called()


class TestQueuedNotification:
    """Tests for QueuedNotification dataclass."""

    def test_from_queue_status(self) -> None:
        """Verify QueuedNotification created from QueueStatus."""
        status = QueueStatus(
            total_pending=10,
            by_source_type={"instagram_post": 10},
            by_priority={1: 2, 3: 8},
            compliance_warnings=1,
            highest_priority_item="test-id",
        )

        queued = QueuedNotification.from_queue_status(status)

        assert queued.total_pending == 10
        assert queued.high_priority_count == 2
        assert queued.compliance_warnings == 1
        assert queued.attempts == 0

    def test_backoff_calculation(self) -> None:
        """Verify backoff increases with attempts."""
        queued = QueuedNotification(
            total_pending=10,
            high_priority_count=2,
            compliance_warnings=1,
            attempts=1,
            queued_at=datetime.now(UTC),
            last_attempt=None,
        )

        # Backoff: 1min, 5min, 15min, 1hr for attempts 1-4
        assert queued.get_backoff_seconds() == 60  # 1 min

        queued.attempts = 2
        assert queued.get_backoff_seconds() == 300  # 5 min

        queued.attempts = 3
        assert queued.get_backoff_seconds() == 900  # 15 min

        queued.attempts = 4
        assert queued.get_backoff_seconds() == 3600  # 1 hr
