"""Health Claim Repository for extracted claims storage.

Epic 6, Story 6-6, Task 7: HealthClaimRepository.

Handles CRUD operations for ExtractedHealthClaim records.
Uses AsyncSession via dependency injection.

Classes:
    HealthClaimRepository: Async repository for extracted claims.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from core.regulatory.models import CompetitorContent, ExtractedHealthClaim
from teams.dawo.scanners.claim_extraction.schemas import ClaimExtractionResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class HealthClaimRepository:
    """Repository for extracted health claims.

    Args:
        session: SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_claims(
        self,
        content_id: UUID,
        claims: list[ClaimExtractionResult],
        confidence_threshold: int = 70,
    ) -> int:
        """Bulk insert extracted claims for a content item.

        Args:
            content_id: UUID of the source CompetitorContent.
            claims: List of extraction results to persist.
            confidence_threshold: Claims at or above get "auto_approved",
                below get "manual_review".

        Returns:
            Number of claims saved.
        """
        if not claims:
            return 0

        for claim in claims:
            review_status = (
                "auto_approved"
                if claim.confidence_score >= confidence_threshold
                else "manual_review"
            )
            record = ExtractedHealthClaim(
                competitor_content_id=content_id,
                claim_text=claim.claim_text,
                surrounding_context=claim.surrounding_context,
                claim_category=claim.claim_category,
                confidence_score=claim.confidence_score,
                language_detected=claim.language_detected,
                extraction_method=claim.extraction_method,
                eu_article_reference=claim.eu_article_reference,
                matched_pattern=claim.matched_pattern,
                llm_reasoning=claim.llm_reasoning,
                review_status=review_status,
            )
            self._session.add(record)

        logger.debug("Saved %d claims for content %s", len(claims), content_id)
        return len(claims)

    async def update_extraction_status(
        self, content_id: UUID, status: str
    ) -> None:
        """Update extraction_status on CompetitorContent.

        Args:
            content_id: UUID of the content to update.
            status: New extraction status value.
        """
        stmt = (
            update(CompetitorContent)
            .where(CompetitorContent.id == content_id)
            .values(extraction_status=status)
        )
        await self._session.execute(stmt)
        logger.debug(
            "Updated extraction_status=%s for content %s", status, content_id
        )

    async def get_high_confidence_claims(
        self,
        min_confidence: int = 70,
        limit: int | None = None,
    ) -> Sequence[ExtractedHealthClaim]:
        """Get claims above confidence threshold with eager-loaded relationships.

        Eagerly loads competitor_content relationship to prevent N+1 queries
        and MissingGreenlet errors in async context (Story 6-7 requirement).

        Args:
            min_confidence: Minimum confidence score.
            limit: Maximum number of claims to return (SQL LIMIT).

        Returns:
            Sequence of ExtractedHealthClaim above threshold.
        """
        stmt = (
            select(ExtractedHealthClaim)
            .options(selectinload(ExtractedHealthClaim.competitor_content))
            .where(ExtractedHealthClaim.confidence_score >= min_confidence)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_claims_for_content(
        self, content_id: UUID
    ) -> Sequence[ExtractedHealthClaim]:
        """Get all claims for a specific content item.

        Args:
            content_id: UUID of the CompetitorContent.

        Returns:
            Sequence of ExtractedHealthClaim for that content.
        """
        stmt = select(ExtractedHealthClaim).where(
            ExtractedHealthClaim.competitor_content_id == content_id
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()


__all__ = [
    "HealthClaimRepository",
]
