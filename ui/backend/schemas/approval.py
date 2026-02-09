"""Pydantic schemas for Approval Queue API.

Provides data validation schemas for the approval queue endpoints.
Uses Pydantic v2 for validation and serialization.

Schemas:
    - ApprovalQueueItemSchema: Individual approval queue item
    - ComplianceCheckSchema: Individual compliance check result
    - QualityBreakdownSchema: Quality score breakdown by factor
    - ApprovalQueueResponse: Paginated response for approval queue
"""

from datetime import datetime
from enum import IntEnum, Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourcePriority(IntEnum):
    """Source-based priority for approval queue ordering.

    Lower values indicate higher priority (more urgent).

    Values:
        TRENDING: Time-sensitive trending content (highest priority)
        SCHEDULED: Content approaching deadline
        EVERGREEN: Flexible timing content
        RESEARCH: Research-based content (lowest urgency)
    """

    TRENDING = 1
    SCHEDULED = 2
    EVERGREEN = 3
    RESEARCH = 4


class ComplianceStatus(str, Enum):
    """Content compliance status.

    Indicates the result of EU Health Claims Regulation (EC 1924/2006)
    validation performed on content.

    Values:
        COMPLIANT: Content passes compliance checks
        WARNING: Borderline content, needs review
        REJECTED: Content contains prohibited claims
    """

    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    REJECTED = "REJECTED"


class QualityColor(str, Enum):
    """Quality score color coding.

    Used for visual indication of content quality.

    Values:
        GREEN: High quality (score >= 8)
        YELLOW: Medium quality (score >= 5 and < 8)
        RED: Low quality (score < 5)
    """

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


def get_quality_color(score: float) -> QualityColor:
    """Calculate quality color from score.

    Args:
        score: Quality score (0-10)

    Returns:
        QualityColor based on score threshold
    """
    if score >= 8:
        return QualityColor.GREEN
    if score >= 5:
        return QualityColor.YELLOW
    return QualityColor.RED


class ComplianceCheckSchema(BaseModel):
    """Individual compliance check result.

    Represents a single compliance check performed on content,
    including the phrase checked, result status, and explanation.
    """

    phrase: str = Field(
        ...,
        description="The phrase that was checked for compliance",
    )
    status: str = Field(
        ...,
        description="Check result: 'prohibited', 'borderline', or 'permitted'",
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of the check result",
    )
    regulation_reference: Optional[str] = Field(
        default=None,
        description="EU regulation reference if applicable",
    )

    model_config = {
        "from_attributes": True,
    }


class QualityBreakdownSchema(BaseModel):
    """Quality score breakdown by factor.

    Each factor contributes to the overall quality score with
    specified weights.
    """

    compliance_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Compliance factor score (25% weight)",
    )
    brand_voice_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Brand voice alignment score (20% weight)",
    )
    visual_quality_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Visual quality score (15% weight)",
    )
    platform_optimization_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Platform optimization score (15% weight)",
    )
    engagement_prediction_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Engagement prediction score (15% weight)",
    )
    authenticity_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Authenticity score (10% weight)",
    )

    model_config = {
        "from_attributes": True,
    }


class ApprovalQueueItemSchema(BaseModel):
    """Schema for approval queue item.

    Contains all fields needed for queue display and detail view.
    """

    id: str = Field(
        ...,
        description="Unique identifier for the approval item",
    )
    thumbnail_url: str = Field(
        ...,
        description="URL to thumbnail image (200x200)",
    )
    caption_excerpt: str = Field(
        ...,
        max_length=100,
        description="First 100 characters of caption",
    )
    full_caption: str = Field(
        ...,
        description="Complete caption text",
    )
    quality_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Overall quality score (0-10)",
    )
    quality_color: QualityColor = Field(
        ...,
        description="Color coding based on quality score",
    )
    compliance_status: ComplianceStatus = Field(
        ...,
        description="Content compliance status",
    )
    would_auto_publish: bool = Field(
        ...,
        description="Whether content meets auto-publish criteria",
    )
    suggested_publish_time: Optional[datetime] = Field(
        default=None,
        description="Suggested time for publishing",
    )
    source_type: str = Field(
        ...,
        description="Content source type (instagram_post, b2b_email, etc.)",
    )
    source_priority: SourcePriority = Field(
        ...,
        description="Source-based priority for ordering",
    )
    hashtags: list[str] = Field(
        default_factory=list,
        description="List of hashtags for the content",
    )
    compliance_details: Optional[list[ComplianceCheckSchema]] = Field(
        default=None,
        description="Detailed compliance check results",
    )
    quality_breakdown: Optional[QualityBreakdownSchema] = Field(
        default=None,
        description="Quality score breakdown by factor",
    )
    created_at: datetime = Field(
        ...,
        description="When the content was created",
    )
    # Story 4-2: Edit support fields
    original_caption: Optional[str] = Field(
        default=None,
        description="Original caption before any edits (for revert)",
    )
    rewrite_suggestions: Optional[list[dict]] = Field(
        default=None,
        description="AI-suggested rewrites for compliance/quality improvement",
    )
    status: Optional[str] = Field(
        default=None,
        description="Current approval status (pending, approved, rejected, scheduled, publishing, published, publish_failed)",
    )
    # Story 4-5: Instagram publishing fields
    instagram_post_id: Optional[str] = Field(
        default=None,
        description="Instagram post ID after successful publish",
    )
    instagram_permalink: Optional[str] = Field(
        default=None,
        description="Direct link to Instagram post",
    )
    published_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when post was published to Instagram",
    )
    publish_error: Optional[str] = Field(
        default=None,
        description="Error message if publish failed",
    )
    publish_attempts: int = Field(
        default=0,
        ge=0,
        description="Number of publish attempts made",
    )

    model_config = {
        "from_attributes": True,
    }


class ApprovalQueueResponse(BaseModel):
    """Response schema for approval queue endpoint.

    Includes paginated items list with cursor-based pagination.
    """

    items: list[ApprovalQueueItemSchema] = Field(
        ...,
        description="List of approval queue items",
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of items in queue",
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor for next page of results",
    )
    has_more: bool = Field(
        ...,
        description="Whether more items exist beyond this page",
    )

    model_config = {
        "from_attributes": True,
    }


__all__ = [
    "SourcePriority",
    "ComplianceStatus",
    "QualityColor",
    "get_quality_color",
    "ComplianceCheckSchema",
    "QualityBreakdownSchema",
    "ApprovalQueueItemSchema",
    "ApprovalQueueResponse",
]
