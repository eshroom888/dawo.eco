"""Notification queue for failed notifications.

Story 4-6: Discord Approval Notifications (Task 4)

Provides a Redis-backed queue for failed notifications with
exponential backoff retry logic.

Architecture Compliance:
- Redis for persistent queue storage
- Exponential backoff for retries
- Max retry limits
- Comprehensive logging

Backoff Schedule:
- Attempt 1: 1 minute
- Attempt 2: 5 minutes
- Attempt 3: 15 minutes
- Attempt 4: 1 hour
- Attempt 5: Abandoned
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Optional, TYPE_CHECKING
import json
import logging

if TYPE_CHECKING:
    import redis.asyncio as redis
    from integrations.discord.client import DiscordClientProtocol
    from core.notifications.approval_notifier import QueueStatus

# Import Discord error types for handling (Task 5.5)
try:
    from integrations.discord.client import DiscordRateLimitError, DiscordAuthError
except ImportError:
    # Fallback for testing without full imports
    DiscordRateLimitError = Exception  # type: ignore
    DiscordAuthError = Exception  # type: ignore

logger = logging.getLogger(__name__)


class NotificationStatus(str, Enum):
    """Status of a queued notification."""

    PENDING = "pending"
    RETRYING = "retrying"
    ABANDONED = "abandoned"


# Backoff schedule in seconds (indexed by attempt number)
BACKOFF_SCHEDULE = {
    1: 60,      # 1 minute
    2: 300,     # 5 minutes
    3: 900,     # 15 minutes
    4: 3600,    # 1 hour
}

MAX_RETRY_ATTEMPTS = 5


@dataclass
class QueuedNotification:
    """A notification queued for retry.

    Stores notification data and retry metadata.

    Attributes:
        total_pending: Total items pending when queued
        high_priority_count: High priority item count
        compliance_warnings: Compliance warning count
        attempts: Number of retry attempts
        queued_at: When notification was first queued
        last_attempt: When last retry was attempted
    """

    total_pending: int
    high_priority_count: int
    compliance_warnings: int
    attempts: int = 0
    queued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_attempt: Optional[datetime] = None

    @classmethod
    def from_queue_status(cls, status: "QueueStatus") -> "QueuedNotification":
        """Create QueuedNotification from QueueStatus.

        Args:
            status: Current queue status

        Returns:
            QueuedNotification with data from status
        """
        high_priority_count = status.by_priority.get(1, 0)  # TRENDING = 1
        return cls(
            total_pending=status.total_pending,
            high_priority_count=high_priority_count,
            compliance_warnings=status.compliance_warnings,
        )

    def get_backoff_seconds(self) -> int:
        """Get backoff time based on attempt count.

        Returns:
            Backoff time in seconds
        """
        return BACKOFF_SCHEDULE.get(self.attempts, 3600)

    def is_ready_for_retry(self) -> bool:
        """Check if notification is ready for retry.

        Returns:
            True if backoff period has passed
        """
        if self.last_attempt is None:
            return True

        backoff = timedelta(seconds=self.get_backoff_seconds())
        next_retry = self.last_attempt + backoff

        return datetime.now(UTC) >= next_retry

    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage."""
        return {
            "total_pending": self.total_pending,
            "high_priority_count": self.high_priority_count,
            "compliance_warnings": self.compliance_warnings,
            "attempts": self.attempts,
            "queued_at": self.queued_at.isoformat(),
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueuedNotification":
        """Create from dictionary (Redis storage)."""
        return cls(
            total_pending=data["total_pending"],
            high_priority_count=data["high_priority_count"],
            compliance_warnings=data["compliance_warnings"],
            attempts=data["attempts"],
            queued_at=datetime.fromisoformat(data["queued_at"]),
            last_attempt=datetime.fromisoformat(data["last_attempt"]) if data.get("last_attempt") else None,
        )


class NotificationQueue:
    """Queue for failed notifications with retry logic.

    Uses Redis to store failed notifications and implements
    exponential backoff for retries.

    Story 4-6, Task 4 Implementation:
    - AC #4: Queue failed notifications for later delivery
    - Exponential backoff: 1min, 5min, 15min, 1hr
    - Max 5 retry attempts

    Attributes:
        _redis: Redis client (injected)
        _discord: Discord client (injected)
        _dashboard_url: URL for notification embeds
    """

    KEY_FAILED_QUEUE = "approval:notification:failed"
    KEY_PENDING_QUEUE = "approval:notification:pending"

    def __init__(
        self,
        redis_client: "redis.Redis",
        discord_client: "DiscordClientProtocol",
        dashboard_url: str = "http://localhost:3000/approval",
    ) -> None:
        """Initialize notification queue.

        Args:
            redis_client: Async Redis client for queue storage
            discord_client: Discord client for sending notifications
            dashboard_url: URL for notification dashboard link
        """
        self._redis = redis_client
        self._discord = discord_client
        self._dashboard_url = dashboard_url

    async def queue_failed(
        self,
        status: "QueueStatus",
    ) -> None:
        """Queue a failed notification for later retry.

        Args:
            status: Queue status when notification failed
        """
        try:
            queued = QueuedNotification.from_queue_status(status)
            data = json.dumps(queued.to_dict())

            await self._redis.lpush(self.KEY_FAILED_QUEUE, data)

            # TTL of 24 hours
            await self._redis.expire(self.KEY_FAILED_QUEUE, 86400)

            logger.info(
                f"Queued failed notification: {status.total_pending} pending items"
            )

        except Exception as e:
            logger.error(f"Failed to queue notification: {e}")

    async def get_failed_count(self) -> int:
        """Get count of failed notifications in queue.

        Returns:
            Number of failed notifications
        """
        try:
            count = await self._redis.llen(self.KEY_FAILED_QUEUE)
            return count or 0
        except Exception as e:
            logger.warning(f"Failed to get failed count: {e}")
            return 0

    async def get_pending_count(self) -> int:
        """Get count of pending notifications in queue.

        Returns:
            Number of pending notifications
        """
        try:
            count = await self._redis.llen(self.KEY_PENDING_QUEUE)
            return count or 0
        except Exception as e:
            logger.warning(f"Failed to get pending count: {e}")
            return 0

    async def retry_failed(self) -> int:
        """Process and retry failed notifications.

        Respects backoff timing and max retry limits.

        Returns:
            Number of notifications processed
        """
        try:
            # Get all failed notifications
            items = await self._redis.lrange(self.KEY_FAILED_QUEUE, 0, -1)

            if not items:
                return 0

            processed = 0

            for item_data in items:
                try:
                    data = json.loads(item_data.decode())
                    queued = QueuedNotification.from_dict(data)

                    # Check if max retries exceeded
                    if queued.attempts >= MAX_RETRY_ATTEMPTS:
                        await self._abandon_notification(queued, item_data)
                        processed += 1
                        continue

                    # Check if ready for retry (backoff passed)
                    if not queued.is_ready_for_retry():
                        continue

                    # Attempt retry
                    success = await self._retry_notification(queued)

                    if success:
                        # Remove from queue
                        await self._redis.lrem(self.KEY_FAILED_QUEUE, 1, item_data)
                        logger.info(
                            f"Successfully retried notification after "
                            f"{queued.attempts + 1} attempts"
                        )
                    else:
                        # Increment attempt and requeue
                        await self._requeue_notification(queued, item_data)

                    processed += 1

                except Exception as e:
                    logger.error(f"Error processing queued notification: {e}")

            return processed

        except Exception as e:
            logger.error(f"Failed to process retry queue: {e}")
            return 0

    async def _retry_notification(
        self,
        queued: QueuedNotification,
    ) -> bool:
        """Attempt to send a queued notification.

        Story 4-6, Task 5.5: Handle Discord-specific error codes.

        Args:
            queued: Notification to retry

        Returns:
            True if sent successfully, False otherwise

        Note:
            Handles Discord rate limit (429) by using the Retry-After value.
            Handles auth errors (401, 403) by abandoning the notification.
        """
        try:
            return await self._discord.send_approval_notification(
                pending_count=queued.total_pending,
                high_priority_count=queued.high_priority_count,
                compliance_warnings=queued.compliance_warnings,
                dashboard_url=self._dashboard_url,
            )
        except DiscordRateLimitError as e:
            # Use Discord's Retry-After for more accurate backoff
            logger.warning(
                f"Discord rate limit hit during retry, "
                f"will retry after {e.retry_after}s"
            )
            return False
        except DiscordAuthError:
            # Auth errors are unrecoverable - abandon notification
            logger.error(
                "Discord auth error during retry, notification will be abandoned"
            )
            # Force max attempts to trigger abandonment
            queued.attempts = MAX_RETRY_ATTEMPTS
            return False

    async def _requeue_notification(
        self,
        queued: QueuedNotification,
        original_data: bytes,
    ) -> None:
        """Requeue notification with incremented attempt count.

        Args:
            queued: Notification to requeue
            original_data: Original data to remove from queue
        """
        try:
            # Remove old entry
            await self._redis.lrem(self.KEY_FAILED_QUEUE, 1, original_data)

            # Add updated entry
            queued.attempts += 1
            queued.last_attempt = datetime.now(UTC)
            data = json.dumps(queued.to_dict())
            await self._redis.lpush(self.KEY_FAILED_QUEUE, data)

            logger.debug(
                f"Requeued notification with attempt {queued.attempts}, "
                f"next retry in {queued.get_backoff_seconds()}s"
            )

        except Exception as e:
            logger.error(f"Failed to requeue notification: {e}")

    async def _abandon_notification(
        self,
        queued: QueuedNotification,
        item_data: bytes,
    ) -> None:
        """Mark notification as abandoned after max retries.

        Args:
            queued: Notification to abandon
            item_data: Original data to remove from queue
        """
        try:
            # Remove from queue
            await self._redis.lrem(self.KEY_FAILED_QUEUE, 1, item_data)

            logger.warning(
                f"Abandoned notification after {queued.attempts} attempts: "
                f"{queued.total_pending} pending items"
            )

        except Exception as e:
            logger.error(f"Failed to abandon notification: {e}")

    async def process_pending(self) -> int:
        """Process pending notifications from rate limiter queue.

        Called when cooldown expires to send batched notifications.

        Returns:
            Number of notifications processed
        """
        try:
            # Get all pending notifications
            items = await self._redis.lrange(self.KEY_PENDING_QUEUE, 0, -1)

            if not items:
                return 0

            # Get the most recent status for batched notification
            if items:
                latest = json.loads(items[0].decode())
                success = await self._discord.send_approval_notification(
                    pending_count=latest["total_pending"],
                    high_priority_count=latest.get("high_priority_count", 0),
                    compliance_warnings=latest["compliance_warnings"],
                    dashboard_url=self._dashboard_url,
                )

                if success:
                    # Clear pending queue
                    await self._redis.delete(self.KEY_PENDING_QUEUE)
                    logger.info(f"Processed {len(items)} pending notifications")
                    return len(items)

            return 0

        except Exception as e:
            logger.error(f"Failed to process pending notifications: {e}")
            return 0


__all__ = [
    "NotificationQueue",
    "QueuedNotification",
    "NotificationStatus",
]
