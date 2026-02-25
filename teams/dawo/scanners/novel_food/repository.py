"""Novel Food Catalogue repository.

Epic 6, Story 6-2, Task 7: Novel Food repository.

SQLAlchemy persistence for Novel Food snapshots, entries, and changes.
Accepts AsyncSession via constructor. Never commits — pipeline calls commit().
"""

import hashlib
import json
import logging
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.regulatory.models import (
    NovelFoodEntry,
    NovelFoodSnapshot,
    NovelFoodChange,
)
from teams.dawo.scanners.novel_food.schemas import (
    NovelFoodEntryRecord,
    CatalogueChangeRecord,
)

logger = logging.getLogger(__name__)


class NovelFoodRepository:
    """Repository for Novel Food Catalogue data persistence.

    Story 6-2, Task 7: CRUD operations for novel food data.

    Uses flush() for writes, never commits. Pipeline orchestrator calls commit().
    Uses batch insert for entries.

    Attributes:
        _session: SQLAlchemy async session
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def save_snapshot(
        self,
        entries: list[NovelFoodEntryRecord],
        species_queried: int,
        search_duration: float,
    ) -> NovelFoodSnapshot:
        """Save a new snapshot with entries.

        Creates snapshot record, then batch-inserts all entries.

        Args:
            entries: Parsed entry records to persist
            species_queried: Number of species queried
            search_duration: Total search duration in seconds

        Returns:
            Created NovelFoodSnapshot instance
        """
        # Compute snapshot hash from sorted entry data
        snapshot_hash = self._compute_snapshot_hash(entries)

        snapshot = NovelFoodSnapshot(
            snapshot_hash=snapshot_hash,
            total_entries=len(entries),
            relevant_entries=len(entries),  # All queried species are relevant
            species_queried=species_queried,
            search_duration_seconds=search_duration,
        )
        self._session.add(snapshot)
        await self._session.flush()

        # Batch insert entries
        if entries:
            entry_mappings = [
                {
                    "snapshot_id": snapshot.id,
                    "species_latin": e.species_latin,
                    "species_common": e.species_common or None,
                    "entry_name": e.entry_name,
                    "novel_food_status": e.novel_food_status,
                    "authorization_status": e.authorization_status or None,
                    "history_of_consumption": e.history_of_consumption or None,
                    "member_state_comments": e.member_state_comments or None,
                    "commission_comments": e.commission_comments or None,
                    "conditions_of_use": e.conditions_of_use or None,
                    "regulation_reference": e.regulation_reference or None,
                    "union_list_entry": e.union_list_entry or None,
                    "source_url": e.source_url or None,
                    "raw_html_hash": e.raw_html_hash or None,
                }
                for e in entries
            ]
            await self._session.execute(
                NovelFoodEntry.__table__.insert(),
                entry_mappings,
            )
            await self._session.flush()

        logger.info(
            "Saved snapshot with %d entries (hash=%s)",
            len(entries),
            snapshot_hash[:12],
        )
        return snapshot

    async def get_latest_snapshot(self) -> Optional[NovelFoodSnapshot]:
        """Get the most recent snapshot.

        Returns:
            Most recent NovelFoodSnapshot or None if no snapshots exist
        """
        stmt = (
            select(NovelFoodSnapshot)
            .order_by(desc(NovelFoodSnapshot.created_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_entries_by_snapshot(
        self, snapshot_id: UUID
    ) -> Sequence[NovelFoodEntry]:
        """Get all entries for a snapshot.

        Args:
            snapshot_id: UUID of the snapshot

        Returns:
            Sequence of NovelFoodEntry records
        """
        stmt = select(NovelFoodEntry).where(
            NovelFoodEntry.snapshot_id == snapshot_id
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_entries_by_species(
        self, snapshot_id: UUID, species_latin: str
    ) -> list[NovelFoodEntry]:
        """Get entries filtered by species.

        Args:
            snapshot_id: UUID of the snapshot
            species_latin: Latin species name to filter by

        Returns:
            List of matching NovelFoodEntry records
        """
        stmt = (
            select(NovelFoodEntry)
            .where(NovelFoodEntry.snapshot_id == snapshot_id)
            .where(NovelFoodEntry.species_latin == species_latin)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save_changes(
        self, changes: list[CatalogueChangeRecord], snapshot_id: UUID
    ) -> int:
        """Save change records for a snapshot.

        Args:
            changes: Detected change records to persist
            snapshot_id: UUID of the new snapshot

        Returns:
            Number of changes saved
        """
        if not changes:
            return 0

        change_mappings = [
            {
                "snapshot_id": snapshot_id,
                "species_latin": c.species_latin,
                "entry_name": c.entry_name,
                "change_type": c.change_type,
                "field_changed": c.field_changed,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "severity": c.severity,
            }
            for c in changes
        ]
        await self._session.execute(
            NovelFoodChange.__table__.insert(),
            change_mappings,
        )
        await self._session.flush()

        logger.info("Saved %d change records for snapshot", len(changes))
        return len(changes)

    async def commit(self) -> None:
        """Commit the current transaction.

        Called by pipeline after all saves are complete.
        """
        await self._session.commit()

    def _compute_snapshot_hash(self, entries: list[NovelFoodEntryRecord]) -> str:
        """Compute SHA-256 hash from sorted entry data.

        Args:
            entries: Entry records to hash

        Returns:
            Hex-encoded SHA-256 hash string
        """
        sorted_data = sorted(
            [
                f"{e.species_latin}:{e.entry_name}:{e.novel_food_status}"
                for e in entries
            ]
        )
        return hashlib.sha256(
            json.dumps(sorted_data).encode("utf-8")
        ).hexdigest()


__all__ = [
    "NovelFoodRepository",
]
