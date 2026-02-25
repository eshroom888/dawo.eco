"""Health Check API router.

Story 4-5, Task 10.3: Health check endpoints for Instagram API and publishing metrics.

Endpoints:
    GET /api/health - Overall system health
    GET /api/health/publishing - Publishing subsystem health
    GET /api/health/metrics - Publishing performance metrics
"""

import logging
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.publishing import get_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])


class PublishingHealthResponse(BaseModel):
    """Response for publishing health check.

    Story 4-5, Task 10.3: Health check response schema.
    """

    healthy: bool = Field(..., description="Overall health status")
    instagram_api_available: bool = Field(
        ..., description="Instagram API connectivity"
    )
    last_successful_publish: Optional[datetime] = Field(
        default=None, description="Timestamp of last success"
    )
    last_failed_publish: Optional[datetime] = Field(
        default=None, description="Timestamp of last failure"
    )
    consecutive_failures: int = Field(
        default=0, description="Number of consecutive failures"
    )
    success_rate: float = Field(..., description="Success rate percentage")
    avg_latency_seconds: float = Field(..., description="Average publish latency")
    quota_remaining: int = Field(..., description="Remaining API quota")

    model_config = {"from_attributes": True}


class PublishingMetricsResponse(BaseModel):
    """Response for publishing metrics.

    Story 4-5, Task 10.4: Metrics response schema.
    """

    total_attempts: int = Field(..., description="Total publish attempts")
    successful_publishes: int = Field(..., description="Successful publishes")
    failed_publishes: int = Field(..., description="Failed publishes")
    success_rate: float = Field(..., description="Success rate (0-100)")
    avg_latency_seconds: float = Field(..., description="Average latency")
    max_latency_seconds: float = Field(..., description="Maximum latency")
    min_latency_seconds: float = Field(..., description="Minimum latency")
    quota_remaining: int = Field(..., description="API quota remaining")
    quota_reset_at: Optional[datetime] = Field(
        default=None, description="When quota resets"
    )
    latency_target_seconds: float = Field(
        default=30.0, description="Target latency threshold"
    )
    success_rate_threshold: float = Field(
        default=99.0, description="Success rate threshold"
    )

    model_config = {"from_attributes": True}


class OverallHealthResponse(BaseModel):
    """Response for overall system health.

    Story 4-5, Task 10.3: Overall health response.
    Story 7-10, Task 7.1: Added degraded_services and queued_operations fields.
    """

    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    timestamp: datetime = Field(..., description="Check timestamp")
    services: dict = Field(default_factory=dict, description="Service statuses")
    degraded_services: int = Field(default=0, description="Number of degraded/unhealthy external services")
    queued_operations: int = Field(default=0, description="Total queued operations across all services")

    model_config = {"from_attributes": True}


@router.get("", response_model=OverallHealthResponse)
async def get_health() -> OverallHealthResponse:
    """Get overall system health status.

    Story 4-5, Task 10.3: Overall health check endpoint.

    Returns:
        OverallHealthResponse with system status
    """
    collector = get_metrics_collector()
    health = collector.get_health_status()

    # Determine overall status
    if health.healthy:
        status = "healthy"
    elif health.consecutive_failures > 0:
        status = "degraded"
    else:
        status = "unhealthy"

    return OverallHealthResponse(
        status=status,
        timestamp=datetime.now(UTC),
        services={
            "instagram_publishing": {
                "healthy": health.healthy,
                "instagram_api_available": health.instagram_api_available,
                "consecutive_failures": health.consecutive_failures,
            },
        },
    )


async def _get_optional_health_registry():
    """Optional dependency: returns registry or None if not configured."""
    from ui.backend.routers.degradation import get_health_registry

    try:
        return await get_health_registry()
    except NotImplementedError:
        return None


@router.get("/services")
async def get_services_health(registry=Depends(_get_optional_health_registry)):
    """Get external service health status.

    Story 7-10, Task 7.1: Alias to /api/system/status for backward compat.
    Delegates to the degradation router's system status endpoint.

    Returns:
        SystemStatusResponse from degradation module
    """
    if registry is None:
        return {"overall_status": "healthy", "services": [], "total_queued_operations": 0, "last_updated": datetime.now(UTC)}

    try:
        from ui.backend.schemas.degradation import SystemStatusResponse, ServiceHealthResponse

        statuses = await registry.get_all_statuses()

        services = []
        total_queued = 0
        for s in statuses:
            queued = await registry.get_queued_count(s.service_name)
            services.append(ServiceHealthResponse(
                service_name=s.service_name,
                status=s.status,
                consecutive_failures=s.consecutive_failures,
                last_success=s.last_success,
                last_failure=s.last_failure,
                last_error=s.last_error,
                queued_operations=queued,
            ))
            total_queued += queued

        status_values = [s.status for s in services]
        if "unhealthy" in status_values:
            overall = "unhealthy"
        elif "degraded" in status_values:
            overall = "degraded"
        else:
            overall = "healthy"

        return SystemStatusResponse(
            overall_status=overall,
            services=services,
            total_queued_operations=total_queued,
            last_updated=datetime.now(UTC),
        )
    except Exception as e:
        logger.warning("Failed to get services health: %s", e)
        return {"overall_status": "unknown", "services": [], "total_queued_operations": 0, "last_updated": datetime.now(UTC)}


@router.get("/publishing", response_model=PublishingHealthResponse)
async def get_publishing_health() -> PublishingHealthResponse:
    """Get Instagram publishing subsystem health.

    Story 4-5, Task 10.3: Publishing health check endpoint.

    Returns:
        PublishingHealthResponse with detailed health status
    """
    collector = get_metrics_collector()
    health = collector.get_health_status()
    metrics = collector.get_metrics()

    logger.debug(
        "Publishing health check: healthy=%s, success_rate=%.1f%%",
        health.healthy,
        metrics.success_rate,
    )

    return PublishingHealthResponse(
        healthy=health.healthy,
        instagram_api_available=health.instagram_api_available,
        last_successful_publish=health.last_successful_publish,
        last_failed_publish=health.last_failed_publish,
        consecutive_failures=health.consecutive_failures,
        success_rate=metrics.success_rate,
        avg_latency_seconds=metrics.avg_latency_seconds,
        quota_remaining=metrics.quota_remaining,
    )


@router.get("/metrics", response_model=PublishingMetricsResponse)
async def get_publishing_metrics() -> PublishingMetricsResponse:
    """Get detailed publishing performance metrics.

    Story 4-5, Task 10.4: Metrics endpoint.

    Returns:
        PublishingMetricsResponse with all metrics
    """
    collector = get_metrics_collector()
    metrics = collector.get_metrics()

    logger.debug(
        "Publishing metrics: attempts=%d, success_rate=%.1f%%, avg_latency=%.2fs",
        metrics.total_attempts,
        metrics.success_rate,
        metrics.avg_latency_seconds,
    )

    return PublishingMetricsResponse(
        total_attempts=metrics.total_attempts,
        successful_publishes=metrics.successful_publishes,
        failed_publishes=metrics.failed_publishes,
        success_rate=metrics.success_rate,
        avg_latency_seconds=metrics.avg_latency_seconds,
        max_latency_seconds=metrics.max_latency_seconds,
        min_latency_seconds=metrics.min_latency_seconds,
        quota_remaining=metrics.quota_remaining,
        quota_reset_at=metrics.quota_reset_at,
        latency_target_seconds=collector.LATENCY_TARGET_SECONDS,
        success_rate_threshold=collector.SUCCESS_RATE_THRESHOLD,
    )


__all__ = [
    "router",
    "PublishingHealthResponse",
    "PublishingMetricsResponse",
    "OverallHealthResponse",
]
