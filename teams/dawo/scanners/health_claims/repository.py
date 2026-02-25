"""Health Claims repository.

Epic 6, Story 6-1, Task 8: Health claims repository.

SQLAlchemy repository for persisting health claims, snapshots, and changes.
"""

import hashlib
import logging
from datetime import datetime, UTC
from typing import Optional, Sequence
from uuid import UUID

import pandas as pd
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.regulatory.models import (
    HealthClaim,
    ClaimSnapshot,
    ClaimChange,
)
from teams.dawo.scanners.health_claims.schemas import ClaimChangeRecord

logger = logging.getLogger(__name__)


class HealthClaimsRepository:
    """Repository for EU Health Claims data persistence.

    Story 6-1, Task 8: SQLAlchemy persistence layer.

    Accepts AsyncSession via constructor. Uses batch inserts for performance.

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
        claims_df: pd.DataFrame,
        source_url: str,
        file_size_bytes: int,
    ) -> ClaimSnapshot:
        """Save a register snapshot and its claims.

        Creates a ClaimSnapshot record and bulk-inserts all claims
        from the DataFrame. Uses batch insert for performance.

        Args:
            claims_df: DataFrame with parsed and filtered claims
            source_url: URL the data was downloaded from
            file_size_bytes: Size of downloaded data in bytes

        Returns:
            Created ClaimSnapshot record
        """
        # Compute hash for deduplication
        snapshot_hash = hashlib.sha256(
            claims_df.to_csv(index=False).encode("utf-8")
        ).hexdigest()

        relevant_count = int(claims_df["is_relevant"].sum()) if "is_relevant" in claims_df.columns else 0

        snapshot = ClaimSnapshot(
            snapshot_hash=snapshot_hash,
            claim_count=len(claims_df),
            relevant_claim_count=relevant_count,
            source_url=source_url,
            downloaded_at=datetime.now(UTC),
            file_size_bytes=file_size_bytes,
        )
        self._session.add(snapshot)
        await self._session.flush()  # Get snapshot.id for FK

        # Batch insert claims
        claim_mappings = []
        for _, row in claims_df.iterrows():
            claim_mappings.append({
                "snapshot_id": snapshot.id,
                "claim_id": str(row.get("claim_id", "")),
                "claim_type": str(row.get("claim_type", "")) if pd.notna(row.get("claim_type")) else None,
                "substance": str(row.get("substance", "")),
                "health_relationship": str(row.get("health_relationship", "")) if pd.notna(row.get("health_relationship")) else None,
                "claim_text": str(row.get("claim_text", "")) if pd.notna(row.get("claim_text")) else None,
                "conditions_of_use": str(row.get("conditions_of_use", "")) if pd.notna(row.get("conditions_of_use")) else None,
                "food_category": str(row.get("food_category", "")) if pd.notna(row.get("food_category")) else None,
                "status": str(row.get("status", "on_hold")),
                "efsa_opinion": str(row.get("efsa_opinion", "")) if pd.notna(row.get("efsa_opinion")) else None,
                "commission_regulation": str(row.get("commission_regulation", "")) if pd.notna(row.get("commission_regulation")) else None,
                "date_of_entry": row.get("date_of_entry") if pd.notna(row.get("date_of_entry")) else None,
                "last_update": row.get("last_update") if pd.notna(row.get("last_update")) else None,
                "restrictions": str(row.get("restrictions", "")) if pd.notna(row.get("restrictions")) else None,
                "is_relevant": bool(row.get("is_relevant", False)),
                "relevance_category": str(row.get("relevance_category", "")) if pd.notna(row.get("relevance_category")) else None,
            })

        if claim_mappings:
            await self._session.execute(
                HealthClaim.__table__.insert(),
                claim_mappings,
            )

        await self._session.flush()

        logger.info(
            "Saved snapshot %s: %d claims (%d relevant)",
            snapshot.id,
            len(claims_df),
            relevant_count,
        )
        return snapshot

    async def get_latest_snapshot(self) -> Optional[ClaimSnapshot]:
        """Get the most recent register snapshot.

        Returns:
            Latest ClaimSnapshot or None if no snapshots exist
        """
        result = await self._session.execute(
            select(ClaimSnapshot)
            .order_by(desc(ClaimSnapshot.downloaded_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_claims_by_snapshot(self, snapshot_id: UUID) -> Sequence[HealthClaim]:
        """Get all claims for a specific snapshot.

        Args:
            snapshot_id: UUID of the snapshot

        Returns:
            Sequence of HealthClaim records
        """
        result = await self._session.execute(
            select(HealthClaim)
            .where(HealthClaim.snapshot_id == snapshot_id)
        )
        return result.scalars().all()

    async def save_changes(
        self,
        changes: list[ClaimChangeRecord],
        snapshot_id: UUID,
    ) -> int:
        """Save detected changes for a snapshot.

        Does NOT commit — caller owns the transaction boundary.

        Args:
            changes: List of detected changes
            snapshot_id: UUID of the new snapshot

        Returns:
            Number of change records saved
        """
        if not changes:
            return 0

        change_mappings = [
            {
                "snapshot_id": snapshot_id,
                "claim_id": c.claim_id,
                "change_type": c.change_type,
                "field_changed": c.field_changed,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "is_relevant": c.is_relevant,
                "severity": c.severity,
            }
            for c in changes
        ]

        await self._session.execute(
            ClaimChange.__table__.insert(),
            change_mappings,
        )
        await self._session.flush()

        logger.info("Saved %d change records for snapshot %s", len(changes), snapshot_id)
        return len(changes)

    async def commit(self) -> None:
        """Commit the current transaction.

        Called by pipeline orchestrator after all saves succeed.
        """
        await self._session.commit()

    async def get_relevant_claims(self, snapshot_id: UUID) -> Sequence[HealthClaim]:
        """Get relevant claims for a specific snapshot.

        Args:
            snapshot_id: UUID of the snapshot

        Returns:
            Sequence of relevant HealthClaim records
        """
        result = await self._session.execute(
            select(HealthClaim)
            .where(
                HealthClaim.snapshot_id == snapshot_id,
                HealthClaim.is_relevant == True,  # noqa: E712
            )
        )
        return result.scalars().all()


__all__ = [
    "HealthClaimsRepository",
]
