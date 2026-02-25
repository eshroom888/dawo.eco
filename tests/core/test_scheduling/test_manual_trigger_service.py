"""Tests for ManualTriggerService.

Story 7-7, Task 1.2: Service tests for manual agent/team triggering.
Target: 25+ tests.
"""

import json
import pytest
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from core.scheduling.dtos import (
    TriggerResult,
    TeamTriggerResult,
    TriggerableAgentDTO,
    TeamDTO,
)
from core.scheduling.models import AgentSchedule, ScheduleChangeLog
from core.scheduling.schedule_repository import AgentScheduleRepository


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
        "agent_name": "health_claims_monitor",
        "display_name": "EU Health Claims Register Monitor",
        "schedule_cron": "0 5 * * 0",
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
        "description": "Monitor EU health claims register",
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
    """Create ManualTriggerService with mock dependencies."""
    from core.scheduling.manual_trigger_service import ManualTriggerService

    return ManualTriggerService(mock_repo, mock_config)


class TestTriggerAgent:
    """Tests for trigger_agent method."""

    @pytest.mark.asyncio
    async def test_trigger_available_agent_returns_queued(self, service, mock_repo):
        """Triggering an available agent returns status 'queued'."""
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            last_run_status="success",
        )
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.update_run_status.return_value = None

        result = await service.trigger_agent("health_claims_monitor")

        assert result.status == "queued"
        assert result.agent_name == "health_claims_monitor"
        assert result.triggered_by == "operator"
        assert result.triggered_at is not None

    @pytest.mark.asyncio
    async def test_trigger_agent_sets_running_status(self, service, mock_repo):
        """Triggering sets last_run_status to 'running' and last_run_at."""
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            last_run_status="success",
        )
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.update_run_status.return_value = None

        await service.trigger_agent("health_claims_monitor")

        mock_repo.update_run_status.assert_called_once()
        call_kwargs = mock_repo.update_run_status.call_args
        assert call_kwargs.kwargs["agent_name"] == "health_claims_monitor"
        assert call_kwargs.kwargs["status"] == "running"

    @pytest.mark.asyncio
    async def test_trigger_running_agent_returns_already_running(self, service, mock_repo):
        """Triggering a running agent returns status 'already_running'."""
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            last_run_status="running",
        )
        mock_repo.get_by_agent_name.return_value = schedule

        result = await service.trigger_agent("health_claims_monitor")

        assert result.status == "already_running"
        assert result.agent_name == "health_claims_monitor"
        # Should NOT update status when already running
        mock_repo.update_run_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_unknown_agent_returns_not_found(self, service, mock_repo):
        """Triggering an agent not in AGENT_RUNNERS returns 'not_found'."""
        result = await service.trigger_agent("nonexistent_agent")

        assert result.status == "not_found"
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_trigger_agent_with_no_schedule_record(self, service, mock_repo):
        """Triggering an agent with no schedule DB record still works (creates status)."""
        mock_repo.get_by_agent_name.return_value = None
        mock_repo.update_run_status.return_value = None

        result = await service.trigger_agent("health_claims_monitor")

        assert result.status == "queued"
        mock_repo.update_run_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_agent_with_none_status_is_not_running(self, service, mock_repo):
        """Agent with last_run_status=None (never run) is treated as available."""
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            last_run_status=None,
        )
        mock_repo.get_by_agent_name.return_value = schedule

        result = await service.trigger_agent("health_claims_monitor")

        assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_trigger_agent_with_failed_status_is_available(self, service, mock_repo):
        """Agent with last_run_status='failed' is available to trigger."""
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            last_run_status="failed",
        )
        mock_repo.get_by_agent_name.return_value = schedule

        result = await service.trigger_agent("health_claims_monitor")

        assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_trigger_agent_with_custom_triggered_by(self, service, mock_repo):
        """Custom triggered_by value is preserved in result."""
        schedule = _make_schedule(last_run_status="success")
        mock_repo.get_by_agent_name.return_value = schedule

        result = await service.trigger_agent(
            "health_claims_monitor",
            triggered_by="api_user",
        )

        assert result.triggered_by == "api_user"

    @pytest.mark.asyncio
    async def test_trigger_agent_with_config_overrides(self, service, mock_repo):
        """Config overrides are stored in result and audit logged."""
        schedule = _make_schedule(last_run_status="success")
        mock_repo.get_by_agent_name.return_value = schedule
        mock_repo.save_change_log.return_value = None

        overrides = {"keywords": ["mushroom", "cordyceps"]}
        result = await service.trigger_agent(
            "health_claims_monitor",
            config_overrides=overrides,
        )

        assert result.status == "queued"
        assert result.config_overrides == overrides
        # Should create audit log for override
        mock_repo.save_change_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_agent_override_audit_log_contents(self, service, mock_repo):
        """Audit log for config override contains correct field and values."""
        schedule = _make_schedule(last_run_status="success")
        mock_repo.get_by_agent_name.return_value = schedule

        overrides = {"scan_depth": 10}
        await service.trigger_agent(
            "health_claims_monitor",
            config_overrides=overrides,
        )

        log_call = mock_repo.save_change_log.call_args[0][0]
        assert log_call.field_changed == "manual_trigger"
        assert log_call.agent_name == "health_claims_monitor"
        assert json.loads(log_call.new_value) == overrides

    @pytest.mark.asyncio
    async def test_trigger_agent_without_overrides_no_audit(self, service, mock_repo):
        """No audit log created when triggering without overrides."""
        schedule = _make_schedule(last_run_status="success")
        mock_repo.get_by_agent_name.return_value = schedule

        await service.trigger_agent("health_claims_monitor")

        mock_repo.save_change_log.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_disabled_agent_still_works(self, service, mock_repo):
        """Manual trigger works even if agent's schedule is disabled."""
        schedule = _make_schedule(
            last_run_status="success",
            enabled=False,
        )
        mock_repo.get_by_agent_name.return_value = schedule

        result = await service.trigger_agent("health_claims_monitor")

        assert result.status == "queued"


class TestTriggerTeam:
    """Tests for trigger_team method."""

    @pytest.mark.asyncio
    async def test_trigger_team_all_agents_available(self, service, mock_repo):
        """Triggering a team with all agents available queues all."""
        # Set up schedule returns for each agent
        for agent in ["health_claims_monitor", "novel_food_monitor", "mattilsynet_monitor"]:
            schedule = _make_schedule(agent_name=agent, last_run_status="success")
            mock_repo.get_by_agent_name.side_effect = (
                lambda name, schedules={
                    "health_claims_monitor": _make_schedule(agent_name="health_claims_monitor", last_run_status="success"),
                    "novel_food_monitor": _make_schedule(agent_name="novel_food_monitor", last_run_status="success"),
                    "mattilsynet_monitor": _make_schedule(agent_name="mattilsynet_monitor", last_run_status="success"),
                }: schedules.get(name)
            )

        result = await service.trigger_team("regulatory_monitors")

        assert result.team_name == "regulatory_monitors"
        assert result.total == 3
        assert result.queued == 3
        assert result.skipped_running == 0
        assert result.failed == 0
        assert len(result.agent_results) == 3

    @pytest.mark.asyncio
    async def test_trigger_team_one_agent_running(self, service, mock_repo):
        """Team trigger with one agent running reports partial success."""
        mock_repo.get_by_agent_name.side_effect = (
            lambda name, schedules={
                "health_claims_monitor": _make_schedule(agent_name="health_claims_monitor", last_run_status="running"),
                "novel_food_monitor": _make_schedule(agent_name="novel_food_monitor", last_run_status="success"),
                "mattilsynet_monitor": _make_schedule(agent_name="mattilsynet_monitor", last_run_status="success"),
            }: schedules.get(name)
        )

        result = await service.trigger_team("regulatory_monitors")

        assert result.queued == 2
        assert result.skipped_running == 1
        assert result.total == 3

    @pytest.mark.asyncio
    async def test_trigger_unknown_team_returns_error(self, service, mock_repo):
        """Triggering unknown team returns failed result."""
        result = await service.trigger_team("nonexistent_team")

        assert result.total == 0
        assert result.failed == 0
        assert result.team_name == "nonexistent_team"

    @pytest.mark.asyncio
    async def test_trigger_team_preserves_agent_order(self, service, mock_repo):
        """Team agents are triggered in dependency order."""
        mock_repo.get_by_agent_name.side_effect = (
            lambda name: _make_schedule(agent_name=name, last_run_status="success")
        )

        result = await service.trigger_team("analytics_pipeline")

        agent_names = [r.agent_name for r in result.agent_results]
        assert agent_names == ["shopify_attribution_poll", "post_publish_scoring", "feedback_loop"]


class TestGetTriggerableAgents:
    """Tests for get_triggerable_agents method."""

    @pytest.mark.asyncio
    async def test_returns_all_registered_agents(self, service, mock_repo):
        """Returns all agents from AGENT_RUNNERS with enriched schedule data."""
        schedules = [
            _make_schedule(agent_name="health_claims_monitor", last_run_status="success"),
            _make_schedule(agent_name="novel_food_monitor", last_run_status="failed"),
        ]
        mock_repo.get_all.return_value = schedules

        agents = await service.get_triggerable_agents()

        # Should return all 8 agents from AGENT_RUNNERS
        assert len(agents) == 8
        agent_names = {a.agent_name for a in agents}
        assert "health_claims_monitor" in agent_names
        assert "feedback_loop" in agent_names

    @pytest.mark.asyncio
    async def test_enriches_with_schedule_data(self, service, mock_repo):
        """Agents with DB records get enriched status info."""
        now = datetime.now(UTC)
        schedules = [
            _make_schedule(
                agent_name="health_claims_monitor",
                last_run_status="success",
                last_run_at=now,
                last_run_duration_seconds=42.5,
                display_name="EU Health Claims Monitor",
            ),
        ]
        mock_repo.get_all.return_value = schedules

        agents = await service.get_triggerable_agents()

        hcm = next(a for a in agents if a.agent_name == "health_claims_monitor")
        assert hcm.last_run_status == "success"
        assert hcm.last_run_at == now
        assert hcm.last_run_duration_seconds == 42.5
        assert hcm.display_name == "EU Health Claims Monitor"
        assert hcm.is_running is False

    @pytest.mark.asyncio
    async def test_running_agent_has_is_running_true(self, service, mock_repo):
        """Agent with last_run_status='running' has is_running=True."""
        schedules = [
            _make_schedule(
                agent_name="health_claims_monitor",
                last_run_status="running",
            ),
        ]
        mock_repo.get_all.return_value = schedules

        agents = await service.get_triggerable_agents()

        hcm = next(a for a in agents if a.agent_name == "health_claims_monitor")
        assert hcm.is_running is True

    @pytest.mark.asyncio
    async def test_agents_without_schedule_get_defaults(self, service, mock_repo):
        """Agents not in DB still appear with default values."""
        mock_repo.get_all.return_value = []

        agents = await service.get_triggerable_agents()

        assert len(agents) == 8
        for agent in agents:
            assert agent.last_run_status is None
            assert agent.is_running is False

    @pytest.mark.asyncio
    async def test_no_n_plus_1_queries(self, service, mock_repo):
        """get_triggerable_agents calls get_all once (no N+1)."""
        mock_repo.get_all.return_value = []

        await service.get_triggerable_agents()

        mock_repo.get_all.assert_called_once()
        mock_repo.get_by_agent_name.assert_not_called()


class TestGetTeams:
    """Tests for get_teams method."""

    @pytest.mark.asyncio
    async def test_returns_all_defined_teams(self, service):
        """Returns all teams from TEAM_DEFINITIONS."""
        teams = await service.get_teams()

        assert len(teams) >= 4
        team_names = {t.team_name for t in teams}
        assert "regulatory_monitors" in team_names
        assert "analytics_pipeline" in team_names
        assert "content_research" in team_names
        assert "all_scanners" in team_names

    @pytest.mark.asyncio
    async def test_team_has_correct_structure(self, service):
        """Each team has required fields populated."""
        teams = await service.get_teams()

        for team in teams:
            assert isinstance(team, TeamDTO)
            assert team.team_name
            assert team.display_name
            assert team.description
            assert len(team.agents) > 0


class TestQueueAfterCurrent:
    """Tests for queue_after_current method."""

    @pytest.mark.asyncio
    async def test_queue_running_agent(self, service, mock_repo):
        """Queueing a running agent returns queued status."""
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            last_run_status="running",
        )
        mock_repo.get_by_agent_name.return_value = schedule

        result = await service.queue_after_current("health_claims_monitor")

        assert result.status == "queued"
        assert "after current" in result.message.lower() or "queued" in result.message.lower()

    @pytest.mark.asyncio
    async def test_queue_unknown_agent_returns_not_found(self, service, mock_repo):
        """Queueing an unknown agent returns not_found."""
        result = await service.queue_after_current("nonexistent_agent")

        assert result.status == "not_found"
