# Story 7.3: Shopify Sales Attribution

Status: done

## Story

As an **operator**,
I want Shopify sales attributed to content that drove them,
so that I understand revenue impact of each post.

## Acceptance Criteria

1. **AC1 - Order Attribution**: Given a Shopify order is placed, When session contains UTM from Instagram post, Then order revenue is attributed to that post, And attribution includes: order ID, revenue, products purchased
2. **AC2 - Multi-Touch Recording**: Given multiple posts contributed to a sale, When user visited from multiple posts before purchase, Then attribution uses last-touch model (most recent post), And all touchpoints are recorded for analysis
3. **AC3 - Revenue Analytics**: Given attribution data exists, When I view post performance, Then I see: attributed revenue, orders, average order value, And ROI can be calculated (if cost data available)
4. **AC4 - Dashboard Latency**: Given a sale occurs within attribution window, When attribution is calculated, Then revenue is correctly linked to post, And products are categorized (which product lines perform best), And data updates in dashboard within 1 hour of sale

## Tasks / Subtasks

- [x] Task 1: Database models and migration (AC: #1, #2)
  - [x] 1.1 Create `shopify_orders` SQLAlchemy model (order_id, shopify_order_gid, total_price, currency, customer_email, line_items_json, created_at, processed_at)
  - [x] 1.2 Create `order_attributions` SQLAlchemy model (id, shopify_order_id FK, post_id, attribution_type enum[last_touch/multi_touch], revenue_attributed, touchpoint_index, visit_occurred_at, utm_source, utm_medium, utm_campaign, utm_content)
  - [x] 1.3 Create Alembic migration `2026_02_24_001_create_shopify_attribution_tables.py`
  - [x] 1.4 Write model unit tests

- [x] Task 2: Shopify Orders GraphQL client extension (AC: #1, #4)
  - [x] 2.1 Add `get_orders_since()` method to `ShopifyClient` — GraphQL query with `customerJourneySummary { firstVisit { utmParameters { source medium campaign content } occurredAt } lastVisit { utmParameters { source medium campaign content } occurredAt } moments(first: 50) { edges { node { ... on CustomerVisit { utmParameters { source medium campaign content } occurredAt } } } } ready }` + `totalPriceSet { shopMoney { amount currencyCode } }` + `lineItems(first: 50) { edges { node { title quantity variant { id price } product { id handle } } } }`
  - [x] 2.2 Add `get_order_by_id()` method for single order lookup
  - [x] 2.3 Create `ShopifyOrder` frozen dataclass result (NOT the SQLAlchemy model — this is the API response DTO)
  - [x] 2.4 Create `OrderLineItem` frozen dataclass (product_id, variant_id, title, quantity, price)
  - [x] 2.5 Create `OrderAttribution` frozen dataclass for customer journey data (visits with UTM params)
  - [x] 2.6 Write client tests with mocked GraphQL responses

- [x] Task 3: Attribution repository (AC: #1, #2, #3)
  - [x] 3.1 Create `AttributionRepository` with constructor injection (AsyncSession)
  - [x] 3.2 Implement `save_order()` — upsert by shopify_order_gid (idempotent)
  - [x] 3.3 Implement `save_attributions()` — batch insert for all touchpoints of one order
  - [x] 3.4 Implement `get_attributions_by_post_id()` — all attributions for a post
  - [x] 3.5 Implement `get_attributions_by_post_ids()` — batch query (IN clause, prevents N+1)
  - [x] 3.6 Implement `get_revenue_summary()` — SQL aggregation: total_revenue, order_count, avg_order_value for a post
  - [x] 3.7 Implement `get_revenue_by_post_ids()` — batch revenue summary
  - [x] 3.8 Implement `get_top_products()` — GROUP BY product from line_items_json, ordered by revenue
  - [x] 3.9 Write repository tests

- [x] Task 4: Attribution service (AC: #1, #2)
  - [x] 4.1 Create `AttributionService` with constructor injection (AttributionRepository, UTMRepository, AttributionConfig)
  - [x] 4.2 Implement `process_order()` — core attribution logic:
    - Extract `lastVisit.utmParameters` for last-touch attribution
    - Extract all `moments` CustomerVisit nodes for multi-touch recording
    - Match UTM `content` field to `short_links.post_id` via UTMRepository
    - Save order + all attributions (last_touch flagged, others as multi_touch)
    - Return `AttributionResult` frozen dataclass
  - [x] 4.3 Implement `process_orders_batch()` — batch processing with partial failure handling (same pattern as `InstagramMetricsCollector.collect_batch()`)
  - [x] 4.4 Implement attribution window filtering: skip orders older than `default_attribution_window_days` (from config, default 30)
  - [x] 4.5 Write service tests with mocked repository and UTM repository

- [x] Task 5: Revenue analytics service (AC: #3)
  - [x] 5.1 Create `RevenueAnalyticsService` with constructor injection (AttributionRepository, ClickAnalyticsService, MetricsQueryService)
  - [x] 5.2 Implement `get_post_revenue()` — returns `PostRevenueResult`: attributed_revenue, order_count, avg_order_value, top_products
  - [x] 5.3 Implement `get_revenue_comparison()` — post revenue vs average (same pattern as `ClickAnalyticsService.get_comparison()`)
  - [x] 5.4 Implement `get_roi_estimate()` — if cost data available: (revenue - cost) / cost
  - [x] 5.5 Implement `get_combined_analytics()` — merges metrics (7-1) + clicks (7-2) + revenue (7-3) into unified `PostAnalyticsSummary`
  - [x] 5.6 Write analytics tests

- [x] Task 6: Webhook endpoint + polling job (AC: #4)
  - [x] 6.1 Create `POST /api/webhooks/shopify/orders-paid` endpoint with HMAC signature verification
  - [x] 6.2 Fire-and-forget: endpoint returns 200 immediately, processes attribution via `asyncio.create_task()`
  - [x] 6.3 Create `poll_shopify_orders` ARQ job as fallback — queries orders created since last poll, processes any unattributed orders
  - [x] 6.4 Schedule polling job hourly via ARQ cron (same pattern as metrics collection in `core/scheduling/jobs.py`)
  - [x] 6.5 Write webhook and job tests

- [x] Task 7: Configuration and registration (AC: all)
  - [x] 7.1 Add `attribution` section to `config/dawo_analytics.json`: `webhook_secret`, `polling_interval_hours`, `attribution_window_days`, `max_touchpoints`
  - [x] 7.2 Create `AttributionConfig` frozen dataclass in `core/config.py`
  - [x] 7.3 Register 3 services in `teams/dawo/team_spec.py` as `RegisteredService` (no LLM tier): `AttributionService`, `RevenueAnalyticsService`, `AttributionRepository`
  - [x] 7.4 Update `core/analytics/__init__.py` with complete `__all__` exports
  - [x] 7.5 Write config validation tests

- [x] Task 8: Integration tests (AC: all)
  - [x] 8.1 End-to-end: order webhook → attribution → revenue query
  - [x] 8.2 Multi-touch scenario: 3 visits from different posts → last-touch wins, all recorded
  - [x] 8.3 No-UTM scenario: order without UTM params → no attribution (no error)
  - [x] 8.4 Attribution window: order outside window → skipped
  - [x] 8.5 Polling fallback: missed webhook → polling catches the order

## Dev Notes

### Shopify GraphQL API — Order Attribution Query

The `Order` object has a `customerJourneySummary` field containing:
- `firstVisit` → `CustomerVisit` with `utmParameters { source medium campaign content term }` and `occurredAt`
- `lastVisit` → `CustomerVisit` (same structure) — **USE THIS FOR LAST-TOUCH ATTRIBUTION**
- `moments(first: N)` → `CustomerMomentConnection` of `CustomerVisit` nodes — **USE FOR MULTI-TOUCH RECORDING**
- `ready` → `Boolean!` — if `false`, attribution data is still processing. **Must check this flag and skip/retry if not ready.**
- `daysToConversion` → `Int` — days between first visit and order

**Critical**: `customerJourneySummary.ready` must be `true` before trusting attribution data. If `false` on webhook, queue for retry via polling job.

**GraphQL Query Pattern** (extend existing `ShopifyClient`):
```graphql
query GetOrdersWithAttribution($first: Int!, $query: String) {
  orders(first: $first, query: $query, sortKey: CREATED_AT) {
    edges {
      node {
        id
        name
        createdAt
        totalPriceSet { shopMoney { amount currencyCode } }
        lineItems(first: 50) {
          edges {
            node {
              title
              quantity
              variant { id price }
              product { id handle }
            }
          }
        }
        customerJourneySummary {
          ready
          daysToConversion
          firstVisit {
            occurredAt
            utmParameters { source medium campaign content }
          }
          lastVisit {
            occurredAt
            utmParameters { source medium campaign content }
          }
          moments(first: 50) {
            edges {
              node {
                ... on CustomerVisit {
                  occurredAt
                  utmParameters { source medium campaign content }
                }
              }
            }
          }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

Filter: `query: "created_at:>'2026-02-23' financial_status:paid"`

### Attribution Matching Logic

1. Extract `lastVisit.utmParameters.content` → this contains the `post_id` (set by Story 7-2's `generate_post_short_link()`)
2. Verify match: query `short_links` table WHERE `post_id = utm_content` to confirm the link belongs to our system
3. If no match → order came from external source, skip attribution (no error)
4. If match → create `OrderAttribution` with `attribution_type = "last_touch"`, `revenue_attributed = order.totalPriceSet.shopMoney.amount`
5. For all `moments` CustomerVisit nodes with matching UTM content → create `OrderAttribution` with `attribution_type = "multi_touch"`, `revenue_attributed = 0` (revenue only on last-touch)

### Webhook HMAC Verification

Shopify signs webhooks with `X-Shopify-Hmac-Sha256` header using the webhook secret. Verify:
```python
import hmac, hashlib, base64
computed = base64.b64encode(
    hmac.new(secret.encode(), body, hashlib.sha256).digest()
).decode()
return hmac.compare_digest(computed, header_hmac)
```
**CRITICAL**: Use `hmac.compare_digest()` for timing-safe comparison. Never use `==`.

### Project Structure Notes

**New files to create:**
```
core/analytics/
├── attribution_models.py    # ShopifyOrderRecord, OrderAttributionRecord SQLAlchemy models
├── attribution_repository.py # AttributionRepository (data access)
├── attribution_service.py   # AttributionService (order processing + UTM matching)
└── revenue_analytics.py     # RevenueAnalyticsService (revenue queries + combined analytics)

integrations/shopify/
└── client.py                # MODIFY: Add get_orders_since(), get_order_by_id()

ui/backend/routers/
└── webhooks.py              # NEW: POST /api/webhooks/shopify/orders-paid

core/config.py               # MODIFY: Add AttributionConfig dataclass
config/dawo_analytics.json   # MODIFY: Add attribution section
core/scheduling/jobs.py      # MODIFY: Add poll_shopify_orders job
teams/dawo/team_spec.py      # MODIFY: Register 3 new services
core/analytics/__init__.py   # MODIFY: Update __all__ exports

migrations/versions/
└── 2026_02_24_001_create_shopify_attribution_tables.py

tests/core/test_analytics/
├── test_attribution_models.py
├── test_attribution_repository.py
├── test_attribution_service.py
└── test_revenue_analytics.py

tests/integrations/shopify/
└── test_client.py           # MODIFY: Add attribution query tests

tests/ui/backend/test_routers/
└── test_webhooks.py

tests/integration/
└── test_shopify_attribution_e2e.py
```

**Alignment**: Follows `core/analytics/` organization (same as 7-1 models, repository, collector, query). New router in `ui/backend/routers/` (same as 7-2 redirect.py).

### Existing Code to Reuse (DO NOT REINVENT)

| Component | Location | Reuse For |
|-----------|----------|-----------|
| `ShopifyClient` | `integrations/shopify/client.py` | Extend with order queries (uses RetryableHttpClient + GraphQL) |
| `UTMParams` | `integrations/shopify/utm.py` | UTM field names match exactly what we store |
| `UTMRepository.get_by_post_id()` | `core/analytics/utm_repository.py` | Verify UTM content → post_id mapping |
| `ShortLink.post_id` | `core/analytics/utm_models.py` | Link short_links to posts for attribution matching |
| `ClickAnalyticsService` | `core/analytics/click_analytics.py` | Import for combined analytics (clicks + revenue) |
| `MetricsQueryService` | `core/analytics/metrics_query.py` | Import for combined analytics (metrics + revenue) |
| `AnalyticsConfig` | `core/config.py` | Pattern for `AttributionConfig` frozen dataclass |
| `CollectionResult` pattern | `core/analytics/metrics_collector.py` | Pattern for `AttributionResult` frozen dataclass |
| Fire-and-forget pattern | `core/analytics/utm_service.py:resolve_and_track()` | Same pattern for webhook → `asyncio.create_task()` |
| `_schedule_post_metrics()` | `core/scheduling/jobs.py` | Pattern for ARQ polling job registration |
| `RegisteredService` | `teams/dawo/team_spec.py` | Registration pattern (no LLM tier) |
| Batch query pattern | `utm_repository.py:get_clicks_by_post_ids()` | Single IN query for `get_attributions_by_post_ids()` |

### Critical Patterns from Stories 7-1 and 7-2

**From Story 7-1 (88 tests):**
- Snapshot-delta pattern: store raw values, compute aggregates at query time
- `RegisteredService` (not RegisteredAgent) — no LLM tier
- Batch `get_by_media_ids()` uses single IN query (no N+1)
- Fire-and-forget scheduling (failures don't block publishing)
- Rate limit awareness: budget API calls

**From Story 7-2 (94 tests):**
- Fire-and-forget click recording via `asyncio.create_task()`
- GDPR: SHA-256 hash IPs, no cookies, no fingerprinting
- Reused existing `UTMParams` (zero duplication)
- Router at `/l/{code}` (root level, not under `/api/`)
- Device categorization without external library
- Cross-service CTR: integrates MetricsQueryService for impressions

**Carry forward:**
- All result types are frozen dataclasses
- Constructor injection on everything
- Protocol-based interfaces for testability
- Partial failure handling in batch operations (never fail-all on one error)
- Tests mirror source: `tests/core/test_analytics/` matches `core/analytics/`

### Anti-Patterns to Avoid

- **NO direct Shopify API calls** — all go through `ShopifyClient` which uses `RetryableHttpClient`
- **NO `getattr()` on user-supplied fields** — SQL injection risk (caught in 6-9)
- **NO in-memory filtering** — all aggregations (revenue, order count, top products) in SQL
- **NO N+1 queries** — always batch with IN clause
- **NO raw IP storage** — if any customer data needed, hash it (GDPR pattern from 7-2)
- **NO hardcoded model names** — use tier system (though this story has no LLM, only RegisteredService)
- **NO duplicate UTMParams** — reuse from `integrations/shopify/utm.py`
- **NO blocking webhook processing** — return 200 immediately, process async

### Testing Standards

- TDD: red-green-refactor cycle
- Target: ~80-100 tests across 8 test files
- Mocking: `AsyncMock(spec=AttributionRepository)` with Protocol pattern
- Integration tests: full order → attribution → revenue query flow
- Edge cases: no UTM, expired window, `ready=false`, duplicate orders (idempotent upsert)
- Test data: use `create_test_order()` factory functions (frozen dataclasses)

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 7, Story 7.3]
- [Source: _bmad-output/planning-artifacts/architecture.md — Error Handling: Retry + Graceful Degradation]
- [Source: _bmad-output/implementation-artifacts/7-1-instagram-engagement-metrics-collection.md — Patterns]
- [Source: _bmad-output/implementation-artifacts/7-2-utm-click-through-tracking.md — UTM/Click Integration]
- [Source: integrations/shopify/client.py — Existing ShopifyClient with GraphQL + cache]
- [Source: core/analytics/utm_repository.py — UTM matching queries]
- [Source: core/analytics/click_analytics.py — Combined analytics pattern]
- [Source: core/scheduling/jobs.py — ARQ job scheduling pattern]
- [Source: Shopify GraphQL Admin API — CustomerJourneySummary, CustomerVisit, UTMParameters objects]
- [Source: Shopify Webhooks — ORDERS_PAID topic with HMAC verification]
- [Source: docs/project-context.md — Registration rules, DI patterns, anti-patterns]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
- FastAPI resolves dependencies before handler body — need DI overrides for 401 tests too
- RuntimeWarnings for `session.add()` / `session.add_all()` are benign (sync methods on AsyncMock)

### Completion Notes List
- 102 tests total across 8 test files (all passing)
- Tasks 1-3: DB models (22 tests) + ShopifyClient extension (17 tests) + Repository (15 tests)
- Task 4: AttributionService with last-touch + multi-touch attribution (13 tests)
- Task 5: RevenueAnalyticsService with combined analytics merging 7-1/7-2/7-3 (13 tests)
- Task 6: Webhook HMAC verification + fire-and-forget + ARQ polling job (10 tests)
- Task 7: AttributionConfig, JSON config, 3 RegisteredService in team_spec, __init__.py exports (6 tests)
- Task 8: E2E integration tests covering all 5 scenarios (6 tests)
- Pulled Task 7.1-7.2 (AttributionConfig) forward as dependency for Task 4

### File List
**New files:**
- `core/analytics/attribution_models.py` — SQLAlchemy models (ShopifyOrderRecord, OrderAttributionRecord, AttributionType)
- `core/analytics/attribution_repository.py` — Data access with batch queries, SQL aggregations
- `core/analytics/attribution_service.py` — Core attribution logic (last-touch + multi-touch)
- `core/analytics/revenue_analytics.py` — Revenue analytics, ROI, combined analytics
- `integrations/shopify/orders.py` — Frozen dataclass DTOs (ShopifyOrder, OrderLineItem, CustomerVisit, OrderAttribution)
- `ui/backend/routers/webhooks.py` — POST /api/webhooks/shopify/orders-paid + poll_shopify_orders
- `migrations/versions/2026_02_24_001_create_shopify_attribution_tables.py` — Alembic migration
- `tests/core/test_analytics/test_attribution_models.py` — 22 tests
- `tests/core/test_analytics/test_attribution_repository.py` — 15 tests
- `tests/core/test_analytics/test_attribution_service.py` — 13 tests
- `tests/core/test_analytics/test_revenue_analytics.py` — 13 tests
- `tests/core/test_analytics/test_attribution_config.py` — 6 tests
- `tests/integrations/shopify/test_client.py` — 17 tests
- `tests/ui/backend/test_routers/test_webhooks.py` — 10 tests
- `tests/integration/test_shopify_attribution_e2e.py` — 6 tests

**Modified files:**
- `integrations/shopify/client.py` — Added get_orders_since(), get_order_by_id(), GraphQL queries
- `integrations/shopify/__init__.py` — Added lazy imports + __all__ for orders DTOs (ShopifyOrder, OrderLineItem, CustomerVisit, OrderAttribution)
- `core/config.py` — Added AttributionConfig frozen dataclass, _build_attribution_config(), updated Config and __all__
- `config/dawo_analytics.json` — Added attribution section
- `core/analytics/__init__.py` — Updated with all Story 7-3 exports
- `core/analytics/revenue_analytics.py` — Added Optional[Any] type hints to constructor params
- `core/scheduling/jobs.py` — Added _run_shopify_attribution_poll ARQ job, cron schedule, __all__ export
- `teams/dawo/team_spec.py` — Registered 3 services: AttributionRepository, AttributionService, RevenueAnalyticsService
- `ui/backend/routers/__init__.py` — Added webhook_router import/export

### Code Review Fixes Applied
1. **[CRITICAL]** Fixed `shop_domain=` → `store_domain=` in `_run_shopify_attribution_poll` (jobs.py:518) — would TypeError at runtime
2. **[HIGH]** Registered `webhook_router` in `ui/backend/routers/__init__.py` — was unmounted
3. **[HIGH]** Added ARQ `cron()` entry for hourly Shopify polling (was `cron_jobs = []`)
4. **[MEDIUM]** Added `Optional[Any]` type hints to `RevenueAnalyticsService.__init__` optional params
5. **[MEDIUM]** Added `_run_shopify_attribution_poll` to `__all__` in jobs.py
6. **[MEDIUM]** Updated story File List with 3 missing modified files
7. **[LOW]** Added orders DTOs to `integrations/shopify/__init__.py` lazy imports + `__all__`
