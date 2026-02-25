"""Gmail Send Rate Limiter.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Token bucket rate limiter for Gmail API sends.
Enforces max 20 sends/minute and daily limits.
"""

import logging
import time
from collections import deque
from datetime import datetime, UTC

from teams.dawo.leads.gmail.config import GmailRateLimitConfig

logger = logging.getLogger(__name__)


class GmailRateLimiter:
    """Token bucket rate limiter for Gmail sends.

    Tracks send timestamps to enforce:
    - Per-minute rate limit (default: 20/min)
    - Daily send limit (default: 500/day)
    - Burst size control

    Configuration is injected via GmailRateLimitConfig.
    """

    def __init__(self, config: GmailRateLimitConfig) -> None:
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration (injected)
        """
        self._config = config
        self._send_timestamps: deque[float] = deque()
        self._daily_count: int = 0
        self._daily_reset_date: str = ""

    def acquire(self) -> bool:
        """Try to acquire a send slot.

        Returns:
            True if a slot is available, False if rate limited
        """
        now = time.monotonic()
        self._cleanup_old_timestamps(now)
        self._check_daily_reset()

        # Check daily limit
        if self._daily_count >= self._config.max_per_day:
            logger.warning("Gmail daily send limit reached")
            return False

        # Check per-minute limit
        if len(self._send_timestamps) >= self._config.max_per_minute:
            logger.debug("Gmail per-minute rate limit reached")
            return False

        # Acquire slot
        self._send_timestamps.append(now)
        self._daily_count += 1
        return True

    def wait_for_slot(self) -> float:
        """Calculate delay until next available slot.

        Returns:
            Seconds to wait (0.0 if slot available)
        """
        now = time.monotonic()
        self._cleanup_old_timestamps(now)

        if len(self._send_timestamps) < self._config.max_per_minute:
            return 0.0

        # Wait until oldest timestamp expires from the 60s window
        oldest = self._send_timestamps[0]
        wait_seconds = 60.0 - (now - oldest)
        return max(0.0, wait_seconds)

    def get_stats(self) -> dict:
        """Get rate limiter statistics.

        Returns:
            Dict with sends_last_minute, sends_today, remaining_quota
        """
        now = time.monotonic()
        self._cleanup_old_timestamps(now)
        self._check_daily_reset()

        return {
            "sends_last_minute": len(self._send_timestamps),
            "sends_today": self._daily_count,
            "remaining_daily_quota": self._config.max_per_day - self._daily_count,
            "max_per_minute": self._config.max_per_minute,
            "max_per_day": self._config.max_per_day,
        }

    def _cleanup_old_timestamps(self, now: float) -> None:
        """Remove timestamps older than 60 seconds.

        Args:
            now: Current monotonic time
        """
        cutoff = now - 60.0
        while self._send_timestamps and self._send_timestamps[0] < cutoff:
            self._send_timestamps.popleft()

    def _check_daily_reset(self) -> None:
        """Reset daily counter if date has changed."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if today != self._daily_reset_date:
            self._daily_count = 0
            self._daily_reset_date = today


__all__ = [
    "GmailRateLimiter",
]
