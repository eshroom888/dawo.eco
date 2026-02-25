# Story 6.8: Evidence Collection & Screenshots

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want violation evidence collected with screenshots and timestamps,
So that I have legally defensible documentation for regulatory reporting.

---

## Acceptance Criteria

1. **Given** a violation is detected (evidence_status="pending_collection")
   **When** evidence collection runs
   **Then** it captures a screenshot of the source page/post using Playwright
   **And** screenshot includes a visible timestamp banner (system clock overlay via DOM injection)
   **And** screenshot is saved to immutable storage at `evidence/screenshots/{YYYY-MM}/{uuid}.png`

2. **Given** evidence is collected
   **When** it's stored
   **Then** an `Evidence` record is created with:
   - Screenshot file path (relative to project root)
   - Source URL
   - Captured timestamp (ISO 8601, timezone-aware)
   - SHA-256 hash of screenshot bytes (computed BEFORE writing to disk)
   - Screenshot file size in bytes
   - Claim text, category, violation type, severity
   - Competitor name
   - JSONB metadata (engagement metrics, hashtags, page title if available)

3. **Given** an Instagram post is the evidence source
   **When** screenshot is taken
   **Then** it uses the embed URL format `https://www.instagram.com/p/{shortcode}/embed/` (no auth needed)
   **And** captures: post content area, caption, engagement metrics, timestamp, account name

4. **Given** a website page is the evidence source
   **When** screenshot is taken
   **Then** it captures the full page (or viewport if full_page disabled in config)
   **And** viewport is set to 1280x900 (configurable)

5. **Given** evidence is stored
   **When** any modification to content fields is attempted
   **Then** modification is BLOCKED by application-level guard (`ImmutableEvidenceError`)
   **And** a PostgreSQL trigger prevents content field changes (screenshot_hash, claim_text, source_url, screenshot_path)
   **And** an audit log entry records the blocked attempt

6. **Given** evidence collection completes for a violation
   **When** screenshot is successfully captured and stored
   **Then** the violation's `evidence_status` is updated from `pending_collection` to `collected`
   **And** a `RegulatoryEvent` is emitted with type `EVIDENCE_COLLECTED`

7. **Given** a batch of violations needs evidence collection
   **When** the evidence collector runs
   **Then** it processes up to `batch_size` violations per run (default: 20)
   **And** captures are bounded by `asyncio.Semaphore` (max 3 concurrent pages)
   **And** batch result includes: total_processed, collected, failed, skipped

8. **Given** a screenshot capture fails (page timeout, network error)
   **When** error occurs
   **Then** the violation's evidence_status remains `pending_collection` (retry next run)
   **And** error is logged with violation ID and URL
   **And** batch continues with remaining violations

9. **Given** evidence already exists for a violation (evidence record with matching violation_id)
   **When** the collector encounters it
   **Then** it skips the violation (idempotent)
   **And** increments `skipped` counter in batch result

---

## Tasks / Subtasks

- [x] Task 1: Create evidence collection config (AC: #7)
  - [x]1.1 Create `config/dawo_evidence_collection.json` with:
    - `enabled`: true
    - `batch_size`: 20 (max violations per run)
    - `viewport_width`: 1280
    - `viewport_height`: 900
    - `timeout_seconds`: 30 (page load timeout)
    - `max_concurrent_captures`: 3 (semaphore limit)
    - `full_page`: true (capture scrollable page)
    - `screenshot_format`: "png"
    - `storage_base_path`: "evidence/screenshots"
    - `chromium_args`: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    - `instagram_embed_template`: "https://www.instagram.com/p/{shortcode}/embed/"
    - `timestamp_banner_enabled`: true
    - `wait_until`: "networkidle" (Playwright wait strategy)
  - [x]1.2 Create frozen dataclass `EvidenceCollectionConfig` in `teams/dawo/scanners/evidence_collection/config.py`
  - [x]1.3 Create `build_evidence_collection_config(data: dict) -> EvidenceCollectionConfig` builder function
  - [x]1.4 Validate in `__post_init__`: positive batch_size, positive viewport dimensions, positive timeout, max_concurrent 1-10, screenshot_format in ("png", "jpeg"), non-empty storage_base_path

- [x] Task 2: Create database models (AC: #2, #5)
  - [x]2.1 Add to `core/regulatory/models.py`:
    - `Evidence` model (see Dev Notes for full schema)
    - `EvidenceAuditLog` model
  - [x]2.2 `Evidence` fields:
    - `id`: UUID PK (default uuid4)
    - `violation_id`: UUID FK to `competitor_violations.id`, unique (one evidence per violation)
    - `competitor_name`: String(255), indexed
    - `source_url`: Text
    - `source_type`: String(50) — "instagram_post", "website_page"
    - `claim_text`: Text
    - `claim_category`: String(50) — treatment, prevention, enhancement, general_wellness
    - `violation_type`: String(50), indexed — violation, suspect
    - `severity`: String(20), indexed — high, medium, low
    - `regulation_violated`: Text, nullable
    - `detection_reasoning`: Text, nullable
    - `confidence`: Float — 0.0-1.0 (normalized from 0-100)
    - `screenshot_path`: Text (relative path)
    - `screenshot_hash`: String(64) — SHA-256 hex
    - `screenshot_size_bytes`: Integer
    - `captured_at`: DateTime(timezone=True)
    - `created_at`: DateTime(timezone=True), default `datetime.now(UTC)`
    - `evidence_metadata`: JSONB, default dict
  - [x]2.3 `EvidenceAuditLog` fields:
    - `id`: UUID PK
    - `evidence_id`: UUID FK to `evidence.id` (ondelete RESTRICT)
    - `action`: String(50) — "created", "verified", "downloaded", "report_included", "modification_blocked"
    - `actor`: String(100) — "system", "operator", "report_generator"
    - `details`: JSONB, nullable
    - `hash_verified`: Boolean, nullable
    - `created_at`: DateTime(timezone=True), default `datetime.now(UTC)`
  - [x]2.4 Add indexes:
    - `ix_evidence_captured_at` on captured_at
    - `ix_evidence_competitor_date` composite on (competitor_name, captured_at)
    - `ix_evidence_violation_id` unique on violation_id
    - `ix_evidence_violation_type` on violation_type
    - `ix_evidence_severity` on severity
    - `ix_evidence_audit_evidence_id` on evidence_audit_log.evidence_id
  - [x]2.5 Add relationships:
    - `Evidence.audit_logs` -> list[EvidenceAuditLog] (one-to-many)
    - `Evidence.violation` -> CompetitorViolation (many-to-one via violation_id)
    - `CompetitorViolation.evidence` -> Evidence (one-to-one, uselist=False)
  - [x]2.6 Add constants: `MAX_SOURCE_TYPE_LENGTH = 50`, `MAX_AUDIT_ACTION_LENGTH = 50`, `MAX_AUDIT_ACTOR_LENGTH = 100`
  - [x]2.7 Update `__all__` in `core/regulatory/models.py` with Evidence, EvidenceAuditLog, new constants

- [x] Task 3: Create Alembic migration (AC: #2, #5)
  - [x]3.1 Create `migrations/versions/2026_02_16_003_create_evidence_tables.py`
  - [x]3.2 Create `evidence` table with all fields, FK to `competitor_violations.id`
  - [x]3.3 Create `evidence_audit_log` table with FK to `evidence.id` (ondelete RESTRICT)
  - [x]3.4 Create all indexes from Task 2.4
  - [x]3.5 Add unique constraint on `violation_id` (one evidence per violation)
  - [x]3.6 Create immutability trigger function `prevent_evidence_update()`:
    ```sql
    CREATE OR REPLACE FUNCTION prevent_evidence_update()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.screenshot_hash != NEW.screenshot_hash
           OR OLD.claim_text != NEW.claim_text
           OR OLD.source_url != NEW.source_url
           OR OLD.screenshot_path != NEW.screenshot_path THEN
            RAISE EXCEPTION 'Evidence records are immutable';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    ```
  - [x]3.7 Create trigger: `evidence_immutable_guard BEFORE UPDATE ON evidence`
  - [x]3.8 Add downgrade function to drop trigger, function, tables

- [x] Task 4: Create schemas/DTOs (AC: #2, #7, #9)
  - [x]4.1 Create `teams/dawo/scanners/evidence_collection/schemas.py`
  - [x]4.2 Create `CaptureResult` dataclass: screenshot_bytes (bytes), url (str), captured_at (datetime), page_title (str), metadata (dict)
  - [x]4.3 Create `EvidenceCreateDTO` dataclass: violation_id (UUID), competitor_name (str), source_url (str), source_type (str), claim_text (str), claim_category (str), violation_type (str), severity (str), regulation_violated (str|None), detection_reasoning (str|None), confidence (float), screenshot_path (str), screenshot_hash (str), screenshot_size_bytes (int), captured_at (datetime), evidence_metadata (dict)
  - [x]4.4 Create `CollectionBatchResult` dataclass: total_processed (int), collected (int), failed (int), skipped_already_collected (int), errors (list[str])
  - [x]4.5 Create `ImmutableEvidenceError` exception class (subclass of ValueError)

- [x] Task 5: Create ScreenshotService protocol and implementation (AC: #1, #3, #4)
  - [x]5.1 Create `teams/dawo/scanners/evidence_collection/screenshot_service.py`
  - [x]5.2 Define `ScreenshotServiceProtocol` (Protocol, runtime_checkable):
    ```python
    @runtime_checkable
    class ScreenshotServiceProtocol(Protocol):
        async def capture(self, url: str, *, full_page: bool = True,
                         viewport_width: int = 1280,
                         viewport_height: int = 900) -> CaptureResult: ...
        async def close(self) -> None: ...
    ```
  - [x]5.3 Create `PlaywrightScreenshotService` implementing the protocol:
    - Accept `config: EvidenceCollectionConfig` via constructor
    - Manage a single Chromium browser instance (lazy initialization)
    - Use `asyncio.Semaphore(config.max_concurrent_captures)` to bound concurrent pages
    - `async def capture(url, *, full_page, viewport_width, viewport_height) -> CaptureResult`:
      1. Acquire semaphore
      2. Create new page with viewport
      3. Navigate to URL with `wait_until=config.wait_until`, timeout=`config.timeout_seconds * 1000`
      4. If `config.timestamp_banner_enabled`: inject timestamp banner via `page.evaluate()`
      5. Capture screenshot bytes via `page.screenshot(full_page=full_page)`
      6. Extract page title via `page.title()`
      7. Close page in `finally` block
      8. Return `CaptureResult(screenshot_bytes, url, captured_at, page_title, metadata={})`
    - `async def close()`: close browser if initialized
    - Handle `TimeoutError`, `Error` from Playwright — log and re-raise as RuntimeError
  - [x]5.4 Create `_build_instagram_embed_url(source_url: str, template: str) -> str`:
    - Extract shortcode from Instagram URL patterns (`/p/{shortcode}/`, `/reel/{shortcode}/`)
    - Return embed URL for screenshot
    - If URL is not Instagram, return original URL
  - [x]5.5 Create timestamp banner injection JavaScript (see Dev Notes for exact code)

- [x] Task 6: Create evidence storage service (AC: #1, #2)
  - [x]6.1 Create `teams/dawo/scanners/evidence_collection/storage.py` with `EvidenceStorageService`
  - [x]6.2 Accept `config: EvidenceCollectionConfig` via constructor
  - [x]6.3 Implement `async def store_screenshot(screenshot_bytes: bytes, evidence_id: UUID) -> tuple[str, str, int]`:
    1. Compute SHA-256 hash of `screenshot_bytes` BEFORE writing
    2. Build path: `{config.storage_base_path}/{YYYY-MM}/{evidence_id}.png`
    3. Create directory if needed (`Path.mkdir(parents=True, exist_ok=True)`)
    4. Write bytes to file
    5. Set file read-only (`Path.chmod(0o444)`) — **NOTE: skip on Windows (use stat flags or skip gracefully)**
    6. Verify by re-reading and comparing hash
    7. Return `(relative_path, sha256_hash, file_size_bytes)`
  - [x]6.4 Implement `async def verify_integrity(screenshot_path: str, expected_hash: str) -> bool`:
    - Read file bytes, compute SHA-256, compare to expected_hash
    - Return True if match, False if mismatch or file missing

- [x] Task 7: Create evidence repository (AC: #2, #5, #9)
  - [x]7.1 Create `teams/dawo/scanners/evidence_collection/repository.py` with `EvidenceRepository`
  - [x]7.2 Accept `AsyncSession` via constructor
  - [x]7.3 Implement `async def create(dto: EvidenceCreateDTO) -> Evidence`:
    - Create Evidence ORM object from DTO
    - `session.add(evidence)`
    - Create audit log entry: action="created", actor="system"
    - Return Evidence object
  - [x]7.4 Implement `async def get_by_violation_id(violation_id: UUID) -> Evidence | None`
  - [x]7.5 Implement `async def get_collected_violation_ids() -> set[UUID]`:
    - Return set of `violation_id` values that already have evidence records (for idempotency)
  - [x]7.6 Implement `async def update(evidence_id: UUID, **kwargs) -> Never`:
    - ALWAYS raises `ImmutableEvidenceError`
    - Logs audit entry: action="modification_blocked", details=kwargs
  - [x]7.7 Implement `async def verify_integrity(evidence_id: UUID) -> bool`:
    - Load evidence record
    - Delegate to storage service for hash comparison
    - Log audit entry: action="verified", hash_verified=True/False
  - [x]7.8 Implement `async def commit() -> None`: `await self._session.commit()`

- [x] Task 8: Create evidence collector orchestrator (AC: #1-#9)
  - [x]8.1 Create `teams/dawo/scanners/evidence_collection/collector.py` with `EvidenceCollector`
  - [x]8.2 Accept deps via constructor:
    - `violation_repository: ViolationRepository` (Story 6-7, for get_pending_evidence_collection)
    - `evidence_repository: EvidenceRepository` (this story)
    - `screenshot_service: ScreenshotServiceProtocol`
    - `storage_service: EvidenceStorageService`
    - `event_emitter: RegulatoryEventEmitter`
    - `config: EvidenceCollectionConfig`
  - [x]8.3 Implement `async def execute() -> CollectionBatchResult`:
    - **Stage 1: Fetch pending violations** — `violation_repository.get_pending_evidence_collection()` limited to `config.batch_size`
    - **Stage 2: Filter already-collected** — `evidence_repository.get_collected_violation_ids()` and skip violations with existing evidence (idempotent)
    - **Stage 3: Process each violation**:
      a. Determine source_type from source_url (Instagram vs website)
      b. Build capture URL (Instagram embed if applicable)
      c. `screenshot_service.capture(url, full_page=config.full_page, viewport_width=config.viewport_width, viewport_height=config.viewport_height)`
      d. `storage_service.store_screenshot(capture_result.screenshot_bytes, evidence_id)`
      e. Build `EvidenceCreateDTO` with all violation fields + screenshot data
      f. `evidence_repository.create(dto)`
      g. Update violation: `evidence_status = "collected"` on the CompetitorViolation record
      h. Emit `EVIDENCE_COLLECTED` event
    - **Stage 4: Commit** — `evidence_repository.commit()`
    - Return `CollectionBatchResult` with statistics
  - [x]8.4 Handle per-violation errors gracefully — log error with violation ID + URL, skip, continue
  - [x]8.5 Log all stages with counts at INFO level
  - [x]8.6 Implement `_determine_source_type(url: str) -> str`: returns "instagram_post" if URL matches Instagram patterns, else "website_page"
  - [x]8.7 Implement `_build_evidence_metadata(capture_result: CaptureResult, violation: CompetitorViolation) -> dict`: page_title, capture_url (may differ from source_url for embeds), viewport dimensions

- [x] Task 9: Add event type (AC: #6)
  - [x]9.1 Add to `RegulatoryEventType` in `core/regulatory/events.py`:
    - `EVIDENCE_COLLECTED = "evidence_collected"` (Story 6-8)
  - [x]9.2 Update `__all__` in `core/regulatory/events.py`
  - [x]9.3 Update `AlertCategory` enum in `teams/dawo/scanners/claims_alerts/schemas.py`:
    - Add `EVIDENCE_COLLECTION = "evidence_collection"`
  - [x]9.4 Update `categorize_event()` in claims_alerts/schemas.py to handle EVIDENCE_COLLECTED

- [x] Task 10: Create package __init__.py and register in team_spec.py (AC: #1-#9)
  - [x]10.1 Create `teams/dawo/scanners/evidence_collection/__init__.py` with complete `__all__`
  - [x]10.2 Export: EvidenceCollectionConfig, EvidenceCollector, EvidenceRepository, EvidenceStorageService, PlaywrightScreenshotService, ScreenshotServiceProtocol, CaptureResult, EvidenceCreateDTO, CollectionBatchResult, ImmutableEvidenceError
  - [x]10.3 Register in team_spec.py:
    - `EvidenceCollector` as RegisteredAgent with capabilities `["competitor_monitoring", "evidence_collection", "screenshot_capture"]`, tier=TIER_SCAN
    - `PlaywrightScreenshotService` as RegisteredService with capabilities `["competitor_monitoring", "screenshot_capture"]`, requires_session=False
    - `EvidenceStorageService` as RegisteredService with capabilities `["competitor_monitoring", "evidence_storage"]`, requires_session=False
    - `EvidenceRepository` as RegisteredService with capabilities `["competitor_monitoring", "evidence_storage"]`, requires_session=True
  - [x]10.4 Add all new imports to team_spec.py

- [x] Task 11: Add playwright dependency (AC: #1)
  - [x]11.1 Add to `requirements.txt`: `playwright>=1.41.0,<2.0.0`
  - [x]11.2 Document post-install: `playwright install chromium`

- [x] Task 12: Create unit tests (AC: #1-#9)
  - [x]12.1 Create `tests/teams/dawo/test_scanners/test_evidence_collection/` with `__init__.py`, `conftest.py`
  - [x]12.2 `conftest.py` fixtures:
    - `sample_config`: EvidenceCollectionConfig with default values
    - `sample_violation_pending`: CompetitorViolation mock with evidence_status="pending_collection", source_url Instagram
    - `sample_violation_website`: CompetitorViolation mock with website source_url
    - `sample_capture_result`: CaptureResult with minimal valid PNG bytes
    - `mock_session`: AsyncSession mock (`session.add` is sync MagicMock, NOT AsyncMock)
    - `mock_screenshot_service`: ScreenshotServiceProtocol mock
    - `mock_storage_service`: EvidenceStorageService mock
    - `mock_violation_repository`: ViolationRepository mock with get_pending_evidence_collection
    - `mock_evidence_repository`: EvidenceRepository mock
    - `mock_event_emitter`: RegulatoryEventEmitter mock
    - `minimal_png_bytes`: fixture returning minimal valid 1x1 PNG bytes
  - [x]12.3 `test_config.py` (~7 tests):
    - Valid config creation
    - Non-positive batch_size -> ValueError
    - Non-positive viewport dimensions -> ValueError
    - Zero timeout -> ValueError
    - max_concurrent out of range -> ValueError
    - Invalid screenshot_format -> ValueError
    - Build function from JSON dict
    - Frozen immutability
  - [x]12.4 `test_screenshot_service.py` (~8 tests):
    - NOTE: Unit tests mock Playwright entirely. No browser launch.
    - `_build_instagram_embed_url` extracts shortcode from `/p/ABC123/` URL
    - `_build_instagram_embed_url` extracts shortcode from `/reel/ABC123/` URL
    - `_build_instagram_embed_url` passes through non-Instagram URL unchanged
    - `capture()` returns CaptureResult with bytes, url, timestamp, page_title
    - `capture()` applies viewport dimensions
    - `capture()` injects timestamp banner when enabled
    - `capture()` handles timeout gracefully (raises RuntimeError)
    - `close()` closes browser
  - [x]12.5 `test_storage.py` (~6 tests):
    - `store_screenshot()` computes SHA-256 hash before writing
    - `store_screenshot()` creates directory structure `{base}/{YYYY-MM}/{uuid}.png`
    - `store_screenshot()` returns (path, hash, size)
    - `store_screenshot()` verifies hash after write
    - `verify_integrity()` returns True for valid hash
    - `verify_integrity()` returns False for tampered file
    - `verify_integrity()` returns False for missing file
  - [x]12.6 `test_repository.py` (~9 tests):
    - `create()` inserts Evidence record and audit log entry
    - `create()` returns ORM object
    - `get_by_violation_id()` returns evidence if exists
    - `get_by_violation_id()` returns None if not exists
    - `get_collected_violation_ids()` returns correct UUID set
    - `update()` ALWAYS raises ImmutableEvidenceError
    - `update()` logs modification_blocked audit entry
    - `verify_integrity()` delegates to storage service
    - `commit()` calls session.commit()
  - [x]12.7 `test_collector.py` (~12 tests):
    - Full pipeline: pending violations -> capture -> store -> create evidence -> update status -> emit event
    - Idempotency: already-collected violations are skipped
    - Instagram URL -> embed URL conversion before capture
    - Website URL -> passed through unchanged
    - Per-violation error handling: one fails, others continue
    - Batch size limiting: respects config.batch_size
    - `CollectionBatchResult` statistics accurate
    - Empty pending list -> empty batch result, no captures
    - Screenshot capture failure -> violation stays pending_collection
    - Evidence_status updated to "collected" after success
    - EVIDENCE_COLLECTED event emitted for each success
    - `_determine_source_type()` classifies URLs correctly
  - [x]12.8 `test_schemas.py` (~5 tests):
    - CaptureResult creation with all fields
    - EvidenceCreateDTO creation with all fields
    - CollectionBatchResult creation with defaults
    - ImmutableEvidenceError is ValueError subclass
    - EvidenceCreateDTO with None regulation_violated

- [x] Task 13: Create integration tests (AC: #1-#9)
  - [x]13.1 Test full pipeline: pending violation -> screenshot mock -> store to temp dir -> evidence in DB -> status updated
  - [x]13.2 Test idempotency: run collector twice -> second run skips all (0 new evidence)
  - [x]13.3 Test immutability guard: attempt to update evidence content fields -> ImmutableEvidenceError
  - [x]13.4 Test hash integrity: store screenshot, verify hash matches
  - [x]13.5 Test Instagram embed URL: Instagram violation -> embed URL used for capture
  - [x]13.6 Test event emission: evidence collected -> EVIDENCE_COLLECTED event emitted
  - [x]13.7 Test batch with mixed results: some succeed, some fail -> accurate batch result

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This is the **eighth story in Epic 6** (CleanMarket & Regulatory Intelligence). It's the **fourth story in the CleanMarket evidence chain** (Stories 6-5 through 6-10).

### Epic 6 Evidence Chain Position

```
Story 6-5 (done)      -> Scan competitor content -> Store in DB (competitor_content table)
Story 6-6 (done)      -> Extract health claims -> Store claims (extracted_health_claims table)
Story 6-7 (done)      -> Detect EU violations from extracted claims -> Store violations (competitor_violations table)
Story 6-8 (this)      -> Capture evidence screenshots for violations (Playwright) -> Store evidence (evidence table)
Story 6-9             -> Searchable evidence database + UI (reads evidence table)
Story 6-10            -> Generate PDF violation reports (reads evidence for report inclusion)
```

**Critical handoff IN:** Story 6-7 stored violations in `competitor_violations` table with `evidence_status="pending_collection"`. This story reads pending violations via `ViolationRepository.get_pending_evidence_collection()` and captures screenshot evidence.

**Critical handoff OUT:** Story 6-9 will read the `evidence` table for search/filter UI. Story 6-10 will read evidence records for PDF report generation. Both depend on `Evidence` model and `EvidenceRepository.search()` (add in Story 6-9).

### Key Design Decision: Three-Layer Immutability

**Source:** [docs/research/immutable-evidence-storage-design.md]

Evidence must be legally defensible. Three layers enforce immutability:

| Layer | Mechanism | What It Protects |
|-------|-----------|------------------|
| **Application** | `EvidenceRepository.update()` raises `ImmutableEvidenceError` | All update attempts at app level |
| **Database** | PostgreSQL trigger `prevent_evidence_update()` | Content fields: screenshot_hash, claim_text, source_url, screenshot_path |
| **File System** | `chmod 0o444` on screenshot files | Physical screenshot files |

**NOTE on Windows:** `Path.chmod(0o444)` has limited effect on Windows. Use `try/except` and log warning if chmod fails. The DB trigger is the primary guard; file permissions are defense-in-depth for Linux/production.

### Playwright Screenshot Strategy

**Source:** [docs/research/playwright-screenshot-evaluation.md]

**Latest version:** Playwright 1.58.0 (Jan 2026). Pin to `>=1.41.0,<2.0.0` per epic-6-prep.md.

**Architecture:**
```python
@runtime_checkable
class ScreenshotServiceProtocol(Protocol):
    async def capture(self, url: str, *, full_page: bool = True,
                     viewport_width: int = 1280,
                     viewport_height: int = 900) -> CaptureResult: ...
    async def close(self) -> None: ...
```

- `PlaywrightScreenshotService`: Real implementation with Chromium
- Tests use `MockScreenshotService` returning minimal valid PNG bytes (ZERO browser deps in tests)

**Key API patterns:**
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True, args=config.chromium_args)
    context = await browser.new_context(viewport={"width": 1280, "height": 900})
    page = await context.new_page()
    await page.goto(url, wait_until="networkidle", timeout=30000)

    # Inject timestamp banner
    await page.evaluate("""(ts) => {
        const banner = document.createElement('div');
        banner.style.cssText = 'position:fixed; top:0; left:0; right:0; background:rgba(0,0,0,0.88); color:#fff; font-family:monospace; font-size:13px; padding:8px 14px; z-index:2147483647;';
        banner.textContent = 'EVIDENCE CAPTURE: ' + ts + ' | URL: ' + window.location.href;
        document.body.prepend(banner);
    }""", ts_display)

    screenshot_bytes = await page.screenshot(full_page=True)
    await page.close()
```

**Instagram embed URL pattern:**
```python
import re

INSTAGRAM_POST_PATTERN = re.compile(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)")

def _build_instagram_embed_url(source_url: str, template: str) -> str:
    match = INSTAGRAM_POST_PATTERN.search(source_url)
    if match:
        shortcode = match.group(1)
        return template.format(shortcode=shortcode)
    return source_url  # Not Instagram, use as-is
```

### SHA-256 Integrity Hashing

**Source:** [docs/research/immutable-evidence-storage-design.md#Integrity-Hash-Generation]

```python
import hashlib
from pathlib import Path

def store_screenshot(screenshot_bytes: bytes, output_path: Path) -> tuple[str, str, int]:
    """Save screenshot and return (path, sha256_hash, size_bytes)."""
    # 1. Hash BEFORE writing to disk
    sha256_hash = hashlib.sha256(screenshot_bytes).hexdigest()

    # 2. Write to disk
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(screenshot_bytes)

    # 3. Set read-only (best-effort on Windows)
    try:
        output_path.chmod(0o444)
    except OSError:
        logger.warning("Could not set read-only: %s", output_path)

    # 4. Verify by re-reading
    verification_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    if sha256_hash != verification_hash:
        raise RuntimeError(f"Hash mismatch after write for {output_path}")

    return str(output_path), sha256_hash, len(screenshot_bytes)
```

### File Storage Layout

```
evidence/
└── screenshots/
    ├── 2026-02/
    │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.png
    │   └── ...
    └── 2026-03/
        └── ...
```

**Path pattern:** `{config.storage_base_path}/{YYYY-MM}/{evidence_id}.{format}`

### Existing Code to REUSE (Not Reinvent)

| Component | Source | What to Use |
|-----------|--------|-------------|
| `ViolationRepository` | `teams/dawo/scanners/violation_detection/repository.py` | `get_pending_evidence_collection()` returns pending violations |
| `CompetitorViolation` | `core/regulatory/models.py` | ORM model with source_url, competitor_name, evidence_status |
| `EvidenceCollectionStatus` | `core/regulatory/models.py` | PENDING_COLLECTION, COLLECTED, NOT_REQUIRED enum |
| `RegulatoryEventEmitter` | `core/regulatory/events.py` | Event emission for evidence collected |
| `RegulatoryEvent` | `core/regulatory/events.py` | Event dataclass with data dict for metadata |
| `AlertCategory` | `teams/dawo/scanners/claims_alerts/schemas.py` | Extend with EVIDENCE_COLLECTION |

**CRITICAL: Do NOT re-implement ViolationRepository.** Reuse from Story 6-7 via DI. Only create `EvidenceRepository` for the new `evidence` table.

### Updating CompetitorViolation Status

After successfully collecting evidence, update the violation's `evidence_status`:

```python
# In EvidenceCollector.execute():
violation.evidence_status = EvidenceCollectionStatus.COLLECTED.value
# The violation_repository session will commit this with evidence_repository.commit()
# IMPORTANT: Both repositories must share the same AsyncSession for transactional consistency
```

**Transactional integrity:** The EvidenceCollector should receive a single `AsyncSession` that is shared between `violation_repository` and `evidence_repository`. This ensures the violation status update and evidence creation are atomic.

### Event Emission

```python
await self._event_emitter.emit(RegulatoryEvent(
    event_type=RegulatoryEventType.EVIDENCE_COLLECTED,
    claim_id=str(violation.extracted_claim_id),
    severity=violation.severity,
    data={
        "violation_id": str(violation.id),
        "evidence_id": str(evidence.id),
        "competitor_name": violation.competitor_name,
        "source_url": violation.source_url,
        "screenshot_hash": screenshot_hash,
        "screenshot_path": screenshot_path,
    },
))
```

### Minimal Valid PNG for Testing

Tests must NOT launch Playwright. Use minimal valid PNG bytes:

```python
import struct
import zlib

def create_minimal_png() -> bytes:
    """Create a minimal valid 1x1 transparent PNG."""
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8-bit RGB
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc & 0xFFFFFFFF)

    # IDAT chunk (compressed pixel data: filter byte + RGB)
    raw_data = b'\x00\xFF\xFF\xFF'  # No filter + white pixel
    compressed = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b'IDAT' + compressed)
    idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc & 0xFFFFFFFF)

    # IEND chunk
    iend_crc = zlib.crc32(b'IEND')
    iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc & 0xFFFFFFFF)

    return signature + ihdr + idat + iend
```

Or simpler: use a hardcoded minimal PNG bytes constant.

### Registration Pattern (MUST FOLLOW)

**Source:** [teams/dawo/team_spec.py]

```python
# EvidenceCollector is a RegisteredAgent (orchestrates collection pipeline)
RegisteredAgent(
    name="evidence_collector",
    agent_class=EvidenceCollector,
    capabilities=["competitor_monitoring", "evidence_collection", "screenshot_capture"],
    tier=TIER_SCAN,  # No LLM needed — capture + store
),

# Supporting services
RegisteredService(
    name="playwright_screenshot_service",
    service_class=PlaywrightScreenshotService,
    capabilities=["competitor_monitoring", "screenshot_capture"],
    requires_session=False,
),
RegisteredService(
    name="evidence_storage_service",
    service_class=EvidenceStorageService,
    capabilities=["competitor_monitoring", "evidence_storage"],
    requires_session=False,
),
RegisteredService(
    name="evidence_repository",
    service_class=EvidenceRepository,
    capabilities=["competitor_monitoring", "evidence_storage"],
    requires_session=True,
),
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], Stories 6-1 through 6-7 patterns

```
teams/dawo/scanners/evidence_collection/     # NEW
|-- __init__.py                              # Export all public types
|-- config.py                                # EvidenceCollectionConfig
|-- screenshot_service.py                    # Protocol + PlaywrightScreenshotService
|-- storage.py                               # EvidenceStorageService (SHA-256 + file I/O)
|-- collector.py                             # EvidenceCollector (orchestrator)
|-- repository.py                            # EvidenceRepository (AsyncSession, immutability guard)
+-- schemas.py                               # DTOs: CaptureResult, EvidenceCreateDTO, CollectionBatchResult, ImmutableEvidenceError

config/
+-- dawo_evidence_collection.json            # NEW

core/regulatory/
+-- models.py                                # ADD: Evidence, EvidenceAuditLog models + constants
+-- events.py                                # ADD: EVIDENCE_COLLECTED event type

migrations/versions/
+-- 2026_02_16_003_create_evidence_tables.py # NEW (evidence + evidence_audit_log + trigger)

tests/teams/dawo/test_scanners/test_evidence_collection/  # NEW
|-- __init__.py
|-- conftest.py                              # Shared fixtures
|-- test_config.py
|-- test_screenshot_service.py
|-- test_storage.py
|-- test_repository.py
|-- test_collector.py
+-- test_schemas.py

tests/integration/
+-- test_evidence_collection_integration.py  # NEW
```

### Testing Strategy (TDD Required)

**CRITICAL: No Playwright in unit tests.** All unit tests mock the screenshot service via `ScreenshotServiceProtocol`. Integration tests may use a mock or skip browser tests with `@pytest.mark.skipif(no_playwright)`.

**Mock patterns:**

```python
@pytest.fixture
def mock_screenshot_service():
    """Mock ScreenshotServiceProtocol."""
    service = AsyncMock(spec=ScreenshotServiceProtocol)
    service.capture = AsyncMock(return_value=CaptureResult(
        screenshot_bytes=MINIMAL_PNG_BYTES,
        url="https://www.instagram.com/p/ABC123/embed/",
        captured_at=datetime.now(UTC),
        page_title="Instagram Post",
        metadata={},
    ))
    service.close = AsyncMock()
    return service

@pytest.fixture
def sample_violation_pending():
    """CompetitorViolation with evidence_status=pending_collection."""
    v = MagicMock(spec=CompetitorViolation)
    v.id = uuid4()
    v.extracted_claim_id = uuid4()
    v.violation_status = "violation"
    v.severity = "high"
    v.regulation_article = "EC 1924/2006 Art. 10"
    v.violation_type = "unauthorized_treatment_claim"
    v.detection_reasoning = "Treatment claim prohibited"
    v.authorized_claims_checked = 0
    v.nearest_authorized_claim = None
    v.competitor_name = "CompetitorA"
    v.source_url = "https://www.instagram.com/p/ABC123/"
    v.evidence_status = "pending_collection"
    v.detected_at = datetime.now(UTC)
    # Mock the claim relationship for claim_text/category
    claim = MagicMock()
    claim.claim_text = "treats brain fog"
    claim.claim_category = "treatment"
    claim.confidence_score = 92
    v.extracted_claim = claim
    return v
```

**Target: ~47 unit tests + ~7 integration tests = ~54 total**

### Previous Story Learnings (CRITICAL -- Apply All)

**Source:** [6-7-eu-violation-detection.md#Completion-Notes], [docs/pre-submission-checklist.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | All components accept deps via constructor, NEVER load files |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in timestamps |
| `result.scalars().all()` vs `result.all()` | Use correct SQLAlchemy result extraction |
| Pre-initialize variables before try blocks | Avoid UnboundLocalError |
| `logger.debug()` for swallowed exceptions | Don't silently eat exceptions |
| `session.add` is sync in SQLAlchemy | Use `MagicMock()` not `AsyncMock()` for `session.add` in tests |
| No N+1 queries | Batch violation fetching; don't load relationships one-by-one |
| Database filtering in SQL, not Python | Filter by evidence_status in SQL |
| Activity logging in one place | Collector logs stage transitions, services log details |
| Handle list values in event data | All event data values must be JSON-serializable |
| RegisteredAgent vs RegisteredService | EvidenceCollector is RegisteredAgent, services are RegisteredService |
| Shared session for transactional integrity | violation_repository and evidence_repository share AsyncSession |

### New Dependencies

```
# Story 6-8: Evidence screenshots
playwright>=1.41.0,<2.0.0
```

Post-install: `playwright install chromium`

**All other dependencies already exist:** hashlib (stdlib), pathlib (stdlib), asyncio (stdlib), uuid (stdlib), datetime (stdlib).

### Anti-Patterns to AVOID (CRITICAL)

1. **NEVER launch Playwright in unit tests** -- Mock via `ScreenshotServiceProtocol`
2. **NEVER load config directly** -- Accept via injection (`EvidenceCollectionConfig`)
3. **NEVER hardcode model names** -- Use `tier="scan"`, never `model="claude-3-haiku"`
4. **NEVER swallow exceptions without logging** -- Always `logger.debug/error`
5. **NEVER use `datetime.utcnow()`** -- Use `datetime.now(UTC)`
6. **NEVER modify evidence content after creation** -- Enforce via ImmutableEvidenceError + DB trigger
7. **NEVER compute hash AFTER writing to disk** -- Hash raw bytes BEFORE write
8. **NEVER create separate sessions** -- Share AsyncSession between violation_repository and evidence_repository
9. **NEVER skip hash verification after write** -- Re-read and compare
10. **NEVER store absolute paths in DB** -- Use relative paths from project root

### Project Structure Notes

- Collector placed in `teams/dawo/scanners/evidence_collection/` following the CleanMarket evidence chain pattern
- Config in `config/dawo_evidence_collection.json` following project naming convention
- Tests mirror source: `tests/teams/dawo/test_scanners/test_evidence_collection/`
- Reuses `ViolationRepository` from Story 6-7 via DI
- Extends `RegulatoryEventType` in `core/regulatory/events.py` with 1 new value
- Extends `core/regulatory/models.py` with 2 new models (Evidence, EvidenceAuditLog) + constants
- Extends `AlertCategory` in claims_alerts/schemas.py for notification integration
- Adds `playwright>=1.41.0,<2.0.0` to requirements.txt (first new dependency since Epic 6 stories 6-1/6-2)
- New Alembic migration with immutability trigger
- No conflicts with Stories 6-1 through 6-7 code (purely additive)

### References

- [Source: epics.md#Story-6.8] -- Original story requirements
- [Source: architecture.md#DAWO-Team-Structure] -- Directory structure, registration pattern
- [Source: project-context.md] -- Critical implementation rules and anti-patterns
- [Source: epic-6-prep.md] -- Playwright decision, evidence storage design, dependency list
- [Source: docs/research/playwright-screenshot-evaluation.md] -- Playwright API, embed URLs, timestamp overlay, resource requirements
- [Source: docs/research/immutable-evidence-storage-design.md] -- Three-layer immutability, Evidence model, audit log, hash verification
- [Source: core/regulatory/models.py] -- CompetitorViolation, EvidenceCollectionStatus enum
- [Source: core/regulatory/events.py] -- RegulatoryEventEmitter, RegulatoryEventType, RegulatoryEvent
- [Source: teams/dawo/scanners/violation_detection/repository.py] -- ViolationRepository.get_pending_evidence_collection()
- [Source: teams/dawo/team_spec.py] -- Registration patterns (RegisteredAgent, RegisteredService, TIER_SCAN)
- [Source: core/config.py] -- Frozen dataclass config pattern
- [Source: config/dawo_violation_detection.json] -- Config JSON pattern reference
- [Source: 6-7-eu-violation-detection.md] -- Previous story learnings, code review fixes, testing patterns
- [Source: docs/pre-submission-checklist.md] -- Quality checklist
- [Source: teams/dawo/scanners/claims_alerts/schemas.py] -- AlertCategory

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- All 13 tasks implemented following TDD red-green-refactor
- 56 unit tests + 9 integration tests = 65 total tests, all passing
- Three-layer immutability enforced: application (ImmutableEvidenceError), database trigger (prevent_evidence_update), file system (chmod 0o444)
- SHA-256 integrity hashing: hash BEFORE write, verify AFTER write
- Instagram embed URL extraction via regex pattern (supports /p/ and /reel/)
- Timestamp banner injection via JavaScript DOM manipulation
- Protocol-based DI with ScreenshotServiceProtocol (runtime_checkable)
- Batch processing with configurable batch_size (default 20)
- Per-violation error handling: failures don't stop batch
- Idempotency: already-collected violations skipped via get_collected_violation_ids()
- Event emission: EVIDENCE_COLLECTED events emitted for each successful collection
- Windows chmod compatibility: try/except with warning log
- session.add is sync MagicMock in tests (not AsyncMock) — matches SQLAlchemy behavior

### Change Log

| File | Action | Description |
|------|--------|-------------|
| `config/dawo_evidence_collection.json` | Created | JSON config with batch, viewport, timeout, storage settings |
| `teams/dawo/scanners/evidence_collection/__init__.py` | Created | Package init with complete __all__ (11 exports) |
| `teams/dawo/scanners/evidence_collection/config.py` | Created | Frozen dataclass + builder + validation |
| `teams/dawo/scanners/evidence_collection/schemas.py` | Created | CaptureResult, EvidenceCreateDTO, CollectionBatchResult, ImmutableEvidenceError |
| `teams/dawo/scanners/evidence_collection/screenshot_service.py` | Created | Protocol + PlaywrightScreenshotService + _build_instagram_embed_url |
| `teams/dawo/scanners/evidence_collection/storage.py` | Created | EvidenceStorageService with SHA-256 hashing |
| `teams/dawo/scanners/evidence_collection/repository.py` | Created | EvidenceRepository with immutability guard + audit logging |
| `teams/dawo/scanners/evidence_collection/collector.py` | Created | EvidenceCollector 4-stage orchestrator |
| `core/regulatory/models.py` | Modified | Added Evidence, EvidenceAuditLog models + constants + relationships |
| `core/regulatory/events.py` | Modified | Added EVIDENCE_COLLECTED event type |
| `teams/dawo/scanners/claims_alerts/schemas.py` | Modified | Added EVIDENCE_COLLECTION alert category + event mapping |
| `teams/dawo/team_spec.py` | Modified | Registered 1 agent + 3 services |
| `requirements.txt` | Modified | Added playwright>=1.41.0,<2.0.0 |
| `migrations/versions/2026_02_16_003_create_evidence_tables.py` | Created | evidence + evidence_audit_log tables + immutability trigger |
| `tests/teams/dawo/test_scanners/test_evidence_collection/__init__.py` | Created | Test package init |
| `tests/teams/dawo/test_scanners/test_evidence_collection/conftest.py` | Created | Shared fixtures (11 fixtures + MINIMAL_PNG_BYTES) |
| `tests/teams/dawo/test_scanners/test_evidence_collection/test_config.py` | Created | 11 config tests |
| `tests/teams/dawo/test_scanners/test_evidence_collection/test_schemas.py` | Created | 7 schema tests |
| `tests/teams/dawo/test_scanners/test_evidence_collection/test_screenshot_service.py` | Created | 9 screenshot service tests |
| `tests/teams/dawo/test_scanners/test_evidence_collection/test_storage.py` | Created | 7 storage tests |
| `tests/teams/dawo/test_scanners/test_evidence_collection/test_repository.py` | Created | 9 repository tests |
| `tests/teams/dawo/test_scanners/test_evidence_collection/test_collector.py` | Created | 13 collector tests |
| `tests/integration/test_evidence_collection_integration.py` | Created | 9 integration tests |

### File List

- config/dawo_evidence_collection.json
- teams/dawo/scanners/evidence_collection/__init__.py
- teams/dawo/scanners/evidence_collection/config.py
- teams/dawo/scanners/evidence_collection/schemas.py
- teams/dawo/scanners/evidence_collection/screenshot_service.py
- teams/dawo/scanners/evidence_collection/storage.py
- teams/dawo/scanners/evidence_collection/repository.py
- teams/dawo/scanners/evidence_collection/collector.py
- core/regulatory/models.py
- core/regulatory/events.py
- teams/dawo/scanners/claims_alerts/schemas.py
- teams/dawo/team_spec.py
- requirements.txt
- migrations/versions/2026_02_16_003_create_evidence_tables.py
- tests/teams/dawo/test_scanners/test_evidence_collection/__init__.py
- tests/teams/dawo/test_scanners/test_evidence_collection/conftest.py
- tests/teams/dawo/test_scanners/test_evidence_collection/test_config.py
- tests/teams/dawo/test_scanners/test_evidence_collection/test_schemas.py
- tests/teams/dawo/test_scanners/test_evidence_collection/test_screenshot_service.py
- tests/teams/dawo/test_scanners/test_evidence_collection/test_storage.py
- tests/teams/dawo/test_scanners/test_evidence_collection/test_repository.py
- tests/teams/dawo/test_scanners/test_evidence_collection/test_collector.py
- tests/integration/test_evidence_collection_integration.py
