# Epic 7 Preparation Tasks

**Created:** 2026-02-19
**Epic:** 7 - Analytics & System Operations
**Status:** Pre-implementation

---

## Carryover from Epic 6 Retrospective

### Process Improvements (Priority: High)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Expand pre-submission checklist (N+1, security, registration) | Dev Team | **Done** | [docs/pre-submission-checklist.md](../../docs/pre-submission-checklist.md) -- added sections 8 (N+1), 9 (Security), 10 (Registration), Epic 6 issues |
| 2 | Add deprecation linting to CI | Charlie | **Dropped** | Carried 3 epics. Problem solved via habit. `datetime.utcnow()` not found in any Epic 6 code. |
| 3 | Document hybrid regex+LLM pattern | Charlie | **Done** | [docs/hybrid-regex-llm-pattern.md](../../docs/hybrid-regex-llm-pattern.md) -- architecture, confidence scoring, cost analysis, reuse guide |
| 4 | Document RegisteredAgent vs RegisteredService usage guide | Charlie | **Done** | [docs/registered-agent-vs-service.md](../../docs/registered-agent-vs-service.md) |
| 5 | Add security review step for user-input SQL/ORM stories | Dana | **Done** | Added as checklist section 9. |

### Technical Debt (Priority: Medium)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | WebSocket event wiring review | Dev Team | Pending | Carried from Epic 4 -> 5 -> 6 -> 7 |
| 2 | Increase integration test coverage on 6-9, 6-10 | QA | Pending | Unit coverage is strong |
| 3 | RegulatoryEventEmitter documentation | Dev Team | **Done** | [docs/regulatory-event-emitter.md](../../docs/regulatory-event-emitter.md) -- 18 event types, 7 producers, architecture, usage guide |

---

## Epic 7 Specific Preparation

### Research Tasks (Critical - Before Epic Starts)

| # | Task | Owner | Status | Research Doc |
|---|------|-------|--------|-------------|
| 1 | Instagram Graph API insights endpoints | Dev Team | **Done** | [instagram-graph-api-insights.md](../../docs/research/instagram-graph-api-insights.md) |
| 2 | UTM tracking strategy and link shortening | Dev Team | **Done** | [utm-tracking-strategy.md](../../docs/research/utm-tracking-strategy.md) |
| 3 | Shopify webhook setup for order attribution | Charlie | **Done** | [shopify-webhook-attribution.md](../../docs/research/shopify-webhook-attribution.md) |
| 4 | ARQ job queue patterns for agent scheduling | Charlie | **Done** | [arq-job-queue-patterns.md](../../docs/research/arq-job-queue-patterns.md) |
| 5 | Google Calendar API OAuth2 flow | Dev Team | **Done** | [google-calendar-api.md](../../docs/research/google-calendar-api.md) |

### Research Tasks (Parallel - During Early Stories)

| # | Task | Owner | Status | Research Doc |
|---|------|-------|--------|-------------|
| 6 | Design post-publish scoring algorithm weights | Dev Team | Pending | At Story 7-4 start |
| 7 | Plan feedback loop data requirements (min post count) | Alice | Pending | At Story 7-5 start |
| 8 | Evaluate cron/schedule libraries compatible with ARQ | Charlie | **Done** | Included in ARQ research -- `cron_expr_to_arq_kwargs()` converter needed |
| 9 | Create test fixture strategy for analytics data | Dana | Pending | At Story 7-1 start |

---

## Key Technical Decisions

### Decisions Made

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Instagram metrics endpoint | `/{media-id}/insights` edge | Full metric set: reach, saves, shares, impressions |
| 2 | Metrics collection strategy | Snapshot at T+1h, T+24h, T+48h, T+7d | API returns lifetime cumulative; delta computed at query time |
| 3 | Link shortening | Custom FastAPI `/l/{code}` redirect | Zero deps, full data ownership, GDPR-compliant |
| 4 | Click tracking approach | Three layers: custom redirect + Shopify native + GA4 | Each serves different purpose |
| 5 | Shopify attribution webhook | `orders/paid` (not `orders/create`) | Only confirmed revenue |
| 6 | Attribution model | Last-touch | Story 7.3 spec; parse `utm_content` from `landing_site` |
| 7 | Attribution windows | 30d (Instagram DTC), 90d (B2B email), 7d (Stories) | Industry standard per channel |
| 8 | Job queue | ARQ (already in use) | Async-native, Redis-backed, existing patterns in `core/scheduling/` |
| 9 | Cron parsing | Custom `cron_expr_to_arq_kwargs()` | Bridge JSON config `schedule_cron` → ARQ `cron()` |
| 10 | Agent scheduling worker | Separate worker from publishing | Different timeout/concurrency profiles |
| 11 | Google Calendar tokens | Separate `calendar_token.json` | Doesn't break existing Gmail integration |
| 12 | Calendar async wrapping | `asyncio.run_in_executor()` | Same proven pattern as Gmail (Story 5-4) |
| 13 | Calendar webhooks | Skip Phase 1 | One-directional sync; bidirectional adds complexity |
| 14 | Deprecated metric | Replace `engagement` with `total_interactions` | Deprecated in Graph API v18.0+ |

### Decisions Pending (Verify at Story Start)

| # | Decision | Options | When to Decide |
|---|----------|---------|---------------|
| 1 | Instagram `instagram_manage_insights` scope | Already approved vs. needs re-auth | Story 7-1 start -- verify via debug_token |
| 2 | Graph API version upgrade (v19.0 → v21.0) | Upgrade now vs. keep v19.0 | Story 7-1 start -- check deprecation timeline |
| 3 | Post-publish scoring weights | Engagement-heavy vs. revenue-heavy | Story 7-4 start -- depends on Stories 7-1 through 7-3 data |
| 4 | Feedback loop minimum post count | 50 vs. 100 scored posts | Story 7-5 start -- depends on data volume |
| 5 | Shopify plan (Standard vs. Plus) | **Decided: Basic plan** | `landing_site` parsing confirmed. No `customerJourneySummary` available. |

---

## New Dependencies

### Required (add to requirements.txt)

```
# Story 7-6: Agent scheduling (already present)
arq>=0.25.0
redis>=5.0.0

# Story 7-2: UTM click tracking (optional)
user-agents>=2.2.0    # User-agent parsing for device breakdown
```

### Infrastructure Requirements

```
# Redis (already required for ARQ publishing)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Shopify webhook endpoint must be publicly accessible (HTTPS)
# Google Calendar API must be enabled in Google Cloud Console
```

### Environment Variables

```bash
# Story 7-3: Shopify webhook (NEW)
SHOPIFY_WEBHOOK_SECRET=whsec_xxxxx    # Different from SHOPIFY_ACCESS_TOKEN

# Story 7-9: Google Calendar (reuses existing OAuth client)
# No new env vars -- uses credentials/calendar_token.json
```

### Google Cloud Console Setup

```
1. APIs & Services > Library > Enable "Google Calendar API"
2. Run scripts/authorize_calendar.py for initial token
```

---

## Epic 7 Stories Overview

| Story | Title | Key Dependencies | New Tech |
|-------|-------|-----------------|----------|
| 7-1 | Instagram Engagement Metrics Collection | Existing Instagram client | `/insights` edge, snapshot scheduling |
| 7-2 | UTM Click-Through Tracking | FastAPI, SQLAlchemy | Custom redirect endpoint, short links |
| 7-3 | Shopify Sales Attribution | Shopify webhooks | HMAC verification, `landing_site` parsing |
| 7-4 | Post-Publish Quality Scoring | 7-1, 7-2, 7-3 data | Scoring algorithm, predicted vs. actual |
| 7-5 | Performance Feedback Loop | 7-4 scores (100+ posts) | Correlation analysis, weight adjustment |
| 7-6 | Agent Schedule Configuration | ARQ, Redis | `cron_expr_to_arq_kwargs()`, worker settings |
| 7-7 | Manual Team/Agent Triggers | 7-6 foundation | FastAPI trigger API, `enqueue_job()` |
| 7-8 | Execution Logs & Status Dashboard | 7-6, 7-7 | `JobExecutionLog` model, React dashboard |
| 7-9 | Google Calendar Sync | Google Calendar API | OAuth2, event CRUD, batch operations |
| 7-10 | Graceful API Degradation | All integrations | Circuit breaker, queue-and-retry, cached fallback |

### Dependency Chains

```
Analytics:   7-1 → 7-2 → 7-3 → 7-4 → 7-5
Operations:  7-6 → 7-7 → 7-8
Standalone:  7-9, 7-10
```

---

## Pre-Implementation Verification Checklists

### Story 7-1 (Instagram Engagement Metrics)
- [ ] Verify `instagram_manage_insights` scope on current token: `GET /debug_token?input_token={token}`
- [ ] Test `/{media-id}/insights` with a recent post to confirm metrics return
- [ ] Check if deprecated `engagement` metric is still used in `integrations/instagram/client.py`
- [ ] Confirm Graph API version (v19.0 → consider v21.0 upgrade)
- [ ] Estimate rate budget: current usage + metrics collection fits within 200 calls/hour

### Story 7-2 (UTM Click-Through Tracking)
- [x] Verify existing `integrations/shopify/utm.py` generates correct UTM params -- confirmed: `utm_source=instagram, utm_medium=post, utm_campaign={content_type}, utm_content={post_id}`
- [ ] Confirm `/l/{code}` redirect hosted on FastAPI backend (not Shopify domain). Store domain: `dawochaga.myshopify.com`
- [ ] Check if GA4 is already configured on Shopify store

### Story 7-3 (Shopify Sales Attribution)
- [ ] Get Shopify webhook signing secret from admin (API secret: `shpss_...` -- may be this)
- [x] Verify Shopify plan → **Basic** ($348/yr). No `customerJourneySummary`. Use `landing_site` parsing.
- [ ] Place a test order with UTM params and inspect `landing_site` field via API
- [ ] Confirm FastAPI backend is publicly accessible (HTTPS) for webhook delivery
- [ ] Obtain Admin API access token (legacy custom apps deprecated Jan 2026; use Dev Dashboard OAuth or `shopify app dev` CLI)

### Story 7-6 (Agent Schedule Configuration)
- [ ] Verify Redis is running and accessible
- [ ] Check existing `core/scheduling/` ARQ setup
- [ ] List all scanner configs with `schedule_cron` fields
- [ ] Confirm `arq` and `redis` packages are installed

### Story 7-9 (Google Calendar Sync)
- [ ] Enable Google Calendar API in Google Cloud Console
- [ ] Run `scripts/authorize_calendar.py` to generate `calendar_token.json`
- [ ] Verify `run_in_executor()` pattern works (test with existing Gmail credential manager)

---

## Pattern Reuse from Previous Epics

| Pattern | Source Epic | Reuse in Epic 7 |
|---------|-----------|-----------------|
| Harvester Framework | Epic 2 | Story 7-1 (metrics collection pipeline) |
| RetryMiddleware | Epic 1 | All external API calls (Instagram, Shopify, Google Calendar) |
| Protocol-based DI | Epic 3 | All new services and clients |
| `asyncio.run_in_executor()` | Epic 5 (Story 5-4) | Story 7-9 (Google Calendar API, synchronous) |
| OAuth2 credential management | Epic 5 (Story 5-4) | Story 7-9 (reuse GmailCredentialsManager pattern) |
| Discord notifications | Epic 4 | Stories 7-6, 7-10 (failure alerts, recovery notices) |
| React dashboard | Epic 5, 6 | Story 7-8 (execution logs UI) |
| FastAPI routers | Epic 5, 6 | Stories 7-2, 7-3, 7-7, 7-8 |
| ARQ job queue | Epic 4 | Stories 7-6, 7-7 (extend existing `core/scheduling/`) |
| UTM parameter generation | Epic 3, 5 | Story 7-2 (extend existing UTM modules) |
| RegulatoryEventEmitter | Epic 6 | Story 7-5 (may inform analytics event pipeline) |

---

## Definition of Ready for Epic 7

- [x] All "High" priority carryover tasks completed (checklist expansion, RegisteredAgent docs, security review)
- [x] All 5 critical research tasks completed with decision documents
- [x] Key technical decisions documented (14 decided, 5 pending verification)
- [x] New dependency list identified (minimal -- `user-agents` optional)
- [x] Environment variable requirements documented (`SHOPIFY_WEBHOOK_SECRET`)
- [ ] Pre-implementation verification checklists (run at story start)
- [x] Hybrid regex+LLM pattern documented (carryover #3)
- [x] RegulatoryEventEmitter documentation (tech debt #3)

---

## Notes

- Epic 7 has two distinct domains: Analytics (7-1 through 7-5) and Operations (7-6 through 7-10)
- Analytics chain has tight coupling -- each story builds on previous
- Story 7-5 (feedback loop) requires 100+ scored posts -- may need synthetic test data
- Story 7-10 (graceful degradation) overlaps with Epic 1's retry middleware -- Elena's suggestion to start it early has merit
- ARQ is already partially in use for publishing (Epic 4) -- agent scheduling extends, not replaces
- Google Calendar integration is structurally identical to Gmail integration (Story 5-4) -- expect similar velocity
- Shopify store domain: `dawochaga.myshopify.com`, store URL: `https://dawochaga.no` (verify)
- Shopify API version in existing client: `2024-01` -- consider upgrade at Story 7-3 start
- Shopify legacy custom apps deprecated Jan 2026. Existing "Pairy" app has masked token (can rotate). Dev Dashboard app "dawo.eco" needs OAuth flow for token.
- Shopify MCP (`shopify-mcp-server`) needs `SHOPIFY_ACCESS_TOKEN` + `MYSHOPIFY_DOMAIN` env vars -- defer setup to Story 7-3

---

*Created: 2026-02-19*
*Based on: Epic 6 Retrospective action items + Epic 7 preparation research*
