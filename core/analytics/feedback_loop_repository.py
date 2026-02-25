"""Repository for feedback loop data access.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 2.1: FeedbackLoopRepository with constructor injection.

Follows the same patterns as QualityScoringRepository (Story 7-4):
- AsyncSession via constructor injection
- Merge for upsert (idempotent by report_date)
- SQL ordering and filtering in database
"""

import logging
from datetime import UTC, date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.analytics.feedback_loop_models import (
    FeedbackReport,
    WeightAdjustmentRecord,
)

logger = logging.getLogger(__name__)


class FeedbackLoopRepository:
    """Data access layer for feedback loop reports and weight adjustments.

    Provides CRUD operations and query methods for FeedbackReport
    and WeightAdjustmentRecord. All database operations use async
    SQLAlchemy patterns.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with async database session.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._session = session

    async def save_report(self, report: FeedbackReport) -> FeedbackReport:
        """Save or update a feedback report (upsert by report_date).

        Uses merge for idempotent upserts.

        Args:
            report: The feedback report to save.

        Returns:
            The merged (persisted) report.
        """
        merged = await self._session.merge(report)
        await self._session.flush()
        return merged

    async def get_latest_report(self) -> Optional[FeedbackReport]:
        """Get the most recent feedback report.

        Returns:
            The latest report by report_date, or None if no reports exist.
        """
        stmt = (
            select(FeedbackReport)
            .order_by(FeedbackReport.report_date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reports_by_date_range(
        self, start: date, end: date
    ) -> list[FeedbackReport]:
        """Get reports within a date range.

        Args:
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            List of reports ordered by report_date ascending.
        """
        stmt = (
            select(FeedbackReport)
            .where(
                FeedbackReport.report_date >= start,
                FeedbackReport.report_date <= end,
            )
            .order_by(FeedbackReport.report_date.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save_weight_adjustment(
        self, record: WeightAdjustmentRecord
    ) -> WeightAdjustmentRecord:
        """Save a weight adjustment record.

        Args:
            record: The weight adjustment record to save.

        Returns:
            The merged (persisted) record.
        """
        merged = await self._session.merge(record)
        await self._session.flush()
        return merged

    async def get_weight_history(
        self, adjustment_type: str, limit: int = 10
    ) -> list[WeightAdjustmentRecord]:
        """Get weight adjustment history for a specific type.

        Args:
            adjustment_type: "quality_scoring" or "source_scoring".
            limit: Maximum records to return.

        Returns:
            List of records ordered by created_at descending.
        """
        stmt = (
            select(WeightAdjustmentRecord)
            .where(WeightAdjustmentRecord.adjustment_type == adjustment_type)
            .order_by(WeightAdjustmentRecord.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_adjustment_applied(self, record_id: UUID) -> None:
        """Mark a weight adjustment as applied by operator.

        Args:
            record_id: UUID of the adjustment record.

        Raises:
            ValueError: If record not found.
        """
        stmt = select(WeightAdjustmentRecord).where(
            WeightAdjustmentRecord.id == record_id
        )
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            raise ValueError(f"WeightAdjustmentRecord {record_id} not found")

        record.applied = True
        record.applied_at = datetime.now(UTC)
        await self._session.flush()


__all__ = [
    "FeedbackLoopRepository",
]
