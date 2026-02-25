# Story 6.9: Searchable Evidence Database

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want violation evidence searchable and filterable,
So that I can find specific violations quickly for reporting.

---

## Acceptance Criteria

1. **Given** evidence exists in the database
   **When** I open the CleanMarket evidence view
   **Then** I see evidence records with: competitor, violation type, date, severity
   **And** thumbnails of screenshots are displayed
   **And** list loads in < 3 seconds for up to 1,000 records

2. **Given** I need to find specific evidence
   **When** I use search/filter
   **Then** I can filter by:
   - Competitor name
   - Violation type (treatment claims, prevention claims, etc.)
   - Date range
   - Severity level
   - Claim keywords

3. **Given** I click on an evidence record
   **When** detail view opens
   **Then** I see: full screenshot, claim text, regulation violated, source URL
   **And** I can download evidence package (screenshot + metadata)
   **And** evidence integrity hash is displayed

4. **Given** evidence links to competitor
   **When** I view competitor profile
   **Then** I see all violations by that competitor
   **And** violation trend over time is displayed

---

## Tasks / Subtasks

- [x] Task 1: Extend EvidenceRepository with search/filter methods (AC: #1, #2, #4)
  - [x] 1.1 Add `async def search(*, competitor_name, violation_type, severity, date_from, date_to, claim_keywords, source_type, sort_by, sort_order, limit, offset) -> tuple[list[Evidence], int]`
  - [x] 1.2 Add `async def get_by_id(evidence_id: UUID) -> Evidence | None` with eager-loaded violation + audit_logs
  - [x] 1.3 Add `async def get_summary_stats() -> EvidenceSummaryStats` — counts by severity, competitor, violation_type
  - [x] 1.4 Add `async def get_distinct_competitors() -> list[str]` — for filter dropdown
  - [x] 1.5 Add `async def get_competitor_timeline(competitor_name: str) -> list[dict]` — monthly violation counts for trend chart
  - [x] 1.6 Add `async def log_download(evidence_id: UUID) -> None` — audit log entry action="downloaded"

- [x] Task 2: Create API response schemas (AC: #1, #2, #3)
  - [x] 2.1 Create `ui/backend/schemas/evidence.py`
  - [x] 2.2 `EvidenceListItemSchema` — id, competitor_name, violation_type, severity, claim_text (truncated 100 chars), captured_at, source_type, screenshot_path, screenshot_hash
  - [x] 2.3 `EvidenceDetailSchema` — all fields + violation relationship + audit_logs list
  - [x] 2.4 `EvidenceListResponse` — items: list[EvidenceListItemSchema], total_count: int, has_more: bool
  - [x] 2.5 `EvidenceSummarySchema` — total_evidence: int, by_severity: dict, by_competitor: dict, by_violation_type: dict
  - [x] 2.6 `CompetitorTimelineEntry` — month: str, count: int
  - [x] 2.7 All schemas use `model_config = {"from_attributes": True}`

- [x] Task 3: Create API router (AC: #1, #2, #3, #4)
  - [x] 3.1 Create `ui/backend/routers/evidence.py` with `router = APIRouter(prefix="/api/evidence", tags=["evidence"])`
  - [x] 3.2 `GET /api/evidence/summary` -> EvidenceSummarySchema
  - [x] 3.3 `GET /api/evidence` -> EvidenceListResponse (query params: competitor, violation_type, severity, date_from, date_to, keywords, source_type, sort_by, sort_order, limit, offset)
  - [x] 3.4 `GET /api/evidence/{evidence_id}` -> EvidenceDetailSchema (eager load violation + audit_logs)
  - [x] 3.5 `GET /api/evidence/{evidence_id}/download` -> StreamingResponse (ZIP: screenshot.png + metadata.json)
  - [x] 3.6 `GET /api/evidence/competitors` -> list[str] (distinct competitor names)
  - [x] 3.7 `GET /api/evidence/competitors/{name}/timeline` -> list[CompetitorTimelineEntry]
  - [x] 3.8 FastAPI `Depends()` for session -> repository injection (follow pipeline.py pattern)

- [x] Task 4: Register router (AC: #1)
  - [x] 4.1 Add `from .evidence import router as evidence_router` to `ui/backend/routers/__init__.py`
  - [x] 4.2 Add `"evidence_router"` to `__all__`

- [x] Task 5: Create evidence download service (AC: #3)
  - [x] 5.1 Create `teams/dawo/scanners/evidence_collection/download.py` with `EvidenceDownloadService`
  - [x] 5.2 Accept `storage_service: EvidenceStorageService` via constructor
  - [x] 5.3 `async def create_evidence_package(evidence: Evidence) -> bytes` — returns ZIP bytes containing:
    - `screenshot.png` — original screenshot file
    - `metadata.json` — evidence record fields (id, competitor, claim, source_url, captured_at, hash, regulation, severity, confidence)
    - `integrity.txt` — SHA-256 hash + verification instructions
  - [x] 5.4 Uses `zipfile.ZipFile` with `io.BytesIO` (stdlib, no new deps)
  - [x] 5.5 Verify screenshot hash before packaging (integrity check)

- [x] Task 6: Create TypeScript types (AC: #1, #2, #3, #4)
  - [x] 6.1 Create `ui/frontend-react/src/types/evidence.ts`
  - [x] 6.2 `Evidence` interface matching EvidenceListItemSchema
  - [x] 6.3 `EvidenceDetail` interface matching EvidenceDetailSchema
  - [x] 6.4 `EvidenceListResponse` interface
  - [x] 6.5 `EvidenceSummary` interface
  - [x] 6.6 `EvidenceFilters` interface (all filter params)
  - [x] 6.7 `CompetitorTimelineEntry` interface
  - [x] 6.8 Display config constants: `SEVERITY_COLORS`, `VIOLATION_TYPE_LABELS`, `SOURCE_TYPE_LABELS`

- [x] Task 7: Create useEvidence hook (AC: #1, #2, #3, #4)
  - [x] 7.1 Create `ui/frontend-react/src/hooks/useEvidence.ts`
  - [x] 7.2 SWR fetcher for `/api/evidence` with filter params serialized to query string
  - [x] 7.3 SWR for `/api/evidence/summary`
  - [x] 7.4 SWR for `/api/evidence/competitors` (filter dropdown)
  - [x] 7.5 `useEvidenceDetail(id)` — SWR for single evidence detail
  - [x] 7.6 `useCompetitorTimeline(name)` — SWR for competitor trend data
  - [x] 7.7 Filter state management with `useState` for all filter params
  - [x] 7.8 `downloadEvidence(id)` function — fetch blob from `/api/evidence/{id}/download`, trigger browser download
  - [x] 7.9 Pagination state: page, pageSize with URL param sync
  - [x] 7.10 Auto-refresh interval: 30 seconds

- [x] Task 8: Create Evidence page components (AC: #1, #2, #3, #4)
  - [x] 8.1 Create `ui/frontend-react/src/components/evidence/` directory
  - [x] 8.2 `EvidenceSummaryCards.tsx` — total evidence count, severity breakdown cards (color-coded: red=high, yellow=medium, green=low)
  - [x] 8.3 `EvidenceFilters.tsx` — competitor dropdown (from /competitors endpoint), violation type select, severity select, date range pickers, keyword text input, clear filters button
  - [x] 8.4 `EvidenceCard.tsx` — list item card: screenshot thumbnail (64x64), competitor name, claim_text excerpt, severity badge, violation_type label, captured_at date, source_type icon
  - [x] 8.5 `EvidenceDetailDrawer.tsx` — slide-out drawer (right side): full screenshot image, all evidence fields, violation info, regulation violated, audit log timeline, download button, integrity hash display
  - [x] 8.6 `CompetitorProfile.tsx` — all violations by competitor, violation count trend chart (simple bar chart using CSS or recharts if available), timeline of violations
  - [x] 8.7 `ScreenshotPreview.tsx` — image component that loads screenshot from `/api/evidence/{id}/screenshot` path, click-to-zoom, loading skeleton

- [x] Task 9: Create Evidence page (AC: #1, #2, #3, #4)
  - [x] 9.1 Create `ui/frontend-react/src/pages/Evidence.tsx`
  - [x] 9.2 Layout: header ("CleanMarket Evidence" title + refresh button), summary cards row, filters row, evidence grid (responsive 1/2/3 columns), pagination controls
  - [x] 9.3 Empty state when no evidence
  - [x] 9.4 Loading skeleton state
  - [x] 9.5 Error state with retry
  - [x] 9.6 Click evidence card -> open EvidenceDetailDrawer
  - [x] 9.7 Click competitor name -> show CompetitorProfile view (or filter to that competitor)

- [x] Task 10: Update package exports (AC: all)
  - [x] 10.1 Update `teams/dawo/scanners/evidence_collection/__init__.py` — add EvidenceDownloadService to `__all__`
  - [x] 10.2 Register `EvidenceDownloadService` as RegisteredService in `team_spec.py`:
    - capabilities: `["competitor_monitoring", "evidence_download"]`
    - requires_session: False

- [x] Task 11: Create backend unit tests (AC: #1-#4)
  - [x] 11.1 Create `tests/teams/dawo/test_scanners/test_evidence_collection/test_search.py`
  - [x] 11.2 Test `search()` with no filters returns all evidence (paginated)
  - [x] 11.3 Test `search()` with competitor_name filter
  - [x] 11.4 Test `search()` with severity filter
  - [x] 11.5 Test `search()` with violation_type filter
  - [x] 11.6 Test `search()` with date_from + date_to range
  - [x] 11.7 Test `search()` with claim_keywords (ILIKE match)
  - [x] 11.8 Test `search()` with multiple combined filters
  - [x] 11.9 Test `search()` pagination (limit/offset, total_count)
  - [x] 11.10 Test `search()` sorting (captured_at desc/asc, severity, competitor_name)
  - [x] 11.11 Test `get_by_id()` returns evidence with violation + audit_logs
  - [x] 11.12 Test `get_by_id()` returns None for missing ID
  - [x] 11.13 Test `get_summary_stats()` correct counts
  - [x] 11.14 Test `get_distinct_competitors()` returns sorted unique names
  - [x] 11.15 Test `get_competitor_timeline()` returns monthly counts
  - [x] 11.16 Test `log_download()` creates audit entry
  - [x] 11.17 Create `tests/teams/dawo/test_scanners/test_evidence_collection/test_download.py`
  - [x] 11.18 Test `create_evidence_package()` returns valid ZIP bytes
  - [x] 11.19 Test ZIP contains screenshot.png + metadata.json + integrity.txt
  - [x] 11.20 Test metadata.json has correct evidence fields
  - [x] 11.21 Test hash verification failure raises error

- [x] Task 12: Create API router unit tests (AC: #1-#4)
  - [x] 12.1 Create `tests/teams/dawo/test_scanners/test_evidence_collection/test_router.py`
  - [x] 12.2 Test `GET /api/evidence/summary` returns summary stats
  - [x] 12.3 Test `GET /api/evidence` returns paginated list
  - [x] 12.4 Test `GET /api/evidence` with filter query params
  - [x] 12.5 Test `GET /api/evidence/{id}` returns detail
  - [x] 12.6 Test `GET /api/evidence/{id}` returns 404 for missing
  - [x] 12.7 Test `GET /api/evidence/{id}/download` returns ZIP
  - [x] 12.8 Test `GET /api/evidence/competitors` returns name list
  - [x] 12.9 Test `GET /api/evidence/competitors/{name}/timeline` returns timeline
  - [x] 12.10 Test pagination defaults (limit=25, offset=0)
  - [x] 12.11 Test pagination limits (max 100)

- [x] Task 13: Create frontend tests (AC: #1-#4)
  - [x] 13.1 Create `ui/frontend-react/src/hooks/__tests__/useEvidence.test.tsx`
  - [x] 13.2 Test useEvidence fetches evidence list
  - [x] 13.3 Test filter changes trigger re-fetch
  - [x] 13.4 Test pagination state management
  - [x] 13.5 Test downloadEvidence triggers blob download

- [x] Task 14: Create integration tests (AC: #1-#4)
  - [x] 14.1 Create `tests/integration/test_evidence_search_integration.py`
  - [x] 14.2 Test full search pipeline: create evidence -> search -> verify results
  - [x] 14.3 Test combined filters return correct subset
  - [x] 14.4 Test pagination returns correct pages
  - [x] 14.5 Test summary stats match actual data
  - [x] 14.6 Test competitor timeline aggregation
  - [x] 14.7 Test evidence download package integrity

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This is the **ninth story in Epic 6** (CleanMarket & Regulatory Intelligence). It's the **fifth story in the CleanMarket evidence chain** (Stories 6-5 through 6-10).

### Epic 6 Evidence Chain Position

```
Story 6-5 (done)      -> Scan competitor content -> Store in DB (competitor_content table)
Story 6-6 (done)      -> Extract health claims -> Store claims (extracted_health_claims table)
Story 6-7 (done)      -> Detect EU violations -> Store violations (competitor_violations table)
Story 6-8 (done)      -> Capture evidence screenshots -> Store evidence (evidence table)
Story 6-9 (this)      -> Search/filter evidence + UI -> Read-only queries on evidence table
Story 6-10            -> Generate PDF violation reports -> Read evidence for report inclusion
```

**Critical handoff IN:** Story 6-8 created `Evidence` model, `EvidenceRepository`, `EvidenceAuditLog`, `EvidenceStorageService`, and the evidence collection pipeline. This story EXTENDS `EvidenceRepository` with search/filter methods and builds the UI layer on top.

**Critical handoff OUT:** Story 6-10 will use `EvidenceRepository.search()` and `EvidenceRepository.get_by_id()` to select evidence records for PDF report generation. The download service pattern may also be reused for report attachments.

### Key Design Decision: Read-Only Search Layer

This story is **read-only** — no evidence is created, modified, or deleted. The immutability guarantees from Story 6-8 remain fully intact:
- `EvidenceRepository.update()` still ALWAYS raises `ImmutableEvidenceError`
- PostgreSQL trigger `prevent_evidence_update()` still blocks content field changes
- Only NEW audit log entries are created (action="downloaded", "searched")

### Search Strategy: ILIKE Over Full-Text Search

**Decision:** Use `ILIKE` for claim keyword search, NOT PostgreSQL `tsvector/tsquery`.

**Rationale:**
- AC specifies "up to 1,000 records" — ILIKE performs fine at this scale
- Existing indexes on `claim_text` not needed (sequential scan is acceptable for < 1,000 rows)
- Avoids migration complexity of adding tsvector columns + GIN indexes
- Keeps it simple — no new dependencies, no schema changes

```python
# Claim keyword search pattern
if claim_keywords:
    conditions.append(Evidence.claim_text.ilike(f"%{claim_keywords}%"))
```

### Pagination Strategy: Offset/Limit

**Decision:** Offset/limit pagination (NOT keyset/cursor).

**Rationale:**
- < 1,000 records — offset performance is excellent
- Simpler implementation, aligns with Pipeline router pattern
- Frontend can show page numbers for user orientation
- Default: limit=25, max=100 per page (matching Pipeline.py)

### Existing Code to REUSE (Not Reinvent)

| Component | Source | What to Use |
|-----------|--------|-------------|
| `EvidenceRepository` | `teams/dawo/scanners/evidence_collection/repository.py` | EXTEND with search methods — do NOT create a new repository |
| `Evidence` model | `core/regulatory/models.py` | All fields denormalized — no joins needed for filtering |
| `EvidenceAuditLog` model | `core/regulatory/models.py` | Log download + search actions |
| `EvidenceStorageService` | `teams/dawo/scanners/evidence_collection/storage.py` | `verify_integrity()` for hash verification before download |
| `ImmutableEvidenceError` | `teams/dawo/scanners/evidence_collection/schemas.py` | Keep enforcing in update() |
| Pipeline router pattern | `ui/backend/routers/pipeline.py` | Depends() injection, Query params, response models |
| Pipeline schemas | `ui/backend/schemas/pipeline.py` | Pydantic with `from_attributes=True`, Field descriptions |
| Pipeline hook | `ui/frontend-react/src/hooks/usePipeline.ts` | SWR pattern, filter state, fetcher function |
| Pipeline page | `ui/frontend-react/src/pages/Pipeline.tsx` | Page layout, component composition, state management |
| Pipeline types | `ui/frontend-react/src/types/pipeline.ts` | TypeScript interface patterns, enum patterns |

**CRITICAL: Do NOT create a new repository class.** Add methods to the existing `EvidenceRepository` in `teams/dawo/scanners/evidence_collection/repository.py`.

### Repository Search Method Pattern

```python
async def search(
    self,
    *,
    competitor_name: str | None = None,
    violation_type: str | None = None,
    severity: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    claim_keywords: str | None = None,
    source_type: str | None = None,
    sort_by: str = "captured_at",
    sort_order: str = "desc",
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[Evidence], int]:
    """Search evidence with filters. Returns (results, total_count)."""
    conditions: list = []

    if competitor_name:
        conditions.append(Evidence.competitor_name == competitor_name)
    if violation_type:
        conditions.append(Evidence.violation_type == violation_type)
    if severity:
        conditions.append(Evidence.severity == severity)
    if date_from:
        conditions.append(Evidence.captured_at >= date_from)
    if date_to:
        conditions.append(Evidence.captured_at <= date_to)
    if claim_keywords:
        conditions.append(Evidence.claim_text.ilike(f"%{claim_keywords}%"))
    if source_type:
        conditions.append(Evidence.source_type == source_type)

    where_clause = and_(*conditions) if conditions else True

    # Count query
    count_stmt = select(func.count(Evidence.id)).where(where_clause)
    total = await self._session.scalar(count_stmt) or 0

    # Sort
    sort_column = getattr(Evidence, sort_by, Evidence.captured_at)
    order = sort_column.desc() if sort_order == "desc" else sort_column.asc()

    # Data query
    stmt = (
        select(Evidence)
        .where(where_clause)
        .order_by(order)
        .limit(limit)
        .offset(offset)
    )
    result = await self._session.execute(stmt)
    evidence_list = list(result.scalars().all())

    return evidence_list, total
```

### Summary Stats Method Pattern

```python
async def get_summary_stats(self) -> dict:
    """Get evidence counts by severity, competitor, and violation_type."""
    # Total count
    total = await self._session.scalar(select(func.count(Evidence.id))) or 0

    # By severity
    severity_stmt = (
        select(Evidence.severity, func.count(Evidence.id))
        .group_by(Evidence.severity)
    )
    severity_result = await self._session.execute(severity_stmt)
    by_severity = {row[0]: row[1] for row in severity_result.all()}

    # By competitor
    competitor_stmt = (
        select(Evidence.competitor_name, func.count(Evidence.id))
        .group_by(Evidence.competitor_name)
        .order_by(func.count(Evidence.id).desc())
    )
    competitor_result = await self._session.execute(competitor_stmt)
    by_competitor = {row[0]: row[1] for row in competitor_result.all()}

    # By violation_type
    type_stmt = (
        select(Evidence.violation_type, func.count(Evidence.id))
        .group_by(Evidence.violation_type)
    )
    type_result = await self._session.execute(type_stmt)
    by_violation_type = {row[0]: row[1] for row in type_result.all()}

    return {
        "total_evidence": total,
        "by_severity": by_severity,
        "by_competitor": by_competitor,
        "by_violation_type": by_violation_type,
    }
```

### Competitor Timeline Method Pattern

```python
async def get_competitor_timeline(self, competitor_name: str) -> list[dict]:
    """Get monthly violation counts for a competitor. Returns [{month, count}, ...]."""
    stmt = (
        select(
            func.to_char(Evidence.captured_at, 'YYYY-MM').label('month'),
            func.count(Evidence.id).label('count'),
        )
        .where(Evidence.competitor_name == competitor_name)
        .group_by(func.to_char(Evidence.captured_at, 'YYYY-MM'))
        .order_by(text("month ASC"))
    )
    result = await self._session.execute(stmt)
    return [{"month": row.month, "count": row.count} for row in result.all()]
```

### API Router Pattern (Follow Pipeline.py)

```python
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
import io

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

DEFAULT_LIMIT = 25
MAX_LIMIT = 100

async def get_db_session() -> AsyncSession:
    raise NotImplementedError("Database session dependency not configured")

def get_repository(session: AsyncSession = Depends(get_db_session)) -> EvidenceRepository:
    storage_service = EvidenceStorageService(config=get_evidence_config())
    return EvidenceRepository(session=session, storage_service=storage_service)

@router.get("/summary", response_model=EvidenceSummarySchema)
async def get_summary(repo: EvidenceRepository = Depends(get_repository)):
    return await repo.get_summary_stats()

@router.get("", response_model=EvidenceListResponse)
async def list_evidence(
    competitor: Optional[str] = Query(default=None),
    violation_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    keywords: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None),
    sort_by: str = Query(default="captured_at"),
    sort_order: str = Query(default="desc"),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repo: EvidenceRepository = Depends(get_repository),
):
    items, total = await repo.search(
        competitor_name=competitor,
        violation_type=violation_type,
        severity=severity,
        date_from=parse_date(date_from),
        date_to=parse_date(date_to),
        claim_keywords=keywords,
        source_type=source_type,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total_count": total,
        "has_more": (offset + limit) < total,
    }
```

### Evidence Download Package Pattern

```python
import io
import json
import zipfile
from pathlib import Path

class EvidenceDownloadService:
    """Creates downloadable evidence packages (ZIP with screenshot + metadata)."""

    def __init__(self, storage_service: EvidenceStorageService):
        self._storage = storage_service

    async def create_evidence_package(self, evidence: Evidence) -> bytes:
        """Create ZIP package: screenshot.png + metadata.json + integrity.txt."""
        # 1. Verify integrity before packaging
        screenshot_path = Path(evidence.screenshot_path)
        if not screenshot_path.exists():
            raise FileNotFoundError(f"Screenshot not found: {evidence.screenshot_path}")

        screenshot_bytes = screenshot_path.read_bytes()
        actual_hash = hashlib.sha256(screenshot_bytes).hexdigest()
        if actual_hash != evidence.screenshot_hash:
            raise RuntimeError(f"Integrity check failed for evidence {evidence.id}")

        # 2. Build metadata JSON
        metadata = {
            "evidence_id": str(evidence.id),
            "competitor_name": evidence.competitor_name,
            "source_url": evidence.source_url,
            "source_type": evidence.source_type,
            "claim_text": evidence.claim_text,
            "claim_category": evidence.claim_category,
            "violation_type": evidence.violation_type,
            "severity": evidence.severity,
            "regulation_violated": evidence.regulation_violated,
            "confidence": evidence.confidence,
            "captured_at": evidence.captured_at.isoformat(),
            "screenshot_hash": evidence.screenshot_hash,
            "screenshot_size_bytes": evidence.screenshot_size_bytes,
        }

        # 3. Build integrity file
        integrity_text = (
            f"SHA-256: {evidence.screenshot_hash}\n"
            f"File: screenshot.png\n"
            f"Captured: {evidence.captured_at.isoformat()}\n"
            f"Verify: sha256sum screenshot.png\n"
        )

        # 4. Create ZIP
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("screenshot.png", screenshot_bytes)
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))
            zf.writestr("integrity.txt", integrity_text)

        return buffer.getvalue()
```

### Frontend Hook Pattern (Follow usePipeline.ts)

```typescript
import useSWR from "swr";
import { useState, useMemo, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const REFRESH_INTERVAL = 30000;

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

export function useEvidence() {
  const [filters, setFilters] = useState<EvidenceFilters>({});
  const [page, setPage] = useState(0);
  const pageSize = 25;

  // Build URL with filters
  const listUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (filters.competitor) params.set("competitor", filters.competitor);
    if (filters.severity) params.set("severity", filters.severity);
    if (filters.violationType) params.set("violation_type", filters.violationType);
    if (filters.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters.dateTo) params.set("date_to", filters.dateTo);
    if (filters.keywords) params.set("keywords", filters.keywords);
    params.set("limit", String(pageSize));
    params.set("offset", String(page * pageSize));
    return `${API_BASE}/evidence?${params.toString()}`;
  }, [filters, page]);

  const { data: evidence, error, isLoading, mutate } = useSWR<EvidenceListResponse>(
    listUrl, fetcher, { refreshInterval: REFRESH_INTERVAL }
  );

  const { data: summary } = useSWR<EvidenceSummary>(
    `${API_BASE}/evidence/summary`, fetcher, { refreshInterval: REFRESH_INTERVAL }
  );

  const { data: competitors } = useSWR<string[]>(
    `${API_BASE}/evidence/competitors`, fetcher
  );

  const downloadEvidence = useCallback(async (id: string) => {
    const response = await fetch(`${API_BASE}/evidence/${id}/download`);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `evidence-${id}.zip`;
    a.click();
    window.URL.revokeObjectURL(url);
  }, []);

  return { evidence, summary, competitors, filters, setFilters, page, setPage,
           pageSize, isLoading, error, refresh: mutate, downloadEvidence };
}
```

### Pydantic Response Schema Pattern (Follow pipeline.py)

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EvidenceListItemSchema(BaseModel):
    """Evidence summary for list view."""
    id: str = Field(..., description="Evidence UUID")
    competitor_name: str
    violation_type: str
    severity: str
    claim_text: str = Field(..., description="Claim text (may be truncated)")
    claim_category: str
    source_type: str
    source_url: str
    captured_at: datetime
    screenshot_path: str
    screenshot_hash: str

    model_config = {"from_attributes": True}

class EvidenceListResponse(BaseModel):
    """Paginated evidence list."""
    items: list[EvidenceListItemSchema]
    total_count: int = Field(..., ge=0)
    has_more: bool

    model_config = {"from_attributes": True}
```

### TypeScript Types Pattern (Follow pipeline.ts)

```typescript
export interface Evidence {
  id: string;
  competitor_name: string;
  violation_type: string;
  severity: string;
  claim_text: string;
  claim_category: string;
  source_type: string;
  source_url: string;
  captured_at: string;
  screenshot_path: string;
  screenshot_hash: string;
}

export const SEVERITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

export const VIOLATION_TYPE_LABELS: Record<string, string> = {
  violation: "Violation",
  suspect: "Suspect",
};
```

### Evidence Model Fields Available for Search (CRITICAL)

All fields are denormalized on the `Evidence` table — NO joins needed:

| Field | Type | Index | Filter Type |
|-------|------|-------|-------------|
| `competitor_name` | String(255) | composite (competitor_name, captured_at) | Exact match (dropdown) |
| `violation_type` | String(50) | ix_evidence_violation_type | Exact match (dropdown) |
| `severity` | String(20) | ix_evidence_severity | Exact match (dropdown) |
| `captured_at` | DateTime(tz) | ix_evidence_captured_at | Date range (from/to) |
| `claim_text` | Text | (none) | ILIKE keyword search |
| `source_type` | String(50) | (none) | Exact match (dropdown) |
| `claim_category` | String(50) | (none) | Exact match (optional) |

### Query Efficiency Guidelines

- **Filter by indexed columns** — competitor_name, severity, violation_type, captured_at all have indexes
- **No joins for list view** — all filter/display fields are on the Evidence table
- **Eager load ONLY for detail view** — `selectinload(Evidence.violation)`, `selectinload(Evidence.audit_logs)` only when fetching single evidence by ID
- **Separate count query** — `select(func.count(Evidence.id)).where(...)` before `select(Evidence).where(...).limit().offset()`
- **Use `result.scalars().all()`** — not `result.all()` (SQLAlchemy pattern)

### Screenshot Serving Strategy

Screenshots are stored on the file system at `evidence/screenshots/{YYYY-MM}/{uuid}.png`.

**For list view thumbnails (AC #1):** The frontend should display thumbnails using an `<img>` tag that loads the screenshot via a backend-served endpoint or static file path. Since screenshots are relative paths from project root, the backend should serve them:

```python
@router.get("/{evidence_id}/screenshot")
async def get_screenshot(
    evidence_id: UUID,
    repo: EvidenceRepository = Depends(get_repository),
):
    evidence = await repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")

    screenshot_path = Path(evidence.screenshot_path)
    if not screenshot_path.exists():
        raise HTTPException(404, "Screenshot file not found")

    return FileResponse(
        screenshot_path,
        media_type="image/png",
        filename=f"evidence-{evidence_id}.png",
    )
```

**For thumbnail display:** Use CSS `object-fit: cover; width: 64px; height: 64px;` on the `<img>` tag.

### Previous Story Learnings (CRITICAL — Apply All)

**Source:** [6-8-evidence-collection-screenshots.md#Completion-Notes]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, functions |
| Config injection pattern | All components accept deps via constructor |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in timestamps |
| `result.scalars().all()` vs `result.all()` | Use correct SQLAlchemy result extraction |
| `session.add` is sync in SQLAlchemy | Use `MagicMock()` not `AsyncMock()` for `session.add` in tests |
| No N+1 queries | Eager load relationships ONLY in detail view, never in list |
| Database filtering in SQL, not Python | All filters applied in SQL WHERE clause |
| Activity logging in one place | Repository logs audit entries, router does NOT |
| RegisteredAgent vs RegisteredService | EvidenceDownloadService is RegisteredService |
| Immutability MUST remain | Never add methods that modify evidence content |

### Testing Strategy

**Repository tests:** Mock `AsyncSession` with `AsyncMock`. Test filter combinations build correct WHERE clauses. Test pagination params (limit, offset) produce correct counts.

**Router tests:** Use `TestClient` or `httpx.AsyncClient` with FastAPI test pattern. Mock repository via `app.dependency_overrides`. Test query parameter parsing and validation.

**Frontend tests:** Mock SWR responses. Test filter state changes. Test download blob trigger.

**Integration tests:** Create real Evidence records in test DB. Execute searches with various filter combinations. Verify pagination, sorting, summary stats.

**Target: ~25 backend unit tests + ~11 router tests + ~4 frontend tests + ~6 integration tests = ~46 total**

### Anti-Patterns to AVOID (CRITICAL)

1. **NEVER modify evidence content** — immutability from Story 6-8 must remain
2. **NEVER join tables for list view** — all fields denormalized on Evidence table
3. **NEVER use `datetime.utcnow()`** — use `datetime.now(UTC)`
4. **NEVER create a new repository class** — extend existing `EvidenceRepository`
5. **NEVER load config directly** — accept via injection
6. **NEVER hardcode model names** — use `tier="scan"`, never model IDs
7. **NEVER swallow exceptions without logging** — always `logger.debug/error`
8. **NEVER use full-text search (tsvector)** — ILIKE is sufficient for < 1,000 records
9. **NEVER eager load relationships in list queries** — only in get_by_id detail view
10. **NEVER serve screenshots without hash verification** — verify before download

### New Dependencies

**None.** This story uses only existing dependencies:
- `zipfile` (stdlib) — for download packages
- `io` (stdlib) — for BytesIO buffer
- `json` (stdlib) — for metadata serialization
- All other deps already in requirements.txt

### Package Structure (MUST FOLLOW)

```
teams/dawo/scanners/evidence_collection/     # EXISTING — extend
|-- __init__.py                              # UPDATE: add EvidenceDownloadService
|-- repository.py                            # UPDATE: add search/filter/stats methods
+-- download.py                              # NEW: EvidenceDownloadService

ui/backend/schemas/
+-- evidence.py                              # NEW: Pydantic response schemas

ui/backend/routers/
|-- __init__.py                              # UPDATE: add evidence_router
+-- evidence.py                              # NEW: API router

ui/frontend-react/src/types/
+-- evidence.ts                              # NEW: TypeScript interfaces

ui/frontend-react/src/hooks/
+-- useEvidence.ts                           # NEW: SWR data fetching hook

ui/frontend-react/src/pages/
+-- Evidence.tsx                             # NEW: Main evidence page

ui/frontend-react/src/components/evidence/   # NEW directory
|-- EvidenceSummaryCards.tsx
|-- EvidenceFilters.tsx
|-- EvidenceCard.tsx
|-- EvidenceDetailDrawer.tsx
|-- CompetitorProfile.tsx
+-- ScreenshotPreview.tsx

tests/teams/dawo/test_scanners/test_evidence_collection/
|-- test_search.py                           # NEW: Repository search tests
|-- test_download.py                         # NEW: Download service tests
+-- test_router.py                           # NEW: API router tests

tests/integration/
+-- test_evidence_search_integration.py      # NEW: Integration tests
```

### Project Structure Notes

- Repository methods added to existing `EvidenceRepository` — no new repository class
- API router follows Pipeline.py patterns exactly (Depends, Query params, response models)
- Frontend follows Pipeline page patterns (SWR hooks, shadcn components, Tailwind styling)
- Download service is a simple stdlib-only ZIP packager — no new dependencies
- All queries use denormalized Evidence fields — zero joins for filtering
- Existing indexes cover all filter columns efficiently
- No database migrations needed — all indexes already exist from Story 6-8

### References

- [Source: epics.md#Story-6.9] — Original story requirements (FR33)
- [Source: architecture.md#DAWO-Team-Structure] — Directory structure, registration pattern
- [Source: project-context.md] — Critical implementation rules and anti-patterns
- [Source: epic-6-prep.md] — Epic 6 overview, pattern reuse table
- [Source: 6-8-evidence-collection-screenshots.md] — Previous story, Evidence model, EvidenceRepository, schemas, test patterns
- [Source: core/regulatory/models.py] — Evidence, EvidenceAuditLog models with indexes and relationships
- [Source: teams/dawo/scanners/evidence_collection/repository.py] — Existing repository methods to extend
- [Source: teams/dawo/scanners/evidence_collection/schemas.py] — Existing DTOs and ImmutableEvidenceError
- [Source: teams/dawo/scanners/evidence_collection/__init__.py] — Current exports to update
- [Source: teams/dawo/team_spec.py] — Registration patterns (RegisteredService)
- [Source: ui/backend/routers/pipeline.py] — API router pattern (Depends, Query, response models)
- [Source: ui/backend/schemas/pipeline.py] — Pydantic schema pattern (from_attributes, Field)
- [Source: ui/frontend-react/src/hooks/usePipeline.ts] — SWR hook pattern, filter state, fetcher
- [Source: ui/frontend-react/src/pages/Pipeline.tsx] — Page layout, component composition
- [Source: ui/frontend-react/src/types/pipeline.ts] — TypeScript interface patterns
- [Source: docs/pre-submission-checklist.md] — Quality checklist

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

Code review performed 2026-02-18 by Amelia (Dev Agent) — adversarial review found 9 issues (2 critical, 4 high, 3 medium), all fixed.

### Completion Notes List

- EvidenceRepository extended with search/filter/stats/timeline methods (Task 1)
- EvidenceDownloadService created for ZIP packaging with SHA-256 verification (Task 5)
- API router with 7 endpoints following Pipeline.py patterns (Task 3)
- Frontend: Evidence page with summary cards, filters, grid, detail drawer, competitor profile (Tasks 8-9)
- useEvidence hook with SWR, filter state, pagination, download (Task 7)
- TypeScript types with display config constants (Task 6)
- Router registered in __init__.py, service registered in team_spec.py (Tasks 4, 10)
- 16 repository unit tests, 4 download tests, 11+ router tests, 4 frontend tests, 8 integration tests (Tasks 11-14)
- **Code Review Fixes (2026-02-18):**
  - C1: Router download endpoint now uses EvidenceDownloadService (was inline ZIP with no hash verification)
  - H1: sort_by parameter whitelisted to ALLOWED_SORT_COLUMNS (was arbitrary getattr)
  - H2: Config loaded from JSON via get_evidence_config dependency (was hardcoded defaults)
  - H4: /screenshot and /download use get_by_id_lightweight (was unnecessary eager loading)
  - M1: Download audit log via BackgroundTasks (was committed before response sent)
  - M2: _parse_date enforces UTC on naive datetimes
  - M3: Integration tests use local MINIMAL_PNG_BYTES (was explicit conftest import)
- **H3 (Acknowledged):** Integration tests use mocked AsyncSession, not real DB — acceptable for Phase 1 scope

### File List

**Backend — Modified:**
- `teams/dawo/scanners/evidence_collection/repository.py` — Added ALLOWED_SORT_COLUMNS, search(), get_by_id(), get_by_id_lightweight(), get_summary_stats(), get_distinct_competitors(), get_competitor_timeline(), log_download()
- `teams/dawo/scanners/evidence_collection/__init__.py` — Added EvidenceDownloadService to exports
- `teams/dawo/team_spec.py` — Registered EvidenceDownloadService as RegisteredService
- `ui/backend/routers/__init__.py` — Added evidence_router import and __all__

**Backend — New:**
- `teams/dawo/scanners/evidence_collection/download.py` — EvidenceDownloadService (ZIP packaging with SHA-256 verification)
- `ui/backend/schemas/evidence.py` — Pydantic response schemas (6 schemas)
- `ui/backend/routers/evidence.py` — FastAPI router with 7 endpoints

**Frontend — New:**
- `ui/frontend-react/src/types/evidence.ts` — TypeScript interfaces + display constants
- `ui/frontend-react/src/hooks/useEvidence.ts` — SWR hooks (useEvidence, useEvidenceDetail, useCompetitorTimeline)
- `ui/frontend-react/src/pages/Evidence.tsx` — Main evidence search page
- `ui/frontend-react/src/components/evidence/EvidenceSummaryCards.tsx`
- `ui/frontend-react/src/components/evidence/EvidenceFilters.tsx`
- `ui/frontend-react/src/components/evidence/EvidenceCard.tsx`
- `ui/frontend-react/src/components/evidence/EvidenceDetailDrawer.tsx`
- `ui/frontend-react/src/components/evidence/CompetitorProfile.tsx`
- `ui/frontend-react/src/components/evidence/ScreenshotPreview.tsx`

**Tests — New:**
- `tests/teams/dawo/test_scanners/test_evidence_collection/test_search.py` — 19 repository search tests
- `tests/teams/dawo/test_scanners/test_evidence_collection/test_download.py` — 4 download service tests
- `tests/teams/dawo/test_scanners/test_evidence_collection/test_router.py` — 14 API router tests
- `tests/integration/test_evidence_search_integration.py` — 8 integration tests
- `ui/frontend-react/src/hooks/__tests__/useEvidence.test.tsx` — 4 frontend hook tests
