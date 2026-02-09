"""Pydantic schemas for UI Backend API.

Provides data validation and serialization schemas for all API endpoints.

Exports:
    - Approval schemas: ApprovalQueueItemSchema, ApprovalQueueResponse, etc.
    - Approval action schemas: ApproveActionSchema, RejectActionSchema, etc.
"""

from .approval import (
    SourcePriority,
    ComplianceStatus,
    QualityColor,
    get_quality_color,
    ComplianceCheckSchema,
    QualityBreakdownSchema,
    ApprovalQueueItemSchema,
    ApprovalQueueResponse,
)

from .approval_actions import (
    RejectReason,
    ApproveActionSchema,
    RejectActionSchema,
    EditActionSchema,
    RewriteSuggestionSchema,
    RevalidationResultSchema,
    ApprovalActionResponse,
    EditHistorySchema,
    ApplyRewriteSchema,
)

# Story 4-3: Batch approval schemas
from .batch_approval import (
    BatchApproveSchema,
    BatchRejectSchema,
    BatchActionResultItem,
    BatchApproveResponse,
    BatchRejectResponse,
)

# Story 4-4: Schedule schemas
from .schedule import (
    ConflictSeverity,
    ConflictInfo,
    ScheduledItemResponse,
    OptimalTimeSlot,
    OptimalTimesResponse,
    RescheduleSchema,
    RescheduleResponse,
    ScheduleCalendarResponse,
    ScheduleCalendarQuery,
)

__all__ = [
    # Approval queue schemas
    "SourcePriority",
    "ComplianceStatus",
    "QualityColor",
    "get_quality_color",
    "ComplianceCheckSchema",
    "QualityBreakdownSchema",
    "ApprovalQueueItemSchema",
    "ApprovalQueueResponse",
    # Approval action schemas
    "RejectReason",
    "ApproveActionSchema",
    "RejectActionSchema",
    "EditActionSchema",
    "RewriteSuggestionSchema",
    "RevalidationResultSchema",
    "ApprovalActionResponse",
    "EditHistorySchema",
    "ApplyRewriteSchema",
    # Story 4-3: Batch approval schemas
    "BatchApproveSchema",
    "BatchRejectSchema",
    "BatchActionResultItem",
    "BatchApproveResponse",
    "BatchRejectResponse",
    # Story 4-4: Schedule schemas
    "ConflictSeverity",
    "ConflictInfo",
    "ScheduledItemResponse",
    "OptimalTimeSlot",
    "OptimalTimesResponse",
    "RescheduleSchema",
    "RescheduleResponse",
    "ScheduleCalendarResponse",
    "ScheduleCalendarQuery",
]
