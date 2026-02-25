# Story 7.2: UTM Click-Through Tracking

Status: done

## Story

As an **operator**,
I want click-throughs from posts tracked via UTM parameters with a custom short-link redirect,
so that I can attribute website traffic to specific content and measure which posts drive the most engagement beyond Instagram.

## Acceptance Criteria

1. **Given** content is published with UTM-tagged links **When** users click through to the website **Then** UTM parameters are captured: source, medium, campaign, content **And** clicks are counted and stored by post ID **And** click data includes: timestamp, hashed IP (GDPR), user-agent, device type, referer

2. **Given** UTM tracking is configured **When** a short link is generated for a post **Then** the short link follows format `/l/{code}` where code is `secrets.token_urlsafe(6)` **And** the link redirects (HTTP 307) to the destination URL with UTM params preserved **And** UTM contains: `utm_source=instagram, utm_medium=post, utm_campaign={content_type}, utm_content={post_id}`

3. **Given** click data is collected **When** I query post analytics **Then** I see: total clicks, unique clicks (by IP hash), clicks by day, device breakdown **And** comparison to average CTR across all posts is available **And** queries return in < 500ms for up to 100k click records

4. **Given** the `/l/{code}` endpoint receives a request **When** the short code is valid **Then** redirect completes in < 50ms **And** click is recorded asynchronously (fire-and-forget, does not block redirect) **And** response is HTTP 307 Temporary Redirect

5. **Given** an invalid short code is requested **When** `/l/{code}` is called **Then** HTTP 404 is returned **And** no click is recorded **And** the event is logged at DEBUG level (not error -- expected bot traffic)

6. **Given** short links exist for posts **When** I query the link service **Then** I can look up links by post_id, by code, or list all links with click counts **And** expired links (> attribution window) are still queryable for historical analysis

## Tasks / Subtasks

- [x] Task 1: Database migration and models (AC: #1, #2)
  - [x] 1.1 Create Alembic migration `2026_02_23_001_create_utm_tracking_tables` with two tables:
    - `short_links`: id (UUID PK), code (VARCHAR 12 UNIQUE), destination_url (TEXT), utm_source (VARCHAR 50), utm_medium (VARCHAR 50), utm_campaign (VARCHAR 100), utm_content (VARCHAR 100), post_id (VARCHAR 100 nullable), source_type (VARCHAR 20, default 'instagram'), created_at (TIMESTAMPTZ), expires_at (TIMESTAMPTZ nullable)
    - `link_clicks`: id (UUID PK), short_link_id (UUID FK -> short_links.id), clicked_at (TIMESTAMPTZ), ip_hash (VARCHAR 64), user_agent (TEXT nullable), device_type (VARCHAR 20 nullable), referer (TEXT nullable)
  - [x] 1.2 Add indexes: `idx_short_links_code` (UNIQUE), `idx_short_links_post_id`, `idx_link_clicks_short_link_id`, `idx_link_clicks_clicked_at`
  - [x] 1.3 Create SQLAlchemy async models `ShortLink` and `LinkClick` in `core/analytics/utm_models.py`
  - [x] 1.4 Write tests for models (field validation, relationship, unique constraint on code)

- [x] Task 2: UTM repository (AC: #1, #3, #6)
  - [x] 2.1 Create `UTMRepository` in `core/analytics/utm_repository.py` with async SQLAlchemy
  - [x] 2.2 Methods: `create_short_link(link)`, `get_by_code(code)`, `get_by_post_id(post_id)`, `record_click(click)`, `get_click_stats(short_link_id)`, `get_clicks_by_post(post_id, days_back=30)`
  - [x] 2.3 `get_click_stats` returns: total_clicks, unique_clicks (COUNT DISTINCT ip_hash), clicks_by_day (GROUP BY DATE), device_breakdown (GROUP BY device_type)
  - [x] 2.4 Batch query: `get_clicks_by_post_ids(post_ids: list[str])` -- prevent N+1
  - [x] 2.5 Write tests for all repository methods (mock async session)

- [x] Task 3: Short link service (AC: #2, #6)
  - [x] 3.1 Create `ShortLinkService` in `core/analytics/utm_service.py`
  - [x] 3.2 Constructor injection: `UTMRepository`, `UTMConfig`
  - [x] 3.3 Method `create_short_link(destination_url, utm_params: UTMParams, post_id: str | None, source_type: str) -> ShortLink`
  - [x] 3.4 Short code generation: `secrets.token_urlsafe(6)` with collision retry (max 3 attempts)
  - [x] 3.5 Method `resolve_and_track(code: str, ip: str, user_agent: str | None, referer: str | None) -> str | None` -- returns destination_url or None if not found
  - [x] 3.6 IP hashing: `hashlib.sha256(ip.encode()).hexdigest()` -- NEVER store raw IP
  - [x] 3.7 Device type parsing: basic categorization from user-agent (mobile/desktop/tablet/bot) -- use simple regex, NOT the `user-agents` library (keep zero deps)
  - [x] 3.8 Method `get_post_click_analytics(post_id: str) -> ClickAnalytics` -- aggregated stats
  - [x] 3.9 Write comprehensive tests (10+ tests: creation, collision handling, resolution, tracking, analytics)

- [x] Task 4: Redirect router endpoint (AC: #2, #4, #5)
  - [x] 4.1 Create `ui/backend/routers/redirect.py` with `redirect_router = APIRouter()`
  - [x] 4.2 Endpoint `GET /l/{code}` -- resolves short link, records click, returns 307 redirect
  - [x] 4.3 Click recording is fire-and-forget: use `asyncio.create_task()` so redirect is not blocked
  - [x] 4.4 404 response for unknown codes (no error logging -- expected for bots/scanners)
  - [x] 4.5 Extract client IP from `request.client.host` (consider X-Forwarded-For behind proxy)
  - [x] 4.6 Register router in `ui/backend/routers/__init__.py`
  - [x] 4.7 Write tests for redirect endpoint (mock service, test 307, test 404, test async click tracking)

- [x] Task 5: Click analytics query service (AC: #3)
  - [x] 5.1 Create `ClickAnalyticsService` in `core/analytics/click_analytics.py`
  - [x] 5.2 Constructor injection: `UTMRepository`
  - [x] 5.3 Method `get_post_analytics(post_id: str) -> PostClickAnalytics` -- total, unique, by_day, by_device, ctr (if impressions available from Story 7-1)
  - [x] 5.4 Method `get_average_ctr(days_back: int = 30) -> float` -- average across all posts
  - [x] 5.5 Method `get_comparison(post_id: str) -> ClickComparison` -- post vs average
  - [x] 5.6 Integrate with `MetricsQueryService` (Story 7-1) for impressions-based CTR calculation
  - [x] 5.7 Write tests for analytics computation (mock repository)

- [x] Task 6: Integration with existing UTM generation (AC: #2)
  - [x] 6.1 Extend `integrations/shopify/utm.py`: add `build_short_link_url(base_url: str, code: str) -> str` helper
  - [x] 6.2 Create `core/analytics/utm_integration.py` with `generate_post_short_link(post_id, destination_url, content_type)` -- orchestrates UTMParams + ShortLinkService
  - [x] 6.3 This does NOT modify the caption generator yet -- short link generation is a standalone service that can be called from anywhere
  - [x] 6.4 Write integration tests verifying UTM param flow: generate -> store -> redirect -> track

- [x] Task 7: Configuration (AC: #2, #3)
  - [x] 7.1 Add UTM config to `config/dawo_analytics.json` (extend existing file): `utm_config` section with `short_link_base_url`, `default_attribution_window_days`, `code_length`
  - [x] 7.2 Add `UTMConfig` frozen dataclass to `core/config.py` with fields: `short_link_base_url: str`, `default_attribution_window_days: int = 30`, `code_length: int = 8`
  - [x] 7.3 Wire into existing `_build_analytics_config` or create `_build_utm_config` loader
  - [x] 7.4 Write config validation tests

- [x] Task 8: Registration and exports (AC: all)
  - [x] 8.1 Update `core/analytics/__init__.py` with new exports: ShortLink, LinkClick, UTMRepository, ShortLinkService, ClickAnalyticsService, PostClickAnalytics, ClickComparison
  - [x] 8.2 Register `ShortLinkService` as `RegisteredService` in `teams/dawo/team_spec.py` (no LLM tier -- pure data service)
  - [x] 8.3 Register `ClickAnalyticsService` as `RegisteredService` in `teams/dawo/team_spec.py`
  - [x] 8.4 Register `UTMRepository` as `RegisteredService` in `teams/dawo/team_spec.py`
  - [x] 8.5 Verify all new `__init__.py` files have complete `__all__` exports

## Dev Notes

### Critical Architecture Patterns

**Extend, don't create:**
- UTM generation already exists in two places:
  - `integrations/shopify/utm.py` -- `UTMParams` dataclass, `build_utm_url()`, `get_product_url_with_utm()` (32 tests)
  - `teams/dawo/leads/gmail/utm.py` -- email URL UTM injection (21 tests)
- DO NOT duplicate UTM generation logic. Reuse `UTMParams` from `integrations/shopify/utm.py`
- DO NOT create a new UTM parameter scheme. Existing scheme: `utm_source=instagram, utm_medium=post, utm_campaign={content_type}, utm_content={post_id}`

**Fire-and-forget click tracking:**
- The `/l/{code}` redirect MUST NOT block on database write
- Use `asyncio.create_task(record_click(...))` pattern
- If click recording fails, the redirect still succeeds -- log error, don't raise
- Same pattern as `_schedule_post_metrics` in `core/scheduling/jobs.py` (Story 7-1)

**GDPR compliance (CRITICAL):**
- NEVER store raw IP addresses in `link_clicks` table
- Always hash with SHA-256: `hashlib.sha256(ip.encode()).hexdigest()`
- No cookies, no fingerprinting, no personal data beyond hashed IP
- User-agent is stored for device categorization only (not user tracking)

**Router registration pattern:**
- Follow existing pattern in `ui/backend/routers/__init__.py`
- The redirect router needs a SHORT prefix (or none) since `/l/{code}` must be brief
- Register as `redirect_router` in the `__all__` list
- IMPORTANT: The `/l/{code}` route should be at the app root level, NOT under `/api/` prefix

**RetryMiddleware NOT needed:**
- This story has NO external API calls -- all operations are local database reads/writes
- The redirect endpoint reads from local DB, the click recording writes to local DB
- No need for retry middleware wrapping

### Existing Code to Reuse

| Component | Location | How to Reuse |
|-----------|----------|-------------|
| UTMParams dataclass | `integrations/shopify/utm.py` | Import and use for param construction |
| build_utm_url() | `integrations/shopify/utm.py` | Reuse for destination URL building |
| SQLAlchemy Base | `core/models.py` | Inherit for new models |
| InstagramMediaMetric pattern | `core/analytics/models.py` | Model structure reference (UUID PK, TIMESTAMPTZ, indexes) |
| InstagramMetricsRepository | `core/analytics/repository.py` | Repository pattern reference (async session, upsert) |
| MetricsQueryService | `core/analytics/metrics_query.py` | Query service pattern + CTR integration point |
| AnalyticsConfig | `core/config.py` | Config dataclass pattern, extend for UTM |
| Router pattern | `ui/backend/routers/evidence.py` | FastAPI router structure reference |
| Pydantic schemas | `ui/backend/schemas/evidence.py` | Schema structure reference |

### Testing Standards

- **TDD required**: Write failing tests first, then implementation
- **Tests mirror source**: `tests/core/test_analytics/test_utm_*.py` mirrors `core/analytics/utm_*.py`
- **Router tests**: `tests/ui/backend/test_routers/test_redirect.py`
- **Protocol-based mocking**: Use `AsyncMock(spec=UTMRepository)` for service tests
- **No N+1 patterns**: `get_clicks_by_post_ids` uses single query with `IN` clause
- **Coverage targets**: Happy path, 404, collision retry, GDPR (verify no raw IP), async fire-and-forget, batch queries
- **Redirect performance**: Test that redirect returns before click is recorded (async)

### Pre-Implementation Verification

Before coding, verify:
- [x] Existing `integrations/shopify/utm.py` exports `UTMParams` and `build_utm_url` in `__init__.py`
- [x] `core/analytics/__init__.py` has current 11 exports (from Story 7-1)
- [x] `ui/backend/routers/__init__.py` router list is current (7 routers)
- [x] FastAPI app mounts routers -- check how `/l/{code}` can be at root level vs `/api/` prefix
- [x] No existing `short_links` or `link_clicks` tables in migrations folder

### Project Structure Notes

**New files to create:**
```
core/analytics/
    utm_models.py              # ShortLink, LinkClick SQLAlchemy models
    utm_repository.py          # UTMRepository (async CRUD)
    utm_service.py             # ShortLinkService (link generation + resolution)
    click_analytics.py         # ClickAnalyticsService (aggregation + CTR)
    utm_integration.py         # generate_post_short_link() orchestrator
migrations/versions/
    2026_02_23_001_create_utm_tracking_tables.py
tests/core/test_analytics/
    test_utm_models.py
    test_utm_repository.py
    test_utm_service.py
    test_click_analytics.py
    test_utm_integration.py
ui/backend/routers/
    redirect.py                # GET /l/{code} endpoint
tests/ui/backend/test_routers/
    test_redirect.py
```

**Files to modify:**
```
core/analytics/__init__.py          # Add 7+ new exports
core/config.py                      # Add UTMConfig frozen dataclass
config/dawo_analytics.json          # Add utm_config section
ui/backend/routers/__init__.py      # Add redirect_router
teams/dawo/team_spec.py             # Register 3 new services
integrations/shopify/utm.py         # Add build_short_link_url() helper
```

### Key Technical Decisions (from Epic 7 prep)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Link shortener | Custom FastAPI `/l/{code}` | Zero deps, GDPR, data ownership |
| Short code generation | `secrets.token_urlsafe(6)` | stdlib, crypto-random, 8B+ combinations |
| IP storage | SHA-256 hash only | GDPR compliance -- never store raw IPs |
| Device parsing | Simple regex on user-agent | No `user-agents` dep needed -- keep zero external deps |
| Click recording | `asyncio.create_task()` fire-and-forget | Redirect speed > tracking reliability |
| New dependencies | None | `secrets`, `hashlib`, `urllib.parse` all stdlib |
| Registration | `RegisteredService` (no LLM tier) | Pure data service, no LLM needed |
| Attribution table | Deferred to Story 7-3 | `utm_attributions` is Shopify webhook-driven |

### Scope Boundaries (DO NOT IMPLEMENT)

- **DO NOT** build `utm_attributions` table -- that's Story 7-3 (Shopify Sales Attribution)
- **DO NOT** modify caption generator to inject short links -- that's a separate integration task
- **DO NOT** build a link management UI -- Story 7-8 will handle dashboards
- **DO NOT** implement GA4 integration -- third-party analytics are configured externally
- **DO NOT** add Shopify webhook handling -- that's Story 7-3
- **DO NOT** add `user-agents` dependency -- use simple regex for device type detection

### Anti-Patterns to Avoid

- **DO NOT** create a new UTM generation system -- reuse `UTMParams` from `integrations/shopify/utm.py`
- **DO NOT** hardcode model names (haiku/sonnet/opus) -- this service has no LLM
- **DO NOT** load config from files directly -- use constructor injection via `UTMConfig`
- **DO NOT** use `getattr` on user-supplied sort fields (SQL injection risk from Epic 6-9)
- **DO NOT** create N+1 queries when loading clicks for multiple posts
- **DO NOT** use `datetime.utcnow()` -- use `datetime.now(UTC)`
- **DO NOT** store raw IP addresses -- always SHA-256 hash (GDPR)
- **DO NOT** block the redirect on click recording -- always fire-and-forget
- **DO NOT** skip `__all__` exports in any `__init__.py`
- **DO NOT** log at ERROR level for 404 on `/l/{code}` -- bots/scanners are expected traffic
- **DO NOT** forget to handle X-Forwarded-For header for IP extraction behind reverse proxy

### Previous Story Intelligence (from Story 7-1)

**Patterns that worked:**
- Repository pattern with upsert (`INSERT ... ON CONFLICT ... DO UPDATE`)
- Frozen dataclass for config (`AnalyticsConfig` with nested types)
- `RegisteredService` for pure data services (no LLM tier)
- Fire-and-forget pattern for non-critical post-publish actions (`_schedule_post_metrics`)
- Batch query methods to prevent N+1 (`get_by_media_ids`)

**Code review fixes to learn from (Story 7-1):**
- H1: Session lifecycle -- use async context manager properly in service methods
- M3: Every model file needs `__all__` export
- M4: Derive enum ordering from enum values, not hardcoded lists
- L1: `datetime.now(UTC)` not `datetime.utcnow()`

**Integration point with Story 7-1:**
- `ClickAnalyticsService.get_post_analytics()` can import `MetricsQueryService` to compute CTR = clicks / impressions
- Use `InstagramMetricsRepository.get_by_media_id()` to get impressions data
- This cross-service query should be in the analytics service layer, not in the repository

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.2]
- [Source: docs/research/utm-tracking-strategy.md]
- [Source: _bmad-output/implementation-artifacts/epic-7-prep.md#Story 7-2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Architecture]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]
- [Source: docs/pre-submission-checklist.md]
- [Source: docs/registered-agent-vs-service.md]
- [Source: integrations/shopify/utm.py -- existing UTM generation to reuse]
- [Source: teams/dawo/leads/gmail/utm.py -- email UTM injection pattern]
- [Source: core/analytics/models.py -- SQLAlchemy model pattern]
- [Source: core/analytics/repository.py -- async repository pattern]
- [Source: core/analytics/metrics_query.py -- CTR integration point]
- [Source: ui/backend/routers/__init__.py -- router registration]
- [Source: _bmad-output/implementation-artifacts/7-1-instagram-engagement-metrics-collection.md -- previous story]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — all tests passed on first or second TDD cycle. No debug sessions required.

### Completion Notes List

- All 8 tasks implemented via strict TDD red-green-refactor cycle
- 94 new tests across 7 test files — all passing
- Reused existing `UTMParams` and `build_utm_url` from `integrations/shopify/utm.py` (zero duplication)
- GDPR compliant: IP addresses stored as SHA-256 hashes only, never raw
- Fire-and-forget click recording via `asyncio.create_task()` for sub-50ms redirect latency
- Batch `get_clicks_by_post_ids` query prevents N+1 (single IN-clause query)
- Cross-service CTR integration with Story 7-1 `MetricsQueryService` for impressions-based CTR
- Device type parsing via simple regex patterns (mobile/tablet/desktop/bot), zero external dependencies
- 3 new `RegisteredService` entries in team_spec (no LLM tier needed)
- Full regression test suite: 650+ tests across analytics, integrations, teams, and UI backend — no regressions
- Pre-existing flaky test `test_generate_tracks_generation_time` unrelated to this story (passes on re-run)

### File List

**New files created:**
- `core/analytics/utm_models.py` — ShortLink and LinkClick SQLAlchemy models
- `core/analytics/utm_repository.py` — UTMRepository (async CRUD, batch queries, click stats)
- `core/analytics/utm_service.py` — ShortLinkService (link generation, resolution, click tracking)
- `core/analytics/click_analytics.py` — ClickAnalyticsService (aggregation, CTR, comparisons)
- `core/analytics/utm_integration.py` — generate_post_short_link() orchestrator
- `ui/backend/routers/redirect.py` — GET /l/{code} redirect endpoint
- `migrations/versions/2026_02_23_001_create_utm_tracking_tables.py` — Alembic migration
- `tests/core/test_analytics/test_utm_models.py` — 26 tests
- `tests/core/test_analytics/test_utm_repository.py` — 13 tests
- `tests/core/test_analytics/test_utm_service.py` — 22 tests
- `tests/core/test_analytics/test_click_analytics.py` — 10 tests
- `tests/core/test_analytics/test_utm_integration.py` — 6 tests
- `tests/core/test_analytics/test_utm_config.py` — 8 tests
- `tests/ui/backend/test_routers/__init__.py` — empty init
- `tests/ui/backend/test_routers/test_redirect.py` — 9 tests

**Files modified:**
- `core/config.py` — Added UTMConfig dataclass, _build_utm_config, utm field on Config, __all__ update
- `config/dawo_analytics.json` — Added utm_config section
- `core/analytics/__init__.py` — Expanded from 11 to 21 exports
- `integrations/shopify/utm.py` — Added build_short_link_url() helper
- `integrations/shopify/__init__.py` — Added build_short_link_url export
- `ui/backend/routers/__init__.py` — Added redirect_router (now 8 routers)
- `teams/dawo/team_spec.py` — Registered 3 new RegisteredService entries
