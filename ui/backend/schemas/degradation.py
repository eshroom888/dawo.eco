"""Pydantic schemas for degradation dashboard endpoints.

Story 7-10, Task 5.1: System status and recovery schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ServiceHealthResponse(BaseModel):
    """Single service health status."""

    service_name: str
    status: str  # "healthy", "degraded", "unhealthy"
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_error: Optional[str] = None
    queued_operations: int = 0


class SystemStatusResponse(BaseModel):
    """Aggregate system status for all monitored services."""

    overall_status: str  # worst status among all services
    services: list[ServiceHealthResponse]
    total_queued_operations: int
    last_updated: datetime


class RecoveryTriggerRequest(BaseModel):
    """Request to trigger manual recovery."""

    service_name: Optional[str] = None  # None = all services


class RecoveryResultResponse(BaseModel):
    """Result of a single service recovery attempt."""

    service_name: str
    processed: int = 0
    remaining: int = 0
    errors: list[str] = Field(default_factory=list)


class RecoveryTriggerResponse(BaseModel):
    """Response for manual recovery trigger."""

    results: list[RecoveryResultResponse]
