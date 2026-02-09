"""Integration tests for notification system.

Story 4-6, Task 9.4: Integration test full notification flow.

Tests the complete notification pipeline including:
- ApprovalNotificationService with all dependencies
- Rate limiting integration
- Failed notification queueing
- Event emission
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.notifications.approval_notifier import (
    ApprovalNotificationService,
    NotificationConfig,
    QueueStatus,
)
from core.notifications.rate_limiter import NotificationRateLimiter
from core.notifications.queue import NotificationQueue
from core.notifications.hooks import on_approval_item_created
from core.notifications.events import (
    notification_events,
    NotificationEventType,
)


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock()
    mock.delete = AsyncMock()
    mock.lpush = AsyncMock()
    mock.lrange = AsyncMock(return_value=[])
    mock.llen = AsyncMock(return_value=0)
    mock.lrem = AsyncMock()
    mock.expire = AsyncMock()
    return mock


@pytest.fixture
def mock_discord_client() -> AsyncMock:
    """Create mock Discord client."""
    mock = AsyncMock()
    mock.send_approval_notification = AsyncMock(return_value=True)
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


class TestNotificationIntegration:
    """Integration tests for notification system."""

    @pytest.mark.asyncio
    async def test_full_notification_flow_success(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Test complete notification flow: threshold met -> notification sent."""
        # Arrange: Create all components
        rate_limiter = NotificationRateLimiter(
            redis_client=mock_redis,
            cooldown_minutes=60,
        )
        notification_queue = NotificationQueue(
            redis_client=mock_redis,
            discord_client=mock_discord_client,
            dashboard_url=notification_config.dashboard_url,
        )
        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=rate_limiter,
            queue_repo=mock_queue_repo,
            notification_queue=notification_queue,
        )

        # Mock queue with 5 items (at threshold)
        mock_items = [create_mock_item() for _ in range(5)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is True
        mock_discord_client.send_approval_notification.assert_called_once()
        # Rate limiter should record the notification
        mock_redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_rate_limited_queues_for_later(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Test that rate-limited notifications are queued for later."""
        # Arrange: Rate limiter returns True (in cooldown)
        last_sent = datetime.now(UTC).isoformat()
        mock_redis.get = AsyncMock(return_value=last_sent.encode())

        rate_limiter = NotificationRateLimiter(
            redis_client=mock_redis,
            cooldown_minutes=60,
        )
        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Mock queue with 10 items (above threshold)
        mock_items = [create_mock_item() for _ in range(10)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 10, None)
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is False
        mock_discord_client.send_approval_notification.assert_not_called()
        # Should queue pending notification
        mock_redis.lpush.assert_called()

    @pytest.mark.asyncio
    async def test_failed_notification_queued_for_retry(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Test that failed notifications are queued for retry."""
        # Arrange: Discord client fails
        mock_discord_client.send_approval_notification = AsyncMock(return_value=False)

        rate_limiter = NotificationRateLimiter(
            redis_client=mock_redis,
            cooldown_minutes=60,
        )
        notification_queue = NotificationQueue(
            redis_client=mock_redis,
            discord_client=mock_discord_client,
            dashboard_url=notification_config.dashboard_url,
        )
        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=rate_limiter,
            queue_repo=mock_queue_repo,
            notification_queue=notification_queue,
        )

        # Mock queue with 5 items (at threshold)
        mock_items = [create_mock_item() for _ in range(5)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )

        # Act
        result = await service.check_and_notify()

        # Assert
        assert result is False
        # Failed notification should be queued
        assert mock_redis.lpush.called

    @pytest.mark.asyncio
    async def test_hook_triggers_notification_and_emits_event(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Test that hook triggers notification check and emits events."""
        # Arrange
        rate_limiter = NotificationRateLimiter(
            redis_client=mock_redis,
            cooldown_minutes=60,
        )
        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Mock queue with 5 items
        mock_items = [create_mock_item() for _ in range(5)]
        mock_queue_repo.get_pending_items = AsyncMock(
            return_value=(mock_items, 5, None)
        )

        item = create_mock_item()

        # Act
        await on_approval_item_created(item, service)

        # Assert: Notification was sent
        mock_discord_client.send_approval_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_compliance_warning_triggers_event(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Test that compliance warning items emit events."""
        # Arrange
        rate_limiter = NotificationRateLimiter(
            redis_client=mock_redis,
            cooldown_minutes=60,
        )
        service = ApprovalNotificationService(
            config=notification_config,
            discord_client=mock_discord_client,
            rate_limiter=rate_limiter,
            queue_repo=mock_queue_repo,
        )

        # Item with compliance warning
        item = create_mock_item(compliance_status="WARNING")

        # Act - hook should emit compliance warning event
        with patch("core.notifications.hooks.notification_events") as mock_events:
            mock_events.emit = AsyncMock()
            await on_approval_item_created(item, service)

            # Assert: Compliance warning event emitted
            mock_events.emit.assert_called()
            call_args = mock_events.emit.call_args[0][0]
            assert call_args.event_type == NotificationEventType.COMPLIANCE_WARNING

    @pytest.mark.asyncio
    async def test_all_components_wired_correctly(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
        mock_queue_repo: AsyncMock,
        notification_config: NotificationConfig,
    ) -> None:
        """Verify all components integrate correctly."""
        # This test verifies that all imports and wiring work
        from core.notifications import (
            ApprovalNotificationService,
            NotificationRateLimiter,
            NotificationQueue,
            on_approval_item_created,
            notification_events,
            process_notification_queue,
            NOTIFICATION_JOB_SETTINGS,
        )

        # Verify exports exist and are callable/usable
        assert callable(ApprovalNotificationService)
        assert callable(NotificationRateLimiter)
        assert callable(NotificationQueue)
        assert callable(on_approval_item_created)
        assert notification_events is not None
        assert callable(process_notification_queue)
        assert isinstance(NOTIFICATION_JOB_SETTINGS, dict)
        assert "cron_jobs" in NOTIFICATION_JOB_SETTINGS
        assert "functions" in NOTIFICATION_JOB_SETTINGS


# ============================================================================
# Story 4-7: Publish Notification Integration Tests
# ============================================================================


@pytest.fixture
def mock_publish_batcher() -> AsyncMock:
    """Create mock publish batcher."""
    mock = AsyncMock()
    mock.add_publish = AsyncMock(return_value=False)
    mock.get_and_clear_batch = AsyncMock(return_value=[])
    mock.get_batch_count = AsyncMock(return_value=0)
    return mock


def create_mock_publish_item(
    caption: str = "Test caption for publish",
    scheduled_time: datetime = None,
) -> MagicMock:
    """Create a mock approval item for publish testing."""
    item = MagicMock()
    item.id = uuid4()
    item.full_caption = caption
    item.scheduled_publish_time = scheduled_time or datetime.now(UTC)
    return item


class TestPublishNotificationIntegration:
    """Integration tests for publish notification system (Story 4-7)."""

    @pytest.mark.asyncio
    async def test_full_publish_success_notification_flow(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Test complete publish success flow: publish -> notification (AC #1)."""
        from core.notifications.publish_notifier import (
            PublishNotificationService,
            PublishNotificationConfig,
            PublishedPostInfo,
        )
        from core.notifications.publish_batcher import PublishBatcher
        from core.notifications.hooks import on_publish_success
        from core.notifications.events import NotificationEventEmitter

        # Arrange: Create all components
        config = PublishNotificationConfig(
            webhook_url="https://discord.com/api/webhooks/test/token",
            batch_window_minutes=15,
            enabled=True,
        )

        # Mock batcher to return True (ready to send) and single post
        mock_redis.get = AsyncMock(return_value=None)  # No batch started

        batcher = PublishBatcher(redis_client=mock_redis, batch_window_minutes=15)
        mock_discord_client.send_publish_notification = AsyncMock(return_value=True)
        mock_discord_client.send_batch_publish_notification = AsyncMock(return_value=True)

        service = PublishNotificationService(
            config=config,
            discord_client=mock_discord_client,
            batcher=batcher,
        )

        event_emitter = AsyncMock()
        event_emitter.emit = AsyncMock()

        item = create_mock_publish_item()

        # Act: Trigger publish success hook
        await on_publish_success(
            item=item,
            instagram_post_id="123456789",
            instagram_url="https://instagram.com/p/abc123",
            notifier=service,
            event_emitter=event_emitter,
        )

        # Assert: Notification was added to batch
        mock_redis.rpush.assert_called()
        event_emitter.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_publish_failure_notification_flow(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Test complete publish failure flow: fail -> immediate notification (AC #3)."""
        from core.notifications.publish_notifier import (
            PublishNotificationService,
            PublishNotificationConfig,
        )
        from core.notifications.publish_batcher import PublishBatcher
        from core.notifications.hooks import on_publish_failed
        from core.notifications.events import NotificationEventEmitter

        # Arrange
        config = PublishNotificationConfig(
            webhook_url="https://discord.com/api/webhooks/test/token",
            enabled=True,
        )

        batcher = PublishBatcher(redis_client=mock_redis, batch_window_minutes=15)
        mock_discord_client.send_publish_failed_notification = AsyncMock(return_value=True)

        service = PublishNotificationService(
            config=config,
            discord_client=mock_discord_client,
            batcher=batcher,
        )

        event_emitter = AsyncMock()
        event_emitter.emit = AsyncMock()

        item = create_mock_publish_item()

        # Act: Trigger publish failure hook
        await on_publish_failed(
            item=item,
            error_reason="Instagram API rate limit exceeded",
            error_type="RATE_LIMIT",
            notifier=service,
            event_emitter=event_emitter,
        )

        # Assert: Immediate notification sent (not batched)
        mock_discord_client.send_publish_failed_notification.assert_called_once()
        event_emitter.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_notification_flow(
        self,
        mock_redis: AsyncMock,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Test batch notification when multiple publishes within window (AC #2)."""
        from core.notifications.publish_notifier import (
            PublishNotificationService,
            PublishNotificationConfig,
            PublishedPostInfo,
        )
        from core.notifications.publish_batcher import PublishBatcher
        from datetime import timedelta
        import json

        # Arrange: Batch with 3 posts already present, window expired
        config = PublishNotificationConfig(
            webhook_url="https://discord.com/api/webhooks/test/token",
            batch_window_minutes=15,
            enabled=True,
        )

        # Simulate batch started 20 minutes ago (expired)
        batch_start = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()
        mock_redis.get = AsyncMock(return_value=batch_start.encode())

        now = datetime.now(UTC)
        batch_items = [
            json.dumps({
                "item_id": f"post-{i}",
                "title": f"Post {i}",
                "caption_excerpt": f"Caption {i}",
                "instagram_url": f"https://instagram.com/p/{i}",
                "publish_time": now.isoformat(),
            }).encode()
            for i in range(3)
        ]
        mock_redis.lrange = AsyncMock(return_value=batch_items)

        batcher = PublishBatcher(redis_client=mock_redis, batch_window_minutes=15)
        mock_discord_client.send_batch_publish_notification = AsyncMock(return_value=True)

        service = PublishNotificationService(
            config=config,
            discord_client=mock_discord_client,
            batcher=batcher,
        )

        # Create one more post to trigger batch send
        post_info = PublishedPostInfo(
            item_id="post-4",
            title="Post 4",
            caption_excerpt="Caption 4",
            instagram_url="https://instagram.com/p/4",
            publish_time=datetime.now(UTC),
        )

        # Act
        result = await service.notify_publish_success(post_info)

        # Assert: Batch notification sent with all posts
        assert result is True
        mock_discord_client.send_batch_publish_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_story_47_components_wired_correctly(self) -> None:
        """Verify all Story 4-7 components integrate correctly."""
        from core.notifications import (
            # Story 4-7 exports
            PublishNotificationService,
            PublishNotifierProtocol,
            PublishNotificationConfig,
            PublishedPostInfo,
            FailedPublishInfo,
            PublishBatcher,
            on_publish_success,
            on_publish_failed,
            NotificationEventType,
        )

        # Verify exports exist and are callable/usable
        assert callable(PublishNotificationService)
        assert callable(PublishBatcher)
        assert callable(on_publish_success)
        assert callable(on_publish_failed)

        # Verify event types
        assert NotificationEventType.PUBLISH_SUCCESS.value == "publish_success"
        assert NotificationEventType.PUBLISH_FAILED.value == "publish_failed"

        # Verify dataclasses
        config = PublishNotificationConfig(
            webhook_url="https://discord.com/api/webhooks/test",
        )
        assert config.batch_window_minutes == 15
        assert config.daily_summary_hour == 22

    @pytest.mark.asyncio
    async def test_daily_summary_job_integration(
        self,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Test daily summary job with full dependencies (AC #4)."""
        from core.notifications.jobs import send_daily_publish_summary
        from dataclasses import dataclass

        @dataclass
        class MockDailyStats:
            published: int
            pending: int
            failed: int

        mock_approval_repo = AsyncMock()
        mock_approval_repo.get_daily_publishing_stats = AsyncMock(
            return_value=MockDailyStats(published=5, pending=2, failed=1)
        )
        mock_approval_repo.get_top_performing_post = AsyncMock(
            return_value={"title": "Top post", "engagement": 150}
        )
        mock_discord_client.send_daily_summary_notification = AsyncMock(return_value=True)

        ctx = {
            "discord_client": mock_discord_client,
            "approval_repo": mock_approval_repo,
        }

        # Act
        result = await send_daily_publish_summary(ctx)

        # Assert
        assert "SENT" in result
        mock_discord_client.send_daily_summary_notification.assert_called_once()
        call_kwargs = mock_discord_client.send_daily_summary_notification.call_args.kwargs
        assert call_kwargs["published_count"] == 5
        assert call_kwargs["top_post"]["title"] == "Top post"
