"""Tests for pending trigger integration in _run_scheduled_agent.

Story 7-7, Task 6.3: Integration tests for pending trigger re-enqueue.
Target: 5+ tests.
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
    """Create a mock _schedule_session context manager."""

    @asynccontextmanager
    async def _fake_session():
        yield mock_repo

    return _fake_session


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


class TestPendingTriggerIntegration:
    """Tests for pending trigger check in _run_scheduled_agent."""

    @pytest.mark.asyncio
    async def test_agent_completes_and_checks_pending(self):
        """After agent completes, pending trigger store is checked."""
        from core.scheduling.jobs import _run_scheduled_agent
        from core.scheduling.manual_trigger_service import PendingTriggerStore

        mock_repo = AsyncMock()
        mock_ctx = {"redis": AsyncMock()}

        # Use a fresh store to avoid test interference
        test_store = PendingTriggerStore()

        with (
            patch("core.scheduling.jobs._schedule_session", _mock_schedule_session(mock_repo)),
            patch("core.scheduling.jobs.AGENT_RUNNERS", {"test_agent": AsyncMock(return_value={"status": "success"})}),
            patch("core.scheduling.manual_trigger_service.pending_trigger_store", test_store),
        ):
            result = await _run_scheduled_agent(mock_ctx, "test_agent")

        assert result["status"] == "success"
        # No pending trigger, so no re-enqueue
        mock_ctx["redis"].enqueue_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_pending_trigger_re_enqueues_after_completion(self):
        """When pending trigger exists, agent is re-enqueued after completion."""
        from core.scheduling.jobs import _run_scheduled_agent
        from core.scheduling.manual_trigger_service import PendingTriggerStore

        mock_repo = AsyncMock()
        mock_ctx = {"redis": AsyncMock()}

        test_store = PendingTriggerStore()
        test_store.add("test_agent", "operator")

        with (
            patch("core.scheduling.jobs._schedule_session", _mock_schedule_session(mock_repo)),
            patch("core.scheduling.jobs.AGENT_RUNNERS", {"test_agent": AsyncMock(return_value={"status": "success"})}),
            patch("core.scheduling.manual_trigger_service.pending_trigger_store", test_store),
        ):
            result = await _run_scheduled_agent(mock_ctx, "test_agent")

        assert result["status"] == "success"
        mock_ctx["redis"].enqueue_job.assert_called_once_with(
            "_run_scheduled_agent", "test_agent"
        )

    @pytest.mark.asyncio
    async def test_pending_trigger_re_enqueues_after_failure(self):
        """Pending triggers are checked even after agent failure."""
        from core.scheduling.jobs import _run_scheduled_agent
        from core.scheduling.manual_trigger_service import PendingTriggerStore

        mock_repo = AsyncMock()
        mock_ctx = {"redis": AsyncMock()}

        test_store = PendingTriggerStore()
        test_store.add("test_agent", "operator")

        async def _failing_runner(ctx):
            raise RuntimeError("Agent failed!")

        with (
            patch("core.scheduling.jobs._schedule_session", _mock_schedule_session(mock_repo)),
            patch("core.scheduling.jobs.AGENT_RUNNERS", {"test_agent": _failing_runner}),
            patch("core.scheduling.manual_trigger_service.pending_trigger_store", test_store),
        ):
            result = await _run_scheduled_agent(mock_ctx, "test_agent")

        assert result["status"] == "failed"
        # Still re-enqueued despite failure
        mock_ctx["redis"].enqueue_job.assert_called_once_with(
            "_run_scheduled_agent", "test_agent"
        )

    @pytest.mark.asyncio
    async def test_pending_trigger_pops_after_re_enqueue(self):
        """Pending trigger is removed from store after re-enqueue."""
        from core.scheduling.jobs import _run_scheduled_agent
        from core.scheduling.manual_trigger_service import PendingTriggerStore

        mock_repo = AsyncMock()
        mock_ctx = {"redis": AsyncMock()}

        test_store = PendingTriggerStore()
        test_store.add("test_agent", "operator")

        with (
            patch("core.scheduling.jobs._schedule_session", _mock_schedule_session(mock_repo)),
            patch("core.scheduling.jobs.AGENT_RUNNERS", {"test_agent": AsyncMock(return_value={"status": "success"})}),
            patch("core.scheduling.manual_trigger_service.pending_trigger_store", test_store),
        ):
            await _run_scheduled_agent(mock_ctx, "test_agent")

        # Store should be empty now
        assert test_store.get("test_agent") is None

    @pytest.mark.asyncio
    async def test_pending_trigger_check_does_not_block_on_error(self):
        """If pending trigger check fails, agent result is still returned."""
        from core.scheduling.jobs import _run_scheduled_agent

        mock_repo = AsyncMock()
        mock_ctx = {"redis": AsyncMock()}

        with (
            patch("core.scheduling.jobs._schedule_session", _mock_schedule_session(mock_repo)),
            patch("core.scheduling.jobs.AGENT_RUNNERS", {"test_agent": AsyncMock(return_value={"status": "success"})}),
            patch(
                "core.scheduling.jobs._check_pending_triggers",
                AsyncMock(side_effect=Exception("Store error")),
            ),
        ):
            # Should not raise — pending trigger check is non-blocking
            result = await _run_scheduled_agent(mock_ctx, "test_agent")

        assert result["status"] == "success"
