"""Service health registry for tracking external API status.

Story 7-10, Task 1.5: Redis-backed health tracking.

The registry records success/failure of external API calls and tracks
consecutive failure counts to determine service health status.

Status is ADVISORY only — it never blocks operations.

Usage:
    config = DegradationConfig()
    registry = ServiceHealthRegistry(config, redis_client)
    status = await registry.record_failure("instagram", "Timeout")
    all_statuses = await registry.get_all_statuses()
"""

import json
import logging
from datetime import UTC, datetime
from typing import Callable, Awaitable

from core.config import DegradationConfig
from core.degradation.models import ServiceHealthStatus

logger = logging.getLogger(__name__)

# Redis key pattern for service health data
REDIS_KEY_PREFIX = "dawo:service_health"

# Redis key for operation queues (used by OperationQueue)
OPERATION_QUEUE_PREFIX = "dawo:incomplete_operations"


class ServiceHealthRegistry:
    """Redis-backed service health registry.

    Tracks consecutive failures and determines health status for
    monitored external services. All methods are resilient to Redis
    failures — they return sensible defaults instead of raising.

    Status transitions (driven by DegradationConfig thresholds):
        0 to failure_threshold-1 failures → "healthy"
        failure_threshold to unhealthy_threshold-1 → "degraded"
        unhealthy_threshold+ → "unhealthy"

    Attributes:
        _config: DegradationConfig with thresholds
        _redis: Async Redis client
        _on_recovery: Optional callback for recovery transition events
    """

    def __init__(
        self,
        config: DegradationConfig,
        redis,
        on_recovery: Callable[[str, int], Awaitable] | None = None,
    ) -> None:
        """Initialize registry with injected config and Redis.

        Args:
            config: DegradationConfig with failure thresholds
            redis: Async Redis client (any client with get/set methods)
            on_recovery: Optional async callback(service_name, queued_count)
                called when a service transitions from degraded/unhealthy to healthy.
                Failures in the callback are logged but never block.
        """
        self._config = config
        self._redis = redis
        self._on_recovery = on_recovery

    def _redis_key(self, service_name: str) -> str:
        """Build Redis key for a service."""
        return f"{REDIS_KEY_PREFIX}:{service_name}"

    def _determine_status(self, consecutive_failures: int) -> str:
        """Determine health status from failure count.

        Args:
            consecutive_failures: Current consecutive failure count

        Returns:
            Status string: "healthy", "degraded", or "unhealthy"
        """
        if consecutive_failures >= self._config.unhealthy_threshold:
            return "unhealthy"
        elif consecutive_failures >= self._config.failure_threshold:
            return "degraded"
        return "healthy"

    def _default_status(self, service_name: str) -> ServiceHealthStatus:
        """Return default healthy status for a service."""
        return ServiceHealthStatus(
            service_name=service_name,
            status="healthy",
            consecutive_failures=0,
            updated_at=datetime.now(UTC),
        )

    async def _load_status(self, service_name: str) -> ServiceHealthStatus:
        """Load status from Redis, or return default if not found.

        Args:
            service_name: Service to load status for

        Returns:
            ServiceHealthStatus from Redis or default healthy status
        """
        raw = await self._redis.get(self._redis_key(service_name))
        if raw is None:
            return self._default_status(service_name)

        data = json.loads(raw)
        return ServiceHealthStatus(
            service_name=data["service_name"],
            status=data.get("status", "healthy"),
            consecutive_failures=data.get("consecutive_failures", 0),
            last_success=_parse_datetime(data.get("last_success")),
            last_failure=_parse_datetime(data.get("last_failure")),
            last_error=data.get("last_error"),
            queued_operations=data.get("queued_operations", 0),
            updated_at=_parse_datetime(data.get("updated_at")),
        )

    async def _save_status(self, status: ServiceHealthStatus) -> None:
        """Save status to Redis.

        Args:
            status: ServiceHealthStatus to persist
        """
        data = {
            "service_name": status.service_name,
            "status": status.status,
            "consecutive_failures": status.consecutive_failures,
            "last_success": status.last_success.isoformat() if status.last_success else None,
            "last_failure": status.last_failure.isoformat() if status.last_failure else None,
            "last_error": status.last_error,
            "queued_operations": status.queued_operations,
            "updated_at": status.updated_at.isoformat() if status.updated_at else None,
        }
        await self._redis.set(self._redis_key(status.service_name), json.dumps(data))

    async def record_success(self, service_name: str) -> ServiceHealthStatus:
        """Record a successful API call for a service.

        Resets consecutive_failures to 0 and sets status to "healthy".
        If the service was previously degraded/unhealthy, fires the
        on_recovery callback (AC5: Discord notification announces recovery).

        Args:
            service_name: Service that succeeded

        Returns:
            Updated ServiceHealthStatus
        """
        try:
            current = await self._load_status(service_name)
            now = datetime.now(UTC)

            new_status = ServiceHealthStatus(
                service_name=service_name,
                status="healthy",
                consecutive_failures=0,
                last_success=now,
                last_failure=current.last_failure,
                last_error=current.last_error,
                queued_operations=current.queued_operations,
                updated_at=now,
            )
            await self._save_status(new_status)

            # Detect recovery transition: degraded/unhealthy → healthy
            if self._on_recovery and current.status != "healthy":
                try:
                    queued = await self.get_queued_count(service_name)
                    await self._on_recovery(service_name, queued)
                except Exception as cb_err:
                    logger.warning(
                        "Recovery callback failed for %s: %s", service_name, cb_err
                    )

            return new_status

        except Exception as e:
            logger.warning("Redis failure in record_success(%s): %s", service_name, e)
            return self._default_status(service_name)

    async def record_failure(
        self, service_name: str, error: str
    ) -> ServiceHealthStatus:
        """Record a failed API call for a service.

        Increments consecutive_failures and updates status based on thresholds.

        Args:
            service_name: Service that failed
            error: Error message from the failure

        Returns:
            Updated ServiceHealthStatus
        """
        try:
            current = await self._load_status(service_name)
            now = datetime.now(UTC)

            new_failures = current.consecutive_failures + 1
            new_status_str = self._determine_status(new_failures)

            new_status = ServiceHealthStatus(
                service_name=service_name,
                status=new_status_str,
                consecutive_failures=new_failures,
                last_success=current.last_success,
                last_failure=now,
                last_error=error,
                queued_operations=current.queued_operations,
                updated_at=now,
            )
            await self._save_status(new_status)
            return new_status

        except Exception as e:
            logger.warning("Redis failure in record_failure(%s): %s", service_name, e)
            return ServiceHealthStatus(
                service_name=service_name,
                status="healthy",
                consecutive_failures=0,
                last_error=error,
                updated_at=datetime.now(UTC),
            )

    async def get_status(self, service_name: str) -> ServiceHealthStatus:
        """Get current health status for a service.

        Args:
            service_name: Service to check

        Returns:
            ServiceHealthStatus (healthy default if Redis unavailable)
        """
        try:
            return await self._load_status(service_name)
        except Exception as e:
            logger.warning("Redis failure in get_status(%s): %s", service_name, e)
            return self._default_status(service_name)

    async def get_all_statuses(self) -> list[ServiceHealthStatus]:
        """Get health status for all monitored services.

        Returns:
            List of ServiceHealthStatus for each monitored service
        """
        results = []
        for service_name in self._config.monitored_services:
            status = await self.get_status(service_name)
            results.append(status)
        return results

    async def get_queued_count(self, service_name: str) -> int:
        """Get count of pending operations for a service.

        Counts operations in the OperationQueue Redis hash that
        match this service's context pattern.

        Args:
            service_name: Service to count queued operations for

        Returns:
            Number of pending operations (0 if Redis unavailable)
        """
        try:
            count = await self._redis.hlen(f"{OPERATION_QUEUE_PREFIX}:{service_name}")
            return count
        except Exception as e:
            logger.warning("Redis failure in get_queued_count(%s): %s", service_name, e)
            return 0

    async def reset_status(self, service_name: str) -> ServiceHealthStatus:
        """Force-reset a service to healthy status.

        Admin override for manual recovery.

        Args:
            service_name: Service to reset

        Returns:
            New healthy ServiceHealthStatus
        """
        try:
            now = datetime.now(UTC)
            new_status = ServiceHealthStatus(
                service_name=service_name,
                status="healthy",
                consecutive_failures=0,
                last_success=now,
                updated_at=now,
            )
            await self._save_status(new_status)
            return new_status
        except Exception as e:
            logger.warning("Redis failure in reset_status(%s): %s", service_name, e)
            return self._default_status(service_name)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string, or return None."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
