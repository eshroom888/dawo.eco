"""FastAPI router for Pipeline API.

Story 5-5: Lead Pipeline Status Tracking.
Provides endpoints for pipeline dashboard, lead management,
status transitions, metrics, and CSV export.

Endpoints:
    GET /api/pipeline/summary: Pipeline dashboard summary
    GET /api/pipeline/metrics: Conversion funnel and trends
    GET /api/pipeline/leads: Paginated lead list
    GET /api/pipeline/leads/{lead_id}: Full lead detail
    GET /api/pipeline/leads/{lead_id}/history: Lead activity log
    POST /api/pipeline/leads/{lead_id}/status: Manual status transition
    POST /api/pipeline/leads/{lead_id}/note: Add manual note
    GET /api/pipeline/followups: Leads needing follow-up
    GET /api/pipeline/export: CSV download
"""

import logging
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.leads.models import LeadStatus, ActivityType
from teams.dawo.leads.repository import LeadRepository
from teams.dawo.leads.pipeline.service import PipelineService
from teams.dawo.leads.pipeline.csv_export import CSVExporter
from ui.backend.schemas.pipeline import (
    PipelineLeadSchema,
    PipelineSummarySchema,
    PipelineLeadListResponse,
    LeadHistoryEntrySchema,
    LeadHistoryResponse,
    StatusUpdateRequest,
    StatusUpdateResponse,
    PipelineMetricsSchema,
    LeadDetailSchema,
    AddNoteRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

DEFAULT_LIMIT = 25
MAX_LIMIT = 100


async def get_db_session() -> AsyncSession:
    """Dependency to get database session.

    Placeholder — replaced by main application configuration.
    """
    raise NotImplementedError("Database session dependency not configured")


def get_repository(session: AsyncSession = Depends(get_db_session)) -> LeadRepository:
    """Get LeadRepository with injected session."""
    return LeadRepository(session)


def get_pipeline_service(repo: LeadRepository = Depends(get_repository)) -> PipelineService:
    """Get PipelineService with injected repository."""
    return PipelineService(repo)


def get_csv_exporter(repo: LeadRepository = Depends(get_repository)) -> CSVExporter:
    """Get CSVExporter with injected repository."""
    return CSVExporter(repo)


def _lead_to_schema(lead, needs_followup: bool = False, days_since_contact: Optional[int] = None) -> PipelineLeadSchema:
    """Convert Lead model to PipelineLeadSchema."""
    return PipelineLeadSchema(
        id=str(lead.id),
        email=lead.email,
        first_name=lead.first_name,
        last_name=lead.last_name,
        company=lead.company,
        job_title=lead.job_title,
        status=lead.status,
        source=lead.source,
        score=lead.score,
        last_contacted_at=lead.last_contacted_at,
        days_since_contact=days_since_contact,
        needs_followup=needs_followup,
        contact_count=lead.contact_count,
        created_at=lead.created_at,
    )


@router.get("/summary", response_model=PipelineSummarySchema)
async def get_summary(
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineSummarySchema:
    """Get pipeline dashboard summary.

    Returns status counts, conversion rate, and follow-up count.
    """
    summary = await service.get_dashboard_summary()
    return PipelineSummarySchema(
        total_leads=summary.total_leads,
        status_counts=summary.status_counts,
        conversion_rate=summary.conversion_rate,
        avg_days_in_pipeline=summary.avg_days_in_pipeline,
        followup_count=summary.followup_count,
    )


@router.get("/metrics", response_model=PipelineMetricsSchema)
async def get_metrics(
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineMetricsSchema:
    """Get conversion funnel, average time per stage, and weekly trend."""
    metrics = await service.get_metrics()
    return PipelineMetricsSchema(
        conversion_rate=metrics.conversion_rate,
        total_leads=metrics.total_leads,
        converted_count=metrics.converted_count,
        avg_time_per_stage=metrics.avg_time_per_stage,
        weekly_trend=metrics.weekly_trend,
    )


@router.get("/leads", response_model=PipelineLeadListResponse)
async def get_leads(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    search: Optional[str] = Query(default=None, description="Search term"),
    sort: str = Query(default="score", description="Sort by field"),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repo: LeadRepository = Depends(get_repository),
) -> PipelineLeadListResponse:
    """Get paginated, filterable lead list."""
    lead_status = None
    if status:
        try:
            lead_status = LeadStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    leads, total = await repo.get_leads_filtered(
        status=lead_status,
        search=search,
        sort_by=sort,
        limit=limit,
        offset=offset,
    )

    lead_schemas = [_lead_to_schema(lead) for lead in leads]
    has_more = (offset + limit) < total

    return PipelineLeadListResponse(
        leads=lead_schemas,
        total_count=total,
        has_more=has_more,
        next_cursor=f"offset:{offset + limit}" if has_more else None,
    )


@router.get("/leads/{lead_id}", response_model=LeadDetailSchema)
async def get_lead_detail(
    lead_id: UUID,
    repo: LeadRepository = Depends(get_repository),
) -> LeadDetailSchema:
    """Get full lead detail with relations."""
    lead = await repo.get_lead_with_relations(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    activities = [
        LeadHistoryEntrySchema(
            id=str(a.id),
            lead_id=str(a.lead_id),
            activity_type=a.activity_type,
            description=a.description,
            timestamp=a.created_at,
            actor=a.created_by,
            metadata=a.activity_metadata,
        )
        for a in (lead.activities or [])
    ]

    return LeadDetailSchema(
        id=str(lead.id),
        email=lead.email,
        first_name=lead.first_name,
        last_name=lead.last_name,
        company=lead.company,
        job_title=lead.job_title,
        status=lead.status,
        source=lead.source,
        score=lead.score,
        last_contacted_at=lead.last_contacted_at,
        needs_followup=False,
        contact_count=lead.contact_count,
        created_at=lead.created_at,
        linkedin_url=lead.linkedin_url,
        website_url=lead.website_url,
        phone=lead.phone,
        country=lead.country,
        industry=lead.industry,
        company_size=lead.company_size,
        enrichment_data=lead.enrichment_data,
        outreach_data=lead.outreach_data,
        tags=lead.tags or [],
        notes=lead.notes,
        assigned_to=lead.assigned_to,
        next_followup_at=lead.next_followup_at,
        converted_at=lead.converted_at,
        lost_reason=lead.lost_reason,
        updated_at=lead.updated_at,
        activities=activities,
    )


@router.get("/leads/{lead_id}/history", response_model=LeadHistoryResponse)
async def get_lead_history(
    lead_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    repo: LeadRepository = Depends(get_repository),
) -> LeadHistoryResponse:
    """Get activity log for a lead."""
    activities = await repo.get_lead_activities(lead_id, limit=limit)

    entries = [
        LeadHistoryEntrySchema(
            id=str(a.id),
            lead_id=str(a.lead_id),
            activity_type=a.activity_type,
            description=a.description,
            timestamp=a.created_at,
            actor=a.created_by,
            metadata=a.activity_metadata,
        )
        for a in activities
    ]

    return LeadHistoryResponse(entries=entries)


@router.post("/leads/{lead_id}/status", response_model=StatusUpdateResponse)
async def update_lead_status(
    lead_id: UUID,
    request: StatusUpdateRequest,
    service: PipelineService = Depends(get_pipeline_service),
) -> StatusUpdateResponse:
    """Manually update lead status."""
    try:
        new_status = LeadStatus(request.new_status)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status: {request.new_status}")

    try:
        lead = await service.update_lead_status(
            lead_id=lead_id,
            new_status=new_status,
            reason=request.reason,
            actor="operator",  # TODO: extract from auth context
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return StatusUpdateResponse(
        success=True,
        lead=_lead_to_schema(lead),
        message=f"Status updated to {request.new_status}",
    )


@router.post("/leads/{lead_id}/note", response_model=LeadHistoryEntrySchema)
async def add_lead_note(
    lead_id: UUID,
    request: AddNoteRequest,
    service: PipelineService = Depends(get_pipeline_service),
) -> LeadHistoryEntrySchema:
    """Add a manual note to a lead."""
    try:
        activity = await service.add_note(
            lead_id=lead_id,
            note_text=request.note,
            actor="operator",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return LeadHistoryEntrySchema(
        id=str(activity.id),
        lead_id=str(activity.lead_id),
        activity_type=activity.activity_type,
        description=activity.description,
        timestamp=activity.created_at,
        actor=activity.created_by,
        metadata=activity.activity_metadata,
    )


@router.get("/followups", response_model=list[PipelineLeadSchema])
async def get_followups(
    service: PipelineService = Depends(get_pipeline_service),
    repo: LeadRepository = Depends(get_repository),
) -> list[PipelineLeadSchema]:
    """Get leads needing follow-up."""
    candidates = await service.detect_followups()
    if not candidates:
        return []

    # Batch fetch all leads in a single query
    lead_ids = [c.lead_id for c in candidates]
    leads = await repo.get_leads_by_ids(lead_ids)
    leads_by_id = {lead.id: lead for lead in leads}

    # Build candidate lookup for days_since_contact
    candidate_by_id = {c.lead_id: c for c in candidates}

    schemas = []
    for lead in leads:
        candidate = candidate_by_id.get(lead.id)
        schemas.append(_lead_to_schema(
            lead,
            needs_followup=True,
            days_since_contact=candidate.days_since_contact if candidate else None,
        ))

    return schemas


@router.get("/export")
async def export_leads_csv(
    status: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    exporter: CSVExporter = Depends(get_csv_exporter),
) -> StreamingResponse:
    """Export leads as CSV download."""
    status_filter = None
    if status:
        try:
            status_filter = LeadStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    df = None
    dt = None
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")

    csv_content = await exporter.export_leads(
        status_filter=status_filter,
        date_from=df,
        date_to=dt,
    )

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=leads_export_{today}.csv"
        },
    )


__all__ = ["router"]
