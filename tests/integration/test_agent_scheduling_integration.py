"""Integration tests for agent scheduling pipeline.

Epic 7, Story 7-6: Agent Schedule Configuration.
Task 10: End-to-end integration tests.

Tests the integration between:
- AgentScheduleService (orchestrator)
- AgentScheduleRepository (data persistence)
- Cron utilities (cron parsing, next_run calculation)
- Schedule dispatcher (_check_due_schedules, _run_scheduled_agent)
"""

import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.scheduling.cron_utils import calculate_next_run, validate_cron_expression
from core.scheduling.dtos import AgentScheduleDTO, ScheduleUpdateRequest
from core.scheduling.models import AgentSchedule
from core.scheduling.schedule_service import AgentScheduleService, DEFAULT_SCHEDULES


@dataclass(frozen=True)
class _MockConfig:
    enabled: bool = True
    check_interval_seconds: int = 60
    max_concurrent_agents: int = 5
    default_timezone: str = "UTC"
    seed_on_startup: bool = True


def _make_schedule(
    agent_name: str = "health_claims_monitor",
    cron: str = "0 5 * * 0",
    enabled: bool = True,
    last_run_status: str | None = None,
    dependencies: list[str] | None = None,
    next_run_at: datetime | None = None,
) -> AgentSchedule:
    schedule = AgentSchedule()
    schedule.id = uuid4()
    schedule.agent_name = agent_name
    schedule.display_name = f"Test {agent_name}"
    schedule.schedule_cron = cron
    schedule.timezone = "UTC"
    schedule.enabled = enabled
    schedule.last_run_status = last_run_status
    schedule.dependencies = dependencies or []
    schedule.next_run_at = next_run_at or calculate_next_run(cron, "UTC")
    return schedule


class TestSeedAndVerify:
    """End-to-end: seed defaults -> verify all 8 agents seeded."""

    @pytest.mark.asyncio
    async def test_seed_creates_all_default_schedules(self):
        """Seed with empty repo creates exactly 8 schedules."""
        repo = AsyncMock()
        repo.count.return_value = 0
        repo.save.side_effect = lambda s: s

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        count = await service.seed_defaults()

        assert count == 8
        assert repo.save.await_count == 8

    @pytest.mark.asyncio
    async def test_seed_skips_when_populated(self):
        """Seed with existing schedules returns 0."""
        repo = AsyncMock()
        repo.count.return_value = 5

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        count = await service.seed_defaults()

        assert count == 0
        repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_seeded_schedules_have_next_run(self):
        """All seeded schedules get a computed next_run_at."""
        saved = []
        repo = AsyncMock()
        repo.count.return_value = 0
        repo.save.side_effect = lambda s: (saved.append(s), s)[-1]

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        await service.seed_defaults()

        for schedule in saved:
            assert schedule.next_run_at is not None
            assert schedule.next_run_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_seed_then_list_returns_all(self):
        """After seeding, get_all_schedules returns DTOs for all agents."""
        saved = []
        repo = AsyncMock()
        repo.count.return_value = 0
        repo.save.side_effect = lambda s: (saved.append(s), s)[-1]
        repo.get_all.return_value = saved

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        await service.seed_defaults()
        dtos = await service.get_all_schedules()

        assert len(dtos) == 8
        names = {d.agent_name for d in dtos}
        assert "health_claims_monitor" in names
        assert "feedback_loop" in names


class TestScheduleUpdateWithAudit:
    """Schedule update -> audit log -> next_run recalculation."""

    @pytest.mark.asyncio
    async def test_update_cron_creates_audit_and_recalculates(self):
        """Updating cron creates audit log and recalculates next_run_at."""
        schedule = _make_schedule()
        old_cron = schedule.schedule_cron

        repo = AsyncMock()
        repo.get_by_agent_name.return_value = schedule
        repo.save.side_effect = lambda s: s

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        updates = ScheduleUpdateRequest(schedule_cron="30 6 * * *")
        dto = await service.update_schedule("health_claims_monitor", updates)

        assert dto is not None
        assert dto.schedule_cron == "30 6 * * *"
        # Audit log created for cron change
        repo.save_change_log.assert_awaited_once()
        log_call = repo.save_change_log.call_args[0][0]
        assert log_call.field_changed == "schedule_cron"
        assert log_call.old_value == old_cron
        assert log_call.new_value == "30 6 * * *"

    @pytest.mark.asyncio
    async def test_update_multiple_fields_creates_multiple_logs(self):
        """Changing both cron and timezone creates two audit entries."""
        schedule = _make_schedule()

        repo = AsyncMock()
        repo.get_by_agent_name.return_value = schedule
        repo.save.side_effect = lambda s: s

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        updates = ScheduleUpdateRequest(
            schedule_cron="0 8 * * 1",
            timezone="Europe/Oslo",
        )
        await service.update_schedule("health_claims_monitor", updates)

        # Two audit log entries (cron + timezone)
        assert repo.save_change_log.await_count == 2

    @pytest.mark.asyncio
    async def test_update_invalid_cron_raises_valueerror(self):
        """Invalid cron expression raises ValueError."""
        schedule = _make_schedule()

        repo = AsyncMock()
        repo.get_by_agent_name.return_value = schedule

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        with pytest.raises(ValueError, match="Invalid cron"):
            await service.update_schedule(
                "health_claims_monitor",
                ScheduleUpdateRequest(schedule_cron="bad_cron"),
            )


class TestDependencyWarnings:
    """Dependency conflict detection integration."""

    @pytest.mark.asyncio
    async def test_warns_when_running_before_dependency(self):
        """Warns if agent runs before dependency completes."""
        now = datetime.now(UTC)
        agent = _make_schedule(
            agent_name="post_publish_scoring",
            cron="0 3 * * *",
            dependencies=["shopify_attribution_poll"],
        )
        dep = _make_schedule(
            agent_name="shopify_attribution_poll",
            cron="0 3 * * *",
            last_run_status="success",
        )
        dep.last_run_duration_seconds = 600.0  # 10 min

        repo = AsyncMock()
        repo.get_by_agent_name.side_effect = (
            lambda name: agent if name == "post_publish_scoring" else dep
        )

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        warnings = await service.check_dependencies(
            "post_publish_scoring", "0 3 * * *", "UTC"
        )

        assert len(warnings) == 1
        assert warnings[0].dependency_name == "shopify_attribution_poll"
        assert warnings[0].severity in ("warning", "critical")

    @pytest.mark.asyncio
    async def test_no_warning_when_no_dependencies(self):
        """No warnings for agents without dependencies."""
        agent = _make_schedule(agent_name="health_claims_monitor", dependencies=[])

        repo = AsyncMock()
        repo.get_by_agent_name.return_value = agent

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        warnings = await service.check_dependencies(
            "health_claims_monitor", "0 5 * * 0", "UTC"
        )

        assert warnings == []


class TestDispatcherIntegration:
    """Dispatcher finds due schedules and dispatches agents."""

    @pytest.mark.asyncio
    async def test_dispatcher_finds_and_dispatches(self):
        """Dispatcher enqueues agents for due schedules."""
        past = datetime.now(UTC) - timedelta(minutes=5)
        schedule = _make_schedule(next_run_at=past, enabled=True)

        mock_db = MagicMock()
        mock_db.get_async_session.return_value = AsyncMock()
        sys.modules["core.database"] = mock_db

        try:
            from core.scheduling.jobs import _check_due_schedules

            mock_repo = AsyncMock()
            mock_repo.get_due_schedules.return_value = [schedule]

            @asynccontextmanager
            async def _fake_session():
                yield mock_repo

            mock_redis = AsyncMock()
            mock_ctx = {"redis": mock_redis}

            with patch(
                "core.scheduling.jobs._schedule_session",
                _fake_session,
            ):
                result = await _check_due_schedules(mock_ctx)

            assert result["checked"] == 1
            assert result["dispatched"] == 1
        finally:
            sys.modules.pop("core.database", None)

    @pytest.mark.asyncio
    async def test_dispatcher_skips_disabled(self):
        """Dispatcher doesn't dispatch disabled schedules (filtered by repo)."""
        mock_db = MagicMock()
        mock_db.get_async_session.return_value = AsyncMock()
        sys.modules["core.database"] = mock_db

        try:
            from core.scheduling.jobs import _check_due_schedules

            mock_repo = AsyncMock()
            mock_repo.get_due_schedules.return_value = []  # DB filters disabled

            @asynccontextmanager
            async def _fake_session():
                yield mock_repo

            mock_ctx = {"redis": AsyncMock()}

            with patch(
                "core.scheduling.jobs._schedule_session",
                _fake_session,
            ):
                result = await _check_due_schedules(mock_ctx)

            assert result["checked"] == 0
            assert result["dispatched"] == 0
        finally:
            sys.modules.pop("core.database", None)


class TestToggleEnabledFlow:
    """Enable/disable integration with audit trail."""

    @pytest.mark.asyncio
    async def test_disable_creates_audit_entry(self):
        """Disabling a schedule logs the change."""
        schedule = _make_schedule(enabled=True)

        repo = AsyncMock()
        repo.get_by_agent_name.return_value = schedule
        repo.save.side_effect = lambda s: s

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        dto = await service.toggle_enabled("health_claims_monitor", False)

        assert dto is not None
        assert dto.enabled is False
        repo.save_change_log.assert_awaited_once()
        log = repo.save_change_log.call_args[0][0]
        assert log.field_changed == "enabled"
        assert log.old_value == "True"
        assert log.new_value == "False"

    @pytest.mark.asyncio
    async def test_toggle_nonexistent_returns_none(self):
        """Toggling non-existent agent returns None."""
        repo = AsyncMock()
        repo.get_by_agent_name.return_value = None

        service = AgentScheduleService(repository=repo, config=_MockConfig())
        result = await service.toggle_enabled("nonexistent", True)

        assert result is None


class TestCronToDispatchIntegration:
    """Cron expression flows through to ARQ kwargs."""

    def test_default_schedules_have_valid_cron(self):
        """All 8 default schedules have valid cron expressions."""
        for defaults in DEFAULT_SCHEDULES:
            assert validate_cron_expression(defaults["schedule_cron"]), (
                f"Invalid cron for {defaults['agent_name']}: {defaults['schedule_cron']}"
            )

    def test_default_schedules_produce_future_next_run(self):
        """All default schedules compute a future next_run_at."""
        now = datetime.now(UTC)
        for defaults in DEFAULT_SCHEDULES:
            next_run = calculate_next_run(
                defaults["schedule_cron"],
                defaults["timezone"],
            )
            assert next_run > now, (
                f"{defaults['agent_name']}: next_run {next_run} should be in the future"
            )
