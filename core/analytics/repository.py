"""Instagram metrics repository.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 2: Metrics repository with async SQLAlchemy.

Provides data access for InstagramMediaMetric with:
- Upsert via merge (ON CONFLICT DO UPDATE) for idempotent saves
- Batch queries to prevent N+1
- Average metrics computation in SQL
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.analytics.models import InstagramMediaMetric

logger = logging.getLogger(__name__)


class InstagramMetricsRepository:
    """Repository for Instagram engagement metrics persistence.

    Story 7-1, Task 2: SQLAlchemy persistence layer.

    Accepts AsyncSession via constructor injection.
    Uses merge for upsert behavior (UNIQUE constraint on media_id + snapshot_label).

    Attributes:
        _session: Async SQLAlchemy session
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    async def save_snapshot(
        self,
        metric: InstagramMediaMetric,
    ) -> InstagramMediaMetric:
        """Save or update a metrics snapshot.

        Task 2.3: Uses merge for INSERT ... ON CONFLICT DO UPDATE behavior.
        If a row with the same (media_id, snapshot_label) exists, it is updated.

        Args:
            metric: InstagramMediaMetric instance to persist

        Returns:
            Merged InstagramMediaMetric instance
        """
        merged = await self._session.merge(metric)
        await self._session.flush()
        logger.info(
            "Saved metrics snapshot: media_id=%s, label=%s",
            metric.media_id,
            metric.snapshot_label,
        )
        return merged

    async def get_by_media_id(
        self,
        media_id: str,
    ) -> Sequence[InstagramMediaMetric]:
        """Get all metrics snapshots for a media ID.

        Args:
            media_id: Instagram media ID

        Returns:
            Sequence of metrics ordered by collected_at ascending
        """
        result = await self._session.execute(
            select(InstagramMediaMetric)
            .where(InstagramMediaMetric.media_id == media_id)
            .order_by(InstagramMediaMetric.collected_at)
        )
        return result.scalars().all()

    async def get_latest_snapshot(
        self,
        media_id: str,
    ) -> Optional[InstagramMediaMetric]:
        """Get the most recent snapshot for a media ID.

        Args:
            media_id: Instagram media ID

        Returns:
            Latest InstagramMediaMetric or None
        """
        result = await self._session.execute(
            select(InstagramMediaMetric)
            .where(InstagramMediaMetric.media_id == media_id)
            .order_by(desc(InstagramMediaMetric.collected_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_media_ids(
        self,
        media_ids: list[str],
    ) -> dict[str, list[InstagramMediaMetric]]:
        """Batch query metrics for multiple media IDs.

        Task 2.4: Prevents N+1 by using a single IN query.

        Args:
            media_ids: List of Instagram media IDs

        Returns:
            Dict mapping media_id to list of metrics
        """
        if not media_ids:
            return {}

        result = await self._session.execute(
            select(InstagramMediaMetric)
            .where(InstagramMediaMetric.media_id.in_(media_ids))
            .order_by(
                InstagramMediaMetric.media_id,
                InstagramMediaMetric.collected_at,
            )
        )
        metrics = result.scalars().all()

        grouped: dict[str, list[InstagramMediaMetric]] = defaultdict(list)
        for m in metrics:
            grouped[m.media_id].append(m)
        return dict(grouped)

    async def get_average_metrics(
        self,
        days_back: int = 30,
    ) -> dict[str, float | int]:
        """Get average metrics across all posts within a time window.

        Computes averages from the latest snapshot per post (typically 7d).
        Filters by collected_at within the specified days_back window.

        Args:
            days_back: Number of days to look back (default 30)

        Returns:
            Dict with avg_impressions, avg_reach, avg_likes, etc. and post_count
        """
        cutoff = datetime.now(UTC) - timedelta(days=days_back)

        result = await self._session.execute(
            select(
                func.avg(InstagramMediaMetric.impressions).label("avg_impressions"),
                func.avg(InstagramMediaMetric.reach).label("avg_reach"),
                func.avg(InstagramMediaMetric.likes).label("avg_likes"),
                func.avg(InstagramMediaMetric.comments).label("avg_comments"),
                func.avg(InstagramMediaMetric.saved).label("avg_saved"),
                func.avg(InstagramMediaMetric.shares).label("avg_shares"),
                func.avg(InstagramMediaMetric.total_interactions).label("avg_total_interactions"),
                func.count(func.distinct(InstagramMediaMetric.media_id)).label("post_count"),
            )
            .where(InstagramMediaMetric.collected_at >= cutoff)
            .where(InstagramMediaMetric.snapshot_label == "7d")
        )

        row = result.one_or_none()
        if row is None:
            return {
                "avg_impressions": 0.0,
                "avg_reach": 0.0,
                "avg_likes": 0.0,
                "avg_comments": 0.0,
                "avg_saved": 0.0,
                "avg_shares": 0.0,
                "avg_total_interactions": 0.0,
                "post_count": 0,
            }

        return dict(row._mapping)

    async def commit(self) -> None:
        """Commit the current transaction.

        Called by pipeline orchestrator after all saves succeed.
        """
        await self._session.commit()


__all__ = [
    "InstagramMetricsRepository",
]
