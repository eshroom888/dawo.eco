"""FastAPI router for Agent Schedule API.

Story 7-6, Task 7.2: Endpoints for schedule management.

Endpoints:
    GET  /api/schedules/             — list all agent schedules (AC1)
    GET  /api/schedules/{agent_name} — get single schedule
    PUT  /api/schedules/{agent_name} — update schedule (AC2), returns warnings (AC3)
    POST /api/schedules/{agent_name}/toggle — enable/disable (AC6)
    GET  /api/schedules/{agent_name}/audit  — get change log (AC2 audit trail)
    POST /api/schedules/seed         — manually trigger default seeding (AC5)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_config
from core.scheduling.dtos import ScheduleUpdateRequest
from core.scheduling.schedule_repository import AgentScheduleRepository
from core.scheduling.schedule_service import AgentScheduleService
from ui.backend.schemas.schedules import (
    AgentScheduleListResponse,
    AgentScheduleResponse,
    AuditLogResponse,
    DependencyWarningResponse,
    ScheduleChangeLogResponse,
    ScheduleUpdateRequestSchema,
    ScheduleUpdateResponse,
    SeedResponse,
    ToggleEnabledRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


async def get_db_session() -> AsyncSession:
    """Dependency to get database session.

    Placeholder — MUST be overridden via app.dependency_overrides[get_db_session]
    in the main application startup. Will raise at runtime if not configured.
    """
    raise NotImplementedError(
        "Database session dependency not configured. "
        "Override get_db_session via app.dependency_overrides in application startup."
    )


def get_schedule_service(
    session: AsyncSession = Depends(get_db_session),
) -> AgentScheduleService:
    """Dependency to get AgentScheduleService.

    Override in tests via app.dependency_overrides.
    """
    repo = AgentScheduleRepository(session)
    config = get_config().agent_scheduler
    return AgentScheduleService(repository=repo, config=config)


def _dto_to_response(dto) -> AgentScheduleResponse:
    """Convert AgentScheduleDTO to Pydantic response."""
    return AgentScheduleResponse(
        id=str(dto.id),
        agent_name=dto.agent_name,
        display_name=dto.display_name,
        description=dto.description,
        schedule_cron=dto.schedule_cron,
        cron_human_readable=dto.cron_human_readable,
        timezone=dto.timezone,
        enabled=dto.enabled,
        last_run_at=dto.last_run_at,
        last_run_status=dto.last_run_status,
        last_run_duration_seconds=dto.last_run_duration_seconds,
        next_run_at=dto.next_run_at,
        dependencies=dto.dependencies,
        config_source=dto.config_source,
    )


@router.get("/", response_model=AgentScheduleListResponse)
async def list_schedules(
    service: AgentScheduleService = Depends(get_schedule_service),
) -> AgentScheduleListResponse:
    """List all agent schedules."""
    schedules = await service.get_all_schedules()
    return AgentScheduleListResponse(
        schedules=[_dto_to_response(s) for s in schedules],
        total_count=len(schedules),
    )


# Static routes MUST be defined before parameterized routes
# to prevent "seed" from matching as {agent_name}.
@router.post("/seed", response_model=SeedResponse)
async def seed_defaults(
    service: AgentScheduleService = Depends(get_schedule_service),
) -> SeedResponse:
    """Manually trigger default schedule seeding."""
    count = await service.seed_defaults()
    return SeedResponse(seeded_count=count)


@router.get("/{agent_name}", response_model=AgentScheduleResponse)
async def get_schedule(
    agent_name: str = Path(..., pattern=r"^[a-z][a-z0-9_]{1,99}$"),
    service: AgentScheduleService = Depends(get_schedule_service),
) -> AgentScheduleResponse:
    """Get a single agent schedule."""
    dto = await service.get_schedule(agent_name)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {agent_name}")
    return _dto_to_response(dto)


@router.put("/{agent_name}", response_model=ScheduleUpdateResponse)
async def update_schedule(
    agent_name: str = Path(..., pattern=r"^[a-z][a-z0-9_]{1,99}$"),
    body: ScheduleUpdateRequestSchema = ...,
    service: AgentScheduleService = Depends(get_schedule_service),
) -> ScheduleUpdateResponse:
    """Update an agent schedule with audit logging.

    Returns updated schedule and any dependency warnings.
    """
    updates = ScheduleUpdateRequest(
        schedule_cron=body.schedule_cron,
        timezone=body.timezone,
        enabled=body.enabled,
        display_name=body.display_name,
        description=body.description,
        dependencies=body.dependencies,
    )

    try:
        dto = await service.update_schedule(agent_name, updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if dto is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {agent_name}")

    # Check dependency warnings if cron or timezone changed
    warnings = []
    if body.schedule_cron or body.timezone:
        dep_warnings = await service.check_dependencies(
            agent_name,
            dto.schedule_cron,
            dto.timezone,
        )
        warnings = [
            DependencyWarningResponse(
                agent_name=w.agent_name,
                dependency_name=w.dependency_name,
                agent_next_run=w.agent_next_run,
                dependency_next_run=w.dependency_next_run,
                warning_message=w.warning_message,
                severity=w.severity,
            )
            for w in dep_warnings
        ]

    return ScheduleUpdateResponse(
        schedule=_dto_to_response(dto),
        warnings=warnings,
    )


@router.post("/{agent_name}/toggle", response_model=AgentScheduleResponse)
async def toggle_enabled(
    agent_name: str = Path(..., pattern=r"^[a-z][a-z0-9_]{1,99}$"),
    body: ToggleEnabledRequest = ...,
    service: AgentScheduleService = Depends(get_schedule_service),
) -> AgentScheduleResponse:
    """Enable or disable an agent schedule."""
    dto = await service.toggle_enabled(agent_name, body.enabled)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {agent_name}")
    return _dto_to_response(dto)


@router.get("/{agent_name}/audit", response_model=AuditLogResponse)
async def get_audit_log(
    agent_name: str = Path(..., pattern=r"^[a-z][a-z0-9_]{1,99}$"),
    service: AgentScheduleService = Depends(get_schedule_service),
) -> AuditLogResponse:
    """Get change log entries for an agent."""
    logs = await service.get_audit_log(agent_name)
    entries = [
        ScheduleChangeLogResponse(
            id=entry.id,
            agent_name=entry.agent_name,
            field_changed=entry.field_changed,
            old_value=entry.old_value,
            new_value=entry.new_value,
            changed_by=entry.changed_by,
            created_at=entry.created_at,
        )
        for entry in logs
    ]
    return AuditLogResponse(entries=entries)


__all__ = ["router"]
