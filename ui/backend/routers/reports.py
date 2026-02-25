"""FastAPI router for Reports API.

Story 6-10: On-Demand Violation Reports.
Provides endpoints for report generation, listing, download, and template info.

Endpoints:
    POST /api/reports/generate: Generate a violation report PDF
    GET  /api/reports: List generated reports (paginated)
    GET  /api/reports/{report_id}/download: Download report PDF
    GET  /api/reports/templates: List available templates
"""

import io
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from teams.dawo.scanners.evidence_collection.report_config import (
    ViolationReportConfig,
    build_violation_report_config,
)
from teams.dawo.scanners.evidence_collection.report_generator import (
    WeasyPrintPDFGenerator,
)
from teams.dawo.scanners.evidence_collection.report_schemas import (
    ViolationReportRequest,
)
from teams.dawo.scanners.evidence_collection.report_storage import (
    ReportStorageService,
)
from teams.dawo.scanners.evidence_collection.repository import EvidenceRepository
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService
from teams.dawo.scanners.evidence_collection.config import (
    EvidenceCollectionConfig,
    build_evidence_collection_config,
)
from ui.backend.schemas.reports import (
    AvailableTemplatesResponse,
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportListItemSchema,
    ReportListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

DEFAULT_LIMIT = 25
MAX_LIMIT = 100


async def get_db_session() -> AsyncSession:
    """Dependency to get database session.

    Placeholder — replaced by main application configuration.
    """
    raise NotImplementedError("Database session dependency not configured")


def get_report_config() -> ViolationReportConfig:
    """Dependency for violation report config. Override in tests."""
    config_path = Path("config/dawo_violation_reports.json")
    if config_path.exists():
        data = json.loads(config_path.read_text())
        return build_violation_report_config(data)
    return ViolationReportConfig()


def get_evidence_config() -> EvidenceCollectionConfig:
    """Dependency for evidence collection config. Override in tests."""
    config_path = Path("config/dawo_evidence_collection.json")
    if config_path.exists():
        data = json.loads(config_path.read_text())
        return build_evidence_collection_config(data)
    return EvidenceCollectionConfig()


def get_evidence_storage(
    evidence_config: EvidenceCollectionConfig = Depends(get_evidence_config),
) -> EvidenceStorageService:
    """Shared EvidenceStorageService dependency."""
    return EvidenceStorageService(config=evidence_config)


def get_repository(
    session: AsyncSession = Depends(get_db_session),
    storage_service: EvidenceStorageService = Depends(get_evidence_storage),
) -> EvidenceRepository:
    """Get EvidenceRepository with injected session."""
    return EvidenceRepository(session=session, storage_service=storage_service)


def get_report_storage(
    report_config: ViolationReportConfig = Depends(get_report_config),
) -> ReportStorageService:
    """Get ReportStorageService with injected config."""
    return ReportStorageService(config=report_config)


def get_generator(
    session: AsyncSession = Depends(get_db_session),
    repository: EvidenceRepository = Depends(get_repository),
    storage_service: EvidenceStorageService = Depends(get_evidence_storage),
    report_config: ViolationReportConfig = Depends(get_report_config),
) -> WeasyPrintPDFGenerator:
    """Get WeasyPrintPDFGenerator with all dependencies."""
    return WeasyPrintPDFGenerator(
        repository=repository,
        storage_service=storage_service,
        config=report_config,
        session=session,
    )


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO date string to timezone-aware datetime, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid date format: {value}"
        )


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(
    body: ReportGenerateRequest,
    generator: WeasyPrintPDFGenerator = Depends(get_generator),
    report_storage: ReportStorageService = Depends(get_report_storage),
    report_config: ViolationReportConfig = Depends(get_report_config),
) -> ReportGenerateResponse:
    """Generate a violation report PDF.

    Accepts evidence IDs or filter criteria to produce a PDF report.
    """
    # Validate template type
    if body.template_type not in report_config.available_templates:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid template_type: {body.template_type}. "
            f"Available: {report_config.available_templates}",
        )

    evidence_ids = [UUID(eid) for eid in body.evidence_ids] if body.evidence_ids else None

    request = ViolationReportRequest(
        evidence_ids=evidence_ids,
        competitor_name=body.competitor_name,
        date_from=_parse_date(body.date_from),
        date_to=_parse_date(body.date_to),
        template_type=body.template_type,
        report_title=body.report_title,
    )

    try:
        result = await generator.generate_report(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await report_storage.save_report(result)

    return ReportGenerateResponse(
        report_id=str(result.report_id),
        filename=result.filename,
        evidence_count=result.evidence_count,
        page_count=result.page_count,
        generated_at=result.generated_at,
        sha256_hash=result.sha256_hash,
        download_url=f"/api/reports/{result.report_id}/download",
    )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    report_storage: ReportStorageService = Depends(get_report_storage),
) -> ReportListResponse:
    """List generated reports with pagination."""
    items, total = await report_storage.list_reports(limit=limit, offset=offset)

    item_schemas = [
        ReportListItemSchema(
            report_id=str(m.report_id),
            filename=m.filename,
            evidence_count=m.evidence_count,
            competitor_name=m.competitor_name,
            template_type=m.template_type,
            generated_at=m.generated_at,
            sha256_hash=m.sha256_hash,
            page_count=m.page_count,
            file_size_bytes=m.file_size_bytes,
        )
        for m in items
    ]

    return ReportListResponse(
        items=item_schemas,
        total_count=total,
        has_more=(offset + limit) < total,
    )


@router.get("/templates", response_model=AvailableTemplatesResponse)
async def get_templates(
    report_config: ViolationReportConfig = Depends(get_report_config),
) -> AvailableTemplatesResponse:
    """List available report template types."""
    return AvailableTemplatesResponse(
        templates=report_config.available_templates
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    report_storage: ReportStorageService = Depends(get_report_storage),
) -> StreamingResponse:
    """Download a generated report PDF."""
    pdf_bytes = await report_storage.get_report(report_id)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Report not found")

    buffer = io.BytesIO(pdf_bytes)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report-{report_id}.pdf"
        },
    )


__all__ = ["router"]
