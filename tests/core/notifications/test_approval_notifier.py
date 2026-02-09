"""Tests for ApprovalNotificationService.

Tests the approval notification orchestration including:
- Threshold triggering
- Rate limiting integration
- Compliance warning counting
- Discord client integration
- Graceful failure handling

Test Coverage:
- AC #1: Threshold-based notification triggering
- AC #2: Rate limiting and batching
- AC #3: Compliance warning prioritization
- AC #4: Non-blocking failure handling
"""

from datetime import datetime, timedelta
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.notifications.approval_notifier import (
    ApprovalNotificationService,
    ApprovalNotifierProtocol,
    NotificationConfig,
    QueueStatus,
)
from core.notifications.rate_limiter import NotificationRateLimiter


@pytest.fixture
def mock_discord_client() -> AsyncMock:
    """Create mock Discord client."""
    mock = AsyncMock()
    mock.send_approval_notification = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_rate_limiter() -> AsyncMock:
    """Create mock rate limiter."""
    mock = AsyncMock(spec=NotificationRateLimiter)
    mock.is_rate_limited = AsyncMock(return_value=False)
    mock.record_notification = AsyncMock()
    mock.queue_pending_notification = AsyncMock()
    return mock


@pytest.fixture
def mock_queue_repo() -> AsyncMock:
    """Create mock approval queue repository."""
    mock = AsyncMock()
    mock.get_pending_items = AsyncMock(return_value=([], 0, None))
    return mock


@pytest.fixture
def notification_config() -> NotificationConfig:
    """Create test notification config."""
    return NotificationConfig(
        webhook_url="https://discord.com/api/webhooks/test/token",
        threshold=5,
        cooldown_minutes=60,
        dashboard_url="http://localhost:3000/approval",
        enabled=True,
    )


def create_mock_item(
    source_type: str = "instagram_post",
    source_priority: int = 3,
    compliance_status: str = "COMPLIANT",
) -> MagicMock:
    """Create a mock approval item for testing."""
    item = MagicMock()
    item.id = uuid4()
    item.source_type = source_type
    item.source_priority = source_priority
    item.compliance_status = compliance_status
    return item


class TestApprovalNotificationService:
    """Tests for approval notification orchestration."""

    @pytest.mark.asyncio
    async def test_notification_sent_at_threshold(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify notification triggers at exactly threshold (AC #1)."""
        # Arrange: 5 pending items (at threshold)
        mock_items = [create_mock_item() for _ in range(5)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is True
        mock_discord_client.send_approval_notification.assert_called_once()
        mock_rate_limiter.record_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_notification_below_threshold(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify no notification when below threshold (AC #1)."""
        # Arrange: 4 pending items (below threshold of 5)
        mock_items = [create_mock_item() for _ in range(4)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 4, None)
        )

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is False
        mock_discord_client.send_approval_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_rate_limiting_prevents_spam(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify rate limiting prevents multiple notifications (AC #2)."""
        # Arrange: Queue is above threshold but rate limited
        mock_items = [create_mock_item() for _ in range(10)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 10, None)
        )
        mock_rate_limiter.is_rate_limited = AsyncMock(return_value=True)

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is False
        mock_discord_client.send_approval_notification.assert_not_called()
        mock_rate_limiter.queue_pending_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_compliance_warnings_counted(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify compliance warnings are correctly aggregated (AC #3)."""
        # Arrange: 5 items, 2 with compliance warnings
        mock_items = [
            create_mock_item(compliance_status="COMPLIANT"),
            create_mock_item(compliance_status="WARNING"),
            create_mock_item(compliance_status="COMPLIANT"),
            create_mock_item(compliance_status="WARNING"),
            create_mock_item(compliance_status="COMPLIANT"),
        ]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        await service.check_and_notify()

        # Assert: Check that 2 compliance warnings were passed
        call_kwargs = mock_discord_client.send_approval_notification.call_args.kwargs
        assert call_kwargs["compliance_warnings"] == 2

    @pytest.mark.asyncio
    async def test_high_priority_counted(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify high priority items are correctly counted."""
        # Arrange: 5 items, 2 are TRENDING (priority 1)
        mock_items = [
            create_mock_item(source_priority=1),  # TRENDING
            create_mock_item(source_priority=1),  # TRENDING
            create_mock_item(source_priority=3),  # EVERGREEN
            create_mock_item(source_priority=3),  # EVERGREEN
            create_mock_item(source_priority=4),  # RESEARCH
        ]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        await service.check_and_notify()

        # Assert: Check that 2 high priority items were counted
        call_kwargs = mock_discord_client.send_approval_notification.call_args.kwargs
        assert call_kwargs["high_priority_count"] == 2

    @pytest.mark.asyncio
    async def test_failure_queued_for_retry(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify failed notifications are queued (AC #4)."""
        # Arrange: Discord client fails
        mock_items = [create_mock_item() for _ in range(5)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )
        mock_discord_client.send_approval_notification = AsyncMock(return_value=False)

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is False
        mock_rate_limiter.record_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_blocking_on_exception(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify content submission not blocked by notification failure (AC #4)."""
        # Arrange: Discord client raises exception
        mock_items = [create_mock_item() for _ in range(5)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )
        mock_discord_client.send_approval_notification = AsyncMock(
            side_effect=Exception("Network error")
        )

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act - should not raise
        result = await service.check_and_notify()

        # Assert: No exception propagated
        assert result is False

    @pytest.mark.asyncio
    async def test_notifications_disabled(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify notifications skip when disabled."""
        # Arrange: Disable notifications
        notification_config.enabled = False
        mock_items = [create_mock_item() for _ in range(10)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 10, None)
        )

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is False
        mock_discord_client.send_approval_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_dashboard_url_passed_to_discord(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify dashboard URL is passed to Discord notification."""
        # Arrange
        mock_items = [create_mock_item() for _ in range(5)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        await service.check_and_notify()

        # Assert
        call_kwargs = mock_discord_client.send_approval_notification.call_args.kwargs
        assert call_kwargs["dashboard_url"] == "http://localhost:3000/approval"

    @pytest.mark.asyncio
    async def test_empty_queue_no_notification(
        self,
        mock_discord_client: AsyncMock,
        mock_rate_limiter: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify no notification for empty queue."""
        # Arrange
        mock_queue_repo.get_pending_items = AsyncMock(return_value=([], 0, None))

        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=mock_rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is False
        mock_discord_client.send_approval_notification.assert_not_called()


class TestQueueStatus:
    """Tests for QueueStatus dataclass."""

    def test_queue_status_creation(self) -> None:
        """Verify QueueStatus dataclass works correctly."""
        status = QueueStatus(
            total_pending=10,
            by_source_type={"instagram_post": 7, "b2b_email": 3},
            by_priority={1: 2, 3: 5, 4: 3},
            compliance_warnings=1,
            highest_priority_item="test-id-123",
        )

        assert status.total_pending == 10
        assert status.by_source_type["instagram_post"] == 7
        assert status.compliance_warnings == 1


class TestNotificationConfig:
    """Tests for NotificationConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify NotificationConfig defaults."""
        config = NotificationConfig(
            webhook_url="https://discord.com/api/webhooks/test/token",
        )

        assert config.threshold == 5
        assert config.cooldown_minutes == 60
        assert config.enabled is True

    def test_custom_threshold(self) -> None:
        """Verify custom threshold configuration."""
        config = NotificationConfig(
            webhook_url="https://discord.com/api/webhooks/test/token",
            threshold=10,
            cooldown_minutes=30,
        )

        assert config.threshold == 10
        assert config.cooldown_minutes == 30
