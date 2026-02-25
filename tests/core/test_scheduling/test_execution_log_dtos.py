"""Tests for execution log DTOs.

Story 7-8, Task 2.2: DTO tests covering frozen immutability, defaults, filter combinations.
Target: 10+ tests.
"""

import pytest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

from core.scheduling.dtos import (
    ExecutionLogDTO,
    ExecutionLogDetailDTO,
    DashboardSummaryDTO,
    ExecutionLogFilterDTO,
)


class TestExecutionLogDTO:
    """Tests for ExecutionLogDTO frozen dataclass."""

    def test_create_with_all_fields(self):
        """Can create DTO with all fields."""
        now = datetime.now(UTC)
        dto = ExecutionLogDTO(
            id="550e8400-e29b-41d4-a716-446655440000",
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Monitor",
            started_at=now,
            completed_at=now,
            duration_seconds=120.5,
            status="success",
            trigger_type="scheduled",
            triggered_by="scheduler",
            summary={"items_processed": 42},
            error_message=None,
            error_traceback=None,
            items_processed=42,
            has_log_output=True,
        )
        assert dto.agent_name == "health_claims_monitor"
        assert dto.display_name == "EU Health Claims Monitor"
        assert dto.status == "success"
        assert dto.items_processed == 42
        assert dto.has_log_output is True

    def test_frozen_immutability(self):
        """DTO is frozen — cannot modify fields after creation."""
        now = datetime.now(UTC)
        dto = ExecutionLogDTO(
            id="test-id",
            agent_name="test",
            display_name="Test",
            started_at=now,
            completed_at=None,
            duration_seconds=None,
            status="running",
            trigger_type="scheduled",
            triggered_by="scheduler",
            summary=None,
            error_message=None,
            error_traceback=None,
            items_processed=0,
            has_log_output=False,
        )
        with pytest.raises(FrozenInstanceError):
            dto.status = "success"  # type: ignore[misc]

    def test_nullable_fields(self):
        """Optional fields accept None."""
        now = datetime.now(UTC)
        dto = ExecutionLogDTO(
            id="test-id",
            agent_name="test",
            display_name="Test",
            started_at=now,
            completed_at=None,
            duration_seconds=None,
            status="running",
            trigger_type="scheduled",
            triggered_by="scheduler",
            summary=None,
            error_message=None,
            error_traceback=None,
            items_processed=0,
            has_log_output=False,
        )
        assert dto.completed_at is None
        assert dto.duration_seconds is None
        assert dto.summary is None
        assert dto.error_message is None


class TestExecutionLogDetailDTO:
    """Tests for ExecutionLogDetailDTO frozen dataclass."""

    def test_includes_log_output(self):
        """Detail DTO includes log_output field."""
        now = datetime.now(UTC)
        dto = ExecutionLogDetailDTO(
            id="test-id",
            agent_name="test",
            display_name="Test",
            started_at=now,
            completed_at=now,
            duration_seconds=60.0,
            status="success",
            trigger_type="scheduled",
            triggered_by="scheduler",
            summary=None,
            error_message=None,
            error_traceback=None,
            items_processed=10,
            has_log_output=True,
            log_output="Processing started...\nDone.",
        )
        assert dto.log_output == "Processing started...\nDone."

    def test_frozen_immutability(self):
        """Detail DTO is frozen."""
        now = datetime.now(UTC)
        dto = ExecutionLogDetailDTO(
            id="test-id",
            agent_name="test",
            display_name="Test",
            started_at=now,
            completed_at=None,
            duration_seconds=None,
            status="running",
            trigger_type="scheduled",
            triggered_by="scheduler",
            summary=None,
            error_message=None,
            error_traceback=None,
            items_processed=0,
            has_log_output=False,
            log_output=None,
        )
        with pytest.raises(FrozenInstanceError):
            dto.log_output = "changed"  # type: ignore[misc]

    def test_log_output_nullable(self):
        """log_output can be None (no logs captured)."""
        now = datetime.now(UTC)
        dto = ExecutionLogDetailDTO(
            id="test-id",
            agent_name="test",
            display_name="Test",
            started_at=now,
            completed_at=None,
            duration_seconds=None,
            status="running",
            trigger_type="scheduled",
            triggered_by="scheduler",
            summary=None,
            error_message=None,
            error_traceback=None,
            items_processed=0,
            has_log_output=False,
            log_output=None,
        )
        assert dto.log_output is None


class TestDashboardSummaryDTO:
    """Tests for DashboardSummaryDTO frozen dataclass."""

    def test_create_with_lists(self):
        """Can create dashboard summary with log lists."""
        dto = DashboardSummaryDTO(
            running=[],
            recent_completions=[],
            recent_failures=[],
            total_executions_24h=0,
            success_rate_24h=0.0,
            avg_duration_24h=None,
        )
        assert dto.running == []
        assert dto.total_executions_24h == 0
        assert dto.success_rate_24h == 0.0
        assert dto.avg_duration_24h is None

    def test_frozen_immutability(self):
        """Dashboard summary is frozen."""
        dto = DashboardSummaryDTO(
            running=[],
            recent_completions=[],
            recent_failures=[],
            total_executions_24h=5,
            success_rate_24h=80.0,
            avg_duration_24h=45.2,
        )
        with pytest.raises(FrozenInstanceError):
            dto.total_executions_24h = 10  # type: ignore[misc]

    def test_with_populated_lists(self):
        """Dashboard summary with actual execution log DTOs."""
        now = datetime.now(UTC)
        running_log = ExecutionLogDTO(
            id="running-1",
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Monitor",
            started_at=now,
            completed_at=None,
            duration_seconds=None,
            status="running",
            trigger_type="scheduled",
            triggered_by="scheduler",
            summary=None,
            error_message=None,
            error_traceback=None,
            items_processed=0,
            has_log_output=False,
        )
        dto = DashboardSummaryDTO(
            running=[running_log],
            recent_completions=[],
            recent_failures=[],
            total_executions_24h=1,
            success_rate_24h=0.0,
            avg_duration_24h=None,
        )
        assert len(dto.running) == 1
        assert dto.running[0].agent_name == "health_claims_monitor"


class TestExecutionLogFilterDTO:
    """Tests for ExecutionLogFilterDTO frozen dataclass."""

    def test_defaults(self):
        """Filter DTO has sensible defaults."""
        dto = ExecutionLogFilterDTO()
        assert dto.agent_name is None
        assert dto.status is None
        assert dto.trigger_type is None
        assert dto.date_from is None
        assert dto.date_to is None
        assert dto.limit == 25
        assert dto.offset == 0

    def test_all_filters_set(self):
        """Can set all filter fields."""
        now = datetime.now(UTC)
        dto = ExecutionLogFilterDTO(
            agent_name="health_claims_monitor",
            status="failed",
            trigger_type="manual",
            date_from=now,
            date_to=now,
            limit=50,
            offset=25,
        )
        assert dto.agent_name == "health_claims_monitor"
        assert dto.status == "failed"
        assert dto.trigger_type == "manual"
        assert dto.limit == 50
        assert dto.offset == 25

    def test_frozen_immutability(self):
        """Filter DTO is frozen."""
        dto = ExecutionLogFilterDTO()
        with pytest.raises(FrozenInstanceError):
            dto.limit = 100  # type: ignore[misc]

    def test_partial_filters(self):
        """Can set only some filter fields."""
        dto = ExecutionLogFilterDTO(
            agent_name="test_agent",
            limit=10,
        )
        assert dto.agent_name == "test_agent"
        assert dto.status is None
        assert dto.limit == 10
        assert dto.offset == 0
