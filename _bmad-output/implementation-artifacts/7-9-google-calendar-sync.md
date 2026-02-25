# Story 7.9: Google Calendar Sync

Status: complete

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want my content schedule visible in Google Calendar,
so that I can see posting schedule alongside other commitments.

## Acceptance Criteria

1. **AC1 - Calendar Event Creation:** Given Google Calendar integration is configured, when content is scheduled for publish, then a calendar event is created with: title=post summary (first 60 chars of caption), time=publish time, description includes link to content in dashboard. Event is created in a dedicated "DAWO Content Schedule" calendar.

2. **AC2 - Event Update on Reschedule:** Given a scheduled post changes, when publish time is modified, then the corresponding calendar event is updated automatically. Sync happens within 5 minutes (via ARQ background job, not blocking the reschedule operation).

3. **AC3 - Published Status Update:** Given content is published, when publish completes, then calendar event is updated to show PUBLISHED status: colorId changes to green (9), title prefixed with checkmark, description updated with Instagram permalink. Event time remains at original schedule time.

4. **AC4 - Dedicated Calendar:** Given I view my Google Calendar, when content events appear, then they're in a dedicated "DAWO Content Schedule" calendar. Calendar is auto-created on first sync if it doesn't exist. I can toggle visibility without affecting sync.

5. **AC5 - Graceful Degradation:** Given calendar API is unavailable, when sync fails, then the operation is marked INCOMPLETE and queued for retry (via existing RetryMiddleware pattern). Operator is NOT blocked from scheduling or publishing. Sync failure is logged but never raises to caller. Failed syncs retry on next `_process_calendar_sync_queue` cron cycle.

## Tasks / Subtasks

- [x] Task 1: Calendar Config + Credentials Manager (AC: 1, 4, 5)
  - [x] 1.1 Create `config/dawo_calendar.json`:
    - `token_path`: "credentials/calendar_token.json"
    - `credentials_path`: "credentials/google-oauth.json"
    - `scopes`: ["https://www.googleapis.com/auth/calendar"]
    - `calendar_name`: "DAWO Content Schedule"
    - `calendar_id`: "${GOOGLE_CALENDAR_ID}" (env var, populated after first run)
    - `sync_enabled`: true
    - `dashboard_base_url`: "${DASHBOARD_BASE_URL}"
    - `color_ids`: { "scheduled": "10", "published": "9", "failed": "11" }
    - `max_title_length`: 60
  - [x] 1.2 Add `CalendarConfig` frozen dataclass to `core/config.py`:
    - `token_path: str`
    - `credentials_path: str`
    - `scopes: list[str]`
    - `calendar_name: str`
    - `calendar_id: str` (empty string default, populated at runtime)
    - `sync_enabled: bool`
    - `dashboard_base_url: str`
    - `color_ids: dict[str, str]`
    - `max_title_length: int = 60`
    - Add to `get_config()` return with key `calendar`
  - [x] 1.3 Create `CalendarCredentialsManager` in `integrations/google_calendar/credentials_manager.py`:
    - **Follow EXACT pattern from** `teams/dawo/leads/gmail/credentials_manager.py`
    - Constructor: `CalendarConfig` (DI, never load files directly)
    - `get_credentials() -> Credentials` — load token, auto-refresh if expired
    - `get_service() -> Resource` — `build("calendar", "v3", credentials=creds)`
    - `is_authenticated() -> bool` — check token validity
    - Custom exception: `CalendarAuthError` for auth failures
    - Token file: `credentials/calendar_token.json` (SEPARATE from gmail_token.json)
    - Reuse OAuth client: `credentials/google-oauth.json` (same Google Cloud project)
  - [x] 1.4 Write config + credentials tests (target: 10+ tests)
    - CalendarConfig frozen immutability
    - CalendarConfig defaults (max_title_length)
    - CalendarConfig in get_config() return
    - CredentialsManager loads token file
    - CredentialsManager auto-refreshes expired token
    - CredentialsManager raises CalendarAuthError on invalid token
    - CredentialsManager returns service object
    - CredentialsManager.is_authenticated() checks validity
    - Missing token file handled gracefully

- [x] Task 2: Calendar Client (AC: 1, 2, 3, 4, 5)
  - [x] 2.1 Create `CalendarClientProtocol` in `integrations/google_calendar/__init__.py`:
    ```python
    @runtime_checkable
    class CalendarClientProtocol(Protocol):
        async def ensure_calendar_exists(self) -> str: ...
        async def create_event(self, event: CalendarEventData) -> CalendarSyncResult: ...
        async def update_event(self, event_id: str, updates: CalendarEventData) -> CalendarSyncResult: ...
        async def delete_event(self, event_id: str) -> bool: ...
    ```
  - [x] 2.2 Create `CalendarClient` in `integrations/google_calendar/client.py`:
    - Constructor: `CalendarCredentialsManager`, `CalendarConfig` (both via DI)
    - `async def ensure_calendar_exists(self) -> str`:
      - Check if `config.calendar_id` is set. If yes, verify it exists via `calendars().get()`.
      - If not set or doesn't exist, create via `calendars().insert(body={"summary": config.calendar_name})`
      - Return `calendar_id` (store for subsequent calls)
      - **CRITICAL:** All sync Google API calls wrapped with `asyncio.get_event_loop().run_in_executor(None, ...)`
    - `async def create_event(self, event: CalendarEventData) -> CalendarSyncResult`:
      - Call `events().insert(calendarId=self._calendar_id, body=event.to_google_event())`
      - Return `CalendarSyncResult(event_id=result["id"], status="created", synced_at=datetime.now(UTC))`
    - `async def update_event(self, event_id: str, updates: CalendarEventData) -> CalendarSyncResult`:
      - Call `events().patch(calendarId=self._calendar_id, eventId=event_id, body=updates.to_google_event())`
      - **Use PATCH not UPDATE** — avoids clearing unset fields
      - Return `CalendarSyncResult(event_id=event_id, status="updated", synced_at=datetime.now(UTC))`
    - `async def delete_event(self, event_id: str) -> bool`:
      - Call `events().delete(calendarId=self._calendar_id, eventId=event_id)`
      - Return True on success, False on 404 (event already removed)
    - All methods: wrap Google API `HttpError` into `CalendarSyncError` with descriptive message
    - Implement `__aenter__`/`__aexit__` for resource cleanup (async context manager)
  - [x] 2.3 Create DTOs in `integrations/google_calendar/dtos.py`:
    - `CalendarEventData` frozen dataclass:
      - `title: str`
      - `start_time: datetime`
      - `end_time: datetime` (default: start_time + 30 min)
      - `description: str`
      - `color_id: str`
      - `extended_properties: dict[str, str]` (for DAWO metadata: post_id, content_type)
      - `to_google_event() -> dict` — converts to Google Calendar API format
    - `CalendarSyncResult` frozen dataclass:
      - `event_id: str`
      - `status: str` ("created", "updated", "deleted", "failed")
      - `synced_at: datetime`
      - `error_message: str | None = None`
  - [x] 2.4 Write client tests (target: 15+ tests)
    - ensure_calendar_exists creates calendar when ID missing
    - ensure_calendar_exists returns existing ID when set
    - ensure_calendar_exists handles calendar deleted externally (recreate)
    - create_event returns CalendarSyncResult with event_id
    - create_event passes correct body format to Google API
    - create_event includes extended properties
    - update_event uses PATCH not UPDATE
    - update_event handles 404 (event deleted externally)
    - delete_event returns True on success
    - delete_event returns False on 404
    - All methods use run_in_executor (async wrapping verified)
    - HttpError mapped to CalendarSyncError
    - CalendarEventData.to_google_event() format verified
    - CalendarSyncResult frozen immutability
    - Context manager cleanup

- [x] Task 3: Event Builder (AC: 1, 2, 3)
  - [x] 3.1 Create `EventBuilder` in `integrations/google_calendar/event_builder.py`:
    - Constructor: `CalendarConfig` (for color_ids, dashboard_base_url, max_title_length)
    - `build_scheduled_event(item: ApprovalItemLike) -> CalendarEventData`:
      - title: First `max_title_length` chars of caption, truncated at word boundary
      - start_time: `item.scheduled_publish_time`
      - end_time: start_time + 30 minutes
      - description: f"Content scheduled for Instagram\n\nDashboard: {dashboard_base_url}/content/{item.id}\n\nCaption preview: {item.full_caption[:200]}..."
      - color_id: `config.color_ids["scheduled"]` (blue=10)
      - extended_properties: `{"post_id": str(item.id), "content_type": "instagram_post"}`
    - `build_published_update(item: ApprovalItemLike, instagram_url: str) -> CalendarEventData`:
      - title: f"Published: {truncated_caption}"
      - color_id: `config.color_ids["published"]` (green=9)
      - description: f"Published to Instagram\n\nInstagram: {instagram_url}\nDashboard: {dashboard_base_url}/content/{item.id}"
      - Preserves original start_time/end_time
    - `build_failed_update(item: ApprovalItemLike, error: str) -> CalendarEventData`:
      - title: f"FAILED: {truncated_caption}"
      - color_id: `config.color_ids["failed"]` (red=11)
      - description includes error message
    - **ApprovalItemLike Protocol**: Define minimal protocol for testability (id, full_caption, scheduled_publish_time)
  - [x] 3.2 Write event builder tests (target: 10+ tests)
    - Title truncation at word boundary
    - Title truncation at exact max_title_length
    - Short title (no truncation)
    - Scheduled event has correct color_id
    - Published update has green color_id and checkmark prefix
    - Failed update has red color_id
    - Description includes dashboard link
    - Extended properties include post_id
    - to_google_event() produces valid API format
    - Time zone handling (UTC)

- [x] Task 4: Calendar Sync Service (AC: 1, 2, 3, 5)
  - [x] 4.1 Create `CalendarSyncService` in `integrations/google_calendar/sync_service.py`:
    - Constructor: `CalendarClientProtocol`, `EventBuilder`, `CalendarConfig`
    - `async def sync_scheduled(self, item: ApprovalItemLike) -> CalendarSyncResult`:
      - If `not config.sync_enabled`, return `CalendarSyncResult(status="disabled")`
      - Ensure calendar exists (lazy, cached after first call)
      - Build event via EventBuilder.build_scheduled_event()
      - If item has `google_calendar_event_id` → update_event
      - Else → create_event
      - Return result
    - `async def sync_published(self, item: ApprovalItemLike, instagram_url: str) -> CalendarSyncResult`:
      - If no `google_calendar_event_id` on item → create_event (was never synced)
      - Else → update_event with published update
    - `async def sync_failed(self, item: ApprovalItemLike, error: str) -> CalendarSyncResult`:
      - Update event with failed status
    - `async def sync_rescheduled(self, item: ApprovalItemLike) -> CalendarSyncResult`:
      - Update event with new time
    - `async def remove_event(self, item: ApprovalItemLike) -> bool`:
      - Delete event if `google_calendar_event_id` exists
    - **All methods wrapped in try/except** — catch all exceptions, log warning, return `CalendarSyncResult(status="failed", error_message=str(e))`
    - **NEVER raise** to caller — graceful degradation is mandatory
  - [x] 4.2 Write service tests (target: 15+ tests)
    - sync_scheduled creates event for new item
    - sync_scheduled updates event for existing item
    - sync_scheduled returns "disabled" when sync_enabled=False
    - sync_published updates event with green color
    - sync_published creates event if never synced
    - sync_failed updates event with red color
    - sync_rescheduled updates event time
    - remove_event deletes event
    - remove_event returns True when no event_id (noop)
    - All methods catch exceptions (never raise)
    - All methods return CalendarSyncResult
    - ensure_calendar_exists called only once (cached)
    - Calendar client called with correct parameters
    - Config.sync_enabled=False short-circuits all methods

- [x] Task 5: Database Migration — Add calendar_event_id (AC: 1, 2, 3)
  - [x] 5.1 Create migration `migrations/versions/2026_03_01_001_add_calendar_event_id.py`:
    - Add column `google_calendar_event_id VARCHAR(255) NULL` to `approval_items` table
    - Add index `idx_approval_items_calendar_event_id` on `google_calendar_event_id`
    - Nullable — calendar sync is optional, existing items have no event ID
    - **NO data migration needed** — new column only
  - [x] 5.2 Add `google_calendar_event_id` field to ApprovalItem model (in `core/approval/models.py` or wherever ApprovalItem lives):
    - `google_calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)`
  - [x] 5.3 Write migration tests (target: 3+ tests)
    - Column exists after migration
    - Column is nullable
    - Index exists
    - Existing rows have NULL value

- [x] Task 6: Integration with Publishing Flow (AC: 1, 2, 3, 5)
  - [x] 6.1 Create ARQ job `sync_calendar_event` in `core/scheduling/jobs.py`:
    - **Lazy imports** inside function (avoid circular deps):
      ```python
      async def sync_calendar_event(ctx: dict, item_id: str, action: str, **kwargs) -> str:
          from integrations.google_calendar import CalendarClient
          from integrations.google_calendar.credentials_manager import CalendarCredentialsManager
          from integrations.google_calendar.sync_service import CalendarSyncService
          from integrations.google_calendar.event_builder import EventBuilder
          from core.config import get_config
          from core.database import get_async_session
      ```
    - Actions: `"scheduled"`, `"published"`, `"rescheduled"`, `"failed"`, `"deleted"`
    - On success: update `item.google_calendar_event_id` in DB
    - On failure: log warning, return `"SYNC_FAILED: {error}"` (never raise)
    - Register in `WorkerSettings.functions` list
  - [x] 6.2 Hook into publish success flow in `core/publishing/publishing_service.py`:
    - After successful publish (`_on_success` or equivalent hook point):
      ```python
      # Fire-and-forget calendar sync (non-blocking)
      try:
          from core.scheduling.jobs import sync_calendar_event
          await arq_pool.enqueue_job("sync_calendar_event", item_id=str(item.id), action="published", instagram_url=result.permalink)
      except Exception:
          logger.warning("Calendar sync enqueue failed", exc_info=True)
      ```
    - **CRITICAL:** Calendar sync MUST NOT block the publish flow. Wrap in try/except.
  - [x] 6.3 Hook into schedule creation/update flow:
    - When `approval_items.scheduled_publish_time` is set or changed → enqueue `sync_calendar_event` with action="scheduled" or "rescheduled"
    - Check `ui/backend/routers/schedule.py` for the reschedule endpoint — add hook there
  - [x] 6.4 Hook into publish failure flow:
    - When publish fails → enqueue `sync_calendar_event` with action="failed"
  - [x] 6.5 Add cron job `_process_calendar_sync_queue` to retry failed syncs:
    - Runs every 15 minutes via ARQ cron
    - Queries approval_items where `scheduled_publish_time IS NOT NULL AND google_calendar_event_id IS NULL AND status IN ('approved', 'scheduled')`
    - Enqueues sync_calendar_event for each
    - Limit: process max 20 items per run (prevent thundering herd)
  - [x] 6.6 Write integration hook tests (target: 12+ tests)
    - Publish success → calendar sync enqueued
    - Publish success with calendar disabled → no sync enqueued
    - Schedule created → calendar sync enqueued
    - Schedule updated → calendar sync enqueued with "rescheduled"
    - Publish failed → calendar sync enqueued with "failed"
    - Calendar sync enqueue failure → publish not blocked
    - ARQ job creates event and stores event_id in DB
    - ARQ job updates event on reschedule
    - ARQ job updates event on publish
    - Retry cron finds unsynced items
    - Retry cron respects max 20 limit
    - Calendar client None → sync skipped gracefully

- [x] Task 7: FastAPI Router + Pydantic Schemas (AC: 1, 4, 5)
  - [x] 7.1 Create Pydantic schemas in `ui/backend/schemas/calendar.py`:
    - `CalendarSyncStatusResponse`:
      - `item_id: str`
      - `google_calendar_event_id: str | None`
      - `sync_status: str` ("synced", "pending", "failed", "disabled")
      - `last_synced_at: datetime | None`
    - `CalendarConfigResponse`:
      - `sync_enabled: bool`
      - `calendar_name: str`
      - `calendar_id: str | None`
    - `ManualSyncRequest`:
      - `item_ids: list[str]` (max 20)
  - [x] 7.2 Create `ui/backend/routers/calendar.py`:
    - `GET  /api/calendar/status` — calendar config + sync status summary
    - `GET  /api/calendar/sync/{item_id}` — sync status for specific item
    - `POST /api/calendar/sync` — manual sync for items (accepts ManualSyncRequest)
      - Validates item_ids exist
      - Enqueues sync_calendar_event for each
      - Returns count of items queued
    - `POST /api/calendar/setup` — create/verify DAWO Content calendar
      - Calls ensure_calendar_exists()
      - Stores calendar_id in config (or env)
      - Returns calendar_id
    - Dependency injection: `get_calendar_service()` with session
    - **Graceful degradation:** If CalendarCredentialsManager fails auth, return 503 with "Calendar not configured"
  - [x] 7.3 Register router in `ui/backend/routers/__init__.py`:
    - Add `from .calendar import router as calendar_router`
    - Add `"calendar_router"` to `__all__`
  - [x] 7.4 Write router tests (target: 10+ tests)
    - GET /api/calendar/status → 200 with config
    - GET /api/calendar/sync/{item_id} → 200 with sync status
    - GET /api/calendar/sync/{item_id} → 404 for missing item
    - POST /api/calendar/sync → 200 with count
    - POST /api/calendar/sync → 400 for too many items (>20)
    - POST /api/calendar/setup → 200 with calendar_id
    - POST /api/calendar/setup → 503 when not configured
    - Calendar disabled → appropriate response
    - Invalid item_id format → 422

- [x] Task 8: OAuth Setup Script (AC: 4)
  - [x] 8.1 Create `scripts/authorize_calendar.py`:
    - **Follow pattern from** `scripts/test_gmail_auth.py`
    - Run `InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)`
    - Call `flow.run_local_server(port=0)` for user consent
    - Save token to `credentials/calendar_token.json`
    - Verify token by calling `calendars().list()` (list user's calendars)
    - Print success message with instructions for setting GOOGLE_CALENDAR_ID env var
    - **One-time setup:** Only needed once, refresh token persists
  - [x] 8.2 Write setup script test (target: 3+ tests)
    - Script creates token file
    - Script verifies token with API call
    - Script handles already-authenticated scenario

- [x] Task 9: Registration + Exports (AC: all)
  - [x] 9.1 Register in `teams/dawo/team_spec.py`:
    - `RegisteredService(name="calendar_sync_service", service_class=CalendarSyncService, capabilities=["calendar", "content_sync"], requires_session=False)`
    - **RegisteredService** (not RegisteredAgent) — no LLM tier needed
  - [x] 9.2 Create `integrations/google_calendar/__init__.py` with `__all__`:
    - `CalendarClientProtocol`
    - `CalendarClient`
    - `CalendarCredentialsManager`
    - `CalendarSyncService`
    - `EventBuilder`
    - `CalendarConfig`
    - `CalendarEventData`
    - `CalendarSyncResult`
    - `CalendarAuthError`
    - `CalendarSyncError`
  - [x] 9.3 Write registration + export tests (target: 5+ tests)
    - All public classes importable from package
    - __all__ is complete
    - RegisteredService in team_spec
    - CalendarClientProtocol is runtime_checkable

- [x] Task 10: Integration Tests (AC: all)
  - [x] 10.1 Create `tests/integration/test_calendar_sync_integration.py`:
    - End-to-end: item scheduled → calendar event created → event_id stored in DB
    - End-to-end: item rescheduled → calendar event updated with new time
    - End-to-end: item published → calendar event updated with green color + permalink
    - End-to-end: item publish failed → calendar event updated with red color
    - Graceful degradation: calendar client unavailable → sync fails silently, publish succeeds
    - Retry cron: unsynced item → cron picks up → sync completes
    - Manual sync: POST /api/calendar/sync → items synced
    - Calendar auto-creation: first sync → calendar created → ID stored
    - Multiple items: batch manual sync respects limit
    - Config disabled: sync_enabled=False → all sync skipped
  - [x] 10.2 Target: 12+ integration tests (14 tests written, all passing)

## Dev Notes

### Critical: What Already Exists (DO NOT Rebuild)

**Reuse from `teams/dawo/leads/gmail/` (Story 5-4) — EXACT TEMPLATE:**
- `credentials_manager.py` — `GmailCredentialsManager` pattern for OAuth lifecycle
- `client.py` — `GmailClient` async wrapping pattern (`run_in_executor`)
- `config.py` — `GmailConfig` frozen dataclass with paths + scopes
- `scripts/test_gmail_auth.py` — Setup script pattern for initial OAuth consent

**Reuse from `core/scheduling/jobs.py` (Stories 7-6, 7-7, 7-8):**
- `_run_scheduled_agent()` — ARQ job pattern with lazy imports
- `WorkerSettings.functions` — job registration pattern
- `WorkerSettings.cron_jobs` — cron registration for retry sync
- Session management: `async with get_async_session() as session:`
- Fire-and-forget pattern: `await arq_pool.enqueue_job("job_name", ...)`

**Reuse from `core/publishing/publishing_service.py` (Epic 4):**
- `_on_success()` hook — where to inject calendar sync enqueue
- `PublishEventEmitter` — event emission pattern (not needed for calendar, but shows hook pattern)

**Reuse from `integrations/shopify/client.py` (Epic 3):**
- `ShopifyClientProtocol` — Protocol-based client interface pattern
- `@runtime_checkable` Protocol — for type-safe mocking
- Frozen dataclass DTOs — response objects pattern

**Reuse from `ui/backend/routers/schedule.py` (Epic 4):**
- `get_db_session()` — dependency injection pattern
- `ApprovalItemRepository` — DB access for approval items
- Reschedule endpoint — where to hook calendar sync on time change

**Reuse from `config/dawo_analytics.json` + `core/config.py`:**
- JSON config file pattern with env var interpolation
- Frozen dataclass config in `core/config.py`

### Architectural Decisions

**Separate Integration Package (NOT in teams/dawo/):**
- Calendar client goes in `integrations/google_calendar/` (alongside `integrations/shopify/`, `integrations/instagram/`)
- It's a platform integration, not a team-specific agent
- Follows existing integration directory structure

**Background Job for All Sync Operations (NOT Inline):**
- All calendar sync goes through ARQ `sync_calendar_event` job
- NEVER call CalendarClient directly from routers or publishing service
- Publishing service enqueues the job → job does the work → stores event_id
- This guarantees: non-blocking, retryable, observable via execution logs

**ApprovalItem Column (NOT Separate Table):**
- Add `google_calendar_event_id` to existing `approval_items` table
- Lightweight: one nullable VARCHAR column
- Enables upsert pattern: has event_id → update, no event_id → create
- Simpler than a separate sync tracking table for Phase 1

**User OAuth2 (NOT Service Account):**
- Service accounts can only access their own calendars (useless for operator)
- User OAuth2 with `InstalledAppFlow` → operator sees events in their personal Google Calendar
- Same approach as Gmail (Story 5-4), proven in production
- One-time setup, refresh token persists indefinitely

**events().patch() (NOT events().update()):**
- `patch()` only modifies specified fields
- `update()` requires ALL fields (clears anything not sent)
- Prevents accidentally clearing description when only updating color

**Retry via Cron (NOT Inline Retry):**
- Failed syncs are NOT retried immediately
- Cron job runs every 15 minutes, finds unsynced items, re-enqueues
- Prevents thundering herd on Google API outage
- Simple, reliable, observable

### No New Dependencies Required

Google Calendar API uses the same packages already in `requirements.txt`:
- `google-api-python-client>=2.0.0` — Calendar API client
- `google-auth>=2.0.0` — OAuth2 credentials
- `google-auth-oauthlib>=1.0.0` — OAuth2 consent flow

Build with: `build("calendar", "v3", credentials=creds)` (same pattern as Gmail's `build("gmail", "v1", credentials=creds)`)

### Google Calendar API Key Facts

- **Scope:** `https://www.googleapis.com/auth/calendar` (full read/write)
- **Rate limits:** 1M queries/day, 500/100s per user (extremely generous, no dedicated limiter needed)
- **Free:** No charges for API usage
- **Color IDs:** Integer strings: "9"=green (published), "10"=blue (scheduled), "11"=red (failed)
- **Extended properties:** `extendedProperties.private` for app-private key-value metadata
- **Async wrapping required:** API is synchronous, must use `run_in_executor()`
- **Token refresh:** Automatic if `creds.expired and creds.refresh_token` — handled by CredentialsManager
- **Batch API:** Up to 50 ops/request via `service.new_batch_http_request()` — optional for Phase 1 (typical 1-5 events/day)

### File Structure

```
integrations/google_calendar/
    __init__.py                        # Protocol + public exports + __all__
    credentials_manager.py             # CalendarCredentialsManager (OAuth lifecycle)
    client.py                          # CalendarClient (async API wrapper)
    dtos.py                            # CalendarEventData, CalendarSyncResult
    event_builder.py                   # ApprovalItem → Calendar Event mapping
    sync_service.py                    # CalendarSyncService (orchestrator)

config/
    dawo_calendar.json                 # Calendar config (calendar_name, color_ids, etc.)

core/config.py                         # Extended: CalendarConfig frozen dataclass
core/scheduling/jobs.py                # Extended: sync_calendar_event job + cron retry
core/publishing/publishing_service.py  # Extended: calendar sync hook on publish success
core/approval/models.py                # Extended: google_calendar_event_id column

migrations/versions/
    2026_03_01_001_add_calendar_event_id.py  # Add column to approval_items

scripts/
    authorize_calendar.py              # Initial OAuth token generation (one-time)

ui/backend/routers/
    __init__.py                        # Updated: register calendar router
    calendar.py                        # NEW: Calendar sync endpoints
    schedule.py                        # Extended: hook calendar sync on reschedule

ui/backend/schemas/
    calendar.py                        # NEW: Pydantic request/response schemas

tests/integrations/google_calendar/
    test_credentials_manager.py        # ~10 tests
    test_client.py                     # ~15 tests
    test_event_builder.py              # ~10 tests
    test_sync_service.py               # ~15 tests
    test_dtos.py                       # ~5 tests

tests/core/test_scheduling/
    test_calendar_sync_job.py          # ~8 tests

tests/ui/backend/test_routers/
    test_calendar.py                   # ~10 tests

tests/integration/
    test_calendar_sync_integration.py  # ~12 tests
```

### Database Change

```sql
ALTER TABLE approval_items
ADD COLUMN google_calendar_event_id VARCHAR(255) NULL;

CREATE INDEX idx_approval_items_calendar_event_id
ON approval_items(google_calendar_event_id);
```

### Testing Approach (Proven Patterns from 7-6, 7-7, 7-8)

- **Protocol-based mocking:** `AsyncMock(spec=CalendarClientProtocol)` for all client tests
- **Frozen dataclasses:** CalendarEventData, CalendarSyncResult are immutable
- **Constructor injection:** CalendarSyncService accepts all deps via constructor
- **run_in_executor mocking:** Mock the underlying sync API call, not the executor wrapper
- **Router tests:** `app.dependency_overrides` for service mocking, `httpx.AsyncClient`
- **Integration tests:** Full flow from publish → enqueue → sync → DB update
- **`datetime.now(UTC)`** not `datetime.utcnow()` (deprecated)
- **sys.modules patching:** For jobs.py tests that need to mock `core.database`
- Tests mirror source: `tests/integrations/google_calendar/` matches `integrations/google_calendar/`

### Previous Story Intelligence (from 7-8)

**What Worked Well:**
- Lazy imports in jobs.py avoided circular dependencies
- Fire-and-forget pattern (try/except: pass) kept main flow unblocked
- Frozen dataclass DTOs kept API contracts clean
- Protocol-based testing enabled clean mocking
- Router tests with `app.dependency_overrides` for service AND Redis pool
- ExecutionEventEmitter pub/sub pattern (could be used for calendar sync events)

**What to Watch For:**
- Must lazy-import CalendarSyncService and CalendarClient in ARQ jobs
- Calendar sync MUST be wrapped in try/except — NEVER block publish flow
- `ensure_calendar_exists()` should cache result (don't call Google API every sync)
- Don't forget `__all__` exports in every new `__init__.py`
- `sys.modules` patching needed for any test importing from `core.scheduling.jobs`
- Google Calendar API is synchronous — ALL calls MUST use `run_in_executor()`
- Token refresh must be handled in CredentialsManager, not in client methods

### Anti-Patterns to Avoid

- **DO NOT** call CalendarClient directly from routers — always enqueue ARQ job
- **DO NOT** block publish flow on calendar sync — fire-and-forget via ARQ
- **DO NOT** reuse Gmail token for Calendar — separate token file
- **DO NOT** use `events().update()` — use `events().patch()` to avoid clearing fields
- **DO NOT** use service account — use User OAuth2 for operator's calendar
- **DO NOT** create dedicated rate limiter — 1M/day quota is more than enough
- **DO NOT** use `datetime.utcnow()` — use `datetime.now(UTC)`
- **DO NOT** skip `__all__` exports in any `__init__.py`
- **DO NOT** store calendar credentials in code — use `credentials/` directory
- **DO NOT** call Google API without `run_in_executor()` — blocks async event loop
- **DO NOT** retry calendar sync inline — use cron-based retry (every 15 min)

### Google Cloud Console Setup (One-Time Prerequisites)

1. Enable Google Calendar API in Google Cloud Console (same project as Gmail)
2. OAuth consent screen already configured (from Gmail setup)
3. Add scope `https://www.googleapis.com/auth/calendar` to consent screen
4. Run `python scripts/authorize_calendar.py` for initial token
5. Set `GOOGLE_CALENDAR_ID` env var (or let auto-creation populate it)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.9]
- [Source: _bmad-output/planning-artifacts/prd.md#System Administration, FR54]
- [Source: _bmad-output/planning-artifacts/architecture.md#External Integration Points]
- [Source: _bmad-output/project-context.md#Agent Registration, Configuration Loading, External API Calls]
- [Source: teams/dawo/leads/gmail/credentials_manager.py — OAuth lifecycle pattern]
- [Source: teams/dawo/leads/gmail/client.py — async wrapping pattern]
- [Source: teams/dawo/leads/gmail/config.py — GmailConfig frozen dataclass]
- [Source: integrations/shopify/client.py — Protocol-based client pattern]
- [Source: integrations/instagram/client.py — Instagram publish client pattern]
- [Source: core/publishing/publishing_service.py — publish success hook point]
- [Source: core/scheduling/jobs.py — ARQ job pattern, WorkerSettings]
- [Source: ui/backend/routers/schedule.py — content scheduling endpoints]
- [Source: config/dawo_analytics.json — JSON config pattern]
- [Source: core/config.py — frozen dataclass config pattern]
- [Source: docs/research/google-calendar-api.md — API research]
- [Source: _bmad-output/implementation-artifacts/7-8-execution-logs-status-dashboard.md — previous story]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- Context crashed mid-Task 6.1 due to context window limit; resumed in new session
- Fixed corrupted `jobs.py` (`_process_calendar_sync_queue` truncated, `WorkerSettings` class declaration missing)
- Fixed `test_returns_sync_disabled_when_disabled`: patch target corrected from `core.scheduling.jobs.get_config` to `core.config.get_config` (lazy import)

### Completion Notes List

- All 10 tasks complete (Tasks 1-5 in first session, Tasks 6-10 in recovery session)
- Total new tests: 19 (calendar sync job) + 14 (router) + 4 (auth script) + 8 (registration/exports) + 14 (integration) = **59 tests, all passing**
- Follows existing patterns: Gmail credentials manager, Shopify protocol-based client, ARQ jobs, fire-and-forget hooks
- Calendar sync never blocks publish flow (try/except on all hook points)
- Cron retry every 15 min for unsynced items (max 20 per batch)
- Color IDs: "10"=blue (scheduled), "9"=green (published), "11"=red (failed)
- `ensure_calendar_exists()` cached after first call per service instance

### File List

**New Files:**
- `config/dawo_calendar.json` — Calendar config (Task 1)
- `integrations/google_calendar/__init__.py` — Package exports, CalendarClientProtocol (Task 1)
- `integrations/google_calendar/credentials_manager.py` — OAuth lifecycle (Task 1)
- `integrations/google_calendar/client.py` — CalendarClient async API wrapper (Task 2)
- `integrations/google_calendar/dtos.py` — CalendarEventData, CalendarSyncResult (Task 3)
- `integrations/google_calendar/event_builder.py` — ApprovalItem → Calendar Event mapping (Task 4)
- `integrations/google_calendar/sync_service.py` — CalendarSyncService orchestrator (Task 5)
- `scripts/authorize_calendar.py` — OAuth setup script (Task 8)
- `ui/backend/routers/calendar.py` — Calendar sync endpoints (Task 7)
- `ui/backend/schemas/calendar.py` — Pydantic request/response schemas (Task 7)
- `migrations/versions/2026_03_01_001_add_calendar_event_id.py` — DB migration (Task 1)
- `tests/integrations/google_calendar/test_credentials_manager.py` — ~10 tests (Task 1)
- `tests/integrations/google_calendar/test_client.py` — ~15 tests (Task 2)
- `tests/integrations/google_calendar/test_dtos.py` — ~5 tests (Task 3)
- `tests/integrations/google_calendar/test_event_builder.py` — ~10 tests (Task 4)
- `tests/integrations/google_calendar/test_sync_service.py` — ~15 tests (Task 5)
- `tests/integrations/google_calendar/test_authorize_script.py` — 4 tests (Task 8)
- `tests/integrations/google_calendar/test_registration_exports.py` — 8 tests (Task 9)
- `tests/core/test_scheduling/test_calendar_sync_job.py` — 19 tests (Task 6)
- `tests/ui/backend/test_routers/test_calendar.py` — 14 tests (Task 7)
- `tests/integration/test_calendar_sync_integration.py` — 14 tests (Task 10)

**Modified Files:**
- `core/config.py` — Added CalendarConfig frozen dataclass (Task 1)
- `core/approval/models.py` — Added google_calendar_event_id column (Task 1)
- `core/scheduling/jobs.py` — Added sync_calendar_event job, cron retry, publish hooks (Task 6)
- `ui/backend/routers/schedule.py` — Reschedule calendar sync hook (Task 6)
- `ui/backend/routers/__init__.py` — Registered calendar_router (Task 7)
- `teams/dawo/team_spec.py` — Registered CalendarSyncService (Task 9)
- `requirements.txt` — No new deps needed (google-api-python-client already present)

### Code Review Record

**Reviewer:** Claude Opus 4.6 (Amelia — BMAD Dev Agent)
**Date:** 2026-02-25
**Result:** PASS with fixes applied (9 findings, all resolved)

**Findings and Fixes:**

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| H1 | HIGH | AC3 requires checkmark prefix on published events; code used "Published: " | Changed to "✓ " prefix in `event_builder.py` |
| H2 | HIGH | Duplicate `CalendarClientProtocol` in `sync_service.py` (untyped) vs `__init__.py` (typed) | Consolidated: canonical typed Protocol in `sync_service.py`, imported by `__init__.py` |
| M1 | MEDIUM | Prefix text ("✓ ", "FAILED: ") not subtracted from max_title_length budget | Added `reserve` param to `_truncate_title()`, callers pass prefix length |
| M2 | MEDIUM | `CalendarConfig` missing from `__init__.py` `__all__` | Added import + export |
| M3 | MEDIUM | `remove_event()` skipped `sync_enabled` check (all other methods had it) | Added guard at top of method |
| M4 | MEDIUM | Redis pool created inline per-request in calendar router | Extracted `_get_redis_pool()` helper |
| L1 | LOW | File List claimed `core/publishing/events.py` modified for calendar event types (not true) | Removed misleading entry |
| L2 | LOW | Pre-existing `datetime.utcnow()` (deprecated) in `schedule.py` (4 occurrences) | Replaced with `datetime.now(UTC)` + added UTC import |
| L3 | LOW | `asyncio.get_event_loop()` (deprecated) in `client.py` (7 occurrences) | Replaced with `asyncio.get_running_loop()` |
