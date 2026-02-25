"""SQLAlchemy models for Instagram engagement metrics.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 1.4: Create SQLAlchemy async model InstagramMediaMetric.

Stores cumulative lifetime metrics from Instagram Insights API
at defined intervals (baseline, 24h, 48h, 7d). Deltas are
computed at query time, not at collection time.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base

MAX_MEDIA_ID_LENGTH = 100
MAX_SNAPSHOT_LABEL_LENGTH = 20


class SnapshotLabel(str, Enum):
    """Collection interval labels for metrics snapshots.

    Values:
        BASELINE: First collection ~1 hour after publish
        DAY_1: Collection at T+24 hours
        DAY_2: Collection at T+48 hours
        DAY_7: Collection at T+7 days
    """

    BASELINE = "baseline"
    DAY_1 = "24h"
    DAY_2 = "48h"
    DAY_7 = "7d"


class InstagramMediaMetric(Base):
    """Instagram post engagement metrics at a point in time.

    Epic 7, Story 7-1: Instagram Engagement Metrics Collection.

    Stores cumulative lifetime values from the Instagram Insights API.
    Each row represents one snapshot (baseline, 24h, 48h, 7d) for a media_id.
    The UNIQUE(media_id, snapshot_label) constraint ensures idempotent upserts.

    Reel-specific metrics (plays, avg_watch_time_ms) are nullable since they
    only apply to Reels/Video content.
    """

    __tablename__ = "instagram_media_metrics"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Post identifier
    media_id: Mapped[str] = mapped_column(
        String(MAX_MEDIA_ID_LENGTH),
        nullable=False,
    )

    # Collection metadata
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    snapshot_label: Mapped[str] = mapped_column(
        String(MAX_SNAPSHOT_LABEL_LENGTH),
        nullable=False,
    )

    # Core engagement metrics (cumulative lifetime values)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, nullable=False)
    saved: Mapped[int] = mapped_column(Integer, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    total_interactions: Mapped[int] = mapped_column(Integer, nullable=False)

    # Reel-specific metrics (nullable -- only for video/reel content)
    plays: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_watch_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Raw API response for debugging/future metric extraction
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Record timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("media_id", "snapshot_label", name="uq_media_snapshot"),
        Index("idx_media_metrics_media_id", "media_id"),
        Index("idx_media_metrics_collected_at", "collected_at"),
        Index("idx_media_metrics_snapshot_label", "snapshot_label"),
    )

    def __repr__(self) -> str:
        return (
            f"<InstagramMediaMetric(media_id={self.media_id!r}, "
            f"snapshot_label={self.snapshot_label!r}, "
            f"likes={self.likes})>"
        )


__all__ = [
    "InstagramMediaMetric",
    "SnapshotLabel",
]
