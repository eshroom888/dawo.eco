"""Tests for AgentScheduleRepository.

Story 7-6, Task 3.2: Repository tests with mocked AsyncSession.
Target: 18+ tests.
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from core.scheduling.schedule_repository import AgentScheduleRepository
from core.scheduling.models import AgentSchedule, ScheduleChangeLog


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


def _make_change_log(**kwargs) -> ScheduleChangeLog:
    """Factory for test ScheduleChangeLog instances."""
    defaults = {
        "id": uuid4(),
        "agent_name": "test_agent",
        "field_changed": "schedule_cron",
        "old_value": "0 0 * * *",
        "new_value": "0 5 * * 0",
        "changed_by": "operator",
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return ScheduleChangeLog(**defaults)


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession.

    session.add() is synchronous in SQLAlchemy —
    use MagicMock to avoid RuntimeWarning from unawaited coroutine.
    """
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session):
    """Create repository with mock session."""
    return AgentScheduleRepository(mock_session)


class TestAgentScheduleRepositoryInit:
    """Tests for repository initialization."""

    def test_accepts_session(self, mock_session):
        """Constructor stores session."""
        repo = AgentScheduleRepository(mock_session)
        assert repo._session is mock_session


class TestGetAll:
    """Tests for get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_returns_list(self, repo, mock_session):
        """Returns list of schedules ordered by next_run_at."""
        schedules = [_make_schedule(agent_name="a"), _make_schedule(agent_name="b")]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = schedules
        mock_session.execute.return_value = result_mock

        result = await repo.get_all()
        assert result == schedules
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_empty(self, repo, mock_session):
        """Returns empty list when no schedules exist."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        result = await repo.get_all()
        assert result == []


class TestGetByAgentName:
    """Tests for get_by_agent_name method."""

    @pytest.mark.asyncio
    async def test_found(self, repo, mock_session):
        """Returns schedule when agent_name matches."""
        schedule = _make_schedule(agent_name="health_claims_monitor")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = schedule
        mock_session.execute.return_value = result_mock

        result = await repo.get_by_agent_name("health_claims_monitor")
        assert result == schedule

    @pytest.mark.asyncio
    async def test_not_found(self, repo, mock_session):
        """Returns None when agent_name not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        result = await repo.get_by_agent_name("nonexistent")
        assert result is None


class TestGetEnabled:
    """Tests for get_enabled method."""

    @pytest.mark.asyncio
    async def test_returns_only_enabled(self, repo, mock_session):
        """Returns only enabled schedules."""
        enabled = [_make_schedule(enabled=True)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = enabled
        mock_session.execute.return_value = result_mock

        result = await repo.get_enabled()
        assert result == enabled


class TestGetDueSchedules:
    """Tests for get_due_schedules method."""

    @pytest.mark.asyncio
    async def test_returns_due_enabled_not_running(self, repo, mock_session):
        """Returns enabled schedules where next_run_at <= now and not running."""
        now = datetime.now(UTC)
        due = [_make_schedule(
            enabled=True,
            next_run_at=now,
            last_run_status="success",
        )]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = due
        mock_session.execute.return_value = result_mock

        result = await repo.get_due_schedules(now)
        assert result == due

    @pytest.mark.asyncio
    async def test_empty_when_none_due(self, repo, mock_session):
        """Returns empty when no schedules are due."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        result = await repo.get_due_schedules(datetime.now(UTC))
        assert result == []


class TestSave:
    """Tests for save method."""

    @pytest.mark.asyncio
    async def test_save_uses_merge(self, repo, mock_session):
        """Save uses session.merge for upsert behavior."""
        schedule = _make_schedule()
        mock_session.merge.return_value = schedule

        result = await repo.save(schedule)
        mock_session.merge.assert_called_once_with(schedule)
        mock_session.flush.assert_called_once()
        assert result == schedule


class TestUpdateRunStatus:
    """Tests for update_run_status method."""

    @pytest.mark.asyncio
    async def test_updates_status_fields(self, repo, mock_session):
        """Updates run status, duration, summary, and next_run."""
        schedule = _make_schedule(agent_name="test_agent")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = schedule
        mock_session.execute.return_value = result_mock

        now = datetime.now(UTC)
        next_run = datetime(2026, 3, 1, 5, 0, 0, tzinfo=UTC)
        await repo.update_run_status(
            agent_name="test_agent",
            status="success",
            duration=45.0,
            summary={"items": 10},
            next_run=next_run,
        )

        assert schedule.last_run_status == "success"
        assert schedule.last_run_duration_seconds == 45.0
        assert schedule.last_run_summary == {"items": 10}
        assert schedule.next_run_at == next_run
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found_does_nothing(self, repo, mock_session):
        """Does nothing if agent not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        await repo.update_run_status("nonexistent", "success", None, None, None)
        mock_session.flush.assert_not_called()


class TestSaveChangeLog:
    """Tests for save_change_log method."""

    @pytest.mark.asyncio
    async def test_adds_and_flushes(self, repo, mock_session):
        """Adds change log and flushes."""
        log = _make_change_log()
        await repo.save_change_log(log)
        mock_session.add.assert_called_once_with(log)
        mock_session.flush.assert_called_once()


class TestGetChangeLogs:
    """Tests for get_change_logs method."""

    @pytest.mark.asyncio
    async def test_returns_logs_with_limit(self, repo, mock_session):
        """Returns change logs ordered by created_at desc."""
        logs = [_make_change_log(), _make_change_log()]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = logs
        mock_session.execute.return_value = result_mock

        result = await repo.get_change_logs("test_agent", limit=50)
        assert result == logs

    @pytest.mark.asyncio
    async def test_custom_limit(self, repo, mock_session):
        """Respects custom limit parameter."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        await repo.get_change_logs("test_agent", limit=10)
        mock_session.execute.assert_called_once()


class TestCount:
    """Tests for count method."""

    @pytest.mark.asyncio
    async def test_returns_count(self, repo, mock_session):
        """Returns integer count of schedules."""
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 8
        mock_session.execute.return_value = result_mock

        result = await repo.count()
        assert result == 8

    @pytest.mark.asyncio
    async def test_returns_zero_when_empty(self, repo, mock_session):
        """Returns 0 when no schedules exist."""
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 0
        mock_session.execute.return_value = result_mock

        result = await repo.count()
        assert result == 0
