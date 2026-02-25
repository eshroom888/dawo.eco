"""Tests for DAWORelevanceFilter.

Story 6-4, Task 4: Relevance filter tests.
"""

import pytest

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig
from teams.dawo.scanners.claims_alerts.relevance_filter import DAWORelevanceFilter


@pytest.fixture
def relevance_filter(alert_config: ClaimsAlertConfig) -> DAWORelevanceFilter:
    return DAWORelevanceFilter(config=alert_config)


class TestIsRelevant:
    """Tests for is_relevant()."""

    def test_relevant_beta_glucan_claim(self, relevance_filter: DAWORelevanceFilter) -> None:
        """Returns True for beta-glucan claim."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.NEW_CLAIM_APPROVED,
            substance="Beta-glucan from oats",
            severity="medium",
        )
        assert relevance_filter.is_relevant(event) is True

    def test_relevant_hericium_substance(self, relevance_filter: DAWORelevanceFilter) -> None:
        """Returns True for Hericium substance."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            substance="Hericium erinaceus extract",
            severity="medium",
        )
        assert relevance_filter.is_relevant(event) is True

    def test_irrelevant_vitamin_c(self, relevance_filter: DAWORelevanceFilter) -> None:
        """Returns False for unrelated substance (Vitamin C)."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            substance="Vitamin C",
            severity="low",
            data={"claim_text": "Vitamin C contributes to normal immune function"},
        )
        assert relevance_filter.is_relevant(event) is False

    def test_critical_enforcement_always_relevant(self, relevance_filter: DAWORelevanceFilter) -> None:
        """CRITICAL enforcement always passes regardless of substance."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
            substance="Unknown supplement",
            severity="critical",
        )
        assert relevance_filter.is_relevant(event) is True

    def test_high_enforcement_always_relevant(self, relevance_filter: DAWORelevanceFilter) -> None:
        """HIGH severity enforcement always passes."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
            substance="Unrelated product",
            severity="high",
        )
        assert relevance_filter.is_relevant(event) is True

    def test_high_severity_non_enforcement_irrelevant_filtered(self, relevance_filter: DAWORelevanceFilter) -> None:
        """HIGH severity non-enforcement event with unrelated substance is filtered."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            substance="Vitamin C",
            severity="high",
            data={"claim_text": "Vitamin C immune function claim"},
        )
        assert relevance_filter.is_relevant(event) is False

    def test_keyword_match_in_data_values(self, relevance_filter: DAWORelevanceFilter) -> None:
        """Matches keyword in event data values."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE,
            substance="",
            severity="medium",
            data={"content_summary": "New regulation on functional mushroom supplements"},
        )
        assert relevance_filter.is_relevant(event) is True

    def test_keyword_match_in_keywords_matched_field(self, relevance_filter: DAWORelevanceFilter) -> None:
        """Matches keyword in Mattilsynet keywords_matched field."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_PAGE_CHANGED,
            substance="",
            severity="low",
            data={"keywords_matched": ["sopp", "chaga", "helse"]},
        )
        assert relevance_filter.is_relevant(event) is True


class TestExtractMatchedProducts:
    """Tests for extract_matched_products()."""

    def test_returns_correct_product_list(self, relevance_filter: DAWORelevanceFilter) -> None:
        """Returns correct matched keywords."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.NEW_CLAIM_APPROVED,
            substance="Beta-glucans from Hericium erinaceus",
            severity="high",
        )
        matched = relevance_filter.extract_matched_products(event)
        assert "hericium" in matched
        assert "beta-glucan" in matched

    def test_returns_empty_for_unrelated(self, relevance_filter: DAWORelevanceFilter) -> None:
        """Returns empty list for unrelated event."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            substance="Vitamin D",
            severity="low",
        )
        matched = relevance_filter.extract_matched_products(event)
        assert matched == []
