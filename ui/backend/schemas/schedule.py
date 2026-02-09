"""Scheduling API schemas.

Story 4-4, Task 2: Pydantic schemas for calendar scheduling endpoints.

Schemas:
    - ScheduledItemResponse: Calendar item for scheduling view
    - OptimalTimeSlot: Suggested optimal publish time
    - OptimalTimesResponse: Response for optimal time suggestions
    - RescheduleSchema: Request to reschedule a post
    - ConflictInfo: Conflict information for a time slot
    - ScheduleCalendarResponse: Full calendar response with items and conflicts
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ConflictSeverity(str, Enum):
    """Conflict severity levels.

    Values:
        WARNING: 2 posts same hour (could impact engagement)
        CRITICAL: 3+ posts same hour (strongly discouraged)
    """

    WARNING = "warning"
    CRITICAL = "critical"


class ConflictInfo(BaseModel):
    """Conflict information for a time slot.

    Story 4-4, Task 2.6: Include conflict indicators in response.

    Attributes:
        hour: ISO datetime for the hour with conflict
        posts_count: Number of posts scheduled in this hour
        post_ids: IDs of conflicting posts
        severity: Warning or critical based on count
    """

    hour: datetime
    posts_count: int = Field(..., ge=2, description="Number of posts (min 2 for conflict)")
    post_ids: list[str] = Field(..., description="IDs of posts in this hour")
    severity: ConflictSeverity


class ScheduledItemResponse(BaseModel):
    """Calendar item for scheduling view.

    Story 4-4, Task 2.2: Calendar-specific response with minimal data
    optimized for calendar rendering.

    Attributes:
        id: Unique identifier
        title: Truncated caption for calendar display
        thumbnail_url: Preview image URL
        scheduled_publish_time: Confirmed publish time
        source_type: Content source (instagram_post, b2b_email, etc.)
        source_priority: Priority level (1-4)
        quality_score: Quality score (0-10)
        quality_color: Color for badge (green/yellow/red)
        compliance_status: Compliance check result
        conflicts: IDs of items scheduled same hour
        is_imminent: True if < 1 hour to publish
        status: Current status (Story 4-5)
        instagram_permalink: Link to published post (Story 4-5)
        published_at: When post was published (Story 4-5)
        publish_error: Error message if failed (Story 4-5)
    """

    id: str
    title: str = Field(..., max_length=100, description="Truncated caption")
    thumbnail_url: str
    scheduled_publish_time: datetime
    source_type: str
    source_priority: int = Field(..., ge=1, le=4)
    quality_score: float = Field(..., ge=0, le=10)
    quality_color: str = Field(..., pattern="^(green|yellow|red)$")
    compliance_status: str
    conflicts: list[str] = Field(default_factory=list)
    is_imminent: bool = False
    # Story 4-5: Publishing status fields
    status: str = Field(default="scheduled", description="Current status")
    instagram_permalink: Optional[str] = Field(default=None, description="Link to Instagram post")
    published_at: Optional[datetime] = Field(default=None, description="When published")
    publish_error: Optional[str] = Field(default=None, description="Error if failed")

    class Config:
        from_attributes = True


class OptimalTimeSlot(BaseModel):
    """Suggested optimal publish time.

    Story 4-4, Task 2.4: Time slot with score and reasoning.

    Attributes:
        time: Suggested publish time
        score: 0-1 score (higher is better)
        reasoning: Human-readable explanation
    """

    time: datetime
    score: float = Field(..., ge=0, le=1, description="Optimal score (0-1)")
    reasoning: str = Field(..., description="Explanation for this suggestion")


class OptimalTimesResponse(BaseModel):
    """Response for optimal time suggestions API.

    Story 4-4, Task 2.3: GET /api/schedule/optimal-times response.

    Attributes:
        item_id: Optional item being scheduled
        target_date: Date for which times are suggested
        suggestions: List of optimal time slots (top 3)
    """

    item_id: Optional[str] = None
    target_date: date
    suggestions: list[OptimalTimeSlot] = Field(..., max_length=5)


class RescheduleSchema(BaseModel):
    """Request to reschedule a post.

    Story 4-4, Task 4.4: PATCH /api/schedule/{item_id}/reschedule body.

    Attributes:
        new_publish_time: New scheduled publish time
        force: Override imminent lock (< 30 min protection)
    """

    new_publish_time: datetime
    force: bool = Field(
        default=False,
        description="Override imminent lock (use with caution)"
    )


class RescheduleResponse(BaseModel):
    """Response from reschedule operation.

    Attributes:
        success: Whether reschedule succeeded
        message: Status message
        item_id: ID of rescheduled item
        new_publish_time: Confirmed new time
        conflicts: Any conflicts at new time
    """

    success: bool
    message: str
    item_id: str
    new_publish_time: datetime
    conflicts: list[ConflictInfo] = Field(default_factory=list)


class ScheduleCalendarResponse(BaseModel):
    """Full calendar response with items and conflicts.

    Story 4-4, Task 2.1: GET /api/schedule/calendar response.

    Attributes:
        items: Scheduled items for the date range
        conflicts: Conflicts detected in the date range
        date_range: Start and end dates of the response
    """

    items: list[ScheduledItemResponse]
    conflicts: list[ConflictInfo] = Field(default_factory=list)
    date_range: dict = Field(
        ...,
        description="Date range with 'start' and 'end' ISO strings"
    )


class ScheduleCalendarQuery(BaseModel):
    """Query parameters for calendar endpoint.

    Story 4-4, Task 2.5: Date range query parameters.

    Attributes:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        status: Filter by status (optional)
    """

    start_date: date
    end_date: date
    status: Optional[list[str]] = Field(
        default=None,
        description="Filter by status: APPROVED, SCHEDULED, PUBLISHED"
    )


class RetryPublishRequest(BaseModel):
    """Request to retry a failed publish.

    Story 4-5, Task 6.1: POST /api/schedule/{item_id}/retry-publish body.

    Attributes:
        force: Override any safety checks (use with caution)
    """

    force: bool = Field(
        default=False,
        description="Force retry even if recently attempted"
    )


class RetryPublishResponse(BaseModel):
    """Response from retry publish operation.

    Story 4-5, Task 6.5: Response with new job information.

    Attributes:
        success: Whether retry was initiated
        message: Status message
        item_id: ID of item being retried
        job_id: ARQ job ID for tracking
        scheduled_for: When publish will be attempted
    """

    success: bool
    message: str
    item_id: str
    job_id: Optional[str] = None
    scheduled_for: Optional[datetime] = None


__all__ = [
    "ConflictSeverity",
    "ConflictInfo",
    "ScheduledItemResponse",
    "OptimalTimeSlot",
    "OptimalTimesResponse",
    "RescheduleSchema",
    "RescheduleResponse",
    "ScheduleCalendarResponse",
    "ScheduleCalendarQuery",
    "RetryPublishRequest",
    "RetryPublishResponse",
]
