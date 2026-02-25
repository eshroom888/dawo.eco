"""FastAPI router for Manual Trigger API.

Story 7-7, Task 5.2: Endpoints for manual agent/team triggering.

Endpoints:
    GET  /api/agents/triggerable        — list all triggerable agents (AC1)
    POST /api/agents/{agent_name}/trigger — trigger single agent (AC2)
    POST /api/agents/{agent_name}/queue   — queue for running agent (AC4)
    GET  /api/teams/                     — list all defined teams (AC3)
    POST /api/teams/{team_name}/trigger  — trigger team (AC3)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_config
from core.scheduling.manual_trigger_service import ManualTriggerService
from core.scheduling.schedule_repository import AgentScheduleRepository
from ui.backend.schemas.triggers import (
    TeamListResponse,
    TeamResponse,
    TeamTriggerResponse,
    TriggerAgentRequest,
    TriggerAgentResponse,
    TriggerableAgentListResponse,
    TriggerableAgentResponse,
    QueueAfterRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["triggers"])

# Path validation pattern (same as schedules router)
AGENT_NAME_PATTERN = r"^[a-z][a-z0-9_]{1,99}$"
TEAM_NAME_PATTERN = r"^[a-z][a-z0-9_]{1,99}$"


async def get_db_session() -> AsyncSession:
    """Dependency to get database session.

    Placeholder — replaced by main application configuration.
    """
    raise NotImplementedError("Database session dependency not configured")


def get_trigger_service(
    session: AsyncSession = Depends(get_db_session),
) -> ManualTriggerService:
    """Dependency to get ManualTriggerService.

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


@router.get("/api/agents/triggerable", response_model=TriggerableAgentListResponse)
async def list_triggerable_agents(
    service: ManualTriggerService = Depends(get_trigger_service),
) -> TriggerableAgentListResponse:
    """List all triggerable agents with current status."""
    agents = await service.get_triggerable_agents()
    return TriggerableAgentListResponse(
        agents=[
            TriggerableAgentResponse(
                agent_name=a.agent_name,
                display_name=a.display_name,
                description=a.description,
                last_run_status=a.last_run_status,
                last_run_at=a.last_run_at,
                last_run_duration_seconds=a.last_run_duration_seconds,
                is_running=a.is_running,
                schedule_cron=a.schedule_cron,
                next_scheduled_run=a.next_scheduled_run,
            )
            for a in agents
        ],
        total_count=len(agents),
    )


@router.post(
    "/api/agents/{agent_name}/trigger",
    response_model=TriggerAgentResponse,
)
async def trigger_agent(
    agent_name: str = Path(..., pattern=AGENT_NAME_PATTERN),
    body: TriggerAgentRequest = TriggerAgentRequest(),
    service: ManualTriggerService = Depends(get_trigger_service),
    arq_pool=Depends(get_arq_pool),
) -> TriggerAgentResponse:
    """Trigger a single agent for immediate execution."""
    result = await service.trigger_agent(
        agent_name,
        triggered_by="operator",
        config_overrides=body.config_overrides,
    )

    if result.status == "not_found":
        raise HTTPException(status_code=404, detail=result.message)

    if result.status == "already_running":
        if body.force:
            # Queue for after current run — do NOT enqueue immediately;
            # _check_pending_triggers will re-enqueue after current run completes
            queue_result = await service.queue_after_current(
                agent_name, triggered_by="operator"
            )
            return TriggerAgentResponse(
                agent_name=queue_result.agent_name,
                status="queued",
                job_id=None,
                triggered_at=queue_result.triggered_at,
                message="Queued for execution after current run completes",
            )
        raise HTTPException(
            status_code=409,
            detail=result.message,
        )

    # Enqueue ARQ job for immediate execution
    job = await arq_pool.enqueue_job("_run_scheduled_agent", agent_name, "manual")

    return TriggerAgentResponse(
        agent_name=result.agent_name,
        status=result.status,
        job_id=job.job_id if job else None,
        triggered_at=result.triggered_at,
        message=result.message,
    )


@router.post(
    "/api/agents/{agent_name}/queue",
    response_model=TriggerAgentResponse,
)
async def queue_agent(
    agent_name: str = Path(..., pattern=AGENT_NAME_PATTERN),
    service: ManualTriggerService = Depends(get_trigger_service),
) -> TriggerAgentResponse:
    """Queue a trigger for an agent that is currently running."""
    result = await service.queue_after_current(agent_name, triggered_by="operator")

    if result.status == "not_found":
        raise HTTPException(status_code=404, detail=result.message)

    if result.status == "not_running":
        raise HTTPException(
            status_code=400,
            detail=result.message,
        )

    return TriggerAgentResponse(
        agent_name=result.agent_name,
        status=result.status,
        job_id=result.job_id,
        triggered_at=result.triggered_at,
        message=result.message,
    )


@router.get("/api/teams/", response_model=TeamListResponse)
async def list_teams(
    service: ManualTriggerService = Depends(get_trigger_service),
) -> TeamListResponse:
    """List all defined teams."""
    teams = await service.get_teams()
    return TeamListResponse(
        teams=[
            TeamResponse(
                team_name=t.team_name,
                display_name=t.display_name,
                agents=t.agents,
                description=t.description,
            )
            for t in teams
        ],
    )


@router.post(
    "/api/teams/{team_name}/trigger",
    response_model=TeamTriggerResponse,
)
async def trigger_team(
    team_name: str = Path(..., pattern=TEAM_NAME_PATTERN),
    service: ManualTriggerService = Depends(get_trigger_service),
    arq_pool=Depends(get_arq_pool),
) -> TeamTriggerResponse:
    """Trigger all agents in a team in dependency order."""
    result = await service.trigger_team(team_name, triggered_by="operator")

    if result.total == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{team_name}' not found",
        )

    # Enqueue ARQ jobs for queued agents
    agent_responses: list[TriggerAgentResponse] = []
    for agent_result in result.agent_results:
        job_id = None
        if agent_result.status == "queued":
            job = await arq_pool.enqueue_job("_run_scheduled_agent", agent_result.agent_name, "manual")
            job_id = job.job_id if job else None

        agent_responses.append(TriggerAgentResponse(
            agent_name=agent_result.agent_name,
            status=agent_result.status,
            job_id=job_id,
            triggered_at=agent_result.triggered_at,
            message=agent_result.message,
        ))

    return TeamTriggerResponse(
        team_name=result.team_name,
        agent_results=agent_responses,
        total=result.total,
        queued=result.queued,
        skipped_running=result.skipped_running,
        failed=result.failed,
    )


__all__ = ["router"]
