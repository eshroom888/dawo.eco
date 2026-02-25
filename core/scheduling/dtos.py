"""Data Transfer Objects for agent scheduling.

Story 7-6, Task 4.2: Frozen dataclasses for schedule DTOs.
Story 7-7, Task 2.1: Trigger DTOs for manual agent/team triggering.
Story 7-8, Task 2.1: Execution log DTOs for dashboard.

Usage:
    from core.scheduling.dtos import AgentScheduleDTO, ScheduleUpdateRequest, DependencyWarning
    from core.scheduling.dtos import TriggerResult, TeamTriggerResult, TriggerableAgentDTO, TeamDTO
    from core.scheduling.dtos import ExecutionLogDTO, ExecutionLogDetailDTO, DashboardSummaryDTO, ExecutionLogFilterDTO
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class AgentScheduleDTO:
    """Agent schedule with computed fields for API responses.

    Attributes:
        id: Schedule UUID
        agent_name: Unique agent identifier
        display_name: Human-readable agent name
        description: Agent description
        schedule_cron: 5-field cron expression
        cron_human_readable: Human-readable cron description
        timezone: IANA timezone
        enabled: Whether schedule is active
        last_run_at: When agent last executed
        last_run_status: Result of last execution
        last_run_duration_seconds: Duration of last run
        next_run_at: Computed next execution time
        dependencies: List of dependency agent names
        config_source: Origin config file
    """

    id: UUID
    agent_name: str
    display_name: str
    description: Optional[str]
    schedule_cron: str
    cron_human_readable: str
    timezone: str
    enabled: bool
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    last_run_duration_seconds: Optional[float]
    next_run_at: Optional[datetime]
    dependencies: list[str]
    config_source: Optional[str]


@dataclass(frozen=True)
class ScheduleUpdateRequest:
    """Request to update an agent's schedule.

    All fields optional — only provided fields are updated.

    Attributes:
        schedule_cron: New cron expression
        timezone: New timezone
        enabled: New enabled state
        display_name: New display name
        description: New description
        dependencies: New dependency list
    """

    schedule_cron: Optional[str] = None
    timezone: Optional[str] = None
    enabled: Optional[bool] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    dependencies: Optional[list[str]] = None


@dataclass(frozen=True)
class DependencyWarning:
    """Warning about scheduling conflicts with dependencies.

    Attributes:
        agent_name: The agent being scheduled
        dependency_name: The dependency that may conflict
        agent_next_run: Next run of the agent
        dependency_next_run: Next run of the dependency
        warning_message: Human-readable warning
        severity: "warning" or "critical"
    """

    agent_name: str
    dependency_name: str
    agent_next_run: Optional[datetime]
    dependency_next_run: Optional[datetime]
    warning_message: str
    severity: str  # "warning" or "critical"


@dataclass(frozen=True)
class ScheduleChangeLogDTO:
    """Audit trail entry for schedule changes.

    Attributes:
        id: Log entry UUID
        agent_name: Which agent's schedule was changed
        field_changed: Name of the modified field
        old_value: Previous value
        new_value: New value after change
        changed_by: Who made the change
        created_at: When the change occurred
    """

    id: str
    agent_name: str
    field_changed: str
    old_value: Optional[str]
    new_value: str
    changed_by: str
    created_at: Optional[datetime]


@dataclass(frozen=True)
class TriggerResult:
    """Result of a manual agent trigger request.

    Story 7-7, Task 2.1: Frozen dataclass for trigger responses.

    Attributes:
        agent_name: Agent that was triggered
        status: Outcome — "queued", "already_running", "failed", "not_found"
        job_id: ARQ job ID once enqueued (set by router, not service)
        triggered_at: When the trigger was requested
        triggered_by: Who triggered ("operator" default)
        config_overrides: Optional runtime config overrides
        message: Human-readable status message
    """

    agent_name: str
    status: str
    job_id: Optional[str]
    triggered_at: datetime
    triggered_by: str
    config_overrides: Optional[dict] = None
    message: str = ""


@dataclass(frozen=True)
class TeamTriggerResult:
    """Aggregated result of triggering a team of agents.

    Story 7-7, Task 2.1: Frozen dataclass for team trigger responses.

    Attributes:
        team_name: Team that was triggered
        agent_results: Per-agent TriggerResult list
        total: Total agents in team
        queued: How many were queued
        skipped_running: How many were already running
        failed: How many failed to trigger
    """

    team_name: str
    agent_results: list[TriggerResult]
    total: int
    queued: int
    skipped_running: int
    failed: int


@dataclass(frozen=True)
class TriggerableAgentDTO:
    """Agent available for manual triggering with current status.

    Story 7-7, Task 2.1: Enriched agent info from registry + schedule DB.

    Attributes:
        agent_name: Unique agent identifier
        display_name: Human-readable name
        description: Agent description
        last_run_status: Last execution status
        last_run_at: When agent last executed
        last_run_duration_seconds: Duration of last run
        is_running: Whether agent is currently executing
        schedule_cron: Current cron expression (for reference)
        next_scheduled_run: Next scheduled execution time
    """

    agent_name: str
    display_name: str
    description: Optional[str] = None
    last_run_status: Optional[str] = None
    last_run_at: Optional[datetime] = None
    last_run_duration_seconds: Optional[float] = None
    is_running: bool = False
    schedule_cron: Optional[str] = None
    next_scheduled_run: Optional[datetime] = None


@dataclass(frozen=True)
class TeamDTO:
    """Team definition for manual triggering.

    Story 7-7, Task 2.1: Static team metadata.

    Attributes:
        team_name: Unique team identifier
        display_name: Human-readable team name
        agents: Ordered list of agent names in dependency order
        description: What this team does
    """

    team_name: str
    display_name: str
    agents: list[str]
    description: str


@dataclass(frozen=True)
class PendingTrigger:
    """Pending trigger for an agent that is currently running.

    Story 7-7, Task 4.1: Ephemeral in-memory pending trigger info.

    Attributes:
        agent_name: Agent to trigger after current run completes
        triggered_by: Who requested the trigger
        queued_at: When the pending trigger was created
        config_overrides: Optional runtime config overrides
    """

    agent_name: str
    triggered_by: str
    queued_at: datetime
    config_overrides: Optional[dict] = None


# Story 7-8: Execution log DTOs for dashboard


@dataclass(frozen=True)
class ExecutionLogDTO:
    """Execution log entry for list views.

    Story 7-8, Task 2.1: Frozen dataclass for execution log API responses.
    Excludes log_output (large text) — use ExecutionLogDetailDTO for detail view.

    Attributes:
        id: Execution UUID as string
        agent_name: Agent identifier
        display_name: Human-readable name (enriched from schedules)
        started_at: When execution began
        completed_at: When execution ended (None while running)
        duration_seconds: Execution duration (None while running)
        status: running, success, failed, incomplete
        trigger_type: scheduled or manual
        triggered_by: Who triggered
        summary: Runner result dict
        error_message: Error description on failure
        error_traceback: Stack trace on failure
        items_processed: Count extracted from summary
        has_log_output: Whether log output exists (flag for UI)
    """

    id: str
    agent_name: str
    display_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    status: str
    trigger_type: str
    triggered_by: str
    summary: Optional[dict]
    error_message: Optional[str]
    error_traceback: Optional[str]
    items_processed: int
    has_log_output: bool


@dataclass(frozen=True)
class ExecutionLogDetailDTO:
    """Execution log entry for detail view (includes log_output).

    Story 7-8, Task 2.1: Extended DTO with full log text for detail view.

    Attributes:
        All fields from ExecutionLogDTO plus:
        log_output: Full captured log text (only for detail view)
    """

    id: str
    agent_name: str
    display_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    status: str
    trigger_type: str
    triggered_by: str
    summary: Optional[dict]
    error_message: Optional[str]
    error_traceback: Optional[str]
    items_processed: int
    has_log_output: bool
    log_output: Optional[str]


@dataclass(frozen=True)
class DashboardSummaryDTO:
    """Dashboard overview with running, recent completions, and failures.

    Story 7-8, Task 2.1: Aggregated dashboard data.

    Attributes:
        running: Currently running agent executions
        recent_completions: Successful executions in last 24h
        recent_failures: Failed/incomplete executions in last 7d
        total_executions_24h: Total execution count in last 24h
        success_rate_24h: Success percentage in last 24h
        avg_duration_24h: Average duration in seconds (None if no data)
    """

    running: list[ExecutionLogDTO]
    recent_completions: list[ExecutionLogDTO]
    recent_failures: list[ExecutionLogDTO]
    total_executions_24h: int
    success_rate_24h: float
    avg_duration_24h: Optional[float]


@dataclass(frozen=True)
class ExecutionLogFilterDTO:
    """Filter criteria for execution log queries.

    Story 7-8, Task 2.1: All fields optional with sensible defaults.

    Attributes:
        agent_name: Filter by agent name
        status: Filter by status
        trigger_type: Filter by trigger type
        date_from: Start of date range
        date_to: End of date range
        limit: Page size (default 25)
        offset: Page offset (default 0)
    """

    agent_name: Optional[str] = None
    status: Optional[str] = None
    trigger_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 25
    offset: int = 0


__all__ = [
    "AgentScheduleDTO",
    "ScheduleUpdateRequest",
    "DependencyWarning",
    "ScheduleChangeLogDTO",
    # Story 7-7: Manual trigger DTOs
    "TriggerResult",
    "TeamTriggerResult",
    "TriggerableAgentDTO",
    "TeamDTO",
    "PendingTrigger",
    # Story 7-8: Execution log DTOs
    "ExecutionLogDTO",
    "ExecutionLogDetailDTO",
    "DashboardSummaryDTO",
    "ExecutionLogFilterDTO",
]
