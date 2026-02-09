"""Tests for PublishNotificationService.

Story 4-7: Discord Publish Notifications

Tests the publish notification orchestration including:
- Single publish notifications
- Batch publish notifications
- Failure notifications
- Non-blocking execution
- Redis batching integration

Test Coverage:
- AC #1: Notification on successful publish
- AC #2: Batching multiple publishes
- AC #3: Failure notifications with error details
"""

from datetime import datetime, timedelta, UTC
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.notifications.publish_notifier import (
    PublishNotificationService,
    PublishNotifierProtocol,
    PublishNotificationConfig,
    PublishedPostInfo,
    FailedPublishInfo,
)


@pytest.fixture
def mock_discord_client() -> AsyncMock:
    """Create mock Discord client."""
    mock = AsyncMock()
    mock.send_publish_notification = AsyncMock(return_value=True)
    mock.send_publish_failed_notification = AsyncMock(return_value=True)
    mock.send_batch_publish_notification = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_batcher() -> AsyncMock:
    """Create mock publish batcher."""
    mock = AsyncMock()
    mock.add_publish = AsyncMock(return_value=False)  # Not ready to send
    mock.get_and_clear_batch = AsyncMock(return_value=[])
    mock.get_batch_count = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_notification_queue() -> AsyncMock:
    """Create mock notification queue."""
    mock = AsyncMock()
    mock.add = AsyncMock()
    return mock


@pytest.fixture
def publish_config() -> PublishNotificationConfig:
    """Create test publish notification config."""
    return PublishNotificationConfig(
        webhook_url="https://discord.com/api/webhooks/test/token",
        batch_window_minutes=15,
        daily_summary_hour=22,
        enabled=True,
        dashboard_url="http://localhost:3000/approval",
    )


def create_published_post_info(
    item_id: str = None,
    title: str = "Test post title",
    caption_excerpt: str = "This is a test caption...",
    instagram_url: str = "https://instagram.com/p/test123",
    publish_time: datetime = None,
) -> PublishedPostInfo:
    """Create a published post info for testing."""
    return PublishedPostInfo(
        item_id=item_id or str(uuid4()),
        title=title,
        caption_excerpt=caption_excerpt,
        instagram_url=instagram_url,
        publish_time=publish_time or datetime.now(UTC),
    )


def create_failed_publish_info(
    item_id: str = None,
    title: str = "Test post title",
    error_reason: str = "API connection failed",
    error_type: str = "API_ERROR",
    scheduled_time: datetime = None,
) -> FailedPublishInfo:
    """Create a failed publish info for testing."""
    return FailedPublishInfo(
        item_id=item_id or str(uuid4()),
        title=title,
        error_reason=error_reason,
        error_type=error_type,
        scheduled_time=scheduled_time or datetime.now(UTC),
    )


class TestPublishNotificationService:
    """Tests for publish notification orchestration."""

    @pytest.mark.asyncio
    async def test_single_publish_notification_batched(
        self,
        mock_discord_client: AsyncMock,
        mock_batcher: AsyncMock,
        mock_notification_queue: AsyncMock,
        publish_config: PublishNotificationConfig,
    ) -> None:
        """Verify single publish is added to batch (AC #2)."""
        # Arrange
        post_info = create_published_post_info()
        mock_batcher.add_publish = AsyncMock(return_value=False)  # Not ready

        service = PublishNotificationService(
            config=publish_config,
            discord_client=mock_discord_client,
            batcher=mock_batcher,
            notification_queue=mock_notification_queue,
        )

        # Act
        result = await service.notify_publish_success(post_info)

        # Assert
        assert result is True
        mock_batcher.add_publish.assert_called_once_with(post_info)
        mock_discord_client.send_publish_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_ready_sends_notification(
        self,
        mock_discord_client: AsyncMock,
        mock_batcher: AsyncMock,
        mock_notification_queue: AsyncMock,
        publish_config: PublishNotificationConfig,
    ) -> None:
        """Verify batch is sent when window expires (AC #2)."""
        # Arrange: Batcher signals ready to send
        post_info = create_published_post_info()
        mock_batcher.add_publish = AsyncMock(return_value=True)  # Ready to send
        mock_batcher.get_and_clear_batch = AsyncMock(return_value=[post_info])

        service = PublishNotificationService(
            config=publish_config,
            discord_client=mock_discord_client,
            batcher=mock_batcher,
            notification_queue=mock_notification_queue,
        )

        # Act
        result = await service.notify_publish_success(post_info)

        # Assert
        assert result is True
        mock_discord_client.send_publish_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_posts_batch_notification(
        self,
        mock_discord_client: AsyncMock,
        mock_batcher: AsyncMock,
        mock_notification_queue: AsyncMock,
        publish_config: PublishNotificationConfig,
    ) -> None:
        """Verify multiple posts trigger batch notification (AC #2)."""
        # Arrange: 3 posts in batch
        posts = [create_published_post_info() for _ in range(3)]
        mock_batcher.add_publish = AsyncMock(return_value=True)
        mock_batcher.get_and_clear_batch = AsyncMock(return_value=posts)

        service = PublishNotificationService(
            config=publish_config,
            discord_client=mock_discord_client,
            batcher=mock_batcher,
            notification_queue=mock_notification_queue,
        )

        # Act
        result = await service.notify_publish_success(posts[0])

        # Assert
        assert result is True
        mock_discord_client.send_batch_publish_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_failure_notification_immediate(
        self,
        mock_discord_client: AsyncMock,
        mock_batcher: AsyncMock,
        mock_notification_queue: AsyncMock,
        publish_config: PublishNotificationConfig,
    ) -> None:
        """Verify failure notifications are sent immediately (AC #3)."""
        # Arrange
        failure_info = create_failed_publish_info()

        service = PublishNotificationService(
            config=publish_config,
            discord_client=mock_discord_client,
            batcher=mock_batcher,
            notification_queue=mock_notification_queue,
        )

        # Act
        result = await service.notify_publish_failed(failure_info)

        # Assert
        assert result is True
        mock_discord_client.send_publish_failed_notification.assert_called_once()
        mock_batcher.add_publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_includes_retry_url(
        self,
        mock_discord_client: AsyncMock,
        mock_batcher: AsyncMock,
        mock_notification_queue: AsyncMock,
        publish_config: PublishNotificationConfig,
    ) -> None:
        """Verify failure notification includes retry dashboard URL (AC #3)."""
        # Arrange
        failure_info = create_failed_publish_info(item_id="test-item-123")

        service = PublishNotificationService(
            config=publish_config,
            discord_client=mock_discord_client,
            batcher=mock_batcher,
            notification_queue=mock_notification_queue,
        )

        # Act
        await service.notify_publish_failed(failure_info)

        # Assert
        call_kwargs = mock_discord_client.send_publish_failed_notification.call_args.kwargs
        assert "dashboard_url" in call_kwargs
        assert "test-item-123" in call_kwargs["dashboard_url"]

    @pytest.mark.asyncio
    async def test_disabled_notifications_skipped(
        self,
        mock_discord_client: AsyncMock,
        mock_batcher: AsyncMock,
        mock_notification_queue: AsyncMock,
        publish_config: PublishNotificationConfig,
    ) -> None:
        """Verify notifications skip when disabled."""
        # Arrange
        publish_config.enabled = False
        post_info = create_published_post_info()

        service = PublishNotificationService(
            config=publish_config,
            discord_client=mock_discord_client,
            batcher=mock_batcher,
            notification_queue=mock_notification_queue,
        )

        # Act
        result = await service.notify_publish_success(post_info)

        # Assert
        assert result is False
        mock_batcher.add_publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_discord_call_queued(
        self,
        mock_discord_client: AsyncMock,
        mock_batcher: AsyncMock,
        mock_notification_queue: AsyncMock,
        publish_config: PublishNotificationConfig,
    ) -> None:
        """Verify failed Discord calls are queued for retry (AC #3)."""
        # Arrange
        failure_info = create_failed_publish_info()
        mock_discord_client.send_publish_failed_notification = AsyncMock(
            return_value=False
        )

        service = PublishNotificationService(
            config=publish_config,
            discord_client=mock_discord_client,
            batcher=mock_batcher,
            notification_queue=mock_notification_queue,
        )

        # Act
        result = await service.notify_publish_failed(failure_info)

        # Assert
        assert result is False
        mock_notification_queue.add.assert_called_once()


class TestPublishedPostInfo:
    """Tests for PublishedPostInfo dataclass."""

    def test_creation(self) -> None:
        """Verify PublishedPostInfo dataclass works correctly."""
        now = datetime.now(UTC)
        info = PublishedPostInfo(
            item_id="test-123",
            title="Test post",
            caption_excerpt="This is a test...",
            instagram_url="https://instagram.com/p/abc",
            publish_time=now,
        )

        assert info.item_id == "test-123"
        assert info.title == "Test post"
        assert info.instagram_url == "https://instagram.com/p/abc"
        assert info.publish_time == now


class TestFailedPublishInfo:
    """Tests for FailedPublishInfo dataclass."""

    def test_creation(self) -> None:
        """Verify FailedPublishInfo dataclass works correctly."""
        now = datetime.now(UTC)
        info = FailedPublishInfo(
            item_id="test-123",
            title="Test post",
            error_reason="Connection failed",
            error_type="NETWORK_ERROR",
            scheduled_time=now,
        )

        assert info.item_id == "test-123"
        assert info.error_type == "NETWORK_ERROR"
        assert info.scheduled_time == now


class TestPublishNotificationConfig:
    """Tests for PublishNotificationConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify PublishNotificationConfig defaults."""
        config = PublishNotificationConfig(
            webhook_url="https://discord.com/api/webhooks/test/token",
        )

        assert config.batch_window_minutes == 15
        assert config.daily_summary_hour == 22
        assert config.enabled is True

    def test_custom_values(self) -> None:
        """Verify custom configuration."""
        config = PublishNotificationConfig(
            webhook_url="https://discord.com/api/webhooks/test/token",
            batch_window_minutes=30,
            daily_summary_hour=20,
        )

        assert config.batch_window_minutes == 30
        assert config.daily_summary_hour == 20
