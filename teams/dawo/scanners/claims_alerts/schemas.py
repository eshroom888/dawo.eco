"""Claims Alert Schemas and DTOs.

Epic 6, Story 6-4, Task 7: Data transfer objects for alert processing.
"""

from dataclasses import dataclass, field
from enum import Enum

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType


class AlertStatus(str, Enum):
    """Status of an alert processing result.

    Values:
        SENT: Alert was sent successfully
        BATCHED: Event was added to batch for later sending
        FILTERED: Event was filtered out (not relevant)
        FAILED: Alert send failed
        QUEUED_FOR_RETRY: Alert was queued for retry after failure
    """

    SENT = "sent"
    BATCHED = "batched"
    FILTERED = "filtered"
    FAILED = "failed"
    QUEUED_FOR_RETRY = "queued_for_retry"


class AlertCategory(str, Enum):
    """Category of regulatory alert.

    Values:
        NEW_CLAIM: New claim approved or authorized
        STATUS_CHANGE: Existing claim/food status changed
        ENFORCEMENT: Enforcement action detected
        REGULATORY_UPDATE: General regulatory update
        PAGE_CHANGE: Monitored page content changed
    """

    NEW_CLAIM = "new_claim"
    STATUS_CHANGE = "status_change"
    ENFORCEMENT = "enforcement"
    REGULATORY_UPDATE = "regulatory_update"
    PAGE_CHANGE = "page_change"
    COMPETITOR_CONTENT = "competitor_content"  # Story 6-5
    HEALTH_CLAIM_EXTRACTION = "health_claim_extraction"  # Story 6-6
    VIOLATION_DETECTION = "violation_detection"  # Story 6-7
    EVIDENCE_COLLECTION = "evidence_collection"  # Story 6-8


@dataclass
class AlertResult:
    """Result of processing a regulatory event for alerting.

    Attributes:
        status: Alert processing status
        events_processed: Number of events processed
        events_batched: Number of events currently in batch
        errors: List of error messages
    """

    status: AlertStatus = AlertStatus.FILTERED
    events_processed: int = 0
    events_batched: int = 0
    errors: list[str] = field(default_factory=list)


# Mapping from RegulatoryEventType to AlertCategory
_EVENT_CATEGORY_MAP: dict[RegulatoryEventType, AlertCategory] = {
    RegulatoryEventType.CLAIM_STATUS_CHANGED: AlertCategory.STATUS_CHANGE,
    RegulatoryEventType.NEW_CLAIM_APPROVED: AlertCategory.NEW_CLAIM,
    RegulatoryEventType.CLAIM_REMOVED: AlertCategory.STATUS_CHANGE,
    RegulatoryEventType.REGISTER_UPDATED: AlertCategory.REGULATORY_UPDATE,
    RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED: AlertCategory.STATUS_CHANGE,
    RegulatoryEventType.NOVEL_FOOD_NEW_ENTRY: AlertCategory.NEW_CLAIM,
    RegulatoryEventType.NOVEL_FOOD_ENTRY_REMOVED: AlertCategory.STATUS_CHANGE,
    RegulatoryEventType.NOVEL_FOOD_CATALOGUE_UPDATED: AlertCategory.REGULATORY_UPDATE,
    RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE: AlertCategory.REGULATORY_UPDATE,
    RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION: AlertCategory.ENFORCEMENT,
    RegulatoryEventType.MATTILSYNET_PAGE_CHANGED: AlertCategory.PAGE_CHANGE,
    RegulatoryEventType.COMPETITOR_CONTENT_DETECTED: AlertCategory.COMPETITOR_CONTENT,
    RegulatoryEventType.COMPETITOR_HEALTH_LANGUAGE_DETECTED: AlertCategory.COMPETITOR_CONTENT,
    RegulatoryEventType.HEALTH_CLAIM_EXTRACTED: AlertCategory.HEALTH_CLAIM_EXTRACTION,
    RegulatoryEventType.HIGH_CONFIDENCE_CLAIM_DETECTED: AlertCategory.HEALTH_CLAIM_EXTRACTION,
    RegulatoryEventType.EU_VIOLATION_DETECTED: AlertCategory.VIOLATION_DETECTION,
    RegulatoryEventType.SUSPECT_CLAIM_FLAGGED: AlertCategory.VIOLATION_DETECTION,
    RegulatoryEventType.EVIDENCE_COLLECTED: AlertCategory.EVIDENCE_COLLECTION,
}


def categorize_event(event: RegulatoryEvent) -> AlertCategory:
    """Map a RegulatoryEvent to its AlertCategory.

    Args:
        event: Regulatory event to categorize

    Returns:
        AlertCategory for the event type
    """
    return _EVENT_CATEGORY_MAP.get(
        event.event_type, AlertCategory.REGULATORY_UPDATE
    )


__all__ = [
    "AlertResult",
    "AlertStatus",
    "AlertCategory",
    "categorize_event",
]
