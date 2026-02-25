"""Repository for post-publish quality scoring data access.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 2: QualityScoringRepository with constructor injection.

Follows the same patterns as InstagramMetricsRepository (Story 7-1):
- AsyncSession via constructor injection
- Merge for upsert (idempotent by post_id)
- Batch queries via IN clause (no N+1)
- SQL aggregations in database, not in-memory Python
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.analytics.quality_scoring_models import PostPublishScoreRecord

logger = logging.getLogger(__name__)


class QualityScoringRepository:
    """Data access layer for post-publish quality scores.

    Provides CRUD operations and aggregation queries for
    PostPublishScoreRecord. All database operations use async
    SQLAlchemy patterns with proper index utilization.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with async database session.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._session = session

    async def save_score(
        self, record: PostPublishScoreRecord
    ) -> PostPublishScoreRecord:
        """Save or update a post-publish score record (upsert by post_id).

        Uses merge for idempotent upserts, same pattern as
        InstagramMetricsRepository.save_snapshot().

        Args:
            record: The score record to save.

        Returns:
            The merged (persisted) record.
        """
        merged = await self._session.merge(record)
        await self._session.flush()
        return merged

    async def get_by_post_id(
        self, post_id: str
    ) -> Optional[PostPublishScoreRecord]:
        """Get a score record by post ID.

        Args:
            post_id: The post identifier.

        Returns:
            The score record, or None if not found.
        """
        stmt = select(PostPublishScoreRecord).where(
            PostPublishScoreRecord.post_id == post_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_post_ids(
        self, post_ids: list[str]
    ) -> dict[str, PostPublishScoreRecord]:
        """Batch query for multiple post IDs (prevents N+1).

        Args:
            post_ids: List of post identifiers.

        Returns:
            Dict mapping post_id to record. Missing IDs are absent.
        """
        if not post_ids:
            return {}

        stmt = select(PostPublishScoreRecord).where(
            PostPublishScoreRecord.post_id.in_(post_ids)
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()
        return {r.post_id: r for r in records}

    async def get_flagged_for_review(
        self, limit: int = 50
    ) -> list[PostPublishScoreRecord]:
        """Get records flagged for review, ordered by variance magnitude.

        Args:
            limit: Maximum records to return.

        Returns:
            List of flagged records, highest variance first.
        """
        stmt = (
            select(PostPublishScoreRecord)
            .where(PostPublishScoreRecord.flagged_for_review.is_(True))
            .order_by(func.abs(PostPublishScoreRecord.variance).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_scored(
        self, limit: int = 500
    ) -> list[PostPublishScoreRecord]:
        """Get all records with both pre- and post-publish scores.

        Args:
            limit: Maximum records to return.

        Returns:
            List of scored records, most recent first.
        """
        stmt = (
            select(PostPublishScoreRecord)
            .where(PostPublishScoreRecord.pre_publish_score.isnot(None))
            .order_by(PostPublishScoreRecord.calculated_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_scored_count(self) -> int:
        """Count records with both pre- and post-publish scores.

        Used to determine when correlation analysis threshold (50+) is met.

        Returns:
            Count of records with both scores.
        """
        stmt = select(func.count(PostPublishScoreRecord.id)).where(
            PostPublishScoreRecord.pre_publish_score.isnot(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_average_post_publish_score(
        self, days_back: int = 30
    ) -> Optional[Decimal]:
        """Get average post-publish score over recent period.

        SQL AVG aggregation — computed in database, not Python.

        Args:
            days_back: Number of days to look back.

        Returns:
            Average score as Decimal, or None if no records.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        stmt = select(func.avg(PostPublishScoreRecord.post_publish_score)).where(
            PostPublishScoreRecord.calculated_at >= cutoff
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_component_averages(
        self, days_back: int = 30
    ) -> dict[str, float]:
        """Get average weighted score per component across scored posts.

        Loads records and computes averages from JSONB component_scores.
        Uses database filtering on date range, then Python aggregation
        on the JSONB field (JSONB aggregation across varying keys).

        Note: Python-side aggregation chosen over SQL because component
        keys vary per record. Acceptable at <500 records per query.

        Args:
            days_back: Number of days to look back.

        Returns:
            Dict mapping component name to average weighted_score.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        stmt = (
            select(PostPublishScoreRecord)
            .where(PostPublishScoreRecord.calculated_at >= cutoff)
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return {}

        # Aggregate weighted_score per component
        component_sums: dict[str, float] = defaultdict(float)
        component_counts: dict[str, int] = defaultdict(int)

        for record in records:
            for component_name, detail in record.component_scores.items():
                weighted_score = detail.get("weighted_score", 0.0)
                component_sums[component_name] += weighted_score
                component_counts[component_name] += 1

        return {
            name: component_sums[name] / component_counts[name]
            for name in component_sums
        }


__all__ = [
    "QualityScoringRepository",
]
