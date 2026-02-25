"""Evidence Repository (Story 6-8, Task 7; Story 6-9, Task 1).

CRUD for immutable Evidence records with audit logging.
Search/filter methods for the evidence database UI.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, NoReturn
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import selectinload

from core.regulatory.models import Evidence, EvidenceAuditLog
from teams.dawo.scanners.evidence_collection.schemas import (
    EvidenceCreateDTO,
    ImmutableEvidenceError,
)
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ALLOWED_SORT_COLUMNS = frozenset({
    "captured_at",
    "severity",
    "competitor_name",
    "violation_type",
    "source_type",
    "claim_category",
})


class EvidenceRepository:
    """Repository for immutable evidence records.

    Enforces application-level immutability. All update attempts
    raise ImmutableEvidenceError.

    Args:
        session: SQLAlchemy async session.
        storage_service: For integrity verification.
    """

    def __init__(
        self, session: AsyncSession, storage_service: EvidenceStorageService
    ) -> None:
        self._session = session
        self._storage_service = storage_service

    async def create(self, dto: EvidenceCreateDTO) -> Evidence:
        """Create an Evidence record with audit log entry.

        Args:
            dto: Evidence creation data.

        Returns:
            Created Evidence ORM object.
        """
        evidence = Evidence(
            violation_id=dto.violation_id,
            competitor_name=dto.competitor_name,
            source_url=dto.source_url,
            source_type=dto.source_type,
            claim_text=dto.claim_text,
            claim_category=dto.claim_category,
            violation_type=dto.violation_type,
            severity=dto.severity,
            regulation_violated=dto.regulation_violated,
            detection_reasoning=dto.detection_reasoning,
            confidence=dto.confidence,
            screenshot_path=dto.screenshot_path,
            screenshot_hash=dto.screenshot_hash,
            screenshot_size_bytes=dto.screenshot_size_bytes,
            captured_at=dto.captured_at,
            evidence_metadata=dto.evidence_metadata,
        )
        self._session.add(evidence)

        audit = EvidenceAuditLog(
            evidence_id=evidence.id,
            action="created",
            actor="system",
            details={"source_url": dto.source_url, "competitor": dto.competitor_name},
        )
        self._session.add(audit)

        logger.debug(
            "Created evidence for violation %s (competitor=%s)",
            dto.violation_id,
            dto.competitor_name,
        )
        return evidence

    async def get_by_violation_id(self, violation_id: UUID) -> Evidence | None:
        """Get evidence by violation ID.

        Args:
            violation_id: UUID of the violation.

        Returns:
            Evidence if exists, None otherwise.
        """
        stmt = select(Evidence).where(Evidence.violation_id == violation_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_collected_violation_ids(self) -> set[UUID]:
        """Get set of violation IDs that have evidence records.

        Returns:
            Set of violation UUIDs with existing evidence.
        """
        stmt = select(Evidence.violation_id)
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def update(self, evidence_id: UUID, **kwargs: object) -> NoReturn:
        """ALWAYS raises ImmutableEvidenceError.

        Evidence records are legally defensible and must never be modified.
        Logs the blocked attempt in the audit log.

        Args:
            evidence_id: UUID of the evidence record.
            **kwargs: Attempted modifications.

        Raises:
            ImmutableEvidenceError: Always.
        """
        audit = EvidenceAuditLog(
            evidence_id=evidence_id,
            action="modification_blocked",
            actor="system",
            details={"attempted_changes": {k: str(v) for k, v in kwargs.items()}},
        )
        self._session.add(audit)
        logger.warning(
            "Blocked modification attempt on evidence %s: %s",
            evidence_id,
            list(kwargs.keys()),
        )
        raise ImmutableEvidenceError(
            f"Evidence {evidence_id} is immutable. Modification blocked."
        )

    async def verify_integrity(self, evidence_id: UUID) -> bool:
        """Verify evidence screenshot integrity.

        Args:
            evidence_id: UUID of the evidence record.

        Returns:
            True if hash matches, False otherwise.
        """
        stmt = select(Evidence).where(Evidence.id == evidence_id)
        result = await self._session.execute(stmt)
        evidence = result.scalars().first()

        if evidence is None:
            logger.warning("Evidence not found for integrity check: %s", evidence_id)
            return False

        is_valid = await self._storage_service.verify_integrity(
            evidence.screenshot_path, evidence.screenshot_hash
        )

        audit = EvidenceAuditLog(
            evidence_id=evidence_id,
            action="verified",
            actor="system",
            hash_verified=is_valid,
        )
        self._session.add(audit)

        return is_valid

    # --- Story 6-9: Search/filter methods ---

    async def search(
        self,
        *,
        competitor_name: str | None = None,
        violation_type: str | None = None,
        severity: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        claim_keywords: str | None = None,
        source_type: str | None = None,
        sort_by: str = "captured_at",
        sort_order: str = "desc",
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[Evidence], int]:
        """Search evidence with filters. Returns (results, total_count).

        Args:
            competitor_name: Exact match filter.
            violation_type: Exact match filter.
            severity: Exact match filter.
            date_from: Minimum captured_at (inclusive).
            date_to: Maximum captured_at (inclusive).
            claim_keywords: ILIKE substring match on claim_text.
            source_type: Exact match filter.
            sort_by: Column name to sort by.
            sort_order: 'asc' or 'desc'.
            limit: Max results per page (default 25).
            offset: Number of results to skip.

        Returns:
            Tuple of (evidence_list, total_count).
        """
        conditions: list = []

        if competitor_name:
            conditions.append(Evidence.competitor_name == competitor_name)
        if violation_type:
            conditions.append(Evidence.violation_type == violation_type)
        if severity:
            conditions.append(Evidence.severity == severity)
        if date_from:
            conditions.append(Evidence.captured_at >= date_from)
        if date_to:
            conditions.append(Evidence.captured_at <= date_to)
        if claim_keywords:
            conditions.append(Evidence.claim_text.ilike(f"%{claim_keywords}%"))
        if source_type:
            conditions.append(Evidence.source_type == source_type)

        where_clause = and_(*conditions) if conditions else True

        # Count query
        count_stmt = select(func.count(Evidence.id)).where(where_clause)
        total = await self._session.scalar(count_stmt) or 0

        # Sort — whitelist to prevent arbitrary attribute access
        if sort_by not in ALLOWED_SORT_COLUMNS:
            sort_by = "captured_at"
        sort_column = getattr(Evidence, sort_by)
        order = sort_column.desc() if sort_order == "desc" else sort_column.asc()

        # Data query
        stmt = (
            select(Evidence)
            .where(where_clause)
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        evidence_list = list(result.scalars().all())

        return evidence_list, total

    async def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        """Get evidence by ID with eager-loaded violation and audit_logs.

        Args:
            evidence_id: UUID of the evidence record.

        Returns:
            Evidence with relations loaded, or None.
        """
        stmt = (
            select(Evidence)
            .where(Evidence.id == evidence_id)
            .options(
                selectinload(Evidence.violation),
                selectinload(Evidence.audit_logs),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_lightweight(self, evidence_id: UUID) -> Evidence | None:
        """Get evidence by ID without eager-loaded relations.

        Use for endpoints that only need evidence fields (screenshot, download).

        Args:
            evidence_id: UUID of the evidence record.

        Returns:
            Evidence without relations, or None.
        """
        stmt = select(Evidence).where(Evidence.id == evidence_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_summary_stats(self) -> dict:
        """Get evidence counts by severity, competitor, and violation_type.

        Returns:
            Dict with total_evidence, by_severity, by_competitor, by_violation_type.
        """
        total = await self._session.scalar(select(func.count(Evidence.id))) or 0

        # By severity
        severity_stmt = (
            select(Evidence.severity, func.count(Evidence.id))
            .group_by(Evidence.severity)
        )
        severity_result = await self._session.execute(severity_stmt)
        by_severity = {row[0]: row[1] for row in severity_result.all()}

        # By competitor (ordered by count desc)
        competitor_stmt = (
            select(Evidence.competitor_name, func.count(Evidence.id))
            .group_by(Evidence.competitor_name)
            .order_by(func.count(Evidence.id).desc())
        )
        competitor_result = await self._session.execute(competitor_stmt)
        by_competitor = {row[0]: row[1] for row in competitor_result.all()}

        # By violation_type
        type_stmt = (
            select(Evidence.violation_type, func.count(Evidence.id))
            .group_by(Evidence.violation_type)
        )
        type_result = await self._session.execute(type_stmt)
        by_violation_type = {row[0]: row[1] for row in type_result.all()}

        return {
            "total_evidence": total,
            "by_severity": by_severity,
            "by_competitor": by_competitor,
            "by_violation_type": by_violation_type,
        }

    async def get_distinct_competitors(self) -> list[str]:
        """Get sorted list of distinct competitor names.

        Returns:
            Sorted list of unique competitor name strings.
        """
        stmt = (
            select(Evidence.competitor_name)
            .distinct()
            .order_by(Evidence.competitor_name.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_competitor_timeline(self, competitor_name: str) -> list[dict]:
        """Get monthly violation counts for a competitor.

        Args:
            competitor_name: Competitor to get timeline for.

        Returns:
            List of {month: 'YYYY-MM', count: int} dicts ordered ascending.
        """
        stmt = (
            select(
                func.to_char(Evidence.captured_at, "YYYY-MM").label("month"),
                func.count(Evidence.id).label("count"),
            )
            .where(Evidence.competitor_name == competitor_name)
            .group_by(func.to_char(Evidence.captured_at, "YYYY-MM"))
            .order_by(text("month ASC"))
        )
        result = await self._session.execute(stmt)
        return [{"month": row.month, "count": row.count} for row in result.all()]

    async def log_download(self, evidence_id: UUID) -> None:
        """Create audit log entry for evidence download.

        Args:
            evidence_id: UUID of the downloaded evidence.
        """
        audit = EvidenceAuditLog(
            evidence_id=evidence_id,
            action="downloaded",
            actor="operator",
        )
        self._session.add(audit)
        logger.debug("Logged download for evidence %s", evidence_id)

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()


__all__ = [
    "ALLOWED_SORT_COLUMNS",
    "EvidenceRepository",
]
