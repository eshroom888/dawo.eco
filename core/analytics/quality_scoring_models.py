"""SQLAlchemy models for post-publish quality scoring.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 1.1: Create PostPublishScoreRecord model.

Stores computed post-publish performance scores and their comparison
against pre-publish quality predictions. Supports variance tracking,
flagging outliers, and correlation analysis.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base

# Column length constants
MAX_POST_ID_LENGTH = 100
MAX_MEDIA_ID_LENGTH = 100
MAX_SNAPSHOT_LABEL_LENGTH = 20


class PostPublishScoreRecord(Base):
    """Post-publish performance score for a published post.

    Story 7-4, Task 1.1: Stores actual performance scores computed
    from engagement, reach, CTR, conversions, and sentiment data
    collected at a defined interval (default 7 days) after publish.

    The variance field tracks the difference between predicted
    (pre-publish) and actual (post-publish) scores. Large variances
    are flagged for operator review.

    Upserted by post_id (idempotent).
    """

    __tablename__ = "post_publish_scores"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Post identifier (unique — idempotent upsert key)
    post_id: Mapped[str] = mapped_column(
        String(MAX_POST_ID_LENGTH),
        nullable=False,
    )

    # Instagram media ID (nullable — for posts not yet published)
    media_id: Mapped[Optional[str]] = mapped_column(
        String(MAX_MEDIA_ID_LENGTH),
        nullable=True,
    )

    # Pre-publish quality score from ContentQualityScorer (nullable)
    pre_publish_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 1),
        nullable=True,
    )

    # Computed actual performance score (1.0-10.0)
    post_publish_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        nullable=False,
    )

    # post_publish_score - pre_publish_score (0 if no pre-publish score)
    variance: Mapped[Decimal] = mapped_column(
        Numeric(5, 1),
        nullable=False,
    )

    # JSONB: breakdown by component with raw_score, weight, weighted_score
    component_scores: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    # JSONB: raw metrics used for calculation
    metrics_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    # True if abs(variance) > threshold
    flagged_for_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Which metrics snapshot interval was used (default "7d")
    snapshot_label: Mapped[str] = mapped_column(
        String(MAX_SNAPSHOT_LABEL_LENGTH),
        nullable=False,
        default="7d",
    )

    # When score was computed
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Row insertion time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_post_publish_scores_post_id", "post_id", unique=True),
        Index("idx_post_publish_scores_calculated_at", "calculated_at"),
        Index("idx_post_publish_scores_flagged", "flagged_for_review"),
    )

    def __repr__(self) -> str:
        return (
            f"<PostPublishScoreRecord(post_id={self.post_id!r}, "
            f"score={self.post_publish_score})>"
        )


__all__ = [
    "PostPublishScoreRecord",
    "MAX_MEDIA_ID_LENGTH",
    "MAX_POST_ID_LENGTH",
    "MAX_SNAPSHOT_LABEL_LENGTH",
]
