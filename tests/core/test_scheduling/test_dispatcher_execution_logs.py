"""Tests for execution log integration in _run_scheduled_agent dispatcher.

Story 7-8, Task 5.3: Dispatcher integration tests.
Target: 8+ tests.
"""

import pytest
import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# Mock core.database before importing jobs module
mock_database = MagicMock()
mock_database.get_async_session = MagicMock()
sys.modules.setdefault("core.database", mock_database)


from core.scheduling.jobs import _run_scheduled_agent, AGENT_RUNNERS


@pytest.fixture
def mock_ctx():
    """ARQ context with mocked Redis."""
    return {"redis": AsyncMock()}


@pytest.fixture
def mock_runner():
    """Successful agent runner mock."""
    runner = AsyncMock()
    runner.return_value = {"status": "success", "items_processed": 42}
    return runner


@pytest.fixture
def mock_failed_runner():
    """Failed agent runner mock."""
    runner = AsyncMock()
    runner.side_effect = Exception("Connection timeout")
    return runner


class TestDispatcherExecutionLogs:
    """Tests for execution log creation in _run_scheduled_agent."""

    @pytest.mark.asyncio
    async def test_success_creates_execution_log(self, mock_ctx, mock_runner):
        """Successful agent run creates execution log with status=success."""
        with (
            patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}),
            patch("core.scheduling.jobs._schedule_session") as mock_session_ctx,
            patch("core.scheduling.jobs._execution_log_session") as mock_log_session_ctx,
            patch("core.scheduling.jobs._check_pending_triggers", new_callable=AsyncMock),
        ):
            mock_repo = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_repo)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_log_service = AsyncMock()
            mock_log_service.start_execution.return_value = MagicMock(id="test-id")
            mock_log_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_log_service)
            mock_log_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _run_scheduled_agent(mock_ctx, "test_agent")

            assert result["status"] == "success"
            mock_log_service.start_execution.assert_awaited_once()
            mock_log_service.complete_execution.assert_awaited_once()
            # Check complete_execution called with status=success
            call_kwargs = mock_log_service.complete_execution.call_args.kwargs
            assert call_kwargs["status"] == "success"

    @pytest.mark.asyncio
    async def test_failure_creates_execution_log_with_error(self, mock_ctx, mock_failed_runner):
        """Failed agent run creates execution log with error details."""
        with (
            patch.dict(AGENT_RUNNERS, {"test_agent": mock_failed_runner}),
            patch("core.scheduling.jobs._schedule_session") as mock_session_ctx,
            patch("core.scheduling.jobs._execution_log_session") as mock_log_session_ctx,
            patch("core.scheduling.jobs._check_pending_triggers", new_callable=AsyncMock),
        ):
            mock_repo = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_repo)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_log_service = AsyncMock()
            mock_log_service.start_execution.return_value = MagicMock(id="test-id")
            mock_log_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_log_service)
            mock_log_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _run_scheduled_agent(mock_ctx, "test_agent")

            assert result["status"] == "failed"
            mock_log_service.complete_execution.assert_awaited_once()
            call_kwargs = mock_log_service.complete_execution.call_args.kwargs
            assert call_kwargs["status"] == "failed"
            assert "Connection timeout" in call_kwargs["error_message"]
            assert call_kwargs["error_traceback"] is not None

    @pytest.mark.asyncio
    async def test_execution_log_failure_does_not_block_agent(self, mock_ctx, mock_runner):
        """Execution log creation failure doesn't block agent execution."""
        with (
            patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}),
            patch("core.scheduling.jobs._schedule_session") as mock_session_ctx,
            patch("core.scheduling.jobs._execution_log_session") as mock_log_session_ctx,
            patch("core.scheduling.jobs._check_pending_triggers", new_callable=AsyncMock),
        ):
            mock_repo = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_repo)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            # Make log service fail
            mock_log_service = AsyncMock()
            mock_log_service.start_execution.side_effect = Exception("DB connection failed")
            mock_log_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_log_service)
            mock_log_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            # Agent should still succeed despite log failure
            result = await _run_scheduled_agent(mock_ctx, "test_agent")
            assert result["status"] == "success"
            mock_runner.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_trigger_type_scheduled_default(self, mock_ctx, mock_runner):
        """trigger_type defaults to 'scheduled' when not passed."""
        with (
            patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}),
            patch("core.scheduling.jobs._schedule_session") as mock_session_ctx,
            patch("core.scheduling.jobs._execution_log_session") as mock_log_session_ctx,
            patch("core.scheduling.jobs._check_pending_triggers", new_callable=AsyncMock),
        ):
            mock_repo = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_repo)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_log_service = AsyncMock()
            mock_log_service.start_execution.return_value = MagicMock(id="test-id")
            mock_log_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_log_service)
            mock_log_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            await _run_scheduled_agent(mock_ctx, "test_agent")

            call_kwargs = mock_log_service.start_execution.call_args.kwargs
            assert call_kwargs["trigger_type"] == "scheduled"

    @pytest.mark.asyncio
    async def test_trigger_type_manual_passed_as_arg(self, mock_ctx, mock_runner):
        """trigger_type is 'manual' when passed explicitly by caller."""
        with (
            patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}),
            patch("core.scheduling.jobs._schedule_session") as mock_session_ctx,
            patch("core.scheduling.jobs._execution_log_session") as mock_log_session_ctx,
            patch("core.scheduling.jobs._check_pending_triggers", new_callable=AsyncMock),
        ):
            mock_repo = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_repo)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_log_service = AsyncMock()
            mock_log_service.start_execution.return_value = MagicMock(id="test-id")
            mock_log_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_log_service)
            mock_log_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            await _run_scheduled_agent(mock_ctx, "test_agent", "manual")

            call_kwargs = mock_log_service.start_execution.call_args.kwargs
            assert call_kwargs["trigger_type"] == "manual"

    @pytest.mark.asyncio
    async def test_log_output_captured(self, mock_ctx, mock_runner):
        """Log output from agent execution is captured."""
        with (
            patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}),
            patch("core.scheduling.jobs._schedule_session") as mock_session_ctx,
            patch("core.scheduling.jobs._execution_log_session") as mock_log_session_ctx,
            patch("core.scheduling.jobs._check_pending_triggers", new_callable=AsyncMock),
        ):
            mock_repo = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_repo)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_log_service = AsyncMock()
            mock_log_service.start_execution.return_value = MagicMock(id="test-id")
            mock_log_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_log_service)
            mock_log_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            await _run_scheduled_agent(mock_ctx, "test_agent")

            # complete_execution should be called with log_output parameter
            call_kwargs = mock_log_service.complete_execution.call_args.kwargs
            assert "log_output" in call_kwargs

    @pytest.mark.asyncio
    async def test_not_found_agent_no_execution_log(self, mock_ctx):
        """Agent not in registry doesn't create execution log."""
        with (
            patch("core.scheduling.jobs._schedule_session") as mock_session_ctx,
            patch("core.scheduling.jobs._execution_log_session") as mock_log_session_ctx,
        ):
            mock_repo = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_repo)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_log_service = AsyncMock()
            mock_log_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_log_service)
            mock_log_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _run_scheduled_agent(mock_ctx, "nonexistent_agent")
            assert result["status"] == "failed"
            # start_execution should NOT have been called for nonexistent agent
            mock_log_service.start_execution.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_summary_passed_to_complete(self, mock_ctx, mock_runner):
        """Runner result dict is passed as summary to complete_execution."""
        with (
            patch.dict(AGENT_RUNNERS, {"test_agent": mock_runner}),
            patch("core.scheduling.jobs._schedule_session") as mock_session_ctx,
            patch("core.scheduling.jobs._execution_log_session") as mock_log_session_ctx,
            patch("core.scheduling.jobs._check_pending_triggers", new_callable=AsyncMock),
        ):
            mock_repo = AsyncMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_repo)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_log_service = AsyncMock()
            mock_log_service.start_execution.return_value = MagicMock(id="test-id")
            mock_log_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_log_service)
            mock_log_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            await _run_scheduled_agent(mock_ctx, "test_agent")

            call_kwargs = mock_log_service.complete_execution.call_args.kwargs
            assert call_kwargs["summary"] == {"status": "success", "items_processed": 42}
