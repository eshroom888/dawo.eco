"""DAWO Product Relevance Filter.

Epic 6, Story 6-4, Task 4: Filter regulatory events by DAWO product relevance.

Checks regulatory events against DAWO product keywords to determine
if an event is relevant to the DAWO product line (mushroom supplements,
adaptogens). CRITICAL/HIGH enforcement actions bypass the filter.
"""

import logging

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig

logger = logging.getLogger(__name__)

# Severity levels that bypass relevance filter for enforcement events
_BYPASS_SEVERITIES = {"critical", "high"}

# Event types classified as enforcement actions
_ENFORCEMENT_TYPES = {
    RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
}


class DAWORelevanceFilter:
    """Filters regulatory events by DAWO product relevance.

    Checks event substance and data against configured product keywords.
    CRITICAL and HIGH severity enforcement actions always pass the filter.

    Attributes:
        _keywords: Lowercased product keywords for matching
    """

    def __init__(self, config: ClaimsAlertConfig) -> None:
        """Initialize filter with product keywords.

        Args:
            config: Claims alert configuration containing product keywords
        """
        self._keywords = [kw.lower() for kw in config.dawo_product_keywords]

    def is_relevant(self, event: RegulatoryEvent) -> bool:
        """Check if event relates to DAWO products.

        Args:
            event: Regulatory event to check

        Returns:
            True if event is relevant to DAWO products
        """
        # CRITICAL/HIGH enforcement actions always pass
        if (
            event.event_type in _ENFORCEMENT_TYPES
            and event.severity.lower() in _BYPASS_SEVERITIES
        ):
            return True

        # Check substance
        if self._matches_keywords(event.substance):
            return True

        # Check data dict values (string values only)
        for value in event.data.values():
            if isinstance(value, str) and self._matches_keywords(value):
                return True
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and self._matches_keywords(item):
                        return True

        return False

    def extract_matched_products(self, event: RegulatoryEvent) -> list[str]:
        """Return which DAWO products this event impacts.

        Args:
            event: Regulatory event to check

        Returns:
            List of matched product keywords
        """
        searchable = self._build_searchable_text(event)
        return [kw for kw in self._keywords if kw in searchable]

    def _matches_keywords(self, text: str) -> bool:
        """Check if text contains any product keyword.

        Args:
            text: Text to search

        Returns:
            True if any keyword found
        """
        text_lower = text.lower()
        return any(kw in text_lower for kw in self._keywords)

    def _build_searchable_text(self, event: RegulatoryEvent) -> str:
        """Build combined searchable text from event fields.

        Args:
            event: Regulatory event

        Returns:
            Lowercased combined text for keyword matching
        """
        parts = [event.substance]
        for value in event.data.values():
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts.extend(str(item) for item in value)
        return " ".join(parts).lower()


__all__ = [
    "DAWORelevanceFilter",
]
