"""Pydantic schemas for Batch Approval operations.

Story 4-3: Batch Approval Capability
Task 3 & 4: Batch approve/reject endpoints.

Provides data validation for batch approve, reject operations.

Schemas:
    - BatchApproveSchema: Request schema for batch approve
    - BatchRejectSchema: Request schema for batch reject
    - BatchActionResultItem: Result for individual item in batch
    - BatchApproveResponse: Response for batch approve
    - BatchRejectResponse: Response for batch reject
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ui.backend.schemas.approval_actions import RejectReason


class BatchApproveSchema(BaseModel):
    """Schema for batch approve action request.

    Approves multiple items at once. Each item uses its suggested_publish_time
    for scheduling.
    """

    item_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of item IDs to approve (max 100)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "item_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "550e8400-e29b-41d4-a716-446655440001",
                ],
            }
        }
    }


class BatchRejectSchema(BaseModel):
    """Schema for batch reject action request.

    Rejects multiple items with the same reason.
    reason_text is required when reason is OTHER.
    """

    item_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of item IDs to reject (max 100)",
    )
    reason: RejectReason = Field(
        ...,
        description="Rejection reason (same for all items)",
    )
    reason_text: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Additional rejection details (required if reason is OTHER)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "item_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "550e8400-e29b-41d4-a716-446655440001",
                ],
                "reason": "compliance_issue",
                "reason_text": "Contains implicit health benefit claim",
            }
        }
    }


class BatchActionResultItem(BaseModel):
    """Result for an individual item in a batch operation.

    Tracks success/failure and details for each item.
    """

    item_id: str = Field(
        ...,
        description="ID of the processed item",
    )
    success: bool = Field(
        ...,
        description="Whether the action succeeded for this item",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if action failed",
    )
    scheduled_publish_time: Optional[datetime] = Field(
        default=None,
        description="Scheduled publish time (for approved items)",
    )

    model_config = {
        "from_attributes": True,
    }


class BatchApproveResponse(BaseModel):
    """Response for batch approve action.

    Provides summary and per-item results.
    """

    batch_id: str = Field(
        ...,
        description="Unique identifier for this batch operation",
    )
    total_requested: int = Field(
        ...,
        description="Total number of items requested for approval",
    )
    successful_count: int = Field(
        ...,
        description="Number of items successfully approved",
    )
    failed_count: int = Field(
        ...,
        description="Number of items that failed to approve",
    )
    results: list[BatchActionResultItem] = Field(
        ...,
        description="Per-item results",
    )
    summary: str = Field(
        ...,
        description="Human-readable summary (e.g., '5 items approved, scheduled for Feb 8-10')",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "batch_id": "batch-550e8400-e29b-41d4-a716",
                "total_requested": 5,
                "successful_count": 5,
                "failed_count": 0,
                "results": [
                    {
                        "item_id": "550e8400-e29b-41d4-a716-446655440000",
                        "success": True,
                        "scheduled_publish_time": "2026-02-10T14:00:00Z",
                    }
                ],
                "summary": "5 items approved, scheduled for Feb 10-12",
            }
        }
    }


class BatchRejectResponse(BaseModel):
    """Response for batch reject action.

    Provides summary and per-item results.
    """

    batch_id: str = Field(
        ...,
        description="Unique identifier for this batch operation",
    )
    total_requested: int = Field(
        ...,
        description="Total number of items requested for rejection",
    )
    successful_count: int = Field(
        ...,
        description="Number of items successfully rejected",
    )
    failed_count: int = Field(
        ...,
        description="Number of items that failed to reject",
    )
    results: list[BatchActionResultItem] = Field(
        ...,
        description="Per-item results",
    )
    summary: str = Field(
        ...,
        description="Human-readable summary (e.g., '5 items rejected: Compliance issue')",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "batch_id": "batch-550e8400-e29b-41d4-a716",
                "total_requested": 3,
                "successful_count": 3,
                "failed_count": 0,
                "results": [
                    {
                        "item_id": "550e8400-e29b-41d4-a716-446655440000",
                        "success": True,
                    }
                ],
                "summary": "3 items rejected: Compliance Issue",
            }
        }
    }


__all__ = [
    "BatchApproveSchema",
    "BatchRejectSchema",
    "BatchActionResultItem",
    "BatchApproveResponse",
    "BatchRejectResponse",
]
