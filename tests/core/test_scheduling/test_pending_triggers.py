"""Tests for PendingTriggerStore.

Story 7-7, Task 4.3: Pending trigger lifecycle tests.
Target: 8+ tests.
"""

import pytest
from datetime import UTC, datetime

from core.scheduling.manual_trigger_service import PendingTriggerStore
from core.scheduling.dtos import PendingTrigger


@pytest.fixture
def store():
    """Fresh PendingTriggerStore for each test."""
    return PendingTriggerStore()


class TestPendingTriggerStore:
    """Tests for PendingTriggerStore add/pop/get lifecycle."""

    def test_add_creates_pending_trigger(self, store):
        """Adding a trigger creates a PendingTrigger entry."""
        trigger = store.add("health_claims_monitor", "operator")

        assert isinstance(trigger, PendingTrigger)
        assert trigger.agent_name == "health_claims_monitor"
        assert trigger.triggered_by == "operator"
        assert trigger.queued_at is not None

    def test_pop_returns_and_removes(self, store):
        """Pop returns the trigger and removes it from store."""
        store.add("health_claims_monitor", "operator")

        result = store.pop("health_claims_monitor")
        assert result is not None
        assert result.agent_name == "health_claims_monitor"

        # Second pop should return None
        assert store.pop("health_claims_monitor") is None

    def test_pop_returns_none_when_empty(self, store):
        """Pop returns None for agent with no pending trigger."""
        result = store.pop("nonexistent_agent")
        assert result is None

    def test_get_peeks_without_removing(self, store):
        """Get returns trigger without removing it."""
        store.add("health_claims_monitor", "operator")

        first = store.get("health_claims_monitor")
        second = store.get("health_claims_monitor")

        assert first is not None
        assert second is not None
        assert first.agent_name == second.agent_name

    def test_get_returns_none_when_empty(self, store):
        """Get returns None for agent with no pending trigger."""
        result = store.get("nonexistent_agent")
        assert result is None

    def test_add_overwrites_existing(self, store):
        """Adding a second trigger for same agent overwrites the first."""
        store.add("health_claims_monitor", "operator_1")
        store.add("health_claims_monitor", "operator_2")

        result = store.pop("health_claims_monitor")
        assert result.triggered_by == "operator_2"

    def test_multiple_agents_independent(self, store):
        """Different agents have independent pending triggers."""
        store.add("health_claims_monitor", "op1")
        store.add("novel_food_monitor", "op2")

        result1 = store.pop("health_claims_monitor")
        result2 = store.pop("novel_food_monitor")

        assert result1.agent_name == "health_claims_monitor"
        assert result2.agent_name == "novel_food_monitor"

    def test_add_with_config_overrides(self, store):
        """Config overrides are stored in PendingTrigger."""
        overrides = {"keywords": ["mushroom"]}
        trigger = store.add("health_claims_monitor", "operator", config_overrides=overrides)

        assert trigger.config_overrides == overrides

    def test_queued_at_is_utc(self, store):
        """PendingTrigger.queued_at uses UTC timezone."""
        trigger = store.add("health_claims_monitor", "operator")

        assert trigger.queued_at.tzinfo is not None
