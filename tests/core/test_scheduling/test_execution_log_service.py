"""Tests for ExecutionLogService.

Story 7-8, Task 4.2: Service tests with mocked repositories.
Target: 20+ tests.
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from core.scheduling.execution_log_service import ExecutionLogService
from core.scheduling.models import AgentExecutionLog, AgentSchedule
from core.scheduling.dtos import (
    ExecutionLogDTO,
    ExecutionLogDetailDTO,
    DashboardSummaryDTO,
    ExecutionLogFilterDTO,
)


def _make_log(**kwargs) -> AgentExecutionLog:
    """Factory for test AgentExecutionLog instances."""
    defaults = {
        "id": uuid4(),
        "agent_name": "test_agent",
        "started_at": datetime.now(UTC),
        "status": "running",
        "trigger_type": "scheduled",
        "triggered_by": "scheduler",
        "items_processed": 0,
        "log_output": None,
        "summary": None,
        "error_message": None,
        "error_traceback": None,
        "completed_at": None,
        "duration_seconds": None,
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return AgentExecutionLog(**defaults)


def _make_schedule(**kwargs) -> AgentSchedule:
    """Factory for test AgentSchedule instances."""
    defaults = {
        "id": uuid4(),
        "agent_name": "test_agent",
        "display_name": "Test Agent",
        "schedule_cron": "0 0 * * *",
        "timezone": "UTC",
        "enabled": True,
        "dependencies": [],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return AgentSchedule(**defaults)


@pytest.fixture
def mock_log_repo():
    """Mock ExecutionLogRepository."""
    return AsyncMock()


@pytest.fixture
def mock_schedule_repo():
    """Mock AgentScheduleRepository."""
    return AsyncMock()


@pytest.fixture
def service(mock_log_repo, mock_schedule_repo):
    """Create ExecutionLogService with mocked dependencies."""
    return ExecutionLogService(mock_log_repo, mock_schedule_repo)


class TestStartExecution:
    """Tests for start_execution method."""

    @pytest.mark.asyncio
    async def test_creates_log_and_returns_dto(self, service, mock_log_repo, mock_schedule_repo):
        """start_execution creates log entry and returns DTO."""
        created_log = _make_log(agent_name="health_claims_monitor")
        mock_log_repo.create.return_value = created_log

        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Monitor",
        )
        mock_schedule_repo.get_by_agent_name.return_value = schedule

        result = await service.start_execution(
            agent_name="health_claims_monitor",
            trigger_type="scheduled",
            triggered_by="scheduler",
        )
        assert isinstance(result, ExecutionLogDTO)
        assert result.agent_name == "health_claims_monitor"
        assert result.display_name == "EU Health Claims Monitor"
        assert result.status == "running"
        mock_log_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fallback_display_name(self, service, mock_log_repo, mock_schedule_repo):
        """Uses title-cased agent_name when no schedule found."""
        created_log = _make_log(agent_name="novel_food_scanner")
        mock_log_repo.create.return_value = created_log
        mock_schedule_repo.get_by_agent_name.return_value = None

        result = await service.start_execution(
            agent_name="novel_food_scanner",
            trigger_type="manual",
            triggered_by="operator",
        )
        assert result.display_name == "Novel Food Scanner"

    @pytest.mark.asyncio
    async def test_manual_trigger_type(self, service, mock_log_repo, mock_schedule_repo):
        """start_execution sets manual trigger_type."""
        created_log = _make_log(trigger_type="manual", triggered_by="operator")
        mock_log_repo.create.return_value = created_log
        mock_schedule_repo.get_by_agent_name.return_value = None

        result = await service.start_execution(
            agent_name="test_agent",
            trigger_type="manual",
            triggered_by="operator",
        )
        assert result.trigger_type == "manual"
        assert result.triggered_by == "operator"


class TestCompleteExecution:
    """Tests for complete_execution method."""

    @pytest.mark.asyncio
    async def test_calculates_duration(self, service, mock_log_repo, mock_schedule_repo):
        """complete_execution calculates duration from started_at."""
        log_id = uuid4()
        started = datetime.now(UTC) - timedelta(minutes=2)
        existing = _make_log(id=log_id, started_at=started)
        mock_log_repo.get_by_id.return_value = existing
        mock_log_repo.update_completion.return_value = True
        mock_schedule_repo.get_by_agent_name.return_value = None

        result = await service.complete_execution(
            log_id=str(log_id),
            status="success",
            summary={"items_processed": 42},
            error_message=None,
            error_traceback=None,
            log_output="Done.",
        )
        assert isinstance(result, ExecutionLogDTO)
        # Duration passed to repo should be > 0
        call_args = mock_log_repo.update_completion.call_args
        assert call_args.kwargs["duration"] > 0

    @pytest.mark.asyncio
    async def test_caps_log_output_at_1000_lines(self, service, mock_log_repo, mock_schedule_repo):
        """complete_execution caps log_output at 1000 lines."""
        log_id = uuid4()
        existing = _make_log(id=log_id)
        mock_log_repo.get_by_id.return_value = existing
        mock_log_repo.update_completion.return_value = True
        mock_schedule_repo.get_by_agent_name.return_value = None

        long_output = "\n".join(f"Line {i}" for i in range(2000))
        await service.complete_execution(
            log_id=str(log_id),
            status="success",
            summary=None,
            error_message=None,
            error_traceback=None,
            log_output=long_output,
        )
        call_args = mock_log_repo.update_completion.call_args
        capped = call_args.kwargs["log_output"]
        assert len(capped.split("\n")) == 1000

    @pytest.mark.asyncio
    async def test_extracts_items_processed(self, service, mock_log_repo, mock_schedule_repo):
        """complete_execution extracts items_processed from summary."""
        log_id = uuid4()
        existing = _make_log(id=log_id)
        mock_log_repo.get_by_id.return_value = existing
        mock_log_repo.update_completion.return_value = True
        mock_schedule_repo.get_by_agent_name.return_value = None

        await service.complete_execution(
            log_id=str(log_id),
            status="success",
            summary={"items_processed": 42},
            error_message=None,
            error_traceback=None,
            log_output=None,
        )
        call_args = mock_log_repo.update_completion.call_args
        assert call_args.kwargs["items_processed"] == 42

    @pytest.mark.asyncio
    async def test_items_processed_default_zero(self, service, mock_log_repo, mock_schedule_repo):
        """items_processed defaults to 0 when not in summary."""
        log_id = uuid4()
        existing = _make_log(id=log_id)
        mock_log_repo.get_by_id.return_value = existing
        mock_log_repo.update_completion.return_value = True
        mock_schedule_repo.get_by_agent_name.return_value = None

        await service.complete_execution(
            log_id=str(log_id),
            status="success",
            summary={"some_other_key": 10},
            error_message=None,
            error_traceback=None,
            log_output=None,
        )
        call_args = mock_log_repo.update_completion.call_args
        assert call_args.kwargs["items_processed"] == 0

    @pytest.mark.asyncio
    async def test_none_summary_items_processed_zero(self, service, mock_log_repo, mock_schedule_repo):
        """items_processed is 0 when summary is None."""
        log_id = uuid4()
        existing = _make_log(id=log_id)
        mock_log_repo.get_by_id.return_value = existing
        mock_log_repo.update_completion.return_value = True
        mock_schedule_repo.get_by_agent_name.return_value = None

        await service.complete_execution(
            log_id=str(log_id),
            status="failed",
            summary=None,
            error_message="error",
            error_traceback="trace",
            log_output=None,
        )
        call_args = mock_log_repo.update_completion.call_args
        assert call_args.kwargs["items_processed"] == 0


class TestGetDashboardSummary:
    """Tests for get_dashboard_summary method."""

    @pytest.mark.asyncio
    async def test_aggregates_running_completions_failures(
        self, service, mock_log_repo, mock_schedule_repo
    ):
        """Dashboard combines running + recent success + recent failures."""
        running = [_make_log(status="running")]
        completions = [_make_log(status="success")]
        failures = [_make_log(status="failed")]

        mock_log_repo.get_running.return_value = running
        # get_recent called 3 times: success(24h), failed(168h), incomplete(168h)
        mock_log_repo.get_recent.side_effect = [completions, failures, []]
        mock_log_repo.get_stats.return_value = {
            "total": 3,
            "success": 1,
            "failed": 1,
            "avg_duration": 30.0,
        }
        mock_schedule_repo.get_all.return_value = []

        result = await service.get_dashboard_summary()
        assert isinstance(result, DashboardSummaryDTO)
        assert len(result.running) == 1
        assert len(result.recent_completions) == 1
        assert len(result.recent_failures) == 1
        assert result.total_executions_24h == 3

    @pytest.mark.asyncio
    async def test_batch_fetches_schedules(self, service, mock_log_repo, mock_schedule_repo):
        """Dashboard fetches all schedules in one batch (no N+1)."""
        mock_log_repo.get_running.return_value = []
        mock_log_repo.get_recent.side_effect = [[], [], []]
        mock_log_repo.get_stats.return_value = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "avg_duration": None,
        }
        mock_schedule_repo.get_all.return_value = []

        await service.get_dashboard_summary()
        mock_schedule_repo.get_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, service, mock_log_repo, mock_schedule_repo):
        """Dashboard calculates success rate percentage."""
        mock_log_repo.get_running.return_value = []
        mock_log_repo.get_recent.side_effect = [[], [], []]
        mock_log_repo.get_stats.return_value = {
            "total": 10,
            "success": 8,
            "failed": 2,
            "avg_duration": 45.0,
        }
        mock_schedule_repo.get_all.return_value = []

        result = await service.get_dashboard_summary()
        assert result.success_rate_24h == 80.0

    @pytest.mark.asyncio
    async def test_zero_total_success_rate(self, service, mock_log_repo, mock_schedule_repo):
        """Success rate is 0.0 when no executions."""
        mock_log_repo.get_running.return_value = []
        mock_log_repo.get_recent.side_effect = [[], [], []]
        mock_log_repo.get_stats.return_value = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "avg_duration": None,
        }
        mock_schedule_repo.get_all.return_value = []

        result = await service.get_dashboard_summary()
        assert result.success_rate_24h == 0.0

    @pytest.mark.asyncio
    async def test_enriches_display_names(self, service, mock_log_repo, mock_schedule_repo):
        """Dashboard enriches display_names from schedule map."""
        running_log = _make_log(agent_name="health_claims_monitor", status="running")
        mock_log_repo.get_running.return_value = [running_log]
        mock_log_repo.get_recent.side_effect = [[], [], []]
        mock_log_repo.get_stats.return_value = {
            "total": 1,
            "success": 0,
            "failed": 0,
            "avg_duration": None,
        }
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Monitor",
        )
        mock_schedule_repo.get_all.return_value = [schedule]

        result = await service.get_dashboard_summary()
        assert result.running[0].display_name == "EU Health Claims Monitor"


class TestGetExecutionDetail:
    """Tests for get_execution_detail method."""

    @pytest.mark.asyncio
    async def test_returns_detail_dto_with_log_output(
        self, service, mock_log_repo, mock_schedule_repo
    ):
        """Detail view includes log_output."""
        log = _make_log(
            log_output="Processing...\nDone.",
            status="success",
        )
        mock_log_repo.get_by_id.return_value = log
        mock_schedule_repo.get_by_agent_name.return_value = None

        result = await service.get_execution_detail(str(log.id))
        assert isinstance(result, ExecutionLogDetailDTO)
        assert result.log_output == "Processing...\nDone."

    @pytest.mark.asyncio
    async def test_returns_none_for_missing(self, service, mock_log_repo, mock_schedule_repo):
        """Returns None when execution not found."""
        mock_log_repo.get_by_id.return_value = None

        result = await service.get_execution_detail(str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_detail_has_log_output_flag(self, service, mock_log_repo, mock_schedule_repo):
        """Detail DTO has_log_output reflects actual log presence."""
        log_with_output = _make_log(log_output="some output")
        mock_log_repo.get_by_id.return_value = log_with_output
        mock_schedule_repo.get_by_agent_name.return_value = None

        result = await service.get_execution_detail(str(log_with_output.id))
        assert result.has_log_output is True

    @pytest.mark.asyncio
    async def test_detail_no_log_output(self, service, mock_log_repo, mock_schedule_repo):
        """Detail DTO has_log_output is False when no log."""
        log_no_output = _make_log(log_output=None)
        mock_log_repo.get_by_id.return_value = log_no_output
        mock_schedule_repo.get_by_agent_name.return_value = None

        result = await service.get_execution_detail(str(log_no_output.id))
        assert result.has_log_output is False


class TestGetFilteredExecutions:
    """Tests for get_filtered_executions method."""

    @pytest.mark.asyncio
    async def test_delegates_to_repo(self, service, mock_log_repo, mock_schedule_repo):
        """Delegates filtering to repository."""
        log = _make_log()
        mock_log_repo.get_filtered.return_value = ([log], 1)
        mock_schedule_repo.get_all.return_value = []

        filters = ExecutionLogFilterDTO(agent_name="test_agent")
        results, total = await service.get_filtered_executions(filters)
        assert len(results) == 1
        assert total == 1
        mock_log_repo.get_filtered.assert_awaited_once_with(filters)

    @pytest.mark.asyncio
    async def test_enriches_display_names_batch(self, service, mock_log_repo, mock_schedule_repo):
        """Filtered results are enriched with display_names in batch."""
        log = _make_log(agent_name="health_claims_monitor")
        mock_log_repo.get_filtered.return_value = ([log], 1)
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Monitor",
        )
        mock_schedule_repo.get_all.return_value = [schedule]

        filters = ExecutionLogFilterDTO()
        results, total = await service.get_filtered_executions(filters)
        assert results[0].display_name == "EU Health Claims Monitor"

    @pytest.mark.asyncio
    async def test_empty_results(self, service, mock_log_repo, mock_schedule_repo):
        """Empty results return empty list and zero count."""
        mock_log_repo.get_filtered.return_value = ([], 0)
        mock_schedule_repo.get_all.return_value = []

        filters = ExecutionLogFilterDTO()
        results, total = await service.get_filtered_executions(filters)
        assert results == []
        assert total == 0


class TestEnrichDisplayName:
    """Tests for _enrich_display_name helper."""

    def test_from_schedule_map(self, service):
        """Uses display_name from schedule map."""
        schedule_map = {"health_claims_monitor": "EU Health Claims Monitor"}
        name = service._enrich_display_name("health_claims_monitor", schedule_map)
        assert name == "EU Health Claims Monitor"

    def test_fallback_title_case(self, service):
        """Falls back to title-cased agent_name."""
        name = service._enrich_display_name("novel_food_scanner", {})
        assert name == "Novel Food Scanner"
