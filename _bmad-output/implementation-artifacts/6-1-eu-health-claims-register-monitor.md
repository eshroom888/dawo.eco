# Story 6.1: EU Health Claims Register Monitor

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want the EU Health Claims Register monitored for changes,
So that I know when new claims are approved that I can use for DAWO products.

---

## Acceptance Criteria

1. **Given** the EU Register monitor is scheduled (weekly Sunday 5 AM)
   **When** it executes
   **Then** it downloads the EU Health Claims Register dataset from the EU Open Data Portal
   **And** it compares current claims against the previously stored snapshot
   **And** it identifies: new approvals, removed claims, modified wording, status changes

2. **Given** a new health claim is approved
   **When** it relates to DAWO product categories (mushrooms, adaptogens, wellness)
   **Then** it is flagged as high priority
   **And** details are stored: claim text, conditions, product categories, approval date

3. **Given** a claim status changes (e.g., "On hold" to "Authorised")
   **When** it relates to configured substance keywords
   **Then** an event is published via the EventBus for downstream consumers (Story 6-4)
   **And** the change record includes: previous status, new status, claim ID, substance

4. **Given** no changes are detected
   **When** the monitor completes
   **Then** it logs successful check with timestamp
   **And** no alerts are triggered
   **And** the snapshot timestamp is updated

5. **Given** the EU Open Data Portal is unavailable
   **When** retry middleware exhausts attempts
   **Then** the scan is marked INCOMPLETE and queued for next cycle
   **And** the previous snapshot remains available

6. **Given** the downloaded dataset has a different format than expected
   **When** parsing fails (wrong delimiter, missing columns, encoding issues)
   **Then** a parse error is logged with details
   **And** the monitor returns INCOMPLETE status without corrupting existing data

---

## Tasks / Subtasks

- [x] Task 1: Create regulatory data models (AC: #1, #2, #3, #4)
  - [x] 1.1 Create `core/regulatory/__init__.py` with `__all__` exports
  - [x] 1.2 Create `core/regulatory/models.py` with SQLAlchemy models:
    - `HealthClaim` (id, claim_id, claim_type, substance, health_relationship, claim_text, conditions_of_use, food_category, status, efsa_opinion, commission_regulation, date_of_entry, last_update, restrictions, is_relevant, relevance_category, created_at, updated_at)
    - `ClaimSnapshot` (id, snapshot_hash, claim_count, relevant_claim_count, source_url, downloaded_at, file_size_bytes, created_at)
    - `ClaimChange` (id, snapshot_id FK, claim_id, change_type enum[NEW, REMOVED, MODIFIED, STATUS_CHANGED], field_changed, old_value, new_value, is_relevant, severity enum[LOW, MEDIUM, HIGH, CRITICAL], created_at)
  - [x] 1.3 Create `ClaimStatus` enum: AUTHORISED, NON_AUTHORISED, ON_HOLD, WITHDRAWN
  - [x] 1.4 Create `ChangeType` enum: NEW, REMOVED, MODIFIED, STATUS_CHANGED
  - [x] 1.5 Create `ChangeSeverity` enum: LOW, MEDIUM, HIGH, CRITICAL
  - [x] 1.6 Add indexes: `idx_health_claims_substance` (substance), `idx_health_claims_status` (status), `idx_claim_changes_snapshot` (snapshot_id), `idx_claim_changes_relevant` (is_relevant, severity)

- [x] Task 2: Create Alembic migration (AC: #1)
  - [x] 2.1 Create migration `2026_02_xx_001_create_regulatory_tables.py`
  - [x] 2.2 Create tables: `health_claims`, `claim_snapshots`, `claim_changes`
  - [x] 2.3 Add all indexes and foreign keys

- [x] Task 3: Create health claims config (AC: #1, #2, #3)
  - [x] 3.1 Create `config/dawo_health_claims.json` with:
    - `monitor.schedule_cron`: `"0 5 * * 0"` (Sunday 5 AM)
    - `monitor.source_url`: EU Open Data Portal dataset page URL
    - `monitor.download_url`: Direct XLS download URL
    - `monitor.request_delay_seconds`: 5
    - `monitor.max_retries`: 3
    - `substances.mushroom`: keyword list (beta-glucan, ganoderma, reishi, etc.)
    - `substances.adaptogen`: keyword list (ashwagandha, rhodiola, etc.)
    - `substances.vitamins_minerals`: keyword list (vitamin d, selenium, etc.)
    - `alert_on_status_change`: list of status transitions to alert on
  - [x] 3.2 Create frozen dataclass `HealthClaimsMonitorConfig` in scanner config.py
  - [x] 3.3 Validate config in `__post_init__` (non-empty keyword lists, valid URL)

- [x] Task 4: Create health claims client (AC: #1, #5, #6)
  - [x] 4.1 Create `teams/dawo/scanners/health_claims/client.py` with `HealthClaimsClient`
  - [x] 4.2 Accept `httpx.AsyncClient` and `RetryMiddleware` via constructor
  - [x] 4.3 Implement `download_register() -> bytes` — downloads XLS from EU Open Data Portal
  - [x] 4.4 Use `RetryMiddleware.execute_with_retry()` for the HTTP request
  - [x] 4.5 Validate response (status code, content-type, non-empty body)
  - [x] 4.6 Create `HealthClaimsClientError` exception class

- [x] Task 5: Create register parser (AC: #1, #6)
  - [x] 5.1 Create `teams/dawo/scanners/health_claims/parser.py` with `RegisterParser`
  - [x] 5.2 Implement `parse(data: bytes) -> pd.DataFrame` — parses XLS/CSV
  - [x] 5.3 Try XLS parse first (`pd.read_excel(engine='openpyxl')`), fall back to CSV (`pd.read_csv(sep=';', encoding='utf-8-sig')`)
  - [x] 5.4 Validate required columns exist: Claim ID, Nutrient/Substance, Status, Claim Text, etc.
  - [x] 5.5 Normalize column names to snake_case
  - [x] 5.6 Parse EU dates (DD/MM/YYYY) with `dayfirst=True`
  - [x] 5.7 Create `ParseError` exception with details about what failed

- [x] Task 6: Create relevance filter (AC: #2)
  - [x] 6.1 Create `teams/dawo/scanners/health_claims/relevance_filter.py` with `RelevanceFilter`
  - [x] 6.2 Accept keyword config via constructor (mushroom, adaptogen, vitamins_minerals lists)
  - [x] 6.3 Implement `filter(df: pd.DataFrame) -> pd.DataFrame` — returns only relevant claims
  - [x] 6.4 Match against substance, claim_text, and conditions_of_use columns (case-insensitive)
  - [x] 6.5 Tag each match with relevance_category: "mushroom", "adaptogen", "vitamin_mineral"
  - [x] 6.6 Return both filtered DataFrame and match statistics

- [x] Task 7: Create change detector (AC: #1, #3)
  - [x] 7.1 Create `teams/dawo/scanners/health_claims/change_detector.py` with `ChangeDetector`
  - [x] 7.2 Implement `detect(previous: pd.DataFrame, current: pd.DataFrame) -> list[ClaimChangeRecord]`
  - [x] 7.3 Detect NEW claims (in current, not in previous — by Claim ID)
  - [x] 7.4 Detect REMOVED claims (in previous, not in current — by Claim ID)
  - [x] 7.5 Detect MODIFIED claims (same Claim ID, different field values)
  - [x] 7.6 Detect STATUS_CHANGED as special case of MODIFIED (with severity escalation)
  - [x] 7.7 Assign severity: STATUS_CHANGED for relevant substances = CRITICAL, new relevant = HIGH, other changes = MEDIUM/LOW
  - [x] 7.8 Use pandas merge/compare (NOT deepdiff on full DataFrame — too slow). Use `df.merge(how='outer', indicator=True)` for set operations, then field comparison on matched rows

- [x] Task 8: Create health claims repository (AC: #1, #2, #3, #4)
  - [x] 8.1 Create `teams/dawo/scanners/health_claims/repository.py` with `HealthClaimsRepository`
  - [x] 8.2 Accept `AsyncSession` via constructor
  - [x] 8.3 Implement `save_snapshot(claims: pd.DataFrame, source_url: str) -> ClaimSnapshot`
  - [x] 8.4 Implement `get_latest_snapshot() -> Optional[ClaimSnapshot]`
  - [x] 8.5 Implement `get_claims_by_snapshot(snapshot_id: UUID) -> Sequence[HealthClaim]`
  - [x] 8.6 Implement `save_changes(changes: list[ClaimChangeRecord], snapshot_id: UUID) -> list[ClaimChange]`
  - [x] 8.7 Implement `get_relevant_claims(snapshot_id: UUID) -> Sequence[HealthClaim]`
  - [x] 8.8 Use batch insert for claims (bulk_save_mappings for performance)

- [x] Task 9: Create monitor pipeline (AC: #1-#6)
  - [x] 9.1 Create `teams/dawo/scanners/health_claims/pipeline.py` with `HealthClaimsMonitorPipeline`
  - [x] 9.2 Accept all dependencies via constructor: client, parser, filter, detector, repository, event_emitter
  - [x] 9.3 Implement `execute() -> MonitorResult`
  - [x] 9.4 Pipeline stages:
    1. Download register (client)
    2. Parse to DataFrame (parser)
    3. Load previous snapshot from DB (repository)
    4. Filter for relevant claims (filter)
    5. Detect changes vs previous (detector)
    6. Save new snapshot + claims (repository)
    7. Save change records (repository)
    8. Publish events for high-severity changes (event_emitter)
  - [x] 9.5 Return `MonitorResult` with: status, claim_count, relevant_count, changes_detected, errors
  - [x] 9.6 Handle first-run (no previous snapshot) — save baseline without change detection

- [x] Task 10: Create event types for regulatory changes (AC: #3)
  - [x] 10.1 Extend `core/publishing/events.py` or create `core/regulatory/events.py`
  - [x] 10.2 Add `RegulatoryEventType` enum: CLAIM_STATUS_CHANGED, NEW_CLAIM_APPROVED, CLAIM_REMOVED, REGISTER_UPDATED
  - [x] 10.3 Add `RegulatoryEvent` dataclass: event_type, claim_id, substance, old_status, new_status, severity, data dict
  - [x] 10.4 Create `RegulatoryEventEmitter` following PublishEventEmitter pattern (pub/sub with asyncio.Queue)

- [x] Task 11: Register in team_spec.py (AC: #1)
  - [x] 11.1 Register `HealthClaimsMonitorPipeline` as `RegisteredService` with capabilities `["regulatory_monitoring", "health_claims"]`
  - [x] 11.2 Register `HealthClaimsClient` as `RegisteredService` with capability `["eu_data_access"]`
  - [x] 11.3 Register `HealthClaimsRepository` as `RegisteredService` with `requires_session=True`
  - [x] 11.4 Add all new imports to scanner `__init__.py` with complete `__all__`

- [x] Task 12: Create unit tests (AC: #1-#6)
  - [x] 12.1 Create `tests/teams/dawo/test_scanners/test_health_claims/` with `__init__.py`, `conftest.py`
  - [x] 12.2 Test `RegisterParser.parse()` with valid XLS/CSV data
  - [x] 12.3 Test `RegisterParser.parse()` with invalid format (wrong columns, bad encoding)
  - [x] 12.4 Test `RelevanceFilter.filter()` matches mushroom keywords
  - [x] 12.5 Test `RelevanceFilter.filter()` matches adaptogen keywords
  - [x] 12.6 Test `RelevanceFilter.filter()` returns empty for irrelevant claims
  - [x] 12.7 Test `RelevanceFilter.filter()` categorizes matches correctly
  - [x] 12.8 Test `ChangeDetector.detect()` identifies NEW claims
  - [x] 12.9 Test `ChangeDetector.detect()` identifies REMOVED claims
  - [x] 12.10 Test `ChangeDetector.detect()` identifies MODIFIED claims
  - [x] 12.11 Test `ChangeDetector.detect()` identifies STATUS_CHANGED with correct severity
  - [x] 12.12 Test `ChangeDetector.detect()` handles empty previous (first run)
  - [x] 12.13 Test `ChangeDetector.detect()` handles no changes (identical DataFrames)
  - [x] 12.14 Test `HealthClaimsClient.download_register()` with mocked httpx
  - [x] 12.15 Test `HealthClaimsClient.download_register()` retry on failure
  - [x] 12.16 Test `HealthClaimsRepository.save_snapshot()` creates snapshot + claims
  - [x] 12.17 Test `HealthClaimsRepository.get_latest_snapshot()` returns most recent
  - [x] 12.18 Test `HealthClaimsRepository.save_changes()` persists change records
  - [x] 12.19 Test `HealthClaimsMonitorPipeline.execute()` full happy path
  - [x] 12.20 Test `HealthClaimsMonitorPipeline.execute()` first run (no previous snapshot)
  - [x] 12.21 Test `HealthClaimsMonitorPipeline.execute()` download failure → INCOMPLETE
  - [x] 12.22 Test `HealthClaimsMonitorPipeline.execute()` parse failure → INCOMPLETE
  - [x] 12.23 Test `HealthClaimsMonitorPipeline.execute()` publishes events for CRITICAL changes
  - [x] 12.24 Test `HealthClaimsMonitorConfig` validation (empty keywords, invalid URL)
  - [x] 12.25 Test `RegulatoryEvent` serialization
  - [x] 12.26 Test all SQLAlchemy models (HealthClaim, ClaimSnapshot, ClaimChange)

- [x] Task 13: Create integration tests (AC: #1-#5)
  - [x] 13.1 Test full pipeline: download mock → parse → filter → detect → save → events
  - [x] 13.2 Test change detection across two sequential runs
  - [x] 13.3 Test relevant claim filtering end-to-end with DB persistence
  - [x] 13.4 Test event emission for status change (On hold → Authorised)
  - [x] 13.5 Test graceful degradation on download failure

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This is the **first story in Epic 6** (CleanMarket & Regulatory Intelligence). It establishes the regulatory monitoring foundation that Stories 6-2 through 6-10 build upon. The models, repository patterns, and event system created here are shared across the entire epic.

### Epic 6 Context

Epic 6 is an **independent domain** from Epic 5 — no direct code dependencies. It introduces regulatory intelligence and competitor monitoring. Story 6-1 is the data foundation: downloading, parsing, storing, and diffing EU health claims data.

**Critical domain knowledge:** Most mushroom/adaptogen health claims are "on hold" (Article 10(3)) since 2012. Detecting ANY change in these statuses is the highest-value capability. For functional mushrooms, NO authorized EU health claims exist — any health claim is unauthorized or prohibited.

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], [epic-6-prep.md]

```
core/regulatory/                          # NEW — shared regulatory models
├── __init__.py                           # Export all public types
├── models.py                             # HealthClaim, ClaimSnapshot, ClaimChange, enums
└── events.py                             # RegulatoryEvent, RegulatoryEventType, RegulatoryEventEmitter

teams/dawo/scanners/health_claims/        # NEW — monitor module
├── __init__.py                           # Export all public types
├── config.py                             # HealthClaimsMonitorConfig (frozen dataclass)
├── client.py                             # HealthClaimsClient (HTTP download + RetryMiddleware)
├── parser.py                             # RegisterParser (XLS/CSV → DataFrame)
├── relevance_filter.py                   # RelevanceFilter (keyword matching)
├── change_detector.py                    # ChangeDetector (DataFrame diff)
├── repository.py                         # HealthClaimsRepository (SQLAlchemy persistence)
├── pipeline.py                           # HealthClaimsMonitorPipeline (orchestrator)
└── schemas.py                            # ClaimChangeRecord, MonitorResult, FilterStats

config/
└── dawo_health_claims.json               # NEW — monitor config + keyword lists

migrations/versions/
└── 2026_02_xx_001_create_regulatory_tables.py  # NEW

tests/teams/dawo/test_scanners/test_health_claims/  # NEW
├── __init__.py
├── conftest.py                           # Fixtures: sample DataFrames, mock client, mock repo
├── test_parser.py
├── test_relevance_filter.py
├── test_change_detector.py
├── test_client.py
├── test_repository.py
├── test_pipeline.py
├── test_config.py
├── test_events.py
└── test_models.py

tests/integration/
└── test_health_claims_integration.py     # NEW
```

### Data Source (CRITICAL — Research Finding)

**Source:** [docs/research/eu-health-claims-register.md]

The EU Health Claims Register is available from the EU Open Data Portal. **Key finding from research:**

- **Primary format is XLS (Excel)**, NOT CSV as originally assumed
- Download URL: `https://ec.europa.eu/food/food-feed-portal/backend/claims/files/EU_Register_on_nutrition_and_health_claims.xls`
- Dataset page: `https://data.europa.eu/data/datasets/eu-register-on-nutrition-and-health-claims`
- **License:** EU Open Data reuse policy (Commission Decision 2011/833/EU) — free to reuse
- **Update frequency:** Irregular, typically quarterly

**Parser must handle both formats:**
```python
# Try XLS first (primary), fall back to CSV
try:
    df = pd.read_excel(BytesIO(data), engine='openpyxl')
except Exception:
    df = pd.read_csv(
        BytesIO(data),
        sep=';',
        encoding='utf-8-sig',
        dayfirst=True,
    )
```

### Pandas Version Note (CRITICAL)

**pandas 2.2.x is specified** in requirements (per epic-6-prep.md). Do NOT upgrade to pandas 3.0 (released Jan 2026) — it has breaking changes:
- String inference changed from `object` to `str` dtype
- Copy-on-Write is now default
- Pin to `pandas>=2.2.0,<3.0.0` in requirements.txt

### New Dependencies (Add to requirements.txt)

```
# Story 6-1: EU Health Claims Monitor
pandas>=2.2.0,<3.0.0
openpyxl>=3.1.0           # XLS parsing (required by pd.read_excel)
deepdiff>=7.0,<9.0.0      # Structured change detection (optional, pandas compare preferred)
```

Note: `beautifulsoup4` and `lxml` already in requirements.txt (from Story 5.2). `httpx` already present.

### Change Detection Strategy

**Use pandas merge/compare, NOT deepdiff on full DataFrame** (deepdiff requires dict conversion and is slow on large datasets):

```python
# Set operations for new/removed claims
merged = current.merge(previous, on='claim_id', how='outer', indicator=True, suffixes=('_curr', '_prev'))
new_claims = merged[merged['_merge'] == 'left_only']
removed_claims = merged[merged['_merge'] == 'right_only']
common = merged[merged['_merge'] == 'both']

# Field-level comparison for modifications
for _, row in common.iterrows():
    for col in TRACKED_COLUMNS:
        if row[f'{col}_curr'] != row[f'{col}_prev']:
            # Record change
```

deepdiff can be used for individual claim comparison if needed, but is optional for this story.

### EventBus Pattern (MUST FOLLOW)

**Source:** [core/publishing/events.py]

Follow the `PublishEventEmitter` pattern exactly:
- Async pub/sub with `asyncio.Queue`
- `emit(event)` method
- `subscribe() -> AsyncGenerator` method
- Singleton via module-level function
- Dataclass events with `to_dict()` method

Create `core/regulatory/events.py` parallel to `core/publishing/events.py`.

### Harvester Framework Adaptation

**Source:** [teams/dawo/scanners/reddit/] and all Epic 2 scanners

Story 6-1 adapts the harvester framework for document monitoring (not social media):

| Epic 2 Stage | Story 6-1 Equivalent | Purpose |
|-------------|---------------------|---------|
| Scanner | HealthClaimsClient | Download register data |
| Harvester | RegisterParser | Parse XLS/CSV to DataFrame |
| Transformer | RelevanceFilter | Filter for relevant substances |
| Validator | ChangeDetector | Detect changes vs previous |
| Publisher | HealthClaimsRepository + EventEmitter | Persist + notify |

The pipeline orchestrator (`HealthClaimsMonitorPipeline`) follows the same pattern as `RedditResearchPipeline`.

### RetryMiddleware Usage (MUST FOLLOW)

**Source:** [teams/dawo/middleware/retry.py], [docs/retry-middleware-patterns.md]

```python
class HealthClaimsClient:
    def __init__(self, http_client: httpx.AsyncClient, retry: RetryMiddleware):
        self._client = http_client
        self._retry = retry

    async def download_register(self) -> bytes:
        async def _download() -> bytes:
            resp = await self._client.get(self._download_url, follow_redirects=True)
            resp.raise_for_status()
            return resp.content

        result = await self._retry.execute_with_retry(
            _download, context="eu_health_claims_download"
        )
        if not result.success:
            raise HealthClaimsClientError(
                f"Download failed after retries: {result.last_error}"
            )
        return result.response
```

### Registration Pattern (MUST FOLLOW)

**Source:** [teams/dawo/team_spec.py]

```python
# In team_spec.py — add to SERVICES list
RegisteredService(
    name="health_claims_monitor",
    service_class=HealthClaimsMonitorPipeline,
    capabilities=["regulatory_monitoring", "health_claims"],
    requires_session=True,
),
RegisteredService(
    name="health_claims_client",
    service_class=HealthClaimsClient,
    capabilities=["eu_data_access"],
    requires_session=False,
),
RegisteredService(
    name="health_claims_repository",
    service_class=HealthClaimsRepository,
    capabilities=["regulatory_storage"],
    requires_session=True,
),
```

### Config Injection Pattern (MUST FOLLOW)

**Source:** [core/config.py], [project-context.md]

```python
@dataclass(frozen=True)
class HealthClaimsMonitorConfig:
    source_url: str
    download_url: str
    request_delay_seconds: int = 5
    max_retries: int = 3
    mushroom_keywords: tuple[str, ...] = ()
    adaptogen_keywords: tuple[str, ...] = ()
    vitamin_mineral_keywords: tuple[str, ...] = ()
    alert_status_transitions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        errors = []
        if not self.download_url:
            errors.append("download_url is required")
        if not self.mushroom_keywords and not self.adaptogen_keywords:
            errors.append("At least one keyword list must be non-empty")
        if errors:
            raise ValueError(f"Invalid config: {'; '.join(errors)}")
```

Load via `core/config.py` `_load_json_config("dawo_health_claims.json")`, inject into pipeline via Team Builder.

### SQLAlchemy Model Pattern

**Source:** [core/leads/models.py]

Follow the Lead model pattern:
- UUID primary keys
- `created_at` / `updated_at` with `datetime.now(UTC)`
- String enums (store `.value`, not enum objects)
- JSONB for flexible metadata fields
- Indexed columns for query performance
- `__tablename__` = plural snake_case

### Testing Strategy (TDD Required)

**Source:** BMAD workflow requires red-green-refactor cycle

**Mock patterns:**
```python
@pytest.fixture
def sample_claims_df():
    """Sample EU Health Claims DataFrame for testing."""
    return pd.DataFrame({
        'claim_id': ['ID-001', 'ID-002', 'ID-003'],
        'substance': ['Beta-glucans', 'Vitamin C', 'Ganoderma lucidum'],
        'status': ['Authorised', 'Authorised', 'On hold'],
        'claim_text': ['Maintenance of normal blood cholesterol', '...', '...'],
        # ... minimal required columns
    })

@pytest.fixture
def mock_health_claims_client():
    client = AsyncMock(spec=HealthClaimsClient)
    client.download_register.return_value = b'<xls data>'
    return client

@pytest.fixture
def mock_retry_middleware():
    retry = AsyncMock(spec=RetryMiddleware)
    retry.execute_with_retry.return_value = RetryResult(
        success=True, response=b'<data>', attempts=1
    )
    return retry
```

**Target: ~60 unit tests + ~5 integration tests**

### Previous Story Learnings (CRITICAL — Apply All)

**Source:** [5-5-lead-pipeline-status-tracking.md#Completion-Notes], [docs/pre-submission-checklist.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | All components accept deps via constructor, NEVER load files |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in timestamps |
| Add logging to exception handlers | All exceptions logged before continuing |
| No N+1 queries | Use batch inserts for claims, eager loading for snapshots |
| Database filtering in SQL | Filter in queries, NOT in Python memory |
| Activity logging in one place | Log pipeline stages once, not per-item |
| TDD approach | Write tests first for each task |

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

This story has **NO LLM agent** — it's a data download/parse/diff pipeline. No LLM tier assignment needed. All components are RegisteredService (not RegisteredAgent).

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER load config directly** — Accept via injection (`HealthClaimsMonitorConfig`)
2. **NEVER make direct HTTP calls** — Always through `RetryMiddleware`
3. **NEVER use deepdiff on full DataFrame** — Use pandas merge/compare (performance)
4. **NEVER store downloaded file permanently** — Parse to DB, keep snapshot hash only
5. **NEVER swallow exceptions without logging**
6. **NEVER corrupt existing data on parse failure** — Fail gracefully, keep previous snapshot
7. **NEVER use `datetime.utcnow()`** — Use `datetime.now(UTC)`

### Pre-Implementation Verification (Run at Story Start)

**Source:** [epic-6-prep.md#Pre-Implementation-Verification-Checklists]

Before coding, manually verify:
- [ ] Visit EU Open Data Portal, confirm dataset exists and note exact download URL
- [ ] Download the XLS and inspect columns, encoding
- [ ] Search register UI for "beta-glucan" and "ganoderma" to confirm relevant results
- [ ] Check robots.txt at ec.europa.eu

### Project Structure Notes

- New `core/regulatory/` module is shared across Epic 6 (Stories 6-1 through 6-10)
- Scanner placed in `teams/dawo/scanners/health_claims/` following architecture conventions
- Config in `config/dawo_health_claims.json` following project naming pattern
- Tests mirror source: `tests/teams/dawo/test_scanners/test_health_claims/`
- No conflicts with existing Epic 5 code (independent domain)

### References

- [Source: epics.md#Story-6.1] — Original story requirements (FR25)
- [Source: docs/research/eu-health-claims-register.md] — EU data source research (download URLs, data format, legal)
- [Source: epic-6-prep.md] — Epic 6 preparation tasks and technical decisions
- [Source: teams/dawo/scanners/reddit/] — Harvester framework patterns to follow
- [Source: teams/dawo/middleware/retry.py] — RetryMiddleware usage patterns
- [Source: core/publishing/events.py] — EventBus pattern to replicate for regulatory events
- [Source: core/leads/models.py] — SQLAlchemy model patterns to follow
- [Source: core/config.py] — Config loading and injection patterns
- [Source: teams/dawo/team_spec.py] — Registration patterns (RegisteredService)
- [Source: project-context.md] — Critical implementation rules and anti-patterns
- [Source: architecture.md#Project-Structure] — Directory organization
- [Source: 5-5-lead-pipeline-status-tracking.md] — Previous story learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- SQLAlchemy `__new__` pattern caused AttributeError in repr tests — fixed by using proper constructors
- `pip` command not found in Windows bash — fixed with `python -m pip`

### Completion Notes List

- All 13 tasks implemented with TDD red-green-refactor cycle
- 148 unit tests + 5 integration tests = 153 total, all passing
- No deepdiff dependency needed — pandas merge/compare handles all change detection
- `core/regulatory/` package created as shared foundation for Epic 6 stories 6-2 through 6-10
- Event system (`RegulatoryEventEmitter`) follows `PublishEventEmitter` pub/sub pattern exactly
- All `__init__.py` files have complete `__all__` exports
- No LLM agents — all components are `RegisteredService` (data pipeline only)
- pandas pinned to `>=2.2.0,<3.0.0` per story requirements

### File List

**New Files Created:**

Core:
- `core/regulatory/__init__.py` — Package exports (models + events)
- `core/regulatory/models.py` — HealthClaim, ClaimSnapshot, ClaimChange SQLAlchemy models + enums
- `core/regulatory/events.py` — RegulatoryEvent, RegulatoryEventType, RegulatoryEventEmitter

Scanner Module:
- `teams/dawo/scanners/health_claims/__init__.py` — Package exports (16 public types)
- `teams/dawo/scanners/health_claims/config.py` — HealthClaimsMonitorConfig frozen dataclass
- `teams/dawo/scanners/health_claims/client.py` — HealthClaimsClient (HTTP + RetryMiddleware)
- `teams/dawo/scanners/health_claims/parser.py` — RegisterParser (XLS/CSV to DataFrame)
- `teams/dawo/scanners/health_claims/relevance_filter.py` — RelevanceFilter (keyword matching)
- `teams/dawo/scanners/health_claims/change_detector.py` — ChangeDetector (pandas merge diff)
- `teams/dawo/scanners/health_claims/repository.py` — HealthClaimsRepository (SQLAlchemy persistence)
- `teams/dawo/scanners/health_claims/pipeline.py` — HealthClaimsMonitorPipeline (orchestrator)
- `teams/dawo/scanners/health_claims/schemas.py` — ClaimChangeRecord, MonitorResult, FilterStats

Config:
- `config/dawo_health_claims.json` — Monitor config + keyword lists

Migration:
- `migrations/versions/2026_02_13_001_create_regulatory_tables.py` — Tables: claim_snapshots, health_claims, claim_changes

Unit Tests:
- `tests/teams/dawo/test_scanners/test_health_claims/__init__.py`
- `tests/teams/dawo/test_scanners/test_health_claims/conftest.py`
- `tests/teams/dawo/test_scanners/test_health_claims/test_models.py` (71 tests)
- `tests/teams/dawo/test_scanners/test_health_claims/test_config.py` (11 tests)
- `tests/teams/dawo/test_scanners/test_health_claims/test_parser.py` (10 tests)
- `tests/teams/dawo/test_scanners/test_health_claims/test_relevance_filter.py` (13 tests)
- `tests/teams/dawo/test_scanners/test_health_claims/test_change_detector.py` (11 tests)
- `tests/teams/dawo/test_scanners/test_health_claims/test_client.py` (4 tests)
- `tests/teams/dawo/test_scanners/test_health_claims/test_repository.py` (7 tests)
- `tests/teams/dawo/test_scanners/test_health_claims/test_pipeline.py` (10 tests)
- `tests/teams/dawo/test_scanners/test_health_claims/test_events.py` (12 tests)

Integration Tests:
- `tests/integration/test_health_claims_integration.py` (5 tests)

**Modified Files:**
- `requirements.txt` — Added pandas>=2.2.0,<3.0.0 and openpyxl>=3.1.0
- `teams/dawo/team_spec.py` — Added 6 RegisteredService entries for health claims components
- `core/publishing/events.py` — Fixed deprecated datetime.utcnow() to datetime.now(UTC)

## Code Review Notes

**Review Date:** 2026-02-13
**Reviewed By:** Amelia (Dev Agent, CR workflow)
**Test Count:** 154 (149 unit + 5 integration) — all passing

### Issues Found & Fixed

| ID | Sev | File | Issue | Fix |
|----|-----|------|-------|-----|
| H1 | HIGH | parser.py | `_try_parse` UnboundLocalError if XLS parses but returns empty df | Pre-initialize `xls_error = None` before try block |
| H2 | HIGH | repository.py | `save_snapshot` and `save_changes` both called `commit()` — partial state on failure | Moved commit to pipeline orchestrator; repository uses `flush()` only |
| M1 | MED | repository.py | `save_changes` queried all changes back from DB after insert; pipeline never used the list | Removed query-back; returns `int` count instead |
| M3 | MED | client.py | `RetryMiddlewareProtocol.execute_with_retry` had no return type | Added `RetryResultProtocol` with typed attributes |
| M4 | MED | pipeline.py | `filtered_df` misleading name (filter returns FULL df with added columns) | Renamed to `annotated_df` |
| L1 | LOW | change_detector.py | `_is_relevant()` only checked substance; RelevanceFilter checks 3 columns | Extended to accept `claim_text` and `conditions_of_use` |
| L2 | LOW | test_parser.py | No test for empty-XLS-then-CSV-fail edge case | Added `test_parse_empty_xls_then_csv_fail_raises` |

### Out-of-Scope Changes Noted (not fixed, tracked for follow-up)
- `requirements.txt` includes additions not in story scope (beautifulsoup4, lxml, ruff)
- `ui/backend/routers/__init__.py` modified (Epic 4/5 debt, not story 6-1)
