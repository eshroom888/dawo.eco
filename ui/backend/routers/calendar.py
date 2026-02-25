"""FastAPI router for Calendar Sync API.

Story 7-9, Task 7.2: Endpoints for Google Calendar sync management.

Endpoints:
    GET  /api/calendar/status         — calendar config + sync summary
    GET  /api/calendar/sync/{item_id} — sync status for specific item
    POST /api/calendar/sync           — manual sync for items (max 20)
    POST /api/calendar/setup          — create/verify DAWO Content calendar
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ui.backend.schemas.calendar import (
    CalendarConfigResponse,
    CalendarSetupResponse,
    CalendarSyncStatusResponse,
    ManualSyncRequest,
    ManualSyncResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


async def _get_redis_pool():
    """Create an ARQ Redis pool from environment config.

    Returns:
        ArqRedis pool (caller must close).

    Raises:
        Exception: If Redis is unreachable.
    """
    from arq import create_pool
    from arq.connections import RedisSettings

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return await create_pool(RedisSettings.from_dsn(redis_url))


async def get_db_session() -> AsyncSession:
    """Dependency to get database session.

    Placeholder — MUST be overridden via app.dependency_overrides[get_db_session]
    in the main application startup.
    """
    raise NotImplementedError(
        "Database session dependency not configured. "
        "Override get_db_session via app.dependency_overrides in application startup."
    )


@router.get("/status", response_model=CalendarConfigResponse)
async def get_calendar_status() -> CalendarConfigResponse:
    """Get calendar integration configuration and status.

    Story 7-9, Task 7.2: GET /api/calendar/status.
    """
    try:
        from core.config import get_config

        config = get_config().calendar
    except Exception as e:
        logger.warning("Calendar config not available: %s", e)
        raise HTTPException(
            status_code=503, detail="Calendar not configured"
        )

    return CalendarConfigResponse(
        sync_enabled=config.sync_enabled,
        calendar_name=config.calendar_name,
        calendar_id=config.calendar_id or None,
    )


@router.get("/sync/{item_id}", response_model=CalendarSyncStatusResponse)
async def get_sync_status(
    item_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> CalendarSyncStatusResponse:
    """Get calendar sync status for a specific approval item.

    Story 7-9, Task 7.2: GET /api/calendar/sync/{item_id}.
    """
    from uuid import UUID

    from core.approval.models import ApprovalItem
    from sqlalchemy import select

    try:
        item_uuid = UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid item_id format")

    query = select(ApprovalItem).where(ApprovalItem.id == item_uuid)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")

    # Determine sync status
    try:
        from core.config import get_config

        sync_enabled = get_config().calendar.sync_enabled
    except Exception:
        sync_enabled = False

    if not sync_enabled:
        status = "disabled"
    elif item.google_calendar_event_id:
        status = "synced"
    else:
        status = "pending"

    return CalendarSyncStatusResponse(
        item_id=item_id,
        google_calendar_event_id=getattr(item, "google_calendar_event_id", None),
        sync_status=status,
        last_synced_at=item.updated_at if status == "synced" else None,
    )


@router.post("/sync", response_model=ManualSyncResponse)
async def manual_sync(
    request: ManualSyncRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ManualSyncResponse:
    """Manually trigger calendar sync for items.

    Story 7-9, Task 7.2: POST /api/calendar/sync.
    Validates item IDs exist, enqueues sync for each.
    """
    from uuid import UUID

    from core.approval.models import ApprovalItem
    from sqlalchemy import select

    # Validate items exist
    try:
        item_uuids = [UUID(iid) for iid in request.item_ids]
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid item_id format in list")

    query = select(ApprovalItem.id).where(ApprovalItem.id.in_(item_uuids))
    result = await db.execute(query)
    found_ids = {str(row[0]) for row in result.all()}

    missing = set(request.item_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Items not found: {', '.join(missing)}",
        )

    # Enqueue sync for each item via ARQ
    queued = 0
    try:
        redis_pool = await _get_redis_pool()

        for item_id in request.item_ids:
            try:
                await redis_pool.enqueue_job(
                    "sync_calendar_event", item_id, "scheduled"
                )
                queued += 1
            except Exception as e:
                logger.warning("Failed to enqueue sync for %s: %s", item_id, e)

        await redis_pool.close()
    except Exception as e:
        logger.warning("Redis connection failed for manual sync: %s", e)

    return ManualSyncResponse(
        queued=queued,
        message=f"Queued {queued}/{len(request.item_ids)} items for calendar sync",
    )


@router.post("/setup", response_model=CalendarSetupResponse)
async def setup_calendar() -> CalendarSetupResponse:
    """Create or verify the DAWO Content Schedule calendar.

    Story 7-9, Task 7.2: POST /api/calendar/setup.
    Calls ensure_calendar_exists() and returns the calendar ID.
    """
    try:
        from core.config import get_config
        from integrations.google_calendar.client import CalendarClient
        from integrations.google_calendar.credentials_manager import (
            CalendarCredentialsManager,
        )

        config = get_config().calendar
        creds_manager = CalendarCredentialsManager(config)
        client = CalendarClient(creds_manager, config)

        calendar_id = await client.ensure_calendar_exists()

        return CalendarSetupResponse(
            calendar_id=calendar_id,
            calendar_name=config.calendar_name,
            message="Calendar verified/created successfully",
        )

    except Exception as e:
        logger.warning("Calendar setup failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Calendar not configured: {e}",
        )


__all__ = ["router"]
