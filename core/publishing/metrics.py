"""Publishing Metrics and Monitoring.

Story 4-5, Task 10: Performance & Monitoring

This module provides metrics collection and monitoring for the
Instagram publishing pipeline. Tracks:
- Publish success/failure rates
- Latency metrics (target < 30s)
- API quota usage (200 calls/hour limit)
- Health check functionality

Architecture Compliance:
- Thread-safe counters for concurrent access
- In-memory metrics with optional persistence hooks
- Health check protocol for dependency injection
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from threading import Lock
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class PublishMetrics:
    """Snapshot of publishing metrics.

    Story 4-5, Task 10.4: Success rate metrics.

    Attributes:
        total_attempts: Total publish attempts
        successful_publishes: Number of successful publishes
        failed_publishes: Number of failed publishes
        success_rate: Success rate as percentage (0-100)
        avg_latency_seconds: Average publish latency
        max_latency_seconds: Maximum observed latency
        min_latency_seconds: Minimum observed latency
        quota_remaining: Remaining API quota for current hour
        quota_reset_at: When quota resets
    """

    total_attempts: int = 0
    successful_publishes: int = 0
    failed_publishes: int = 0
    success_rate: float = 100.0
    avg_latency_seconds: float = 0.0
    max_latency_seconds: float = 0.0
    min_latency_seconds: float = 0.0
    quota_remaining: int = 200
    quota_reset_at: Optional[datetime] = None


@dataclass
class HealthStatus:
    """Health check status result.

    Story 4-5, Task 10.3: Health check for Instagram API.

    Attributes:
        healthy: Whether the service is healthy
        instagram_api_available: Instagram API connectivity status
        last_successful_publish: Timestamp of last successful publish
        last_failed_publish: Timestamp of last failed publish
        consecutive_failures: Number of consecutive failures
        details: Additional status details
    """

    healthy: bool = True
    instagram_api_available: bool = True
    last_successful_publish: Optional[datetime] = None
    last_failed_publish: Optional[datetime] = None
    consecutive_failures: int = 0
    details: dict = field(default_factory=dict)


@runtime_checkable
class PublishMetricsCollectorProtocol(Protocol):
    """Protocol for publish metrics collection.

    Story 4-5, Task 10: Protocol for dependency injection.
    """

    def record_publish_attempt(
        self,
        success: bool,
        latency_seconds: float,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a publish attempt with outcome and timing."""
        ...

    def get_metrics(self) -> PublishMetrics:
        """Get current metrics snapshot."""
        ...

    def get_health_status(self) -> HealthStatus:
        """Get current health status."""
        ...


class PublishMetricsCollector:
    """Collects and aggregates publishing metrics.

    Story 4-5, Task 10: Performance & Monitoring

    Thread-safe metrics collection for Instagram publishing.
    Maintains sliding window of recent operations for accurate
    success rate calculation.

    Attributes:
        LATENCY_TARGET_SECONDS: Target latency (30s per story)
        QUOTA_LIMIT_PER_HOUR: Instagram API quota limit (200)
        SUCCESS_RATE_THRESHOLD: Minimum acceptable success rate (99%)
        WINDOW_SIZE: Number of recent operations to track (1000)
        FAILURE_THRESHOLD: Consecutive failures before unhealthy (3)
    """

    LATENCY_TARGET_SECONDS = 30.0
    QUOTA_LIMIT_PER_HOUR = 200
    SUCCESS_RATE_THRESHOLD = 99.0
    WINDOW_SIZE = 1000
    FAILURE_THRESHOLD = 3

    def __init__(self) -> None:
        """Initialize metrics collector.

        Story 4-5, Task 10.1: Initialize timing metrics.
        """
        self._lock = Lock()

        # Counters
        self._total_attempts = 0
        self._successful_publishes = 0
        self._failed_publishes = 0

        # Latency tracking
        self._latencies: deque[float] = deque(maxlen=self.WINDOW_SIZE)

        # Sliding window for recent success/failure
        self._recent_outcomes: deque[bool] = deque(maxlen=self.WINDOW_SIZE)

        # Timestamps
        self._last_successful_publish: Optional[datetime] = None
        self._last_failed_publish: Optional[datetime] = None

        # Consecutive failure tracking
        self._consecutive_failures = 0

        # API quota tracking (Story 4-5, Task 10.6)
        self._quota_window_start: datetime = datetime.now(UTC)
        self._quota_calls_in_window = 0

        # Health status
        self._instagram_api_available = True

        logger.info("PublishMetricsCollector initialized")

    def record_publish_attempt(
        self,
        success: bool,
        latency_seconds: float,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a publish attempt.

        Story 4-5, Task 10.1-10.2: Record timing metrics and latency.

        Args:
            success: Whether the publish succeeded
            latency_seconds: Time taken for the operation
            error_message: Error message if failed
        """
        with self._lock:
            now = datetime.now(UTC)

            # Update counters
            self._total_attempts += 1
            self._recent_outcomes.append(success)
            self._latencies.append(latency_seconds)

            if success:
                self._successful_publishes += 1
                self._last_successful_publish = now
                self._consecutive_failures = 0
                logger.debug(
                    "Recorded successful publish: latency=%.2fs",
                    latency_seconds,
                )
            else:
                self._failed_publishes += 1
                self._last_failed_publish = now
                self._consecutive_failures += 1
                logger.warning(
                    "Recorded failed publish: latency=%.2fs, error=%s, "
                    "consecutive_failures=%d",
                    latency_seconds,
                    error_message,
                    self._consecutive_failures,
                )

            # Update quota tracking
            self._record_quota_usage()

            # Story 4-5, Task 10.2: Log latency warnings
            if latency_seconds > self.LATENCY_TARGET_SECONDS:
                logger.warning(
                    "Publish latency %.2fs exceeds target of %.2fs",
                    latency_seconds,
                    self.LATENCY_TARGET_SECONDS,
                )

            # Story 4-5, Task 10.5: Check success rate threshold
            self._check_success_rate_alert()

    def _record_quota_usage(self) -> None:
        """Track API quota usage.

        Story 4-5, Task 10.6: Track API quota (200 calls/hour).
        """
        now = datetime.now(UTC)

        # Reset window if hour has passed
        if now - self._quota_window_start >= timedelta(hours=1):
            self._quota_window_start = now
            self._quota_calls_in_window = 0
            logger.debug("Quota window reset")

        self._quota_calls_in_window += 1

        # Warn if approaching limit
        remaining = self.QUOTA_LIMIT_PER_HOUR - self._quota_calls_in_window
        if remaining <= 20:
            logger.warning(
                "Instagram API quota low: %d/%d calls remaining",
                remaining,
                self.QUOTA_LIMIT_PER_HOUR,
            )

    def _check_success_rate_alert(self) -> None:
        """Check if success rate has dropped below threshold.

        Story 4-5, Task 10.5: Alert if success rate drops below threshold.
        """
        if len(self._recent_outcomes) < 10:
            # Not enough data for reliable rate
            return

        successes = sum(1 for outcome in self._recent_outcomes if outcome)
        rate = (successes / len(self._recent_outcomes)) * 100

        if rate < self.SUCCESS_RATE_THRESHOLD:
            logger.error(
                "SUCCESS RATE ALERT: Publishing success rate %.1f%% "
                "is below threshold %.1f%% (window: %d operations)",
                rate,
                self.SUCCESS_RATE_THRESHOLD,
                len(self._recent_outcomes),
            )

    def get_metrics(self) -> PublishMetrics:
        """Get current metrics snapshot.

        Story 4-5, Task 10.4: Create publish success rate metric.

        Returns:
            PublishMetrics with current values
        """
        with self._lock:
            # Calculate success rate from sliding window
            if self._recent_outcomes:
                successes = sum(1 for o in self._recent_outcomes if o)
                success_rate = (successes / len(self._recent_outcomes)) * 100
            else:
                success_rate = 100.0

            # Calculate latency stats
            if self._latencies:
                avg_latency = sum(self._latencies) / len(self._latencies)
                max_latency = max(self._latencies)
                min_latency = min(self._latencies)
            else:
                avg_latency = 0.0
                max_latency = 0.0
                min_latency = 0.0

            # Calculate quota remaining
            quota_remaining = max(
                0,
                self.QUOTA_LIMIT_PER_HOUR - self._quota_calls_in_window,
            )
            quota_reset_at = self._quota_window_start + timedelta(hours=1)

            return PublishMetrics(
                total_attempts=self._total_attempts,
                successful_publishes=self._successful_publishes,
                failed_publishes=self._failed_publishes,
                success_rate=round(success_rate, 2),
                avg_latency_seconds=round(avg_latency, 3),
                max_latency_seconds=round(max_latency, 3),
                min_latency_seconds=round(min_latency, 3),
                quota_remaining=quota_remaining,
                quota_reset_at=quota_reset_at,
            )

    def get_health_status(self) -> HealthStatus:
        """Get current health status.

        Story 4-5, Task 10.3: Health check for Instagram API.

        Health is determined by:
        - Consecutive failure count (< FAILURE_THRESHOLD)
        - Instagram API availability flag
        - Recent success rate

        Returns:
            HealthStatus with current state
        """
        with self._lock:
            metrics = self.get_metrics()

            # Determine overall health
            healthy = (
                self._consecutive_failures < self.FAILURE_THRESHOLD
                and self._instagram_api_available
                and metrics.success_rate >= 90.0  # Lower threshold for health
            )

            return HealthStatus(
                healthy=healthy,
                instagram_api_available=self._instagram_api_available,
                last_successful_publish=self._last_successful_publish,
                last_failed_publish=self._last_failed_publish,
                consecutive_failures=self._consecutive_failures,
                details={
                    "success_rate": metrics.success_rate,
                    "avg_latency_seconds": metrics.avg_latency_seconds,
                    "quota_remaining": metrics.quota_remaining,
                    "latency_target_seconds": self.LATENCY_TARGET_SECONDS,
                    "success_rate_threshold": self.SUCCESS_RATE_THRESHOLD,
                },
            )

    def set_instagram_api_available(self, available: bool) -> None:
        """Update Instagram API availability status.

        Story 4-5, Task 10.3: Health check updates.

        Args:
            available: Whether API is reachable
        """
        with self._lock:
            if self._instagram_api_available != available:
                logger.info(
                    "Instagram API availability changed: %s -> %s",
                    self._instagram_api_available,
                    available,
                )
                self._instagram_api_available = available

    def reset(self) -> None:
        """Reset all metrics.

        Primarily for testing purposes.
        """
        with self._lock:
            self._total_attempts = 0
            self._successful_publishes = 0
            self._failed_publishes = 0
            self._latencies.clear()
            self._recent_outcomes.clear()
            self._last_successful_publish = None
            self._last_failed_publish = None
            self._consecutive_failures = 0
            self._quota_window_start = datetime.now(UTC)
            self._quota_calls_in_window = 0
            self._instagram_api_available = True
            logger.info("Metrics collector reset")


# Singleton instance for global access
_metrics_collector: Optional[PublishMetricsCollector] = None
_metrics_lock = Lock()


def get_metrics_collector() -> PublishMetricsCollector:
    """Get the global metrics collector instance.

    Thread-safe singleton accessor.

    Returns:
        PublishMetricsCollector singleton instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        with _metrics_lock:
            if _metrics_collector is None:
                _metrics_collector = PublishMetricsCollector()
    return _metrics_collector


__all__ = [
    "PublishMetrics",
    "HealthStatus",
    "PublishMetricsCollector",
    "PublishMetricsCollectorProtocol",
    "get_metrics_collector",
]
