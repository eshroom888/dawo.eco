"""Schedule API router.

Story 4-4: Calendar scheduling endpoints for approved content.

Endpoints:
    GET /api/schedule/calendar - Get scheduled items for date range
    GET /api/schedule/optimal-times - Get optimal time suggestions
    PATCH /api/schedule/{item_id}/reschedule - Reschedule a post
"""

import logging
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ui.backend.schemas.schedule import (
    ScheduleCalendarResponse,
    ScheduledItemResponse,
    OptimalTimesResponse,
    OptimalTimeSlot,
    RescheduleSchema,
    RescheduleResponse,
    ConflictInfo,
    ConflictSeverity,
    RetryPublishRequest,
    RetryPublishResponse,
)
from ui.backend.repositories.approval_repository import ApprovalItemRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

# Constants
CONFLICT_WARNING_THRESHOLD = 2
CONFLICT_CRITICAL_THRESHOLD = 3
IMMINENT_THRESHOLD_SECONDS = 3600  # 1 hour


def get_quality_color(score: float) -> str:
    """Get quality color from score."""
    if score >= 8:
        return "green"
    if score >= 5:
        return "yellow"
    return "red"


def is_imminent(scheduled_time: datetime) -> bool:
    """Check if a scheduled time is within 1 hour."""
    if not scheduled_time:
        return False
    time_to_publish = (scheduled_time - datetime.utcnow()).total_seconds()
    return 0 < time_to_publish < IMMINENT_THRESHOLD_SECONDS


def truncate_caption(caption: str, max_length: int = 50) -> str:
    """Truncate caption for calendar display."""
    if len(caption) <= max_length:
        return caption
    return caption[: max_length - 3] + "..."


async def get_db() -> AsyncSession:
    """Database session dependency.

    Yields an async database session for request handling.
    Session is automatically closed after request completes.
    """
    try:
        from core.database import get_async_session
        async with get_async_session() as session:
            yield session
    except ImportError:
        # Fallback for when database module isn't configured yet
        from core.database import async_session_factory
        async with async_session_factory() as session:
            yield session


def detect_conflicts(items: list) -> list[ConflictInfo]:
    """Detect scheduling conflicts in a list of items.

    Story 4-4, Task 2.6: Include conflict indicators in response.

    Args:
        items: List of ApprovalItem objects

    Returns:
        List of ConflictInfo for hours with 2+ posts
    """
    # Group items by hour
    hour_groups: dict[str, list[str]] = {}

    for item in items:
        if not item.scheduled_publish_time:
            continue
        hour_key = item.scheduled_publish_time.strftime("%Y-%m-%dT%H:00:00")
        if hour_key not in hour_groups:
            hour_groups[hour_key] = []
        hour_groups[hour_key].append(str(item.id))

    # Find conflicts
    conflicts = []
    for hour_key, item_ids in hour_groups.items():
        if len(item_ids) >= CONFLICT_WARNING_THRESHOLD:
            severity = (
                ConflictSeverity.CRITICAL
                if len(item_ids) >= CONFLICT_CRITICAL_THRESHOLD
                else ConflictSeverity.WARNING
            )
            conflicts.append(
                ConflictInfo(
                    hour=datetime.fromisoformat(hour_key),
                    posts_count=len(item_ids),
                    post_ids=item_ids,
                    severity=severity,
                )
            )

    return conflicts


def add_conflict_ids_to_items(
    items: list,
    conflicts: list[ConflictInfo],
) -> dict[str, list[str]]:
    """Build mapping of item_id to conflicting item_ids.

    Args:
        items: List of ApprovalItem objects
        conflicts: List of detected conflicts

    Returns:
        Dict mapping item_id to list of conflicting item_ids
    """
    # Build hour -> item_ids mapping
    hour_items: dict[str, list[str]] = {}
    for item in items:
        if not item.scheduled_publish_time:
            continue
        hour_key = item.scheduled_publish_time.strftime("%Y-%m-%dT%H:00:00")
        if hour_key not in hour_items:
            hour_items[hour_key] = []
        hour_items[hour_key].append(str(item.id))

    # Build item_id -> conflicts mapping
    item_conflicts: dict[str, list[str]] = {}
    for conflict in conflicts:
        hour_key = conflict.hour.strftime("%Y-%m-%dT%H:00:00")
        if hour_key in hour_items:
            for item_id in hour_items[hour_key]:
                # Exclude self from conflicts list
                others = [id for id in hour_items[hour_key] if id != item_id]
                item_conflicts[item_id] = others

    return item_conflicts


@router.get("/calendar", response_model=ScheduleCalendarResponse)
async def get_schedule_calendar(
    start_date: date = Query(..., description="Start of date range"),
    end_date: date = Query(..., description="End of date range"),
    status: Optional[list[str]] = Query(
        None,
        description="Filter by status: APPROVED, SCHEDULED, PUBLISHED"
    ),
    db: AsyncSession = Depends(get_db),
) -> ScheduleCalendarResponse:
    """Get scheduled items for calendar view.

    Story 4-4, Task 2.1: GET /api/schedule/calendar endpoint.

    Returns items scheduled within the date range, with conflict
    detection and imminent status indicators.
    """
    repo = ApprovalItemRepository(db)

    # Convert dates to datetime for query
    start_datetime = datetime.combine(start_date, time.min)
    end_datetime = datetime.combine(end_date, time.max)

    # Get items
    items = await repo.get_scheduled_items(
        start_date=start_datetime,
        end_date=end_datetime,
        statuses=status,
    )

    # Detect conflicts
    conflicts = detect_conflicts(items)
    item_conflicts = add_conflict_ids_to_items(items, conflicts)

    # Convert to response format
    response_items = []
    for item in items:
        item_id = str(item.id)
        response_items.append(
            ScheduledItemResponse(
                id=item_id,
                title=truncate_caption(item.full_caption),
                thumbnail_url=item.thumbnail_url,
                scheduled_publish_time=item.scheduled_publish_time,
                source_type=item.source_type,
                source_priority=item.source_priority,
                quality_score=item.quality_score,
                quality_color=get_quality_color(item.quality_score),
                compliance_status=item.compliance_status,
                conflicts=item_conflicts.get(item_id, []),
                is_imminent=is_imminent(item.scheduled_publish_time),
            )
        )

    return ScheduleCalendarResponse(
        items=response_items,
        conflicts=conflicts,
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    )


@router.get("/optimal-times", response_model=OptimalTimesResponse)
async def get_optimal_times(
    target_date: date = Query(..., description="Date to get suggestions for"),
    item_id: Optional[str] = Query(None, description="Item being scheduled"),
    db: AsyncSession = Depends(get_db),
) -> OptimalTimesResponse:
    """Get optimal time suggestions for a date.

    Story 4-4, Task 2.3: GET /api/schedule/optimal-times endpoint.

    Returns top 3 suggested time slots based on:
    - Instagram peak engagement hours
    - Conflict avoidance (existing scheduled posts)
    - Historical engagement data (placeholder for Epic 7)
    """
    repo = ApprovalItemRepository(db)

    # Get existing items for the target date
    start_datetime = datetime.combine(target_date, time.min)
    end_datetime = datetime.combine(target_date, time.max)
    existing_items = await repo.get_scheduled_items(start_datetime, end_datetime)

    # Build hour usage map
    hour_counts: dict[int, int] = {}
    for item in existing_items:
        if item.scheduled_publish_time:
            hour = item.scheduled_publish_time.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

    # Instagram peak hours (local time) - weekday pattern
    day_of_week = target_date.weekday()
    if day_of_week < 5:  # Weekday
        peak_hours = [9, 10, 11, 19, 20, 21]
    else:  # Weekend
        peak_hours = [10, 11, 12, 17, 18, 19]

    # Score each hour (6am to 11pm)
    hour_scores: list[tuple[int, float, str]] = []
    for hour in range(6, 23):
        # Base peak time score
        if hour in peak_hours:
            peak_score = 1.0
            peak_reason = "Peak engagement time"
        elif any(abs(hour - ph) == 1 for ph in peak_hours):
            peak_score = 0.7
            peak_reason = "Near peak engagement"
        else:
            peak_score = 0.3
            peak_reason = "Off-peak hours"

        # Conflict avoidance score
        conflict_count = hour_counts.get(hour, 0)
        if conflict_count == 0:
            conflict_score = 1.0
            conflict_reason = "no conflicts"
        elif conflict_count == 1:
            conflict_score = 0.5
            conflict_reason = "1 other post scheduled"
        else:
            conflict_score = max(0, 1 - conflict_count * 0.5)
            conflict_reason = f"{conflict_count} posts same hour (crowded)"

        # Weighted total (engagement 40%, peak 35%, conflict 25%)
        # Since engagement isn't available yet, use peak as proxy
        total_score = (peak_score * 0.75) + (conflict_score * 0.25)

        # Build reasoning
        reasoning = f"{peak_reason}, {conflict_reason}"

        hour_scores.append((hour, total_score, reasoning))

    # Sort by score descending, take top 3
    hour_scores.sort(key=lambda x: x[1], reverse=True)
    top_3 = hour_scores[:3]

    suggestions = [
        OptimalTimeSlot(
            time=datetime.combine(target_date, time(hour=h, minute=0)),
            score=round(score, 2),
            reasoning=reasoning,
        )
        for h, score, reasoning in top_3
    ]

    return OptimalTimesResponse(
        item_id=item_id,
        target_date=target_date,
        suggestions=suggestions,
    )


@router.patch("/{item_id}/reschedule", response_model=RescheduleResponse)
async def reschedule_item(
    item_id: str,
    request: RescheduleSchema,
    db: AsyncSession = Depends(get_db),
) -> RescheduleResponse:
    """Reschedule a post to a new time.

    Story 4-4, Task 4.3: PATCH /api/schedule/{item_id}/reschedule endpoint.

    Validates:
    - Item exists and is in APPROVED or SCHEDULED status
    - Not within 30 minutes of current publish time (unless force=true)

    Returns conflicts at the new time slot.
    """
    repo = ApprovalItemRepository(db)

    try:
        item = await repo.reschedule_item(
            item_id=item_id,
            new_publish_time=request.new_publish_time,
            force=request.force,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check for conflicts at new time
    same_hour_items = await repo.get_items_at_hour(request.new_publish_time)
    conflicts = []
    if len(same_hour_items) >= CONFLICT_WARNING_THRESHOLD:
        conflicts.append(
            ConflictInfo(
                hour=request.new_publish_time.replace(minute=0, second=0, microsecond=0),
                posts_count=len(same_hour_items),
                post_ids=[str(i.id) for i in same_hour_items],
                severity=(
                    ConflictSeverity.CRITICAL
                    if len(same_hour_items) >= CONFLICT_CRITICAL_THRESHOLD
                    else ConflictSeverity.WARNING
                ),
            )
        )

    # Commit the transaction
    await db.commit()

    return RescheduleResponse(
        success=True,
        message=f"Rescheduled to {request.new_publish_time.isoformat()}",
        item_id=item_id,
        new_publish_time=item.scheduled_publish_time,
        conflicts=conflicts,
    )


@router.post("/{item_id}/retry-publish", response_model=RetryPublishResponse)
async def retry_publish(
    item_id: str,
    request: Optional[RetryPublishRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> RetryPublishResponse:
    """Retry publishing a failed post.

    Story 4-5, Task 6.1: POST /api/schedule/{item_id}/retry-publish endpoint.

    Validates:
    - Item exists and is in PUBLISH_FAILED status
    - Resets status to SCHEDULED and clears publish_error
    - Re-enqueues ARQ job for immediate publish

    Returns:
        RetryPublishResponse with job_id for tracking
    """
    from uuid import UUID
    from core.approval.models import ApprovalItem, ApprovalStatus
    from core.scheduling.jobs import enqueue_publish_job
    from sqlalchemy import select

    # Parse force flag from request
    force = request.force if request else False

    # Story 4-5, Task 6.2: Validate item is in PUBLISH_FAILED status
    query = select(ApprovalItem).where(ApprovalItem.id == UUID(item_id))
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")

    if item.status != ApprovalStatus.PUBLISH_FAILED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Item must be in PUBLISH_FAILED status to retry. Current: {item.status}",
        )

    # Check if recently attempted (within 1 minute) unless force=True
    if not force and item.publish_attempts and item.publish_attempts >= 3:
        if item.updated_at and (datetime.utcnow() - item.updated_at).total_seconds() < 60:
            raise HTTPException(
                status_code=429,
                detail="Too many recent attempts. Wait 1 minute or use force=true.",
            )

    # Story 4-5, Task 6.3: Reset status to SCHEDULED and clear publish_error
    item.status = ApprovalStatus.SCHEDULED.value
    item.publish_error = None
    item.updated_at = datetime.utcnow()

    # Set publish time to now for immediate retry
    publish_time = datetime.utcnow() + timedelta(seconds=5)
    item.scheduled_publish_time = publish_time

    await db.commit()

    # Story 4-5, Task 6.4: Re-enqueue ARQ job for immediate publish
    job_id = None
    try:
        # Get Redis pool from app state or create connection
        import os
        from arq import create_pool
        from arq.connections import RedisSettings

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        redis_settings = RedisSettings.from_dsn(redis_url)
        redis_pool = await create_pool(redis_settings)

        job_id = await enqueue_publish_job(
            redis_pool=redis_pool,
            item_id=item_id,
            publish_time=publish_time,
        )

        await redis_pool.close()

        logger.info(
            "Retry publish enqueued for item %s, job_id: %s",
            item_id,
            job_id,
        )
    except Exception as e:
        logger.warning("Failed to enqueue retry job: %s", e)
        # Continue - the status is updated, manual trigger may be needed

    # Story 4-5, Task 6.5: Return success response with new job_id
    return RetryPublishResponse(
        success=True,
        message="Retry initiated" if job_id else "Status reset, manual trigger may be needed",
        item_id=item_id,
        job_id=job_id,
        scheduled_for=publish_time,
    )


__all__ = [
    "router",
]
