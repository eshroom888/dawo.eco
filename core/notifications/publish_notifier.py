"""Publish notification service.

Story 4-7: Discord Publish Notifications

Orchestrates Discord notifications for Instagram publishing events.
Handles successful publishes (with batching) and failures (immediate).

Architecture Compliance:
- Protocol-based dependency injection
- Configuration via constructor
- Non-blocking notification flow
- Graceful error handling

Usage:
    service = PublishNotificationService(
        config=PublishNotificationConfig(...),
        discord_client=discord_client,
        batcher=publish_batcher,
        notification_queue=notification_queue,
    )
    await service.notify_publish_success(post_info)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from integrations.discord.client import DiscordClientProtocol
    from core.notifications.queue import NotificationQueue

logger = logging.getLogger(__name__)


@dataclass
class PublishNotificationConfig:
    """Configuration for publish notifications.

    Loaded via dependency injection from config files.

    Attributes:
        webhook_url: Discord webhook URL
        batch_window_minutes: Time to wait for additional posts before sending (default: 15)
        daily_summary_hour: Hour to send daily summary (default: 22 / 10 PM)
        dashboard_url: URL to approval dashboard for embed link
        enabled: Whether notifications are enabled
    """

    webhook_url: str
    batch_window_minutes: int = 15
    daily_summary_hour: int = 22
    dashboard_url: str = "http://localhost:3000/approval"
    enabled: bool = True


@dataclass
class PublishedPostInfo:
    """Information about a published post.

    Used to pass publish success data to notification service.

    Attributes:
        item_id: Approval item ID
        title: Post title/excerpt (first 50 chars of caption)
        caption_excerpt: First 100 chars of caption
        instagram_url: Direct link to Instagram post
        publish_time: When the post was published
    """

    item_id: str
    title: str
    caption_excerpt: str
    instagram_url: str
    publish_time: datetime


@dataclass
class FailedPublishInfo:
    """Information about a failed publish.

    Used to pass publish failure data to notification service.

    Attributes:
        item_id: Approval item ID
        title: Post title/excerpt
        error_reason: Human-readable error message
        error_type: Error category (API_ERROR, RATE_LIMIT, etc.)
        scheduled_time: Original scheduled publish time
    """

    item_id: str
    title: str
    error_reason: str
    error_type: str
    scheduled_time: datetime


class PublishNotifierProtocol(Protocol):
    """Protocol for publish notification service.

    Defines the interface for notification services to enable
    dependency injection and testing.
    """

    async def notify_publish_success(
        self,
        post_info: PublishedPostInfo,
    ) -> bool:
        """Notify about successful publish.

        Returns:
            True if notification was sent/batched, False otherwise
        """
        ...

    async def notify_publish_failed(
        self,
        failure_info: FailedPublishInfo,
    ) -> bool:
        """Notify about failed publish.

        Returns:
            True if notification was sent, False otherwise
        """
        ...


class PublishBatcherProtocol(Protocol):
    """Protocol for publish batcher.

    Defines the interface for batching logic.
    """

    async def add_publish(self, post_info: PublishedPostInfo) -> bool:
        """Add a published post to the batch.

        Returns:
            True if batch should be sent now, False to continue batching
        """
        ...

    async def get_and_clear_batch(self) -> list[PublishedPostInfo]:
        """Get all batched posts and clear the batch.

        Returns:
            List of published post info objects
        """
        ...

    async def get_batch_count(self) -> int:
        """Get current number of posts in batch."""
        ...


class NotificationQueueProtocol(Protocol):
    """Protocol for notification queue."""

    async def add(
        self,
        notification_type: str,
        data: dict,
    ) -> None:
        """Add a notification to the retry queue."""
        ...


class PublishNotificationService:
    """Service for sending publish notifications.

    Handles notifications for successful and failed Instagram publishes.
    Implements intelligent batching to prevent notification spam when
    multiple posts publish in quick succession.

    Story 4-7 Implementation:
    - AC #1: Single post publish notifications
    - AC #2: Batch notifications for multiple posts
    - AC #3: Failure notifications with error details

    Attributes:
        _config: Publish notification configuration
        _discord: Discord webhook client (injected)
        _batcher: Publish batcher for aggregating notifications
        _notification_queue: Queue for failed notification retries
    """

    def __init__(
        self,
        config: PublishNotificationConfig,
        discord_client: "DiscordClientProtocol",
        batcher: PublishBatcherProtocol,
        notification_queue: Optional[NotificationQueueProtocol] = None,
    ) -> None:
        """Initialize notification service with dependencies.

        Args:
            config: Publish notification configuration
            discord_client: Discord webhook client for sending notifications
            batcher: Publish batcher for aggregating multiple publishes
            notification_queue: Queue for failed notification retry (optional)
        """
        self._config = config
        self._discord = discord_client
        self._batcher = batcher
        self._notification_queue = notification_queue

    async def notify_publish_success(
        self,
        post_info: PublishedPostInfo,
    ) -> bool:
        """Notify about successful publish.

        Uses batching to aggregate multiple publishes into single
        notification if they occur within batch_window_minutes.

        Args:
            post_info: Information about the published post

        Returns:
            True if notification was sent/batched, False on error

        Note:
            This method never raises exceptions - failures are logged
            but do not block the publishing flow.
        """
        if not self._config.enabled:
            logger.debug("Publish notifications disabled")
            return False

        try:
            # Add to batch
            should_send = await self._batcher.add_publish(post_info)

            if should_send:
                # Batch window expired or this is the only post
                return await self._send_batched_notification()

            logger.debug(
                f"Post {post_info.item_id} added to batch, waiting for window"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to process publish success notification: {e}")
            return False

    async def notify_publish_failed(
        self,
        failure_info: FailedPublishInfo,
    ) -> bool:
        """Notify about failed publish.

        Failed publishes are always sent immediately - no batching.
        Includes error details and retry link.

        Args:
            failure_info: Information about the failed publish

        Returns:
            True if notification was sent, False on error

        Note:
            This method never raises exceptions - failures are logged
            but do not block the publishing flow.
        """
        if not self._config.enabled:
            logger.debug("Publish notifications disabled")
            return False

        try:
            retry_url = f"{self._config.dashboard_url}?retry={failure_info.item_id}"

            success = await self._discord.send_publish_failed_notification(
                post_title=failure_info.title,
                error_reason=failure_info.error_reason,
                error_type=failure_info.error_type,
                dashboard_url=retry_url,
                scheduled_time=failure_info.scheduled_time,
            )

            if not success:
                await self._queue_failed_notification(failure_info)

            logger.info(
                f"Publish failure notification {'sent' if success else 'queued'}: "
                f"{failure_info.item_id}"
            )

            return success

        except Exception as e:
            logger.error(f"Failed to process publish failure notification: {e}")
            return False

    async def _send_batched_notification(self) -> bool:
        """Send notification for all batched publishes.

        Determines whether to send single or batch notification
        based on number of posts in batch.

        Returns:
            True if notification sent successfully, False otherwise
        """
        posts = await self._batcher.get_and_clear_batch()

        if not posts:
            return True

        if len(posts) == 1:
            # Single post - send individual notification
            post = posts[0]
            return await self._discord.send_publish_notification(
                post_title=post.title,
                instagram_url=post.instagram_url,
                publish_time=post.publish_time,
                caption_excerpt=post.caption_excerpt,
            )
        else:
            # Multiple posts - send batch notification
            return await self._discord.send_batch_publish_notification(
                posts=[
                    {
                        "title": p.title,
                        "instagram_url": p.instagram_url,
                        "publish_time": p.publish_time.isoformat(),
                    }
                    for p in posts
                ]
            )

    async def _queue_failed_notification(
        self,
        failure_info: FailedPublishInfo,
    ) -> None:
        """Queue failed notification for later retry.

        Task 7.2: On final failure, queue notification for later retry.

        Args:
            failure_info: Information about the failed publish
        """
        if self._notification_queue is None:
            logger.debug("No notification queue configured, skipping retry queue")
            return

        try:
            await self._notification_queue.add(
                notification_type="publish_failed",
                data={
                    "item_id": failure_info.item_id,
                    "title": failure_info.title,
                    "error_reason": failure_info.error_reason,
                    "error_type": failure_info.error_type,
                    "scheduled_time": failure_info.scheduled_time.isoformat(),
                },
            )
            logger.info(
                f"Queued failed publish notification for retry: {failure_info.item_id}"
            )
        except Exception as e:
            logger.error(f"Failed to queue notification for retry: {e}")


__all__ = [
    "PublishNotificationService",
    "PublishNotifierProtocol",
    "PublishBatcherProtocol",
    "NotificationQueueProtocol",
    "PublishNotificationConfig",
    "PublishedPostInfo",
    "FailedPublishInfo",
]
