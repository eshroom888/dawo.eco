# Story 7.7: Manual Team/Agent Triggers

Status: complete

## Story

As an operator,
I want to manually trigger agents or teams on-demand,
so that I can run tasks immediately when needed without waiting for scheduled execution.

## Acceptance Criteria

1. **AC1 - Agent List with Run Now:** When viewing the agent/team list, I see each agent with a "Run Now" button and last execution status (success/failed/incomplete/running/never_run).

2. **AC2 - Immediate Execution:** When I click "Run Now" and the agent is not already running, it executes immediately via ARQ job queue. Execution appears in logs. The button shows "Running..." state until completion.

3. **AC3 - Team Trigger:** When I trigger a "team" (a logical group of agents), all team agents execute in configured dependency order. Team status shows overall progress (e.g., "2/5 complete").

4. **AC4 - Already Running Guard:** When I try to trigger an agent that is already running, I see a warning "Agent already running" and can choose to: (a) queue for next execution after current run completes, or (b) cancel the request.

5. **AC5 - Parameter Overrides:** When I need to trigger with custom parameters (e.g., a scanner with custom keywords), I can override default config for this run only. The override is logged in the audit trail but does NOT change the saved schedule config.

## Tasks / Subtasks

- [x] Task 1: Manual Trigger Service Layer (AC: 2, 3, 4, 5)
  - [x] 1.1 Create `ManualTriggerService` in `core/scheduling/manual_trigger_service.py`
    - Constructor: `AgentScheduleRepository`, `AgentSchedulerConfig`
    - `trigger_agent(agent_name: str, triggered_by: str = "operator", config_overrides: dict | None = None) -> TriggerResult`
      - Validates agent_name against `AGENT_RUNNERS` registry keys (import from jobs.py)
      - Checks if agent is currently running (`last_run_status == "running"`)
      - If running: returns `TriggerResult(status="already_running", ...)`
      - If not running: sets `last_run_status = "running"`, `last_run_at = now`, returns `TriggerResult(status="queued", job_id=...)`
      - Logs override in audit trail if `config_overrides` provided (field_changed="manual_trigger", new_value=JSON of overrides)
      - Does NOT actually enqueue ARQ job — returns result with info for the router to enqueue
    - `trigger_team(team_name: str, triggered_by: str = "operator") -> TeamTriggerResult`
      - Resolves team to ordered list of agents using `TEAM_DEFINITIONS` dict
      - For each agent in dependency order: calls `trigger_agent()` sequentially
      - Tracks overall progress: `completed`, `queued`, `skipped_running`, `failed`
      - Returns `TeamTriggerResult` with per-agent results
    - `queue_after_current(agent_name: str, triggered_by: str = "operator") -> TriggerResult`
      - For already-running agents: marks as "queued" in a pending-triggers store (in-memory dict, not DB — ephemeral)
      - When `_run_scheduled_agent` completes, it checks pending triggers and re-enqueues
    - `get_triggerable_agents() -> list[TriggerableAgentDTO]`
      - Returns all agents from `AGENT_RUNNERS.keys()` with their current schedule status
      - Enriches with display_name, last_run_status, last_run_at from schedule DB
    - `get_teams() -> list[TeamDTO]`
      - Returns all defined teams with their agent lists
  - [x] 1.2 Write service tests (target: 25+ tests)
    - Trigger available agent → status "queued"
    - Trigger running agent → status "already_running"
    - Queue after current run
    - Team trigger with dependency ordering
    - Team trigger with one agent already running (partial success)
    - Config override audit logging
    - Get triggerable agents merges registry + schedule DB
    - Invalid agent name rejection

- [x] Task 2: DTOs for Manual Triggering (AC: 1, 2, 3, 4, 5)
  - [x] 2.1 Add to `core/scheduling/dtos.py`:
    - `TriggerResult` frozen dataclass:
      - `agent_name: str`
      - `status: str` — "queued" / "already_running" / "failed" / "not_found"
      - `job_id: str | None` — ARQ job ID once enqueued
      - `triggered_at: datetime`
      - `triggered_by: str`
      - `config_overrides: dict | None`
      - `message: str` — human-readable status message
    - `TeamTriggerResult` frozen dataclass:
      - `team_name: str`
      - `agent_results: list[TriggerResult]`
      - `total: int`
      - `queued: int`
      - `skipped_running: int`
      - `failed: int`
    - `TriggerableAgentDTO` frozen dataclass:
      - `agent_name: str`
      - `display_name: str`
      - `description: str | None`
      - `last_run_status: str | None`
      - `last_run_at: datetime | None`
      - `last_run_duration_seconds: float | None`
      - `is_running: bool`
      - `schedule_cron: str | None` — for reference
      - `next_scheduled_run: datetime | None`
    - `TeamDTO` frozen dataclass:
      - `team_name: str`
      - `display_name: str`
      - `agents: list[str]` — ordered agent names
      - `description: str`
  - [x] 2.2 Write DTO tests (target: 8+ tests covering frozen immutability, defaults)

- [x] Task 3: Team Definitions Registry (AC: 3)
  - [x] 3.1 Create `TEAM_DEFINITIONS` dict in `core/scheduling/manual_trigger_service.py`
    ```python
    TEAM_DEFINITIONS: dict[str, dict] = {
        "regulatory_monitors": {
            "display_name": "Regulatory Monitors",
            "description": "All regulatory scanning agents",
            "agents": ["health_claims_monitor", "novel_food_monitor", "mattilsynet_monitor"],
        },
        "analytics_pipeline": {
            "display_name": "Analytics Pipeline",
            "description": "Full analytics chain: attribution → scoring → feedback",
            "agents": ["shopify_attribution_poll", "post_publish_scoring", "feedback_loop"],
        },
        "content_research": {
            "display_name": "Content Research",
            "description": "Research scanners for content sources",
            "agents": ["competitor_scanner", "lead_scanner"],
        },
        "all_scanners": {
            "display_name": "All Scanners",
            "description": "Run all scanner agents in dependency order",
            "agents": [
                "health_claims_monitor", "novel_food_monitor", "mattilsynet_monitor",
                "competitor_scanner", "lead_scanner",
                "shopify_attribution_poll", "post_publish_scoring", "feedback_loop",
            ],
        },
    }
    ```
  - [x] 3.2 Validate all team agent names exist in `AGENT_RUNNERS` at import time (fail-fast)
  - [x] 3.3 Write team definition tests (target: 5+ tests)

- [x] Task 4: Pending Triggers Store (AC: 4)
  - [x] 4.1 Create `PendingTriggerStore` in `core/scheduling/manual_trigger_service.py`
    - In-memory dict: `_pending_triggers: dict[str, PendingTrigger]` (module-level, not class instance — shared across requests)
    - `PendingTrigger` frozen dataclass: `agent_name`, `triggered_by`, `queued_at`, `config_overrides`
    - `add(agent_name, triggered_by, config_overrides) -> PendingTrigger`
    - `pop(agent_name) -> PendingTrigger | None` — removes and returns
    - `get(agent_name) -> PendingTrigger | None` — peek without removal
    - Thread-safe via simple dict (asyncio is single-threaded, no lock needed)
  - [x] 4.2 Integrate with `_run_scheduled_agent` in `core/scheduling/jobs.py`:
    - After agent completes: check `pending_triggers.pop(agent_name)`
    - If pending exists: re-enqueue `_run_scheduled_agent` with the pending trigger's agent_name
    - Log: "Executing pending manual trigger for {agent_name}"
  - [x] 4.3 Write pending trigger tests (target: 8+ tests)
    - Add + pop lifecycle
    - Pop returns None when empty
    - Re-enqueue after completion

- [x] Task 5: FastAPI Router for Manual Triggers (AC: 1, 2, 3, 4, 5)
  - [x] 5.1 Create Pydantic schemas in `ui/backend/schemas/triggers.py`:
    - `TriggerAgentRequest` — optional `config_overrides: dict | None`, optional `force: bool = False`
    - `TriggerAgentResponse` — agent_name, status, job_id, triggered_at, message
    - `TriggerTeamRequest` — optional `team_name: str`
    - `TeamTriggerResponse` — team_name, agent_results list, total, queued, skipped_running, failed
    - `TriggerableAgentResponse` — agent_name, display_name, description, last_run_status, last_run_at, is_running, schedule_cron, next_scheduled_run
    - `TriggerableAgentListResponse` — agents list, total_count
    - `TeamListResponse` — teams list
    - `TeamResponse` — team_name, display_name, agents, description
    - `QueueAfterRequest` — empty body (no fields needed)
  - [x] 5.2 Create `ui/backend/routers/triggers.py`:
    - `GET  /api/agents/triggerable` — list all triggerable agents with status (AC1)
    - `POST /api/agents/{agent_name}/trigger` — trigger single agent (AC2)
    - `POST /api/agents/{agent_name}/queue` — queue trigger for running agent (AC4)
    - `GET  /api/teams/` — list all defined teams (AC3)
    - `POST /api/teams/{team_name}/trigger` — trigger team (AC3)
    - Path validation: `pattern=r"^[a-z][a-z0-9_]{1,99}$"` on all name params
    - Dependency injection: `get_trigger_service()` with session + config
    - ARQ enqueue: use `ctx["redis"].enqueue_job("_run_scheduled_agent", agent_name)` inside router after service confirms "queued"
    - Error codes: 404 (not found), 409 (already running, without force), 400 (invalid params), 503 (Redis unavailable)
  - [x] 5.3 Register router in `ui/backend/routers/__init__.py`
    - Add `from .triggers import router as triggers_router`
    - Add `"triggers_router"` to `__all__`
  - [x] 5.4 Write router tests (target: 18+ tests)
    - Trigger available agent → 200 with job_id
    - Trigger running agent → 409 with warning
    - Trigger running agent with force=true → 200 (queues)
    - Trigger unknown agent → 404
    - Trigger team → 200 with per-agent results
    - Trigger unknown team → 404
    - List triggerable agents → 200 with status enrichment
    - List teams → 200
    - Queue after running → 200
    - Queue non-running → 400 (not running, just trigger normally)
    - Config overrides in request → audit logged
    - Redis unavailable → 503
    - Path validation rejects special chars

- [x] Task 6: Integration with Existing Dispatcher (AC: 2, 4)
  - [x] 6.1 Extend `_run_scheduled_agent` in `core/scheduling/jobs.py`:
    - After runner completes (success or failure), check `pending_trigger_store.pop(agent_name)`
    - If pending exists, re-enqueue via `ctx["redis"].enqueue_job("_run_scheduled_agent", agent_name)`
    - Log re-enqueue event
    - **CRITICAL:** Import `pending_trigger_store` from `manual_trigger_service` via lazy import to avoid circular deps
  - [x] 6.2 Add `_run_scheduled_agent` to also accept optional `config_overrides` parameter:
    - If `config_overrides` provided, pass to runner function (future extension — for now runners ignore extras)
    - Store overrides in `last_run_summary` for audit visibility
  - [x] 6.3 Write integration tests (target: 5+ tests)
    - Manual trigger → ARQ enqueue → agent executes → status updates
    - Manual trigger while running → queue → after completion → re-enqueue
    - Team trigger → all agents execute in order

- [x] Task 7: React Frontend Hook (AC: 1, 2, 3, 4)
  - [x] 7.1 Create TypeScript types in `ui/frontend-react/src/types/triggers.ts`:
    - `TriggerableAgent` interface
    - `Team` interface
    - `TriggerResult` interface
    - `TeamTriggerResult` interface
    - `AgentTriggerFilters` interface
  - [x] 7.2 Create `ui/frontend-react/src/hooks/useAgentTriggers.ts`:
    - SWR fetcher for `/api/agents/triggerable` with 15s refresh interval
    - `triggerAgent(agentName: string, overrides?: Record<string, unknown>) -> Promise<TriggerResult>`
    - `queueAgent(agentName: string) -> Promise<TriggerResult>`
    - `triggerTeam(teamName: string) -> Promise<TeamTriggerResult>`
    - `fetchTeams() -> Team[]`
    - Returns: `agents`, `teams`, `isLoading`, `error`, `triggerAgent`, `queueAgent`, `triggerTeam`, `refresh`
    - Auto-refresh agents after trigger action (mutate SWR cache)
  - [x] 7.3 Write hook tests in `ui/frontend-react/src/hooks/__tests__/useAgentTriggers.test.tsx`:
    - SWR data fetching
    - Trigger actions POST correct endpoints
    - Error handling for 409/404/503
    - Cache invalidation after trigger
    - Target: 12+ tests

- [x] Task 8: Registration + Exports (AC: all)
  - [x] 8.1 Register in `teams/dawo/team_spec.py`:
    - `RegisteredService(name="manual_trigger_service", service_class=ManualTriggerService, capabilities=["scheduling", "manual_trigger"], requires_session=True)`
  - [x] 8.2 Update `core/scheduling/__init__.py` with new exports:
    - `ManualTriggerService`
    - DTOs: `TriggerResult`, `TeamTriggerResult`, `TriggerableAgentDTO`, `TeamDTO`
    - `TEAM_DEFINITIONS`
    - `pending_trigger_store`
  - [x] 8.3 Update `core/scheduling/jobs.py` `__all__` if any new public functions added
  - [x] 8.4 Write registration + export tests (target: 5+ tests)

- [x] Task 9: Integration Tests (AC: all)
  - [x] 9.1 Create `tests/integration/test_manual_triggers_integration.py`:
    - End-to-end: trigger agent → verify ARQ enqueue → verify status update
    - Trigger running agent → queue → verify pending store → mock completion → verify re-enqueue
    - Trigger team → all agents triggered in order → team result aggregation
    - Config override → audit trail entry created
    - List triggerable agents → returns all 8 registered agents with enriched status
    - List teams → returns all 4 team definitions
    - Enable/disable via schedules doesn't affect manual trigger (can trigger disabled agents)
  - [x] 9.2 Target: 12+ integration tests

## Dev Notes

### Critical: What Already Exists (DO NOT Rebuild)

**Reuse from `core/scheduling/jobs.py` (1176 lines, Story 7-6):**
- `AGENT_RUNNERS: dict[str, Callable]` — 8 registered runners (lines 896-906)
- `_run_scheduled_agent(ctx, agent_name)` — executes runner, updates status (lines 972-1040)
- `_schedule_session()` — managed session context manager (lines 767-783)
- `WorkerSettings` — ARQ config with `functions` list (line 1067 includes `_run_scheduled_agent`)
- All 5 scanner runner functions + 3 analytics runners (lines 786-905)
- `enqueue_publish_job()` — pattern for ARQ job enqueuing (lines 1094-1127)

**Reuse from `core/scheduling/schedule_service.py` (419 lines, Story 7-6):**
- `AgentScheduleService` — get_all_schedules, get_schedule, update_schedule, toggle_enabled
- `DEFAULT_SCHEDULES` list — all 8 agents with display_name, cron, dependencies
- `_to_dto()` helper for model-to-DTO conversion

**Reuse from `core/scheduling/schedule_repository.py` (203 lines, Story 7-6):**
- `get_by_agent_name()` — lookup by name
- `update_run_status()` — set status, duration, summary, next_run
- `save_change_log()` — audit trail
- `get_all()` — all schedules ordered by next_run

**Reuse from `core/scheduling/dtos.py` (125 lines, Story 7-6):**
- `AgentScheduleDTO` — full schedule with computed fields
- `ScheduleChangeLogDTO` — audit trail entry

**Reuse from `ui/backend/routers/schedules.py` (Story 7-6):**
- `get_db_session()` — dependency placeholder pattern
- `get_schedule_service()` — service DI pattern
- `_dto_to_response()` — DTO-to-Pydantic conversion helper
- Path validation: `pattern=r"^[a-z][a-z0-9_]{1,99}$"`

**Reuse from `ui/backend/schemas/schedules.py` (131 lines, Story 7-6):**
- Pydantic schema patterns for schedule responses
- `AgentScheduleResponse` — can be extended or imported for trigger responses

**Reuse from frontend hooks:**
- `usePipeline.ts` — SWR fetcher pattern, async action pattern
- `useReports.ts` — POST action pattern with error handling

### Architectural Decisions

**Separate Router (NOT Extending schedules.py):**
- Manual triggers are a distinct concern from schedule configuration
- Separate `triggers.py` router keeps single responsibility
- Prefix: `/api/agents/` and `/api/teams/` (not `/api/schedules/`)

**Service Calls Repository (NOT Direct DB in Router):**
- `ManualTriggerService` owns business logic: validation, status checking, audit logging
- Router handles: ARQ enqueuing (needs Redis from ctx), HTTP responses
- Service DOES NOT enqueue jobs — it prepares and validates, router enqueues

**Why service doesn't enqueue:**
- ARQ Redis pool is only available in router/job context, not in service layer
- Service remains testable without Redis mock
- Router has `request.app.state.redis` or dependency-injected Redis

**In-Memory Pending Store (NOT Database):**
- Pending triggers are ephemeral — if worker restarts, they're lost (acceptable)
- Database overhead not justified for rare manual-queue-after-running scenario
- Module-level dict in `manual_trigger_service.py` — shared across async requests

**Team Definitions are Static (NOT Database):**
- Teams are defined by architecture, not user-configurable
- Stored as dict constant in service module
- Future: could be moved to config if teams become user-configurable

**Manual Trigger Can Override Disabled Schedules:**
- An agent disabled for scheduled runs can still be manually triggered
- Manual = explicit operator intent, not bound by schedule enable/disable

**Force Flag for Running Agents:**
- Default: 409 Conflict if agent is running
- `force=true`: queue for execution after current run completes
- Alternative: `POST /api/agents/{name}/queue` endpoint for queueing explicitly

### Critical ARQ Integration Pattern

**Enqueuing for Immediate Execution:**
```python
# In router — NOT deferred, executes immediately
job = await redis_pool.enqueue_job(
    "_run_scheduled_agent",
    agent_name,
    # No _defer_until — runs ASAP
)
```

**Getting Redis in Router:**
```python
from fastapi import Request

@router.post("/{agent_name}/trigger")
async def trigger_agent(
    agent_name: str,
    request: Request,
    service: ManualTriggerService = Depends(get_trigger_service),
):
    # Get Redis pool from app state (set during startup)
    redis = request.app.state.arq_pool
    if redis is None:
        raise HTTPException(503, "Job queue unavailable")

    result = await service.trigger_agent(agent_name, triggered_by="operator")
    if result.status == "queued":
        job = await redis.enqueue_job("_run_scheduled_agent", agent_name)
        # Update result with actual job_id
```

**Alternative: Redis via Dependency:**
```python
async def get_arq_pool(request: Request):
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is None:
        raise HTTPException(503, "Job queue unavailable")
    return pool
```

### File Structure

```
core/scheduling/
├── __init__.py                      # Updated with new exports
├── jobs.py                          # Extended: pending trigger check in _run_scheduled_agent
├── manual_trigger_service.py        # NEW: ManualTriggerService, TEAM_DEFINITIONS, PendingTriggerStore
├── dtos.py                          # Extended: TriggerResult, TeamTriggerResult, TriggerableAgentDTO, TeamDTO
├── models.py                        # NO CHANGES (no new DB tables)
├── schedule_repository.py           # NO CHANGES
├── schedule_service.py              # NO CHANGES
├── cron_utils.py                    # NO CHANGES
├── optimal_time.py                  # Existing — DO NOT MODIFY
└── conflict_detector.py             # Existing — DO NOT MODIFY

ui/backend/
├── routers/
│   ├── __init__.py                  # Updated: register triggers router
│   └── triggers.py                  # NEW: GET/POST trigger endpoints
└── schemas/
    └── triggers.py                  # NEW: Pydantic request/response models

ui/frontend-react/src/
├── types/
│   └── triggers.ts                  # NEW: TypeScript interfaces
└── hooks/
    ├── useAgentTriggers.ts          # NEW: SWR hook + trigger actions
    └── __tests__/
        └── useAgentTriggers.test.tsx # NEW: Hook tests

tests/core/test_scheduling/
├── test_manual_trigger_service.py   # ~25 tests
├── test_trigger_dtos.py             # ~8 tests
├── test_team_definitions.py         # ~5 tests
├── test_pending_triggers.py         # ~8 tests

tests/ui/backend/test_routers/
└── test_triggers.py                 # ~18 tests

tests/integration/
└── test_manual_triggers_integration.py  # ~12 tests
```

### No New Database Models or Migrations

This story uses **existing** `agent_schedules` table for status tracking.
- `last_run_status` = "running" is set when manual trigger fires
- `last_run_at` is updated on manual trigger
- Audit trail uses existing `schedule_change_logs` table
- No new tables, no new migration files

### Testing Approach (Proven Patterns from 7-6)

- **Frozen dataclasses** for all new DTOs — immutable results
- **Constructor injection** on ManualTriggerService (repository + config)
- **AsyncMock(spec=AgentScheduleRepository)** for repository mocking
- **Tests mirror source**: `tests/core/test_scheduling/test_manual_trigger_service.py`
- **Router tests**: `app.dependency_overrides` for service mocking, `httpx.AsyncClient`
- **No N+1**: `get_triggerable_agents()` fetches all schedules in one query, merges with AGENT_RUNNERS in Python
- **`datetime.now(UTC)`** not `datetime.utcnow()` (deprecated)
- **sys.modules patching**: For jobs.py tests that need to mock `core.database`

### Previous Story Intelligence (from 7-6)

**What Worked Well:**
- Frozen dataclass DTOs kept API contracts clean
- `_schedule_session()` context manager simplified session lifecycle
- Path regex validation `^[a-z][a-z0-9_]{1,99}$` caught malformed inputs
- `AGENT_RUNNERS` registry prevented arbitrary code execution
- Lazy imports in jobs.py avoided circular dependencies

**What to Watch For:**
- Must lazy-import `PendingTriggerStore` in `_run_scheduled_agent` to avoid circular deps
- ARQ `enqueue_job` returns a `Job` object with `job_id` attribute — use for tracking
- Router tests need `app.dependency_overrides` for BOTH service AND Redis pool
- Don't forget `__all__` exports in every new and modified `__init__.py`
- `sys.modules` patching needed for any test importing from `core.scheduling.jobs`

### Anti-Patterns to Avoid

- **DO NOT** enqueue ARQ jobs inside the service layer — service validates, router enqueues
- **DO NOT** create new DB tables/migrations — reuse existing `agent_schedules` + `schedule_change_logs`
- **DO NOT** use `getattr` on agent names — validate against `AGENT_RUNNERS.keys()`
- **DO NOT** block on ARQ job completion in the trigger endpoint — return immediately with job_id
- **DO NOT** make pending triggers persistent (DB) — in-memory dict is sufficient
- **DO NOT** modify `AGENT_RUNNERS` or existing scanner runners — extend with new integration points only
- **DO NOT** use `datetime.utcnow()` — use `datetime.now(UTC)`
- **DO NOT** skip `__all__` exports in any `__init__.py`
- **DO NOT** put team definitions in DB — they're architectural constants
- **DO NOT** allow triggering agents not in `AGENT_RUNNERS` — whitelist only

### Technology Notes

- **ARQ v0.27.0** — `enqueue_job(func_name, *args)` for immediate execution (no `_defer_until`)
- **ARQ Job object** — `job.job_id` returns the job tracking ID
- **FastAPI Request.app.state** — access shared state like Redis pool
- **SWR v2.x** — `mutate()` for cache invalidation after trigger action
- **React 18** — hooks pattern, no class components
- **No new pip dependencies** — everything uses existing packages

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.7]
- [Source: _bmad-output/planning-artifacts/prd.md#System Administration, FR52]
- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Architecture, ARQ Job Queue]
- [Source: _bmad-output/project-context.md#Agent Registration, Configuration Loading]
- [Source: core/scheduling/jobs.py — AGENT_RUNNERS registry, _run_scheduled_agent, WorkerSettings]
- [Source: core/scheduling/schedule_service.py — AgentScheduleService, DEFAULT_SCHEDULES]
- [Source: core/scheduling/schedule_repository.py — update_run_status, get_by_agent_name]
- [Source: core/scheduling/dtos.py — AgentScheduleDTO, ScheduleChangeLogDTO]
- [Source: ui/backend/routers/schedules.py — get_db_session, get_schedule_service patterns]
- [Source: ui/backend/schemas/schedules.py — Pydantic schema patterns]
- [Source: ui/backend/routers/__init__.py — router registration pattern]
- [Source: ui/frontend-react/src/hooks/usePipeline.ts — SWR hook pattern]
- [Source: _bmad-output/implementation-artifacts/7-6-agent-schedule-configuration.md — previous story]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- _check_pending_triggers exception propagation: Function was called in try block of _run_scheduled_agent but exceptions propagated to except block which called it again. Fixed by wrapping both calls in their own try/except.
- Lazy import pattern needed in _check_pending_triggers to avoid circular deps between jobs.py and manual_trigger_service.py.
- Integration test patch target: Must patch `core.scheduling.manual_trigger_service.pending_trigger_store` (source), not `core.scheduling.jobs.pending_trigger_store` (lazy import target doesn't exist as module attr).

### Completion Notes List

- Task 1: ManualTriggerService with 5 methods (trigger_agent, trigger_team, queue_after_current, get_triggerable_agents, get_teams). 25 tests.
- Task 2: 5 frozen dataclass DTOs (TriggerResult, TeamTriggerResult, TriggerableAgentDTO, TeamDTO, PendingTrigger). 11 tests.
- Task 3: TEAM_DEFINITIONS with 4 teams + validate_team_definitions(). 7 tests.
- Task 4: PendingTriggerStore with add/pop/get + module-level singleton. 9 tests.
- Task 5: FastAPI router with 5 endpoints, Pydantic schemas, path validation. 15 tests.
- Task 6: _check_pending_triggers in jobs.py, integrated into _run_scheduled_agent success+failure paths. 5 tests.
- Task 7: TypeScript types + useAgentTriggers SWR hook + 14 hook tests (frontend skeleton, no jest runner).
- Task 8: RegisteredService in team_spec.py, exports in scheduling __init__.py and jobs.py __all__. 10 tests.
- Task 9: 17 integration tests covering all cross-component flows.

### Change Log

- `core/scheduling/dtos.py` — Added TriggerResult, TeamTriggerResult, TriggerableAgentDTO, TeamDTO, PendingTrigger dataclasses + __all__
- `core/scheduling/manual_trigger_service.py` — NEW: ManualTriggerService, TEAM_DEFINITIONS, validate_team_definitions, PendingTriggerStore, pending_trigger_store
- `core/scheduling/jobs.py` — Added _check_pending_triggers(), integrated into _run_scheduled_agent, updated __all__
- `core/scheduling/__init__.py` — Added imports and __all__ entries for all Story 7-7 components
- `ui/backend/schemas/triggers.py` — NEW: Pydantic request/response schemas
- `ui/backend/routers/triggers.py` — NEW: 5 API endpoints for manual triggering
- `ui/backend/routers/__init__.py` — Registered triggers_router
- `ui/frontend-react/src/types/triggers.ts` — NEW: TypeScript interfaces
- `ui/frontend-react/src/hooks/useAgentTriggers.ts` — NEW: SWR hook with trigger actions
- `teams/dawo/team_spec.py` — Added ManualTriggerService import and RegisteredService entry

### File List

**New Files:**
- `core/scheduling/manual_trigger_service.py` (~420 lines)
- `ui/backend/schemas/triggers.py` (~120 lines)
- `ui/backend/routers/triggers.py` (~180 lines)
- `ui/frontend-react/src/types/triggers.ts` (~77 lines)
- `ui/frontend-react/src/hooks/useAgentTriggers.ts` (~163 lines)

**Modified Files:**
- `core/scheduling/dtos.py` — +5 DTOs, +~110 lines
- `core/scheduling/jobs.py` — +_check_pending_triggers, +~30 lines
- `core/scheduling/__init__.py` — +imports and __all__, +~15 lines
- `ui/backend/routers/__init__.py` — +triggers_router import and export
- `teams/dawo/team_spec.py` — +ManualTriggerService registration

**Test Files:**
- `tests/core/test_scheduling/test_manual_trigger_service.py` — 25 tests
- `tests/core/test_scheduling/test_trigger_dtos.py` — 11 tests
- `tests/core/test_scheduling/test_team_definitions.py` — 7 tests
- `tests/core/test_scheduling/test_pending_triggers.py` — 9 tests
- `tests/core/test_scheduling/test_dispatcher_pending_triggers.py` — 5 tests
- `tests/core/test_scheduling/test_manual_trigger_registration.py` — 10 tests
- `tests/ui/backend/test_routers/test_triggers.py` — 18 tests
- `tests/integration/test_manual_triggers_integration.py` — 19 tests
- `ui/frontend-react/src/hooks/__tests__/useAgentTriggers.test.tsx` — 14 tests

**Total: 118 tests (104 backend executed + 14 frontend written)**

## Code Review

**Date:** 2026-02-25
**Reviewer:** Amelia (Dev Agent) — Adversarial CR

### Issues Found & Fixed

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| H1 | HIGH | Double enqueue on `force=true` — router enqueued ARQ job AND added to pending store, causing potential concurrent execution | Removed `arq_pool.enqueue_job` from force path; `_check_pending_triggers` handles re-enqueue |
| M1 | MEDIUM | `queue_after_current` accepted non-running agents silently; pending trigger would never fire | Added `last_run_status == "running"` check; returns `not_running` status; router returns 400 |
| M2 | MEDIUM | Missing router tests: queue non-running→400, team Redis→503, team path validation→422 | Added 3 router tests |
| L1 | LOW | Registration capabilities used gerund form (`manual_triggering`) inconsistent with codebase | Normalized to `manual_trigger`, `team_trigger` |
| L2 | LOW | Unparameterized `list` types in DTOs (`agent_results: list`, `agents: list`) | Changed to `list[TriggerResult]` and `list[str]` |
| L3 | LOW | No integration test for disabled agent manual triggering | Added `TestDisabledAgentTrigger` with 2 tests |

### Files Modified in CR
- `ui/backend/routers/triggers.py` — H1 fix (removed double enqueue), M1 fix (400 for not_running)
- `core/scheduling/manual_trigger_service.py` — M1 fix (running status check in queue_after_current)
- `core/scheduling/dtos.py` — L2 fix (parameterized list types)
- `teams/dawo/team_spec.py` — L1 fix (capabilities naming)
- `tests/ui/backend/test_routers/test_triggers.py` — M2 fix (+3 tests)
- `tests/integration/test_manual_triggers_integration.py` — L3 fix (+2 tests), M1 test fix
- `tests/core/test_scheduling/test_manual_trigger_registration.py` — L1 test update

### Post-CR Test Results
**104 passed, 0 failed** (3.78s)
