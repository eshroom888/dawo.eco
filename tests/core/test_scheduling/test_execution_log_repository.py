"""Tests for ExecutionLogRepository.

Story 7-8, Task 3.2: Repository tests with mocked AsyncSession.
Target: 18+ tests.
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

from core.scheduling.execution_log_repository import ExecutionLogRepository
from core.scheduling.models import AgentExecutionLog
from core.scheduling.dtos import ExecutionLogFilterDTO


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
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return AgentExecutionLog(**defaults)


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session):
    """Create repository with mocked session."""
    return ExecutionLogRepository(mock_session)


class TestCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_adds_and_flushes(self, repo, mock_session):
        """create() adds log to session and flushes."""
        log = _make_log()
        result = await repo.create(log)
        mock_session.add.assert_called_once_with(log)
        mock_session.flush.assert_awaited_once()
        assert result is log

    @pytest.mark.asyncio
    async def test_create_returns_log_instance(self, repo, mock_session):
        """create() returns the same AgentExecutionLog instance."""
        log = _make_log(agent_name="health_claims_monitor")
        result = await repo.create(log)
        assert result.agent_name == "health_claims_monitor"


class TestUpdateCompletion:
    """Tests for update_completion method."""

    @pytest.mark.asyncio
    async def test_update_completion_success(self, repo, mock_session):
        """update_completion updates fields and returns True."""
        log_id = uuid4()
        existing = _make_log(id=log_id, status="running")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await repo.update_completion(
            log_id=log_id,
            status="success",
            duration=120.5,
            summary={"items_processed": 42},
            error_message=None,
            error_traceback=None,
            log_output="Done.",
            items_processed=42,
        )
        assert result is True
        assert existing.status == "success"
        assert existing.duration_seconds == 120.5
        assert existing.items_processed == 42
        assert existing.log_output == "Done."
        assert existing.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_completion_not_found(self, repo, mock_session):
        """update_completion returns False when log not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.update_completion(
            log_id=uuid4(),
            status="success",
            duration=10.0,
            summary=None,
            error_message=None,
            error_traceback=None,
            log_output=None,
            items_processed=0,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_update_completion_with_error(self, repo, mock_session):
        """update_completion stores error fields on failure."""
        log_id = uuid4()
        existing = _make_log(id=log_id, status="running")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        await repo.update_completion(
            log_id=log_id,
            status="failed",
            duration=5.0,
            summary=None,
            error_message="Connection timeout",
            error_traceback="Traceback...",
            log_output="Error log",
            items_processed=0,
        )
        assert existing.error_message == "Connection timeout"
        assert existing.error_traceback == "Traceback..."


class TestGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_session):
        """get_by_id returns log when found."""
        log_id = uuid4()
        existing = _make_log(id=log_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id(log_id)
        assert result is existing

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_session):
        """get_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id(uuid4())
        assert result is None


class TestGetRunning:
    """Tests for get_running method."""

    @pytest.mark.asyncio
    async def test_get_running_returns_running_only(self, repo, mock_session):
        """get_running returns only status='running' logs."""
        running1 = _make_log(status="running")
        running2 = _make_log(status="running")

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [running1, running2]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_running()
        assert len(result) == 2
        assert all(log.status == "running" for log in result)

    @pytest.mark.asyncio
    async def test_get_running_empty(self, repo, mock_session):
        """get_running returns empty list when none running."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_running()
        assert result == []


class TestGetRecent:
    """Tests for get_recent method."""

    @pytest.mark.asyncio
    async def test_get_recent_default_24h(self, repo, mock_session):
        """get_recent queries last 24h by default."""
        log1 = _make_log(status="success")

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [log1]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_recent()
        assert len(result) == 1
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_recent_with_status_filter(self, repo, mock_session):
        """get_recent filters by status when provided."""
        log1 = _make_log(status="failed")

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [log1]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repo.get_recent(status="failed")
        assert len(result) == 1


class TestGetFiltered:
    """Tests for get_filtered method."""

    @pytest.mark.asyncio
    async def test_get_filtered_no_filters(self, repo, mock_session):
        """get_filtered with defaults returns paginated results + total."""
        log1 = _make_log()

        mock_result = MagicMock()
        mock_rows = [(log1, 1)]
        mock_result.all.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        filters = ExecutionLogFilterDTO()
        results, total = await repo.get_filtered(filters)
        assert len(results) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_filtered_with_agent_name(self, repo, mock_session):
        """get_filtered applies agent_name filter."""
        log1 = _make_log(agent_name="health_claims_monitor")

        mock_result = MagicMock()
        mock_rows = [(log1, 1)]
        mock_result.all.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        filters = ExecutionLogFilterDTO(agent_name="health_claims_monitor")
        results, total = await repo.get_filtered(filters)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_filtered_with_status(self, repo, mock_session):
        """get_filtered applies status filter."""
        log1 = _make_log(status="failed")

        mock_result = MagicMock()
        mock_rows = [(log1, 1)]
        mock_result.all.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        filters = ExecutionLogFilterDTO(status="failed")
        results, total = await repo.get_filtered(filters)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_filtered_pagination(self, repo, mock_session):
        """get_filtered respects offset and limit."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        filters = ExecutionLogFilterDTO(limit=10, offset=25)
        results, total = await repo.get_filtered(filters)
        assert results == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_filtered_empty_returns_empty_list(self, repo, mock_session):
        """get_filtered returns empty list (not None) when no results."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        filters = ExecutionLogFilterDTO()
        results, total = await repo.get_filtered(filters)
        assert results == []
        assert total == 0


class TestGetStats:
    """Tests for get_stats method."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_aggregates(self, repo, mock_session):
        """get_stats returns dict with aggregate values."""
        mock_result = MagicMock()
        mock_result.one.return_value = (10, 8, 2, 45.2)
        mock_session.execute.return_value = mock_result

        stats = await repo.get_stats()
        assert stats["total"] == 10
        assert stats["success"] == 8
        assert stats["failed"] == 2
        assert stats["avg_duration"] == 45.2

    @pytest.mark.asyncio
    async def test_get_stats_empty_database(self, repo, mock_session):
        """get_stats handles empty database gracefully."""
        mock_result = MagicMock()
        mock_result.one.return_value = (0, 0, 0, None)
        mock_session.execute.return_value = mock_result

        stats = await repo.get_stats()
        assert stats["total"] == 0
        assert stats["avg_duration"] is None


class TestCleanupOld:
    """Tests for cleanup_old method."""

    @pytest.mark.asyncio
    async def test_cleanup_old_returns_count(self, repo, mock_session):
        """cleanup_old returns number of deleted records."""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        deleted = await repo.cleanup_old(days=90)
        assert deleted == 5
        mock_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_cleanup_old_no_records(self, repo, mock_session):
        """cleanup_old returns 0 when nothing to delete."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        deleted = await repo.cleanup_old(days=90)
        assert deleted == 0
