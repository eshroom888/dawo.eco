"""Pydantic schemas for Agent Schedule API.

Story 7-6, Task 7.1: Request/response schemas for schedule management.

Schemas:
    - AgentScheduleResponse: Schedule details for API responses
    - AgentScheduleListResponse: List with total count
    - ScheduleUpdateRequestSchema: Partial update fields
    - ToggleEnabledRequest: Enable/disable toggle
    - ScheduleUpdateResponse: Updated schedule with dependency warnings
    - DependencyWarningResponse: Warning details
    - ScheduleChangeLogResponse: Audit trail entry
    - AuditLogResponse: List of audit entries
    - SeedResponse: Seed result count
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentScheduleResponse(BaseModel):
    """Agent schedule for API responses."""

    id: str = Field(..., description="Schedule UUID")
    agent_name: str = Field(..., description="Unique agent identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None, description="Agent description")
    schedule_cron: str = Field(..., description="5-field cron expression")
    cron_human_readable: str = Field(..., description="Human-readable cron")
    timezone: str = Field(..., description="IANA timezone")
    enabled: bool = Field(..., description="Whether schedule is active")
    last_run_at: Optional[datetime] = Field(default=None, description="Last execution time")
    last_run_status: Optional[str] = Field(default=None, description="Last run result")
    last_run_duration_seconds: Optional[float] = Field(
        default=None, description="Last run duration"
    )
    next_run_at: Optional[datetime] = Field(default=None, description="Next execution time")
    dependencies: list[str] = Field(default_factory=list, description="Dependency agent names")
    config_source: Optional[str] = Field(default=None, description="Origin config file")

    model_config = {"from_attributes": True}


class AgentScheduleListResponse(BaseModel):
    """List of agent schedules with total count."""

    schedules: list[AgentScheduleResponse] = Field(..., description="Schedule entries")
    total_count: int = Field(..., ge=0, description="Total schedules")


class ScheduleUpdateRequestSchema(BaseModel):
    """Request body for updating an agent schedule."""

    schedule_cron: Optional[str] = Field(default=None, description="New cron expression")
    timezone: Optional[str] = Field(default=None, description="New timezone")
    enabled: Optional[bool] = Field(default=None, description="New enabled state")
    display_name: Optional[str] = Field(default=None, description="New display name")
    description: Optional[str] = Field(default=None, description="New description")
    dependencies: Optional[list[str]] = Field(
        default=None, description="New dependency list"
    )


class ToggleEnabledRequest(BaseModel):
    """Request body for toggling schedule enabled state."""

    enabled: bool = Field(..., description="New enabled state")


class DependencyWarningResponse(BaseModel):
    """Dependency conflict warning."""

    agent_name: str = Field(..., description="Agent being scheduled")
    dependency_name: str = Field(..., description="Conflicting dependency")
    agent_next_run: Optional[datetime] = Field(default=None, description="Agent next run")
    dependency_next_run: Optional[datetime] = Field(
        default=None, description="Dependency next run"
    )
    warning_message: str = Field(..., description="Human-readable warning")
    severity: str = Field(..., description="warning or critical")


class ScheduleUpdateResponse(BaseModel):
    """Response after updating a schedule, includes dependency warnings."""

    schedule: AgentScheduleResponse = Field(..., description="Updated schedule")
    warnings: list[DependencyWarningResponse] = Field(
        default_factory=list, description="Dependency warnings"
    )


class ScheduleChangeLogResponse(BaseModel):
    """Audit trail entry."""

    id: str = Field(..., description="Log entry UUID")
    agent_name: str = Field(..., description="Agent name")
    field_changed: str = Field(..., description="Changed field name")
    old_value: Optional[str] = Field(default=None, description="Previous value")
    new_value: str = Field(..., description="New value")
    changed_by: str = Field(..., description="Who made the change")
    created_at: Optional[datetime] = Field(default=None, description="When the change was made")


class AuditLogResponse(BaseModel):
    """List of audit trail entries."""

    entries: list[ScheduleChangeLogResponse] = Field(
        ..., description="Audit log entries"
    )


class SeedResponse(BaseModel):
    """Result of seeding default schedules."""

    seeded_count: int = Field(..., ge=0, description="Number of schedules seeded")


__all__ = [
    "AgentScheduleListResponse",
    "AgentScheduleResponse",
    "AuditLogResponse",
    "DependencyWarningResponse",
    "ScheduleChangeLogResponse",
    "ScheduleUpdateRequestSchema",
    "ScheduleUpdateResponse",
    "SeedResponse",
    "ToggleEnabledRequest",
]
