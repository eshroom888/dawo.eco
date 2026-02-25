"""Tests for AgentSchedule and ScheduleChangeLog models.

Story 7-6, Task 1.4: Model tests covering constraints, defaults, JSONB, relationships.
Target: 18+ tests.
"""

import pytest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from core.scheduling.models import (
    AgentSchedule,
    ScheduleChangeLog,
    MAX_AGENT_NAME_LENGTH,
    MAX_DISPLAY_NAME_LENGTH,
    MAX_STATUS_LENGTH,
    MAX_TIMEZONE_LENGTH,
    MAX_CRON_LENGTH,
    MAX_FIELD_CHANGED_LENGTH,
    MAX_CHANGED_BY_LENGTH,
)
from core.models import Base


class TestAgentScheduleModel:
    """Tests for the AgentSchedule SQLAlchemy model."""

    def test_inherits_from_base(self):
        """AgentSchedule inherits from declarative Base."""
        assert issubclass(AgentSchedule, Base)

    def test_tablename(self):
        """Table name is agent_schedules (plural, snake_case)."""
        assert AgentSchedule.__tablename__ == "agent_schedules"

    def test_create_minimal_instance(self):
        """Can create instance with only required fields."""
        schedule = AgentSchedule(
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Register Monitor",
            schedule_cron="0 5 * * 0",
        )
        assert schedule.agent_name == "health_claims_monitor"
        assert schedule.display_name == "EU Health Claims Register Monitor"
        assert schedule.schedule_cron == "0 5 * * 0"

    def test_default_timezone_column(self):
        """Column default for timezone is UTC (applied at DB INSERT)."""
        col = AgentSchedule.__table__.columns["timezone"]
        assert col.default.arg == "UTC"

    def test_default_enabled_column(self):
        """Column default for enabled is True (applied at DB INSERT)."""
        col = AgentSchedule.__table__.columns["enabled"]
        assert col.default.arg is True

    def test_explicit_timezone_value(self):
        """Timezone accepts explicit value."""
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 7 * * 1",
            timezone="Europe/Oslo",
        )
        assert schedule.timezone == "Europe/Oslo"

    def test_explicit_enabled_false(self):
        """Enabled accepts explicit False."""
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 0 * * *",
            enabled=False,
        )
        assert schedule.enabled is False

    def test_nullable_description(self):
        """Description can be None."""
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 0 * * *",
            description=None,
        )
        assert schedule.description is None

    def test_nullable_last_run_fields(self):
        """Last run fields can be None (never run)."""
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 0 * * *",
        )
        assert schedule.last_run_at is None
        assert schedule.last_run_status is None
        assert schedule.last_run_duration_seconds is None
        assert schedule.last_run_summary is None

    def test_nullable_next_run_at(self):
        """next_run_at can be None."""
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 0 * * *",
        )
        assert schedule.next_run_at is None

    def test_dependencies_default_column(self):
        """Column default for dependencies is empty list (applied at DB INSERT)."""
        col = AgentSchedule.__table__.columns["dependencies"]
        # server_default is "[]" string for JSONB empty array
        assert "[]" in str(col.server_default.arg)

    def test_dependencies_explicit_empty_list(self):
        """Dependencies accepts explicit empty list."""
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 0 * * *",
            dependencies=[],
        )
        assert schedule.dependencies == []

    def test_dependencies_jsonb_with_values(self):
        """Dependencies stores list of agent name strings."""
        deps = ["shopify_attribution_poll", "post_publish_scoring"]
        schedule = AgentSchedule(
            agent_name="feedback_loop",
            display_name="Performance Feedback Loop",
            schedule_cron="0 4 * * 0",
            dependencies=deps,
        )
        assert schedule.dependencies == deps
        assert isinstance(schedule.dependencies, list)

    def test_last_run_summary_jsonb(self):
        """last_run_summary stores dict via JSONB."""
        summary = {"items_processed": 42, "errors": []}
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 0 * * *",
            last_run_summary=summary,
        )
        assert schedule.last_run_summary == summary

    def test_config_source_nullable(self):
        """config_source can be None or a string."""
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 0 * * *",
            config_source="dawo_health_claims.json",
        )
        assert schedule.config_source == "dawo_health_claims.json"

    def test_all_run_status_values(self):
        """last_run_status accepts valid status strings."""
        for status in ["success", "failed", "incomplete", "running"]:
            schedule = AgentSchedule(
                agent_name="test_agent",
                display_name="Test Agent",
                schedule_cron="0 0 * * *",
                last_run_status=status,
            )
            assert schedule.last_run_status == status

    def test_last_run_duration_float(self):
        """last_run_duration_seconds stores float."""
        schedule = AgentSchedule(
            agent_name="test_agent",
            display_name="Test Agent",
            schedule_cron="0 0 * * *",
            last_run_duration_seconds=45.7,
        )
        assert schedule.last_run_duration_seconds == 45.7

    def test_repr(self):
        """__repr__ includes agent_name and schedule_cron."""
        schedule = AgentSchedule(
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Monitor",
            schedule_cron="0 5 * * 0",
        )
        repr_str = repr(schedule)
        assert "health_claims_monitor" in repr_str
        assert "0 5 * * 0" in repr_str

    def test_max_length_constants_defined(self):
        """Length constants are defined and reasonable."""
        assert MAX_AGENT_NAME_LENGTH == 100
        assert MAX_DISPLAY_NAME_LENGTH == 200
        assert MAX_STATUS_LENGTH == 20
        assert MAX_TIMEZONE_LENGTH == 50
        assert MAX_CRON_LENGTH == 50

    def test_full_instance_with_all_fields(self):
        """Can create a fully-populated instance."""
        now = datetime.now(UTC)
        schedule = AgentSchedule(
            id=uuid4(),
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Register Monitor",
            description="Weekly scan of EU health claims register",
            schedule_cron="0 5 * * 0",
            timezone="UTC",
            enabled=True,
            last_run_at=now,
            last_run_status="success",
            last_run_duration_seconds=120.5,
            last_run_summary={"items_processed": 42},
            next_run_at=now,
            dependencies=[],
            config_source="dawo_health_claims.json",
            created_at=now,
            updated_at=now,
        )
        assert schedule.agent_name == "health_claims_monitor"
        assert schedule.description == "Weekly scan of EU health claims register"
        assert schedule.last_run_duration_seconds == 120.5


class TestScheduleChangeLogModel:
    """Tests for the ScheduleChangeLog SQLAlchemy model."""

    def test_inherits_from_base(self):
        """ScheduleChangeLog inherits from declarative Base."""
        assert issubclass(ScheduleChangeLog, Base)

    def test_tablename(self):
        """Table name is schedule_change_logs."""
        assert ScheduleChangeLog.__tablename__ == "schedule_change_logs"

    def test_create_instance(self):
        """Can create a change log entry."""
        log = ScheduleChangeLog(
            agent_name="health_claims_monitor",
            field_changed="schedule_cron",
            old_value="0 5 * * 0",
            new_value="0 6 * * 0",
        )
        assert log.agent_name == "health_claims_monitor"
        assert log.field_changed == "schedule_cron"
        assert log.old_value == "0 5 * * 0"
        assert log.new_value == "0 6 * * 0"

    def test_default_changed_by_column(self):
        """Column default for changed_by is 'operator'."""
        col = ScheduleChangeLog.__table__.columns["changed_by"]
        assert col.default.arg == "operator"

    def test_explicit_changed_by(self):
        """changed_by accepts explicit value."""
        log = ScheduleChangeLog(
            agent_name="test_agent",
            field_changed="timezone",
            new_value="Europe/Oslo",
            changed_by="admin",
        )
        assert log.changed_by == "admin"

    def test_old_value_nullable(self):
        """old_value can be None (first time setting)."""
        log = ScheduleChangeLog(
            agent_name="test_agent",
            field_changed="enabled",
            old_value=None,
            new_value="true",
        )
        assert log.old_value is None

    def test_repr(self):
        """__repr__ includes agent_name and field_changed."""
        log = ScheduleChangeLog(
            agent_name="health_claims_monitor",
            field_changed="schedule_cron",
            old_value="0 5 * * 0",
            new_value="0 6 * * 0",
        )
        repr_str = repr(log)
        assert "health_claims_monitor" in repr_str
        assert "schedule_cron" in repr_str

    def test_max_length_constants(self):
        """Length constants for ScheduleChangeLog fields."""
        assert MAX_FIELD_CHANGED_LENGTH == 50
        assert MAX_CHANGED_BY_LENGTH == 50
