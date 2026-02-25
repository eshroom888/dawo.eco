"""Competitor Content Repository.

Epic 6, Story 6-5, Task 7: Database persistence for competitor scan data.
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Sequence
from uuid import UUID

from sqlalchemy import select

from core.regulatory.models import (
    CompetitorContent,
    CompetitorScanSnapshot,
    ExtractionStatus,
)
from teams.dawo.scanners.competitor.schemas import ParsedContent

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CompetitorRepository:
    """Repository for competitor scan snapshots and content.

    Args:
        session: AsyncSession for database access
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_snapshot(
        self, competitor_name: str, source_type: str
    ) -> CompetitorScanSnapshot:
        """Create a new scan snapshot record.

        Args:
            competitor_name: Name of the competitor being scanned
            source_type: Source type (instagram or website)

        Returns:
            Created CompetitorScanSnapshot with in_progress status
        """
        snapshot = CompetitorScanSnapshot(
            competitor_name=competitor_name,
            source_type=source_type,
            scan_started_at=datetime.now(UTC),
            status="in_progress",
        )
        self._session.add(snapshot)
        return snapshot

    async def save_content_batch(
        self, items: list[ParsedContent], snapshot_id: UUID
    ) -> int:
        """Bulk insert content items.

        Args:
            items: Parsed content items to save
            snapshot_id: ID of the parent snapshot

        Returns:
            Number of items saved
        """
        if not items:
            return 0

        models = [
            CompetitorContent(
                snapshot_id=snapshot_id,
                competitor_name=item.competitor_name,
                source_type=item.source_type,
                source_url=item.source_url,
                content_text=item.content_text,
                hashtags=item.hashtags if item.hashtags else None,
                account_or_domain=item.account_or_domain,
                published_at=item.published_at,
                captured_at=datetime.now(UTC),
                content_hash=item.content_hash,
                has_health_language=item.has_health_language,
                health_keywords_matched=(
                    item.health_keywords_matched
                    if item.health_keywords_matched
                    else None
                ),
                extraction_status=(
                    ExtractionStatus.PENDING.value
                    if item.has_health_language
                    else ExtractionStatus.NO_CLAIMS.value
                ),
            )
            for item in items
        ]

        self._session.add_all(models)

        logger.info("Saved %d content items for snapshot %s", len(models), snapshot_id)
        return len(models)

    async def update_snapshot_stats(
        self,
        snapshot_id: UUID,
        total: int,
        health_count: int,
        status: str,
    ) -> None:
        """Update snapshot statistics after scan completion.

        Args:
            snapshot_id: Snapshot to update
            total: Total items found
            health_count: Items with health language
            status: New status (completed or failed)
        """
        stmt = select(CompetitorScanSnapshot).where(
            CompetitorScanSnapshot.id == snapshot_id
        )
        result = await self._session.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if snapshot:
            snapshot.total_items_found = total
            snapshot.items_with_health_language = health_count
            snapshot.status = status
            snapshot.scan_completed_at = datetime.now(UTC)

    async def get_pending_extraction(self) -> Sequence[CompetitorContent]:
        """Get content items pending health claim extraction (for Story 6-6).

        Returns:
            Sequence of CompetitorContent with extraction_status="pending"
        """
        stmt = select(CompetitorContent).where(
            CompetitorContent.extraction_status == ExtractionStatus.PENDING.value
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def commit(self) -> None:
        """Commit current transaction."""
        await self._session.commit()


__all__ = [
    "CompetitorRepository",
]
