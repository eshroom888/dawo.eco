"""Tests for claims alert schemas.

Story 6-4, Task 9: Schema and DTO tests.
"""

import pytest

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from teams.dawo.scanners.claims_alerts.schemas import (
    AlertResult,
    AlertStatus,
    AlertCategory,
    categorize_event,
)


class TestAlertResult:
    """Tests for AlertResult dataclass."""

    def test_default_creation(self) -> None:
        """AlertResult has correct defaults."""
        result = AlertResult()
        assert result.status == AlertStatus.FILTERED
        assert result.events_processed == 0
        assert result.events_batched == 0
        assert result.errors == []

    def test_custom_creation(self) -> None:
        """AlertResult with custom fields."""
        result = AlertResult(
            status=AlertStatus.SENT,
            events_processed=3,
            events_batched=0,
            errors=["test error"],
        )
        assert result.status == AlertStatus.SENT
        assert result.events_processed == 3
        assert result.errors == ["test error"]


class TestAlertStatus:
    """Tests for AlertStatus enum."""

    def test_all_values(self) -> None:
        """All expected status values exist."""
        assert AlertStatus.SENT == "sent"
        assert AlertStatus.BATCHED == "batched"
        assert AlertStatus.FILTERED == "filtered"
        assert AlertStatus.FAILED == "failed"
        assert AlertStatus.QUEUED_FOR_RETRY == "queued_for_retry"


class TestCategorizeEvent:
    """Tests for categorize_event() mapping."""

    @pytest.mark.parametrize(
        "event_type,expected_category",
        [
            (RegulatoryEventType.CLAIM_STATUS_CHANGED, AlertCategory.STATUS_CHANGE),
            (RegulatoryEventType.NEW_CLAIM_APPROVED, AlertCategory.NEW_CLAIM),
            (RegulatoryEventType.CLAIM_REMOVED, AlertCategory.STATUS_CHANGE),
            (RegulatoryEventType.REGISTER_UPDATED, AlertCategory.REGULATORY_UPDATE),
            (RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED, AlertCategory.STATUS_CHANGE),
            (RegulatoryEventType.NOVEL_FOOD_NEW_ENTRY, AlertCategory.NEW_CLAIM),
            (RegulatoryEventType.NOVEL_FOOD_ENTRY_REMOVED, AlertCategory.STATUS_CHANGE),
            (RegulatoryEventType.NOVEL_FOOD_CATALOGUE_UPDATED, AlertCategory.REGULATORY_UPDATE),
            (RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE, AlertCategory.REGULATORY_UPDATE),
            (RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION, AlertCategory.ENFORCEMENT),
            (RegulatoryEventType.MATTILSYNET_PAGE_CHANGED, AlertCategory.PAGE_CHANGE),
        ],
    )
    def test_maps_all_event_types(
        self,
        event_type: RegulatoryEventType,
        expected_category: AlertCategory,
    ) -> None:
        """categorize_event maps all RegulatoryEventType values correctly."""
        event = RegulatoryEvent(event_type=event_type)
        assert categorize_event(event) == expected_category
