"""Competitor Content Duplicate Checker.

Epic 6, Story 6-5, Task 6: Deduplicate content using SHA-256 content_hash.
Uses batch SQL query (single IN clause) — no N+1 queries.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select, tuple_

from core.regulatory.models import CompetitorContent
from teams.dawo.scanners.competitor.schemas import ParsedContent

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CompetitorDuplicateChecker:
    """Check for duplicate competitor content using content_hash.

    Uses a single batch SQL query to check all items at once.

    Args:
        session: AsyncSession for database access
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def check_duplicates(
        self, items: list[ParsedContent]
    ) -> list[ParsedContent]:
        """Filter out items that already exist in the database.

        Uses batch query with (content_hash, competitor_name) pairs.

        Args:
            items: List of parsed content to check

        Returns:
            List of items NOT already in the database
        """
        if not items:
            return []

        # Build set of (hash, competitor_name) tuples for batch query
        hash_name_pairs = [
            (item.content_hash, item.competitor_name)
            for item in items
        ]

        # Single batch query — no N+1
        stmt = select(
            CompetitorContent.content_hash,
            CompetitorContent.competitor_name,
        ).where(
            tuple_(
                CompetitorContent.content_hash,
                CompetitorContent.competitor_name,
            ).in_(hash_name_pairs)
        )

        result = await self._session.execute(stmt)
        existing = {(row[0], row[1]) for row in result.all()}

        # Filter out existing items
        new_items = [
            item for item in items
            if (item.content_hash, item.competitor_name) not in existing
        ]

        logger.debug(
            "Dedup check: %d items, %d existing, %d new",
            len(items), len(items) - len(new_items), len(new_items),
        )

        return new_items


__all__ = [
    "CompetitorDuplicateChecker",
]
