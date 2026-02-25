"""Mattilsynet data repository.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 9: SQLAlchemy persistence for snapshots, updates, and page hashes.
"""

import hashlib
import logging
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.regulatory.models import (
    MattilsynetSnapshot,
    MattilsynetUpdate,
    MattilsynetPageHash,
)
from teams.dawo.scanners.mattilsynet.schemas import RegulatoryUpdateRecord

logger = logging.getLogger(__name__)


class MattilsynetRepository:
    """Repository for Mattilsynet regulatory data.

    Handles persistence of scan snapshots, regulatory updates,
    and page hash tracking. Uses flush() internally; pipeline
    calls commit().

    Attributes:
        _session: SQLAlchemy async session
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            session: SQLAlchemy AsyncSession instance
        """
        self._session = session

    async def save_snapshot(
        self,
        total_updates: int,
        relevant_updates: int,
        feeds_checked: int,
        pages_checked: int,
        scan_duration: float,
    ) -> MattilsynetSnapshot:
        """Save a new scan snapshot.

        Args:
            total_updates: Total updates found
            relevant_updates: Relevant updates found
            feeds_checked: Number of feeds checked
            pages_checked: Number of pages checked
            scan_duration: Scan duration in seconds

        Returns:
            Created MattilsynetSnapshot instance
        """
        hash_input = f"{total_updates}:{relevant_updates}:{feeds_checked}:{pages_checked}:{datetime.now(UTC).isoformat()}"
        snapshot_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        snapshot = MattilsynetSnapshot(
            snapshot_hash=snapshot_hash,
            total_updates=total_updates,
            relevant_updates=relevant_updates,
            feeds_checked=feeds_checked,
            pages_checked=pages_checked,
            scan_duration_seconds=scan_duration,
        )
        self._session.add(snapshot)
        await self._session.flush()

        logger.debug("Saved snapshot %s", snapshot.id)
        return snapshot

    async def get_latest_snapshot(self) -> Optional[MattilsynetSnapshot]:
        """Get the most recent scan snapshot.

        Returns:
            Latest MattilsynetSnapshot or None
        """
        result = await self._session.execute(
            select(MattilsynetSnapshot)
            .order_by(MattilsynetSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_updates(
        self,
        updates: list[RegulatoryUpdateRecord],
        snapshot_id: UUID,
    ) -> int:
        """Save regulatory updates via batch insert.

        Args:
            updates: List of update records to persist
            snapshot_id: Foreign key to snapshot

        Returns:
            Count of saved updates
        """
        if not updates:
            return 0

        mappings = [
            {
                "snapshot_id": snapshot_id,
                "title": u.title,
                "url": u.url,
                "content_summary": u.content_summary,
                "published_at": u.published_at,
                "source_type": u.source_type,
                "category": u.category,
                "keywords_matched": u.keywords_matched,
                "relevance_tier": u.relevance_tier,
                "severity": u.severity,
                "is_relevant": u.is_relevant,
                "raw_content_hash": u.raw_content_hash,
            }
            for u in updates
        ]

        await self._session.execute(
            MattilsynetUpdate.__table__.insert(), mappings
        )
        await self._session.flush()

        logger.debug("Saved %d updates for snapshot %s", len(mappings), snapshot_id)
        return len(mappings)

    async def get_known_urls(self, since: datetime) -> set[str]:
        """Get URLs of previously seen updates for deduplication.

        Args:
            since: Only return URLs from updates created after this time

        Returns:
            Set of known update URLs
        """
        result = await self._session.execute(
            select(MattilsynetUpdate.url).where(
                MattilsynetUpdate.created_at >= since
            )
        )
        return {row[0] for row in result.all()}

    async def get_page_hash(self, url: str) -> Optional[MattilsynetPageHash]:
        """Get stored page hash for a URL.

        Args:
            url: Page URL

        Returns:
            MattilsynetPageHash or None
        """
        result = await self._session.execute(
            select(MattilsynetPageHash).where(
                MattilsynetPageHash.url == url
            )
        )
        return result.scalar_one_or_none()

    async def save_page_hash(
        self,
        url: str,
        page_name: str,
        content_hash: str,
    ) -> MattilsynetPageHash:
        """Save a new page hash record.

        Args:
            url: Page URL
            page_name: Human-readable page name
            content_hash: SHA-256 hash of page content

        Returns:
            Created MattilsynetPageHash instance
        """
        now = datetime.now(UTC)
        page_hash = MattilsynetPageHash(
            url=url,
            page_name=page_name,
            content_hash=content_hash,
            last_checked=now,
            last_changed=None,
        )
        self._session.add(page_hash)
        await self._session.flush()

        logger.debug("Saved page hash for '%s'", url)
        return page_hash

    async def update_page_hash(
        self,
        url: str,
        content_hash: str,
        changed: bool,
    ) -> None:
        """Update an existing page hash record.

        Args:
            url: Page URL
            content_hash: New SHA-256 hash
            changed: Whether content actually changed
        """
        now = datetime.now(UTC)
        page_hash = await self.get_page_hash(url)
        if page_hash is None:
            logger.warning("No page hash found for '%s', cannot update", url)
            return

        page_hash.content_hash = content_hash
        page_hash.last_checked = now
        if changed:
            page_hash.last_changed = now

        await self._session.flush()
        logger.debug("Updated page hash for '%s' (changed=%s)", url, changed)

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()
        logger.debug("Transaction committed")


__all__ = [
    "MattilsynetRepository",
]
