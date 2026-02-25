# Story 7.1: Instagram Engagement Metrics Collection

Status: complete

## Story

As an **operator**,
I want Instagram engagement metrics collected at regular intervals,
so that I can measure content performance over time.

## Acceptance Criteria

1. **Given** a post is published to Instagram **When** 1 hour has passed **Then** the metrics collector retrieves: likes, comments, shares, saves, reach, impressions, total_interactions **And** metrics are stored with media_id, snapshot_label="baseline", and timestamp **And** collection repeats at 24h, 48h, and 7d intervals

2. **Given** Instagram API is available **When** metrics are collected **Then** data is retrieved in < 10 seconds per post **And** all available metrics are captured (image + reel-specific where applicable) **And** collection respects the 200 calls/hour shared rate limit

3. **Given** metrics are collected at multiple intervals **When** I view post performance **Then** I see trend data: initial engagement, growth over time, final metrics **And** comparison to average post performance is shown

4. **Given** Instagram API is unavailable **When** scheduled collection fails **Then** it's queued for retry at next opportunity **And** partial data is preserved **And** operator is notified of gaps in data via Discord

## Tasks / Subtasks

- [x] Task 1: Database migration and model (AC: #1)
  - [x] 1.1 Create Alembic migration `create_instagram_media_metrics` table with columns: id (UUID PK), media_id (VARCHAR 100), collected_at (TIMESTAMPTZ), snapshot_label (VARCHAR 20), impressions (INT), reach (INT), likes (INT), comments (INT), saved (INT), shares (INT), total_interactions (INT), plays (INT nullable), avg_watch_time_ms (INT nullable), raw_response (JSONB), created_at (TIMESTAMPTZ)
  - [x] 1.2 Add UNIQUE constraint on (media_id, snapshot_label)
  - [x] 1.3 Add indexes: idx_media_metrics_media_id, idx_media_metrics_collected_at, idx_media_metrics_snapshot_label
  - [x] 1.4 Create SQLAlchemy async model `InstagramMediaMetric` in `core/analytics/models.py`
  - [x] 1.5 Write tests for model (field validation, unique constraint behavior)

- [x] Task 2: Metrics repository (AC: #1, #4)
  - [x] 2.1 Create `InstagramMetricsRepository` in `core/analytics/repository.py` with async SQLAlchemy
  - [x] 2.2 Methods: `save_snapshot(metric)`, `get_by_media_id(media_id)`, `get_latest_snapshot(media_id)`, `get_average_metrics(days_back=30)` -- `get_pending_collections` deferred to jobs layer (Task 4.5), `get_all_snapshots` removed (duplicate of `get_by_media_id`)
  - [x] 2.3 Use `INSERT ... ON CONFLICT (media_id, snapshot_label) DO UPDATE` for idempotent saves
  - [x] 2.4 Batch query support: `get_by_media_ids(media_ids: list[str])` -- prevent N+1
  - [x] 2.5 Write tests for all repository methods

- [x] Task 3: Update Instagram client for insights (AC: #1, #2)
  - [x] 3.1 Update `get_media_insights()` in `integrations/instagram/client.py` to use correct metric list: impressions, reach, likes, comments, saved, shares, total_interactions (replace deprecated `engagement`)
  - [x] 3.2 Add reel-specific metrics: ig_reels_aggregated_all_plays_count, ig_reels_avg_watch_time (conditional on media_type)
  - [x] 3.3 Add `get_media_insights()` to `InstagramPublishClientProtocol` if not already present
  - [x] 3.4 Count insights calls against shared `RateLimitTracker` (200 calls/hour budget)
  - [x] 3.5 Return structured `MediaInsightsResult` dataclass (not raw dict)
  - [x] 3.6 Write tests for updated client method (mock httpx responses)

- [x] Task 4: Metrics collector service (AC: #1, #2, #4)
  - [x] 4.1 Create `InstagramMetricsCollector` in `core/analytics/metrics_collector.py`
  - [x] 4.2 Constructor injection: `InstagramPublishClientProtocol`, `InstagramMetricsRepository`, `AnalyticsConfig`
  - [x] 4.3 Method `collect_metrics(media_id: str, snapshot_label: str) -> CollectionResult` -- calls client, stores via repo
  - [x] 4.4 Method `collect_batch(media_ids: list[str], snapshot_label: str) -> BatchCollectionResult` -- processes all with rate limit awareness
  - [x] 4.5 Method `get_pending_posts(snapshot_label: str) -> list[str]` -- deferred to jobs layer (crosses module boundary)
  - [x] 4.6 Uses client Protocol (which wraps API calls) -- RetryMiddleware at client level
  - [x] 4.7 Handle partial failures: store successful metrics, log failures, return mixed results
  - [x] 4.8 Write comprehensive tests with mocked client and repository (10/10 pass)

- [x] Task 5: ARQ scheduling jobs (AC: #1, #4)
  - [x] 5.1 Create `core/analytics/jobs.py` with ARQ job functions
  - [x] 5.2 Job `collect_metrics_job(ctx, snapshot_label)`: find pending posts, call collector service
  - [x] 5.3 Define cron schedule: baseline=hourly check via ANALYTICS_JOB_SETTINGS
  - [x] 5.4 Job `schedule_metrics_collection(redis_pool, media_id, published_at)`: enqueue deferred jobs at T+1h, T+24h, T+48h, T+7d
  - [x] 5.5 ANALYTICS_JOB_SETTINGS dict with cron_jobs + functions (separate from WorkerSettings)
  - [x] 5.6 `_send_analytics_discord_alert` for collection failure notifications
  - [x] 5.7 Write tests for job functions (22/22 pass)

- [x] Task 6: Hook into publishing flow (AC: #1)
  - [x] 6.1 Added `_schedule_post_metrics` helper + call in `schedule_publish_job` success path
  - [x] 6.2 Only enqueues when `publish_result.instagram_post_id` is truthy
  - [x] 6.3 Integration tests verifying publish -> metrics scheduling flow (7/7 pass)

- [x] Task 7: Configuration (AC: #2)
  - [x] 7.1 Create `config/dawo_analytics.json` with: collection_intervals, rate_limit_buffer, retry_config, discord_channel
  - [x] 7.2 Add `AnalyticsConfig` frozen dataclass to `core/config.py` (with CollectionInterval)
  - [x] 7.3 Wire config loading into existing config system (_build_analytics_config, get_config)

- [x] Task 8: Metrics query API (AC: #3)
  - [x] 8.1 Create `core/analytics/metrics_query.py` with `MetricsQueryService`
  - [x] 8.2 Methods: `get_post_metrics`, `get_average_metrics`, `get_performance_comparison` with result dataclasses
  - [x] 8.3 Delta computation: ordered by SNAPSHOT_ORDER, diff between consecutive snapshots
  - [x] 8.4 Write tests for delta computation and comparison logic (16/16 pass)

- [x] Task 9: Registration and exports (AC: all)
  - [x] 9.1 Updated `core/analytics/__init__.py` with complete `__all__` (11 exports)
  - [x] 9.2 Registered `InstagramMetricsCollector` as `RegisteredService` in `teams/dawo/team_spec.py`
  - [x] 9.3 Registered `MetricsQueryService` and `InstagramMetricsRepository` as `RegisteredService`
  - [x] 9.4 Verified all 5 analytics module `__init__.py` files have complete `__all__` exports

## Dev Notes

### Critical Architecture Patterns

**Extend, don't create:**
- The Instagram client already exists at `integrations/instagram/client.py` with `InstagramPublishClient`
- It already has a `get_media_insights()` method but it uses the **deprecated** `engagement` metric -- update it
- The client uses `httpx.AsyncClient` and the Facebook Graph API v19.0
- DO NOT create a separate Instagram client. Extend the existing one.

**Rate limit awareness:**
- Shared 200 calls/hour budget across ALL Instagram API operations (scanning, publishing, insights)
- Currently ~105 calls/hour used. ~95 remaining budget.
- Insights endpoint: 1 API call per post per collection
- With 10 posts/day and 4 snapshots each: ~40 calls/day = ~2 calls/hour average. Well within budget.
- Still must register calls against `RateLimitTracker` in client

**Snapshot-delta pattern:**
- Instagram API returns **lifetime cumulative values only** -- no date-range filtering
- Must store raw cumulative snapshots and compute deltas at query time
- Use UNIQUE(media_id, snapshot_label) to prevent duplicate snapshots
- Use UPSERT for idempotent re-collection on retry

**RetryMiddleware pattern:**
- All external API calls go through `RetryMiddleware`
- Returns `RetryResult` with `is_incomplete` flag -- NEVER raises
- See `docs/retry-middleware-patterns.md`

**Event-driven scheduling:**
- When a post is published successfully (in `schedule_publish_job`), enqueue deferred metrics collection jobs
- Use ARQ `_defer_until` parameter for future execution (proven pattern in `core/scheduling/jobs.py`)
- Cron pattern from `core/notifications/jobs.py`: use `cron_jobs` dict with `hour`/`minute` sets

### Existing Code to Reuse

| Component | Location | How to Reuse |
|-----------|----------|-------------|
| Instagram client | `integrations/instagram/client.py` | Update `get_media_insights()` method |
| Client protocol | `integrations/instagram/client.py` | Add insights to `InstagramPublishClientProtocol` |
| Rate limit tracker | `integrations/instagram/client.py` | Register insights calls against existing tracker |
| RetryMiddleware | `core/middleware/retry.py` | Wrap all API calls |
| ARQ deferred jobs | `core/scheduling/jobs.py:enqueue_publish_job` | Pattern for `_defer_until` |
| Cron job config | `core/notifications/jobs.py` | NOTIFICATION_JOB_SETTINGS cron_jobs pattern |
| Discord alerts | `core/scheduling/jobs.py:_send_discord_failure_alert` | Reuse for analytics failure alerts |
| Event emission | `core/publishing/events.py:PublishEventEmitter` | Pattern for analytics events |
| Config system | `core/config.py` | Add `AnalyticsConfig` frozen dataclass |
| Approval items | `core/approval/models.py` | Query published posts: `instagram_post_id IS NOT NULL` |

### Testing Standards

- **TDD required**: Write failing tests first, then implementation
- **Tests mirror source**: `tests/core/analytics/` mirrors `core/analytics/`
- **Protocol-based mocking**: Use `AsyncMock(spec=InstagramPublishClientProtocol)`
- **No N+1 patterns**: Batch load metrics in tests, verify query counts
- **Coverage targets**: Success paths, failure paths, partial failures, rate limit handling, retry behavior
- **Fixtures**: Create factory functions for `InstagramMediaMetric` test objects

### Pre-Implementation Verification (from Epic 7 prep)

Before coding, verify:
- [ ] `instagram_manage_insights` scope on current token: `GET /debug_token?input_token={token}`
- [ ] Test `/{media-id}/insights` with a recent post to confirm metrics return
- [ ] Check if deprecated `engagement` metric is still used in `integrations/instagram/client.py`
- [ ] Confirm Graph API version (v19.0 -- consider v21.0 upgrade if deprecation timeline is near)
- [ ] Estimate rate budget: current usage + metrics collection fits within 200 calls/hour

### Project Structure Notes

**New files to create:**
```
core/analytics/
    __init__.py
    models.py                  # InstagramMediaMetric SQLAlchemy model
    repository.py              # InstagramMetricsRepository
    metrics_collector.py       # InstagramMetricsCollector service
    metrics_query.py           # MetricsQueryService
    jobs.py                    # ARQ job functions
config/
    dawo_analytics.json        # Analytics configuration
migrations/versions/
    2026_02_20_001_create_instagram_media_metrics.py
tests/core/analytics/
    __init__.py
    test_models.py
    test_repository.py
    test_metrics_collector.py
    test_metrics_query.py
    test_jobs.py
```

**Files to modify:**
```
integrations/instagram/client.py          # Update get_media_insights()
core/scheduling/jobs.py                   # Hook metrics scheduling after publish
core/config.py                            # Add AnalyticsConfig
teams/dawo/team_spec.py                   # Register new services
```

### Key Technical Decisions (from Epic 7 prep)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Metrics endpoint | `/{media-id}/insights` edge | Full metric set: reach, saves, shares, impressions |
| Collection intervals | T+1h, T+24h, T+48h, T+7d | API returns lifetime cumulative; delta at query time |
| Deprecated metric | Replace `engagement` with `total_interactions` | Deprecated in Graph API v18.0+ |
| Library | Extend existing httpx client | Zero deps, consistent with codebase |
| Registration | `RegisteredService` (no LLM tier) | Pure Python data collection, no LLM needed |
| Job queue | ARQ (already in use) | Async-native, Redis-backed, existing patterns |

### Anti-Patterns to Avoid

- **DO NOT** create a new Instagram client class -- extend the existing one
- **DO NOT** hardcode model names (haiku/sonnet/opus) -- this service has no LLM
- **DO NOT** load config from files directly -- use constructor injection
- **DO NOT** use `getattr` on user-supplied sort fields (SQL injection risk from Epic 6)
- **DO NOT** create N+1 queries when loading metrics for multiple posts
- **DO NOT** use `datetime.utcnow()` -- use `datetime.now(UTC)`
- **DO NOT** forget to count insights API calls against the shared rate limit tracker
- **DO NOT** silently swallow exceptions -- log all failures
- **DO NOT** skip `__all__` exports in any `__init__.py`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.1]
- [Source: docs/research/instagram-graph-api-insights.md]
- [Source: _bmad-output/implementation-artifacts/epic-7-prep.md#Story 7-1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Architecture]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]
- [Source: docs/pre-submission-checklist.md]
- [Source: docs/retry-middleware-patterns.md]
- [Source: docs/registered-agent-vs-service.md]
- [Source: integrations/instagram/client.py -- existing client to extend]
- [Source: core/scheduling/jobs.py -- ARQ deferred job pattern]
- [Source: core/notifications/jobs.py -- cron job configuration pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None

### Completion Notes List

- All 9 tasks completed via TDD red-green-refactor cycle
- 88 new tests across 6 test files, all passing
- Task 7 (Configuration) implemented early as dependency for Task 4
- Pre-existing failures in `tests/core/scheduling/test_jobs.py` (5 tests) confirmed as pre-existing via git stash test
- `_schedule_post_metrics` helper added as fire-and-forget pattern (failures don't block publishing)
- Snapshot-delta pattern: store raw cumulative values, compute deltas at query time via SNAPSHOT_ORDER
- No N+1 queries: `get_by_media_ids` uses single IN query, batch collection iterates sequentially (rate limit aware)

### Change Log

- Task 1: Created migration + SQLAlchemy model (20 tests)
- Task 2: Created repository with upsert, batch query, averages (14 tests)
- Task 3: Updated Instagram client with MediaInsightsResult, non-deprecated metrics (13 tests)
- Task 4: Created metrics collector with partial failure handling (10 tests)
- Task 5: Created ARQ jobs with cron schedule + deferred jobs + Discord alerts (22 tests)
- Task 6: Hooked metrics scheduling into publish flow via _schedule_post_metrics (7 tests)
- Task 7: Created AnalyticsConfig, CollectionInterval, dawo_analytics.json
- Task 8: Created MetricsQueryService with delta computation + comparison (16 tests)
- Task 9: Updated __init__.py exports (11 items), registered 3 services in team_spec.py
- Code Review Fixes:
  - H1: Fixed session lifecycle in jobs.py (sync _get_session returning context manager, async with wrapper)
  - H2: Removed duplicate get_all_snapshots (identical to get_by_media_id), updated metrics_query.py + tests
  - H3: Documented get_pending_collections deferral in Task 2.2
  - L3: Added cron safety nets for all 4 snapshot labels (was baseline only)
  - M3: Added __all__ to models.py
  - M4: Derived SNAPSHOT_ORDER from SnapshotLabel enum
  - M5: Typed get_average_metrics return as dict[str, float | int]
  - L1: Fixed 5x datetime.utcnow() → datetime.now(UTC) in core/scheduling/jobs.py
  - L2: Fixed test count (88 across 6 files, not 89 across 5)
  - M1/M2: Added undocumented files to File List

### File List

**New files created:**
- `core/analytics/__init__.py` -- Module init with 11 exports
- `core/analytics/models.py` -- InstagramMediaMetric, SnapshotLabel
- `core/analytics/repository.py` -- InstagramMetricsRepository
- `core/analytics/metrics_collector.py` -- InstagramMetricsCollector, CollectionResult, BatchCollectionResult
- `core/analytics/metrics_query.py` -- MetricsQueryService, PostMetricsResult, MetricsDelta, AverageMetrics, PerformanceComparison
- `core/analytics/jobs.py` -- collect_metrics_job, collect_single_metrics_job, schedule_metrics_collection, ANALYTICS_JOB_SETTINGS
- `config/dawo_analytics.json` -- Analytics configuration (intervals, rate limit buffer, retry, discord)
- `migrations/versions/2026_02_20_001_create_instagram_media_metrics.py` -- Alembic migration
- `tests/core/test_analytics/__init__.py` -- Test module init
- `tests/core/test_analytics/test_models.py` -- 20 tests
- `tests/core/test_analytics/test_repository.py` -- 13 tests
- `tests/core/test_analytics/test_metrics_collector.py` -- 10 tests
- `tests/core/test_analytics/test_metrics_query.py` -- 16 tests
- `tests/core/test_analytics/test_jobs.py` -- 22 tests
- `tests/integration/test_analytics_integration.py` -- 7 integration tests

**Files modified:**
- `integrations/instagram/client.py` -- Added MediaInsightsResult, updated get_media_insights, added to protocol
- `core/config.py` -- Added AnalyticsConfig, CollectionInterval, _build_analytics_config
- `core/scheduling/jobs.py` -- Added _schedule_post_metrics hook after publish success, added UTC import
- `teams/dawo/team_spec.py` -- Registered 3 analytics services (collector, repository, query)
- `tests/integrations/instagram/test_client.py` -- Added 13 tests for insights
- `core/publishing/events.py` -- Fixed datetime.utcnow() → datetime.now(UTC)
- `requirements.txt` -- Pre-existing Epic 5/6 dependency additions (no Story 7-1 changes)
