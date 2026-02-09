"""Pydantic schemas for Approval Queue action endpoints.

Provides data validation for approve, reject, and edit operations.

Schemas:
    - RejectReason: Enum for predefined rejection reasons
    - ApproveActionSchema: Schema for approve action
    - RejectActionSchema: Schema for reject action with reason
    - EditActionSchema: Schema for caption edit action
    - RevalidationResultSchema: Result of compliance/quality revalidation
    - ApprovalActionResponse: Standard response for all actions
    - EditHistorySchema: Schema for edit history entries
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ui.backend.schemas.approval import (
    ComplianceCheckSchema,
    QualityBreakdownSchema,
)


class RejectReason(str, Enum):
    """Predefined rejection reasons for analytics and ML feedback.

    Values provide consistent categorization for:
    - Operator workflow efficiency
    - ML feedback pipeline training
    - Analytics and reporting
    """

    COMPLIANCE_ISSUE = "compliance_issue"
    BRAND_VOICE_MISMATCH = "brand_voice_mismatch"
    LOW_QUALITY = "low_quality"
    IRRELEVANT_CONTENT = "irrelevant_content"
    DUPLICATE_CONTENT = "duplicate_content"
    OTHER = "other"


class ApproveActionSchema(BaseModel):
    """Schema for approve action request.

    Allows optional override of suggested publish time.
    If not provided, uses the item's suggested_publish_time.
    """

    scheduled_publish_time: Optional[datetime] = Field(
        default=None,
        description="Override suggested publish time (optional)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "scheduled_publish_time": "2026-02-10T14:00:00Z",
            }
        }
    }


class RejectActionSchema(BaseModel):
    """Schema for reject action request.

    Requires a reason from predefined enum.
    reason_text is required when reason is OTHER.
    """

    reason: RejectReason = Field(
        ...,
        description="Rejection reason from predefined options",
    )
    reason_text: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Additional rejection details (required if reason is OTHER)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "reason": "compliance_issue",
                "reason_text": "Contains implicit health benefit claim in paragraph 2",
            }
        }
    }


class EditActionSchema(BaseModel):
    """Schema for edit action request.

    Validates caption length and optional hashtag updates.
    """

    caption: str = Field(
        ...,
        min_length=1,
        max_length=2200,
        description="Updated caption text",
    )
    hashtags: Optional[list[str]] = Field(
        default=None,
        max_length=30,
        description="Updated hashtag list (max 30 per Instagram limit)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "caption": "Updated caption with compliant language...",
                "hashtags": ["DAWO", "DAWOmushrooms", "wellness"],
            }
        }
    }


class RewriteSuggestionSchema(BaseModel):
    """Schema for AI rewrite suggestion.

    Provides original text, suggested replacement, and reason.
    """

    id: str = Field(
        ...,
        description="Unique identifier for the suggestion",
    )
    original_text: str = Field(
        ...,
        description="Original text that needs improvement",
    )
    suggested_text: str = Field(
        ...,
        description="AI-suggested replacement text",
    )
    reason: str = Field(
        ...,
        description="Explanation of why change is suggested",
    )
    type: str = Field(
        ...,
        description="Suggestion type: compliance, brand_voice, or quality",
    )

    model_config = {
        "from_attributes": True,
    }


class RevalidationResultSchema(BaseModel):
    """Result of compliance and quality revalidation.

    Returned after editing content to show updated scores.
    """

    compliance_status: str = Field(
        ...,
        description="Updated compliance status",
    )
    compliance_details: Optional[list[ComplianceCheckSchema]] = Field(
        default=None,
        description="Detailed compliance check results",
    )
    quality_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Updated quality score (0-10)",
    )
    quality_breakdown: Optional[QualityBreakdownSchema] = Field(
        default=None,
        description="Quality score breakdown by factor",
    )
    rewrite_suggestions: Optional[list[RewriteSuggestionSchema]] = Field(
        default=None,
        description="AI-generated rewrite suggestions",
    )

    model_config = {
        "from_attributes": True,
    }


class ApprovalActionResponse(BaseModel):
    """Standard response for approval actions.

    Provides consistent response format for approve, reject, and edit.
    """

    success: bool = Field(
        ...,
        description="Whether the action completed successfully",
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
    )
    item_id: str = Field(
        ...,
        description="ID of the affected approval item",
    )
    new_status: str = Field(
        ...,
        description="New status after action (pending, approved, rejected)",
    )
    revalidation: Optional[RevalidationResultSchema] = Field(
        default=None,
        description="Revalidation results (for edit actions)",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Content approved successfully",
                "item_id": "550e8400-e29b-41d4-a716-446655440000",
                "new_status": "approved",
            }
        }
    }


class EditHistorySchema(BaseModel):
    """Schema for edit history entry.

    Records each caption edit for audit trail.
    """

    id: str = Field(
        ...,
        description="Unique identifier for the edit record",
    )
    previous_caption: str = Field(
        ...,
        description="Caption before this edit",
    )
    new_caption: str = Field(
        ...,
        description="Caption after this edit",
    )
    edited_at: datetime = Field(
        ...,
        description="Timestamp of the edit",
    )
    editor: str = Field(
        ...,
        description="Who made the edit (operator or system)",
    )

    model_config = {
        "from_attributes": True,
    }


class ApplyRewriteSchema(BaseModel):
    """Schema for applying AI rewrite suggestions."""

    suggestion_ids: list[str] = Field(
        ...,
        min_length=1,
        description="IDs of suggestions to apply",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "suggestion_ids": ["sug-001", "sug-002"],
            }
        }
    }


__all__ = [
    "RejectReason",
    "ApproveActionSchema",
    "RejectActionSchema",
    "EditActionSchema",
    "RewriteSuggestionSchema",
    "RevalidationResultSchema",
    "ApprovalActionResponse",
    "EditHistorySchema",
    "ApplyRewriteSchema",
]
