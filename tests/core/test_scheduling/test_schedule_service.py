"""Tests for AgentScheduleService.

Story 7-6, Task 4.3: Service tests including dependency warnings,
seeding, and audit logging.
Target: 25+ tests.
"""

import pytest
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from core.scheduling.schedule_service import AgentScheduleService
from core.scheduling.schedule_repository import AgentScheduleRepository
from core.scheduling.models import AgentSchedule, ScheduleChangeLog
from core.scheduling.dtos import (
    AgentScheduleDTO,
    ScheduleChangeLogDTO,
    ScheduleUpdateRequest,
    DependencyWarning,
)


@dataclass(frozen=True)
class MockSchedulerConfig:
    """Mock config matching AgentSchedulerConfig interface."""

    enabled: bool = True
    check_interval_seconds: int = 60
    max_concurrent_agents: int = 5
    default_timezone: str = "UTC"
    seed_on_startup: bool = True


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
        "next_run_at": None,
        "config_source": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "description": None,
    }
    defaults.update(kwargs)
    return AgentSchedule(**defaults)


@pytest.fixture
def mock_repo():
    """Create a mock repository."""
    return AsyncMock(spec=AgentScheduleRepository)


@pytest.fixture
def mock_config():
    """Create a mock config."""
    return MockSchedulerConfig()


@pytest.fixture
def service(mock_repo, mock_config):
    """Create service with mock dependencies."""
    return AgentScheduleService(mock_repo, mock_config)


class TestGetAllSchedules:
    """Tests for get_all_schedules."""

    @pytest.mark.asyncio
    async def test_returns_dtos(self, service, mock_repo):
        """Converts model instances to DTOs with human-readable cron."""
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Monitor",
            schedule_cron="0 5 * * 0",
        )
        mock_repo.get_all.return_value = [schedule]

        result = await service.get_all_schedules()
        assert len(result) == 1
        assert isinstance(result[0], AgentScheduleDTO)
        assert result[0].agent_name == "health_claims_monitor"
        assert "Sunday" in result[0].cron_human_readable

    @pytest.mark.asyncio
    async def test_empty_list(self, service, mock_repo):
        """Returns empty list when no schedules exist."""
        mock_repo.get_all.return_value = []
        result = await service.get_all_schedules()
        assert result == []


class TestGetSchedule:
    """Tests for get_schedule."""

    @pytest.mark.asyncio
    async def test_found(self, service, mock_repo):
        """Returns DTO for found schedule."""
        schedule = _make_schedule(agent_name="test_agent")
        mock_repo.get_by_agent_name.return_value = schedule

        result = await service.get_schedule("test_agent")
        assert result is not None
        assert result.agent_name == "test_agent"

    @pytest.mark.asyncio
    async def test_not_found(self, service, mock_repo):
        """Returns None for unknown agent."""
        mock_repo.get_by_agent_name.return_value = None

        result = await service.get_schedule("nonexistent")
        assert result is None


class TestUpdateSchedule:
    """Tests for update_schedule."""

    @pytest.mark.asyncio
    async def test_updates_cron(self, service, mock_repo):
        """Updates cron expression and creates audit log."""
        schedule = _make_schedule(
            agent_name="test_agent",
            schedule_cron="0 5 * * 0",
        )
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save.return_value = schedule

        update = ScheduleUpdateRequest(schedule_cron="0 6 * * 0")
        result = await service.update_schedule("test_agent", update)

        assert result is not None
        mock_repo.save_change_log.assert_called()
        mock_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_timezone(self, service, mock_repo):
        """Updates timezone and creates audit log."""
        schedule = _make_schedule(timezone="UTC")
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save.return_value = schedule

        update = ScheduleUpdateRequest(timezone="Europe/Oslo")
        result = await service.update_schedule("test_agent", update)
        assert result is not None
        mock_repo.save_change_log.assert_called()

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, service, mock_repo):
        """Returns None for unknown agent."""
        mock_repo.get_by_agent_name.return_value = None

        update = ScheduleUpdateRequest(schedule_cron="0 6 * * 0")
        result = await service.update_schedule("nonexistent", update)
        assert result is None

    @pytest.mark.asyncio
    async def test_validates_cron_expression(self, service, mock_repo):
        """Raises ValueError for invalid cron expression."""
        schedule = _make_schedule()
        mock_repo.get_by_agent_name.return_value = schedule

        update = ScheduleUpdateRequest(schedule_cron="invalid")
        with pytest.raises(ValueError, match="Invalid cron"):
            await service.update_schedule("test_agent", update)

    @pytest.mark.asyncio
    async def test_multiple_field_updates(self, service, mock_repo):
        """Updates multiple fields, creates log for each."""
        schedule = _make_schedule(
            schedule_cron="0 5 * * 0",
            timezone="UTC",
            display_name="Old Name",
        )
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save.return_value = schedule

        update = ScheduleUpdateRequest(
            schedule_cron="0 6 * * 0",
            timezone="Europe/Oslo",
            display_name="New Name",
        )
        await service.update_schedule("test_agent", update)
        # Should create 3 change log entries
        assert mock_repo.save_change_log.call_count == 3


class TestToggleEnabled:
    """Tests for toggle_enabled."""

    @pytest.mark.asyncio
    async def test_disable(self, service, mock_repo):
        """Disables an agent schedule."""
        schedule = _make_schedule(enabled=True)
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save.return_value = schedule

        result = await service.toggle_enabled("test_agent", False)
        assert result is not None
        mock_repo.save_change_log.assert_called()
        mock_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_enable(self, service, mock_repo):
        """Enables an agent schedule."""
        schedule = _make_schedule(enabled=False)
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save.return_value = schedule

        result = await service.toggle_enabled("test_agent", True)
        assert result is not None

    @pytest.mark.asyncio
    async def test_toggle_nonexistent(self, service, mock_repo):
        """Returns None for unknown agent."""
        mock_repo.get_by_agent_name.return_value = None

        result = await service.toggle_enabled("nonexistent", False)
        assert result is None


class TestCheckDependencies:
    """Tests for check_dependencies (AC3)."""

    @pytest.mark.asyncio
    async def test_no_dependencies(self, service, mock_repo):
        """Returns empty list when no dependencies."""
        schedule = _make_schedule(dependencies=[])
        mock_repo.get_by_agent_name.return_value = schedule

        result = await service.check_dependencies("test_agent", "0 5 * * 0", "UTC")
        assert result == []

    @pytest.mark.asyncio
    async def test_dependency_runs_before_agent(self, service, mock_repo):
        """No warning when dependency runs before agent."""
        agent = _make_schedule(
            agent_name="feedback_loop",
            dependencies=["post_publish_scoring"],
        )
        dep = _make_schedule(
            agent_name="post_publish_scoring",
            schedule_cron="0 3 * * *",
            last_run_duration_seconds=120.0,
        )
        mock_repo.get_by_agent_name.side_effect = lambda name: {
            "feedback_loop": agent,
            "post_publish_scoring": dep,
        }.get(name)

        # Agent runs Sunday 04:00, dep runs daily 03:00 (finishes ~03:02)
        result = await service.check_dependencies(
            "feedback_loop", "0 4 * * 0", "UTC"
        )
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_dependency_conflict_warning(self, service, mock_repo):
        """Warning when agent runs before dependency completes."""
        agent = _make_schedule(
            agent_name="feedback_loop",
            dependencies=["post_publish_scoring"],
        )
        dep = _make_schedule(
            agent_name="post_publish_scoring",
            schedule_cron="0 3 * * *",
            last_run_duration_seconds=7200.0,  # 2 hours
        )
        mock_repo.get_by_agent_name.side_effect = lambda name: {
            "feedback_loop": agent,
            "post_publish_scoring": dep,
        }.get(name)

        # Agent runs daily 03:30, dep runs daily 03:00 (finishes ~05:00)
        result = await service.check_dependencies(
            "feedback_loop", "30 3 * * *", "UTC"
        )
        assert len(result) >= 1
        assert isinstance(result[0], DependencyWarning)

    @pytest.mark.asyncio
    async def test_unknown_dependency(self, service, mock_repo):
        """Warning when dependency agent doesn't exist."""
        agent = _make_schedule(
            agent_name="test_agent",
            dependencies=["nonexistent_agent"],
        )
        mock_repo.get_by_agent_name.side_effect = lambda name: (
            agent if name == "test_agent" else None
        )

        result = await service.check_dependencies("test_agent", "0 5 * * 0", "UTC")
        assert len(result) == 1
        assert "not found" in result[0].warning_message.lower()


class TestSeedDefaults:
    """Tests for seed_defaults (AC5)."""

    @pytest.mark.asyncio
    async def test_seeds_when_empty(self, service, mock_repo):
        """Seeds default schedules when count is 0."""
        mock_repo.count.return_value = 0
        mock_repo.save.return_value = _make_schedule()

        count = await service.seed_defaults()
        assert count > 0
        assert mock_repo.save.call_count > 0

    @pytest.mark.asyncio
    async def test_skips_when_not_empty(self, service, mock_repo):
        """Does not seed when schedules already exist."""
        mock_repo.count.return_value = 8

        count = await service.seed_defaults()
        assert count == 0
        mock_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_seeds_all_eight_agents(self, service, mock_repo):
        """Seeds all 8 default agents."""
        mock_repo.count.return_value = 0
        mock_repo.save.return_value = _make_schedule()

        count = await service.seed_defaults()
        assert count == 8

    @pytest.mark.asyncio
    async def test_seed_passes_next_run_at(self, service, mock_repo):
        """Each seeded schedule has computed next_run_at."""
        mock_repo.count.return_value = 0
        mock_repo.save.return_value = _make_schedule()

        await service.seed_defaults()
        for call in mock_repo.save.call_args_list:
            schedule = call.args[0]
            assert schedule.next_run_at is not None


class TestGetAuditLog:
    """Tests for get_audit_log."""

    @pytest.mark.asyncio
    async def test_returns_dtos(self, service, mock_repo):
        """Returns list of ScheduleChangeLogDTO."""
        log = ScheduleChangeLog(
            id=uuid4(),
            agent_name="test_agent",
            field_changed="schedule_cron",
            old_value="0 0 * * *",
            new_value="0 5 * * 0",
            changed_by="operator",
            created_at=datetime.now(UTC),
        )
        mock_repo.get_change_logs.return_value = [log]

        result = await service.get_audit_log("test_agent")
        assert len(result) == 1
        assert isinstance(result[0], ScheduleChangeLogDTO)
        assert result[0].field_changed == "schedule_cron"

    @pytest.mark.asyncio
    async def test_empty_audit_log(self, service, mock_repo):
        """Returns empty list when no changes logged."""
        mock_repo.get_change_logs.return_value = []

        result = await service.get_audit_log("test_agent")
        assert result == []

    @pytest.mark.asyncio
    async def test_respects_limit(self, service, mock_repo):
        """Passes limit parameter to repository."""
        mock_repo.get_change_logs.return_value = []

        await service.get_audit_log("test_agent", limit=10)
        mock_repo.get_change_logs.assert_called_once_with("test_agent", 10)


class TestToDtoEdgeCases:
    """Tests for _to_dto edge cases."""

    def test_none_timezone_defaults_to_utc(self, service):
        """None timezone defaults to 'UTC' in DTO."""
        schedule = _make_schedule(timezone=None)
        dto = service._to_dto(schedule)
        assert dto.timezone == "UTC"

    def test_none_enabled_defaults_to_true(self, service):
        """None enabled defaults to True in DTO."""
        schedule = _make_schedule(enabled=None)
        dto = service._to_dto(schedule)
        assert dto.enabled is True

    def test_none_dependencies_defaults_to_empty(self, service):
        """None dependencies defaults to empty list in DTO."""
        schedule = _make_schedule(dependencies=None)
        dto = service._to_dto(schedule)
        assert dto.dependencies == []


class TestUpdateScheduleAdvanced:
    """Additional update_schedule tests."""

    @pytest.mark.asyncio
    async def test_updates_description(self, service, mock_repo):
        """Updates description field with audit log."""
        schedule = _make_schedule(description="Old desc")
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save.return_value = schedule

        update = ScheduleUpdateRequest(description="New desc")
        result = await service.update_schedule("test_agent", update)
        assert result is not None
        mock_repo.save_change_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_dependencies(self, service, mock_repo):
        """Updates dependencies field with audit log."""
        schedule = _make_schedule(dependencies=[])
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save.return_value = schedule

        update = ScheduleUpdateRequest(dependencies=["shopify_attribution_poll"])
        result = await service.update_schedule("test_agent", update)
        assert result is not None
        mock_repo.save_change_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_change_skips_audit_log(self, service, mock_repo):
        """No audit log when value hasn't changed."""
        schedule = _make_schedule(
            schedule_cron="0 5 * * 0",
            display_name="Test Agent",
        )
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save.return_value = schedule

        # Same values as existing
        update = ScheduleUpdateRequest(
            schedule_cron="0 5 * * 0",
            display_name="Test Agent",
        )
        await service.update_schedule("test_agent", update)
        mock_repo.save_change_log.assert_not_called()


class TestCheckDependenciesAdvanced:
    """Additional dependency check tests."""

    @pytest.mark.asyncio
    async def test_critical_severity_for_long_running_dep(self, service, mock_repo):
        """Sets severity='critical' when dep duration > 1 hour."""
        agent = _make_schedule(
            agent_name="feedback_loop",
            dependencies=["post_publish_scoring"],
        )
        dep = _make_schedule(
            agent_name="post_publish_scoring",
            schedule_cron="0 3 * * *",
            last_run_duration_seconds=7200.0,  # 2 hours > 3600 threshold
        )
        mock_repo.get_by_agent_name.side_effect = lambda name: {
            "feedback_loop": agent,
            "post_publish_scoring": dep,
        }.get(name)

        result = await service.check_dependencies(
            "feedback_loop", "30 3 * * *", "UTC"
        )
        assert len(result) >= 1
        assert result[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_agent_not_found_returns_empty(self, service, mock_repo):
        """Returns empty list when agent itself not found."""
        mock_repo.get_by_agent_name.return_value = None

        result = await service.check_dependencies("nonexistent", "0 5 * * 0", "UTC")
        assert result == []
