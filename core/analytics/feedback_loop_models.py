"""SQLAlchemy models for performance feedback loop.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 1.1: FeedbackReport model.
Task 1.2: WeightAdjustmentRecord model.

Stores weekly feedback analysis reports and weight adjustment proposals.
FeedbackReport captures content type rankings, posting time analysis,
hashtag performance, and strategy recommendations. WeightAdjustmentRecord
tracks proposed and applied weight changes for operator transparency.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base

# Column length constants
MAX_STATUS_LENGTH = 20
MAX_ADJUSTMENT_TYPE_LENGTH = 50


class FeedbackReport(Base):
    """Weekly performance feedback analysis report.

    Story 7-5, Task 1.1: Stores results from weekly feedback analysis
    including content type rankings, posting time analysis, hashtag
    performance, weight adjustment proposals, and strategy recommendations.

    One report per report_date (unique index). Status is "complete" when
    all analysis sections succeed, "partial" when some sections fail
    with insufficient data.
    """

    __tablename__ = "feedback_reports"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Report date (unique — one report per week)
    report_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    # Threshold used for this run
    min_posts_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # How many posts were analyzed
    total_posts_analyzed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Analysis results (JSONB, nullable for partial reports)
    content_type_rankings: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    time_slot_analysis: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    hashtag_rankings: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    weight_adjustment_proposal: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    source_performance: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    recommendations: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # "complete" or "partial"
    status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    # Sections that failed due to insufficient data
    missing_sections: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Row insertion time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_feedback_reports_report_date", "report_date", unique=True),
        Index("idx_feedback_reports_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<FeedbackReport(report_date={self.report_date!s}, "
            f"status={self.status!r})>"
        )


class WeightAdjustmentRecord(Base):
    """Record of a proposed or applied weight adjustment.

    Story 7-5, Task 1.2: Tracks weight change proposals from correlation
    analysis. Adjustments are PROPOSED only — operator must explicitly
    apply them (human-in-the-loop).

    adjustment_type: "quality_scoring" or "source_scoring"
    """

    __tablename__ = "weight_adjustment_records"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Type of adjustment
    adjustment_type: Mapped[str] = mapped_column(
        String(MAX_ADJUSTMENT_TYPE_LENGTH),
        nullable=False,
    )

    # Before/after weights
    previous_weights: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    new_weights: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Correlation data that informed this adjustment
    correlation_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Whether this adjustment has been applied by operator
    applied: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # When operator applied the adjustment
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # FK to the feedback report that generated this proposal
    feedback_report_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("feedback_reports.id"),
        nullable=False,
    )

    # Row insertion time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_weight_adj_feedback_report_id", "feedback_report_id"),
        Index("idx_weight_adj_adjustment_type", "adjustment_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<WeightAdjustmentRecord(type={self.adjustment_type!r}, "
            f"applied={self.applied})>"
        )


__all__ = [
    "FeedbackReport",
    "WeightAdjustmentRecord",
    "MAX_ADJUSTMENT_TYPE_LENGTH",
    "MAX_STATUS_LENGTH",
]
