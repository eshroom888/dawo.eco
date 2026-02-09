"""Approval notification service.

Story 4-6: Discord Approval Notifications

Monitors the approval queue and sends Discord notifications when
the queue reaches a configurable threshold. Implements rate limiting
to prevent notification spam.

Architecture Compliance:
- Protocol-based dependency injection
- Configuration via constructor
- Non-blocking notification flow
- Graceful error handling

Usage:
    service = ApprovalNotificationService(
        config=NotificationConfig(...),
        discord_client=discord_client,
        rate_limiter=rate_limiter,
        queue_repo=queue_repo,
    )
    await service.check_and_notify()
"""

from dataclasses import dataclass
from typing import Optional, Protocol, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from integrations.discord.client import DiscordClientProtocol
    from core.notifications.rate_limiter import NotificationRateLimiter
    from core.notifications.queue import NotificationQueue

logger = logging.getLogger(__name__)


@dataclass
class QueueStatus:
    """Current state of the approval queue.

    Aggregates queue metrics for notification content.

    Attributes:
        total_pending: Total items pending approval
        by_source_type: Item counts by source type
        by_priority: Item counts by priority level
        compliance_warnings: Items with WARNING compliance status
        highest_priority_item: ID of highest priority item
    """

    total_pending: int
    by_source_type: dict[str, int]
    by_priority: dict[int, int]
    compliance_warnings: int
    highest_priority_item: Optional[str]


@dataclass
class NotificationConfig:
    """Configuration for approval notifications.

    Loaded via dependency injection from config files.

    Attributes:
        webhook_url: Discord webhook URL
        threshold: Minimum queue size to trigger notification (default: 5)
        cooldown_minutes: Minimum time between notifications (default: 60)
        dashboard_url: URL to approval dashboard for embed link
        enabled: Whether notifications are enabled
    """

    webhook_url: str
    threshold: int = 5
    cooldown_minutes: int = 60
    dashboard_url: str = "http://localhost:3000/approval"
    enabled: bool = True


class ApprovalNotifierProtocol(Protocol):
    """Protocol for approval notification service.

    Defines the interface for notification services to enable
    dependency injection and testing.
    """

    async def check_and_notify(self) -> bool:
        """Check queue state and send notification if warranted.

        Returns:
            True if notification was sent, False otherwise
        """
        ...


class ApprovalQueueRepoProtocol(Protocol):
    """Protocol for approval queue repository.

    Minimal interface needed by notification service.
    """

    async def get_pending_items(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> tuple[list, int, Optional[str]]:
        """Get pending approval items.

        Returns:
            Tuple of (items, total_count, next_cursor)
        """
        ...


class ApprovalNotificationService:
    """Service for sending approval queue notifications.

    Monitors the approval queue and sends Discord notifications
    when the queue reaches a configurable threshold. Implements
    rate limiting to prevent notification spam.

    Story 4-6 Implementation:
    - AC #1: Threshold-based notification triggering
    - AC #2: Rate limiting with 1-hour cooldown
    - AC #3: Compliance warning prioritization
    - AC #4: Non-blocking failure handling

    Attributes:
        _config: Notification configuration
        _discord: Discord webhook client (injected)
        _rate_limiter: Rate limiting service (injected)
        _queue_repo: Approval queue repository (injected)
        _notification_queue: Queue for failed notifications (injected, optional)
    """

    def __init__(
        self,
        config: NotificationConfig,
        discord_client: "DiscordClientProtocol",
        rate_limiter: "NotificationRateLimiter",
        queue_repo: ApprovalQueueRepoProtocol,
        notification_queue: Optional["NotificationQueue"] = None,
    ) -> None:
        """Initialize notification service with dependencies.

        Args:
            config: Notification configuration
            discord_client: Discord webhook client for sending notifications
            rate_limiter: Rate limiting service
            queue_repo: Repository for querying approval queue
            notification_queue: Queue for failed notification retry (optional)
        """
        self._config = config
        self._discord = discord_client
        self._rate_limiter = rate_limiter
        self._queue_repo = queue_repo
        self._notification_queue = notification_queue

    async def check_and_notify(self) -> bool:
        """Check queue state and send notification if warranted.

        Notification is sent when:
        1. Notifications are enabled
        2. Queue size >= threshold
        3. Not currently rate-limited

        Returns:
            True if notification was sent, False otherwise

        Note:
            This method never raises exceptions - failures are logged
            and return False to avoid blocking caller.
        """
        try:
            return await self._check_and_notify_internal()
        except Exception as e:
            logger.error(f"Notification check failed: {e}")
            return False

    async def _check_and_notify_internal(self) -> bool:
        """Internal notification check logic.

        Separated for cleaner exception handling.
        """
        if not self._config.enabled:
            logger.debug("Notifications disabled, skipping check")
            return False

        # Get current queue status
        status = await self._get_queue_status()

        # Check threshold
        if status.total_pending < self._config.threshold:
            logger.debug(
                f"Queue size {status.total_pending} below threshold "
                f"{self._config.threshold}, skipping notification"
            )
            return False

        # Check rate limit
        if await self._rate_limiter.is_rate_limited():
            logger.debug("Rate limited, queuing notification for later")
            await self._rate_limiter.queue_pending_notification(status)
            return False

        # Send notification
        success = await self._send_notification(status)

        if success:
            await self._rate_limiter.record_notification()
            logger.info(
                f"Sent approval notification: {status.total_pending} pending, "
                f"{status.compliance_warnings} warnings"
            )
        else:
            logger.warning("Failed to send approval notification")
            # Queue for retry (Task 5.3)
            await self._queue_failed_notification(status)

        return success

    async def _queue_failed_notification(self, status: QueueStatus) -> None:
        """Queue failed notification for later retry.

        Task 5.3: On final failure, queue notification for later retry.

        Args:
            status: Queue status when notification failed
        """
        if self._notification_queue is None:
            logger.debug("No notification queue configured, skipping retry queue")
            return

        try:
            await self._notification_queue.queue_failed(status)
            logger.info(
                f"Queued failed notification for retry: {status.total_pending} pending"
            )
        except Exception as e:
            logger.error(f"Failed to queue notification for retry: {e}")

    async def _get_queue_status(self) -> QueueStatus:
        """Get current approval queue status from repository.

        Fetches all pending items and aggregates metrics for
        notification content.

        Returns:
            QueueStatus with aggregated queue metrics
        """
        # Get all pending items (paginated fetch)
        all_items = []
        cursor = None

        while True:
            items, total_count, next_cursor = await self._queue_repo.get_pending_items(
                limit=100,
                cursor=cursor,
            )
            all_items.extend(items)
            cursor = next_cursor
            if not cursor:
                break

        # Aggregate metrics
        by_source_type: dict[str, int] = {}
        by_priority: dict[int, int] = {}
        compliance_warnings = 0
        highest_priority_item = None
        min_priority = 999

        for item in all_items:
            # Count by source type
            source = item.source_type
            by_source_type[source] = by_source_type.get(source, 0) + 1

            # Count by priority
            priority = item.source_priority
            by_priority[priority] = by_priority.get(priority, 0) + 1

            # Track highest priority item
            if priority < min_priority:
                min_priority = priority
                highest_priority_item = str(item.id)

            # Count compliance warnings
            if item.compliance_status == "WARNING":
                compliance_warnings += 1

        return QueueStatus(
            total_pending=len(all_items),
            by_source_type=by_source_type,
            by_priority=by_priority,
            compliance_warnings=compliance_warnings,
            highest_priority_item=highest_priority_item,
        )

    async def _send_notification(self, status: QueueStatus) -> bool:
        """Send Discord notification via existing client.

        Uses the DiscordWebhookClient.send_approval_notification()
        method added in Epic 4 prep.

        Args:
            status: Current queue status for notification content

        Returns:
            True if notification sent successfully, False otherwise
        """
        # Count high priority items (TRENDING = 1)
        high_priority_count = status.by_priority.get(1, 0)

        return await self._discord.send_approval_notification(
            pending_count=status.total_pending,
            high_priority_count=high_priority_count,
            compliance_warnings=status.compliance_warnings,
            dashboard_url=self._config.dashboard_url,
        )


__all__ = [
    "ApprovalNotificationService",
    "ApprovalNotifierProtocol",
    "ApprovalQueueRepoProtocol",
    "NotificationConfig",
    "QueueStatus",
]
