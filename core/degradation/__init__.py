"""Graceful API degradation handling.

Story 7-10: Service health monitoring, alerting, and recovery processing.
"""

from core.degradation.alerts import DegradationAlertService
from core.degradation.models import RecoveryResult, ServiceHealthStatus
from core.degradation.recovery import RecoveryProcessor
from core.degradation.registry import ServiceHealthRegistry
from core.degradation.wiring import record_service_health

__all__ = [
    "DegradationAlertService",
    "RecoveryProcessor",
    "RecoveryResult",
    "ServiceHealthRegistry",
    "ServiceHealthStatus",
    "record_service_health",
]
