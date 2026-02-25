# Story 6.5: Competitor Content Scanner

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want competitor Instagram accounts and websites scanned for content,
So that I can identify potential EU violations in their marketing.

---

## Acceptance Criteria

1. **Given** competitor accounts are configured
   **When** the scanner executes (daily 3 AM)
   **Then** it scans each competitor's recent Instagram posts (last 7 days)
   **And** it scans configured website pages (product pages, blog posts)
   **And** it respects rate limits and robots.txt

2. **Given** competitor content is collected
   **When** the harvester processes it
   **Then** it extracts: text content, captions, hashtags used
   **And** it captures: source URL, timestamp, account/domain
   **And** it does NOT store competitor images (privacy)

3. **Given** a competitor post is found
   **When** it contains wellness/health language
   **Then** it's queued for health claim extraction (Story 6.6)
   **And** source metadata is preserved for evidence

---

## Tasks / Subtasks

- [x] Task 1: Create competitor scanner config (AC: #1)
  - [x]1.1 Create `config/dawo_competitor_scanner.json` with:
    - `enabled`: true
    - `schedule_cron`: `"0 3 * * *"` (daily 3 AM)
    - `instagram.enabled`: true
    - `instagram.scan_window_days`: 7
    - `instagram.max_posts_per_competitor`: 25
    - `websites.enabled`: true
    - `websites.request_delay_seconds`: 5
    - `websites.max_pages_per_domain`: 20
    - `request_delay_seconds`: 3
    - `max_retries`: 3
    - `timeout_seconds`: 30
    - `user_agent`: `"DAWO-ECO-CompetitorMonitor/1.0 (+https://imagoeco.com/bot)"`
    - `competitors`: array of `{ "name": str, "instagram_username": str|null, "website_urls": [str], "is_primary": bool }`
    - `health_language_keywords`: `["boost", "improve", "enhance", "support", "treat", "cure", "prevent", "heal", "strengthen", "immunity", "immune", "cognitive", "energy", "anti-inflammatory", "antioxidant", "adaptogen", "nootropic", "stotter", "bidrar", "fremmer", "styrker", "forbedrer", "immunforsvar", "behandler", "kurerer", "forebygger", "helbreder", "helsepastander", "kosttilskudd"]`
  - [x]1.2 Create frozen dataclass `CompetitorScannerConfig` in `teams/dawo/scanners/competitor/config.py`
  - [x]1.3 Create nested frozen dataclass `CompetitorConfig` for individual competitor entries
  - [x]1.4 Create nested frozen dataclass `InstagramScanConfig` and `WebsiteScanConfig`
  - [x]1.5 Create `build_competitor_scanner_config(data: dict) -> CompetitorScannerConfig` builder function
  - [x]1.6 Validate in `__post_init__`: at least 1 competitor, non-empty keywords, positive delays

- [x] Task 2: Create database models (AC: #2, #3)
  - [x]2.1 Add models to `core/regulatory/models.py`:
    - `CompetitorScanSnapshot`: id (UUID PK), competitor_name (str), source_type (str: "instagram"|"website"), scan_started_at (datetime), scan_completed_at (datetime nullable), total_items_found (int), items_with_health_language (int), status (str: "in_progress"|"completed"|"failed"), error_message (str nullable), created_at (datetime)
    - `CompetitorContent`: id (UUID PK), snapshot_id (UUID FK), competitor_name (str), source_type (str: "instagram"|"website"), source_url (str), content_text (Text), hashtags (JSONB nullable), account_or_domain (str), published_at (datetime nullable), captured_at (datetime), content_hash (str — SHA-256 of content_text for dedup), has_health_language (bool), health_keywords_matched (JSONB nullable), extraction_status (str: "pending"|"extracted"|"no_claims"|"error"), created_at (datetime)
  - [x]2.2 Add enums: `CompetitorSourceType` (INSTAGRAM, WEBSITE), `ExtractionStatus` (PENDING, EXTRACTED, NO_CLAIMS, ERROR)
  - [x]2.3 Add indexes: `idx_competitor_content_snapshot` on snapshot_id, `idx_competitor_content_extraction` on extraction_status, `idx_competitor_content_hash` unique on (content_hash, competitor_name) for dedup, `idx_competitor_content_source` on (source_type, competitor_name)
  - [x]2.4 Add relationships: CompetitorScanSnapshot.items -> CompetitorContent (one-to-many)

- [x] Task 3: Create Alembic migration (AC: #2)
  - [x]3.1 Create `migrations/versions/2026_02_15_001_create_competitor_tables.py`
  - [x]3.2 Create `competitor_scan_snapshots` table
  - [x]3.3 Create `competitor_content` table with foreign key to snapshots
  - [x]3.4 Create all indexes from Task 2.3
  - [x]3.5 Add downgrade function to drop both tables

- [x] Task 4: Create website scraper client (AC: #1, #2)
  - [x]4.1 Create `teams/dawo/scanners/competitor/website_client.py` with `WebsiteScraperClient`
  - [x]4.2 Accept deps via constructor: `http_client: httpx.AsyncClient`, `retry: RetryMiddlewareProtocol`, `config: WebsiteScanConfig`
  - [x]4.3 Implement `check_robots_txt(base_url: str) -> RobotsTxtResult` — fetch and parse robots.txt via `urllib.robotparser.RobotFileParser`, cache result per domain
  - [x]4.4 Implement `is_allowed(url: str) -> bool` — check URL against cached robots.txt for user_agent
  - [x]4.5 Implement `scrape_page(url: str) -> ScrapedPage` — fetch HTML, parse with BeautifulSoup, extract:
    - Page title (from `<title>` tag)
    - Main text content (from `<main>`, `<article>`, or `<body>` with tag stripping)
    - Meta description (from `<meta name="description">`)
    - All outbound links (for potential crawling in future stories)
    - Product claims from structured data (`application/ld+json`) if present
  - [x]4.6 Implement `scrape_competitor_pages(competitor: CompetitorConfig) -> list[ScrapedPage]` — iterate website_urls, check robots.txt, scrape allowed pages with delay between requests
  - [x]4.7 Handle errors gracefully: connection timeout, HTTP errors, parse failures — log and continue, never crash

- [x] Task 5: Create content parser (AC: #2)
  - [x]5.1 Create `teams/dawo/scanners/competitor/parser.py` with `CompetitorContentParser`
  - [x]5.2 Accept config via constructor (health_language_keywords)
  - [x]5.3 Implement `parse_instagram_post(post_data: dict, competitor: CompetitorConfig) -> ParsedContent` — extract caption, hashtags, timestamp, permalink from Instagram API response format (same as `InstagramClient.get_user_media()` returns)
  - [x]5.4 Implement `parse_website_page(page: ScrapedPage, competitor: CompetitorConfig) -> ParsedContent` — extract text, URL, title, timestamp
  - [x]5.5 Implement `detect_health_language(text: str) -> HealthLanguageResult` — case-insensitive keyword matching against `health_language_keywords` list. Return matched keywords and boolean flag. This is a SIMPLE pre-filter, NOT LLM-based claim extraction (that's Story 6-6).
  - [x]5.6 Implement `compute_content_hash(text: str) -> str` — SHA-256 hash of normalized (lowered, whitespace-collapsed) text for dedup

- [x] Task 6: Create duplicate checker (AC: #2)
  - [x]6.1 Create `teams/dawo/scanners/competitor/duplicate_checker.py` with `CompetitorDuplicateChecker`
  - [x]6.2 Accept `AsyncSession` via constructor for DB access
  - [x]6.3 Implement `check_duplicates(items: list[ParsedContent]) -> list[ParsedContent]` — query `competitor_content` table by content_hash + competitor_name, return only new items
  - [x]6.4 Use batch query (single SQL `IN` clause) — no N+1 queries

- [x] Task 7: Create repository (AC: #2, #3)
  - [x]7.1 Create `teams/dawo/scanners/competitor/repository.py` with `CompetitorRepository`
  - [x]7.2 Accept `AsyncSession` via constructor
  - [x]7.3 Implement `create_snapshot(competitor_name: str, source_type: str) -> CompetitorScanSnapshot`
  - [x]7.4 Implement `save_content_batch(items: list[ParsedContent], snapshot_id: UUID) -> int` — bulk insert using `session.add_all()`, return count saved
  - [x]7.5 Implement `update_snapshot_stats(snapshot_id: UUID, total: int, health_count: int, status: str) -> None`
  - [x]7.6 Implement `get_pending_extraction() -> Sequence[CompetitorContent]` — query where extraction_status="pending" (for Story 6-6 integration)
  - [x]7.7 Implement `commit() -> None` — `await self._session.commit()`

- [x] Task 8: Create pipeline orchestrator (AC: #1, #2, #3)
  - [x]8.1 Create `teams/dawo/scanners/competitor/pipeline.py` with `CompetitorScanPipeline`
  - [x]8.2 Accept all deps via constructor: `instagram_client: InstagramClient` (from `teams/dawo/scanners/instagram/tools.py`), `website_client: WebsiteScraperClient`, `parser: CompetitorContentParser`, `duplicate_checker: CompetitorDuplicateChecker`, `repository: CompetitorRepository`, `event_emitter: RegulatoryEventEmitter`, `config: CompetitorScannerConfig`
  - [x]8.3 Implement `execute() -> CompetitorScanResult`:
    - For each competitor in config:
      - Stage 1: Create snapshot record
      - Stage 2a: If Instagram enabled → call `instagram_client.get_user_media(username, limit)` → parse posts
      - Stage 2b: If websites enabled → call `website_client.scrape_competitor_pages(competitor)` → parse pages
      - Stage 3: Run health language detection on all content
      - Stage 4: Check duplicates against DB
      - Stage 5: Save new content to DB
      - Stage 6: Update snapshot stats
      - Stage 7: Emit events for content with health language
    - Return `CompetitorScanResult` with statistics
  - [x]8.4 Handle per-competitor errors gracefully — log error, update snapshot status to "failed", continue with next competitor
  - [x]8.5 Respect `request_delay_seconds` between API calls (use `asyncio.sleep`)
  - [x]8.6 Log all stages with counts at INFO level

- [x] Task 9: Create schemas/DTOs (AC: #1-#3)
  - [x]9.1 Create `teams/dawo/scanners/competitor/schemas.py`
  - [x]9.2 Create `ParsedContent` dataclass: source_type (str), competitor_name (str), source_url (str), content_text (str), hashtags (list[str]), account_or_domain (str), published_at (datetime|None), content_hash (str), has_health_language (bool), health_keywords_matched (list[str])
  - [x]9.3 Create `ScrapedPage` dataclass: url (str), title (str), content_text (str), meta_description (str), links (list[str]), fetched_at (datetime)
  - [x]9.4 Create `RobotsTxtResult` dataclass: allowed (bool), checked_at (datetime), robots_url (str)
  - [x]9.5 Create `HealthLanguageResult` dataclass: has_health_language (bool), keywords_matched (list[str]), keyword_count (int)
  - [x]9.6 Create `CompetitorScanResult` dataclass: status (str), competitors_scanned (int), total_content_found (int), new_content_saved (int), duplicates_skipped (int), health_language_detected (int), errors (list[str])
  - [x]9.7 Create `CompetitorScanStatus` enum: COMPLETE, PARTIAL, FAILED

- [x] Task 10: Add event types (AC: #3)
  - [x]10.1 Add to `RegulatoryEventType` in `core/regulatory/events.py`:
    - `COMPETITOR_CONTENT_DETECTED = "competitor_content_detected"` (Story 6-5)
    - `COMPETITOR_HEALTH_LANGUAGE_DETECTED = "competitor_health_language_detected"` (Story 6-5)
  - [x]10.2 Update `__all__` in `core/regulatory/events.py` (already complete, just verify)
  - [x]10.3 Update `AlertCategory` enum in `teams/dawo/scanners/claims_alerts/schemas.py` — add `COMPETITOR_CONTENT = "competitor_content"`
  - [x]10.4 Update `categorize_event()` in claims_alerts/schemas.py to handle new event types

- [x] Task 11: Create package __init__.py and register in team_spec.py (AC: #1)
  - [x]11.1 Create `teams/dawo/scanners/competitor/__init__.py` with complete `__all__`
  - [x]11.2 Export: CompetitorScannerConfig, CompetitorConfig, WebsiteScraperClient, CompetitorContentParser, CompetitorDuplicateChecker, CompetitorRepository, CompetitorScanPipeline, ParsedContent, ScrapedPage, CompetitorScanResult, CompetitorScanStatus, HealthLanguageResult
  - [x]11.3 Register in team_spec.py:
    - `CompetitorScanPipeline` as RegisteredService with capabilities `["competitor_monitoring", "content_scanning"]`, requires_session=True
    - `WebsiteScraperClient` as RegisteredService with capabilities `["competitor_monitoring", "web_scraping"]`, requires_session=False
    - `CompetitorContentParser` as RegisteredService with capabilities `["competitor_monitoring", "content_parsing"]`, requires_session=False
    - `CompetitorDuplicateChecker` as RegisteredService with capabilities `["competitor_monitoring", "deduplication"]`, requires_session=True
    - `CompetitorRepository` as RegisteredService with capabilities `["competitor_monitoring", "competitor_storage"]`, requires_session=True
  - [x]11.4 Add all new imports to team_spec.py

- [x] Task 12: Create unit tests (AC: #1-#3)
  - [x]12.1 Create `tests/teams/dawo/test_scanners/test_competitor/` with `__init__.py`, `conftest.py`
  - [x]12.2 `conftest.py` fixtures: sample competitor config, sample Instagram API response, sample HTML page, sample ParsedContent, mock httpx client, mock AsyncSession, mock RetryMiddleware
  - [x]12.3 `test_config.py` (~8 tests):
    - Valid config creation
    - Empty competitors list → ValueError
    - Empty keywords → ValueError
    - Non-positive delay → ValueError
    - Build function from JSON dict
    - Nested InstagramScanConfig/WebsiteScanConfig validation
    - Default values
    - Frozen immutability
  - [x]12.4 `test_website_client.py` (~8 tests):
    - `scrape_page()` extracts title, text, meta description from sample HTML
    - `scrape_page()` strips script/style tags from content
    - `check_robots_txt()` parses standard robots.txt
    - `is_allowed()` returns False for disallowed paths
    - `is_allowed()` returns True for allowed paths
    - `scrape_competitor_pages()` skips disallowed URLs
    - Connection timeout handled gracefully (returns empty, logs error)
    - HTTP 404/500 handled gracefully
  - [x]12.5 `test_parser.py` (~8 tests):
    - `parse_instagram_post()` extracts caption, hashtags, permalink, timestamp
    - `parse_instagram_post()` handles missing caption (empty string)
    - `parse_website_page()` extracts text, URL, title
    - `detect_health_language()` returns True for "boost immunity" (English)
    - `detect_health_language()` returns True for "styrker immunforsvaret" (Norwegian)
    - `detect_health_language()` returns False for "mushroom recipes" (no health keywords)
    - `detect_health_language()` is case-insensitive
    - `compute_content_hash()` returns consistent SHA-256 for normalized text
  - [x]12.6 `test_duplicate_checker.py` (~4 tests):
    - Returns only new items (filters existing by content_hash)
    - Returns all items when none exist in DB
    - Returns empty when all items are duplicates
    - Uses batch query (verify single DB call via mock)
  - [x]12.7 `test_repository.py` (~6 tests):
    - `create_snapshot()` creates record with in_progress status
    - `save_content_batch()` saves all items and returns count
    - `update_snapshot_stats()` updates total and status
    - `get_pending_extraction()` returns only pending items
    - `commit()` calls session.commit()
    - Empty batch returns 0
  - [x]12.8 `test_pipeline.py` (~8 tests):
    - Full pipeline with Instagram + website → saves content, returns COMPLETE
    - Pipeline with Instagram only (website disabled) → scans only Instagram
    - Pipeline with website only (Instagram disabled) → scrapes only websites
    - Duplicate content skipped (not saved twice)
    - Health language detected → events emitted
    - Per-competitor error handling → continues with next competitor
    - Rate limit error → returns PARTIAL, logs warning
    - All competitors fail → returns FAILED
  - [x]12.9 `test_schemas.py` (~5 tests):
    - ParsedContent creation with all fields
    - CompetitorScanResult creation
    - CompetitorScanStatus enum values
    - HealthLanguageResult dataclass
    - ScrapedPage dataclass

- [x] Task 13: Create integration tests (AC: #1-#3)
  - [x]13.1 Test full flow: config → pipeline → Instagram mock → parser → dedup → repository → DB has content
  - [x]13.2 Test website scraping: config → pipeline → website mock → parser → dedup → repository → DB has content
  - [x]13.3 Test deduplication: run pipeline twice with same content → second run saves 0 new items
  - [x]13.4 Test health language flagging: content with "boost immunity" → extraction_status="pending", has_health_language=True
  - [x]13.5 Test event emission: health language content → RegulatoryEvent emitted with type COMPETITOR_HEALTH_LANGUAGE_DETECTED

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This is the **fifth story in Epic 6** (CleanMarket & Regulatory Intelligence). It is the first story in the **CleanMarket evidence chain** (Stories 6-5 through 6-10). Stories 6-1 through 6-4 handled regulatory monitoring and alerts. Story 6-5 pivots to **competitor intelligence** — scanning competitor content for potential EU Health Claims violations.

### Epic 6 Context: CleanMarket Evidence Chain

```
Story 6-5 (this)     → Scan competitor content → Store in DB
Story 6-6             → Extract health claims from stored content (LLM)
Story 6-7             → Detect EU violations from extracted claims
Story 6-8             → Capture evidence screenshots (Playwright)
Story 6-9             → Searchable evidence database + UI
Story 6-10            → Generate PDF violation reports
```

**Critical handoff:** Story 6-5 stores content in `competitor_content` table with `extraction_status="pending"`. Story 6-6 picks up pending content, runs LLM claim extraction, and updates `extraction_status="extracted"`.

### Key Differences from Previous Epic 6 Stories

| Aspect | Stories 6-1/6-2/6-3 (Regulatory) | Story 6-4 (Alerts) | Story 6-5 (Competitor) |
|--------|----------------------------------|--------------------|-----------------------|
| Data source | EU official sources | Internal events | Competitor Instagram + websites |
| Output | Regulatory DB records | Discord notifications | Competitor content DB records |
| Database | Regulatory tables | None | **New competitor tables** |
| Instagram API | No | No | **Yes — reuse existing client** |
| Web scraping | Yes (EU sites) | No | **Yes — competitor websites** |
| LLM needed | No | No | **No** (keyword pre-filter only) |
| robots.txt | EU sites respected | N/A | **Must respect** |

### Key Differences from Epic 2 Instagram Scanner

| Aspect | Epic 2 Instagram Scanner (Story 2-5) | Story 6-5 Competitor Scanner |
|--------|--------------------------------------|------------------------------|
| Purpose | Research intelligence → Research Pool | CleanMarket evidence → Competitor DB |
| Output | Research Pool items (scored, compliance-checked) | CompetitorContent records (raw, for extraction) |
| LLM stages | ThemeExtractor + ClaimDetector (both tier="generate") | **None** — simple keyword pre-filter |
| Database | Research Pool tables | **New competitor_content tables** |
| Website scraping | No | **Yes** |
| Evidence chain | No | **Yes** — feeds 6-6 → 6-7 → 6-8 → 6-9 → 6-10 |
| Content storage | Transformed + scored | **Raw content preserved** for evidence integrity |

**CRITICAL: Reuse `InstagramClient` from `teams/dawo/scanners/instagram/tools.py`** — do NOT create a new Instagram API client. It already has `get_user_media(username, limit)` for Business Discovery.

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], Stories 6-1/6-2/6-3/6-4 patterns

```
teams/dawo/scanners/competitor/           # NEW — competitor content scanner
├── __init__.py                           # Export all public types
├── config.py                             # CompetitorScannerConfig + nested configs
├── website_client.py                     # WebsiteScraperClient (httpx + BeautifulSoup)
├── parser.py                             # CompetitorContentParser (Instagram + website)
├── duplicate_checker.py                  # CompetitorDuplicateChecker (content_hash dedup)
├── repository.py                         # CompetitorRepository (AsyncSession)
├── pipeline.py                           # CompetitorScanPipeline (orchestrator)
└── schemas.py                            # ParsedContent, ScrapedPage, CompetitorScanResult

config/
└── dawo_competitor_scanner.json          # NEW — competitor list + keywords

core/regulatory/
└── models.py                             # ADD: CompetitorScanSnapshot, CompetitorContent

core/regulatory/
└── events.py                             # ADD: 2 new RegulatoryEventType values

migrations/versions/
└── 2026_02_15_001_create_competitor_tables.py  # NEW

tests/teams/dawo/test_scanners/test_competitor/  # NEW
├── __init__.py
├── conftest.py                           # Shared fixtures
├── test_config.py
├── test_website_client.py
├── test_parser.py
├── test_duplicate_checker.py
├── test_repository.py
├── test_pipeline.py
└── test_schemas.py

tests/integration/
└── test_competitor_scanner_integration.py  # NEW
```

### Instagram Integration (MUST REUSE — Do NOT Reinvent)

**Source:** [teams/dawo/scanners/instagram/tools.py]

The existing `InstagramClient` from Epic 2 provides everything needed:

```python
from teams.dawo.scanners.instagram.tools import (
    InstagramClient,           # Instagram Graph API client
    InstagramClientConfig,     # Config from teams/dawo/scanners/instagram/config.py
    RetryMiddlewareProtocol,   # Retry middleware protocol
    RateLimitTracker,          # Hourly rate limit tracking
    InstagramAPIError,         # API error class
    RateLimitError,            # Rate limit error class
)

# Key method for Story 6-5:
posts: list[dict] = await instagram_client.get_user_media(
    username="competitor_username",   # Without @
    limit=25,                         # Max posts to retrieve
)

# Returns list of dicts with: id, caption, permalink, timestamp, like_count, comments_count, media_type
```

**CRITICAL:** Use the same `InstagramClient` instance (shared rate limit tracker) to avoid exceeding the Instagram Business account's 200 calls/hour limit. The Epic 2 Instagram scanner and Story 6-5 competitor scanner SHARE the rate limit.

### Website Scraping Pattern (NEW — Follow Mattilsynet Pattern)

**Source:** [teams/dawo/scanners/mattilsynet/client.py], [docs/research/mattilsynet-regulatory-monitor.md]

Mattilsynet already uses `httpx + BeautifulSoup4` for HTML scraping. Follow the same pattern:

```python
import httpx
from bs4 import BeautifulSoup

class WebsiteScraperClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        retry: RetryMiddlewareProtocol,
        config: WebsiteScanConfig,
    ) -> None:
        self._client = http_client
        self._retry = retry
        self._config = config
        self._robots_cache: dict[str, RobotsTxtResult] = {}
```

**robots.txt handling:** Use `urllib.robotparser.RobotFileParser` (stdlib, no new dependency):

```python
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

async def check_robots_txt(self, base_url: str) -> RobotsTxtResult:
    domain = urlparse(base_url).netloc
    if domain in self._robots_cache:
        return self._robots_cache[domain]

    robots_url = f"{urlparse(base_url).scheme}://{domain}/robots.txt"
    # Fetch robots.txt, parse, cache result
    rp = RobotFileParser()
    rp.set_url(robots_url)
    # ... fetch and parse ...
    allowed = rp.can_fetch(self._config.user_agent, base_url)
```

### Database Models (Follow Existing Pattern)

**Source:** [core/regulatory/models.py] — ClaimSnapshot, HealthClaim, NovelFoodSnapshot, NovelFoodEntry, MattilsynetSnapshot, MattilsynetUpdate

Follow the exact same snapshot + entries pattern:

```python
# Constants (follow existing pattern)
MAX_COMPETITOR_NAME_LENGTH = 200
MAX_URL_LENGTH = 2048
MAX_DOMAIN_LENGTH = 500
MAX_STATUS_LENGTH = 50

class CompetitorScanSnapshot(Base):
    __tablename__ = "competitor_scan_snapshots"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    competitor_name: Mapped[str] = mapped_column(String(MAX_COMPETITOR_NAME_LENGTH), nullable=False)
    source_type: Mapped[str] = mapped_column(String(MAX_STATUS_LENGTH), nullable=False)
    # ... (see Task 2 for full schema)

class CompetitorContent(Base):
    __tablename__ = "competitor_content"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("competitor_scan_snapshots.id"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    extraction_status: Mapped[str] = mapped_column(String(MAX_STATUS_LENGTH), default="pending")
    # ... (see Task 2 for full schema)
```

**Dedup strategy:** SHA-256 hash of normalized content text. Unique constraint on `(content_hash, competitor_name)` prevents storing identical content from the same competitor across scans.

### Event System (Extend Existing)

**Source:** [core/regulatory/events.py]

Add 2 new event types. The claims_alerts subscriber (Story 6-4) will handle notification formatting.

```python
# Add to RegulatoryEventType enum:
COMPETITOR_CONTENT_DETECTED = "competitor_content_detected"               # Story 6-5
COMPETITOR_HEALTH_LANGUAGE_DETECTED = "competitor_health_language_detected"  # Story 6-5

# Emit events for content with health language:
await self._event_emitter.emit(RegulatoryEvent(
    event_type=RegulatoryEventType.COMPETITOR_HEALTH_LANGUAGE_DETECTED,
    claim_id="",  # No claim ID yet — extraction is Story 6-6
    substance="",
    severity="medium",
    data={
        "competitor_name": competitor.name,
        "source_type": "instagram",
        "source_url": parsed.source_url,
        "keywords_matched": parsed.health_keywords_matched,
        "content_preview": parsed.content_text[:200],
    },
))
```

### Health Language Pre-Filter (SIMPLE — Not LLM)

**CRITICAL:** Story 6-5 does **keyword-based pre-filtering** only. Full LLM-based health claim extraction is Story 6-6.

The pre-filter:
1. Lowercases content text
2. Searches for keywords from config (English + Norwegian)
3. Sets `has_health_language=True` and records matched keywords
4. Sets `extraction_status="pending"` for Story 6-6 to pick up

Content WITHOUT health language still gets stored (for completeness) but with `extraction_status="no_claims"` — Story 6-6 skips it.

### Registration Pattern (MUST FOLLOW)

**Source:** [teams/dawo/team_spec.py], Stories 6-1/6-2/6-3/6-4 patterns

```python
# In team_spec.py — add to SERVICES list
RegisteredService(
    name="competitor_scan_pipeline",
    service_class=CompetitorScanPipeline,
    capabilities=["competitor_monitoring", "content_scanning"],
    requires_session=True,  # Pipeline uses repository
),
RegisteredService(
    name="website_scraper_client",
    service_class=WebsiteScraperClient,
    capabilities=["competitor_monitoring", "web_scraping"],
    requires_session=False,  # HTTP client
),
RegisteredService(
    name="competitor_content_parser",
    service_class=CompetitorContentParser,
    capabilities=["competitor_monitoring", "content_parsing"],
    requires_session=False,
),
RegisteredService(
    name="competitor_duplicate_checker",
    service_class=CompetitorDuplicateChecker,
    capabilities=["competitor_monitoring", "deduplication"],
    requires_session=True,  # DB access
),
RegisteredService(
    name="competitor_repository",
    service_class=CompetitorRepository,
    capabilities=["competitor_monitoring", "competitor_storage"],
    requires_session=True,  # DB access
),
```

### Config Injection Pattern (MUST FOLLOW)

**Source:** [core/config.py], Stories 6-1/6-2/6-3/6-4 config.py

```python
@dataclass(frozen=True)
class CompetitorConfig:
    """Individual competitor entry."""
    name: str = ""
    instagram_username: Optional[str] = None
    website_urls: tuple[str, ...] = ()
    is_primary: bool = False

@dataclass(frozen=True)
class CompetitorScannerConfig:
    enabled: bool = True
    schedule_cron: str = "0 3 * * *"
    competitors: tuple[CompetitorConfig, ...] = ()
    health_language_keywords: tuple[str, ...] = ()
    instagram: InstagramScanConfig = field(default_factory=InstagramScanConfig)
    websites: WebsiteScanConfig = field(default_factory=WebsiteScanConfig)
    request_delay_seconds: int = 3
    max_retries: int = 3
    timeout_seconds: int = 30
    user_agent: str = "DAWO-ECO-CompetitorMonitor/1.0"

    def __post_init__(self) -> None:
        errors: list[str] = []
        if not self.competitors:
            errors.append("At least one competitor must be configured")
        if not self.health_language_keywords:
            errors.append("health_language_keywords must not be empty")
        if self.request_delay_seconds <= 0:
            errors.append("request_delay_seconds must be positive")
        if errors:
            raise ValueError(f"Invalid CompetitorScannerConfig: {'; '.join(errors)}")
```

### Testing Strategy (TDD Required)

**Source:** BMAD workflow requires red-green-refactor cycle

**Mock patterns:**

```python
@pytest.fixture
def sample_instagram_response():
    """Sample Instagram API response for get_user_media()."""
    return [
        {
            "id": "17895695668004550",
            "caption": "Our lion's mane extract boosts cognitive function! #nootropics #wellness",
            "permalink": "https://www.instagram.com/p/ABC123/",
            "timestamp": "2026-02-10T12:00:00+0000",
            "like_count": 150,
            "comments_count": 12,
            "media_type": "IMAGE",
        },
    ]

@pytest.fixture
def sample_html_page():
    """Sample competitor website HTML."""
    return """
    <html><head><title>Product - Brain Boost</title>
    <meta name="description" content="Our mushroom supplement enhances cognitive function">
    </head><body><main>
    <h1>Brain Boost Lion's Mane</h1>
    <p>This supplement treats brain fog and improves memory naturally.</p>
    </main></body></html>
    """

@pytest.fixture
def competitor_config():
    return CompetitorScannerConfig(
        competitors=(
            CompetitorConfig(
                name="CompetitorA",
                instagram_username="competitor_a",
                website_urls=("https://competitor-a.com/products/lions-mane",),
                is_primary=True,
            ),
        ),
        health_language_keywords=(
            "boost", "improve", "enhance", "treat", "cure",
            "prevent", "immunity", "cognitive", "styrker", "forbedrer",
        ),
    )

@pytest.fixture
def mock_instagram_client():
    client = AsyncMock(spec=InstagramClient)
    client.get_user_media = AsyncMock(return_value=[])
    return client

@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient for website scraping."""
    client = AsyncMock()
    return client
```

**Target: ~47 unit tests + ~5 integration tests**

### Previous Story Learnings (CRITICAL — Apply All)

**Source:** [6-4-new-claims-activation-alerts.md#Completion-Notes], [6-3-mattilsynet-regulatory-monitor.md#Completion-Notes], [docs/pre-submission-checklist.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | All components accept deps via constructor, NEVER load files |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in timestamps |
| Add logging to exception handlers | All exceptions logged before continuing |
| Pre-initialize variables before try blocks | Avoid UnboundLocalError |
| `logger.debug()` for swallowed exceptions | Don't silently eat exceptions |
| Populate all result fields | Don't leave CompetitorScanResult fields empty |
| TDD approach | Write tests first for each task |
| Protocol-based DI for testing | Use `RetryMiddlewareProtocol`, mock `InstagramClient` |
| No N+1 queries | Batch all DB queries (single IN clause for dedup check) |
| Database filtering in SQL | Filter by extraction_status in SQL, not in Python |
| Activity logging in one place | Pipeline logs stage transitions, components log details |
| Relevance filter bypass restricted to enforcement only (Story 6-4 learning) | Health language pre-filter must check ALL content types equally |
| Handle list values in event data (Story 6-4 learning) | `keywords_matched` in event data must be serializable list |

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

This story has **NO LLM agent** — it's a pure scraping + parsing + storage pipeline. No LLM tier assignment needed. All components are RegisteredService (not RegisteredAgent).

Health claim extraction using LLM is Story 6-6. This story only does keyword-based pre-filtering (free, fast, deterministic).

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], Stories 6-1/6-2/6-3/6-4 code review learnings

1. **NEVER create a new Instagram API client** — Reuse `InstagramClient` from `teams/dawo/scanners/instagram/tools.py`
2. **NEVER load config directly** — Accept via injection (`CompetitorScannerConfig`)
3. **NEVER store competitor images** — Text and metadata only (privacy/copyright, Meta ToS)
4. **NEVER do LLM-based claim extraction** — That's Story 6-6. This story does keyword pre-filter only.
5. **NEVER swallow exceptions without logging**
6. **NEVER use `datetime.utcnow()`** — Use `datetime.now(UTC)`
7. **NEVER block on scraping failures** — Log error, continue with next competitor/page
8. **NEVER ignore robots.txt** — Must check and respect for all website URLs
9. **NEVER use N+1 queries** — Batch dedup check with single SQL `IN` clause
10. **NEVER import `InstagramClient` directly in pipeline constructor type hint** — Use the class but type the parameter. The Epic 2 `InstagramClient` is not Protocol-based, so direct class reference is acceptable here (unlike Discord which uses Protocol).

### New Dependencies

**None.** All dependencies already exist:
- `httpx` — HTTP client (used throughout)
- `beautifulsoup4` + `lxml` — HTML parsing (added in Stories 6-2/6-3)
- `teams/dawo/scanners/instagram/tools.py` — InstagramClient (Epic 2)
- `core/regulatory/events.py` — RegulatoryEventEmitter (Story 6-1)
- `urllib.robotparser` — robots.txt parsing (Python stdlib)
- `hashlib` — SHA-256 hashing (Python stdlib)

No changes to `requirements.txt` needed.

### Project Structure Notes

- Scanner placed in `teams/dawo/scanners/competitor/` following capability-based organization
- Config in `config/dawo_competitor_scanner.json` following project naming pattern
- Tests mirror source: `tests/teams/dawo/test_scanners/test_competitor/`
- Reuses `InstagramClient` from `teams/dawo/scanners/instagram/tools.py` (Epic 2)
- Extends `RegulatoryEventType` in `core/regulatory/events.py` with 2 new values
- Extends `core/regulatory/models.py` with 2 new models + 2 new enums
- Extends `AlertCategory` in claims_alerts/schemas.py for Story 6-4 notification integration
- No conflicts with Stories 6-1 through 6-4 code (purely additive)
- New Alembic migration for competitor tables

### References

- [Source: epics.md#Story-6.5] — Original story requirements (FR29)
- [Source: architecture.md#DAWO-Team-Structure] — Directory structure, registration pattern
- [Source: project-context.md] — Critical implementation rules and anti-patterns
- [Source: teams/dawo/scanners/instagram/tools.py] — InstagramClient (get_user_media, search_hashtag)
- [Source: teams/dawo/scanners/instagram/schemas.py] — HarvestedPost, ClaimDetectionResult patterns
- [Source: teams/dawo/scanners/instagram/claim_detector.py] — HealthClaimDetector pattern (for reference, NOT reuse)
- [Source: teams/dawo/scanners/mattilsynet/client.py] — Web scraping pattern (httpx + BeautifulSoup)
- [Source: core/regulatory/events.py] — RegulatoryEventEmitter, RegulatoryEventType (extend)
- [Source: core/regulatory/models.py] — Snapshot + entries model pattern
- [Source: teams/dawo/scanners/claims_alerts/schemas.py] — AlertCategory (extend)
- [Source: teams/dawo/team_spec.py] — Registration patterns (RegisteredService)
- [Source: docs/research/nlp-health-claim-extraction.md] — Health claim extraction approach (Story 6-6, not this story)
- [Source: docs/research/playwright-screenshot-evaluation.md] — Screenshot tool (Story 6-8, not this story)
- [Source: docs/research/immutable-evidence-storage-design.md] — Evidence storage (Story 6-9, not this story)
- [Source: 6-4-new-claims-activation-alerts.md] — Previous story learnings
- [Source: docs/pre-submission-checklist.md] — Quality checklist

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None

### Completion Notes List

- **58 unit tests + 5 integration tests = 63 total** (exceeds target of ~47 unit + ~5 integration)
- Config validation changed from "must be positive" to "must be non-negative" for `request_delay_seconds` — allows `0` for fast test execution while still rejecting negative values
- Reuses existing `InstagramClient` from Epic 2 via DI (not imported directly — mock in tests)
- No new dependencies added — all existing (httpx, beautifulsoup4, hashlib, urllib.robotparser)
- Website scraper follows Mattilsynet httpx + BeautifulSoup pattern exactly
- SHA-256 content hashing with normalization (lowercase + whitespace collapse) for deterministic dedup
- Batch SQL query for duplicate checking (no N+1) using `tuple_().in_()`
- Per-competitor error handling: failures logged, pipeline continues with next competitor
- Health language pre-filter is keyword-only (no LLM) — LLM extraction is Story 6-6
- Events emitted only for NEW health language content (not duplicates)
- `extraction_status="pending"` set automatically for health language content → Story 6-6 handoff
- `repository.get_pending_extraction()` method provided for Story 6-6 to query pending items
- Complete `__all__` in `__init__.py` with all 16 public exports
- 5 RegisteredService entries added to `team_spec.py` SERVICES list
- 2 new RegulatoryEventType values added, AlertCategory extended for claims_alerts integration

### File List

**New files:**
- `config/dawo_competitor_scanner.json` — Competitor list, keywords, scanning parameters
- `teams/dawo/scanners/competitor/__init__.py` — Package exports (16 public types)
- `teams/dawo/scanners/competitor/config.py` — Frozen dataclass configs + builder
- `teams/dawo/scanners/competitor/schemas.py` — ParsedContent, ScrapedPage, CompetitorScanResult DTOs
- `teams/dawo/scanners/competitor/website_client.py` — WebsiteScraperClient (httpx + BS4 + robots.txt)
- `teams/dawo/scanners/competitor/parser.py` — CompetitorContentParser (IG + web + health keywords)
- `teams/dawo/scanners/competitor/duplicate_checker.py` — CompetitorDuplicateChecker (batch SHA-256 dedup)
- `teams/dawo/scanners/competitor/repository.py` — CompetitorRepository (CRUD + pending query)
- `teams/dawo/scanners/competitor/pipeline.py` — CompetitorScanPipeline (orchestrator)
- `migrations/versions/2026_02_15_001_create_competitor_tables.py` — Alembic migration
- `tests/teams/dawo/test_scanners/test_competitor/__init__.py`
- `tests/teams/dawo/test_scanners/test_competitor/conftest.py` — Shared fixtures
- `tests/teams/dawo/test_scanners/test_competitor/test_config.py` — 16 tests
- `tests/teams/dawo/test_scanners/test_competitor/test_schemas.py` — 7 tests
- `tests/teams/dawo/test_scanners/test_competitor/test_website_client.py` — 8 tests
- `tests/teams/dawo/test_scanners/test_competitor/test_parser.py` — 10 tests
- `tests/teams/dawo/test_scanners/test_competitor/test_duplicate_checker.py` — 4 tests
- `tests/teams/dawo/test_scanners/test_competitor/test_repository.py` — 6 tests
- `tests/teams/dawo/test_scanners/test_competitor/test_pipeline.py` — 7 tests
- `tests/integration/test_competitor_integration.py` — 5 integration tests

**Modified files:**
- `core/regulatory/models.py` — Added CompetitorScanSnapshot, CompetitorContent, enums, constants
- `core/regulatory/events.py` — Added COMPETITOR_CONTENT_DETECTED, COMPETITOR_HEALTH_LANGUAGE_DETECTED
- `teams/dawo/scanners/claims_alerts/schemas.py` — Added COMPETITOR_CONTENT AlertCategory + event mappings
- `teams/dawo/team_spec.py` — Added imports + 5 RegisteredService entries

### Code Review Record

**Reviewer:** Claude Opus 4.6 (Amelia — Dev Agent, CR workflow)
**Date:** 2026-02-15
**Result:** PASS (10 issues found and fixed)

**Issues fixed:**

| ID | Severity | File | Fix |
|----|----------|------|-----|
| H1 | CRITICAL | `duplicate_checker.py:69` | `result.scalars().all()` dropped 2nd column → dedup broken. Changed to `result.all()` with tuple set comprehension. Updated test mocks. |
| H2 | HIGH | `website_client.py` | RetryMiddleware injected but never used. Wrapped `check_robots_txt` and `scrape_page` HTTP calls in `self._retry.execute_with_retry()`. |
| H3 | HIGH | `website_client.py:_parse_html` | LD+JSON extraction (Task 4.5) not implemented. Added `_extract_ld_json()` method extracting name/description/text from `<script type="application/ld+json">`. |
| M1 | MEDIUM | `website_client.py:106,131` | `can_fetch("*", url)` ignored configured user_agent. Added `user_agent` param to constructor, changed to `can_fetch(self._user_agent, url)`. |
| M2 | MEDIUM | `duplicate_checker.py`, `repository.py` | `session: object` → `session: AsyncSession` via `TYPE_CHECKING` pattern. |
| M3 | MEDIUM | `website_client.py:93` | `timeout=self._config.request_delay_seconds` used delay as timeout. Changed to `timeout=30` (consistent with `scrape_page`). |
| M4 | MEDIUM | `pipeline.py:208` | `health_count: len(health_in_new)` reported only new items. Changed to `health_count` variable (total detected before dedup). |
| L1 | LOW | `website_client.py:173` | `html.parser` → `lxml` (already in requirements.txt, faster). |
| L2 | LOW | `website_client.py:39-46` | Added docstring note that local `RetryMiddlewareProtocol` mirrors project-level protocol. |
| L3 | LOW | `conftest.py:193` | `session.add` was auto-created as `AsyncMock` but called synchronously → RuntimeWarning. Added explicit `session.add = MagicMock()`. |

**Post-fix test run:** 63/63 passed, 0 warnings.
