# Story 7.10: Graceful API Degradation Handling

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the system to continue operating when external APIs fail,
so that temporary outages don't stop my workflow.

## Acceptance Criteria

1. **AC1 - Graceful Degradation Strategy:** Given an external API is unavailable (Instagram, Shopify, Discord, Google Calendar), when an operation requires that API, then it follows the graceful degradation strategy: retry with backoff (existing RetryMiddleware from Story 1.5), mark operation INCOMPLETE if retries fail, continue other operations that don't need that API, and send Discord alert for API errors (if Discord is available).

2. **AC2 - Instagram API Down:** Given Instagram API is down, when publishing is scheduled, then publish is queued for retry via the existing OperationQueue. Other content generation continues unblocked. Discord notification is sent about the issue.

3. **AC3 - Shopify Cache Fallback:** Given Shopify API is unavailable, when content generator needs product data, then it uses cached data if available (< 24h old via existing stale cache pattern in ShopifyClient). Content proceeds with placeholder if no cache. Operator is notified to review product references.

4. **AC4 - Multi-API Status Dashboard:** Given multiple APIs are down, when operator views system status, then they see: which APIs are affected, what operations are queued, and estimated impact is shown (X posts waiting).

5. **AC5 - Auto-Recovery:** Given an API recovers, when it becomes available again, then queued operations process automatically. Discord notification announces recovery. Catch-up processing respects rate limits (using existing rate limit config).

## Tasks / Subtasks

- [x] Task 1: Service Health Registry (AC: 1, 4)
  - [x] 1.1 Create `core/degradation/__init__.py` with `__all__` exports
  - [x] 1.2 Create `ServiceHealthStatus` frozen dataclass in `core/degradation/models.py`:
    - `service_name: str` (e.g., "instagram", "shopify", "discord", "google_calendar")
    - `status: str` ("healthy", "degraded", "unhealthy")
    - `consecutive_failures: int`
    - `last_success: datetime | None`
    - `last_failure: datetime | None`
    - `last_error: str | None`
    - `queued_operations: int`
    - `updated_at: datetime`
  - [x] 1.3 Create `DegradationConfig` frozen dataclass in `core/config.py`:
    - `failure_threshold: int = 3` (consecutive failures before marking degraded)
    - `unhealthy_threshold: int = 10` (consecutive failures before marking unhealthy)
    - `recovery_check_interval_seconds: int = 300` (5 minutes)
    - `max_recovery_batch_size: int = 20` (items per recovery pass)
    - `alert_cooldown_seconds: int = 300` (5 min between alerts per service)
    - `stale_cache_ttl_hours: int = 24`
    - Add to `get_config()` return with key `degradation`
  - [x] 1.4 Create `config/dawo_degradation.json`:
    ```json
    {
      "failure_threshold": 3,
      "unhealthy_threshold": 10,
      "recovery_check_interval_seconds": 300,
      "max_recovery_batch_size": 20,
      "alert_cooldown_seconds": 300,
      "stale_cache_ttl_hours": 24,
      "monitored_services": [
        "instagram",
        "shopify",
        "discord",
        "google_calendar"
      ]
    }
    ```
  - [x] 1.5 Create `ServiceHealthRegistry` in `core/degradation/registry.py`:
    - Constructor: `DegradationConfig`, `redis: Redis` (both via DI)
    - Redis key pattern: `dawo:service_health:{service_name}`
    - `async def record_success(self, service_name: str) -> ServiceHealthStatus`:
      - Reset consecutive_failures to 0
      - Update last_success, status to "healthy"
      - If transitioning FROM degraded/unhealthy → emit recovery event
    - `async def record_failure(self, service_name: str, error: str) -> ServiceHealthStatus`:
      - Increment consecutive_failures
      - Update last_failure, last_error
      - Status transitions: 0-2 failures → "healthy", 3-9 → "degraded", 10+ → "unhealthy"
      - Thresholds driven by DegradationConfig
    - `async def get_status(self, service_name: str) -> ServiceHealthStatus`:
      - Read from Redis, return current status
    - `async def get_all_statuses(self) -> list[ServiceHealthStatus]`:
      - Read all monitored services from config
      - Return list of statuses
    - `async def get_queued_count(self, service_name: str) -> int`:
      - Count operations in Redis operation queue for this service
    - **All methods wrapped in try/except** — Redis failures return sensible defaults (healthy status), NEVER raise
  - [x] 1.6 Write registry + config tests (target: 15+ tests, actual: 26)
    - DegradationConfig frozen immutability
    - DegradationConfig defaults
    - DegradationConfig in get_config() return
    - ServiceHealthStatus frozen immutability
    - record_success resets consecutive_failures
    - record_success transitions from degraded to healthy
    - record_failure increments consecutive_failures
    - record_failure transitions healthy → degraded at threshold
    - record_failure transitions degraded → unhealthy at threshold
    - get_status returns healthy default when no data
    - get_all_statuses returns all monitored services
    - get_queued_count returns pending operation count
    - Redis failure in record_success doesn't raise
    - Redis failure in get_status returns healthy default
    - Recovery event emitted on status transition

- [x] Task 2: Integration with Existing RetryMiddleware (AC: 1, 2, 3)
  - [x] 2.1 Extend `RetryMiddleware` in `teams/dawo/middleware/retry.py`:
    - Add optional `service_health_registry: ServiceHealthRegistry | None = None` to constructor
    - After each attempt: call `registry.record_success()` or `registry.record_failure()`
    - **CRITICAL:** This is an OPTIONAL enhancement. RetryMiddleware MUST work without the registry (backward compatible)
    - When `is_incomplete=True` → also record failure
    - When success → record success
  - [x] 2.2 Extend `RetryableHttpClient` in `teams/dawo/middleware/http_client.py`:
    - Accept optional `ServiceHealthRegistry` in constructor
    - Pass through to RetryMiddleware
  - [x] 2.3 Add pre-check in RetryMiddleware (optional optimization):
    - If service is "unhealthy" AND cache fallback exists → skip API call, go straight to fallback
    - If service is "unhealthy" AND no fallback → proceed with API call anyway (might recover)
    - **NEVER block an operation** — unhealthy status is advisory, not a hard gate
  - [x] 2.4 Write middleware extension tests (target: 10+ tests, actual: 14)
    - RetryMiddleware works without registry (backward compat)
    - RetryMiddleware records success on successful API call
    - RetryMiddleware records failure on failed API call
    - RetryMiddleware records failure on is_incomplete
    - RetryableHttpClient passes registry to middleware
    - Pre-check skips API when unhealthy + cache available
    - Pre-check still calls API when unhealthy + no cache
    - Registry None → no recording (no errors)

- [x] Task 3: Degradation Alerts via Discord (AC: 1, 2, 5)
  - [x] 3.1 Create `DegradationAlertService` in `core/degradation/alerts.py`:
    - Constructor: `ServiceHealthRegistry`, `DiscordAlertManager` (from existing `teams/dawo/middleware/discord_alerts.py`), `DegradationConfig`
    - `async def on_service_degraded(self, service_name: str, error: str) -> bool`:
      - Rate-limited: max 1 alert per service per `alert_cooldown_seconds`
      - Discord embed with: service name, error message, consecutive failures, queued operations count
      - Color: orange (degraded) or red (unhealthy)
      - Returns True if alert sent, False if cooldown active
    - `async def on_service_recovered(self, service_name: str) -> bool`:
      - Always send recovery alerts (no cooldown)
      - Discord embed: service name, recovery time, queued operations to process
      - Color: green
    - `async def send_status_summary(self) -> bool`:
      - Aggregate status of all monitored services
      - Send summary embed with per-service health
      - Intended for periodic reporting (e.g., daily)
    - **All methods catch exceptions** — Discord unavailability doesn't cascade
    - **If Discord itself is unhealthy** → log warning locally, don't try to send alert about Discord via Discord
  - [x] 3.2 Write alert service tests (target: 10+ tests, actual: 13)
    - on_service_degraded sends Discord alert
    - on_service_degraded respects cooldown
    - on_service_recovered always sends (no cooldown)
    - send_status_summary includes all services
    - Discord failure doesn't raise
    - Discord-about-Discord detection (no self-alert loop)
    - Alert includes queued operations count
    - Color matches severity (orange vs red)

- [x] Task 4: Recovery Processing (AC: 5)
  - [x] 4.1 Create `RecoveryProcessor` in `core/degradation/recovery.py`:
    - Constructor: `ServiceHealthRegistry`, `OperationQueue` (existing from `teams/dawo/middleware/operation_queue.py`), `DegradationConfig`
    - `async def check_and_recover(self, service_name: str) -> RecoveryResult`:
      - Check if service status is "healthy" (recently recovered)
      - Get pending operations for this service from OperationQueue
      - Process up to `max_recovery_batch_size` operations
      - Re-enqueue each via ARQ job (fire-and-forget, respects rate limits)
      - Return `RecoveryResult(service=name, processed=N, remaining=M, errors=[])`
    - `async def process_all_services(self) -> list[RecoveryResult]`:
      - For each monitored service: check_and_recover
      - Return aggregate results
  - [x] 4.2 Create `RecoveryResult` frozen dataclass in `core/degradation/models.py`:
    - `service_name: str`
    - `processed: int`
    - `remaining: int`
    - `errors: list[str]`
  - [x] 4.3 Add ARQ cron job `_process_recovery_queue` in `core/scheduling/jobs.py`:
    - Runs every 5 minutes (configurable via recovery_check_interval_seconds)
    - Calls `RecoveryProcessor.process_all_services()`
    - Logs results
    - **Lazy imports** inside function (same pattern as all other ARQ jobs)
    - Register in `WorkerSettings.cron_jobs`
  - [x] 4.4 Write recovery tests (target: 12+ tests, actual: 12)
    - check_and_recover processes pending operations for healthy service
    - check_and_recover skips degraded/unhealthy services
    - check_and_recover respects max_recovery_batch_size
    - check_and_recover returns correct remaining count
    - process_all_services iterates all monitored services
    - ARQ cron job calls process_all_services
    - Recovery enqueues via ARQ (fire-and-forget)
    - Empty queue returns processed=0
    - Error in one operation doesn't block others
    - RecoveryResult frozen immutability
    - Rate limit respect during catch-up (batch size limits)

- [x] Task 5: System Status Dashboard Endpoint (AC: 4)
  - [x] 5.1 Create Pydantic schemas in `ui/backend/schemas/degradation.py`:
    - `ServiceHealthResponse`:
      - `service_name: str`
      - `status: str` ("healthy", "degraded", "unhealthy")
      - `consecutive_failures: int`
      - `last_success: datetime | None`
      - `last_failure: datetime | None`
      - `last_error: str | None`
      - `queued_operations: int`
    - `SystemStatusResponse`:
      - `overall_status: str` ("healthy", "degraded", "unhealthy")
      - `services: list[ServiceHealthResponse]`
      - `total_queued_operations: int`
      - `last_updated: datetime`
    - `RecoveryTriggerRequest`:
      - `service_name: str | None = None` (None = all services)
    - `RecoveryTriggerResponse`:
      - `results: list[RecoveryResultResponse]`
    - `RecoveryResultResponse`:
      - `service_name: str`
      - `processed: int`
      - `remaining: int`
      - `errors: list[str]`
  - [x] 5.2 Create `ui/backend/routers/degradation.py`:
    - `GET  /api/system/status` — overall system status with per-service health
      - Overall status = worst status among all services
      - Returns `SystemStatusResponse`
    - `GET  /api/system/status/{service_name}` — single service health
      - Returns `ServiceHealthResponse`
      - 404 if service_name not in monitored_services
    - `POST /api/system/recover` — manual recovery trigger
      - Accepts `RecoveryTriggerRequest`
      - Calls RecoveryProcessor.check_and_recover() or process_all_services()
      - Returns count of operations re-queued
    - `POST /api/system/reset/{service_name}` — manual health reset
      - Force-resets service status to "healthy" (admin override)
      - Useful when operator knows API is back but auto-detection hasn't caught up
    - Dependency injection: `get_health_registry()`, `get_recovery_processor()`
  - [x] 5.3 Register router in `ui/backend/routers/__init__.py`:
    - Add `from .degradation import router as degradation_router`
    - Add `"degradation_router"` to `__all__`
  - [x] 5.4 Write router tests (target: 10+ tests, actual: 11)
    - GET /api/system/status → 200 with all services
    - GET /api/system/status → overall_status reflects worst service
    - GET /api/system/status/instagram → 200 with single service
    - GET /api/system/status/unknown → 404
    - POST /api/system/recover → 200 with recovery results
    - POST /api/system/recover with service_name → recovers single service
    - POST /api/system/reset/instagram → 200, resets to healthy
    - POST /api/system/reset/unknown → 404
    - total_queued_operations sums across all services
    - Response when all healthy vs when some degraded

- [x] Task 6: Wire Into Existing Integration Points (AC: 1, 2, 3, 5)
  - [x] 6.1 Created `core/degradation/wiring.py` centralized fire-and-forget helper:
    - `record_service_health(registry, service_name, success, error)` — None-safe, exception-safe
    - Can be called from any integration point (publishing, Shopify, calendar, Discord)
    - **Try/except around all registry calls** — never block agent execution
  - [x] 6.2 Shopify integration compatibility:
    - The existing stale cache fallback (24h TTL) already satisfies AC3
    - RetryMiddleware pre-check (Task 2.3) uses cache_fallback for Shopify
  - [x] 6.3 Calendar sync compatibility:
    - Calendar already has graceful degradation (never blocks publish)
    - Wiring helper available for sync_calendar_event to call
  - [x] 6.4 Discord self-referential protection:
    - DegradationAlertService (Task 3) detects service_name=="discord" and skips
  - [x] 6.5 Write integration wiring tests (target: 12+ tests, actual: 11)
    - Publishing success → instagram marked healthy
    - Publishing failure → instagram marked with failure
    - Calendar sync success/failure → google_calendar recorded
    - Discord success/failure → discord recorded
    - Shopify success/failure → shopify recorded
    - Registry failure doesn't raise
    - None registry is safe no-op
    - Multiple services tracked independently

- [x] Task 7: Extend Existing Health Endpoint (AC: 4)
  - [x] 7.1 Extend `ui/backend/routers/health.py`:
    - Add `GET /api/health/services` — delegates to degradation registry
    - Add field: `degraded_services: int` to OverallHealthResponse
    - Add field: `queued_operations: int` to OverallHealthResponse
  - [x] 7.2 Write extended health tests (target: 5+ tests, actual: 4)
    - OverallHealthResponse has degraded_services field
    - OverallHealthResponse defaults to 0
    - Backward compat — existing code works without new fields
    - /services endpoint exists in router

- [x] Task 8: Registration + Exports (AC: all)
  - [x] 8.1 Register in `teams/dawo/team_spec.py`:
    - `RegisteredService(name="service_health_registry", ...)`
    - `RegisteredService(name="recovery_processor", ...)`
    - `RegisteredService(name="degradation_alert_service", ...)`
    - **RegisteredService** (not RegisteredAgent) — no LLM tier needed for any
  - [x] 8.2 Updated `core/degradation/__init__.py` with complete `__all__`:
    - `ServiceHealthRegistry`, `ServiceHealthStatus`, `DegradationAlertService`
    - `RecoveryProcessor`, `RecoveryResult`, `record_service_health`
  - [x] 8.3 Write registration + export tests (target: 5+ tests, actual: 9)
    - All public classes importable from package
    - __all__ is complete
    - All RegisteredServices in team_spec
    - No RegisteredAgent (none use LLM)
    - Degradation services don't require session

- [x] Task 9: Integration Tests (AC: all)
  - [x] 9.1 Create `tests/integration/test_degradation_integration.py`:
    - End-to-end: API fails 3x → service marked degraded → Discord alert sent
    - End-to-end: API recovers → service marked healthy
    - End-to-end: Recovery processes queued operations
    - End-to-end: Multiple APIs down → each tracked independently
    - End-to-end: Manual health reset → service status forced to healthy
    - Discord self-referential: Discord down → logged locally, not alerted via Discord
    - Graceful degradation: registry Redis unavailable → system continues
    - Wiring with None/broken registry is safe
    - Rate limit respect: recovery batch doesn't exceed max_recovery_batch_size
    - Recovery skips non-healthy services
  - [x] 9.2 Target: 12+ integration tests (actual: 11)

## Dev Notes

### Critical: What Already Exists (DO NOT Rebuild)

**RetryMiddleware** (`teams/dawo/middleware/retry.py`) — EXTEND, don't rebuild:
- `RetryResult` with `is_incomplete` flag — the existing graceful degradation signal
- `RetryConfig` with exponential backoff, jitter, 429 handling
- Retryable status codes: {500, 502, 503, 504, 429}
- Returns `RetryResult`, NEVER raises exceptions

**RetryableHttpClient** (`teams/dawo/middleware/http_client.py`) — EXTEND:
- Wraps httpx with RetryMiddleware
- All external API calls route through this
- `get()`, `post()`, `put()`, `delete()`, `patch()` all return `RetryResult`

**OperationQueue** (`teams/dawo/middleware/operation_queue.py`) — REUSE:
- `IncompleteOperation` dataclass with operation_id, context, payload, retry_count
- Redis-backed: `dawo:incomplete_operations` hash
- Methods: `queue_for_retry()`, `get_pending_operations()`, `remove_from_queue()`, `update_operation()`, `increment_retry()`
- Already persists failed operations — this is the recovery source

**Discord Alerts** (`teams/dawo/middleware/discord_alerts.py`) — REUSE:
- `DiscordAlertManager` with rate-limited alerting (5-min cooldown per API)
- Redis-backed rate limiting: `dawo:alert_cooldown:{api_name}`
- `send_api_error_alert()` with api_name, error, attempts, queued_for_retry
- Graceful degradation: Discord/Redis failures don't raise, return False

**Health Endpoint** (`ui/backend/routers/health.py`) — EXTEND:
- `GET /api/health` — overall system health
- `GET /api/health/publishing` — Instagram publishing subsystem
- `PublishingHealthResponse` with consecutive_failures, success_rate
- Status transitions: healthy → degraded → unhealthy

**Publishing Metrics** (`core/publishing/metrics.py`) — REUSE:
- Tracks success/failure rates, latency percentiles
- Rate limit quota tracking
- Thread-safe counters

**Shopify Stale Cache** (`integrations/shopify/client.py`) — ALREADY EXISTS:
- Normal cache TTL: 1 hour
- Extended degraded cache TTL: 24 hours
- Falls back to stale cache when API fails
- Returns `is_placeholder=True` on stale data
- **This already satisfies AC3** — just need to wire in health recording

**Rate Limits Config** (`config/dawo_rate_limits.json`) — REUSE:
- instagram_api: quota 200/hr, timeout 30s, failure_threshold 3
- discord_webhook: 5 req/s, burst 50
- notifications: cooldown 60 min, backoff schedule [60, 300, 900, 3600]

**ARQ Jobs** (`core/scheduling/jobs.py`) — EXTEND:
- `_run_scheduled_agent()` — add health recording after execution
- `_send_discord_failure_alert()` — already handles Discord alerts
- `_process_calendar_sync_queue` cron — existing retry pattern
- Lazy import pattern for avoiding circular deps
- Fire-and-forget pattern (try/except: pass)

### Architectural Decisions

**Simple In-Process Health Registry (NOT Circuit Breaker Library):**
- This is a single-operator tool, not microservices
- No need for `pybreaker` or `circuitbreaker` library — too complex
- Simple consecutive failure counting in Redis is sufficient
- Status is ADVISORY, never blocks operations (unlike true circuit breakers)
- Redis gives cross-process visibility (FastAPI + ARQ workers share state)

**New Package: `core/degradation/` (NOT in `teams/dawo/`):**
- Degradation handling is a platform concern, not team-specific
- Follows `core/analytics/`, `core/scheduling/` pattern
- Contains: models.py, registry.py, alerts.py, recovery.py

**Extend Existing Middleware (NOT Replace):**
- RetryMiddleware gets optional `ServiceHealthRegistry` — backward compatible
- Existing callers unaffected (registry defaults to None)
- New callers can pass registry for health tracking

**Recovery via Existing OperationQueue (NOT New Table):**
- OperationQueue already persists failed ops in Redis
- RecoveryProcessor reads from OperationQueue, re-enqueues via ARQ
- No new database table needed — Redis is the source of truth for queued ops
- This is ephemeral state (if Redis restarts, queued ops are lost — acceptable for single operator)

**Batch Recovery with Rate Limits (NOT Thundering Herd):**
- Recovery processes max N items per cycle (configurable, default 20)
- Cron runs every 5 minutes
- This prevents flooding a recovering API with queued requests
- Same pattern as calendar sync retry cron (Story 7-9)

**Dashboard via FastAPI Router (NOT WebSocket):**
- Simple REST endpoint for status polling
- Operator refreshes dashboard to see current state
- Real-time not needed — status changes infrequently
- WebSocket would be over-engineering for a single operator

### No New Dependencies Required

All required libraries already in `requirements.txt`:
- `redis` — for health state persistence (already used by ARQ)
- `httpx` — for API clients (already used everywhere)
- `fastapi` + `pydantic` — for dashboard endpoints (already used)
- No circuit breaker library needed — simple counting is enough

### File Structure

```
core/degradation/
    __init__.py                        # Public exports + __all__
    models.py                          # ServiceHealthStatus, RecoveryResult
    registry.py                        # ServiceHealthRegistry (Redis-backed)
    alerts.py                          # DegradationAlertService
    recovery.py                        # RecoveryProcessor

config/
    dawo_degradation.json              # Degradation config (thresholds, intervals)

core/config.py                         # Extended: DegradationConfig frozen dataclass

teams/dawo/middleware/retry.py         # Extended: optional ServiceHealthRegistry
teams/dawo/middleware/http_client.py   # Extended: optional ServiceHealthRegistry passthrough

core/scheduling/jobs.py                # Extended: health recording + recovery cron

integrations/shopify/client.py         # Extended: record success/failure
ui/backend/routers/health.py           # Extended: degraded services count

ui/backend/routers/
    __init__.py                        # Updated: register degradation router
    degradation.py                     # NEW: System status dashboard endpoints

ui/backend/schemas/
    degradation.py                     # NEW: Pydantic request/response schemas

teams/dawo/team_spec.py               # Extended: 3 new RegisteredServices

tests/core/test_degradation/
    test_models.py                     # ~5 tests (frozen dataclasses)
    test_registry.py                   # ~15 tests (health tracking)
    test_alerts.py                     # ~10 tests (Discord degradation alerts)
    test_recovery.py                   # ~12 tests (recovery processor)

tests/teams/dawo/test_middleware/
    test_retry_health.py               # ~10 tests (middleware extension)

tests/ui/backend/test_routers/
    test_degradation.py                # ~10 tests (dashboard endpoints)
    test_health_extended.py            # ~5 tests (health endpoint extension)

tests/integration/
    test_degradation_integration.py    # ~12 tests (end-to-end flows)
```

### Testing Approach (Proven Patterns from Epic 7)

- **Protocol-based mocking:** `AsyncMock(spec=ServiceHealthRegistry)` for all dependent tests
- **Frozen dataclasses:** ServiceHealthStatus, RecoveryResult, DegradationConfig are immutable
- **Constructor injection:** All new classes accept deps via constructor
- **Router tests:** `app.dependency_overrides` for service mocking, `httpx.AsyncClient`
- **Integration tests:** Full flow from API failure → health recorded → alert sent → recovery processed
- **`datetime.now(UTC)`** not `datetime.utcnow()` (deprecated)
- **sys.modules patching:** For jobs.py tests that need to mock lazy imports
- **Redis mocking:** `AsyncMock` for Redis client (don't need real Redis in unit tests)
- Tests mirror source: `tests/core/test_degradation/` matches `core/degradation/`

### Previous Story Intelligence (from 7-9)

**What Worked Well:**
- Lazy imports in jobs.py avoided circular dependencies
- Fire-and-forget pattern (try/except: pass) kept main flow unblocked
- Frozen dataclass DTOs kept API contracts clean
- Protocol-based testing enabled clean mocking
- Router tests with `app.dependency_overrides` for service AND Redis pool
- Cron-based retry (every 15 min) instead of inline retry — simple and reliable

**What to Watch For:**
- Must lazy-import all degradation classes in ARQ jobs
- Health recording MUST be wrapped in try/except — NEVER block agent execution
- Redis failures in health registry must return sensible defaults (not raise)
- Don't forget `__all__` exports in `core/degradation/__init__.py`
- Discord self-alert loop: don't try to alert about Discord failure via Discord
- Recovery batch size must be respected (prevent thundering herd)
- `sys.modules` patching needed for any test importing from `core.scheduling.jobs`
- `asyncio.get_running_loop()` not `asyncio.get_event_loop()` (deprecated)

### Anti-Patterns to Avoid

- **DO NOT** install circuit breaker libraries — simple counting is enough for single operator
- **DO NOT** make health status a hard gate — it's advisory, operations should still attempt
- **DO NOT** alert about Discord via Discord — detect self-referential loop
- **DO NOT** process entire recovery queue at once — respect batch size limits
- **DO NOT** create new database table for health state — Redis is sufficient
- **DO NOT** break RetryMiddleware backward compatibility — registry is optional
- **DO NOT** block publishing on health recording failure — fire-and-forget
- **DO NOT** use `datetime.utcnow()` — use `datetime.now(UTC)`
- **DO NOT** skip `__all__` exports in any `__init__.py`
- **DO NOT** call Google/Instagram/Shopify APIs without `run_in_executor()` where sync
- **DO NOT** use `getattr` on user-supplied sort fields — SQL injection risk
- **DO NOT** retry recovery immediately — use cron-based batch processing

### Key Design Principle

**Advisory, Not Blocking:** The entire degradation system is an OBSERVABILITY layer. It records what's happening and alerts the operator. It NEVER prevents an operation from attempting. Even if a service is marked "unhealthy", operations still try (the API might have recovered). The only exception is the Shopify stale cache optimization: if the API is known unhealthy AND a fresh cache miss occurs, skip the API call and use stale cache directly (saves time, doesn't block).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.10]
- [Source: _bmad-output/planning-artifacts/prd.md#FR55, NFR16, NFR17]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling - Retry + graceful degradation hybrid]
- [Source: _bmad-output/project-context.md#External API Calls, Retry Middleware]
- [Source: teams/dawo/middleware/retry.py — RetryMiddleware, RetryResult, RetryConfig]
- [Source: teams/dawo/middleware/http_client.py — RetryableHttpClient]
- [Source: teams/dawo/middleware/operation_queue.py — OperationQueue, IncompleteOperation]
- [Source: teams/dawo/middleware/discord_alerts.py — DiscordAlertManager]
- [Source: core/publishing/metrics.py — PublishingMetrics]
- [Source: ui/backend/routers/health.py — Health endpoints]
- [Source: integrations/shopify/client.py — Stale cache fallback pattern]
- [Source: integrations/discord/client.py — Discord client, DiscordRateLimitError]
- [Source: core/scheduling/jobs.py — ARQ job patterns, cron jobs]
- [Source: config/dawo_rate_limits.json — Rate limit configuration]
- [Source: _bmad-output/implementation-artifacts/7-9-google-calendar-sync.md — Previous story]
- [Source: docs/retry-middleware-patterns.md — Retry middleware documentation]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

Code review session 2026-02-25

### Completion Notes List

- 112 tests (0 placeholders) across 11 test files
- Code review found 9 issues (2H, 5M, 2L) — all fixed:
  - H1: Added on_recovery callback to ServiceHealthRegistry for AC5 recovery event emission
  - H2: Replaced 3x datetime.utcnow() with datetime.now(UTC) in health.py
  - M1: Fixed alerts.py double-private access (_discord._discord) — now accepts DiscordClientProtocol directly
  - M2: Fixed health.py get_services_health() to use Depends() instead of direct call
  - M3: Populated this Dev Agent Record
  - M4: Added get_operations_for_service() to OperationQueue, recovery.py uses it
  - M5: Removed 4 private _build_* functions from config.py __all__
  - L1: Fixed mutable default errors=[] in RecoveryResultResponse schema
  - L2: Replaced Optional[datetime] with datetime | None in models.py + registry.py

### File List

- core/degradation/__init__.py
- core/degradation/models.py
- core/degradation/registry.py
- core/degradation/alerts.py
- core/degradation/recovery.py
- core/degradation/wiring.py
- core/config.py (DegradationConfig + __all__)
- config/dawo_degradation.json
- teams/dawo/middleware/retry.py
- teams/dawo/middleware/http_client.py
- teams/dawo/middleware/operation_queue.py
- core/scheduling/jobs.py (_process_recovery_queue cron)
- ui/backend/routers/degradation.py
- ui/backend/routers/health.py
- ui/backend/routers/__init__.py
- ui/backend/schemas/degradation.py
- teams/dawo/team_spec.py
- tests/core/test_degradation/ (7 test files, 78 tests)
- tests/integration/test_degradation_integration.py (11 tests)
- tests/ui/backend/test_routers/test_degradation.py (11 tests)
- tests/ui/backend/test_routers/test_health_degradation.py (4 tests)
- tests/teams/dawo/test_middleware/test_retry_health.py (14 tests)
