"""Violation Repository (Story 6-7, Task 6).

Handles CRUD operations for CompetitorViolation records.
Uses AsyncSession via dependency injection.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Sequence
from uuid import UUID

from sqlalchemy import select

from core.regulatory.models import CompetitorViolation
from teams.dawo.scanners.violation_detection.schemas import ViolationResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ViolationRepository:
    """Repository for competitor violation records.

    Args:
        session: SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_violation(self, result: ViolationResult) -> CompetitorViolation:
        """Insert a single violation record.

        Args:
            result: ViolationResult to persist.

        Returns:
            Created CompetitorViolation ORM object.
        """
        violation = CompetitorViolation(
            extracted_claim_id=result.extracted_claim_id,
            violation_status=result.violation_status,
            severity=result.severity,
            regulation_article=result.regulation_article,
            violation_type=result.violation_type,
            detection_reasoning=result.detection_reasoning,
            authorized_claims_checked=result.authorized_claims_checked,
            nearest_authorized_claim=result.nearest_authorized_claim,
            competitor_name=result.competitor_name,
            source_url=result.source_url,
            evidence_status=result.evidence_status,
            detected_at=datetime.now(UTC),
        )
        self._session.add(violation)
        logger.debug(
            "Saved violation for claim %s: status=%s",
            result.extracted_claim_id,
            result.violation_status,
        )
        return violation

    async def save_violations_batch(
        self, results: list[ViolationResult]
    ) -> int:
        """Bulk insert violation records.

        Args:
            results: List of ViolationResult to persist.

        Returns:
            Number of records saved.
        """
        if not results:
            return 0

        for result in results:
            await self.save_violation(result)

        logger.debug("Saved %d violation records in batch", len(results))
        return len(results)

    async def get_evaluated_claim_ids(self) -> set[UUID]:
        """Return set of extracted_claim_id values with existing violations.

        Used for idempotency check — skip claims already evaluated.

        Returns:
            Set of UUIDs for claims that already have violation records.
        """
        stmt = select(CompetitorViolation.extracted_claim_id)
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def get_violations_by_status(
        self, status: str
    ) -> Sequence[CompetitorViolation]:
        """Get violations filtered by violation_status.

        Args:
            status: Violation status to filter by.

        Returns:
            Sequence of matching CompetitorViolation records.
        """
        stmt = select(CompetitorViolation).where(
            CompetitorViolation.violation_status == status
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_violations_by_competitor(
        self, competitor_name: str
    ) -> Sequence[CompetitorViolation]:
        """Get violations filtered by competitor_name.

        Args:
            competitor_name: Competitor name to filter by.

        Returns:
            Sequence of matching CompetitorViolation records.
        """
        stmt = select(CompetitorViolation).where(
            CompetitorViolation.competitor_name == competitor_name
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_pending_evidence_collection(
        self,
    ) -> Sequence[CompetitorViolation]:
        """Get violations pending evidence collection (for Story 6-8).

        Returns:
            Sequence of violations with evidence_status='pending_collection'.
        """
        stmt = select(CompetitorViolation).where(
            CompetitorViolation.evidence_status == "pending_collection"
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()


__all__ = [
    "ViolationRepository",
]
