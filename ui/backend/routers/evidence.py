"""FastAPI router for Evidence API.

Story 6-9: Searchable Evidence Database.
Provides endpoints for evidence search, detail, download, and competitor analysis.

Endpoints:
    GET /api/evidence/summary: Evidence dashboard summary
    GET /api/evidence: Paginated, filtered evidence list
    GET /api/evidence/competitors: Distinct competitor names
    GET /api/evidence/{evidence_id}: Full evidence detail
    GET /api/evidence/{evidence_id}/download: Evidence package ZIP
    GET /api/evidence/{evidence_id}/screenshot: Screenshot image
    GET /api/evidence/competitors/{name}/timeline: Monthly violation counts
"""

import io
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from teams.dawo.scanners.evidence_collection.config import (
    EvidenceCollectionConfig,
    build_evidence_collection_config,
)
from teams.dawo.scanners.evidence_collection.download import EvidenceDownloadService
from teams.dawo.scanners.evidence_collection.repository import EvidenceRepository
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService
from ui.backend.schemas.evidence import (
    AuditLogEntrySchema,
    CompetitorTimelineEntry,
    EvidenceDetailSchema,
    EvidenceListItemSchema,
    EvidenceListResponse,
    EvidenceSummarySchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

DEFAULT_LIMIT = 25
MAX_LIMIT = 100


async def get_db_session() -> AsyncSession:
    """Dependency to get database session.

    Placeholder — replaced by main application configuration.
    """
    raise NotImplementedError("Database session dependency not configured")


def get_evidence_config() -> EvidenceCollectionConfig:
    """Dependency for evidence collection config. Override in tests."""
    config_path = Path("config/dawo_evidence_collection.json")
    if config_path.exists():
        data = json.loads(config_path.read_text())
        return build_evidence_collection_config(data)
    return EvidenceCollectionConfig()


def get_repository(
    session: AsyncSession = Depends(get_db_session),
    config: EvidenceCollectionConfig = Depends(get_evidence_config),
) -> EvidenceRepository:
    """Get EvidenceRepository with injected session and storage service."""
    storage_service = EvidenceStorageService(config=config)
    return EvidenceRepository(session=session, storage_service=storage_service)


def get_download_service(
    config: EvidenceCollectionConfig = Depends(get_evidence_config),
) -> EvidenceDownloadService:
    """Get EvidenceDownloadService with injected config."""
    storage_service = EvidenceStorageService(config=config)
    return EvidenceDownloadService(storage_service=storage_service)


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
        raise HTTPException(status_code=400, detail=f"Invalid date format: {value}")


@router.get("/summary", response_model=EvidenceSummarySchema)
async def get_summary(
    repo: EvidenceRepository = Depends(get_repository),
) -> EvidenceSummarySchema:
    """Get evidence dashboard summary stats."""
    stats = await repo.get_summary_stats()
    return EvidenceSummarySchema(**stats)


@router.get("/competitors", response_model=list[str])
async def get_competitors(
    repo: EvidenceRepository = Depends(get_repository),
) -> list[str]:
    """Get distinct competitor names for filter dropdown."""
    return await repo.get_distinct_competitors()


@router.get("/competitors/{name}/timeline", response_model=list[CompetitorTimelineEntry])
async def get_competitor_timeline(
    name: str,
    repo: EvidenceRepository = Depends(get_repository),
) -> list[CompetitorTimelineEntry]:
    """Get monthly violation counts for a competitor."""
    timeline = await repo.get_competitor_timeline(name)
    return [CompetitorTimelineEntry(**entry) for entry in timeline]


@router.get("", response_model=EvidenceListResponse)
async def list_evidence(
    competitor: Optional[str] = Query(default=None, description="Filter by competitor"),
    violation_type: Optional[str] = Query(default=None, description="Filter by violation type"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    date_from: Optional[str] = Query(default=None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(default=None, description="End date (ISO format)"),
    keywords: Optional[str] = Query(default=None, description="Claim text keyword search"),
    source_type: Optional[str] = Query(default=None, description="Filter by source type"),
    sort_by: str = Query(default="captured_at", description="Sort by field"),
    sort_order: str = Query(default="desc", description="Sort order (asc/desc)"),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repo: EvidenceRepository = Depends(get_repository),
) -> EvidenceListResponse:
    """Get paginated, filtered evidence list."""
    items, total = await repo.search(
        competitor_name=competitor,
        violation_type=violation_type,
        severity=severity,
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        claim_keywords=keywords,
        source_type=source_type,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    item_schemas = [
        EvidenceListItemSchema(
            id=str(e.id),
            competitor_name=e.competitor_name,
            violation_type=e.violation_type,
            severity=e.severity,
            claim_text=e.claim_text[:100] if e.claim_text else "",
            claim_category=e.claim_category,
            source_type=e.source_type,
            source_url=e.source_url,
            captured_at=e.captured_at,
            screenshot_path=e.screenshot_path,
            screenshot_hash=e.screenshot_hash,
        )
        for e in items
    ]

    return EvidenceListResponse(
        items=item_schemas,
        total_count=total,
        has_more=(offset + limit) < total,
    )


@router.get("/{evidence_id}", response_model=EvidenceDetailSchema)
async def get_evidence_detail(
    evidence_id: UUID,
    repo: EvidenceRepository = Depends(get_repository),
) -> EvidenceDetailSchema:
    """Get full evidence detail with relations."""
    evidence = await repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    audit_entries = [
        AuditLogEntrySchema(
            id=str(a.id),
            action=a.action,
            actor=a.actor,
            details=a.details,
            hash_verified=a.hash_verified,
            created_at=a.created_at,
        )
        for a in (evidence.audit_logs or [])
    ]

    return EvidenceDetailSchema(
        id=str(evidence.id),
        competitor_name=evidence.competitor_name,
        violation_type=evidence.violation_type,
        severity=evidence.severity,
        claim_text=evidence.claim_text,
        claim_category=evidence.claim_category,
        source_type=evidence.source_type,
        source_url=evidence.source_url,
        captured_at=evidence.captured_at,
        screenshot_path=evidence.screenshot_path,
        screenshot_hash=evidence.screenshot_hash,
        screenshot_size_bytes=evidence.screenshot_size_bytes,
        regulation_violated=evidence.regulation_violated,
        detection_reasoning=evidence.detection_reasoning,
        confidence=evidence.confidence,
        evidence_metadata=evidence.evidence_metadata,
        created_at=evidence.created_at,
        audit_logs=audit_entries,
    )


@router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: UUID,
    background_tasks: BackgroundTasks,
    repo: EvidenceRepository = Depends(get_repository),
    download_service: EvidenceDownloadService = Depends(get_download_service),
) -> StreamingResponse:
    """Download evidence package as ZIP (screenshot + metadata + integrity).

    Uses EvidenceDownloadService which verifies SHA-256 integrity before packaging.
    Audit log is recorded via background task after response is sent.
    """
    evidence = await repo.get_by_id_lightweight(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    try:
        package_bytes = await download_service.create_evidence_package(evidence)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Screenshot file not found")
    except RuntimeError as exc:
        logger.error("Evidence integrity failure: %s", exc)
        raise HTTPException(status_code=500, detail="Evidence integrity check failed")

    # Log download after response is sent
    background_tasks.add_task(_log_download_background, repo, evidence_id)

    buffer = io.BytesIO(package_bytes)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=evidence-{evidence_id}.zip"
        },
    )


async def _log_download_background(
    repo: EvidenceRepository, evidence_id: UUID
) -> None:
    """Background task: log evidence download in audit trail."""
    try:
        await repo.log_download(evidence_id)
        await repo.commit()
    except Exception:
        logger.exception("Failed to log download for evidence %s", evidence_id)


@router.get("/{evidence_id}/screenshot")
async def get_screenshot(
    evidence_id: UUID,
    repo: EvidenceRepository = Depends(get_repository),
) -> FileResponse:
    """Serve evidence screenshot image."""
    evidence = await repo.get_by_id_lightweight(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    screenshot_path = Path(evidence.screenshot_path)
    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot file not found")

    return FileResponse(
        screenshot_path,
        media_type="image/png",
        filename=f"evidence-{evidence_id}.png",
    )


__all__ = ["router"]
