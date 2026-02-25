"""Tests for regulatory events.

Story 6-1, Task 12.25: RegulatoryEvent serialization tests.
"""

import pytest
import asyncio
from datetime import datetime, UTC

from core.regulatory.events import (
    RegulatoryEvent,
    RegulatoryEventType,
    RegulatoryEventEmitter,
    get_regulatory_events,
)


class TestRegulatoryEvent:
    """Test 12.25: RegulatoryEvent serialization."""

    def test_to_dict(self):
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            claim_id="ID-001",
            substance="Beta-glucans",
            old_status="on_hold",
            new_status="authorised",
            severity="critical",
            data={"field_changed": "status"},
        )
        d = event.to_dict()
        assert d["event_type"] == "claim_status_changed"
        assert d["claim_id"] == "ID-001"
        assert d["substance"] == "Beta-glucans"
        assert d["old_status"] == "on_hold"
        assert d["new_status"] == "authorised"
        assert d["severity"] == "critical"
        assert "timestamp" in d
        assert "event_id" in d

    def test_event_id_unique(self):
        e1 = RegulatoryEvent(event_type=RegulatoryEventType.REGISTER_UPDATED)
        e2 = RegulatoryEvent(event_type=RegulatoryEventType.REGISTER_UPDATED)
        assert e1.event_id != e2.event_id

    def test_timestamp_utc(self):
        event = RegulatoryEvent(event_type=RegulatoryEventType.REGISTER_UPDATED)
        assert event.timestamp.tzinfo is not None

    def test_default_values(self):
        event = RegulatoryEvent(event_type=RegulatoryEventType.NEW_CLAIM_APPROVED)
        assert event.claim_id == ""
        assert event.substance == ""
        assert event.old_status == ""
        assert event.severity == "low"
        assert event.data == {}


class TestRegulatoryEventType:
    """Test enum values."""

    def test_claim_status_changed(self):
        assert RegulatoryEventType.CLAIM_STATUS_CHANGED.value == "claim_status_changed"

    def test_new_claim_approved(self):
        assert RegulatoryEventType.NEW_CLAIM_APPROVED.value == "new_claim_approved"

    def test_claim_removed(self):
        assert RegulatoryEventType.CLAIM_REMOVED.value == "claim_removed"

    def test_register_updated(self):
        assert RegulatoryEventType.REGISTER_UPDATED.value == "register_updated"

    def test_is_str_enum(self):
        assert isinstance(RegulatoryEventType.CLAIM_STATUS_CHANGED, str)


class TestRegulatoryEventEmitter:
    """Test event emitter pub/sub."""

    @pytest.mark.asyncio
    async def test_emit_to_subscriber(self):
        emitter = RegulatoryEventEmitter()
        received = []

        async def consumer():
            async for event in emitter.subscribe():
                received.append(event)
                break  # Only receive one

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.01)

        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            claim_id="ID-001",
        )
        await emitter.emit(event)
        await asyncio.sleep(0.01)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(received) == 1
        assert received[0].claim_id == "ID-001"

    @pytest.mark.asyncio
    async def test_subscriber_count(self):
        emitter = RegulatoryEventEmitter()
        assert emitter.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        emitter = get_regulatory_events()
        assert isinstance(emitter, RegulatoryEventEmitter)
