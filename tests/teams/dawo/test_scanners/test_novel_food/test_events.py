"""Tests for Novel Food event types.

Story 6-2, Task 9: Extend event types for Novel Food changes.
"""

import pytest

from core.regulatory.events import RegulatoryEventType, RegulatoryEvent


class TestNovelFoodEventTypes:
    """Tests for Novel Food event types in RegulatoryEventType enum."""

    def test_novel_food_status_changed(self):
        assert RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED.value == "novel_food_status_changed"

    def test_novel_food_new_entry(self):
        assert RegulatoryEventType.NOVEL_FOOD_NEW_ENTRY.value == "novel_food_new_entry"

    def test_novel_food_entry_removed(self):
        assert RegulatoryEventType.NOVEL_FOOD_ENTRY_REMOVED.value == "novel_food_entry_removed"

    def test_novel_food_catalogue_updated(self):
        assert RegulatoryEventType.NOVEL_FOOD_CATALOGUE_UPDATED.value == "novel_food_catalogue_updated"

    def test_novel_food_event_is_str(self):
        assert isinstance(RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED, str)


class TestRegulatoryEventWithNovelFood:
    """Tests that RegulatoryEvent supports novel food data."""

    def test_create_novel_food_event(self):
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED,
            claim_id="",
            substance="Hericium erinaceus",
            old_status="not_determined",
            new_status="novel",
            severity="critical",
            data={
                "entry_name": "Hericium erinaceus - fruiting body",
                "field_changed": "novel_food_status",
                "species_common": "Lion's Mane",
            },
        )
        assert event.event_type == RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED
        assert event.substance == "Hericium erinaceus"
        assert event.data["entry_name"] == "Hericium erinaceus - fruiting body"

    def test_novel_food_event_to_dict(self):
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.NOVEL_FOOD_NEW_ENTRY,
            substance="Inonotus obliquus",
            severity="high",
            data={"entry_name": "Chaga - extract"},
        )
        d = event.to_dict()
        assert d["event_type"] == "novel_food_new_entry"
        assert d["substance"] == "Inonotus obliquus"
        assert d["data"]["entry_name"] == "Chaga - extract"


class TestEventExports:
    """Tests that __all__ includes novel food event types."""

    def test_events_module_all(self):
        from core.regulatory import events
        assert "RegulatoryEventType" in events.__all__

    def test_regulatory_init_exports_event_type(self):
        from core.regulatory import __all__ as reg_all
        assert "RegulatoryEventType" in reg_all
