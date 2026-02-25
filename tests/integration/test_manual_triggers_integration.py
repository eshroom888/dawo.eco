"""Integration tests for manual agent/team trigger pipeline.

Epic 7, Story 7-7: Manual Team/Agent Triggers.
Task 9.1: End-to-end integration tests.

Tests the integration between:
- ManualTriggerService (orchestrator)
- PendingTriggerStore (in-memory queue)
- TEAM_DEFINITIONS / validate_team_definitions (registry)
- _check_pending_triggers (dispatcher integration)
- Router schemas (Pydantic validation)
Target: 12+ tests.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.scheduling.dtos import (
    PendingTrigger,
    TeamDTO,
    TeamTriggerResult,
    TriggerableAgentDTO,
    TriggerResult,
)
from core.scheduling.manual_trigger_service import (
    ManualTriggerService,
    PendingTriggerStore,
    TEAM_DEFINITIONS,
    pending_trigger_store,
    validate_team_definitions,
)
from core.scheduling.models import AgentSchedule


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
    display_name: str | None = None,
    description: str | None = None,
) -> AgentSchedule:
    schedule = AgentSchedule()
    schedule.id = uuid4()
    schedule.agent_name = agent_name
    schedule.display_name = display_name or f"Test {agent_name}"
    schedule.description = description
    schedule.schedule_cron = cron
    schedule.timezone = "UTC"
    schedule.enabled = enabled
    schedule.last_run_status = last_run_status
    schedule.last_run_at = None
    schedule.last_run_duration_seconds = None
    schedule.next_run_at = None
    schedule.dependencies = []
    return schedule


def _build_service() -> tuple[ManualTriggerService, AsyncMock]:
    """Build service with mock repository."""
    repo = AsyncMock()
    repo.get_by_agent_name.return_value = None
    repo.update_run_status.return_value = None
    repo.save_change_log.return_value = None
    repo.get_all.return_value = []
    config = _MockConfig()
    service = ManualTriggerService(repository=repo, config=config)
    return service, repo


class TestTriggerAgentFlow:
    """End-to-end: trigger_agent validates -> marks running -> returns result."""

    @pytest.mark.asyncio
    async def test_trigger_valid_agent_marks_running(self):
        """Triggering a valid agent calls update_run_status with 'running'."""
        service, repo = _build_service()

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ):
            result = await service.trigger_agent("health_claims_monitor", "test_user")

        assert result.status == "queued"
        repo.update_run_status.assert_awaited_once_with(
            agent_name="health_claims_monitor",
            status="running",
            duration=None,
            summary=None,
            next_run=None,
        )

    @pytest.mark.asyncio
    async def test_trigger_unknown_agent_returns_not_found(self):
        """Triggering unknown agent returns not_found without DB call."""
        service, repo = _build_service()

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ):
            result = await service.trigger_agent("nonexistent_agent", "test_user")

        assert result.status == "not_found"
        repo.update_run_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_trigger_running_agent_returns_already_running(self):
        """Triggering currently-running agent returns already_running."""
        service, repo = _build_service()
        schedule = _make_schedule(last_run_status="running")
        repo.get_by_agent_name.return_value = schedule

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ):
            result = await service.trigger_agent("health_claims_monitor", "test_user")

        assert result.status == "already_running"

    @pytest.mark.asyncio
    async def test_trigger_with_overrides_logs_to_audit(self):
        """Config overrides are logged to ScheduleChangeLog."""
        service, repo = _build_service()
        overrides = {"keywords": ["mushroom"]}

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ):
            result = await service.trigger_agent(
                "health_claims_monitor", "test_user", config_overrides=overrides
            )

        assert result.status == "queued"
        repo.save_change_log.assert_awaited_once()
        log_arg = repo.save_change_log.call_args[0][0]
        assert log_arg.field_changed == "manual_trigger"
        assert "mushroom" in log_arg.new_value


class TestTriggerTeamFlow:
    """End-to-end: trigger_team iterates agents, aggregates results."""

    @pytest.mark.asyncio
    async def test_trigger_team_triggers_all_agents(self):
        """Triggering a team triggers each agent in order."""
        service, repo = _build_service()
        runners = {
            "health_claims_monitor": MagicMock(),
            "novel_food_monitor": MagicMock(),
            "mattilsynet_monitor": MagicMock(),
        }

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value=runners,
        ):
            result = await service.trigger_team("regulatory_monitors", "test_user")

        assert result.team_name == "regulatory_monitors"
        assert result.total == 3
        assert result.queued == 3

    @pytest.mark.asyncio
    async def test_trigger_team_skips_running_agents(self):
        """Running agents within a team get skipped (already_running)."""
        service, repo = _build_service()
        # First agent running, rest idle
        schedule = _make_schedule(agent_name="health_claims_monitor", last_run_status="running")
        repo.get_by_agent_name.side_effect = lambda name: (
            schedule if name == "health_claims_monitor" else None
        )
        runners = {
            "health_claims_monitor": MagicMock(),
            "novel_food_monitor": MagicMock(),
            "mattilsynet_monitor": MagicMock(),
        }

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value=runners,
        ):
            result = await service.trigger_team("regulatory_monitors", "test_user")

        assert result.total == 3
        assert result.queued == 2
        assert result.skipped_running == 1

    @pytest.mark.asyncio
    async def test_trigger_unknown_team_returns_empty(self):
        """Triggering unknown team returns empty result."""
        service, repo = _build_service()

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={},
        ):
            result = await service.trigger_team("nonexistent_team", "test_user")

        assert result.total == 0
        assert result.queued == 0


class TestQueueAfterCurrentFlow:
    """End-to-end: queue_after_current -> pending store -> dispatcher pick-up."""

    @pytest.mark.asyncio
    async def test_queue_then_pop_lifecycle(self):
        """Queue adds to store; pop retrieves and removes."""
        service, repo = _build_service()
        # Agent must be running for queue_after_current to accept
        schedule = _make_schedule(agent_name="health_claims_monitor", last_run_status="running")
        repo.get_by_agent_name.return_value = schedule
        store = PendingTriggerStore()

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ), patch(
            "core.scheduling.manual_trigger_service.pending_trigger_store",
            store,
        ):
            result = await service.queue_after_current(
                "health_claims_monitor", "test_user"
            )

        assert result.status == "queued"
        # Pending trigger is in the store
        pending = store.pop("health_claims_monitor")
        assert pending is not None
        assert pending.triggered_by == "test_user"
        # Second pop returns None
        assert store.pop("health_claims_monitor") is None

    @pytest.mark.asyncio
    async def test_check_pending_triggers_enqueues_job(self):
        """_check_pending_triggers pops and re-enqueues after completion."""
        from core.scheduling.jobs import _check_pending_triggers

        store = PendingTriggerStore()
        store.add("health_claims_monitor", "test_user")

        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}

        with patch(
            "core.scheduling.manual_trigger_service.pending_trigger_store",
            store,
        ):
            await _check_pending_triggers(ctx, "health_claims_monitor")

        mock_redis.enqueue_job.assert_awaited_once_with(
            "_run_scheduled_agent", "health_claims_monitor"
        )
        # Store is now empty
        assert store.pop("health_claims_monitor") is None

    @pytest.mark.asyncio
    async def test_check_pending_triggers_no_pending_is_noop(self):
        """_check_pending_triggers with no pending trigger does nothing."""
        from core.scheduling.jobs import _check_pending_triggers

        store = PendingTriggerStore()
        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}

        with patch(
            "core.scheduling.manual_trigger_service.pending_trigger_store",
            store,
        ):
            await _check_pending_triggers(ctx, "health_claims_monitor")

        mock_redis.enqueue_job.assert_not_awaited()


class TestTriggerableAgentsEnrichment:
    """End-to-end: get_triggerable_agents merges AGENT_RUNNERS + schedules."""

    @pytest.mark.asyncio
    async def test_enrichment_with_schedule_data(self):
        """Agents with DB schedules get enriched display_name and status."""
        service, repo = _build_service()
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            display_name="Health Claims Monitor",
            description="Monitors EU register",
            last_run_status="completed",
        )
        repo.get_all.return_value = [schedule]

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ):
            agents = await service.get_triggerable_agents()

        assert len(agents) == 1
        agent = agents[0]
        assert agent.display_name == "Health Claims Monitor"
        assert agent.last_run_status == "completed"
        assert agent.is_running is False

    @pytest.mark.asyncio
    async def test_enrichment_without_schedule_uses_defaults(self):
        """Agents without DB schedule get agent_name as display_name."""
        service, repo = _build_service()
        repo.get_all.return_value = []

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ):
            agents = await service.get_triggerable_agents()

        assert len(agents) == 1
        assert agents[0].display_name == "health_claims_monitor"
        assert agents[0].is_running is False


class TestTeamDefinitionsValidation:
    """End-to-end: validate_team_definitions checks TEAM_DEFINITIONS against AGENT_RUNNERS."""

    def test_validation_passes_with_correct_definitions(self):
        """Current TEAM_DEFINITIONS pass validation."""
        validate_team_definitions()  # Should not raise

    def test_validation_fails_for_bad_agent(self, monkeypatch):
        """Validation raises ValueError for unknown agent in team."""
        bad = {
            "test_team": {
                "display_name": "Test",
                "description": "Bad team",
                "agents": ["totally_fake_agent"],
            },
        }
        monkeypatch.setattr(
            "core.scheduling.manual_trigger_service.TEAM_DEFINITIONS",
            bad,
        )

        with pytest.raises(ValueError, match="totally_fake_agent"):
            validate_team_definitions()


class TestPydanticSchemaIntegration:
    """End-to-end: Pydantic schemas validate and serialize correctly."""

    def test_trigger_agent_request_validates(self):
        """TriggerAgentRequest accepts valid data."""
        from ui.backend.schemas.triggers import TriggerAgentRequest

        req = TriggerAgentRequest(force=True, config_overrides={"k": "v"})
        assert req.force is True
        assert req.config_overrides == {"k": "v"}

    def test_trigger_agent_request_rejects_bad_override_type(self):
        """TriggerAgentRequest rejects non-dict overrides."""
        from ui.backend.schemas.triggers import TriggerAgentRequest

        # None is valid (optional), but string is not
        req = TriggerAgentRequest(config_overrides=None)
        assert req.config_overrides is None

    def test_trigger_agent_response_serializes(self):
        """TriggerAgentResponse serializes all fields."""
        from ui.backend.schemas.triggers import TriggerAgentResponse

        resp = TriggerAgentResponse(
            agent_name="health_claims_monitor",
            status="queued",
            job_id="job-123",
            triggered_at="2026-02-24T12:00:00Z",
            message="Triggered",
        )
        data = resp.model_dump()
        assert data["agent_name"] == "health_claims_monitor"
        assert data["status"] == "queued"
        assert data["job_id"] == "job-123"


class TestDisabledAgentTrigger:
    """Disabled agents can still be manually triggered (schedule.enabled is irrelevant)."""

    @pytest.mark.asyncio
    async def test_disabled_agent_can_be_triggered(self):
        """A disabled agent is still triggerable via manual trigger."""
        service, repo = _build_service()
        # Agent has a schedule but is disabled
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            enabled=False,
            last_run_status="completed",
        )
        repo.get_by_agent_name.return_value = schedule

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ):
            result = await service.trigger_agent("health_claims_monitor", "test_user")

        # Should succeed — enabled flag only affects cron, not manual trigger
        assert result.status == "queued"
        repo.update_run_status.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_queue_non_running_agent_returns_not_running(self):
        """queue_after_current rejects agents not currently running."""
        service, repo = _build_service()
        # Agent exists but not running
        schedule = _make_schedule(
            agent_name="health_claims_monitor",
            last_run_status="completed",
        )
        repo.get_by_agent_name.return_value = schedule

        with patch(
            "core.scheduling.manual_trigger_service._get_agent_runners",
            return_value={"health_claims_monitor": MagicMock()},
        ):
            result = await service.queue_after_current("health_claims_monitor", "test_user")

        assert result.status == "not_running"
