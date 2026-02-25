"""Pydantic schemas for Calendar Sync API.

Story 7-9, Task 7.1: Request/response schemas for Google Calendar sync.

Schemas:
    - CalendarSyncStatusResponse: Sync status for a single item
    - CalendarConfigResponse: Calendar configuration status
    - ManualSyncRequest: Trigger manual sync for items
    - ManualSyncResponse: Manual sync result
    - CalendarSetupResponse: Calendar setup result
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CalendarSyncStatusResponse(BaseModel):
    """Sync status for a single approval item."""

    item_id: str = Field(..., description="Approval item ID")
    google_calendar_event_id: Optional[str] = Field(
        default=None, description="Google Calendar event ID"
    )
    sync_status: str = Field(
        ..., description="synced / pending / failed / disabled"
    )
    last_synced_at: Optional[datetime] = Field(
        default=None, description="When last synced"
    )

    model_config = {"from_attributes": True}


class CalendarConfigResponse(BaseModel):
    """Calendar integration configuration status."""

    sync_enabled: bool = Field(..., description="Whether sync is active")
    calendar_name: str = Field(..., description="Target calendar name")
    calendar_id: Optional[str] = Field(
        default=None, description="Google Calendar ID"
    )


class ManualSyncRequest(BaseModel):
    """Request to manually sync items to calendar."""

    item_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Item IDs to sync (max 20)",
    )


class ManualSyncResponse(BaseModel):
    """Result of manual sync request."""

    queued: int = Field(..., ge=0, description="Items queued for sync")
    message: str = Field(default="", description="Human-readable status")


class CalendarSetupResponse(BaseModel):
    """Result of calendar setup/verification."""

    calendar_id: str = Field(..., description="Created/verified calendar ID")
    calendar_name: str = Field(..., description="Calendar name")
    message: str = Field(default="", description="Human-readable status")


__all__ = [
    "CalendarConfigResponse",
    "CalendarSetupResponse",
    "CalendarSyncStatusResponse",
    "ManualSyncRequest",
    "ManualSyncResponse",
]
