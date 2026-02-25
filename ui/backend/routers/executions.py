"""FastAPI router for Execution Dashboard API.

Story 7-8, Task 7.2: Endpoints for execution dashboard.

Endpoints:
    GET  /api/executions/dashboard        — dashboard summary (AC1, AC2)
    GET  /api/executions/                 — filtered/paginated history (AC5)
    GET  /api/executions/{execution_id}   — single execution detail (AC3)
    POST /api/executions/{execution_id}/retry — retry failed execution (AC4)
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_config
from core.scheduling.dtos import ExecutionLogFilterDTO
from core.scheduling.execution_log_repository import ExecutionLogRepository
from core.scheduling.execution_log_service import ExecutionLogService
from core.scheduling.manual_trigger_service import ManualTriggerService
from core.scheduling.schedule_repository import AgentScheduleRepository
from ui.backend.schemas.executions import (
    DashboardSummaryResponse,
    ExecutionLogDetailResponse,
    ExecutionLogListResponse,
    ExecutionLogResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["executions"])


async def get_db_session() -> AsyncSession:
    """Dependency to get database session.

    Placeholder — replaced by main application configuration.
    """
    raise NotImplementedError("Database session dependency not configured")


def get_execution_service(
    session: AsyncSession = Depends(get_db_session),
) -> ExecutionLogService:
    """Dependency to get ExecutionLogService.

    Override in tests via app.dependency_overrides.
    """
    log_repo = ExecutionLogRepository(session)
    schedule_repo = AgentScheduleRepository(session)
    return ExecutionLogService(log_repo, schedule_repo)


def get_trigger_service(
    session: AsyncSession = Depends(get_db_session),
) -> ManualTriggerService:
    """Dependency to get ManualTriggerService for retry.

    Override in tests via app.dependency_overrides.
    """
    repo = AgentScheduleRepository(session)
    config = get_config().agent_scheduler
    return ManualTriggerService(repository=repo, config=config)


async def get_arq_pool(request: Request):
    """Dependency to get ARQ Redis pool from app state.

    Raises:
        HTTPException: 503 if Redis pool not available.
    """
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Job queue unavailable")
    return pool


def _dto_to_response(dto) -> ExecutionLogResponse:
    """Convert ExecutionLogDTO to ExecutionLogResponse."""
    return ExecutionLogResponse(
        id=str(dto.id),
        agent_name=dto.agent_name,
        display_name=dto.display_name,
        started_at=dto.started_at,
        completed_at=dto.completed_at,
        duration_seconds=dto.duration_seconds,
        status=dto.status,
        trigger_type=dto.trigger_type,
        triggered_by=dto.triggered_by,
        summary=dto.summary,
        error_message=dto.error_message,
        items_processed=dto.items_processed,
        has_log_output=dto.has_log_output,
    )


@router.get(
    "/api/executions/dashboard",
    response_model=DashboardSummaryResponse,
)
async def get_dashboard_summary(
    service: ExecutionLogService = Depends(get_execution_service),
) -> DashboardSummaryResponse:
    """Get execution dashboard summary.

    Returns currently running, recent completions, recent failures,
    and aggregate stats for the last 24 hours.
    """
    summary = await service.get_dashboard_summary()
    return DashboardSummaryResponse(
        running=[_dto_to_response(d) for d in summary.running],
        recent_completions=[_dto_to_response(d) for d in summary.recent_completions],
        recent_failures=[_dto_to_response(d) for d in summary.recent_failures],
        total_executions_24h=summary.total_executions_24h,
        success_rate_24h=summary.success_rate_24h,
        avg_duration_24h=summary.avg_duration_24h,
    )


@router.get(
    "/api/executions/",
    response_model=ExecutionLogListResponse,
)
async def list_executions(
    agent_name: Optional[str] = Query(default=None, description="Filter by agent"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    trigger_type: Optional[str] = Query(default=None, description="Filter by trigger"),
    date_from: Optional[datetime] = Query(default=None, description="Start date"),
    date_to: Optional[datetime] = Query(default=None, description="End date"),
    limit: int = Query(default=25, ge=1, le=100, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    service: ExecutionLogService = Depends(get_execution_service),
) -> ExecutionLogListResponse:
    """List execution logs with filtering and pagination."""
    filters = ExecutionLogFilterDTO(
        agent_name=agent_name,
        status=status,
        trigger_type=trigger_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    results, total = await service.get_filtered_executions(filters)
    return ExecutionLogListResponse(
        executions=[_dto_to_response(d) for d in results],
        total_count=total,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/api/executions/{execution_id}",
    response_model=ExecutionLogDetailResponse,
)
async def get_execution_detail(
    execution_id: str = Path(..., description="Execution log UUID"),
    service: ExecutionLogService = Depends(get_execution_service),
) -> ExecutionLogDetailResponse:
    """Get execution detail with log output."""
    # Validate UUID format
    try:
        UUID(execution_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid execution_id format")

    detail = await service.get_execution_detail(execution_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionLogDetailResponse(
        id=str(detail.id),
        agent_name=detail.agent_name,
        display_name=detail.display_name,
        started_at=detail.started_at,
        completed_at=detail.completed_at,
        duration_seconds=detail.duration_seconds,
        status=detail.status,
        trigger_type=detail.trigger_type,
        triggered_by=detail.triggered_by,
        summary=detail.summary,
        error_message=detail.error_message,
        items_processed=detail.items_processed,
        has_log_output=detail.has_log_output,
        log_output=detail.log_output,
        error_traceback=detail.error_traceback,
    )


@router.post(
    "/api/executions/{execution_id}/retry",
)
async def retry_execution(
    execution_id: str = Path(..., description="Execution log UUID to retry"),
    service: ExecutionLogService = Depends(get_execution_service),
    trigger_service: ManualTriggerService = Depends(get_trigger_service),
    arq_pool=Depends(get_arq_pool),
) -> dict:
    """Retry a failed execution.

    Extracts agent_name from execution log and delegates to
    ManualTriggerService.trigger_agent() (from Story 7-7),
    then enqueues the ARQ job for actual execution.
    """
    try:
        UUID(execution_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid execution_id format")

    detail = await service.get_execution_detail(execution_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    if detail.status not in ("failed", "incomplete"):
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed or incomplete executions, current status: {detail.status}",
        )

    result = await trigger_service.trigger_agent(
        agent_name=detail.agent_name,
        triggered_by="operator",
    )

    # Enqueue ARQ job for actual execution
    job_id = None
    if result.status == "queued":
        job = await arq_pool.enqueue_job(
            "_run_scheduled_agent", detail.agent_name, "manual",
        )
        job_id = job.job_id if job else None

    return {
        "agent_name": result.agent_name,
        "status": result.status,
        "job_id": job_id,
        "message": result.message,
        "triggered_at": result.triggered_at.isoformat(),
    }


__all__ = ["router"]
