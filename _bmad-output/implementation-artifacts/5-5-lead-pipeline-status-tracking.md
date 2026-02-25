# Story 5.5: Lead Pipeline Status Tracking

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want lead status tracked through pipeline stages with metrics and follow-up alerts,
So that I can monitor progress, follow up appropriately, and measure conversion performance.

---

## Acceptance Criteria

1. **Given** leads exist in the system
   **When** I view the lead pipeline dashboard
   **Then** I see leads organized by status:
   - `NEW` → awaiting enrichment
   - `QUALIFIED` → ready for outreach draft
   - `OUTREACH_PENDING` → awaiting approval
   - `CONTACTED` → email sent, awaiting response
   - `REPLIED` → received reply (manual update)
   - `CONVERTED` → became customer (manual update)
   - `LOST` → declined or unresponsive
   **And** intermediate statuses are also shown: `RESEARCHING`, `MEETING_SCHEDULED`, `NEGOTIATING`, `NURTURE`

2. **Given** a lead has been contacted
   **When** 7 days pass without response
   **Then** system flags the lead as needing follow-up
   **And** lead is visually highlighted in dashboard
   **And** the follow-up count is shown in the summary

3. **Given** I need pipeline metrics
   **When** I view the summary
   **Then** I see: leads by stage, conversion rate, average time in each stage
   **And** weekly trend of new discoveries vs. conversions

4. **Given** a lead status changes
   **When** the change is logged
   **Then** full history is preserved: status, timestamp, actor (system/operator)
   **And** I can view the complete journey of any lead

5. **Given** I need to manually update lead status
   **When** I change a lead to `REPLIED`, `MEETING_SCHEDULED`, `NEGOTIATING`, `CONVERTED`, or `LOST`
   **Then** the transition is validated and recorded with timestamp
   **And** activity log captures the change with optional reason/note

6. **Given** export is needed
   **When** I request lead export
   **Then** CSV download includes all lead data and status history
   **And** export respects any date/status filters applied

---

## Tasks / Subtasks

- [x] Task 1: Create Pipeline API schemas (AC: #1, #3, #4, #5, #6)
  - [x] 1.1 Create `ui/backend/schemas/pipeline.py` with Pydantic models
  - [x] 1.2 `PipelineLeadSchema` — lead summary for pipeline view (id, email, company, status, score, last_contacted_at, days_since_contact, needs_followup)
  - [x] 1.3 `PipelineSummarySchema` — status counts, conversion rate, avg time per stage, followup_count
  - [x] 1.4 `PipelineLeadListResponse` — paginated lead list with cursor
  - [x] 1.5 `LeadHistoryEntrySchema` — single activity record (type, description, timestamp, actor, metadata)
  - [x] 1.6 `LeadHistoryResponse` — list of history entries for a lead
  - [x] 1.7 `StatusUpdateRequest` — new_status, reason (optional), note (optional)
  - [x] 1.8 `StatusUpdateResponse` — updated lead with confirmation
  - [x] 1.9 `PipelineMetricsSchema` — conversion funnel, avg time per stage, weekly_new, weekly_converted
  - [x] 1.10 `LeadDetailSchema` — full lead detail (extends PipelineLeadSchema with enrichment_data, outreach_data, emails, activities)
  - [x] 1.11 `AddNoteRequest` — note text

- [x] Task 2: Extend LeadRepository with pipeline query methods (AC: #1, #2, #3, #4)
  - [x] 2.1 Add `get_pipeline_summary() -> dict` — counts per status across ALL LeadStatus values
  - [x] 2.2 Add `get_leads_filtered(status: Optional[LeadStatus], search: Optional[str], sort_by: str, limit: int, offset: int) -> tuple[Sequence[Lead], int]` — paginated, filterable lead query with total count
  - [x] 2.3 Add `get_lead_with_relations(lead_id: UUID) -> Optional[Lead]` — eager-load activities and emails
  - [x] 2.4 Add `get_lead_activities(lead_id: UUID, limit: int = 50) -> Sequence[LeadActivity]` — activity history ordered by created_at desc
  - [x] 2.5 Add `get_followup_candidates(days_threshold: int = 7) -> Sequence[Lead]` — leads where status=CONTACTED AND last_contacted_at < now - days_threshold AND last_replied_at is NULL
  - [x] 2.6 Add `get_conversion_metrics() -> dict` — total leads, leads per status, conversion rate (CONVERTED / total), avg days from NEW to each status
  - [x] 2.7 Add `get_weekly_trend(weeks: int = 8) -> list[dict]` — weekly new leads count and weekly converted count
  - [x] 2.8 Add `get_avg_time_per_stage() -> dict[str, float]` — average days leads spend in each status (calculated from activity log STATUS_CHANGE entries)

- [x] Task 3: Create Pipeline service (AC: #1, #2, #3, #5)
  - [x] 3.1 Create `teams/dawo/leads/pipeline/` directory with `__init__.py`
  - [x] 3.2 Create `schemas.py` with `PipelineSummary`, `ConversionMetrics`, `WeeklyTrend`, `FollowUpCandidate`, `StageTimingStats` dataclasses
  - [x] 3.3 Create `service.py` with `PipelineService` class
  - [x] 3.4 Accept `LeadRepository` via dependency injection
  - [x] 3.5 Implement `get_dashboard_summary() -> PipelineSummary`
  - [x] 3.6 Implement `get_metrics() -> ConversionMetrics`
  - [x] 3.7 Implement `update_lead_status(lead_id, new_status, reason, actor) -> Lead`
  - [x] 3.8 Implement `add_note(lead_id, note_text, actor) -> LeadActivity`
  - [x] 3.9 Implement `detect_followups(days_threshold: int = 7) -> list[FollowUpCandidate]`
  - [x] 3.10 Define `VALID_MANUAL_TRANSITIONS: dict[LeadStatus, set[LeadStatus]]`

- [x] Task 4: Create CSV export service (AC: #6)
  - [x] 4.1 Create `teams/dawo/leads/pipeline/csv_export.py` with `CSVExporter` class
  - [x] 4.2 Accept `LeadRepository` via injection
  - [x] 4.3 Implement `export_leads(status_filter, date_from, date_to) -> str`
  - [x] 4.4 Implement `export_lead_history(lead_id: UUID) -> str`
  - [x] 4.5 Use `io.StringIO` + `csv.writer` for in-memory CSV generation

- [x] Task 5: Create Pipeline FastAPI router (AC: #1, #2, #3, #4, #5, #6)
  - [x] 5.1 Create `ui/backend/routers/pipeline.py` with APIRouter(prefix="/api/pipeline", tags=["pipeline"])
  - [x] 5.2 `GET /api/pipeline/summary` → PipelineSummarySchema (status counts, followup count, conversion rate)
  - [x] 5.3 `GET /api/pipeline/metrics` → PipelineMetricsSchema (conversion funnel, avg time per stage, weekly trend)
  - [x] 5.4 `GET /api/pipeline/leads` → PipelineLeadListResponse (paginated, filterable: ?status=contacted&search=company&sort=score&limit=25&offset=0)
  - [x] 5.5 `GET /api/pipeline/leads/{lead_id}` → LeadDetailSchema (full lead detail with relations)
  - [x] 5.6 `GET /api/pipeline/leads/{lead_id}/history` → LeadHistoryResponse (activity log)
  - [x] 5.7 `POST /api/pipeline/leads/{lead_id}/status` → StatusUpdateResponse (manual status transition)
  - [x] 5.8 `POST /api/pipeline/leads/{lead_id}/note` → LeadHistoryEntrySchema (add manual note)
  - [x] 5.9 `GET /api/pipeline/followups` → list[PipelineLeadSchema] (leads needing follow-up)
  - [x] 5.10 `GET /api/pipeline/export` → StreamingResponse (CSV download, ?status=&date_from=&date_to=)
  - [x] 5.11 Set Content-Disposition header for CSV filename: `leads_export_{date}.csv`

- [x] Task 6: Register router and services (AC: #1)
  - [x] 6.1 Add `pipeline_router` to `ui/backend/routers/__init__.py`
  - [x] 6.2 Register `PipelineService` as RegisteredService in `teams/dawo/team_spec.py`
  - [x] 6.3 Register `CSVExporter` as RegisteredService in `teams/dawo/team_spec.py`
  - [x] 6.4 Mount router in FastAPI app (check `ui/backend/main.py` or equivalent)

- [x] Task 7: Create frontend Pipeline page (AC: #1, #2, #3, #5)
  - [x] 7.1 Create `ui/frontend-react/src/pages/Pipeline.tsx` — main pipeline dashboard page
  - [x] 7.2 Create `ui/frontend-react/src/hooks/usePipeline.ts` — data fetching hook for pipeline API
  - [x] 7.3 Create `ui/frontend-react/src/hooks/useLeadDetail.ts` — data fetching for single lead + history
  - [x] 7.4 Add Pipeline page to React Router (in App.tsx or route config) — N/A, no App.tsx/router exists; page exported as module

- [x] Task 8: Create frontend pipeline components (AC: #1, #2, #3)
  - [x] 8.1 Create `ui/frontend-react/src/components/pipeline/PipelineSummaryCards.tsx` — top-level metric cards (total leads, conversion rate, followup count, leads this week)
  - [x] 8.2 Create `ui/frontend-react/src/components/pipeline/PipelineStageColumn.tsx` — single status column with lead count badge
  - [x] 8.3 Create `ui/frontend-react/src/components/pipeline/LeadCard.tsx` — compact lead card (company, contact, score, days since contact, followup badge)
  - [x] 8.4 Create `ui/frontend-react/src/components/pipeline/FollowUpBadge.tsx` — visual indicator for overdue follow-ups
  - [x] 8.5 Create `ui/frontend-react/src/components/pipeline/PipelineFilters.tsx` — status filter, search input, sort dropdown
  - [x] 8.6 Create `ui/frontend-react/src/components/pipeline/LeadDetailDrawer.tsx` — slide-out drawer with full lead info, history timeline, status transition buttons
  - [x] 8.7 Create `ui/frontend-react/src/components/pipeline/StatusTransitionButton.tsx` — dropdown with valid next statuses + reason modal
  - [x] 8.8 Create `ui/frontend-react/src/components/pipeline/LeadHistoryTimeline.tsx` — vertical timeline of lead activities
  - [x] 8.9 Create `ui/frontend-react/src/components/pipeline/PipelineMetricsPanel.tsx` — conversion funnel chart + weekly trend
  - [x] 8.10 Create `ui/frontend-react/src/components/pipeline/CSVExportButton.tsx` — export trigger with filter params

- [x] Task 9: Create backend unit tests (AC: #1-#6)
  - [x] 9.1 Create `tests/teams/dawo/test_leads/test_pipeline/` directory with `__init__.py`, `conftest.py`
  - [x] 9.2 Test `PipelineService.get_dashboard_summary()` with various lead distributions
  - [x] 9.3 Test `PipelineService.update_lead_status()` valid transitions
  - [x] 9.4 Test `PipelineService.update_lead_status()` invalid transitions (raises error)
  - [x] 9.5 Test `PipelineService.update_lead_status()` sets converted_at, lost_reason, last_replied_at correctly
  - [x] 9.6 Test `PipelineService.detect_followups()` returns leads past threshold
  - [x] 9.7 Test `PipelineService.detect_followups()` excludes leads that already replied
  - [x] 9.8 Test `PipelineService.get_metrics()` conversion rate calculation
  - [x] 9.9 Test `PipelineService.add_note()` creates NOTE_ADDED activity
  - [x] 9.10 Test `CSVExporter.export_leads()` generates valid CSV with headers
  - [x] 9.11 Test `CSVExporter.export_leads()` respects status filter
  - [x] 9.12 Test `CSVExporter.export_leads()` respects date range filter
  - [x] 9.13 Test `CSVExporter.export_lead_history()` includes all activities
  - [x] 9.14 Test `LeadRepository.get_pipeline_summary()` counts all statuses
  - [x] 9.15 Test `LeadRepository.get_leads_filtered()` pagination and search
  - [x] 9.16 Test `LeadRepository.get_followup_candidates()` threshold logic
  - [x] 9.17 Test `LeadRepository.get_conversion_metrics()` calculations
  - [x] 9.18 Test `LeadRepository.get_weekly_trend()` aggregation
  - [x] 9.19 Test `LeadRepository.get_avg_time_per_stage()` from activity log
  - [x] 9.20 Test `LeadRepository.get_lead_with_relations()` eager loading
  - [x] 9.21 Test `VALID_MANUAL_TRANSITIONS` map completeness
  - [x] 9.22 Test Pipeline schema serialization (all Pydantic models)

- [x] Task 10: Create router/API tests (AC: #1-#6)
  - [x] 10.1 Test `GET /api/pipeline/summary` returns correct schema
  - [x] 10.2 Test `GET /api/pipeline/metrics` returns conversion data
  - [x] 10.3 Test `GET /api/pipeline/leads` pagination parameters
  - [x] 10.4 Test `GET /api/pipeline/leads` search filter
  - [x] 10.5 Test `GET /api/pipeline/leads/{id}` returns full detail
  - [x] 10.6 Test `GET /api/pipeline/leads/{id}` 404 for unknown lead
  - [x] 10.7 Test `GET /api/pipeline/leads/{id}/history` returns activities
  - [x] 10.8 Test `POST /api/pipeline/leads/{id}/status` valid transition
  - [x] 10.9 Test `POST /api/pipeline/leads/{id}/status` invalid transition returns 422
  - [x] 10.10 Test `POST /api/pipeline/leads/{id}/note` creates activity
  - [x] 10.11 Test `GET /api/pipeline/followups` returns flagged leads
  - [x] 10.12 Test `GET /api/pipeline/export` returns CSV with correct Content-Type
  - [x] 10.13 Test `GET /api/pipeline/export` with status filter

- [x] Task 11: Create integration tests (AC: #1-#6)
  - [x] 11.1 Test full pipeline flow: NEW → QUALIFIED → OUTREACH_PENDING → CONTACTED → REPLIED → CONVERTED
  - [x] 11.2 Test follow-up detection after simulated 7-day gap
  - [x] 11.3 Test manual status transitions with activity logging
  - [x] 11.4 Test CSV export includes correct lead data after status transitions
  - [x] 11.5 Test pipeline summary accuracy with mixed lead statuses
  - [x] 11.6 Test conversion metrics calculation end-to-end
  - [x] 11.7 Test weekly trend data accuracy

- [x] Task 12: Create frontend component tests (AC: #1, #2)
  - [x] 12.1 Test `PipelineSummaryCards` renders metric values
  - [x] 12.2 Test `LeadCard` displays lead info and follow-up badge
  - [x] 12.3 Test `StatusTransitionButton` shows valid next statuses
  - [x] 12.4 Test `LeadHistoryTimeline` renders activity entries
  - [x] 12.5 Test `PipelineFilters` emits correct filter events
  - [x] 12.6 Test `CSVExportButton` triggers download
  - [x] 12.7 Test `usePipeline` hook fetches and returns data

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This story completes Epic 5 (B2B Sales Pipeline) by adding the operator-facing pipeline dashboard. It builds on all 4 previous stories:
- Story 5-1: B2B Lead Research Scanner (creates leads with status=NEW)
- Story 5-2: Lead Information Enrichment (moves leads to QUALIFIED/RESEARCHING)
- Story 5-3: Personalized Outreach Draft Generator (moves leads to OUTREACH_PENDING)
- Story 5-4: Gmail API Integration (moves leads to CONTACTED)

This story adds: manual status updates (REPLIED, CONVERTED, LOST), follow-up detection, pipeline metrics, and the dashboard UI.

### Pipeline Data Flow

```
[Existing automated flow - Stories 5-1 through 5-4]
NEW → RESEARCHING → QUALIFIED → OUTREACH_PENDING → CONTACTED

[This story - manual operator updates + follow-up detection]
CONTACTED → REPLIED → MEETING_SCHEDULED → NEGOTIATING → CONVERTED
CONTACTED → LOST (after timeout or manual)
CONTACTED → NURTURE (long-term follow-up)
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure]

```
teams/dawo/leads/
├── __init__.py                    # ADD pipeline exports
├── repository.py                  # EXTEND with pipeline query methods
├── scanner/                       # FROM Story 5-1 (unchanged)
├── enrichment/                    # FROM Story 5-2 (unchanged)
├── outreach/                      # FROM Story 5-3 (unchanged)
├── gmail/                         # FROM Story 5-4 (unchanged)
└── pipeline/                      # CREATE THIS MODULE
    ├── __init__.py                # Export all public types
    ├── schemas.py                 # PipelineSummary, ConversionMetrics, etc.
    ├── service.py                 # PipelineService
    └── csv_export.py              # CSVExporter

ui/backend/
├── routers/
│   ├── __init__.py                # ADD pipeline_router
│   └── pipeline.py                # CREATE - Pipeline API endpoints
└── schemas/
    └── pipeline.py                # CREATE - Pydantic request/response models

ui/frontend-react/src/
├── pages/
│   └── Pipeline.tsx               # CREATE - Pipeline dashboard page
├── hooks/
│   ├── usePipeline.ts             # CREATE - Pipeline data hook
│   └── useLeadDetail.ts           # CREATE - Lead detail hook
└── components/pipeline/
    ├── PipelineSummaryCards.tsx    # Metric cards
    ├── PipelineStageColumn.tsx    # Status column with leads
    ├── LeadCard.tsx               # Compact lead card
    ├── FollowUpBadge.tsx          # Overdue indicator
    ├── PipelineFilters.tsx        # Search/filter controls
    ├── LeadDetailDrawer.tsx       # Slide-out detail view
    ├── StatusTransitionButton.tsx # Manual status change
    ├── LeadHistoryTimeline.tsx    # Activity timeline
    ├── PipelineMetricsPanel.tsx   # Funnel + trends
    └── CSVExportButton.tsx        # Export trigger

tests/teams/dawo/test_leads/
└── test_pipeline/                 # CREATE THIS
    ├── __init__.py
    ├── conftest.py                # Fixtures, mocks
    ├── test_schemas.py
    ├── test_service.py
    ├── test_csv_export.py
    └── test_repository_pipeline.py

tests/integration/
└── test_pipeline_integration.py   # CREATE THIS
```

### Existing Models to REUSE (DO NOT RECREATE)

**Source:** [core/leads/models.py]

```python
# Lead model — already has ALL pipeline fields:
from core.leads.models import (
    Lead,           # Full lead model with status, score, timestamps
    LeadActivity,   # Audit trail with activity_type, description, activity_metadata
    OutreachEmail,  # Email tracking with gmail IDs
    LeadStatus,     # NEW, RESEARCHING, QUALIFIED, OUTREACH_PENDING, CONTACTED,
                    # REPLIED, MEETING_SCHEDULED, NEGOTIATING, CONVERTED, LOST, NURTURE
    LeadSource,     # LINKEDIN, WEBSITE, REFERRAL, etc.
    EmailStatus,    # DRAFT, SENT, DELIVERED, etc.
    ActivityType,   # CREATED, STATUS_CHANGE, EMAIL_SENT, NOTE_ADDED, etc.
)
```

**Critical Lead fields already available:**
- `status` (String, indexed) — pipeline stage
- `score` (Float, indexed) — lead score 0-100
- `last_contacted_at` (DateTime) — for follow-up detection
- `last_replied_at` (DateTime) — to exclude replied leads from follow-up
- `contact_count` (Integer) — number of outreach attempts
- `next_followup_at` (DateTime) — scheduled follow-up time
- `converted_at` (DateTime) — conversion timestamp
- `lost_reason` (String) — why lead was lost
- `created_at` / `updated_at` — timestamps for metrics

**Critical LeadActivity fields:**
- `activity_type` (String) — maps to ActivityType enum
- `description` (Text) — human-readable description
- `activity_metadata` (JSONB, column name "metadata") — stores old_status, new_status, reason, etc.
- `created_by` (String) — "system" or operator email
- `created_at` (DateTime) — activity timestamp

### Existing Repository Methods to REUSE (DO NOT RECREATE)

**Source:** [teams/dawo/leads/repository.py]

```python
from teams.dawo.leads.repository import LeadRepository

# Already implemented:
repo.get_lead_by_id(lead_id)          # Get single lead
repo.get_leads_by_status(status)       # Filter by status
repo.update_lead_status(lead_id, status, reason)  # Change status + log activity
repo.count_leads_by_status()           # Count per status
repo.add_activity(lead_id, type, desc, metadata)   # Public activity creation
repo.mark_existing_customer(lead_id)   # Set CONVERTED status
repo._create_activity(...)             # Internal activity creation
```

**DO NOT duplicate** these methods. Call them from PipelineService. Only add new query methods for:
- Filtered/paginated lead listing
- Eager-loaded lead with relations
- Follow-up candidate detection
- Conversion metrics aggregation
- Weekly trend aggregation
- Average time per stage calculation

### Valid Status Transitions (CRITICAL)

**Source:** Derived from LeadStatus enum and pipeline flow

```python
VALID_MANUAL_TRANSITIONS: dict[str, set[str]] = {
    # Operator can manually move leads forward or to terminal states
    LeadStatus.NEW.value: {LeadStatus.RESEARCHING.value, LeadStatus.LOST.value},
    LeadStatus.RESEARCHING.value: {LeadStatus.QUALIFIED.value, LeadStatus.LOST.value},
    LeadStatus.QUALIFIED.value: {LeadStatus.OUTREACH_PENDING.value, LeadStatus.LOST.value, LeadStatus.NURTURE.value},
    LeadStatus.OUTREACH_PENDING.value: {LeadStatus.CONTACTED.value, LeadStatus.LOST.value},
    LeadStatus.CONTACTED.value: {LeadStatus.REPLIED.value, LeadStatus.LOST.value, LeadStatus.NURTURE.value},
    LeadStatus.REPLIED.value: {LeadStatus.MEETING_SCHEDULED.value, LeadStatus.NEGOTIATING.value, LeadStatus.CONVERTED.value, LeadStatus.LOST.value, LeadStatus.NURTURE.value},
    LeadStatus.MEETING_SCHEDULED.value: {LeadStatus.NEGOTIATING.value, LeadStatus.CONVERTED.value, LeadStatus.LOST.value},
    LeadStatus.NEGOTIATING.value: {LeadStatus.CONVERTED.value, LeadStatus.LOST.value},
    LeadStatus.NURTURE.value: {LeadStatus.CONTACTED.value, LeadStatus.LOST.value},
    # Terminal states — no transitions out
    LeadStatus.CONVERTED.value: set(),
    LeadStatus.LOST.value: {LeadStatus.NURTURE.value},  # Can reactivate lost leads to nurture
}
```

### Follow-Up Detection Logic

**Source:** AC #2, Epic 5 Story 5.5

```python
async def get_followup_candidates(self, days_threshold: int = 7) -> Sequence[Lead]:
    """Find leads that need follow-up.

    Criteria:
    - status = CONTACTED (email sent, no response)
    - last_contacted_at < now() - days_threshold
    - last_replied_at IS NULL (never replied)
    """
    cutoff = datetime.now(UTC) - timedelta(days=days_threshold)
    result = await self._session.execute(
        select(Lead)
        .where(
            Lead.status == LeadStatus.CONTACTED.value,
            Lead.last_contacted_at < cutoff,
            Lead.last_replied_at.is_(None),
        )
        .order_by(Lead.last_contacted_at.asc())
    )
    return result.scalars().all()
```

### Conversion Metrics Calculation

**Source:** AC #3

```python
# Conversion rate = CONVERTED leads / total leads (excluding NEW)
# Avg time per stage = calculate from LeadActivity STATUS_CHANGE entries

async def get_avg_time_per_stage(self) -> dict[str, float]:
    """Calculate average days spent in each status.

    Uses LeadActivity STATUS_CHANGE events to calculate duration
    between consecutive status transitions.
    """
    # Query all STATUS_CHANGE activities
    # For each lead, calculate time between consecutive status changes
    # Aggregate by status for averages
```

### CSV Export Format

**Source:** AC #6

```python
CSV_COLUMNS = [
    "id", "email", "first_name", "last_name", "company",
    "job_title", "status", "source", "score", "country",
    "industry", "created_at", "last_contacted_at",
    "contact_count", "converted_at", "lost_reason",
]
```

Use `io.StringIO` + `csv.writer` for in-memory generation. Return as `StreamingResponse` with:
```python
from fastapi.responses import StreamingResponse

return StreamingResponse(
    iter([csv_content]),
    media_type="text/csv",
    headers={"Content-Disposition": f"attachment; filename=leads_export_{date}.csv"},
)
```

### FastAPI Router Pattern

**Source:** [ui/backend/routers/approval_queue.py]

Follow the same pattern as approval_queue router:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

@router.get("/summary", response_model=PipelineSummarySchema)
async def get_pipeline_summary(
    session: AsyncSession = Depends(get_session),
) -> PipelineSummarySchema:
    repo = LeadRepository(session)
    service = PipelineService(repo)
    return await service.get_dashboard_summary()
```

### Frontend Patterns

**Source:** [ui/frontend-react/src/components/approval/], shadcn/ui

Follow existing approval queue component patterns:
- Use shadcn/ui `Card`, `Badge`, `Button`, `Sheet` (for drawer), `Table`
- Use Tailwind CSS for layout: `grid`, `flex`, responsive breakpoints
- Use custom hooks for data fetching (`usePipeline`, `useLeadDetail`)
- Use `fetch` for API calls (no axios — match existing pattern)
- Color coding for statuses: green (CONVERTED), blue (CONTACTED/REPLIED), yellow (NEW/QUALIFIED), red (LOST)
- Follow-up leads get amber/orange badge with "Needs follow-up" text

### Pipeline Dashboard Layout

```
┌──────────────────────────────────────────────┐
│ [Summary Cards: Total | Conversion | Followup]│
├──────────────────────────────────────────────┤
│ [Filters: Status ▼ | Search... | Sort ▼]    │
│ [Export CSV] [Show Metrics ▼]                │
├──────────────────────────────────────────────┤
│ Pipeline Board (Kanban-style columns)         │
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐  │
│ │NEW │ │QUAL│ │PEND│ │CONT│ │REPL│ │CONV│  │
│ │ 5  │ │ 3  │ │ 2  │ │ 4  │ │ 1  │ │ 2  │  │
│ │card│ │card│ │card│ │card│ │card│ │card│  │
│ │card│ │card│ │    │ │card│ │    │ │card│  │
│ │... │ │... │ │    │ │card│ │    │ │    │  │
│ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘  │
└──────────────────────────────────────────────┘
```

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

This story has NO agent — it's a backend API + frontend dashboard. No LLM tier assignment needed. PipelineService is a registered service, not an agent.

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

### Testing Strategy

**Source:** Previous story patterns (128 tests in 5-4, 181 tests in 5-3)

**Mock patterns:**
```python
# conftest.py
@pytest.fixture
def mock_lead_repository():
    """Mock LeadRepository for service tests."""
    repo = AsyncMock(spec=LeadRepository)
    repo.get_pipeline_summary.return_value = {
        "new": 5, "qualified": 3, "outreach_pending": 2,
        "contacted": 4, "replied": 1, "converted": 2, "lost": 1,
    }
    return repo

@pytest.fixture
def pipeline_service(mock_lead_repository):
    """PipelineService with mocked repository."""
    return PipelineService(mock_lead_repository)

@pytest.fixture
def sample_leads():
    """Generate sample Lead objects for testing."""
    # Use Lead model constructor with test data
    ...
```

**Test categories:**
- Pipeline service (summary, metrics, status transitions, follow-ups, notes)
- CSV exporter (format, filters, edge cases)
- Repository pipeline methods (queries, aggregation, pagination)
- API router (all endpoints, error cases, query params)
- Integration (full flow, status transitions, metric accuracy)
- Frontend components (rendering, interactions, hooks)

**Target:** ~100+ backend tests, ~20 frontend tests

### Previous Story Learnings (CRITICAL — Apply All)

**Source:** [5-4-gmail-api-integration.md#Completion-Notes]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | PipelineService and CSVExporter accept deps via constructor |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in time calculations |
| `activity_metadata` field naming | Use this field name for LeadActivity (DB column is "metadata") |
| Add logging to exception handlers | All exceptions logged before continuing |
| Protocol-based DI for tests | Service uses Protocol classes for dependency injection |
| TDD approach | Write tests first for each task |

### Database Considerations

**No new migrations needed.** All models (Lead, LeadActivity, OutreachEmail) already exist with all required fields. The pipeline queries use existing columns and relationships.

Existing indexes support pipeline queries:
- `idx_leads_pipeline` (status, score DESC) — for filtered lead listing
- `idx_leads_followup` (next_followup_at) — for follow-up detection
- `idx_leads_company_search` (company) — for search queries

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER load config directly** — Accept via injection
2. **NEVER create duplicate repository methods** — Reuse existing `update_lead_status()`, `count_leads_by_status()`, `add_activity()`
3. **NEVER use LLM model names** — Not applicable (no agent in this story)
4. **NEVER swallow exceptions without logging**
5. **NEVER allow invalid status transitions** — Validate against VALID_MANUAL_TRANSITIONS before updating
6. **NEVER expose lead personal data in logs** — Log lead_id, not email addresses
7. **NEVER recreate Lead/LeadActivity models** — Import from `core.leads.models`

### Existing Components to REUSE

```python
# Lead models and repository
from core.leads.models import Lead, LeadStatus, LeadActivity, ActivityType, LeadSource
from teams.dawo.leads.repository import LeadRepository

# Config loading pattern
from core.config import get_config

# Existing UI patterns
# Follow approval_queue.py router patterns
# Follow React approval components patterns for UI structure
```

### References

- [Source: epics.md#Story-5.5] — Original story requirements (FR21)
- [Source: core/leads/models.py] — Lead, LeadActivity, LeadStatus, ActivityType models
- [Source: teams/dawo/leads/repository.py] — LeadRepository to extend
- [Source: ui/backend/routers/approval_queue.py] — Router pattern to follow
- [Source: ui/backend/schemas/approval.py] — Schema pattern to follow
- [Source: ui/frontend-react/src/components/approval/] — Frontend component patterns
- [Source: 5-4-gmail-api-integration.md] — Previous story patterns and learnings
- [Source: project-context.md] — Critical implementation rules
- [Source: architecture.md#Project-Structure] — Directory organization

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- All 12 tasks implemented and passing
- Code review fixes applied: H1 double activity logging, H2 fragile field mutation, M1 N+1 query, M2 in-memory date filtering, M3 integration test flow, M4 missing exports, L1 type hints, L3 datetime UTC
- 88 tests (81 unit + 7 integration) all passing

### File List

- `teams/dawo/leads/pipeline/__init__.py` — Pipeline module exports
- `teams/dawo/leads/pipeline/schemas.py` — Frozen dataclasses (PipelineSummary, ConversionMetrics, WeeklyTrend, FollowUpCandidate, StageTimingStats)
- `teams/dawo/leads/pipeline/service.py` — PipelineService business logic, VALID_MANUAL_TRANSITIONS
- `teams/dawo/leads/pipeline/csv_export.py` — CSVExporter for lead data export
- `teams/dawo/leads/__init__.py` — Leads module exports (updated with pipeline types)
- `teams/dawo/leads/repository.py` — LeadRepository pipeline methods (get_pipeline_summary, get_leads_filtered, get_leads_by_ids, get_followup_candidates, etc.)
- `teams/dawo/team_spec.py` — RegisteredService entries for PipelineService and CSVExporter
- `ui/backend/schemas/pipeline.py` — 10 Pydantic API schemas
- `ui/backend/routers/pipeline.py` — FastAPI router with 9 endpoints
- `ui/backend/routers/__init__.py` — Router exports
- `core/leads/models.py` — LeadStatus enum, Lead/LeadActivity models
- `ui/frontend-react/src/pages/Pipeline.tsx` — Pipeline dashboard page
- `ui/frontend-react/src/hooks/usePipeline.ts` — Pipeline data hook
- `ui/frontend-react/src/types/pipeline.ts` — TypeScript types
- `ui/frontend-react/src/components/pipeline/index.ts` — Component barrel exports
- `ui/frontend-react/src/components/pipeline/PipelineSummaryCards.tsx`
- `ui/frontend-react/src/components/pipeline/PipelineStageColumn.tsx`
- `ui/frontend-react/src/components/pipeline/LeadCard.tsx`
- `ui/frontend-react/src/components/pipeline/FollowUpBadge.tsx`
- `ui/frontend-react/src/components/pipeline/PipelineFilters.tsx`
- `ui/frontend-react/src/components/pipeline/LeadDetailDrawer.tsx`
- `ui/frontend-react/src/components/pipeline/StatusTransitionButton.tsx`
- `ui/frontend-react/src/components/pipeline/LeadHistoryTimeline.tsx`
- `ui/frontend-react/src/components/pipeline/PipelineMetricsPanel.tsx`
- `ui/frontend-react/src/components/pipeline/CSVExportButton.tsx`
- `tests/teams/dawo/test_leads/test_pipeline/conftest.py` — Shared test fixtures
- `tests/teams/dawo/test_leads/test_pipeline/test_service.py` — 17 service tests
- `tests/teams/dawo/test_leads/test_pipeline/test_csv_export.py` — 7 CSV export tests
- `tests/teams/dawo/test_leads/test_pipeline/test_router.py` — 13 router tests
- `tests/teams/dawo/test_leads/test_pipeline/test_repository_pipeline.py` — 13 repository tests
- `tests/teams/dawo/test_leads/test_pipeline/test_schemas.py` — 24 schema tests
- `tests/integration/test_pipeline_integration.py` — 7 integration tests
- `ui/frontend-react/src/components/pipeline/__tests__/PipelineSummaryCards.test.tsx`
- `ui/frontend-react/src/components/pipeline/__tests__/LeadCard.test.tsx`
- `ui/frontend-react/src/components/pipeline/__tests__/StatusTransitionButton.test.tsx`
- `ui/frontend-react/src/components/pipeline/__tests__/LeadHistoryTimeline.test.tsx`
- `ui/frontend-react/src/components/pipeline/__tests__/PipelineFilters.test.tsx`
- `ui/frontend-react/src/components/pipeline/__tests__/CSVExportButton.test.tsx`
- `ui/frontend-react/src/hooks/__tests__/usePipeline.test.tsx`
- `migrations/versions/2026_02_09_002_add_outreach_data_to_leads.py` — DB migration
