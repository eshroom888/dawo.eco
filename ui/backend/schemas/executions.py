"""Pydantic schemas for Execution Dashboard API.

Story 7-8, Task 7.1: Request/response schemas for execution dashboard.

Schemas:
    - ExecutionLogResponse: List view of a single execution
    - ExecutionLogDetailResponse: Detail view with log_output
    - DashboardSummaryResponse: Dashboard overview data
    - ExecutionLogListResponse: Paginated execution list
    - ExecutionFilterParams: Query parameters for filtering
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExecutionLogResponse(BaseModel):
    """Single execution log entry for list views."""

    id: str = Field(..., description="Execution log UUID")
    agent_name: str = Field(..., description="Agent that was executed")
    display_name: str = Field(..., description="Human-readable agent name")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(
        default=None, description="Execution end time (null if running)"
    )
    duration_seconds: Optional[float] = Field(
        default=None, description="Duration in seconds (null if running)"
    )
    status: str = Field(..., description="running/success/failed/incomplete")
    trigger_type: str = Field(..., description="scheduled/manual")
    triggered_by: str = Field(..., description="Who triggered the execution")
    summary: Optional[dict] = Field(default=None, description="Runner result summary")
    error_message: Optional[str] = Field(
        default=None, description="Error description on failure"
    )
    items_processed: int = Field(default=0, description="Items processed count")
    has_log_output: bool = Field(default=False, description="Whether log output exists")

    model_config = {"from_attributes": True}


class ExecutionLogDetailResponse(ExecutionLogResponse):
    """Execution detail with full log output."""

    log_output: Optional[str] = Field(
        default=None, description="Captured log output (last 1000 lines)"
    )
    error_traceback: Optional[str] = Field(
        default=None, description="Stack trace on failure"
    )


class DashboardSummaryResponse(BaseModel):
    """Dashboard overview data."""

    running: list[ExecutionLogResponse] = Field(
        ..., description="Currently running executions"
    )
    recent_completions: list[ExecutionLogResponse] = Field(
        ..., description="Recent successful completions (24h)"
    )
    recent_failures: list[ExecutionLogResponse] = Field(
        ..., description="Recent failures (7d)"
    )
    total_executions_24h: int = Field(
        ..., ge=0, description="Total executions in last 24h"
    )
    success_rate_24h: float = Field(
        ..., ge=0, le=100, description="Success rate percentage"
    )
    avg_duration_24h: Optional[float] = Field(
        default=None, description="Average duration in seconds"
    )


class ExecutionLogListResponse(BaseModel):
    """Paginated execution list."""

    executions: list[ExecutionLogResponse] = Field(
        ..., description="Execution log entries"
    )
    total_count: int = Field(..., ge=0, description="Total matching records")
    has_more: bool = Field(..., description="Whether more results exist")


class ExecutionFilterParams(BaseModel):
    """Query parameters for filtering execution logs.

    Story 7-8, Task 7.1: Filter schema for list endpoint.
    """

    agent_name: Optional[str] = Field(default=None, description="Filter by agent name")
    status: Optional[str] = Field(default=None, description="Filter by status")
    trigger_type: Optional[str] = Field(default=None, description="Filter by trigger type")
    date_from: Optional[datetime] = Field(default=None, description="Start date filter")
    date_to: Optional[datetime] = Field(default=None, description="End date filter")
    limit: int = Field(default=25, ge=1, le=100, description="Page size")
    offset: int = Field(default=0, ge=0, description="Page offset")


__all__ = [
    "DashboardSummaryResponse",
    "ExecutionFilterParams",
    "ExecutionLogDetailResponse",
    "ExecutionLogListResponse",
    "ExecutionLogResponse",
]
