"""Orshot usage tracking for monthly render limits.

Tracks monthly render usage against the Starter tier limits:
- 3,000 renders/month
- Alert at 80% (2,400 renders)
- Hard stop at 100% (3,000 renders)

Architecture Compliance:
- Redis client injected via constructor
- Discord alerts via injected client
- Configuration via constructor parameters
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class RedisClientProtocol(Protocol):
    """Protocol for Redis client interface."""

    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        ...

    async def incr(self, key: str) -> int:
        """Increment key value."""
        ...

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration."""
        ...

    async def exists(self, key: str) -> int:
        """Check if key exists (returns count)."""
        ...

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key value with optional expiration."""
        ...


@runtime_checkable
class DiscordAlertProtocol(Protocol):
    """Protocol for Discord alert client."""

    async def send_webhook(self, message: str) -> bool:
        """Send a message via webhook."""
        ...


class OrshotUsageTracker:
    """Track monthly Orshot render usage.

    Persists usage count to Redis with monthly keys.
    Sends Discord alerts when usage reaches warning threshold.

    Attributes:
        MONTHLY_LIMIT: Maximum renders per month (3000 for Starter tier)
        WARNING_THRESHOLD: Percentage for warning alert (0.80 = 80%)
        KEY_PREFIX: Redis key prefix for usage tracking
    """

    MONTHLY_LIMIT = 3000
    WARNING_THRESHOLD = 0.80
    KEY_PREFIX = "orshot:usage"
    ALERT_KEY_PREFIX = "orshot:alert"

    def __init__(
        self,
        redis_client: RedisClientProtocol,
        discord_client: Optional[DiscordAlertProtocol] = None,
        monthly_limit: Optional[int] = None,
        warning_threshold: Optional[float] = None,
    ) -> None:
        """Initialize usage tracker.

        Args:
            redis_client: Async Redis client for persistence
            discord_client: Optional Discord client for alerts
            monthly_limit: Override default monthly limit (for testing)
            warning_threshold: Override default warning threshold (for testing)
        """
        self._redis = redis_client
        self._discord = discord_client
        self._monthly_limit = monthly_limit or self.MONTHLY_LIMIT
        self._warning_threshold = warning_threshold or self.WARNING_THRESHOLD

    def _get_monthly_key(self) -> str:
        """Get Redis key for current month.

        Returns:
            Key in format: orshot:usage:2026-02
        """
        return f"{self.KEY_PREFIX}:{datetime.now(timezone.utc):%Y-%m}"

    def _get_alert_key(self) -> str:
        """Get Redis key for monthly alert tracking.

        Returns:
            Key in format: orshot:alert:2026-02
        """
        return f"{self.ALERT_KEY_PREFIX}:{datetime.now(timezone.utc):%Y-%m}"

    async def get_usage(self) -> int:
        """Get current month's render count.

        Returns:
            Current usage count, 0 if not set
        """
        key = self._get_monthly_key()
        try:
            count = await self._redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error("Failed to get usage count: %s", e)
            return 0

    async def can_render(self) -> bool:
        """Check if rendering is allowed within usage limits.

        Returns:
            True if under monthly limit, False if limit reached
        """
        current = await self.get_usage()
        can_render = current < self._monthly_limit

        if not can_render:
            logger.warning(
                "Orshot monthly limit reached: %d/%d",
                current,
                self._monthly_limit,
            )

        return can_render

    async def increment(self) -> tuple[int, bool, bool]:
        """Increment usage count and check thresholds.

        Returns:
            Tuple of (new_count, is_warning, is_limit_reached)
        """
        key = self._get_monthly_key()

        try:
            count = await self._redis.incr(key)

            # Set expiry to 45 days on first increment (handle month rollover)
            if count == 1:
                await self._redis.expire(key, 45 * 24 * 60 * 60)

            warning_count = int(self._monthly_limit * self._warning_threshold)
            is_warning = count >= warning_count
            is_limit = count >= self._monthly_limit

            # Log usage milestones
            if count % 500 == 0:
                logger.info(
                    "Orshot usage milestone: %d/%d (%.1f%%)",
                    count,
                    self._monthly_limit,
                    (count / self._monthly_limit) * 100,
                )

            # Send alert if just crossed warning threshold
            if is_warning and count == warning_count:
                await self._send_warning_alert(count)

            return count, is_warning, is_limit

        except Exception as e:
            logger.error("Failed to increment usage: %s", e)
            # Return safe defaults - allow render but report error
            return 0, False, False

    async def _send_warning_alert(self, count: int) -> None:
        """Send Discord alert for usage warning.

        Only sends once per month (tracked via Redis key).

        Args:
            count: Current render count
        """
        if not self._discord:
            logger.debug("No Discord client configured, skipping alert")
            return

        alert_key = self._get_alert_key()

        try:
            # Check if alert already sent this month
            if await self._redis.exists(alert_key):
                logger.debug("Usage warning alert already sent this month")
                return

            # Format and send alert
            percentage = (count / self._monthly_limit) * 100
            message = f"""⚠️ **Orshot Usage Warning**

• **Current Usage:** {count:,}/{self._monthly_limit:,} renders ({percentage:.0f}%)
• **Threshold:** {self._warning_threshold * 100:.0f}% warning level
• **Action:** Consider upgrading tier or reducing render volume

---
_DAWO Orshot Usage Tracker_"""

            await self._discord.send_webhook(message)

            # Mark alert as sent (expires in 45 days)
            await self._redis.set(alert_key, "1", ex=45 * 24 * 60 * 60)
            logger.info("Sent Orshot usage warning alert: %d renders", count)

        except Exception as e:
            # Graceful degradation - don't fail for alert errors
            logger.warning("Failed to send usage warning alert: %s", e)

    async def get_remaining(self) -> int:
        """Get remaining renders for current month.

        Returns:
            Number of renders remaining
        """
        current = await self.get_usage()
        return max(0, self._monthly_limit - current)

    async def get_percentage(self) -> float:
        """Get current usage as percentage.

        Returns:
            Usage percentage (0.0 to 100.0+)
        """
        current = await self.get_usage()
        return (current / self._monthly_limit) * 100
