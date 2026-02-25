"""Degradation dashboard API endpoints.

Story 7-10, Task 5.2: System status and recovery endpoints.

Endpoints:
    GET  /api/system/status              — Overall system status
    GET  /api/system/status/{service}    — Single service health
    POST /api/system/recover             — Manual recovery trigger
    POST /api/system/reset/{service}     — Manual health reset
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from ui.backend.schemas.degradation import (
    RecoveryResultResponse,
    RecoveryTriggerRequest,
    RecoveryTriggerResponse,
    ServiceHealthResponse,
    SystemStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

# Status severity ordering for "worst status" computation
_STATUS_SEVERITY = {"healthy": 0, "degraded": 1, "unhealthy": 2}


def _worst_status(statuses: list[str]) -> str:
    """Compute the worst status from a list."""
    if not statuses:
        return "healthy"
    return max(statuses, key=lambda s: _STATUS_SEVERITY.get(s, 0))


async def get_health_registry():
    """Dependency: ServiceHealthRegistry.

    Overridden in tests via app.dependency_overrides.
    In production, wired by app startup.
    """
    raise NotImplementedError("ServiceHealthRegistry not configured")


async def get_recovery_processor():
    """Dependency: RecoveryProcessor.

    Overridden in tests via app.dependency_overrides.
    In production, wired by app startup.
    """
    raise NotImplementedError("RecoveryProcessor not configured")


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    registry=Depends(get_health_registry),
) -> SystemStatusResponse:
    """Get aggregate system status for all monitored services.

    Returns overall status (worst among all services) and per-service details.
    """
    statuses = await registry.get_all_statuses()

    services = []
    total_queued = 0

    for s in statuses:
        queued = await registry.get_queued_count(s.service_name)
        services.append(
            ServiceHealthResponse(
                service_name=s.service_name,
                status=s.status,
                consecutive_failures=s.consecutive_failures,
                last_success=s.last_success,
                last_failure=s.last_failure,
                last_error=s.last_error,
                queued_operations=queued,
            )
        )
        total_queued += queued

    overall = _worst_status([s.status for s in services])

    return SystemStatusResponse(
        overall_status=overall,
        services=services,
        total_queued_operations=total_queued,
        last_updated=datetime.now(UTC),
    )


@router.get("/status/{service_name}", response_model=ServiceHealthResponse)
async def get_service_status(
    service_name: str,
    registry=Depends(get_health_registry),
) -> ServiceHealthResponse:
    """Get health status for a single service.

    Returns 404 if service_name is not in monitored services.
    """
    from core.config import get_config

    config = get_config().degradation
    if service_name not in config.monitored_services:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' is not monitored")

    status = await registry.get_status(service_name)
    queued = await registry.get_queued_count(service_name)

    return ServiceHealthResponse(
        service_name=status.service_name,
        status=status.status,
        consecutive_failures=status.consecutive_failures,
        last_success=status.last_success,
        last_failure=status.last_failure,
        last_error=status.last_error,
        queued_operations=queued,
    )


@router.post("/recover", response_model=RecoveryTriggerResponse)
async def trigger_recovery(
    request: RecoveryTriggerRequest,
    processor=Depends(get_recovery_processor),
) -> RecoveryTriggerResponse:
    """Manually trigger recovery processing.

    If service_name is provided, recover only that service.
    Otherwise, recover all monitored services.
    """
    if request.service_name:
        result = await processor.check_and_recover(request.service_name)
        results = [result]
    else:
        results = await processor.process_all_services()

    return RecoveryTriggerResponse(
        results=[
            RecoveryResultResponse(
                service_name=r.service_name,
                processed=r.processed,
                remaining=r.remaining,
                errors=r.errors,
            )
            for r in results
        ]
    )


@router.post("/reset/{service_name}", response_model=ServiceHealthResponse)
async def reset_service_status(
    service_name: str,
    registry=Depends(get_health_registry),
) -> ServiceHealthResponse:
    """Force-reset a service to healthy status.

    Admin override for manual recovery when operator knows API is back.
    Returns 404 if service_name is not in monitored services.
    """
    from core.config import get_config

    config = get_config().degradation
    if service_name not in config.monitored_services:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' is not monitored")

    status = await registry.reset_status(service_name)

    return ServiceHealthResponse(
        service_name=status.service_name,
        status=status.status,
        consecutive_failures=status.consecutive_failures,
        last_success=status.last_success,
        queued_operations=0,
    )
