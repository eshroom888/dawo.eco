"""Tests for trigger DTOs.

Story 7-7, Task 2.2: Frozen dataclass DTOs for manual triggering.
Target: 8+ tests covering frozen immutability, defaults.
"""

import pytest
from datetime import UTC, datetime

from core.scheduling.dtos import (
    PendingTrigger,
    TeamDTO,
    TeamTriggerResult,
    TriggerableAgentDTO,
    TriggerResult,
)


class TestTriggerResult:
    """Tests for TriggerResult frozen dataclass."""

    def test_create_with_required_fields(self):
        """TriggerResult can be created with required fields."""
        now = datetime.now(UTC)
        result = TriggerResult(
            agent_name="health_claims_monitor",
            status="queued",
            job_id=None,
            triggered_at=now,
            triggered_by="operator",
        )
        assert result.agent_name == "health_claims_monitor"
        assert result.status == "queued"
        assert result.job_id is None
        assert result.triggered_at == now
        assert result.triggered_by == "operator"
        assert result.config_overrides is None
        assert result.message == ""

    def test_frozen_immutability(self):
        """TriggerResult is frozen — cannot modify fields."""
        result = TriggerResult(
            agent_name="test",
            status="queued",
            job_id=None,
            triggered_at=datetime.now(UTC),
            triggered_by="operator",
        )
        with pytest.raises(AttributeError):
            result.status = "changed"

    def test_with_config_overrides(self):
        """TriggerResult stores config_overrides dict."""
        overrides = {"keywords": ["mushroom"]}
        result = TriggerResult(
            agent_name="test",
            status="queued",
            job_id="abc-123",
            triggered_at=datetime.now(UTC),
            triggered_by="api",
            config_overrides=overrides,
            message="Triggered with overrides",
        )
        assert result.config_overrides == overrides
        assert result.job_id == "abc-123"
        assert result.message == "Triggered with overrides"


class TestTeamTriggerResult:
    """Tests for TeamTriggerResult frozen dataclass."""

    def test_create_with_all_fields(self):
        """TeamTriggerResult holds aggregated team trigger data."""
        agent_result = TriggerResult(
            agent_name="test",
            status="queued",
            job_id=None,
            triggered_at=datetime.now(UTC),
            triggered_by="operator",
        )
        result = TeamTriggerResult(
            team_name="regulatory_monitors",
            agent_results=[agent_result],
            total=3,
            queued=1,
            skipped_running=1,
            failed=1,
        )
        assert result.team_name == "regulatory_monitors"
        assert len(result.agent_results) == 1
        assert result.total == 3

    def test_frozen_immutability(self):
        """TeamTriggerResult is frozen."""
        result = TeamTriggerResult(
            team_name="test",
            agent_results=[],
            total=0,
            queued=0,
            skipped_running=0,
            failed=0,
        )
        with pytest.raises(AttributeError):
            result.team_name = "changed"


class TestTriggerableAgentDTO:
    """Tests for TriggerableAgentDTO frozen dataclass."""

    def test_defaults_for_optional_fields(self):
        """Optional fields have correct defaults."""
        agent = TriggerableAgentDTO(
            agent_name="health_claims_monitor",
            display_name="EU Health Claims Monitor",
        )
        assert agent.description is None
        assert agent.last_run_status is None
        assert agent.last_run_at is None
        assert agent.last_run_duration_seconds is None
        assert agent.is_running is False
        assert agent.schedule_cron is None
        assert agent.next_scheduled_run is None

    def test_frozen_immutability(self):
        """TriggerableAgentDTO is frozen."""
        agent = TriggerableAgentDTO(
            agent_name="test",
            display_name="Test",
        )
        with pytest.raises(AttributeError):
            agent.is_running = True


class TestTeamDTO:
    """Tests for TeamDTO frozen dataclass."""

    def test_create_team(self):
        """TeamDTO stores team definition."""
        team = TeamDTO(
            team_name="regulatory_monitors",
            display_name="Regulatory Monitors",
            agents=["health_claims_monitor", "novel_food_monitor"],
            description="All regulatory agents",
        )
        assert team.team_name == "regulatory_monitors"
        assert len(team.agents) == 2
        assert team.description == "All regulatory agents"

    def test_frozen_immutability(self):
        """TeamDTO is frozen."""
        team = TeamDTO(
            team_name="test",
            display_name="Test",
            agents=["a"],
            description="desc",
        )
        with pytest.raises(AttributeError):
            team.team_name = "changed"


class TestPendingTrigger:
    """Tests for PendingTrigger frozen dataclass."""

    def test_create_with_defaults(self):
        """PendingTrigger defaults config_overrides to None."""
        trigger = PendingTrigger(
            agent_name="test",
            triggered_by="operator",
            queued_at=datetime.now(UTC),
        )
        assert trigger.config_overrides is None

    def test_frozen_immutability(self):
        """PendingTrigger is frozen."""
        trigger = PendingTrigger(
            agent_name="test",
            triggered_by="operator",
            queued_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            trigger.agent_name = "changed"
