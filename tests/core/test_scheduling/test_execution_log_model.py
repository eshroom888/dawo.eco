"""Tests for AgentExecutionLog model.

Story 7-8, Task 1.4: Model tests covering constraints, defaults, indexes, repr.
Target: 8+ tests.
"""

import pytest
from datetime import UTC, datetime
from uuid import uuid4

from core.scheduling.models import (
    AgentExecutionLog,
    MAX_AGENT_NAME_LENGTH,
    MAX_STATUS_LENGTH,
)
from core.models import Base


class TestAgentExecutionLogModel:
    """Tests for the AgentExecutionLog SQLAlchemy model."""

    def test_inherits_from_base(self):
        """AgentExecutionLog inherits from declarative Base."""
        assert issubclass(AgentExecutionLog, Base)

    def test_tablename(self):
        """Table name is agent_execution_logs (plural, snake_case)."""
        assert AgentExecutionLog.__tablename__ == "agent_execution_logs"

    def test_create_minimal_instance(self):
        """Can create instance with only required fields."""
        now = datetime.now(UTC)
        log = AgentExecutionLog(
            agent_name="health_claims_monitor",
            started_at=now,
            status="running",
            trigger_type="scheduled",
        )
        assert log.agent_name == "health_claims_monitor"
        assert log.started_at == now
        assert log.status == "running"
        assert log.trigger_type == "scheduled"

    def test_full_instance_with_all_fields(self):
        """Can create a fully-populated instance."""
        now = datetime.now(UTC)
        log_id = uuid4()
        log = AgentExecutionLog(
            id=log_id,
            agent_name="health_claims_monitor",
            started_at=now,
            completed_at=now,
            duration_seconds=120.5,
            status="success",
            trigger_type="manual",
            triggered_by="operator",
            summary={"items_processed": 42, "errors": []},
            error_message=None,
            error_traceback=None,
            log_output="Processing started...\nDone.",
            items_processed=42,
            created_at=now,
        )
        assert log.id == log_id
        assert log.agent_name == "health_claims_monitor"
        assert log.completed_at == now
        assert log.duration_seconds == 120.5
        assert log.status == "success"
        assert log.trigger_type == "manual"
        assert log.triggered_by == "operator"
        assert log.summary == {"items_processed": 42, "errors": []}
        assert log.log_output == "Processing started...\nDone."
        assert log.items_processed == 42

    def test_nullable_fields_accept_none(self):
        """Optional fields accept None."""
        now = datetime.now(UTC)
        log = AgentExecutionLog(
            agent_name="test_agent",
            started_at=now,
            status="running",
            trigger_type="scheduled",
        )
        assert log.completed_at is None
        assert log.duration_seconds is None
        assert log.summary is None
        assert log.error_message is None
        assert log.error_traceback is None
        assert log.log_output is None

    def test_status_values(self):
        """status accepts all valid status strings."""
        now = datetime.now(UTC)
        for status in ["running", "success", "failed", "incomplete"]:
            log = AgentExecutionLog(
                agent_name="test_agent",
                started_at=now,
                status=status,
                trigger_type="scheduled",
            )
            assert log.status == status

    def test_trigger_type_values(self):
        """trigger_type accepts scheduled and manual."""
        now = datetime.now(UTC)
        for trigger_type in ["scheduled", "manual"]:
            log = AgentExecutionLog(
                agent_name="test_agent",
                started_at=now,
                status="running",
                trigger_type=trigger_type,
            )
            assert log.trigger_type == trigger_type

    def test_default_triggered_by_column(self):
        """Column default for triggered_by is 'scheduler'."""
        col = AgentExecutionLog.__table__.columns["triggered_by"]
        assert col.default.arg == "scheduler"

    def test_default_items_processed_column(self):
        """Column default for items_processed is 0."""
        col = AgentExecutionLog.__table__.columns["items_processed"]
        assert col.default.arg == 0

    def test_indexes_exist(self):
        """Required indexes are defined on the table."""
        table = AgentExecutionLog.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "idx_execution_logs_agent_name" in index_names
        assert "idx_execution_logs_started_at" in index_names
        assert "idx_execution_logs_status" in index_names
        assert "idx_execution_logs_agent_started" in index_names

    def test_repr(self):
        """__repr__ includes agent_name and status."""
        now = datetime.now(UTC)
        log = AgentExecutionLog(
            agent_name="health_claims_monitor",
            started_at=now,
            status="running",
            trigger_type="scheduled",
        )
        repr_str = repr(log)
        assert "health_claims_monitor" in repr_str
        assert "running" in repr_str

    def test_error_fields_on_failure(self):
        """Error fields populated on failed execution."""
        now = datetime.now(UTC)
        log = AgentExecutionLog(
            agent_name="test_agent",
            started_at=now,
            status="failed",
            trigger_type="scheduled",
            error_message="Connection timeout",
            error_traceback="Traceback (most recent call last):\n  ...",
        )
        assert log.error_message == "Connection timeout"
        assert log.error_traceback.startswith("Traceback")

    def test_summary_jsonb(self):
        """summary stores dict via JSONB."""
        now = datetime.now(UTC)
        summary = {"items_processed": 10, "new_items": 3, "errors": []}
        log = AgentExecutionLog(
            agent_name="test_agent",
            started_at=now,
            status="success",
            trigger_type="scheduled",
            summary=summary,
        )
        assert log.summary == summary
        assert isinstance(log.summary, dict)
