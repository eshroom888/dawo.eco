"""Integration tests for Execution Logs & Status Dashboard.

Epic 7, Story 7-8, Task 10.1: End-to-end integration tests.

Tests the integration between:
- ExecutionLogRepository (persistence)
- ExecutionLogService (business logic + display_name enrichment)
- ExecutionEventEmitter (real-time events)
- ManualTriggerService (retry)
- LogCaptureHandler (output capture)
- Dashboard aggregation + filtering + pagination

Target: 15+ tests.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from core.scheduling.dtos import (
    DashboardSummaryDTO,
    ExecutionLogDTO,
    ExecutionLogDetailDTO,
    ExecutionLogFilterDTO,
)
from core.scheduling.execution_events import (
    ExecutionEvent,
    ExecutionEventEmitter,
    ExecutionEventType,
)
from core.scheduling.execution_log_service import ExecutionLogService
from core.scheduling.log_capture import LogCaptureHandler
from core.scheduling.manual_trigger_service import ManualTriggerService
from core.scheduling.models import AgentExecutionLog


# --- Helpers ---


@dataclass(frozen=True)
class _MockConfig:
    enabled: bool = True
    check_interval_seconds: int = 60
    max_concurrent_agents: int = 5
    default_timezone: str = "UTC"
    seed_on_startup: bool = True


def _make_log(
    agent_name: str = "health_claims_monitor",
    status: str = "success",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    duration_seconds: float | None = 60.0,
    trigger_type: str = "scheduled",
    triggered_by: str = "scheduler",
    error_message: str | None = None,
    error_traceback: str | None = None,
    items_processed: int = 0,
    log_output: str | None = None,
    summary: dict | None = None,
) -> AgentExecutionLog:
    """Create a mock AgentExecutionLog for testing."""
    now = datetime.now(UTC)
    log = AgentExecutionLog()
    log.id = uuid4()
    log.agent_name = agent_name
    log.started_at = started_at or now - timedelta(seconds=60)
    log.completed_at = completed_at or (now if status != "running" else None)
    log.duration_seconds = duration_seconds if status != "running" else None
    log.status = status
    log.trigger_type = trigger_type
    log.triggered_by = triggered_by
    log.summary = summary
    log.error_message = error_message
    log.error_traceback = error_traceback
    log.items_processed = items_processed
    log.log_output = log_output
    return log


def _make_schedule_mock(agent_name: str, display_name: str) -> MagicMock:
    """Create a mock schedule object for get_all()."""
    schedule = MagicMock()
    schedule.agent_name = agent_name
    schedule.display_name = display_name
    return schedule


def _build_service() -> tuple[ExecutionLogService, AsyncMock, AsyncMock]:
    """Build service with mock repos.

    No spec= on log_repo so we can freely set return values
    for all service methods (get_running, get_recent, get_stats, etc.).
    """
    log_repo = AsyncMock()
    schedule_repo = AsyncMock()
    schedule_repo.get_all.return_value = []
    schedule_repo.get_by_agent_name.return_value = None
    service = ExecutionLogService(log_repo, schedule_repo)
    return service, log_repo, schedule_repo


# --- End-to-end flow tests ---


class TestDispatcherToServiceFlow:
    """Test the flow from agent dispatch to dashboard display."""

    @pytest.mark.asyncio
    async def test_execution_log_created_and_shows_in_dashboard(self) -> None:
        """E2E: agent dispatched → log created → dashboard shows."""
        service, log_repo, schedule_repo = _build_service()

        running_log = _make_log(
            agent_name="health_claims_monitor",
            status="running",
            duration_seconds=None,
        )
        success_log = _make_log(
            agent_name="novel_food_monitor",
            status="success",
            items_processed=42,
        )

        log_repo.get_running.return_value = [running_log]

        def _get_recent(hours: int, status: str) -> list:
            expected_hours = {"success": 24, "failed": 168, "incomplete": 168}
            assert hours == expected_hours.get(status, 24), (
                f"Unexpected hours={hours} for status={status}"
            )
            return {"success": [success_log], "failed": [], "incomplete": []}.get(status, [])

        log_repo.get_recent.side_effect = _get_recent
        log_repo.get_stats.return_value = {
            "total": 5, "success": 4, "avg_duration": 45.0,
        }

        schedule_repo.get_all.return_value = [
            _make_schedule_mock("health_claims_monitor", "Health Claims Monitor"),
            _make_schedule_mock("novel_food_monitor", "Novel Food Monitor"),
        ]

        summary = await service.get_dashboard_summary()

        assert isinstance(summary, DashboardSummaryDTO)
        assert len(summary.running) == 1
        assert summary.running[0].agent_name == "health_claims_monitor"
        assert summary.running[0].display_name == "Health Claims Monitor"
        assert len(summary.recent_completions) == 1
        assert summary.recent_completions[0].items_processed == 42
        assert summary.total_executions_24h == 5
        assert summary.success_rate_24h == 80.0

    @pytest.mark.asyncio
    async def test_failed_agent_creates_log_with_error(self) -> None:
        """E2E: failed agent → log with error_message + traceback."""
        service, log_repo, schedule_repo = _build_service()

        failed_log = _make_log(
            agent_name="competitor_scanner",
            status="failed",
            error_message="Connection timeout",
            error_traceback="Traceback...\nTimeoutError",
            log_output="Starting scan...\nConnecting...\nERROR: timeout",
        )

        log_repo.get_by_id.return_value = failed_log

        detail = await service.get_execution_detail(str(failed_log.id))

        assert isinstance(detail, ExecutionLogDetailDTO)
        assert detail.status == "failed"
        assert detail.error_message == "Connection timeout"
        assert detail.error_traceback == "Traceback...\nTimeoutError"
        assert "ERROR: timeout" in detail.log_output


class TestLogCaptureIntegration:
    """Test log capture integration with execution detail view."""

    @pytest.mark.asyncio
    async def test_captured_log_visible_in_detail(self) -> None:
        """Log capture output is stored and visible in detail view."""
        import logging

        # Simulate log capture during agent execution
        test_logger = logging.getLogger("test.integration.capture")
        test_logger.setLevel(logging.DEBUG)
        handler = LogCaptureHandler.attach("test.integration.capture")

        test_logger.info("Starting scan...")
        test_logger.info("Processing 10 items")
        test_logger.warning("Slow response from API")
        test_logger.info("Scan complete")

        output = handler.get_output()
        handler.detach()

        assert "Starting scan..." in output
        assert "Processing 10 items" in output
        assert "Slow response from API" in output
        assert "Scan complete" in output

        # Now verify the service can return this in a detail view
        service, log_repo, schedule_repo = _build_service()
        log = _make_log(log_output=output)
        log_repo.get_by_id.return_value = log

        detail = await service.get_execution_detail(str(log.id))
        assert "Processing 10 items" in detail.log_output

    def test_log_capture_handler_detach_cleanup(self) -> None:
        """Handler detach removes handler from logger (resource safety)."""
        import logging

        logger = logging.getLogger("test.integration.cleanup")
        handler = LogCaptureHandler.attach("test.integration.cleanup")

        initial_count = len(logger.handlers)
        handler.detach()
        assert len(logger.handlers) == initial_count - 1

    def test_log_capture_max_lines_respected(self) -> None:
        """Handler respects max_lines cap."""
        import logging

        handler = LogCaptureHandler(max_lines=5)
        logger = logging.getLogger("test.integration.maxlines")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        for i in range(10):
            logger.info("Line %d", i)

        output = handler.get_output()
        lines = [l for l in output.strip().split("\n") if l.strip()]
        assert len(lines) == 5

        logger.removeHandler(handler)


class TestFilteredHistoryIntegration:
    """Test filtered execution history through the service layer."""

    @pytest.mark.asyncio
    async def test_filter_by_agent_name(self) -> None:
        """Filter by agent_name returns only matching executions."""
        service, log_repo, schedule_repo = _build_service()

        claims_log = _make_log(agent_name="health_claims_monitor")
        log_repo.get_filtered.return_value = ([claims_log], 1)

        filters = ExecutionLogFilterDTO(agent_name="health_claims_monitor")
        result = await service.get_filtered_executions(filters)

        assert result[1] == 1
        assert result[0][0].agent_name == "health_claims_monitor"
        log_repo.get_filtered.assert_called_once_with(filters)

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self) -> None:
        """Filter by date range returns only matching executions."""
        service, log_repo, schedule_repo = _build_service()

        now = datetime.now(UTC)
        log = _make_log(started_at=now - timedelta(hours=2))
        log_repo.get_filtered.return_value = ([log], 1)

        filters = ExecutionLogFilterDTO(
            date_from=now - timedelta(hours=3),
            date_to=now,
        )
        result = await service.get_filtered_executions(filters)
        assert result[1] == 1

    @pytest.mark.asyncio
    async def test_filter_by_status(self) -> None:
        """Filter by status returns only matching executions."""
        service, log_repo, schedule_repo = _build_service()

        failed_log = _make_log(status="failed", error_message="boom")
        log_repo.get_filtered.return_value = ([failed_log], 1)

        filters = ExecutionLogFilterDTO(status="failed")
        result = await service.get_filtered_executions(filters)
        assert result[1] == 1
        assert result[0][0].status == "failed"


class TestDashboardAggregation:
    """Test dashboard summary aggregation with mixed statuses."""

    @pytest.mark.asyncio
    async def test_mixed_statuses_aggregate_correctly(self) -> None:
        """Mix of running, success, failed → correct aggregation."""
        service, log_repo, schedule_repo = _build_service()

        running = [_make_log(agent_name="a1", status="running")]
        completions = [
            _make_log(agent_name="a2", status="success", items_processed=10),
            _make_log(agent_name="a3", status="success", items_processed=20),
        ]
        failures = [
            _make_log(agent_name="a4", status="failed", error_message="err"),
        ]

        log_repo.get_running.return_value = running

        def _get_recent(hours: int, status: str) -> list:
            expected_hours = {"success": 24, "failed": 168, "incomplete": 168}
            assert hours == expected_hours.get(status, 24), (
                f"Unexpected hours={hours} for status={status}"
            )
            return {"success": completions, "failed": failures, "incomplete": []}.get(status, [])

        log_repo.get_recent.side_effect = _get_recent
        log_repo.get_stats.return_value = {
            "total": 10, "success": 7, "avg_duration": 30.0,
        }

        summary = await service.get_dashboard_summary()

        assert len(summary.running) == 1
        assert len(summary.recent_completions) == 2
        assert len(summary.recent_failures) == 1
        assert summary.total_executions_24h == 10
        assert summary.success_rate_24h == 70.0
        assert summary.avg_duration_24h == 30.0


class TestPagination:
    """Test execution history pagination through the service."""

    @pytest.mark.asyncio
    async def test_pagination_first_page(self) -> None:
        """30 executions, limit=25 → first page 25, has_more indicated."""
        service, log_repo, schedule_repo = _build_service()

        logs = [_make_log(agent_name=f"agent_{i}") for i in range(25)]
        log_repo.get_filtered.return_value = (logs, 30)

        filters = ExecutionLogFilterDTO(limit=25, offset=0)
        executions, total = await service.get_filtered_executions(filters)

        assert len(executions) == 25
        assert total == 30  # total_count indicates more exist

    @pytest.mark.asyncio
    async def test_pagination_second_page(self) -> None:
        """Offset=25 returns remaining 5 executions."""
        service, log_repo, schedule_repo = _build_service()

        logs = [_make_log(agent_name=f"agent_{i}") for i in range(5)]
        log_repo.get_filtered.return_value = (logs, 30)

        filters = ExecutionLogFilterDTO(limit=25, offset=25)
        executions, total = await service.get_filtered_executions(filters)

        assert len(executions) == 5
        assert total == 30


class TestExecutionEventsIntegration:
    """Test execution event emission and subscription."""

    @pytest.mark.asyncio
    async def test_event_emitted_on_start(self) -> None:
        """STARTED event emitted when execution begins."""
        import asyncio

        emitter = ExecutionEventEmitter()
        received = []

        async def collect():
            async for event in emitter.subscribe():
                received.append(event)
                break  # Collect one

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)

        await emitter.emit(
            ExecutionEvent(
                event_type=ExecutionEventType.STARTED,
                agent_name="health_claims_monitor",
                execution_id="test-uuid",
                data={"trigger_type": "scheduled"},
            )
        )

        await asyncio.wait_for(task, timeout=1.0)

        assert len(received) == 1
        assert received[0].event_type == ExecutionEventType.STARTED
        assert received[0].agent_name == "health_claims_monitor"

    @pytest.mark.asyncio
    async def test_event_emitted_on_complete(self) -> None:
        """COMPLETED event emitted when execution succeeds."""
        import asyncio

        emitter = ExecutionEventEmitter()
        received = []

        async def collect():
            async for event in emitter.subscribe():
                received.append(event)
                break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)

        await emitter.emit(
            ExecutionEvent(
                event_type=ExecutionEventType.COMPLETED,
                agent_name="novel_food_monitor",
                execution_id="test-uuid-2",
                data={"status": "success", "duration": 45.0},
            )
        )

        await asyncio.wait_for(task, timeout=1.0)

        assert received[0].event_type == ExecutionEventType.COMPLETED
        assert received[0].data["status"] == "success"

    @pytest.mark.asyncio
    async def test_event_emitted_on_failure(self) -> None:
        """FAILED event emitted when execution fails."""
        import asyncio

        emitter = ExecutionEventEmitter()
        received = []

        async def collect():
            async for event in emitter.subscribe():
                received.append(event)
                break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)

        await emitter.emit(
            ExecutionEvent(
                event_type=ExecutionEventType.FAILED,
                agent_name="competitor_scanner",
                execution_id="test-uuid-3",
                data={"error": "Connection timeout"},
            )
        )

        await asyncio.wait_for(task, timeout=1.0)

        assert received[0].event_type == ExecutionEventType.FAILED
        assert received[0].data["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_event_to_dict_serialization(self) -> None:
        """Events can be serialized to JSON-compatible dict."""
        event = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            agent_name="health_claims_monitor",
            execution_id="uuid-123",
            data={"trigger_type": "manual"},
        )

        d = event.to_dict()

        assert d["event_type"] == "execution_started"
        assert d["agent_name"] == "health_claims_monitor"
        assert d["execution_id"] == "uuid-123"
        assert d["data"]["trigger_type"] == "manual"
        assert "timestamp" in d
        assert "event_id" in d


class TestRetryIntegration:
    """Test retry flow from dashboard through ManualTriggerService."""

    @pytest.mark.asyncio
    @patch("core.scheduling.manual_trigger_service._get_agent_runners")
    async def test_retry_failed_execution(self, mock_runners: MagicMock) -> None:
        """Retry failed execution → ManualTriggerService.trigger_agent called."""
        mock_runners.return_value = {
            "competitor_scanner": MagicMock(),
        }

        repo = AsyncMock()
        repo.get_by_agent_name.return_value = None  # Not currently running
        repo.update_run_status.return_value = None
        config = _MockConfig()

        trigger_service = ManualTriggerService(repository=repo, config=config)
        result = await trigger_service.trigger_agent(
            "competitor_scanner", triggered_by="operator"
        )

        assert result.status == "queued"
        assert result.agent_name == "competitor_scanner"
        assert result.triggered_by == "operator"
        repo.update_run_status.assert_called_once()

    @pytest.mark.asyncio
    @patch("core.scheduling.manual_trigger_service._get_agent_runners")
    async def test_retry_already_running_rejected(self, mock_runners: MagicMock) -> None:
        """Retry of already-running agent is rejected."""
        mock_runners.return_value = {
            "competitor_scanner": MagicMock(),
        }

        schedule = MagicMock()
        schedule.last_run_status = "running"

        repo = AsyncMock()
        repo.get_by_agent_name.return_value = schedule
        config = _MockConfig()

        trigger_service = ManualTriggerService(repository=repo, config=config)
        result = await trigger_service.trigger_agent("competitor_scanner")

        assert result.status == "already_running"
