# RegulatoryEventEmitter

**Created:** 2026-02-19
**Origin:** Epic 6 (CleanMarket & Regulatory Intelligence)
**Location:** `core/regulatory/events.py`

---

## Overview

Async pub/sub event system for regulatory intelligence. Producers emit `RegulatoryEvent` instances, consumers subscribe via async generators. Built on `asyncio.Queue` with singleton access pattern.

## Architecture

```
Producers (7 modules)              Consumer (1 module)
┌──────────────────┐
│ HealthClaimsHarv │──┐
│ NovelFoodHarv    │──┤
│ MattilsynetHarv  │──┤         ┌─────────────────────┐
│ CompetitorScan   │──┼─emit()──▶ RegulatoryEventEmitter│
│ ClaimExtraction  │──┤         │ asyncio.Queue(100)   │
│ ViolationDetect  │──┤         └──────┬──────────────┘
│ EvidenceCollect  │──┘                │ subscribe()
                                       ▼
                              ┌─────────────────────────┐
                              │ RegulatoryAlertSubscriber│
                              │ → ClaimsAlertService     │
                              │ → Discord notifications  │
                              └─────────────────────────┘
```

## Event Types (18)

### EU Health Claims Register (Story 6-1)
| Event Type | Trigger |
|-----------|---------|
| `CLAIM_STATUS_CHANGED` | Claim status changed in EU register |
| `NEW_CLAIM_APPROVED` | New claim approved |
| `CLAIM_REMOVED` | Claim removed from register |
| `REGISTER_UPDATED` | Bulk register update detected |

### Novel Food Catalogue (Story 6-2)
| Event Type | Trigger |
|-----------|---------|
| `NOVEL_FOOD_STATUS_CHANGED` | Entry status changed |
| `NOVEL_FOOD_NEW_ENTRY` | New substance added |
| `NOVEL_FOOD_ENTRY_REMOVED` | Entry removed |
| `NOVEL_FOOD_CATALOGUE_UPDATED` | Bulk catalogue update |

### Mattilsynet Regulatory (Story 6-3)
| Event Type | Trigger |
|-----------|---------|
| `MATTILSYNET_REGULATORY_UPDATE` | New regulatory guidance |
| `MATTILSYNET_ENFORCEMENT_ACTION` | Enforcement action published |
| `MATTILSYNET_PAGE_CHANGED` | Monitored page changed |

### Competitor Monitoring (Story 6-5)
| Event Type | Trigger |
|-----------|---------|
| `COMPETITOR_CONTENT_DETECTED` | New competitor content found |
| `COMPETITOR_HEALTH_LANGUAGE_DETECTED` | Health-related language detected |

### Claim Extraction (Story 6-6)
| Event Type | Trigger |
|-----------|---------|
| `HEALTH_CLAIM_EXTRACTED` | Claim extracted from content |
| `HIGH_CONFIDENCE_CLAIM_DETECTED` | Claim with confidence >= threshold |

### Violation Detection (Story 6-7)
| Event Type | Trigger |
|-----------|---------|
| `EU_VIOLATION_DETECTED` | EU regulation violation found |
| `SUSPECT_CLAIM_FLAGGED` | Borderline claim flagged for review |

### Evidence Collection (Story 6-8)
| Event Type | Trigger |
|-----------|---------|
| `EVIDENCE_COLLECTED` | Screenshot/evidence captured |

## Core Classes

### `RegulatoryEvent` (dataclass)

```python
@dataclass
class RegulatoryEvent:
    event_type: RegulatoryEventType   # Required
    claim_id: str = ""                 # Optional context
    substance: str = ""                # Optional context
    old_status: str = ""               # For status changes
    new_status: str = ""               # For status changes
    severity: str = "low"              # "low" | "medium" | "high"
    data: dict = field(default_factory=dict)  # Arbitrary payload
    timestamp: datetime                # Auto: datetime.now(UTC)
    event_id: str                      # Auto: uuid4()
```

### `RegulatoryEventEmitter`

```python
class RegulatoryEventEmitter:
    MAX_QUEUE_SIZE = 100      # Per-subscriber queue depth
    MAX_SUBSCRIBERS = 100     # Max concurrent subscribers

    async def emit(self, event: RegulatoryEvent) -> None:
        """Broadcast event to all subscribers. Non-blocking."""

    async def subscribe(self) -> AsyncGenerator[RegulatoryEvent, None]:
        """Yields events as they arrive. Use with 'async for'."""

    @property
    def subscriber_count(self) -> int:
        """Current number of active subscribers."""
```

## Usage

### Access (Singleton)

```python
from core.regulatory.events import get_regulatory_events, regulatory_events

# Function call (preferred in DI constructors)
emitter = get_regulatory_events()

# Module-level alias (convenience)
emitter = regulatory_events
```

### Producing Events

```python
from core.regulatory.events import RegulatoryEvent, RegulatoryEventType

await emitter.emit(RegulatoryEvent(
    event_type=RegulatoryEventType.EU_VIOLATION_DETECTED,
    claim_id=str(violation.id),
    substance=violation.substance,
    severity="high",
    data={"article": "14.1a", "competitor": competitor_name},
))
```

### Consuming Events

```python
class RegulatoryAlertSubscriber:
    def __init__(self, service, event_emitter):
        self._service = service
        self._emitter = event_emitter

    async def start(self):
        async for event in self._emitter.subscribe():
            await self._service.handle_event(event)

    async def stop(self):
        await self._service.flush_pending()
```

**Current consumer:** `RegulatoryAlertSubscriber` (Story 6-4) routes events to `ClaimsAlertService`, which batches and sends Discord notifications.

## Producer Reference

| Story | Module | Events Emitted |
|-------|--------|---------------|
| 6-1 | `scanners/health_claims/harvester.py` | `CLAIM_STATUS_CHANGED`, `NEW_CLAIM_APPROVED`, `CLAIM_REMOVED`, `REGISTER_UPDATED` |
| 6-2 | `scanners/novel_food/harvester.py` | `NOVEL_FOOD_STATUS_CHANGED`, `NOVEL_FOOD_NEW_ENTRY`, `NOVEL_FOOD_ENTRY_REMOVED`, `NOVEL_FOOD_CATALOGUE_UPDATED` |
| 6-3 | `scanners/mattilsynet/harvester.py` | `MATTILSYNET_REGULATORY_UPDATE`, `MATTILSYNET_ENFORCEMENT_ACTION`, `MATTILSYNET_PAGE_CHANGED` |
| 6-5 | `scanners/competitor/scanner.py` | `COMPETITOR_CONTENT_DETECTED`, `COMPETITOR_HEALTH_LANGUAGE_DETECTED` |
| 6-6 | `scanners/claim_extraction/engine.py` | `HEALTH_CLAIM_EXTRACTED`, `HIGH_CONFIDENCE_CLAIM_DETECTED` |
| 6-7 | `scanners/violation_detection/detector.py` | `EU_VIOLATION_DETECTED`, `SUSPECT_CLAIM_FLAGGED` |
| 6-8 | `scanners/evidence_collection/collector.py` | `EVIDENCE_COLLECTED` |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Queue backend | `asyncio.Queue` | In-process, zero deps, sufficient for single-worker |
| Access pattern | Singleton via `get_regulatory_events()` | All producers share one emitter instance |
| Delivery | Fan-out to all subscribers | Each subscriber gets its own queue |
| Backpressure | `MAX_QUEUE_SIZE=100` | Prevents unbounded memory if consumer is slow |
| Error handling | Non-blocking emit | Producer never blocks on slow consumers |
| Thread safety | `asyncio.Lock` | Safe for concurrent async tasks |

## Epic 7 Relevance

Story 7-5 (Performance Feedback Loop) may extend the event system for analytics events. The existing pattern supports adding new `RegulatoryEventType` values and additional consumers without modifying producers.

---
*Documentation for Epic 7+ reference*
