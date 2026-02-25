"""Degradation data models.

Story 7-10, Task 1.2/4.2: Frozen dataclasses for service health tracking.

Models:
    ServiceHealthStatus: Current health state of a monitored service
    RecoveryResult: Result of a recovery processing attempt
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ServiceHealthStatus:
    """Current health state of a monitored external service.

    Attributes:
        service_name: Service identifier (e.g., "instagram", "shopify")
        status: Health status ("healthy", "degraded", "unhealthy")
        consecutive_failures: Number of consecutive failures
        last_success: Timestamp of last successful API call
        last_failure: Timestamp of last failed API call
        last_error: Error message from last failure
        queued_operations: Number of pending operations for this service
        updated_at: When this status was last updated
    """

    service_name: str
    status: str = "healthy"
    consecutive_failures: int = 0
    last_success: datetime | None = None
    last_failure: datetime | None = None
    last_error: str | None = None
    queued_operations: int = 0
    updated_at: datetime | None = None


@dataclass(frozen=True)
class RecoveryResult:
    """Result of a recovery processing attempt for a service.

    Story 7-10, Task 4.2.

    Attributes:
        service_name: Service that was recovered
        processed: Number of operations successfully re-enqueued
        remaining: Number of operations still pending
        errors: Error messages from failed re-enqueue attempts
    """

    service_name: str
    processed: int = 0
    remaining: int = 0
    errors: list[str] = field(default_factory=list)
