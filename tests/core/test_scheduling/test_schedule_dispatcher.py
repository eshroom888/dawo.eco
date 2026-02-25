"""Tests for schedule dispatcher and agent runner.

Story 7-6, Task 5.4: Dispatcher tests covering due schedule detection,
overlapping prevention, status updates, and agent name resolution.
Target: 20+ tests.
"""

import pytest
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from core.scheduling.models import AgentSchedule


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
        "last_run_at": None,
        "last_run_status": None,
        "last_run_duration_seconds": None,
        "last_run_summary": None,
        "next_run_at": datetime.now(UTC) - timedelta(minutes=5),
        "config_source": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "description": None,
    }
    defaults.update(kwargs)
    return AgentSchedule(**defaults)


def _mock_schedule_session(mock_repo):
    """Create a mock _schedule_session that yields mock_repo as context manager."""

    @asynccontextmanager
    async def _fake_session():
        yield mock_repo

    return _fake_session


# Patch sys.modules for database deps that don't exist in test env
@pytest.fixture(autouse=True)
def mock_database_modules():
    """Mock core.database module for job tests."""
    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_db.get_async_session = MagicMock(return_value=mock_session)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch.dict(sys.modules, {"core.database": mock_db}):
        yield mock_db


class TestCheckDueSchedules:
    """Tests for _check_due_schedules dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatches_due_schedules(self):
        """Finds and dispatches due schedules."""
        from core.scheduling.jobs import _check_due_schedules

        due_schedule = _make_schedule(
            agent_name="health_claims_monitor",
            last_run_status="success",
        )

        mock_repo = AsyncMock()
        mock_repo.get_due_schedules.return_value = [due_schedule]
        mock_repo.update_run_status = AsyncMock()

        mock_ctx = {"redis": AsyncMock()}
        mock_ctx["redis"].enqueue_job = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            result = await _check_due_schedules(mock_ctx)

        assert result["checked"] == 1
        assert result["dispatched"] == 1

    @pytest.mark.asyncio
    async def test_skips_running_schedules(self):
        """Skips schedules already in 'running' status."""
        from core.scheduling.jobs import _check_due_schedules

        # get_due_schedules already filters running, so result is empty
        mock_repo = AsyncMock()
        mock_repo.get_due_schedules.return_value = []

        mock_ctx = {"redis": AsyncMock()}

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            result = await _check_due_schedules(mock_ctx)

        assert result["dispatched"] == 0

    @pytest.mark.asyncio
    async def test_returns_count_dict(self):
        """Returns dict with checked, dispatched, skipped_running counts."""
        from core.scheduling.jobs import _check_due_schedules

        mock_repo = AsyncMock()
        mock_repo.get_due_schedules.return_value = []

        mock_ctx = {"redis": AsyncMock()}

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            result = await _check_due_schedules(mock_ctx)

        assert "checked" in result
        assert "dispatched" in result
        assert "skipped_running" in result


class TestRunScheduledAgent:
    """Tests for _run_scheduled_agent."""

    @pytest.mark.asyncio
    async def test_resolves_known_agent(self):
        """Resolves and runs a known agent from registry."""
        from core.scheduling.jobs import _run_scheduled_agent, AGENT_RUNNERS

        mock_runner = AsyncMock(return_value={"status": "success", "items_processed": 5})
        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ), patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}):
            result = await _run_scheduled_agent({"redis": AsyncMock()}, "test_agent")

        assert result["status"] == "success"
        mock_runner.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_error(self):
        """Returns error for unknown agent name."""
        from core.scheduling.jobs import _run_scheduled_agent

        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            result = await _run_scheduled_agent(
                {"redis": AsyncMock()}, "totally_unknown_agent"
            )

        assert result["status"] == "failed"
        assert "not found" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_updates_status_on_success(self):
        """Updates run status to 'success' after successful execution."""
        from core.scheduling.jobs import _run_scheduled_agent, AGENT_RUNNERS

        mock_runner = AsyncMock(return_value={"status": "success"})
        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ), patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}):
            await _run_scheduled_agent({"redis": AsyncMock()}, "test_agent")

        mock_repo.update_run_status.assert_called_once()
        call_args = mock_repo.update_run_status.call_args
        assert call_args.kwargs.get("status") == "success"

    @pytest.mark.asyncio
    async def test_updates_status_on_failure(self):
        """Updates run status to 'failed' when runner raises."""
        from core.scheduling.jobs import _run_scheduled_agent, AGENT_RUNNERS

        mock_runner = AsyncMock(side_effect=RuntimeError("Boom"))
        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ), patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}):
            result = await _run_scheduled_agent({"redis": AsyncMock()}, "test_agent")

        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_validates_agent_name_against_registry(self):
        """Does not execute arbitrary agent names (security)."""
        from core.scheduling.jobs import _run_scheduled_agent

        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            result = await _run_scheduled_agent(
                {"redis": AsyncMock()},
                "'; DROP TABLE agent_schedules; --",
            )

        assert result["status"] == "failed"


class TestAgentRunnersRegistry:
    """Tests for the AGENT_RUNNERS registry."""

    def test_registry_has_expected_agents(self):
        """Registry contains all 8 expected agent runners."""
        from core.scheduling.jobs import AGENT_RUNNERS

        expected = {
            "health_claims_monitor",
            "novel_food_monitor",
            "mattilsynet_monitor",
            "competitor_scanner",
            "lead_scanner",
            "shopify_attribution_poll",
            "post_publish_scoring",
            "feedback_loop",
        }
        assert set(AGENT_RUNNERS.keys()) == expected

    def test_all_runners_are_callable(self):
        """All registry entries are callable."""
        from core.scheduling.jobs import AGENT_RUNNERS

        for name, runner in AGENT_RUNNERS.items():
            assert callable(runner), f"Runner for {name} is not callable"


class TestWorkerSettingsIntegration:
    """Tests that dispatcher is registered in WorkerSettings."""

    def test_check_due_schedules_in_cron_jobs(self):
        """_check_due_schedules is registered as a cron job."""
        from core.scheduling.jobs import WorkerSettings

        cron_funcs = [job.coroutine for job in WorkerSettings.cron_jobs]
        # Look for _check_due_schedules by name
        func_names = [f.__name__ if hasattr(f, "__name__") else str(f) for f in cron_funcs]
        assert "_check_due_schedules" in func_names

    def test_run_scheduled_agent_in_functions(self):
        """_run_scheduled_agent is registered in functions list."""
        from core.scheduling.jobs import WorkerSettings

        func_names = [
            f.__name__ if hasattr(f, "__name__") else str(f)
            for f in WorkerSettings.functions
        ]
        assert "_run_scheduled_agent" in func_names

    def test_existing_cron_jobs_preserved(self):
        """Existing hardcoded cron jobs still present as fallback."""
        from core.scheduling.jobs import WorkerSettings

        cron_funcs = [job.coroutine for job in WorkerSettings.cron_jobs]
        func_names = [f.__name__ if hasattr(f, "__name__") else str(f) for f in cron_funcs]
        assert "_run_shopify_attribution_poll" in func_names
        assert "_run_post_publish_scoring" in func_names
        assert "_run_feedback_loop" in func_names

    def test_dispatcher_runs_every_minute(self):
        """_check_due_schedules cron configured with minute=None (every minute)."""
        from core.scheduling.jobs import WorkerSettings

        for job in WorkerSettings.cron_jobs:
            func_name = getattr(job.coroutine, "__name__", "")
            if func_name == "_check_due_schedules":
                # minute=None means every minute in ARQ
                assert job.minute is None
                return
        pytest.fail("_check_due_schedules not found in cron_jobs")


class TestCheckDueSchedulesAdvanced:
    """Additional dispatcher tests for edge cases."""

    @pytest.mark.asyncio
    async def test_dispatches_multiple_schedules(self):
        """Dispatches all due schedules in a single check."""
        from core.scheduling.jobs import _check_due_schedules

        schedules = [
            _make_schedule(agent_name="health_claims_monitor"),
            _make_schedule(agent_name="novel_food_monitor"),
            _make_schedule(agent_name="competitor_scanner"),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_due_schedules.return_value = schedules
        mock_repo.update_run_status = AsyncMock()

        mock_ctx = {"redis": AsyncMock()}
        mock_ctx["redis"].enqueue_job = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            result = await _check_due_schedules(mock_ctx)

        assert result["checked"] == 3
        assert result["dispatched"] == 3

    @pytest.mark.asyncio
    async def test_enqueues_via_redis(self):
        """Enqueues _run_scheduled_agent job via Redis for each due schedule."""
        from core.scheduling.jobs import _check_due_schedules

        schedule = _make_schedule(agent_name="lead_scanner")

        mock_repo = AsyncMock()
        mock_repo.get_due_schedules.return_value = [schedule]
        mock_repo.update_run_status = AsyncMock()

        mock_redis = AsyncMock()
        mock_ctx = {"redis": mock_redis}

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            await _check_due_schedules(mock_ctx)

        mock_redis.enqueue_job.assert_called_once_with(
            "_run_scheduled_agent", "lead_scanner"
        )

    @pytest.mark.asyncio
    async def test_handles_no_redis_in_context(self):
        """Returns early with error when Redis is missing — no agents stuck in running."""
        from core.scheduling.jobs import _check_due_schedules

        # No redis key in ctx
        mock_ctx = {}

        result = await _check_due_schedules(mock_ctx)

        # Should return early without dispatching — prevents agents stuck in "running"
        assert result["dispatched"] == 0
        assert result["checked"] == 0
        assert result["error"] == "no_redis"

    @pytest.mark.asyncio
    async def test_dispatcher_handles_exception_gracefully(self):
        """Returns error dict when dispatcher encounters exception."""
        from core.scheduling.jobs import _check_due_schedules

        mock_repo = AsyncMock()
        mock_repo.get_due_schedules.side_effect = RuntimeError("DB connection lost")

        mock_ctx = {"redis": AsyncMock()}

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            result = await _check_due_schedules(mock_ctx)

        assert result["checked"] == 0
        assert result["dispatched"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_calculates_next_run_after_dispatch(self):
        """Sets next_run_at via update_run_status after dispatching."""
        from core.scheduling.jobs import _check_due_schedules

        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            schedule_cron="0 5 * * 0",
            timezone="UTC",
        )

        mock_repo = AsyncMock()
        mock_repo.get_due_schedules.return_value = [schedule]
        mock_repo.update_run_status = AsyncMock()

        mock_ctx = {"redis": AsyncMock()}

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            await _check_due_schedules(mock_ctx)

        # Single update_run_status call with status="running" and next_run set
        mock_repo.update_run_status.assert_called_once()
        call_kwargs = mock_repo.update_run_status.call_args.kwargs
        assert call_kwargs["status"] == "running"
        assert call_kwargs["next_run"] is not None


class TestRunScheduledAgentAdvanced:
    """Additional runner tests for edge cases."""

    @pytest.mark.asyncio
    async def test_runner_tracks_duration(self):
        """Records execution duration in status update."""
        from core.scheduling.jobs import _run_scheduled_agent, AGENT_RUNNERS

        mock_runner = AsyncMock(return_value={"status": "success"})
        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ), patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}):
            await _run_scheduled_agent({"redis": AsyncMock()}, "test_agent")

        call_kwargs = mock_repo.update_run_status.call_args.kwargs
        assert "duration" in call_kwargs
        assert isinstance(call_kwargs["duration"], float)
        assert call_kwargs["duration"] >= 0

    @pytest.mark.asyncio
    async def test_runner_handles_incomplete_status(self):
        """Passes 'incomplete' status through from runner result."""
        from core.scheduling.jobs import _run_scheduled_agent, AGENT_RUNNERS

        mock_runner = AsyncMock(
            return_value={"status": "incomplete", "items_processed": 3}
        )
        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ), patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}):
            result = await _run_scheduled_agent({"redis": AsyncMock()}, "test_agent")

        assert result["status"] == "incomplete"
        call_kwargs = mock_repo.update_run_status.call_args.kwargs
        assert call_kwargs["status"] == "incomplete"

    @pytest.mark.asyncio
    async def test_runner_stores_summary_on_success(self):
        """Stores runner result dict as summary in status update."""
        from core.scheduling.jobs import _run_scheduled_agent, AGENT_RUNNERS

        runner_result = {"status": "success", "items_processed": 10, "errors": []}
        mock_runner = AsyncMock(return_value=runner_result)
        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ), patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}):
            await _run_scheduled_agent({"redis": AsyncMock()}, "test_agent")

        call_kwargs = mock_repo.update_run_status.call_args.kwargs
        assert call_kwargs["summary"] == runner_result

    @pytest.mark.asyncio
    async def test_unknown_agent_updates_status_to_failed(self):
        """Updates DB status to failed when agent not in registry."""
        from core.scheduling.jobs import _run_scheduled_agent

        mock_repo = AsyncMock()

        with patch(
            "core.scheduling.jobs._schedule_session",
            _mock_schedule_session(mock_repo),
        ):
            await _run_scheduled_agent({"redis": AsyncMock()}, "nonexistent_agent")

        mock_repo.update_run_status.assert_called_once()
        call_kwargs = mock_repo.update_run_status.call_args.kwargs
        assert call_kwargs["status"] == "failed"
