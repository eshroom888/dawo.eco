"""Regulatory Event System.

Epic 6, Story 6-1, Task 10: Event types for regulatory changes.

Pub/sub event system for regulatory monitoring, following the
PublishEventEmitter pattern from core/publishing/events.py.

Usage:
    from core.regulatory.events import regulatory_events, RegulatoryEvent

    # Emit an event
    await regulatory_events.emit(RegulatoryEvent(
        event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
        claim_id="ID-001",
        substance="Beta-glucans",
        old_status="on_hold",
        new_status="authorised",
        severity="critical",
    ))

    # Subscribe to events
    async for event in regulatory_events.subscribe():
        handle_event(event)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class RegulatoryEventType(str, Enum):
    """Types of regulatory events.

    Values:
        CLAIM_STATUS_CHANGED: Claim authorization status changed
        NEW_CLAIM_APPROVED: New claim authorised in register
        CLAIM_REMOVED: Claim removed from register
        REGISTER_UPDATED: Register download completed with changes
        NOVEL_FOOD_STATUS_CHANGED: Novel food classification changed (Story 6-2)
        NOVEL_FOOD_NEW_ENTRY: New entry added to catalogue (Story 6-2)
        NOVEL_FOOD_ENTRY_REMOVED: Entry removed from catalogue (Story 6-2)
        NOVEL_FOOD_CATALOGUE_UPDATED: Catalogue query completed with changes (Story 6-2)
        MATTILSYNET_REGULATORY_UPDATE: Mattilsynet regulatory change detected (Story 6-3)
        MATTILSYNET_ENFORCEMENT_ACTION: Mattilsynet enforcement action detected (Story 6-3)
        MATTILSYNET_PAGE_CHANGED: Mattilsynet monitored page changed (Story 6-3)
    """

    CLAIM_STATUS_CHANGED = "claim_status_changed"
    NEW_CLAIM_APPROVED = "new_claim_approved"
    CLAIM_REMOVED = "claim_removed"
    REGISTER_UPDATED = "register_updated"
    NOVEL_FOOD_STATUS_CHANGED = "novel_food_status_changed"
    NOVEL_FOOD_NEW_ENTRY = "novel_food_new_entry"
    NOVEL_FOOD_ENTRY_REMOVED = "novel_food_entry_removed"
    NOVEL_FOOD_CATALOGUE_UPDATED = "novel_food_catalogue_updated"
    MATTILSYNET_REGULATORY_UPDATE = "mattilsynet_regulatory_update"
    MATTILSYNET_ENFORCEMENT_ACTION = "mattilsynet_enforcement_action"
    MATTILSYNET_PAGE_CHANGED = "mattilsynet_page_changed"
    COMPETITOR_CONTENT_DETECTED = "competitor_content_detected"  # Story 6-5
    COMPETITOR_HEALTH_LANGUAGE_DETECTED = "competitor_health_language_detected"  # Story 6-5
    HEALTH_CLAIM_EXTRACTED = "health_claim_extracted"  # Story 6-6
    HIGH_CONFIDENCE_CLAIM_DETECTED = "high_confidence_claim_detected"  # Story 6-6
    EU_VIOLATION_DETECTED = "eu_violation_detected"  # Story 6-7
    SUSPECT_CLAIM_FLAGGED = "suspect_claim_flagged"  # Story 6-7
    EVIDENCE_COLLECTED = "evidence_collected"  # Story 6-8


@dataclass
class RegulatoryEvent:
    """Event emitted when regulatory changes are detected.

    Story 6-1, Task 10: Regulatory event for downstream consumers.

    Attributes:
        event_type: Type of regulatory event
        claim_id: EU register claim identifier
        substance: Substance/nutrient name
        old_status: Previous claim status (for status changes)
        new_status: New claim status (for status changes)
        severity: Change severity level
        data: Additional event-specific data
        timestamp: When event occurred
        event_id: Unique event identifier
    """

    event_type: RegulatoryEventType
    claim_id: str = ""
    substance: str = ""
    old_status: str = ""
    new_status: str = ""
    severity: str = "low"
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "claim_id": self.claim_id,
            "substance": self.substance,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "severity": self.severity,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class RegulatoryEventEmitter:
    """Event emitter for regulatory changes.

    Story 6-1, Task 10: Pub/sub for regulatory events.

    Thread-safe asyncio-based pub/sub for regulatory events.
    Follows the PublishEventEmitter pattern from core/publishing/events.py.

    Attributes:
        MAX_QUEUE_SIZE: Maximum events per subscriber queue (100)
        MAX_SUBSCRIBERS: Maximum concurrent subscribers (100)
    """

    MAX_QUEUE_SIZE = 100
    MAX_SUBSCRIBERS = 100

    def __init__(self) -> None:
        """Initialize event emitter."""
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        logger.info("RegulatoryEventEmitter initialized")

    async def emit(self, event: RegulatoryEvent) -> None:
        """Emit an event to all subscribers.

        Args:
            event: Regulatory event to emit
        """
        async with self._lock:
            dead_queues = []

            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(
                        "Subscriber queue full, dropping event %s",
                        event.event_id,
                    )
                except Exception as e:
                    logger.warning("Failed to emit to subscriber: %s", e)
                    dead_queues.append(queue)

            for queue in dead_queues:
                self._subscribers.remove(queue)

        logger.debug(
            "Emitted %s event for claim %s to %d subscribers",
            event.event_type.value,
            event.claim_id,
            len(self._subscribers),
        )

    async def subscribe(self) -> AsyncGenerator[RegulatoryEvent, None]:
        """Subscribe to regulatory events.

        Yields:
            RegulatoryEvent objects as they are emitted
        """
        if len(self._subscribers) >= self.MAX_SUBSCRIBERS:
            logger.warning("Max subscribers reached, rejecting new subscription")
            return

        queue: asyncio.Queue[RegulatoryEvent] = asyncio.Queue(
            maxsize=self.MAX_QUEUE_SIZE
        )

        async with self._lock:
            self._subscribers.append(queue)

        logger.debug("New subscriber added, total: %d", len(self._subscribers))

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)
            logger.debug("Subscriber removed, total: %d", len(self._subscribers))

    @property
    def subscriber_count(self) -> int:
        """Get current subscriber count."""
        return len(self._subscribers)


# Singleton instance
_regulatory_events: Optional[RegulatoryEventEmitter] = None


def get_regulatory_events() -> RegulatoryEventEmitter:
    """Get the global regulatory events emitter.

    Returns:
        RegulatoryEventEmitter singleton instance
    """
    global _regulatory_events
    if _regulatory_events is None:
        _regulatory_events = RegulatoryEventEmitter()
    return _regulatory_events


# Convenience alias
regulatory_events = get_regulatory_events()


__all__ = [
    "RegulatoryEvent",
    "RegulatoryEventType",
    "RegulatoryEventEmitter",
    "get_regulatory_events",
    "regulatory_events",
]
