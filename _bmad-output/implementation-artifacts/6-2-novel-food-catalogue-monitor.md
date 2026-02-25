# Story 6.2: Novel Food Catalogue Monitor

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want the EU Novel Food Catalogue monitored for status changes,
So that I'm alerted to classification changes affecting DAWO products.

---

## Acceptance Criteria

1. **Given** the Novel Food monitor is scheduled (weekly Sunday 5:30 AM)
   **When** it executes
   **Then** it queries the EU Food & Feed Portal for all configured mushroom species (lion's mane, chaga, reishi, cordyceps, shiitake, maitake)
   **And** it compares current catalogue entries against the previously stored snapshot
   **And** it identifies: new entries, removed entries, status changes, authorization updates, condition changes

2. **Given** a product classification changes
   **When** it affects DAWO products (e.g., Chaga novel food status update)
   **Then** it is flagged URGENT for operator review
   **And** alert includes: previous status, new status, species, entry name, implications
   **And** an event is published via the RegulatoryEventEmitter for downstream consumers (Story 6-4)

3. **Given** a new mushroom species or form is added to the catalogue
   **When** it is relevant to wellness supplements
   **Then** it is logged for market opportunity review
   **And** compliance implications are noted

4. **Given** no changes are detected
   **When** the monitor completes
   **Then** it logs successful check with timestamp
   **And** no alerts are triggered
   **And** the snapshot timestamp is updated

5. **Given** the EU Food & Feed Portal is unavailable
   **When** retry middleware exhausts attempts
   **Then** the scan is marked INCOMPLETE and queued for next cycle
   **And** the previous snapshot remains available

6. **Given** the portal page structure changes unexpectedly
   **When** parsing fails (missing selectors, different HTML layout, API response format change)
   **Then** a parse error is logged with details
   **And** the monitor returns INCOMPLETE status without corrupting existing data

---

## Tasks / Subtasks

- [x]Task 1: Extend regulatory data models for Novel Food (AC: #1, #2, #3, #4)
  - [x]1.1 Add to `core/regulatory/models.py`:
    - `NovelFoodEntry` (id, snapshot_id FK, species_latin, species_common, entry_name, novel_food_status, authorization_status, history_of_consumption, member_state_comments, commission_comments, conditions_of_use, regulation_reference, union_list_entry, source_url, raw_html_hash, created_at, updated_at)
    - `NovelFoodSnapshot` (id, snapshot_hash, total_entries, relevant_entries, species_queried, search_duration_seconds, created_at)
    - `NovelFoodChange` (id, snapshot_id FK, species_latin, entry_name, change_type enum, field_changed, old_value, new_value, severity enum, created_at)
  - [x]1.2 Add `NovelFoodStatus` enum: NOVEL, NOT_NOVEL, NOT_DETERMINED, AMBIGUOUS
  - [x]1.3 Add `AuthorizationStatus` enum: AUTHORISED, NOT_AUTHORISED, PENDING, NOT_APPLICABLE
  - [x]1.4 Add indexes: `idx_novel_food_entries_species` (species_latin), `idx_novel_food_entries_snapshot` (snapshot_id), `idx_novel_food_changes_snapshot` (snapshot_id), `idx_novel_food_changes_severity` (severity)
  - [x]1.5 Update `core/regulatory/__init__.py` with all new exports in `__all__`

- [x]Task 2: Create Alembic migration (AC: #1)
  - [x]2.1 Create migration `2026_02_xx_001_create_novel_food_tables.py`
  - [x]2.2 Create tables: `novel_food_entries`, `novel_food_snapshots`, `novel_food_changes`
  - [x]2.3 Add all indexes and foreign keys (cascade delete from snapshot)

- [x]Task 3: Create Novel Food config (AC: #1, #2)
  - [x]3.1 Create `config/dawo_novel_food.json` with:
    - `monitor.schedule_cron`: `"30 5 * * 0"` (Sunday 5:30 AM)
    - `monitor.search_url`: `"https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search"`
    - `monitor.portal_url`: `"https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search"`
    - `monitor.request_delay_seconds`: 10 (conservative: 1 req per 10 sec)
    - `monitor.max_retries`: 3
    - `monitor.timeout_seconds`: 30
    - `monitor.user_agent`: `"DAWO-ECO-RegulatoryMonitor/1.0"`
    - `species`: list of objects with `latin_name`, `common_names` (array), `is_dawo_product` (bool)
    - `alert_on_status_change`: list of status transitions to alert on
  - [x]3.2 Create frozen dataclass `NovelFoodMonitorConfig` in `teams/dawo/scanners/novel_food/config.py`
  - [x]3.3 Create `build_novel_food_config(data: dict) -> NovelFoodMonitorConfig` builder function
  - [x]3.4 Validate config in `__post_init__` (non-empty species list, valid URL)

- [x]Task 4: Create catalogue client (AC: #1, #5, #6)
  - [x]4.1 Create `teams/dawo/scanners/novel_food/client.py` with `NovelFoodCatalogueClient`
  - [x]4.2 Accept `httpx.AsyncClient`, `RetryMiddlewareProtocol`, and config via constructor
  - [x]4.3 Implement `search_species(species_name: str) -> bytes` — fetches search results for one species
  - [x]4.4 Implement `fetch_all_species(species_list: list[SpeciesConfig]) -> dict[str, bytes]` — fetches all species with rate limiting delay between requests
  - [x]4.5 Try backend JSON endpoint first (`/backend/novel-food-catalogue/search?searchText=`), fall back to HTML page scraping
  - [x]4.6 Use `RetryMiddleware.execute_with_retry()` for each HTTP request
  - [x]4.7 Set proper headers: User-Agent, Accept-Language: en, Accept: application/json (for backend endpoint)
  - [x]4.8 Create `NovelFoodClientError` exception class
  - [x]4.9 Implement `asyncio.sleep(config.request_delay_seconds)` between species queries

- [x]Task 5: Create catalogue parser (AC: #1, #6)
  - [x]5.1 Create `teams/dawo/scanners/novel_food/parser.py` with `CatalogueParser`
  - [x]5.2 Implement `parse_json_response(data: bytes, species_latin: str) -> list[NovelFoodEntryRecord]` — parse backend JSON response
  - [x]5.3 Implement `parse_html_response(data: bytes, species_latin: str) -> list[NovelFoodEntryRecord]` — parse HTML with BeautifulSoup as fallback
  - [x]5.4 Try JSON parsing first; if response is not JSON, fall back to HTML parsing
  - [x]5.5 Extract fields: entry_name, novel_food_status, authorization_status, history_of_consumption, member_state_comments, commission_comments, conditions_of_use, regulation_reference, union_list_entry
  - [x]5.6 Normalize status values to enums (handle variations like "Yes", "No", "Not determined", case variations)
  - [x]5.7 Compute SHA-256 hash of raw response bytes for each entry
  - [x]5.8 Create `CatalogueParseError` exception with details about what failed
  - [x]5.9 Log warning (not error) when a species returns zero entries — may be expected for some search terms

- [x]Task 6: Create change detector (AC: #1, #2, #3)
  - [x]6.1 Create `teams/dawo/scanners/novel_food/change_detector.py` with `NovelFoodChangeDetector`
  - [x]6.2 Implement `detect(previous: list[NovelFoodEntryRecord], current: list[NovelFoodEntryRecord]) -> list[CatalogueChangeRecord]`
  - [x]6.3 Match entries by composite key: (species_latin, entry_name) — NOT a single ID (catalogue has no stable IDs)
  - [x]6.4 Detect NEW entries (in current, not in previous)
  - [x]6.5 Detect REMOVED entries (in previous, not in current)
  - [x]6.6 Detect field-level MODIFIED changes on matched entries
  - [x]6.7 Detect STATUS_CHANGED as special case (novel_food_status or authorization_status changed)
  - [x]6.8 Assign severity:
    - CRITICAL: novel_food_status change for DAWO products, authorization_status change
    - HIGH: novel_food_status change for non-DAWO species, new entries for relevant species
    - MEDIUM: conditions_of_use changes, regulation_reference changes
    - LOW: member_state_comments changes, commission_comments changes
  - [x]6.9 Handle first run (empty previous) — return empty change list

- [x]Task 7: Create Novel Food repository (AC: #1, #2, #3, #4)
  - [x]7.1 Create `teams/dawo/scanners/novel_food/repository.py` with `NovelFoodRepository`
  - [x]7.2 Accept `AsyncSession` via constructor
  - [x]7.3 Implement `save_snapshot(entries: list[NovelFoodEntryRecord], species_queried: int, search_duration: float) -> NovelFoodSnapshot`
  - [x]7.4 Implement `get_latest_snapshot() -> Optional[NovelFoodSnapshot]`
  - [x]7.5 Implement `get_entries_by_snapshot(snapshot_id: UUID) -> Sequence[NovelFoodEntry]`
  - [x]7.6 Implement `save_changes(changes: list[CatalogueChangeRecord], snapshot_id: UUID) -> int`
  - [x]7.7 Implement `get_entries_by_species(snapshot_id: UUID, species_latin: str) -> Sequence[NovelFoodEntry]`
  - [x]7.8 Implement `commit() -> None` (called by pipeline after all saves)
  - [x]7.9 Use batch insert for entries (`__table__.insert()` with mappings)
  - [x]7.10 Compute SHA-256 hash from sorted entry data for snapshot deduplication

- [x]Task 8: Create monitor pipeline (AC: #1-#6)
  - [x]8.1 Create `teams/dawo/scanners/novel_food/pipeline.py` with `NovelFoodMonitorPipeline`
  - [x]8.2 Accept all dependencies via constructor: client, parser, change_detector, repository, event_emitter, config
  - [x]8.3 Implement `execute() -> MonitorResult`
  - [x]8.4 Pipeline stages:
    1. Fetch all species from catalogue (client)
    2. Parse responses to entry records (parser)
    3. Load previous snapshot from DB (repository)
    4. Reconstruct previous entry records from DB (repository)
    5. Detect changes vs previous (change_detector)
    6. Save new snapshot + entries (repository)
    7. Save change records (repository)
    8. Commit transaction (repository)
    9. Publish events for CRITICAL/HIGH severity changes (event_emitter)
  - [x]8.5 Return `MonitorResult` with: status, total_entries, species_queried, changes_detected, errors
  - [x]8.6 Handle first run (no previous snapshot) — save baseline without change detection
  - [x]8.7 Handle partial failures — if some species fail, continue with others, report partial success
  - [x]8.8 Track total search duration for performance monitoring

- [x]Task 9: Extend event types for Novel Food changes (AC: #2)
  - [x]9.1 Add to `RegulatoryEventType` enum in `core/regulatory/events.py`:
    - `NOVEL_FOOD_STATUS_CHANGED`
    - `NOVEL_FOOD_NEW_ENTRY`
    - `NOVEL_FOOD_ENTRY_REMOVED`
    - `NOVEL_FOOD_CATALOGUE_UPDATED`
  - [x]9.2 Verify `RegulatoryEvent` dataclass supports novel food data fields (species_latin, entry_name in data dict)
  - [x]9.3 Update `core/regulatory/__init__.py` exports if new types added

- [x]Task 10: Register in team_spec.py (AC: #1)
  - [x]10.1 Register `NovelFoodMonitorPipeline` as `RegisteredService` with capabilities `["regulatory_monitoring", "novel_food"]`
  - [x]10.2 Register `NovelFoodCatalogueClient` as `RegisteredService` with capability `["eu_data_access"]`
  - [x]10.3 Register `NovelFoodRepository` as `RegisteredService` with `requires_session=True`
  - [x]10.4 Register `CatalogueParser` as `RegisteredService` with capability `["data_parsing"]`
  - [x]10.5 Register `NovelFoodChangeDetector` as `RegisteredService` with capability `["change_detection"]`
  - [x]10.6 Add all new imports to scanner `__init__.py` with complete `__all__`

- [x]Task 11: Create unit tests (AC: #1-#6)
  - [x]11.1 Create `tests/teams/dawo/test_scanners/test_novel_food/` with `__init__.py`, `conftest.py`
  - [x]11.2 Test `CatalogueParser.parse_json_response()` with valid JSON response
  - [x]11.3 Test `CatalogueParser.parse_html_response()` with valid HTML response
  - [x]11.4 Test `CatalogueParser` fallback from JSON to HTML
  - [x]11.5 Test `CatalogueParser` with unexpected format (raises CatalogueParseError)
  - [x]11.6 Test `CatalogueParser` normalizes status values correctly
  - [x]11.7 Test `CatalogueParser` returns empty list for no results (not error)
  - [x]11.8 Test `NovelFoodChangeDetector.detect()` identifies NEW entries
  - [x]11.9 Test `NovelFoodChangeDetector.detect()` identifies REMOVED entries
  - [x]11.10 Test `NovelFoodChangeDetector.detect()` identifies MODIFIED entries (field-level)
  - [x]11.11 Test `NovelFoodChangeDetector.detect()` identifies STATUS_CHANGED with correct severity
  - [x]11.12 Test `NovelFoodChangeDetector.detect()` handles empty previous (first run)
  - [x]11.13 Test `NovelFoodChangeDetector.detect()` handles no changes
  - [x]11.14 Test `NovelFoodChangeDetector` severity assignment (CRITICAL for DAWO products)
  - [x]11.15 Test `NovelFoodCatalogueClient.search_species()` with mocked httpx (JSON response)
  - [x]11.16 Test `NovelFoodCatalogueClient.search_species()` with mocked httpx (HTML fallback)
  - [x]11.17 Test `NovelFoodCatalogueClient.fetch_all_species()` rate limiting delay
  - [x]11.18 Test `NovelFoodCatalogueClient.search_species()` retry on failure
  - [x]11.19 Test `NovelFoodRepository.save_snapshot()` creates snapshot + entries
  - [x]11.20 Test `NovelFoodRepository.get_latest_snapshot()` returns most recent
  - [x]11.21 Test `NovelFoodRepository.save_changes()` persists change records
  - [x]11.22 Test `NovelFoodRepository.get_entries_by_species()` filters correctly
  - [x]11.23 Test `NovelFoodMonitorPipeline.execute()` full happy path
  - [x]11.24 Test `NovelFoodMonitorPipeline.execute()` first run (no previous snapshot)
  - [x]11.25 Test `NovelFoodMonitorPipeline.execute()` fetch failure → INCOMPLETE
  - [x]11.26 Test `NovelFoodMonitorPipeline.execute()` parse failure → INCOMPLETE
  - [x]11.27 Test `NovelFoodMonitorPipeline.execute()` partial failure (some species fail) → PARTIAL
  - [x]11.28 Test `NovelFoodMonitorPipeline.execute()` publishes events for CRITICAL changes
  - [x]11.29 Test `NovelFoodMonitorConfig` validation (empty species, invalid URL)
  - [x]11.30 Test all SQLAlchemy models (NovelFoodEntry, NovelFoodSnapshot, NovelFoodChange)

- [x]Task 12: Create integration tests (AC: #1-#5)
  - [x]12.1 Test full pipeline: mock fetch → parse → detect → save → events
  - [x]12.2 Test change detection across two sequential runs
  - [x]12.3 Test status change detection end-to-end (novel → not_novel)
  - [x]12.4 Test event emission for CRITICAL status change on DAWO product
  - [x]12.5 Test graceful degradation on fetch failure (INCOMPLETE status)

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This is the **second story in Epic 6** (CleanMarket & Regulatory Intelligence). It builds directly on the regulatory foundation established in Story 6-1, reusing the `core/regulatory/` models, events system, and `MonitorResult`/`MonitorStatus` schemas.

### Epic 6 Context

Story 6-2 monitors the EU Novel Food Catalogue — a separate regulatory database from the Health Claims Register (Story 6-1). The Novel Food Catalogue tracks whether food ingredients are classified as "novel food" under EU Regulation 2015/2283. For DAWO:
- **Chaga** is classified as supplement-only (novel food)
- **Lion's Mane, Cordyceps** are novel food
- **Shiitake** fruiting body is NOT novel (traditional consumption)
- Any reclassification directly impacts what DAWO can legally sell and how it markets products

**Critical domain knowledge:** The Novel Food Catalogue has NO stable entry IDs. Entries must be matched by composite key (species_latin + entry_name). The same mushroom species can have MULTIPLE entries with DIFFERENT statuses depending on form (fruiting body vs extract vs mycelium).

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], Story 6-1 patterns

```
core/regulatory/                          # EXISTING — extend with Novel Food models
├── __init__.py                           # Update exports
├── models.py                             # ADD: NovelFoodEntry, NovelFoodSnapshot, NovelFoodChange, enums
└── events.py                             # ADD: NOVEL_FOOD_* event types to RegulatoryEventType

teams/dawo/scanners/novel_food/           # NEW — monitor module
├── __init__.py                           # Export all public types
├── config.py                             # NovelFoodMonitorConfig (frozen dataclass)
├── client.py                             # NovelFoodCatalogueClient (HTTP scraping + RetryMiddleware)
├── parser.py                             # CatalogueParser (JSON/HTML → NovelFoodEntryRecord)
├── change_detector.py                    # NovelFoodChangeDetector (entry-level diff)
├── repository.py                         # NovelFoodRepository (SQLAlchemy persistence)
├── pipeline.py                           # NovelFoodMonitorPipeline (orchestrator)
└── schemas.py                            # NovelFoodEntryRecord, CatalogueChangeRecord, SpeciesConfig

config/
└── dawo_novel_food.json                  # NEW — monitor config + species list

migrations/versions/
└── 2026_02_xx_001_create_novel_food_tables.py  # NEW

tests/teams/dawo/test_scanners/test_novel_food/  # NEW
├── __init__.py
├── conftest.py                           # Fixtures: sample entries, mock client, mock repo
├── test_parser.py
├── test_change_detector.py
├── test_client.py
├── test_repository.py
├── test_pipeline.py
├── test_config.py
├── test_events.py
└── test_models.py

tests/integration/
└── test_novel_food_integration.py        # NEW
```

### Data Source (CRITICAL — Research Finding)

**Source:** [docs/research/eu-novel-food-catalogue-research.md]

The EU Novel Food Catalogue is accessible via the Food & Feed Information Portal. **Key findings from research:**

- **Search URL:** `https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search`
- **Backend API (undocumented):** `https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search` with `searchText=` parameter — returns JSON
- **Updates page:** `https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/updates`
- **No official public API or bulk download** — must query per species
- **License:** EU Open Data reuse policy (Commission Decision 2011/833/EU)
- **Update frequency:** Ad-hoc, approximately monthly
- **No changelog or RSS feed** — must snapshot and diff locally

**IMPORTANT — Verify at implementation start:**
1. Test `httpx GET` to backend endpoint with `searchText=Hericium` — check if JSON response
2. If backend returns JSON, use that (faster, structured)
3. If backend blocked or returns HTML, use BeautifulSoup to parse the HTML search page
4. If page is JS-rendered only, prepare Playwright fallback (but do NOT add dependency unless needed)

### Access Strategy (MUST FOLLOW)

**Primary:** Try the undocumented backend JSON API first:
```python
response = await client.get(
    "https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search",
    params={"searchText": species_name},
    headers={
        "Accept": "application/json",
        "Accept-Language": "en",
        "User-Agent": "DAWO-ECO-RegulatoryMonitor/1.0",
    },
    timeout=30.0,
)
```

**Fallback:** If JSON not available, parse HTML:
```python
response = await client.get(
    "https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search",
    params={"searchText": species_name},
    headers={"Accept-Language": "en"},
)
soup = BeautifulSoup(response.text, "lxml")
entries = soup.select(".search-result-item")  # Verify selector at impl time
```

**Rate Limiting:** 1 request per 10 seconds minimum. Total run: ~12 queries (6 species x ~2 name variants) = ~2 minutes.

### Key Differences from Story 6-1

| Aspect | Story 6-1 (Health Claims) | Story 6-2 (Novel Food) |
|--------|--------------------------|------------------------|
| Data source | XLS bulk download (single file) | Per-species HTTP queries (multiple requests) |
| Parsing | pandas read_excel/read_csv | JSON parse or BeautifulSoup HTML |
| Data volume | ~2,500 claims in one download | ~5-20 entries per species query |
| Entry matching | By Claim ID (stable, unique) | By (species_latin, entry_name) composite key |
| Rate limiting | Single download, no rate limit concern | 10-second delay between requests |
| Partial failure | All-or-nothing download | Individual species can fail independently |
| Status values | AUTHORISED, NON_AUTHORISED, ON_HOLD, WITHDRAWN | NOVEL, NOT_NOVEL, NOT_DETERMINED, AMBIGUOUS |
| pandas usage | Heavy (DataFrame for 2500+ rows) | None needed — use lists of dataclasses |

### No Pandas Required

Unlike Story 6-1 which operates on a large spreadsheet, Story 6-2 works with small sets of individual entries. Use `list[NovelFoodEntryRecord]` (dataclasses) instead of DataFrames. Change detection operates on lists, not pandas merge.

### New Dependencies

**None required** — all dependencies are already in `requirements.txt`:
- `httpx` — already present
- `beautifulsoup4>=4.12.0` — already present (from Story 5.2)
- `lxml>=5.0.0` — already present (from Story 5.2)

**NOT needed for this story:**
- `playwright` — only if JS-rendering required (deferred decision)
- `pandas` — not needed, entries are small structured records

### Change Detection Strategy

Since there are no stable IDs in the Novel Food Catalogue, match entries by composite key:

```python
def _make_key(entry: NovelFoodEntryRecord) -> tuple[str, str]:
    return (entry.species_latin.lower().strip(), entry.entry_name.lower().strip())

def detect(
    self,
    previous: list[NovelFoodEntryRecord],
    current: list[NovelFoodEntryRecord],
) -> list[CatalogueChangeRecord]:
    prev_map = {_make_key(e): e for e in previous}
    curr_map = {_make_key(e): e for e in current}

    prev_keys = set(prev_map.keys())
    curr_keys = set(curr_map.keys())

    new_entries = curr_keys - prev_keys
    removed_entries = prev_keys - curr_keys
    common_entries = prev_keys & curr_keys

    # Field-level comparison for common entries
    for key in common_entries:
        prev_entry = prev_map[key]
        curr_entry = curr_map[key]
        # Compare tracked fields...
```

### Severity Mapping

```python
SEVERITY_MAP = {
    # Field → (default_severity, dawo_product_severity)
    "novel_food_status": ("high", "critical"),
    "authorization_status": ("high", "critical"),
    "conditions_of_use": ("medium", "medium"),
    "regulation_reference": ("medium", "medium"),
    "union_list_entry": ("medium", "high"),
    "member_state_comments": ("low", "low"),
    "commission_comments": ("low", "low"),
    "history_of_consumption": ("low", "medium"),
}
```

DAWO products (from config `is_dawo_product: true`): lion's mane, chaga, reishi, cordyceps, shiitake, maitake — all get elevated severity.

### EventBus Pattern (MUST FOLLOW)

**Source:** [core/regulatory/events.py], Story 6-1 patterns

Reuse the existing `RegulatoryEventEmitter` singleton. Add new event types to `RegulatoryEventType` enum. Emit events for CRITICAL and HIGH severity changes:

```python
if change.severity in ("critical", "high"):
    event = RegulatoryEvent(
        event_type=RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED,
        claim_id="",  # Not applicable for novel food
        substance=change.species_latin,
        old_status=change.old_value or "",
        new_status=change.new_value or "",
        severity=change.severity,
        data={
            "entry_name": change.entry_name,
            "field_changed": change.field_changed,
            "species_common": species_common_name,
        },
    )
    await self._event_emitter.emit(event)
```

### RetryMiddleware Usage (MUST FOLLOW)

**Source:** [teams/dawo/middleware/retry.py], Story 6-1 client.py patterns

```python
class NovelFoodCatalogueClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        retry: RetryMiddlewareProtocol,
        config: NovelFoodMonitorConfig,
    ) -> None:
        self._client = http_client
        self._retry = retry
        self._config = config

    async def search_species(self, species_name: str) -> bytes:
        async def _fetch() -> bytes:
            resp = await self._client.get(
                self._config.search_url,
                params={"searchText": species_name},
                headers=self._headers,
                timeout=self._config.timeout_seconds,
            )
            resp.raise_for_status()
            return resp.content

        result = await self._retry.execute_with_retry(
            _fetch, context=f"novel_food_search_{species_name}"
        )
        if not result.success:
            raise NovelFoodClientError(
                f"Search failed for '{species_name}' after retries: {result.last_error}"
            )
        return result.response
```

### Registration Pattern (MUST FOLLOW)

**Source:** [teams/dawo/team_spec.py], Story 6-1 patterns

```python
# In team_spec.py — add to SERVICES list
RegisteredService(
    name="novel_food_monitor",
    service_class=NovelFoodMonitorPipeline,
    capabilities=["regulatory_monitoring", "novel_food"],
    requires_session=True,
),
RegisteredService(
    name="novel_food_client",
    service_class=NovelFoodCatalogueClient,
    capabilities=["eu_data_access"],
    requires_session=False,
),
RegisteredService(
    name="novel_food_repository",
    service_class=NovelFoodRepository,
    capabilities=["regulatory_storage"],
    requires_session=True,
),
RegisteredService(
    name="catalogue_parser",
    service_class=CatalogueParser,
    capabilities=["regulatory_monitoring", "data_parsing"],
    requires_session=False,
),
RegisteredService(
    name="novel_food_change_detector",
    service_class=NovelFoodChangeDetector,
    capabilities=["regulatory_monitoring", "change_detection"],
    requires_session=False,
),
```

### Config Injection Pattern (MUST FOLLOW)

**Source:** [core/config.py], Story 6-1 config.py

```python
@dataclass(frozen=True)
class SpeciesConfig:
    latin_name: str
    common_names: tuple[str, ...] = ()
    is_dawo_product: bool = False

@dataclass(frozen=True)
class NovelFoodMonitorConfig:
    search_url: str = ""
    portal_url: str = ""
    schedule_cron: str = "30 5 * * 0"
    request_delay_seconds: int = 10
    max_retries: int = 3
    timeout_seconds: int = 30
    user_agent: str = "DAWO-ECO-RegulatoryMonitor/1.0"
    species: tuple[SpeciesConfig, ...] = ()
    alert_status_transitions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        errors = []
        if not self.search_url:
            errors.append("search_url is required")
        if not self.species:
            errors.append("At least one species must be configured")
        if errors:
            raise ValueError(f"Invalid config: {'; '.join(errors)}")
```

### SQLAlchemy Model Pattern

**Source:** [core/regulatory/models.py], Story 6-1 patterns

Follow the existing model patterns:
- UUID primary keys with `server_default=func.gen_random_uuid()`
- `created_at` / `updated_at` with `datetime.now(UTC)`
- String enums (store `.value`, not enum objects)
- JSONB NOT needed — all fields are structured
- Indexed columns for query performance
- FK with `ondelete="CASCADE"` from snapshot
- `__tablename__` = plural snake_case
- Use the same MAX length constants pattern

### Schemas Pattern (MUST FOLLOW)

**Source:** [teams/dawo/scanners/health_claims/schemas.py]

```python
@dataclass
class NovelFoodEntryRecord:
    """DTO for a parsed Novel Food Catalogue entry."""
    species_latin: str
    species_common: str = ""
    entry_name: str = ""
    novel_food_status: str = ""
    authorization_status: str = ""
    history_of_consumption: str = ""
    member_state_comments: str = ""
    commission_comments: str = ""
    conditions_of_use: str = ""
    regulation_reference: str = ""
    union_list_entry: str = ""
    source_url: str = ""
    raw_html_hash: str = ""

@dataclass
class CatalogueChangeRecord:
    """DTO for a detected change in the catalogue."""
    species_latin: str
    entry_name: str
    change_type: str  # ChangeType.value
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    severity: str = "low"
```

Reuse `MonitorStatus` and `MonitorResult` from Story 6-1 schemas (import from health_claims or move to shared location if not already).

### Testing Strategy (TDD Required)

**Source:** BMAD workflow requires red-green-refactor cycle

**Mock patterns:**
```python
@pytest.fixture
def sample_json_response():
    """Mock JSON response from backend API."""
    return json.dumps([
        {
            "name": "Hericium erinaceus (Lion's Mane) - fruiting body",
            "novelFoodStatus": "Yes",
            "authorisationStatus": None,
            "historyOfConsumption": "No history of...",
            # ...
        }
    ]).encode("utf-8")

@pytest.fixture
def sample_html_response():
    """Mock HTML response from search page."""
    return b"""<html><body>
    <div class="search-result-item">
        <h3>Hericium erinaceus (Lion's Mane)</h3>
        <span class="status">Novel food</span>
        ...
    </div>
    </body></html>"""

@pytest.fixture
def sample_entry_records():
    """Sample NovelFoodEntryRecord list for testing."""
    return [
        NovelFoodEntryRecord(
            species_latin="Hericium erinaceus",
            species_common="Lion's Mane",
            entry_name="Hericium erinaceus - fruiting body",
            novel_food_status="novel",
            authorization_status="not_authorised",
        ),
        # ...
    ]

@pytest.fixture
def species_config():
    """Test species configuration."""
    return [
        SpeciesConfig(latin_name="Hericium erinaceus", common_names=("Lion's Mane",), is_dawo_product=True),
        SpeciesConfig(latin_name="Inonotus obliquus", common_names=("Chaga",), is_dawo_product=True),
    ]
```

**Target: ~55-65 unit tests + ~5 integration tests**

### Previous Story Learnings (CRITICAL — Apply All)

**Source:** [6-1-eu-health-claims-register-monitor.md#Code-Review-Notes], [docs/pre-submission-checklist.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | All components accept deps via constructor, NEVER load files |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in timestamps |
| Add logging to exception handlers | All exceptions logged before continuing |
| Repository uses `flush()`, pipeline calls `commit()` | Never commit in repository — commit in pipeline orchestrator only |
| Pre-initialize variables before try blocks | Avoid UnboundLocalError (H1 from 6-1 code review) |
| Return count not query-back from save_changes | Don't query back records that caller doesn't use (M1 from 6-1 review) |
| Name variables accurately | `filtered_df` → `annotated_df` pattern (M4 from 6-1 review) |
| Multi-column relevance check | Check all relevant text fields, not just one (L1 from 6-1 review) |
| TDD approach | Write tests first for each task |

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

This story has **NO LLM agent** — it's a web scraping/parsing/diffing pipeline. No LLM tier assignment needed. All components are RegisteredService (not RegisteredAgent).

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], Story 6-1 code review learnings

1. **NEVER load config directly** — Accept via injection (`NovelFoodMonitorConfig`)
2. **NEVER make direct HTTP calls** — Always through `RetryMiddleware`
3. **NEVER use pandas for this story** — Small datasets, use lists of dataclasses
4. **NEVER assume stable entry IDs** — Match by composite key (species_latin + entry_name)
5. **NEVER commit in repository** — Only pipeline calls `commit()`
6. **NEVER swallow exceptions without logging**
7. **NEVER corrupt existing data on parse failure** — Fail gracefully, keep previous snapshot
8. **NEVER use `datetime.utcnow()`** — Use `datetime.now(UTC)`
9. **NEVER add Playwright dependency** unless httpx+BeautifulSoup fails (verify at story start)
10. **NEVER exceed rate limits** — 10 second delay between requests to EU servers

### Pre-Implementation Verification (Run at Story Start)

**Source:** [epic-6-prep.md#Pre-Implementation-Verification-Checklists]

Before coding, manually verify:
- [x]Test `httpx GET https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search?searchText=Hericium` — check if JSON response
- [x]If not JSON, test `httpx GET https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search?searchText=Hericium` — check HTML
- [x]Inspect response HTML structure for CSS selectors or JSON fields
- [x]Check `https://ec.europa.eu/robots.txt` and `https://food.ec.europa.eu/robots.txt`
- [x]Visit catalogue updates page: `https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/updates`
- [x]Verify all 6 target species return results: Hericium erinaceus, Inonotus obliquus, Ganoderma lucidum, Cordyceps militaris, Lentinula edodes, Grifola frondosa

### Project Structure Notes

- Extends `core/regulatory/` models (shared across Epic 6 stories)
- Scanner placed in `teams/dawo/scanners/novel_food/` following architecture conventions
- Config in `config/dawo_novel_food.json` following project naming pattern
- Tests mirror source: `tests/teams/dawo/test_scanners/test_novel_food/`
- Reuses `MonitorStatus`, `MonitorResult` schemas from Story 6-1 (import or extract to shared location)
- Reuses `RegulatoryEventEmitter` singleton from Story 6-1
- No conflicts with Story 6-1 code (separate scanner module, additive model changes)

### References

- [Source: epics.md#Story-6.2] — Original story requirements (FR26)
- [Source: docs/research/eu-novel-food-catalogue-research.md] — EU data source research (access methods, data structure, legal)
- [Source: epic-6-prep.md] — Epic 6 preparation tasks and technical decisions
- [Source: 6-1-eu-health-claims-register-monitor.md] — Previous story patterns, code review learnings
- [Source: teams/dawo/scanners/health_claims/] — Harvester framework patterns to follow
- [Source: teams/dawo/middleware/retry.py] — RetryMiddleware usage patterns
- [Source: core/regulatory/events.py] — RegulatoryEventEmitter to extend and reuse
- [Source: core/regulatory/models.py] — SQLAlchemy model patterns and shared regulatory models
- [Source: core/config.py] — Config loading and injection patterns
- [Source: teams/dawo/team_spec.py] — Registration patterns (RegisteredService)
- [Source: project-context.md] — Critical implementation rules and anti-patterns
- [Source: architecture.md#Project-Structure] — Directory organization
- [Source: docs/pre-submission-checklist.md] — Quality checklist

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- Code review (Amelia, Opus 4.6): Fixed 10 issues (3 HIGH, 3 MEDIUM, 4 LOW)
- H1: Fixed `_CHANGE_EVENT_MAP` key mismatch (`"new_entry"` → `"new"`) in pipeline.py
- H2: Fixed `parse_response` raising on zero results — now returns `[]` per Task 5.9
- H3: Populated `MonitorResult.claim_count` with total entries in pipeline.py
- M2: Added `logger.debug()` for swallowed JSON parse exceptions in parser.py
- M3: Added `"modified"` mapping to `_CHANGE_EVENT_MAP` in pipeline.py
- L1: Added comment for unused `portal_url` config field
- L2: Fixed type hint `BeautifulSoup` → `Tag` on `_extract_field` in parser.py
- L3: Removed unused `datetime, UTC` import from schemas.py

### File List

**Core Regulatory (extended)**
- `core/regulatory/models.py` — Added NovelFoodEntry, NovelFoodSnapshot, NovelFoodChange models, NovelFoodStatus/AuthorizationStatus enums
- `core/regulatory/events.py` — Added NOVEL_FOOD_* event types to RegulatoryEventType enum
- `core/regulatory/__init__.py` — Updated exports with all Novel Food types

**Scanner Module (new)**
- `teams/dawo/scanners/novel_food/__init__.py` — Package exports
- `teams/dawo/scanners/novel_food/config.py` — NovelFoodMonitorConfig, SpeciesConfig, build_novel_food_config
- `teams/dawo/scanners/novel_food/client.py` — NovelFoodCatalogueClient with RetryMiddleware
- `teams/dawo/scanners/novel_food/parser.py` — CatalogueParser (JSON/HTML), CatalogueParseError
- `teams/dawo/scanners/novel_food/change_detector.py` — NovelFoodChangeDetector with severity mapping
- `teams/dawo/scanners/novel_food/repository.py` — NovelFoodRepository (CRUD, batch insert)
- `teams/dawo/scanners/novel_food/pipeline.py` — NovelFoodMonitorPipeline orchestrator
- `teams/dawo/scanners/novel_food/schemas.py` — NovelFoodEntryRecord, CatalogueChangeRecord DTOs

**Config**
- `config/dawo_novel_food.json` — Monitor config + 6 species

**Migration**
- `migrations/versions/2026_02_13_002_create_novel_food_tables.py` — Novel food tables + indexes

**Registration**
- `teams/dawo/team_spec.py` — 5 RegisteredService entries for Novel Food

**Unit Tests**
- `tests/teams/dawo/test_scanners/test_novel_food/__init__.py`
- `tests/teams/dawo/test_scanners/test_novel_food/conftest.py` — Shared fixtures
- `tests/teams/dawo/test_scanners/test_novel_food/test_parser.py`
- `tests/teams/dawo/test_scanners/test_novel_food/test_change_detector.py`
- `tests/teams/dawo/test_scanners/test_novel_food/test_client.py`
- `tests/teams/dawo/test_scanners/test_novel_food/test_repository.py`
- `tests/teams/dawo/test_scanners/test_novel_food/test_pipeline.py`
- `tests/teams/dawo/test_scanners/test_novel_food/test_config.py`
- `tests/teams/dawo/test_scanners/test_novel_food/test_events.py`
- `tests/teams/dawo/test_scanners/test_novel_food/test_models.py`

**Integration Tests**
- `tests/integration/test_novel_food_integration.py`
