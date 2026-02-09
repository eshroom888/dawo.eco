"""Notification rate limiter.

Story 4-6: Discord Approval Notifications (Task 2)

Uses Redis to track last notification time and enforce
cooldown period. Supports queuing pending notifications
during cooldown for batched delivery.

Architecture Compliance:
- Redis for distributed state
- Configurable cooldown period
- Pending notification batching
"""

from datetime import datetime, timedelta, UTC
from typing import Optional, TYPE_CHECKING
import json
import logging

if TYPE_CHECKING:
    import redis.asyncio as redis
    from core.notifications.approval_notifier import QueueStatus

logger = logging.getLogger(__name__)


class NotificationRateLimiter:
    """Rate limiter for approval notifications.

    Uses Redis to track last notification time and enforce
    cooldown period. Supports queuing pending notifications
    during cooldown for batched delivery.

    Story 4-6, Task 2 Implementation:
    - AC #2: 1-hour cooldown between notifications
    - Pending notification queuing for batching

    Attributes:
        _redis: Redis client (injected)
        _cooldown: Minimum time between notifications
    """

    KEY_LAST_NOTIFICATION = "approval:notification:last_sent"
    KEY_PENDING_QUEUE = "approval:notification:pending"

    def __init__(
        self,
        redis_client: "redis.Redis",
        cooldown_minutes: int = 60,
    ) -> None:
        """Initialize rate limiter with Redis client.

        Args:
            redis_client: Async Redis client for state storage
            cooldown_minutes: Minimum minutes between notifications (default: 60)
        """
        self._redis = redis_client
        self._cooldown = timedelta(minutes=cooldown_minutes)

    async def is_rate_limited(self) -> bool:
        """Check if currently in cooldown period.

        Returns:
            True if rate limited, False if notification can be sent
        """
        try:
            last_sent = await self._redis.get(self.KEY_LAST_NOTIFICATION)

            if not last_sent:
                return False

            last_sent_time = datetime.fromisoformat(last_sent.decode())
            cooldown_expires = last_sent_time + self._cooldown

            return datetime.now(UTC) < cooldown_expires

        except Exception as e:
            logger.warning(f"Rate limit check failed, allowing notification: {e}")
            return False

    async def record_notification(self) -> None:
        """Record that a notification was just sent.

        Sets the last notification timestamp in Redis with TTL.
        Clears any pending notifications since we just sent.
        """
        try:
            now = datetime.now(UTC).isoformat()

            # Set with TTL slightly longer than cooldown for cleanup
            ttl_seconds = int(self._cooldown.total_seconds()) + 60
            await self._redis.setex(
                self.KEY_LAST_NOTIFICATION,
                ttl_seconds,
                now,
            )

            # Clear pending queue since we just sent
            await self._redis.delete(self.KEY_PENDING_QUEUE)

            logger.debug(f"Recorded notification at {now}")

        except Exception as e:
            logger.error(f"Failed to record notification: {e}")

    async def queue_pending_notification(
        self,
        status: "QueueStatus",
    ) -> None:
        """Queue notification data for later batched delivery.

        During cooldown, we accumulate status updates and send
        a batched summary when cooldown expires.

        Args:
            status: Current queue status to queue
        """
        try:
            data = {
                "total_pending": status.total_pending,
                "compliance_warnings": status.compliance_warnings,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            await self._redis.lpush(
                self.KEY_PENDING_QUEUE,
                json.dumps(data),
            )

            # Expire pending queue after 24 hours
            await self._redis.expire(self.KEY_PENDING_QUEUE, 86400)

            logger.debug(
                f"Queued pending notification: {status.total_pending} items"
            )

        except Exception as e:
            logger.error(f"Failed to queue pending notification: {e}")

    async def get_time_until_available(self) -> Optional[timedelta]:
        """Get remaining cooldown time.

        Returns:
            Remaining cooldown time, or None if not rate limited
        """
        try:
            last_sent = await self._redis.get(self.KEY_LAST_NOTIFICATION)

            if not last_sent:
                return None

            last_sent_time = datetime.fromisoformat(last_sent.decode())
            cooldown_expires = last_sent_time + self._cooldown
            remaining = cooldown_expires - datetime.now(UTC)

            if remaining.total_seconds() <= 0:
                return None

            return remaining

        except Exception as e:
            logger.warning(f"Failed to get cooldown time: {e}")
            return None

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


__all__ = [
    "NotificationRateLimiter",
]
