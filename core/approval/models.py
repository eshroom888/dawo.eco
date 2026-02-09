"""Approval database models.

Defines SQLAlchemy ORM models for content approval workflow.
Uses PostgreSQL-specific features: UUID, JSONB, ARRAY.

Models:
    - ApprovalItem: Content item pending approval with quality scores,
      compliance status, and source priority for queue ordering.
    - ApprovalItemEdit: Audit trail for caption edits.

Enums:
    - ApprovalStatus: Workflow states (PENDING, APPROVED, REJECTED, etc.)
    - SourcePriority: Source-based priority ordering (1-4)
    - RejectReasonType: Predefined rejection reasons

Database Schema (PostgreSQL):
    - approval_items table with performance indexes
    - approval_item_edits table for edit history
    - Index on source_priority for efficient queue sorting
    - Index on status for filtering pending items
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text, Index, Boolean, Float, func, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base

if TYPE_CHECKING:
    from typing import List


class ApprovalStatus(str, Enum):
    """Approval workflow status.

    Values:
        PENDING: Awaiting human review
        APPROVED: Content approved for publishing
        REJECTED: Content rejected, needs revision
        SCHEDULED: Content scheduled for publishing
        PUBLISHING: Currently publishing to Instagram (Story 4-5)
        PUBLISHED: Content successfully published
        PUBLISH_FAILED: Publishing failed
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"  # Story 4-5: Intermediate status during publish
    PUBLISHED = "published"
    PUBLISH_FAILED = "publish_failed"


class RejectReasonType(str, Enum):
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


class SourcePriority(IntEnum):
    """Source-based priority for approval queue ordering.

    Lower values indicate higher priority (more urgent).
    Used for sorting the approval queue by content type urgency.

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
    """Content compliance check result.

    Values:
        COMPLIANT: Content passes all compliance checks
        WARNING: Borderline content, needs review
        REJECTED: Content contains prohibited claims
    """

    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    REJECTED = "REJECTED"


# Model constants
MAX_SOURCE_TYPE_LENGTH = 50
MAX_CAPTION_LENGTH = 10000
MAX_URL_LENGTH = 2048
MAX_STATUS_LENGTH = 20
MAX_COMPLIANCE_LENGTH = 20
MAX_REASON_LENGTH = 50
MAX_REASON_TEXT_LENGTH = 500
MAX_EDITOR_LENGTH = 100


class ApprovalItem(Base):
    """Content item pending approval.

    Stores content submitted for approval with quality scores,
    compliance status, and source priority for queue ordering.

    Attributes:
        id: Unique identifier (UUID)
        thumbnail_url: URL to preview thumbnail
        full_caption: Complete caption text
        original_caption: Original caption before any edits
        hashtags: List of hashtags for the content
        quality_score: Overall quality score (0-10)
        compliance_status: EU compliance check result
        compliance_details: Detailed compliance check results (JSONB)
        quality_breakdown: Quality score breakdown by factor (JSONB)
        rewrite_suggestions: AI-generated rewrite suggestions (JSONB)
        would_auto_publish: Whether content meets auto-publish criteria
        suggested_publish_time: Suggested time for publishing
        scheduled_publish_time: Confirmed scheduled publish time
        source_type: Content source type (instagram_post, b2b_email, etc.)
        source_priority: Source-based priority for queue ordering
        status: Approval workflow status
        rejection_reason: Reason for rejection (if rejected)
        rejection_text: Additional rejection details
        archived_at: When item was archived (rejected)
        approved_at: When item was approved
        approved_by: Who approved the item
        instagram_post_id: Instagram post ID after successful publish (Story 4-5)
        instagram_permalink: Instagram post URL after publish (Story 4-5)
        published_at: When content was published to Instagram (Story 4-5)
        publish_error: Error message if publish failed (Story 4-5)
        publish_attempts: Number of publish attempts (Story 4-5)
        created_at: When the item was submitted
        updated_at: When the item was last updated
    """

    __tablename__ = "approval_items"

    # Primary key - UUID for distributed compatibility
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Content fields
    thumbnail_url: Mapped[str] = mapped_column(
        String(MAX_URL_LENGTH),
        nullable=False,
    )

    full_caption: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Store original caption for revert functionality
    original_caption: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    hashtags: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        server_default="{}",
    )

    # Quality scoring
    quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    # Compliance
    compliance_status: Mapped[str] = mapped_column(
        String(MAX_COMPLIANCE_LENGTH),
        nullable=False,
        default=ComplianceStatus.COMPLIANT.value,
    )

    # Detailed data as JSONB
    compliance_details: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    quality_breakdown: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # AI rewrite suggestions (for edit UI)
    rewrite_suggestions: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # Auto-publish eligibility
    would_auto_publish: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Publishing times
    suggested_publish_time: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    scheduled_publish_time: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    # Source information
    source_type: Mapped[str] = mapped_column(
        String(MAX_SOURCE_TYPE_LENGTH),
        nullable=False,
        default="instagram_post",
    )

    source_priority: Mapped[int] = mapped_column(
        nullable=False,
        default=SourcePriority.EVERGREEN.value,
        index=True,  # Index for efficient queue sorting
    )

    # Workflow status
    status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=ApprovalStatus.PENDING.value,
        index=True,  # Index for filtering pending items
    )

    # Rejection tracking
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(MAX_REASON_LENGTH),
        nullable=True,
        default=None,
    )

    rejection_text: Mapped[Optional[str]] = mapped_column(
        String(MAX_REASON_TEXT_LENGTH),
        nullable=True,
        default=None,
    )

    archived_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    # Approval tracking
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    approved_by: Mapped[Optional[str]] = mapped_column(
        String(MAX_EDITOR_LENGTH),
        nullable=True,
        default=None,
    )

    # Instagram publishing fields (Story 4-5)
    instagram_post_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        index=True,  # Index for querying published posts
    )

    instagram_permalink: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    published_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    publish_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    publish_attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship to edit history
    edits: Mapped["List[ApprovalItemEdit]"] = relationship(
        "ApprovalItemEdit",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ApprovalItemEdit.edited_at.desc()",
    )

    # Table-level indexes for query performance
    __table_args__ = (
        # Composite index for queue sorting
        Index(
            "idx_approval_items_queue",
            status,
            source_priority,
            suggested_publish_time,
        ),
        # Index for source_priority to support efficient sorting
        Index("idx_approval_items_priority", source_priority.asc()),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ApprovalItem(id={self.id}, source_type={self.source_type}, "
            f"status={self.status}, priority={self.source_priority})>"
        )


class ApprovalItemEdit(Base):
    """Audit trail for caption edits.

    Records each edit to an approval item's caption for
    version history and rollback functionality.

    Attributes:
        id: Unique identifier (UUID)
        item_id: Foreign key to ApprovalItem
        previous_caption: Caption before this edit
        new_caption: Caption after this edit
        edited_at: Timestamp of the edit
        editor: Who made the edit (operator or system)
    """

    __tablename__ = "approval_item_edits"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("approval_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    previous_caption: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    new_caption: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    edited_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        server_default=func.now(),
    )

    editor: Mapped[str] = mapped_column(
        String(MAX_EDITOR_LENGTH),
        nullable=False,
        default="operator",
    )

    # Relationship back to item
    item: Mapped["ApprovalItem"] = relationship(
        "ApprovalItem",
        back_populates="edits",
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ApprovalItemEdit(id={self.id}, item_id={self.item_id}, "
            f"editor={self.editor}, edited_at={self.edited_at})>"
        )


__all__ = [
    "ApprovalItem",
    "ApprovalItemEdit",
    "ApprovalStatus",
    "SourcePriority",
    "ComplianceStatus",
    "RejectReasonType",
]
