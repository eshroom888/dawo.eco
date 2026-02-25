# Story 6.4: New Claims Activation Alerts

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want immediate alerts when new health claims become usable for DAWO products,
So that I can update my content strategy ahead of competitors.

---

## Acceptance Criteria

1. **Given** a new claim is approved (from Stories 6.1-6.3 event system)
   **When** it applies to DAWO products (mushroom/adaptogen categories)
   **Then** Discord alert is sent: "New claim approved: [claim text]"
   **And** alert includes: applicable products, wording guidelines, effective date
   **And** alert is sent within 60 seconds of event emission

2. **Given** a claim alert is generated
   **When** operator views details in the alert
   **Then** they see: full claim text, usage conditions, example compliant phrases
   **And** content team notification indicates caption templates may need updating

3. **Given** multiple claims are approved in the same monitoring cycle
   **When** alerts would spam the Discord channel
   **Then** they are batched into summary: "X new regulatory updates for mushroom supplements"
   **And** individual claims are linked for review in each embed field

4. **Given** a claim has usage restrictions or conditions
   **When** alert is generated
   **Then** restrictions are prominently displayed in the Discord embed
   **And** compliance checker relevance rules acknowledge the new claim data
   **And** the system records which claims are newly actionable

5. **Given** regulatory news is detected from Mattilsynet (enforcement actions)
   **When** it has HIGH or CRITICAL severity
   **Then** an alert is sent with appropriate urgency formatting
   **And** the alert distinguishes between new opportunities (approved claims) and risk alerts (enforcement)

6. **Given** the Discord webhook is unavailable
   **When** an alert fails to send
   **Then** the alert is queued for retry using the existing NotificationQueue pattern
   **And** retry follows exponential backoff (1min, 5min, 15min, 1hr)
   **And** alerts are never lost — they persist until successfully delivered or max retries exhausted

---

## Tasks / Subtasks

- [x] Task 1: Create claims alert config (AC: #1, #3, #6)
  - [x] 1.1 Create `config/dawo_claims_alerts.json` with:
    - `enabled`: true
    - `webhook_url`: `"${DISCORD_REGULATORY_WEBHOOK_URL}"`
    - `batch_window_seconds`: 300 (5 minutes — regulatory monitors run weekly/daily, batching within a single run)
    - `dashboard_url`: `"https://app.imagoeco.com/dawo/regulatory"`
    - `max_retry_attempts`: 5
    - `backoff_schedule`: [60, 300, 900, 3600]
    - `dawo_product_keywords`: ["lion's mane", "chaga", "reishi", "cordyceps", "shiitake", "maitake", "hericium", "inonotus", "ganoderma", "lentinula", "grifola", "beta-glucan", "adaptogen", "functional mushroom"]
    - `severity_emoji_map`: {"critical": "red_circle", "high": "orange_circle", "medium": "yellow_circle", "low": "white_circle"}
  - [x] 1.2 Create frozen dataclass `ClaimsAlertConfig` in `teams/dawo/scanners/claims_alerts/config.py`
  - [x] 1.3 Create `build_claims_alert_config(data: dict) -> ClaimsAlertConfig` builder function
  - [x] 1.4 Validate in `__post_init__`: non-empty webhook_url, non-empty product_keywords, batch_window > 0

- [x] Task 2: Create alert formatter (AC: #1, #2, #4, #5)
  - [x] 2.1 Create `teams/dawo/scanners/claims_alerts/formatter.py` with `ClaimsAlertFormatter`
  - [x] 2.2 Accept config via constructor
  - [x] 2.3 Implement `format_claim_alert(event: RegulatoryEvent) -> DiscordEmbed` — single claim alert
    - Title: emoji + "New Approved Claim" or "Regulatory Update" or "Enforcement Action" based on event type
    - Description: claim text or update summary
    - Fields: Applicable Products, Usage Conditions, Effective Date, Severity, Source
    - Color: Use severity-based color (SUCCESS for new claims, WARNING for enforcement, INFO for updates)
  - [x] 2.4 Implement `format_batch_alert(events: list[RegulatoryEvent]) -> DiscordEmbed` — batched summary
    - Title: "X Regulatory Updates Detected"
    - Description: Summary counts by type (new claims, status changes, enforcement)
    - Fields: One field per event with inline title + claim text (max 25 fields per embed)
    - Footer: "Review full details at [dashboard_url]"
  - [x] 2.5 Implement `format_enforcement_alert(event: RegulatoryEvent) -> DiscordEmbed` — high-urgency enforcement
    - Title: "ENFORCEMENT ACTION: [title]"
    - Color: ERROR (red)
    - Fields: Source URL, Category, Keywords Matched, Potential Impact
  - [x] 2.6 Implement `_determine_embed_color(event: RegulatoryEvent) -> EmbedColor` helper
  - [x] 2.7 Implement `_extract_applicable_products(event: RegulatoryEvent) -> str` — match event substance/data against dawo_product_keywords
  - [x] 2.8 Implement `_format_usage_conditions(event: RegulatoryEvent) -> str` — extract conditions from event.data

- [x] Task 3: Create alert batcher (AC: #3)
  - [x] 3.1 Create `teams/dawo/scanners/claims_alerts/batcher.py` with `ClaimsAlertBatcher`
  - [x] 3.2 Accept config via constructor
  - [x] 3.3 Implement `add_event(event: RegulatoryEvent) -> bool` — add event to batch, return True if batch window expired and batch should flush
  - [x] 3.4 Implement `get_and_clear_batch() -> list[RegulatoryEvent]` — return all batched events and reset
  - [x] 3.5 Implement `has_pending() -> bool` — check if batch has unflushed events
  - [x] 3.6 Implement `flush_if_expired() -> Optional[list[RegulatoryEvent]]` — flush if batch window expired, return None if not
  - [x] 3.7 Use in-memory list + timestamp (no Redis needed — regulatory monitors run infrequently, same process)
  - [x] 3.8 Batch window starts at first event, flushes at `batch_window_seconds` elapsed or when explicitly flushed

- [x] Task 4: Create DAWO product relevance filter (AC: #1, #4)
  - [x] 4.1 Create `teams/dawo/scanners/claims_alerts/relevance_filter.py` with `DAWORelevanceFilter`
  - [x] 4.2 Accept config (product keywords list) via constructor
  - [x] 4.3 Implement `is_relevant(event: RegulatoryEvent) -> bool` — check if event relates to DAWO products
    - Check `event.substance` against product keywords (case-insensitive)
    - Check `event.data` dict values for keyword matches
    - Check `event.data.get("keywords_matched", [])` for Mattilsynet events
    - Enforcement actions (CRITICAL/HIGH) always pass relevance filter regardless of keyword match
  - [x] 4.4 Implement `extract_matched_products(event: RegulatoryEvent) -> list[str]` — return which DAWO products this event impacts

- [x] Task 5: Create claims alert service (AC: #1-#6)
  - [x] 5.1 Create `teams/dawo/scanners/claims_alerts/service.py` with `ClaimsAlertService`
  - [x] 5.2 Accept all deps via constructor: `discord_client: DiscordClientProtocol`, `formatter: ClaimsAlertFormatter`, `batcher: ClaimsAlertBatcher`, `relevance_filter: DAWORelevanceFilter`, `notification_queue: NotificationQueueProtocol`, `config: ClaimsAlertConfig`
  - [x] 5.3 Implement `handle_event(event: RegulatoryEvent) -> AlertResult`
    - Check enabled flag
    - Check relevance filter — skip irrelevant events (log debug)
    - For CRITICAL/HIGH enforcement: send immediately (bypass batcher)
    - For other events: add to batcher, flush if window expired
    - On flush: format as batch (>1) or single (<= 1) embed
    - Send via discord_client.send_embed()
    - On failure: queue for retry via notification_queue
    - Return AlertResult with status, events_processed, events_batched
  - [x] 5.4 Implement `flush_pending() -> AlertResult` — force-flush any pending batch (for shutdown/cleanup)
  - [x] 5.5 Implement `_send_alert(embed: DiscordEmbed) -> bool` — send with error handling, return success
  - [x] 5.6 Implement `_queue_for_retry(embed: DiscordEmbed, error: str) -> None` — save to notification queue

- [x] Task 6: Create event subscriber (AC: #1)
  - [x] 6.1 Create `teams/dawo/scanners/claims_alerts/subscriber.py` with `RegulatoryAlertSubscriber`
  - [x] 6.2 Accept `ClaimsAlertService` and `RegulatoryEventEmitter` via constructor
  - [x] 6.3 Implement `start() -> None` — subscribe to regulatory events and route to service
    - Use `regulatory_events.subscribe()` async generator
    - For each event: call `service.handle_event(event)`
    - Log all events received and their routing decisions
  - [x] 6.4 Implement `stop() -> None` — flush pending batch and unsubscribe
  - [x] 6.5 Handle subscriber errors gracefully — log and continue, never crash the subscriber loop

- [x] Task 7: Create schemas/DTOs (AC: #1-#5)
  - [x] 7.1 Create `teams/dawo/scanners/claims_alerts/schemas.py`
  - [x] 7.2 Create `AlertResult` dataclass: status (sent/batched/filtered/failed), events_processed (int), events_batched (int), errors (list[str])
  - [x] 7.3 Create `AlertStatus` enum: SENT, BATCHED, FILTERED, FAILED, QUEUED_FOR_RETRY
  - [x] 7.4 Create `AlertCategory` enum: NEW_CLAIM, STATUS_CHANGE, ENFORCEMENT, REGULATORY_UPDATE, PAGE_CHANGE
  - [x] 7.5 Implement `categorize_event(event: RegulatoryEvent) -> AlertCategory` function — map RegulatoryEventType to AlertCategory

- [x] Task 8: Create package __init__.py and register in team_spec.py (AC: #1)
  - [x] 8.1 Create `teams/dawo/scanners/claims_alerts/__init__.py` with complete `__all__`
  - [x] 8.2 Export: ClaimsAlertConfig, ClaimsAlertFormatter, ClaimsAlertBatcher, DAWORelevanceFilter, ClaimsAlertService, RegulatoryAlertSubscriber, AlertResult, AlertStatus, AlertCategory
  - [x] 8.3 Register `ClaimsAlertService` as `RegisteredService` in team_spec.py with capabilities `["regulatory_alerting", "claims_alerts", "discord_notifications"]`
  - [x] 8.4 Register `ClaimsAlertFormatter` as `RegisteredService` with capability `["regulatory_alerting", "notification_formatting"]`
  - [x] 8.5 Register `DAWORelevanceFilter` as `RegisteredService` with capability `["regulatory_alerting", "relevance_filtering"]`
  - [x] 8.6 Register `ClaimsAlertBatcher` as `RegisteredService` with capability `["regulatory_alerting", "notification_batching"]`
  - [x] 8.7 Register `RegulatoryAlertSubscriber` as `RegisteredService` with capability `["regulatory_alerting", "event_subscription"]`
  - [x] 8.8 Add all new imports to team_spec.py

- [x] Task 9: Create unit tests (AC: #1-#6)
  - [x] 9.1 Create `tests/teams/dawo/test_scanners/test_claims_alerts/` with `__init__.py`, `conftest.py`
  - [x] 9.2 Test `ClaimsAlertFormatter.format_claim_alert()` with NEW_CLAIM_APPROVED event — verify embed title, fields, color
  - [x] 9.3 Test `ClaimsAlertFormatter.format_claim_alert()` with CLAIM_STATUS_CHANGED event
  - [x] 9.4 Test `ClaimsAlertFormatter.format_claim_alert()` with NOVEL_FOOD_STATUS_CHANGED event
  - [x] 9.5 Test `ClaimsAlertFormatter.format_enforcement_alert()` with MATTILSYNET_ENFORCEMENT_ACTION event
  - [x] 9.6 Test `ClaimsAlertFormatter.format_batch_alert()` with multiple events — verify count, fields
  - [x] 9.7 Test `ClaimsAlertFormatter._extract_applicable_products()` matches DAWO product keywords
  - [x] 9.8 Test `ClaimsAlertFormatter._extract_applicable_products()` returns empty for unrelated substances
  - [x] 9.9 Test `ClaimsAlertBatcher.add_event()` returns False when within batch window
  - [x] 9.10 Test `ClaimsAlertBatcher.add_event()` returns True when batch window expired
  - [x] 9.11 Test `ClaimsAlertBatcher.get_and_clear_batch()` returns all events and resets
  - [x] 9.12 Test `ClaimsAlertBatcher.flush_if_expired()` returns None when not expired
  - [x] 9.13 Test `ClaimsAlertBatcher.flush_if_expired()` returns events when expired
  - [x] 9.14 Test `DAWORelevanceFilter.is_relevant()` returns True for beta-glucan claim
  - [x] 9.15 Test `DAWORelevanceFilter.is_relevant()` returns True for Hericium substance
  - [x] 9.16 Test `DAWORelevanceFilter.is_relevant()` returns False for unrelated substance (e.g., "vitamin C")
  - [x] 9.17 Test `DAWORelevanceFilter.is_relevant()` returns True for CRITICAL enforcement regardless of substance
  - [x] 9.18 Test `DAWORelevanceFilter.extract_matched_products()` returns correct product list
  - [x] 9.19 Test `ClaimsAlertService.handle_event()` sends alert for relevant HIGH severity event
  - [x] 9.20 Test `ClaimsAlertService.handle_event()` skips irrelevant events (filtered)
  - [x] 9.21 Test `ClaimsAlertService.handle_event()` batches non-urgent events
  - [x] 9.22 Test `ClaimsAlertService.handle_event()` sends immediately for CRITICAL enforcement
  - [x] 9.23 Test `ClaimsAlertService.handle_event()` queues for retry on Discord failure
  - [x] 9.24 Test `ClaimsAlertService.flush_pending()` sends batched events
  - [x] 9.25 Test `ClaimsAlertService.handle_event()` with disabled config returns early
  - [x] 9.26 Test `RegulatoryAlertSubscriber.start()` receives events and routes to service
  - [x] 9.27 Test `RegulatoryAlertSubscriber.stop()` flushes pending batch
  - [x] 9.28 Test `ClaimsAlertConfig` validation (empty webhook, empty keywords)
  - [x] 9.29 Test `categorize_event()` maps all RegulatoryEventType values correctly
  - [x] 9.30 Test `AlertResult` dataclass creation and field defaults

- [x] Task 10: Create integration tests (AC: #1-#6)
  - [x] 10.1 Test full flow: emit RegulatoryEvent -> subscriber receives -> service processes -> formatter creates embed -> mock Discord client receives embed
  - [x] 10.2 Test batching: emit 3 events within window -> single batch Discord call after flush
  - [x] 10.3 Test enforcement bypass: emit CRITICAL enforcement -> immediate Discord call (no batching)
  - [x] 10.4 Test relevance filtering: emit irrelevant event -> no Discord call
  - [x] 10.5 Test retry on failure: mock Discord failure -> verify notification queue receives failed alert

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This is the **fourth story in Epic 6** (CleanMarket & Regulatory Intelligence). It is the first **consumer** of the regulatory event system built in Stories 6-1, 6-2, and 6-3. Those stories emit `RegulatoryEvent` objects via the `RegulatoryEventEmitter` pub/sub system — this story subscribes to those events and routes them to Discord as operator-facing alerts.

### Epic 6 Context

Story 6-4 bridges two existing systems:
1. **Input:** `RegulatoryEventEmitter` (core/regulatory/events.py) — emits events for claim changes, novel food updates, Mattilsynet enforcement
2. **Output:** `DiscordWebhookClient` (integrations/discord/client.py) — sends rich embeds to Discord channels

**No new external data sources.** No HTTP scraping, no database models, no migrations. This is pure event processing + notification formatting.

### Key Differences from Stories 6-1, 6-2, 6-3

| Aspect | Stories 6-1/6-2/6-3 (Producers) | Story 6-4 (Consumer) |
|--------|--------------------------------|---------------------|
| Data source | External (EU sites, Mattilsynet) | Internal (RegulatoryEventEmitter) |
| Output | Database records + events | Discord notifications |
| Database | New tables + migrations | **None** — no new tables |
| New dependencies | pandas, feedparser, etc. | **None** — all deps exist |
| LLM needed | No | No |
| Complexity | Medium-High (scraping, parsing) | Low-Medium (event routing, formatting) |

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], Stories 6-1/6-2/6-3 patterns

```
teams/dawo/scanners/claims_alerts/       # NEW — alert consumer module
├── __init__.py                          # Export all public types
├── config.py                            # ClaimsAlertConfig
├── formatter.py                         # ClaimsAlertFormatter (event -> DiscordEmbed)
├── batcher.py                           # ClaimsAlertBatcher (in-memory time-window batching)
├── relevance_filter.py                  # DAWORelevanceFilter (product keyword matching)
├── service.py                           # ClaimsAlertService (orchestrator)
├── subscriber.py                        # RegulatoryAlertSubscriber (event loop)
└── schemas.py                           # AlertResult, AlertStatus, AlertCategory

config/
└── dawo_claims_alerts.json              # NEW — alert config

tests/teams/dawo/test_scanners/test_claims_alerts/ # NEW
├── __init__.py
├── conftest.py                          # Fixtures: sample events, mock Discord client
├── test_formatter.py
├── test_batcher.py
├── test_relevance_filter.py
├── test_service.py
├── test_subscriber.py
├── test_config.py
└── test_schemas.py

tests/integration/
└── test_claims_alerts_integration.py    # NEW
```

### Event Types to Handle (ALL 11)

**Source:** [core/regulatory/events.py]

The subscriber must handle ALL `RegulatoryEventType` values:

| Event Type | Source Story | Alert Category | Urgency |
|------------|-------------|---------------|---------|
| `CLAIM_STATUS_CHANGED` | 6-1 | STATUS_CHANGE | Normal (batch) |
| `NEW_CLAIM_APPROVED` | 6-1 | NEW_CLAIM | Normal (batch) |
| `CLAIM_REMOVED` | 6-1 | STATUS_CHANGE | Normal (batch) |
| `REGISTER_UPDATED` | 6-1 | REGULATORY_UPDATE | Low (batch) |
| `NOVEL_FOOD_STATUS_CHANGED` | 6-2 | STATUS_CHANGE | Normal (batch) |
| `NOVEL_FOOD_NEW_ENTRY` | 6-2 | NEW_CLAIM | Normal (batch) |
| `NOVEL_FOOD_ENTRY_REMOVED` | 6-2 | STATUS_CHANGE | Normal (batch) |
| `NOVEL_FOOD_CATALOGUE_UPDATED` | 6-2 | REGULATORY_UPDATE | Low (batch) |
| `MATTILSYNET_REGULATORY_UPDATE` | 6-3 | REGULATORY_UPDATE | Normal (batch) |
| `MATTILSYNET_ENFORCEMENT_ACTION` | 6-3 | ENFORCEMENT | **Immediate** (bypass batcher) |
| `MATTILSYNET_PAGE_CHANGED` | 6-3 | PAGE_CHANGE | Low (batch) |

**Immediate send rule:** `MATTILSYNET_ENFORCEMENT_ACTION` and any event with `severity in ("critical", "high")` bypass the batcher and send immediately.

### Discord Integration (MUST REUSE — Do NOT Reinvent)

**Source:** [integrations/discord/client.py], [integrations/discord/__init__.py]

The existing Discord infrastructure from Epic 4 provides everything needed:

```python
from integrations.discord import (
    DiscordWebhookClient,       # HTTP client with rate limit handling
    DiscordClientProtocol,      # Protocol for DI/mocking
    DiscordEmbed,               # Rich embed dataclass
    EmbedField,                 # Individual embed field
    EmbedColor,                 # Predefined color enum
    DiscordRateLimitError,      # 429 with retry_after
    DiscordAuthError,           # 401/403 unrecoverable
)
```

**EmbedColor values available:**
- `SUCCESS` (0x2ECC71) — Use for new approved claims (opportunities)
- `WARNING` (0xFFA500) — Use for borderline/medium severity
- `ERROR` (0xE74C3C) — Use for enforcement actions (threats)
- `INFO` (0x0099FF) — Use for general regulatory updates

**CRITICAL:** Use `DiscordClientProtocol` for dependency injection, not `DiscordWebhookClient` directly. This enables testing with `AsyncMock(spec=DiscordClientProtocol)`.

### Notification Queue Pattern (MUST REUSE)

**Source:** [core/notifications/queue.py]

For retry on Discord failure, reuse the existing `NotificationQueue` pattern:

```python
from core.notifications.queue import NotificationQueue

# On send failure:
await notification_queue.queue_failed(alert_data)

# Background retry job processes queue with exponential backoff
```

However, since the existing `NotificationQueue` is Redis-based and tightly coupled to approval notifications, the dev agent should **create a protocol abstraction** for queue interaction:

```python
@runtime_checkable
class NotificationQueueProtocol(Protocol):
    async def queue_failed(self, data: dict) -> None: ...
    async def retry_failed(self) -> int: ...
```

This allows testing without Redis and future swap to a regulatory-specific queue if needed.

### Batching Strategy

**Source:** [core/notifications/publish_batcher.py] (reference pattern)

Unlike the publish batcher (Redis-based, 15-minute window), this story uses **in-memory batching** because:
- Regulatory monitors run infrequently (weekly/daily)
- Events from a single monitor run arrive in rapid succession (seconds apart)
- A 5-minute batch window captures all events from one monitoring cycle
- No cross-process batching needed (subscriber runs in same process as monitors)

```python
class ClaimsAlertBatcher:
    def __init__(self, config: ClaimsAlertConfig) -> None:
        self._batch: list[RegulatoryEvent] = []
        self._batch_start: Optional[datetime] = None
        self._window = timedelta(seconds=config.batch_window_seconds)
```

### Relevance Filter — DAWO Product Keywords

**Source:** [config/dawo_health_claims.json], [config/dawo_novel_food.json], [config/dawo_mattilsynet.json]

Not all regulatory events are relevant to DAWO. The filter checks event content against product keywords:

- **Latin names:** Hericium erinaceus, Inonotus obliquus, Ganoderma lucidum, Cordyceps militaris, Lentinula edodes, Grifola frondosa
- **Common names:** Lion's Mane, Chaga, Reishi, Cordyceps, Shiitake, Maitake
- **Compounds:** beta-glucan, polysaccharide, adaptogen
- **Categories:** functional mushroom, medicinal mushroom, mushroom supplement

**Exception:** CRITICAL and HIGH severity enforcement actions bypass the relevance filter — any enforcement in the supplement space is relevant to DAWO for CleanMarket intelligence (Story 6-7 integration point).

### Registration Pattern (MUST FOLLOW)

**Source:** [teams/dawo/team_spec.py], Stories 6-1/6-2/6-3 patterns

```python
# In team_spec.py — add to SERVICES list
RegisteredService(
    name="claims_alert_service",
    service_class=ClaimsAlertService,
    capabilities=["regulatory_alerting", "claims_alerts", "discord_notifications"],
    requires_session=False,  # No database — event processing only
),
RegisteredService(
    name="claims_alert_formatter",
    service_class=ClaimsAlertFormatter,
    capabilities=["regulatory_alerting", "notification_formatting"],
    requires_session=False,
),
RegisteredService(
    name="dawo_relevance_filter",
    service_class=DAWORelevanceFilter,
    capabilities=["regulatory_alerting", "relevance_filtering"],
    requires_session=False,
),
RegisteredService(
    name="claims_alert_batcher",
    service_class=ClaimsAlertBatcher,
    capabilities=["regulatory_alerting", "notification_batching"],
    requires_session=False,
),
RegisteredService(
    name="regulatory_alert_subscriber",
    service_class=RegulatoryAlertSubscriber,
    capabilities=["regulatory_alerting", "event_subscription"],
    requires_session=False,
),
```

### Config Injection Pattern (MUST FOLLOW)

**Source:** [core/config.py], Stories 6-1/6-2/6-3 config.py

```python
@dataclass(frozen=True)
class ClaimsAlertConfig:
    enabled: bool = True
    webhook_url: str = ""
    batch_window_seconds: int = 300
    dashboard_url: str = ""
    max_retry_attempts: int = 5
    backoff_schedule: tuple[int, ...] = (60, 300, 900, 3600)
    dawo_product_keywords: tuple[str, ...] = ()
    severity_emoji_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        errors: list[str] = []
        if self.enabled and not self.webhook_url:
            errors.append("webhook_url must not be empty when enabled")
        if not self.dawo_product_keywords:
            errors.append("dawo_product_keywords must not be empty")
        if self.batch_window_seconds <= 0:
            errors.append("batch_window_seconds must be positive")
        if errors:
            raise ValueError(f"Invalid ClaimsAlertConfig: {'; '.join(errors)}")
```

### Testing Strategy (TDD Required)

**Source:** BMAD workflow requires red-green-refactor cycle

**Mock patterns:**
```python
@pytest.fixture
def sample_new_claim_event():
    """Sample NEW_CLAIM_APPROVED event from Story 6-1."""
    return RegulatoryEvent(
        event_type=RegulatoryEventType.NEW_CLAIM_APPROVED,
        claim_id="CLAIM-2026-001",
        substance="Beta-glucans from Hericium erinaceus",
        old_status="",
        new_status="authorised",
        severity="high",
        data={
            "claim_text": "Beta-glucans contribute to normal immune function",
            "conditions_of_use": "3g per day",
            "product_categories": ["food supplement"],
            "approval_date": "2026-02-01",
        },
    )

@pytest.fixture
def sample_enforcement_event():
    """Sample MATTILSYNET_ENFORCEMENT_ACTION event from Story 6-3."""
    return RegulatoryEvent(
        event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
        claim_id="",
        substance="",
        severity="critical",
        data={
            "title": "Tilbakekalling: Soppekstrakt med ulovlige helsepastander",
            "url": "https://www.mattilsynet.no/varsler/tilbakekalling-soppekstrakt",
            "category": "enforcement",
            "keywords_matched": ["tilbakekalling", "helsepastander", "sopp"],
            "content_summary": "Mattilsynet har vedtatt tilbakekalling av et kosttilskudd.",
        },
    )

@pytest.fixture
def sample_irrelevant_event():
    """Event that does NOT relate to DAWO products."""
    return RegulatoryEvent(
        event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
        claim_id="CLAIM-9999",
        substance="Vitamin C",
        old_status="authorised",
        new_status="on_hold",
        severity="low",
        data={"claim_text": "Vitamin C contributes to normal immune function"},
    )

@pytest.fixture
def mock_discord_client():
    client = AsyncMock(spec=DiscordClientProtocol)
    client.send_embed = AsyncMock(return_value=None)
    return client

@pytest.fixture
def alert_config():
    return ClaimsAlertConfig(
        enabled=True,
        webhook_url="https://discord.com/api/webhooks/test/test",
        batch_window_seconds=300,
        dashboard_url="https://app.imagoeco.com/dawo/regulatory",
        dawo_product_keywords=(
            "lion's mane", "chaga", "reishi", "cordyceps",
            "hericium", "inonotus", "ganoderma", "beta-glucan",
            "adaptogen", "functional mushroom", "sopp",
        ),
    )
```

**Target: ~30 unit tests + ~5 integration tests**

### Previous Story Learnings (CRITICAL — Apply All)

**Source:** [6-3-mattilsynet-regulatory-monitor.md#Completion-Notes], [6-2-novel-food-catalogue-monitor.md#Completion-Notes], [docs/pre-submission-checklist.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | All components accept deps via constructor, NEVER load files |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in timestamps |
| Add logging to exception handlers | All exceptions logged before continuing |
| Pre-initialize variables before try blocks | Avoid UnboundLocalError |
| Add `logger.debug()` for swallowed exceptions | Don't silently eat exceptions |
| Populate all result fields | Don't leave AlertResult fields empty |
| TDD approach | Write tests first for each task |
| Protocol-based DI for testing | Use `DiscordClientProtocol`, `NotificationQueueProtocol` |

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

This story has **NO LLM agent** — it's a pure event processing + notification formatting pipeline. No LLM tier assignment needed. All components are RegisteredService (not RegisteredAgent).

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], Stories 6-1/6-2/6-3 code review learnings

1. **NEVER load config directly** — Accept via injection (`ClaimsAlertConfig`)
2. **NEVER create a new Discord client** — Accept via `DiscordClientProtocol` injection
3. **NEVER create new database tables** — This story has no persistence layer
4. **NEVER reinvent notification queue** — Reuse or adapt existing `NotificationQueue` pattern
5. **NEVER reinvent embed formatting** — Reuse `DiscordEmbed`, `EmbedField`, `EmbedColor` from integrations/discord/
6. **NEVER swallow exceptions without logging**
7. **NEVER use `datetime.utcnow()`** — Use `datetime.now(UTC)`
8. **NEVER block on Discord failures** — Queue for retry, never crash
9. **NEVER send more than 25 fields per embed** — Discord API limit
10. **NEVER import `DiscordWebhookClient` directly in service** — Use `DiscordClientProtocol` for testability

### New Dependencies

**None.** All dependencies already exist:
- `integrations/discord/` — DiscordWebhookClient, DiscordEmbed, etc.
- `core/regulatory/events.py` — RegulatoryEventEmitter, RegulatoryEvent
- `core/notifications/queue.py` — NotificationQueue pattern (reference)

No changes to `requirements.txt` needed.

### Project Structure Notes

- Scanner placed in `teams/dawo/scanners/claims_alerts/` (alert consumer is logically grouped with regulatory scanners)
- Config in `config/dawo_claims_alerts.json` following project naming pattern
- Tests mirror source: `tests/teams/dawo/test_scanners/test_claims_alerts/`
- Reuses `RegulatoryEventEmitter` singleton from Story 6-1
- Reuses `DiscordWebhookClient` + `DiscordEmbed` from Epic 4
- No conflicts with Stories 6-1, 6-2, 6-3 code (purely additive — consumes their events)
- No database models, no migrations

### References

- [Source: epics.md#Story-6.4] — Original story requirements (FR28)
- [Source: core/regulatory/events.py] — RegulatoryEventEmitter pub/sub system (11 event types)
- [Source: integrations/discord/client.py] — DiscordWebhookClient, DiscordEmbed, EmbedColor
- [Source: integrations/discord/__init__.py] — Discord package exports and Protocol
- [Source: core/notifications/queue.py] — NotificationQueue retry pattern
- [Source: core/notifications/publish_batcher.py] — Batching pattern reference
- [Source: core/notifications/publish_notifier.py] — Notification service pattern reference
- [Source: core/notifications/rate_limiter.py] — Rate limiting pattern reference
- [Source: config/dawo_notifications.json] — Existing notification config structure
- [Source: 6-1-eu-health-claims-register-monitor.md] — Event emission patterns
- [Source: 6-2-novel-food-catalogue-monitor.md] — Event emission patterns
- [Source: 6-3-mattilsynet-regulatory-monitor.md] — Event emission patterns, learnings
- [Source: teams/dawo/team_spec.py] — Registration patterns (RegisteredService)
- [Source: project-context.md] — Critical implementation rules and anti-patterns
- [Source: architecture.md#Project-Structure] — Directory organization
- [Source: docs/pre-submission-checklist.md] — Quality checklist

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A — no debug issues encountered during implementation.

### Completion Notes List

- All 10 tasks implemented with TDD red-green-refactor cycle
- 60 unit tests + 5 integration tests = 65 total tests, all passing
- No new dependencies added — reuses existing Discord, regulatory events, and notification patterns
- No database tables or migrations — pure event processing + notification formatting
- `NotificationQueueProtocol` created for DI/testing without Redis dependency
- CRITICAL/HIGH severity enforcement events bypass both relevance filter and batcher for immediate Discord delivery
- In-memory batching (not Redis) — appropriate for infrequent regulatory monitor runs
- All components registered as `RegisteredService` in team_spec.py (90 total services)
- Complete `__all__` exports in `__init__.py`
- Followed all anti-patterns from project-context.md and previous story learnings

### Change Log

| Change | Reason |
|--------|--------|
| Created schemas.py during Task 5 (before Task 7) | Service needed AlertResult/AlertStatus as return types |
| Used `NotificationQueueProtocol` instead of direct `NotificationQueue` | Existing queue is Redis-based and tightly coupled to approval notifications |
| **[Code Review]** Relevance filter bypass restricted to enforcement events only | Was bypassing for ALL high/critical — would false-positive on non-DAWO products |
| **[Code Review]** Formatter `_extract_applicable_products()` now handles list values | Was ignoring list values (keywords_matched, product_categories) in event.data |
| **[Code Review]** Enforcement embed no longer duplicates content_summary | Was showing same text in both description and "Potential Impact" field |
| **[Code Review]** `test_batches_non_urgent_events` fixed to use medium severity | Was using high severity event that gets sent immediately, masking bug |
| **[Code Review]** Removed duplicate `alert_config` fixtures from 4 test files | Now use shared conftest.py fixture — single source of truth |
| **[Code Review]** Inlined unused `batched_count` variable in service.py | Dead variable, constant `1` is clearer |

### File List

**Source files (9):**
- `config/dawo_claims_alerts.json` — Alert configuration (webhook, keywords, batching)
- `teams/dawo/scanners/claims_alerts/__init__.py` — Package exports (12 symbols)
- `teams/dawo/scanners/claims_alerts/config.py` — ClaimsAlertConfig frozen dataclass + builder
- `teams/dawo/scanners/claims_alerts/formatter.py` — ClaimsAlertFormatter (event -> DiscordEmbed)
- `teams/dawo/scanners/claims_alerts/batcher.py` — ClaimsAlertBatcher (in-memory time-window)
- `teams/dawo/scanners/claims_alerts/relevance_filter.py` — DAWORelevanceFilter (keyword matching)
- `teams/dawo/scanners/claims_alerts/service.py` — ClaimsAlertService orchestrator + NotificationQueueProtocol
- `teams/dawo/scanners/claims_alerts/subscriber.py` — RegulatoryAlertSubscriber (event loop)
- `teams/dawo/scanners/claims_alerts/schemas.py` — AlertResult, AlertStatus, AlertCategory, categorize_event

**Modified files (1):**
- `teams/dawo/team_spec.py` — Added 5 RegisteredService entries + imports

**Test files (9):**
- `tests/teams/dawo/test_scanners/test_claims_alerts/__init__.py`
- `tests/teams/dawo/test_scanners/test_claims_alerts/conftest.py` — Shared fixtures
- `tests/teams/dawo/test_scanners/test_claims_alerts/test_config.py` — 10 tests
- `tests/teams/dawo/test_scanners/test_claims_alerts/test_formatter.py` — 9 tests
- `tests/teams/dawo/test_scanners/test_claims_alerts/test_batcher.py` — 9 tests
- `tests/teams/dawo/test_scanners/test_claims_alerts/test_relevance_filter.py` — 9 tests
- `tests/teams/dawo/test_scanners/test_claims_alerts/test_service.py` — 6 tests
- `tests/teams/dawo/test_scanners/test_claims_alerts/test_subscriber.py` — 2 tests
- `tests/teams/dawo/test_scanners/test_claims_alerts/test_schemas.py` — 14 tests
- `tests/integration/test_claims_alerts_integration.py` — 5 tests
