"""Agent scheduling database models.

Story 7-6, Task 1: Database models for agent schedule management.
Story 7-8, Task 1: AgentExecutionLog for historical execution tracking.

Models:
    - AgentSchedule: Stores per-agent scheduling configuration and run status
    - ScheduleChangeLog: Audit trail for schedule modifications
    - AgentExecutionLog: Historical execution log entries for dashboard

Usage:
    from core.scheduling.models import AgentSchedule, ScheduleChangeLog, AgentExecutionLog
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base

# Column length constants
MAX_AGENT_NAME_LENGTH = 100
MAX_DISPLAY_NAME_LENGTH = 200
MAX_STATUS_LENGTH = 20
MAX_TIMEZONE_LENGTH = 50
MAX_CRON_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500
MAX_CONFIG_SOURCE_LENGTH = 200
MAX_FIELD_CHANGED_LENGTH = 50
MAX_CHANGED_BY_LENGTH = 50
MAX_OLD_NEW_VALUE_LENGTH = 500
MAX_TRIGGER_TYPE_LENGTH = 20
MAX_TRIGGERED_BY_LENGTH = 50


class AgentSchedule(Base):
    """Agent schedule configuration and run status.

    Story 7-6, Task 1.1: Stores scheduling config, run status,
    and dependency information for each scheduled agent.

    Attributes:
        id: UUID primary key
        agent_name: Unique agent identifier (e.g. "health_claims_monitor")
        display_name: Human-readable name
        description: Optional description of the agent's purpose
        schedule_cron: 5-field cron expression
        timezone: IANA timezone (default "UTC")
        enabled: Whether the schedule is active
        last_run_at: When agent last executed
        last_run_status: Result of last execution
        last_run_duration_seconds: How long the last run took
        last_run_summary: JSONB with detailed run results
        next_run_at: Computed next execution time
        dependencies: JSONB list of agent_name strings this agent depends on
        config_source: Origin config file (e.g. "dawo_health_claims.json")
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """

    __tablename__ = "agent_schedules"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    agent_name: Mapped[str] = mapped_column(
        String(MAX_AGENT_NAME_LENGTH),
        nullable=False,
        unique=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(
        String(MAX_DISPLAY_NAME_LENGTH),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(MAX_DESCRIPTION_LENGTH),
        nullable=True,
    )
    schedule_cron: Mapped[str] = mapped_column(
        String(MAX_CRON_LENGTH),
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(MAX_TIMEZONE_LENGTH),
        nullable=False,
        default="UTC",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_run_status: Mapped[Optional[str]] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=True,
    )
    last_run_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    last_run_summary: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dependencies: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    config_source: Mapped[Optional[str]] = mapped_column(
        String(MAX_CONFIG_SOURCE_LENGTH),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_agent_schedules_next_run_at", "next_run_at"),
        Index(
            "idx_agent_schedules_enabled",
            "enabled",
            postgresql_where=(enabled == True),  # noqa: E712
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AgentSchedule(agent_name={self.agent_name!r}, "
            f"schedule_cron={self.schedule_cron!r}, "
            f"enabled={self.enabled})>"
        )


class ScheduleChangeLog(Base):
    """Audit trail for agent schedule changes.

    Story 7-6, Task 1.2: Records every modification to schedule config
    for traceability and rollback capability.

    Attributes:
        id: UUID primary key
        agent_name: Which agent's schedule was changed
        field_changed: Name of the modified field
        old_value: Previous value (None for first-time settings)
        new_value: New value after change
        changed_by: Who made the change (default "operator")
        created_at: When the change occurred
    """

    __tablename__ = "schedule_change_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    agent_name: Mapped[str] = mapped_column(
        String(MAX_AGENT_NAME_LENGTH),
        nullable=False,
        index=True,
    )
    field_changed: Mapped[str] = mapped_column(
        String(MAX_FIELD_CHANGED_LENGTH),
        nullable=False,
    )
    old_value: Mapped[Optional[str]] = mapped_column(
        String(MAX_OLD_NEW_VALUE_LENGTH),
        nullable=True,
    )
    new_value: Mapped[str] = mapped_column(
        String(MAX_OLD_NEW_VALUE_LENGTH),
        nullable=False,
    )
    changed_by: Mapped[str] = mapped_column(
        String(MAX_CHANGED_BY_LENGTH),
        nullable=False,
        default="operator",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<ScheduleChangeLog(agent_name={self.agent_name!r}, "
            f"field_changed={self.field_changed!r}, "
            f"new_value={self.new_value!r})>"
        )


class AgentExecutionLog(Base):
    """Historical execution log entry for agent runs.

    Story 7-8, Task 1.1: Tracks each agent execution with status,
    duration, log output, and error details for the dashboard.

    Attributes:
        id: UUID primary key
        agent_name: Agent identifier (indexed, loose FK to agent_schedules)
        started_at: When execution began
        completed_at: When execution ended (None while running)
        duration_seconds: Execution duration (None while running)
        status: running, success, failed, incomplete
        trigger_type: scheduled or manual
        triggered_by: Who triggered (default "scheduler")
        summary: JSONB runner result dict
        error_message: Error description on failure
        error_traceback: Stack trace on failure
        log_output: Captured log lines (capped at 1000)
        items_processed: Count extracted from summary
        created_at: Record creation timestamp
    """

    __tablename__ = "agent_execution_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    agent_name: Mapped[str] = mapped_column(
        String(MAX_AGENT_NAME_LENGTH),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default="running",
    )
    trigger_type: Mapped[str] = mapped_column(
        String(MAX_TRIGGER_TYPE_LENGTH),
        nullable=False,
        default="scheduled",
    )
    triggered_by: Mapped[str] = mapped_column(
        String(MAX_TRIGGERED_BY_LENGTH),
        nullable=False,
        default="scheduler",
    )
    summary: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_traceback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    log_output: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    items_processed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_execution_logs_agent_name", "agent_name"),
        Index("idx_execution_logs_started_at", started_at.desc()),
        Index("idx_execution_logs_status", "status"),
        Index("idx_execution_logs_agent_started", "agent_name", started_at.desc()),
    )

    def __repr__(self) -> str:
        return (
            f"<AgentExecutionLog(agent_name={self.agent_name!r}, "
            f"status={self.status!r}, "
            f"started_at={self.started_at!r})>"
        )


__all__ = [
    "AgentSchedule",
    "ScheduleChangeLog",
    "AgentExecutionLog",
    "MAX_AGENT_NAME_LENGTH",
    "MAX_DISPLAY_NAME_LENGTH",
    "MAX_STATUS_LENGTH",
    "MAX_TIMEZONE_LENGTH",
    "MAX_CRON_LENGTH",
    "MAX_DESCRIPTION_LENGTH",
    "MAX_CONFIG_SOURCE_LENGTH",
    "MAX_FIELD_CHANGED_LENGTH",
    "MAX_CHANGED_BY_LENGTH",
    "MAX_OLD_NEW_VALUE_LENGTH",
    "MAX_TRIGGER_TYPE_LENGTH",
    "MAX_TRIGGERED_BY_LENGTH",
]
