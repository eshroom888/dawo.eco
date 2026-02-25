# Story 7.8: Execution Logs & Status Dashboard

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to see agent execution status and logs,
so that I know what's running and can debug issues.

## Acceptance Criteria

1. **AC1 - Dashboard Overview:** When I open the execution dashboard, it loads showing: currently running agents (with start time and progress indicator), recent completions (last 24h), and recent failures (last 7d).

2. **AC2 - Real-Time Status:** When agents are running, the dashboard shows real-time status: agent name, start time, progress indicator. Dashboard updates every 30 seconds via SWR polling.

3. **AC3 - Execution Detail View:** When I click on an agent execution, a detail view shows: start/end time, duration, status (success/failed/incomplete), trigger type (scheduled/manual), and log output (last 1000 lines) with errors highlighted.

4. **AC4 - Failure Details:** When I view a failed execution, I see: error message, stack trace (if available), retry count. I can trigger manual retry from this view (reuses Story 7-7 ManualTriggerService).

5. **AC5 - Historical Filtering:** When I filter by date range, I see all executions in that period. I can also filter by: agent name, status (success/failed/incomplete/running), trigger type (scheduled/manual). Results are paginated (25 per page).

## Tasks / Subtasks

- [x] Task 1: Execution Log Database Model + Migration (AC: 1, 3, 5)
  - [x]1.1 Create `AgentExecutionLog` model in `core/scheduling/models.py`
    - `id: UUID` primary key (gen_random_uuid)
    - `agent_name: str` (VARCHAR 100, indexed, FK-like to agent_schedules.agent_name)
    - `started_at: datetime` (timestamptz, not null)
    - `completed_at: datetime | None` (timestamptz, nullable — null while running)
    - `duration_seconds: float | None` (nullable — null while running)
    - `status: str` (VARCHAR 20: "running", "success", "failed", "incomplete")
    - `trigger_type: str` (VARCHAR 20: "scheduled", "manual")
    - `triggered_by: str` (VARCHAR 50, default "scheduler")
    - `summary: dict | None` (JSONB — runner result dict)
    - `error_message: str | None` (TEXT, nullable — populated on failure)
    - `error_traceback: str | None` (TEXT, nullable — stack trace on failure)
    - `log_output: str | None` (TEXT, nullable — captured log lines, capped at 1000 lines)
    - `items_processed: int` (default 0 — extracted from summary)
    - `created_at: datetime` (server_default=now)
    - Indexes: `idx_execution_logs_agent_name`, `idx_execution_logs_started_at`, `idx_execution_logs_status`, composite `(agent_name, started_at DESC)`
  - [x]1.2 Add `AgentExecutionLog` to `models.py` `__all__`
  - [x]1.3 Create Alembic migration `migrations/versions/2026_02_28_001_create_execution_logs.py`
    - Table name: `agent_execution_logs`
    - All indexes above
    - No foreign key constraint to agent_schedules (agent_name may not exist in schedule table if removed)
  - [x]1.4 Write model tests (target: 8+ tests)
    - Model instantiation with all fields
    - Nullable fields accept None
    - Status values validation
    - Index existence checks
    - Repr output

- [x] Task 2: Execution Log DTOs (AC: 1, 3, 5)
  - [x]2.1 Add to `core/scheduling/dtos.py`:
    - `ExecutionLogDTO` frozen dataclass:
      - `id: str` (UUID as string)
      - `agent_name: str`
      - `display_name: str` — enriched from AGENT_RUNNERS/DEFAULT_SCHEDULES
      - `started_at: datetime`
      - `completed_at: datetime | None`
      - `duration_seconds: float | None`
      - `status: str`
      - `trigger_type: str`
      - `triggered_by: str`
      - `summary: dict | None`
      - `error_message: str | None`
      - `error_traceback: str | None`
      - `items_processed: int`
      - `has_log_output: bool` — flag, not the full text (for list views)
    - `ExecutionLogDetailDTO` frozen dataclass (extends LogDTO concept):
      - All fields from `ExecutionLogDTO`
      - `log_output: str | None` — full log text (only for detail view)
    - `DashboardSummaryDTO` frozen dataclass:
      - `running: list[ExecutionLogDTO]`
      - `recent_completions: list[ExecutionLogDTO]` — last 24h, success only
      - `recent_failures: list[ExecutionLogDTO]` — last 7d, failed/incomplete
      - `total_executions_24h: int`
      - `success_rate_24h: float` — percentage
      - `avg_duration_24h: float | None` — average seconds
    - `ExecutionLogFilterDTO` frozen dataclass:
      - `agent_name: str | None`
      - `status: str | None`
      - `trigger_type: str | None`
      - `date_from: datetime | None`
      - `date_to: datetime | None`
      - `limit: int = 25`
      - `offset: int = 0`
  - [x]2.2 Write DTO tests (target: 10+ tests covering frozen immutability, defaults, filter combinations)

- [x] Task 3: Execution Log Repository (AC: 1, 3, 5)
  - [x]3.1 Create `ExecutionLogRepository` in `core/scheduling/execution_log_repository.py`
    - Constructor: `AsyncSession`
    - `create(log: AgentExecutionLog) -> AgentExecutionLog` — insert new execution entry
    - `update_completion(log_id: UUID, status: str, duration: float, summary: dict | None, error_message: str | None, error_traceback: str | None, log_output: str | None, items_processed: int) -> bool` — update when execution completes
    - `get_by_id(log_id: UUID) -> AgentExecutionLog | None` — single execution detail
    - `get_running() -> list[AgentExecutionLog]` — all with status="running"
    - `get_recent(hours: int = 24, status: str | None = None, limit: int = 50) -> list[AgentExecutionLog]` — recent executions, optionally filtered by status
    - `get_filtered(filters: ExecutionLogFilterDTO) -> tuple[list[AgentExecutionLog], int]` — filtered + paginated, returns (results, total_count). **Single SQL query with COUNT window function — NO N+1.**
    - `get_stats(hours: int = 24) -> dict` — aggregated stats (total, success, failed, avg_duration) via SQL aggregate query, NOT in-memory Python
    - `cleanup_old(days: int = 90) -> int` — delete logs older than N days, return count deleted
  - [x]3.2 Write repository tests (target: 18+ tests)
    - CRUD lifecycle: create → update_completion → get_by_id
    - get_running returns only status="running"
    - get_recent with/without status filter
    - get_filtered with every filter combination
    - get_filtered pagination (offset, limit)
    - get_filtered returns correct total_count alongside results
    - get_stats returns correct aggregates
    - cleanup_old deletes only old records
    - Empty results return empty list (not None)

- [x] Task 4: Execution Log Service (AC: 1, 2, 3, 4, 5)
  - [x]4.1 Create `ExecutionLogService` in `core/scheduling/execution_log_service.py`
    - Constructor: `ExecutionLogRepository`, `AgentScheduleRepository` (for display_name enrichment)
    - `start_execution(agent_name: str, trigger_type: str, triggered_by: str) -> ExecutionLogDTO`
      - Creates `AgentExecutionLog` with status="running", started_at=now
      - Returns DTO with enriched display_name from schedule repo
    - `complete_execution(log_id: str, status: str, summary: dict | None, error_message: str | None, error_traceback: str | None, log_output: str | None) -> ExecutionLogDTO`
      - Calculates duration from started_at
      - Extracts items_processed from summary.get("items_processed", 0)
      - Caps log_output at 1000 lines (split, take last 1000, rejoin)
      - Updates via repository
    - `get_dashboard_summary() -> DashboardSummaryDTO`
      - Queries running, recent success (24h), recent failures (7d)
      - Computes stats via repo.get_stats(24)
      - Returns enriched DTOs with display_names
      - **Single batch query for all schedules — NO N+1**
    - `get_execution_detail(log_id: str) -> ExecutionLogDetailDTO | None`
      - Returns full detail including log_output
    - `get_filtered_executions(filters: ExecutionLogFilterDTO) -> tuple[list[ExecutionLogDTO], int]`
      - Delegates to repo, enriches with display_names
    - Helper: `_enrich_display_name(agent_name: str, schedule_map: dict) -> str`
      - Lookup from pre-fetched schedule_map, fallback to agent_name.replace("_", " ").title()
  - [x]4.2 Write service tests (target: 20+ tests)
    - start_execution creates log and returns DTO
    - complete_execution calculates duration correctly
    - complete_execution caps log_output at 1000 lines
    - get_dashboard_summary aggregates running + completions + failures
    - get_dashboard_summary enriches display_names in batch (no N+1)
    - get_execution_detail returns None for missing
    - get_execution_detail includes log_output
    - get_filtered_executions with various filter combos
    - items_processed extraction from summary dict

- [x] Task 5: Integrate Log Capture into Agent Dispatcher (AC: 1, 3)
  - [x]5.1 Create `LogCaptureHandler` in `core/scheduling/log_capture.py`
    - Subclass `logging.Handler`
    - Constructor: `max_lines: int = 1000`
    - Captures log records to in-memory `StringIO` buffer
    - `get_output() -> str` — returns captured log text (last max_lines)
    - `attach(logger_name: str) -> LogCaptureHandler` — classmethod, attaches to specified logger
    - `detach()` — removes handler from logger
    - Thread-safe via `threading.Lock` (ARQ may use thread pool)
  - [x]5.2 Extend `_run_scheduled_agent` in `core/scheduling/jobs.py`:
    - **At start:** Create execution log via lazy import of `ExecutionLogService`
      ```python
      # Lazy import to avoid circular deps
      from core.scheduling.execution_log_service import ExecutionLogService
      from core.scheduling.execution_log_repository import ExecutionLogRepository
      ```
    - Attach `LogCaptureHandler` to root logger before runner execution
    - **On success:** Complete execution log with status, summary, captured logs
    - **On failure:** Complete execution log with "failed", error_message=str(e), error_traceback=traceback.format_exc(), captured logs
    - **In finally:** Always detach log capture handler
    - Determine trigger_type: check if agent was from pending trigger store → "manual", else → "scheduled"
    - **CRITICAL:** Execution log creation must NOT block agent execution on failure. Wrap in try/except, log warning, continue.
  - [x]5.3 Write dispatcher integration tests (target: 8+ tests)
    - Agent success → execution log created with status="success"
    - Agent failure → execution log with status="failed", error_message, traceback
    - Log output captured in execution log
    - Log output capped at 1000 lines
    - Execution log creation failure doesn't block agent
    - trigger_type correctly identified (scheduled vs manual)
    - duration_seconds calculated correctly

- [x] Task 6: Execution Event Emitter for Real-Time Updates (AC: 2)
  - [x]6.1 Create `ExecutionEventEmitter` in `core/scheduling/execution_events.py`
    - Follow **exact pattern** from `core/publishing/events.py` (PublishEventEmitter)
    - `ExecutionEventType` enum: `STARTED`, `COMPLETED`, `FAILED`
    - `ExecutionEvent` dataclass: event_type, agent_name, execution_id, data dict, timestamp
    - `ExecutionEventEmitter` class: emit(), subscribe(), subscriber_count
    - Singleton via `get_execution_events()` function
    - MAX_QUEUE_SIZE = 100, MAX_SUBSCRIBERS = 100
  - [x]6.2 Emit events from `_run_scheduled_agent`:
    - `STARTED` when execution begins (after log entry created)
    - `COMPLETED` when runner returns success
    - `FAILED` when runner throws or returns failed status
    - **Lazy import** of emitter to avoid circular deps
    - Event emission must NOT block agent execution (fire-and-forget with try/except)
  - [x]6.3 Add WebSocket endpoint `/ws/executions` in `ui/backend/routers/websocket.py`:
    - New `execution_manager = ConnectionManager()`
    - Follow existing `/ws/publish` pattern exactly
    - Forward `ExecutionEvent` objects to connected clients
    - Add to `/ws/all` combined stream with source="execution"
    - Update `/ws/status` to include execution connection count
  - [x]6.4 Write event emitter tests (target: 10+ tests)
    - Emit to zero subscribers (no error)
    - Emit to one subscriber
    - Multiple subscribers receive same event
    - Queue full drops event (no error)
    - Max subscribers limit enforced
    - Singleton pattern returns same instance
    - Event to_dict() serialization
    - WebSocket endpoint accepts connections

- [x] Task 7: FastAPI Router for Execution Dashboard (AC: 1, 2, 3, 4, 5)
  - [x]7.1 Create Pydantic schemas in `ui/backend/schemas/executions.py`:
    - `ExecutionLogResponse` — id, agent_name, display_name, started_at, completed_at, duration_seconds, status, trigger_type, triggered_by, summary, error_message, items_processed, has_log_output
    - `ExecutionLogDetailResponse` — all above + log_output, error_traceback
    - `DashboardSummaryResponse` — running list, recent_completions list, recent_failures list, total_executions_24h, success_rate_24h, avg_duration_24h
    - `ExecutionLogListResponse` — executions list, total_count, has_more
    - `ExecutionFilterParams` — agent_name, status, trigger_type, date_from, date_to, limit, offset (all optional query params)
  - [x]7.2 Create `ui/backend/routers/executions.py`:
    - `GET  /api/executions/dashboard` — dashboard summary (AC1, AC2)
    - `GET  /api/executions/` — filtered/paginated execution history (AC5)
    - `GET  /api/executions/{execution_id}` — single execution detail with logs (AC3)
    - `POST /api/executions/{execution_id}/retry` — retry failed execution (AC4)
      - Extracts agent_name from execution log
      - Delegates to `ManualTriggerService.trigger_agent()` (from 7-7)
      - Returns TriggerResult from trigger service
    - Dependency injection: `get_execution_service()` with session
    - Path validation on execution_id: UUID format check
    - Error codes: 404 (not found), 400 (invalid filters)
  - [x]7.3 Register router in `ui/backend/routers/__init__.py`
    - Add `from .executions import router as executions_router`
    - Add `"executions_router"` to `__all__`
  - [x]7.4 Write router tests (target: 15+ tests)
    - Dashboard summary → 200 with running, completions, failures
    - Execution list with no filters → 200 with paginated results
    - Execution list with agent_name filter → filtered results
    - Execution list with status filter → filtered results
    - Execution list with date range → filtered results
    - Execution list with combined filters → correct intersection
    - Execution detail → 200 with log_output
    - Execution detail not found → 404
    - Retry failed execution → 200 with trigger result
    - Retry non-failed execution → 400 (can only retry failed)
    - Retry non-existent execution → 404
    - Invalid execution_id format → 422
    - Pagination: offset + limit respected

- [x] Task 8: React Frontend Hook (AC: 1, 2, 3, 4, 5)
  - [x]8.1 Create TypeScript types in `ui/frontend-react/src/types/executions.ts`:
    - `ExecutionLog` interface — matches ExecutionLogResponse
    - `ExecutionLogDetail` interface — matches ExecutionLogDetailResponse
    - `DashboardSummary` interface — matches DashboardSummaryResponse
    - `ExecutionFilters` interface — agent_name, status, trigger_type, date_from, date_to
    - `ExecutionListResponse` interface — executions, total_count, has_more
  - [x]8.2 Create `ui/frontend-react/src/hooks/useExecutionDashboard.ts`:
    - SWR fetcher for `/api/executions/dashboard` with 30s refresh interval (AC2)
    - SWR fetcher for `/api/executions/` with filters and pagination
    - `getExecutionDetail(id: string) -> Promise<ExecutionLogDetail>` — on-demand fetch
    - `retryExecution(id: string) -> Promise<TriggerResult>` — POST to retry endpoint
    - Filter state management: `filters`, `setFilters`
    - Pagination state: `page`, `setPage`
    - Returns: `dashboard`, `executions`, `totalCount`, `hasMore`, `isLoading`, `error`, `filters`, `setFilters`, `page`, `setPage`, `getExecutionDetail`, `retryExecution`, `refresh`
    - Auto-refresh dashboard after retry action (mutate SWR cache)
  - [x]8.3 Write hook tests in `ui/frontend-react/src/hooks/__tests__/useExecutionDashboard.test.tsx`:
    - SWR data fetching for dashboard
    - SWR data fetching for execution list
    - Filter changes trigger new fetch
    - Pagination state management
    - Retry action POSTs correct endpoint
    - Error handling for 404
    - Cache invalidation after retry
    - Target: 12+ tests

- [x] Task 9: Registration + Exports (AC: all)
  - [x]9.1 Register in `teams/dawo/team_spec.py`:
    - `RegisteredService(name="execution_log_service", service_class=ExecutionLogService, capabilities=["scheduling", "execution_logs", "dashboard"], requires_session=True)`
  - [x]9.2 Update `core/scheduling/__init__.py` with new exports:
    - `AgentExecutionLog` (model)
    - `ExecutionLogRepository`
    - `ExecutionLogService`
    - DTOs: `ExecutionLogDTO`, `ExecutionLogDetailDTO`, `DashboardSummaryDTO`, `ExecutionLogFilterDTO`
    - `ExecutionEventEmitter`, `ExecutionEvent`, `ExecutionEventType`, `get_execution_events`
    - `LogCaptureHandler`
  - [x]9.3 Update `core/scheduling/models.py` `__all__` with `AgentExecutionLog`
  - [x]9.4 Update `core/scheduling/dtos.py` `__all__` with new DTOs
  - [x]9.5 Write registration + export tests (target: 5+ tests)

- [x] Task 10: Integration Tests (AC: all)
  - [x]10.1 Create `tests/integration/test_execution_logs_integration.py`:
    - End-to-end: agent dispatched → execution log created → status updated → dashboard shows
    - Failed agent → execution log with error_message + traceback → retry from dashboard → new execution created
    - Log capture: agent runs → log output captured → visible in detail view
    - Filtered history: create multiple executions → filter by agent → correct results
    - Filtered history: filter by date range → correct results
    - Filtered history: filter by status → correct results
    - Dashboard summary: mix of running, success, failed → correct aggregation
    - Pagination: 30 executions, limit=25 → first page has 25, has_more=true
    - Execution events emitted on start/complete/fail
    - Retry failed execution → ManualTriggerService called → new execution log created
  - [x]10.2 Target: 15+ integration tests

## Dev Notes

### Critical: What Already Exists (DO NOT Rebuild)

**Reuse from `core/scheduling/jobs.py` (Story 7-6, 7-7):**
- `AGENT_RUNNERS: dict[str, Callable]` — 8 registered runners (line 898)
- `_run_scheduled_agent(ctx, agent_name)` — the dispatcher to extend (line 1013)
- `_schedule_session()` — managed session context manager (line 767)
- `_check_pending_triggers()` — pending manual trigger check (line 976)
- **Pattern:** Lazy imports inside functions to avoid circular deps with `core.database`

**Reuse from `core/scheduling/schedule_repository.py` (Story 7-6):**
- `AgentScheduleRepository` — get_all() for display_name enrichment
- `get_by_agent_name()` — individual schedule lookup
- `update_run_status()` — still called for schedule status (execution log is ADDITIONAL, not replacing)

**Reuse from `core/scheduling/manual_trigger_service.py` (Story 7-7):**
- `ManualTriggerService.trigger_agent()` — for retry from dashboard (AC4)
- `pending_trigger_store` — for determining trigger_type in dispatcher

**Reuse from `core/publishing/events.py` (Story 4-5):**
- `PublishEventEmitter` pattern — EXACT template for `ExecutionEventEmitter`
- `PublishEvent.to_dict()` — serialization pattern
- Singleton via `get_publish_events()` — same pattern for `get_execution_events()`

**Reuse from `ui/backend/routers/websocket.py` (Epic 4):**
- `ConnectionManager` class — already exists, reuse for execution events
- WebSocket streaming pattern — `/ws/publish` as template for `/ws/executions`
- Combined `/ws/all` stream — extend to include execution events

**Reuse from `ui/backend/routers/schedules.py` (Story 7-6):**
- `get_db_session()` — dependency placeholder pattern
- `_dto_to_response()` — DTO-to-Pydantic conversion helper pattern
- Path validation regex: `^[a-z][a-z0-9_]{1,99}$` — for agent_name params

**Reuse from `ui/backend/routers/triggers.py` (Story 7-7):**
- `get_trigger_service()` — DI pattern for ManualTriggerService (needed for retry endpoint)
- ARQ Redis pool from `request.app.state.arq_pool` — for retry enqueuing

**Reuse from frontend hooks (Story 5-5, 7-7):**
- `usePipeline.ts` — SWR fetcher, filter state, pagination pattern
- `useAgentTriggers.ts` — POST action pattern, mutate after action

### Architectural Decisions

**New `agent_execution_logs` Table (NOT Extending agent_schedules):**
- `agent_schedules` stores only the LAST run. Dashboard needs history.
- Separate table allows efficient date range queries, aggregation, cleanup.
- No FK to agent_schedules — agent_name is the loose coupling key. If a schedule is deleted, historical logs remain.
- 90-day retention policy via `cleanup_old()` to prevent unbounded growth.

**Execution Log IS Additional to Schedule Status (NOT Replacing):**
- `_run_scheduled_agent` still calls `repo.update_run_status()` on the schedule table.
- Execution log is a SECOND write for historical tracking.
- If execution log creation fails, agent execution is NOT blocked (try/except wrapper).

**Log Capture via logging.Handler (NOT stdout/stderr Redirect):**
- Python `logging.Handler` subclass captures structured log output.
- Attached to root logger before agent execution, detached after.
- Max 1000 lines — captures last N lines if output exceeds limit.
- Thread-safe with `threading.Lock` (ARQ may use thread pool for some operations).

**SWR Polling (NOT WebSocket) for Dashboard Auto-Refresh:**
- AC2 says "dashboard updates every 30 seconds" — SWR refreshInterval=30000 is sufficient.
- WebSocket execution events are available for OPTIONAL real-time enhancement.
- SWR is simpler, more reliable, and already the established pattern.
- WebSocket provides bonus real-time updates for status transitions.

**Retry Delegates to ManualTriggerService (NOT Direct ARQ Enqueue):**
- Retry button calls existing `ManualTriggerService.trigger_agent()` from Story 7-7.
- Service handles: running guard, status update, audit logging.
- Router handles: ARQ enqueue (same pattern as triggers.py).
- Prevents duplicating business logic.

**ExecutionEventEmitter Follows PublishEventEmitter Exactly:**
- Same asyncio.Queue-based pub/sub pattern.
- Same singleton pattern, same MAX_QUEUE_SIZE/MAX_SUBSCRIBERS.
- Same `to_dict()` serialization for WebSocket transport.
- Consistency reduces cognitive load and bugs.

### Critical: Execution Log vs Schedule Status

```
_run_scheduled_agent(ctx, agent_name):
    1. Create execution log (status="running") ← NEW
    2. Emit STARTED event ← NEW
    3. Run agent runner (existing)
    4. Update schedule status (existing — repo.update_run_status)
    5. Complete execution log (status/summary/logs) ← NEW
    6. Emit COMPLETED/FAILED event ← NEW
    7. Check pending triggers (existing — Story 7-7)
```

Both writes (schedule + execution log) use separate sessions. Execution log failure does NOT block schedule status update.

### File Structure

```
core/scheduling/
├── __init__.py                          # Updated with new exports
├── models.py                            # Extended: AgentExecutionLog model
├── dtos.py                              # Extended: 4 new DTOs
├── execution_log_repository.py          # NEW: CRUD for execution logs
├── execution_log_service.py             # NEW: Business logic for dashboard
├── execution_events.py                  # NEW: ExecutionEventEmitter (pub/sub)
├── log_capture.py                       # NEW: LogCaptureHandler
├── jobs.py                              # Extended: log creation in _run_scheduled_agent
├── manual_trigger_service.py            # NO CHANGES
├── schedule_repository.py               # NO CHANGES
├── schedule_service.py                  # NO CHANGES
├── cron_utils.py                        # NO CHANGES
├── optimal_time.py                      # NO CHANGES
├── conflict_detector.py                 # NO CHANGES

ui/backend/
├── routers/
│   ├── __init__.py                      # Updated: register executions router
│   ├── executions.py                    # NEW: Dashboard + history + detail + retry endpoints
│   └── websocket.py                     # Extended: /ws/executions endpoint + combined stream
└── schemas/
    └── executions.py                    # NEW: Pydantic request/response models

ui/frontend-react/src/
├── types/
│   └── executions.ts                    # NEW: TypeScript interfaces
└── hooks/
    ├── useExecutionDashboard.ts         # NEW: SWR hook + retry actions
    └── __tests__/
        └── useExecutionDashboard.test.tsx  # NEW: Hook tests

migrations/versions/
└── 2026_02_28_001_create_execution_logs.py  # NEW: agent_execution_logs table

tests/core/test_scheduling/
├── test_execution_log_model.py          # ~8 tests
├── test_execution_log_dtos.py           # ~10 tests
├── test_execution_log_repository.py     # ~18 tests
├── test_execution_log_service.py        # ~20 tests
├── test_log_capture.py                  # ~8 tests
├── test_execution_events.py             # ~10 tests
├── test_dispatcher_execution_logs.py    # ~8 tests

tests/ui/backend/test_routers/
└── test_executions.py                   # ~15 tests

tests/integration/
└── test_execution_logs_integration.py   # ~15 tests
```

### Database Model

```sql
CREATE TABLE agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(100) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_seconds FLOAT,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    trigger_type VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    triggered_by VARCHAR(50) NOT NULL DEFAULT 'scheduler',
    summary JSONB,
    error_message TEXT,
    error_traceback TEXT,
    log_output TEXT,
    items_processed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_execution_logs_agent_name ON agent_execution_logs(agent_name);
CREATE INDEX idx_execution_logs_started_at ON agent_execution_logs(started_at DESC);
CREATE INDEX idx_execution_logs_status ON agent_execution_logs(status);
CREATE INDEX idx_execution_logs_agent_started ON agent_execution_logs(agent_name, started_at DESC);
```

### Testing Approach (Proven Patterns from 7-6, 7-7)

- **Frozen dataclasses** for all new DTOs — immutable results
- **Constructor injection** on ExecutionLogService (both repositories + optional config)
- **AsyncMock(spec=ExecutionLogRepository)** for repository mocking
- **AsyncMock(spec=AgentScheduleRepository)** for display_name enrichment mocking
- **Tests mirror source**: `tests/core/test_scheduling/test_execution_log_service.py`
- **Router tests**: `app.dependency_overrides` for service mocking, `httpx.AsyncClient`
- **No N+1**: Dashboard fetches all schedules in one query for display_name map, then batch processes
- **`datetime.now(UTC)`** not `datetime.utcnow()` (deprecated)
- **sys.modules patching**: For jobs.py tests that need to mock `core.database`
- **LogCaptureHandler tests**: Use standard logging module, verify captured output

### Previous Story Intelligence (from 7-7)

**What Worked Well:**
- Frozen dataclass DTOs kept API contracts clean
- Path regex validation caught malformed inputs
- Lazy imports in jobs.py avoided circular dependencies
- `AGENT_RUNNERS` registry prevented arbitrary code execution
- Router tests with `app.dependency_overrides` for both service AND Redis pool
- Code review caught double-enqueue bug (H1) early

**What to Watch For:**
- Must lazy-import `ExecutionLogService` and `ExecutionLogRepository` in `_run_scheduled_agent` to avoid circular deps
- Execution log creation/update must be wrapped in try/except — NEVER block agent execution
- Log capture handler must be detached in finally block — resource leak risk
- `get_filtered()` must return `(list, total_count)` tuple — UI needs both for pagination
- Dashboard `get_stats()` must use SQL aggregates, NOT fetch-all-then-compute-in-Python
- Don't forget `__all__` exports in every new and modified `__init__.py`
- `sys.modules` patching needed for any test importing from `core.scheduling.jobs`
- WebSocket extension needs to register new `execution_manager` and update all three endpoints

### Anti-Patterns to Avoid

- **DO NOT** replace schedule status tracking — execution log is ADDITIONAL to existing `update_run_status()`
- **DO NOT** block agent execution if execution log creation fails — wrap in try/except
- **DO NOT** store unlimited log output — cap at 1000 lines in service layer
- **DO NOT** create N+1 queries for display_name enrichment — batch fetch all schedules once
- **DO NOT** compute stats in Python — use SQL aggregate functions (COUNT, AVG, etc.)
- **DO NOT** use `getattr` on agent names — validate against `AGENT_RUNNERS.keys()`
- **DO NOT** redirect stdout/stderr for log capture — use Python logging.Handler
- **DO NOT** add FK constraint from execution_logs to agent_schedules — logs should survive schedule deletion
- **DO NOT** use `datetime.utcnow()` — use `datetime.now(UTC)`
- **DO NOT** skip `__all__` exports in any `__init__.py`
- **DO NOT** duplicate ManualTriggerService logic for retry — delegate to existing service

### Technology Notes

- **SQLAlchemy Text type** — use `Text` (not `String`) for `error_message`, `error_traceback`, `log_output` (unbounded length)
- **PostgreSQL window function** — `COUNT(*) OVER()` for total count alongside paginated results in single query
- **Python logging.Handler** — subclass with `emit(record)` method, attach to root logger
- **threading.Lock** — for LogCaptureHandler thread safety (ARQ may use thread pool)
- **traceback.format_exc()** — captures current exception traceback as string
- **StringIO** — in-memory text buffer for log capture
- **ARQ v0.27.0** — same patterns as Story 7-6, 7-7
- **SWR v2.x** — 30s refreshInterval for dashboard, `mutate()` for cache invalidation
- **React 18** — hooks pattern, no class components
- **No new pip dependencies** — everything uses existing packages

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.8]
- [Source: _bmad-output/planning-artifacts/prd.md#System Administration, FR53]
- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Architecture, ARQ Job Queue]
- [Source: _bmad-output/project-context.md#Agent Registration, Configuration Loading]
- [Source: core/scheduling/jobs.py — AGENT_RUNNERS registry, _run_scheduled_agent]
- [Source: core/scheduling/models.py — AgentSchedule model, ScheduleChangeLog]
- [Source: core/scheduling/schedule_repository.py — get_all, update_run_status patterns]
- [Source: core/scheduling/dtos.py — existing DTO patterns]
- [Source: core/scheduling/manual_trigger_service.py — ManualTriggerService for retry]
- [Source: core/publishing/events.py — PublishEventEmitter pattern (exact template)]
- [Source: ui/backend/routers/websocket.py — ConnectionManager, WebSocket streaming pattern]
- [Source: ui/backend/routers/schedules.py — get_db_session, DI patterns]
- [Source: ui/backend/routers/triggers.py — trigger service DI, ARQ enqueue pattern]
- [Source: ui/backend/schemas/schedules.py — Pydantic schema patterns]
- [Source: ui/frontend-react/src/hooks/usePipeline.ts — SWR fetcher, filter, pagination patterns]
- [Source: ui/frontend-react/src/hooks/useAgentTriggers.ts — POST action, mutate patterns]
- [Source: _bmad-output/implementation-artifacts/7-7-manual-team-agent-triggers.md — previous story]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- Context resumed across 2 sessions due to context window limits

### Completion Notes List

- Task 1: AgentExecutionLog model + migration (13 tests)
- Task 2: ExecutionLogDTO, ExecutionLogDetailDTO, DashboardSummaryDTO, ExecutionLogFilterDTO (13 tests)
- Task 3: ExecutionLogRepository with CRUD, filtering, stats, cleanup (20 tests)
- Task 4: ExecutionLogService with dashboard, detail, filtered, enrichment (22 tests)
- Task 5: LogCaptureHandler + _run_scheduled_agent integration + was_triggered() fix (8 tests)
- Task 6: ExecutionEventEmitter + WebSocket endpoints + event emission in dispatcher (14 tests)
- Task 7: FastAPI router with dashboard/list/detail/retry endpoints (17 tests)
- Task 8: React useExecutionDashboard hook with SWR, filters, pagination, retry (14 tests)
- Task 9: core/scheduling exports + team_spec registration (11 tests)
- Task 10: Integration tests covering all ACs end-to-end (17 tests)
- Total: 149 new tests (376 total in scheduling + router + integration suite)
- Notable fixes: Added PendingTriggerStore.was_triggered() method (needed by dispatcher)
- Notable fixes: Added finally block for log_handler.detach() (resource leak prevention)
- All event emissions are fire-and-forget (lazy import + try/except: pass)

### File List

**New files:**
- core/scheduling/execution_log_repository.py
- core/scheduling/execution_log_service.py
- core/scheduling/execution_events.py
- core/scheduling/log_capture.py
- migrations/versions/2026_02_28_001_create_execution_logs.py
- ui/backend/routers/executions.py
- ui/backend/schemas/executions.py
- ui/frontend-react/src/types/executions.ts
- ui/frontend-react/src/hooks/useExecutionDashboard.ts
- ui/frontend-react/src/hooks/__tests__/useExecutionDashboard.test.tsx
- tests/core/test_scheduling/test_execution_log_model.py
- tests/core/test_scheduling/test_execution_log_dtos.py
- tests/core/test_scheduling/test_execution_log_repository.py
- tests/core/test_scheduling/test_execution_log_service.py
- tests/core/test_scheduling/test_log_capture.py
- tests/core/test_scheduling/test_execution_events.py
- tests/core/test_scheduling/test_dispatcher_execution_logs.py
- tests/core/test_scheduling/test_registration_78.py
- tests/ui/backend/test_routers/test_executions.py
- tests/integration/test_execution_logs_integration.py

**Modified files:**
- core/scheduling/__init__.py (new exports)
- core/scheduling/models.py (AgentExecutionLog model)
- core/scheduling/dtos.py (4 new DTOs)
- core/scheduling/jobs.py (log capture + event emission in _run_scheduled_agent)
- core/scheduling/manual_trigger_service.py (was_triggered() method)
- core/publishing/events.py (datetime.utcnow → datetime.now(UTC) fix)
- ui/backend/routers/__init__.py (executions_router registration)
- ui/backend/routers/triggers.py (trigger_type="manual" passed to ARQ enqueue)
- ui/backend/routers/websocket.py (execution events + /ws/executions)
- teams/dawo/team_spec.py (ExecutionLogService + ExecutionLogRepository registration)

### Code Review Record

**Reviewer:** Amelia (Dev Agent CR workflow)
**Date:** 2026-02-25
**Findings (7 total): 1 HIGH, 3 MEDIUM, 3 LOW — all fixed**

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| H1 | HIGH | trigger_type always "scheduled" — `was_triggered()` never returns True at the right moment | Changed `_run_scheduled_agent` signature to accept `trigger_type` param; callers pass `"manual"` explicitly; retry endpoint now enqueues ARQ job |
| M1 | MEDIUM | `core/publishing/events.py` modified but not in story File List | Added to File List |
| M2 | MEDIUM | Missing `ExecutionFilterParams` Pydantic schema (specified in Task 7.1) | Added `ExecutionFilterParams` to `ui/backend/schemas/executions.py` |
| M3 | MEDIUM | `get_dashboard_summary` makes 5 sequential DB queries | Parallelized with `asyncio.gather()` |
| L1 | LOW | `ExecutionEvent` dataclass not frozen (all other DTOs are frozen) | Added `frozen=True` |
| L2 | LOW | `complete_execution` does extra `get_by_id` after update | Build DTO from known values, eliminated round-trip |
| L3 | LOW | Integration test mock ignores `hours` parameter | Replaced lambda with named function that asserts correct hours |

**Post-fix test run:** 47/47 passed (0.93s)
