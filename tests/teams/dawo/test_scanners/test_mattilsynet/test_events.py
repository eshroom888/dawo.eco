"""Tests for Mattilsynet-specific regulatory event types.

Epic 6, Story 6-3: Task 13.36-13.38.
"""

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType


class TestMattilsynetEventTypes:
    """Verify the 3 new Mattilsynet event types exist."""

    def test_regulatory_update_event_type(self) -> None:
        assert RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE.value == "mattilsynet_regulatory_update"

    def test_enforcement_action_event_type(self) -> None:
        assert RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION.value == "mattilsynet_enforcement_action"

    def test_page_changed_event_type(self) -> None:
        assert RegulatoryEventType.MATTILSYNET_PAGE_CHANGED.value == "mattilsynet_page_changed"


class TestMattilsynetEventCreation:
    """Verify events can be created with Mattilsynet types."""

    def test_create_regulatory_update_event(self) -> None:
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE,
            severity="high",
            data={"title": "Test update", "url": "https://mattilsynet.no/test"},
        )
        assert event.event_type == RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE
        assert event.severity == "high"
        assert event.data["title"] == "Test update"

    def test_create_enforcement_action_event(self) -> None:
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
            severity="critical",
            data={"title": "Recall", "url": "https://mattilsynet.no/recall"},
        )
        assert event.event_type == RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION
        assert event.severity == "critical"

    def test_create_page_changed_event(self) -> None:
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_PAGE_CHANGED,
            severity="medium",
            data={"url": "https://mattilsynet.no/kosttilskudd"},
        )
        assert event.event_type == RegulatoryEventType.MATTILSYNET_PAGE_CHANGED

    def test_event_to_dict_includes_mattilsynet_type(self) -> None:
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE,
            severity="high",
        )
        d = event.to_dict()
        assert d["event_type"] == "mattilsynet_regulatory_update"
        assert d["severity"] == "high"
        assert "event_id" in d
        assert "timestamp" in d
