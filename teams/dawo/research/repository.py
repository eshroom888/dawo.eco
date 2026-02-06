"""Research Pool Repository for database operations.

Provides async CRUD operations for research items using SQLAlchemy.
Follows the repository pattern with dependency-injected sessions.

Usage:
    from sqlalchemy.ext.asyncio import AsyncSession
    from teams.dawo.research import ResearchPoolRepository, ResearchQueryFilters

    # Create repository with injected session
    repo = ResearchPoolRepository(session)

    # Add item
    item = await repo.add_item(item_create)

    # Query with filters
    filters = ResearchQueryFilters(source=ResearchSource.REDDIT, min_score=7.0)
    items = await repo.query(filters)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID, uuid4
import logging

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ResearchItem, ResearchSource, ComplianceStatus, DEFAULT_LIMIT
from .schemas import ResearchItemCreate, ResearchItemUpdate
from .exceptions import ItemNotFoundError, DatabaseError

# Module logger
logger = logging.getLogger(__name__)


@dataclass
class ResearchQueryFilters:
    """Query parameters for Research Pool searches.

    All filter fields are optional. When None, no filtering is applied
    for that field.

    Attributes:
        source: Filter by research source type
        tags: Filter by tag overlap (ANY match)
        min_score: Minimum score threshold (inclusive)
        max_score: Maximum score threshold (inclusive)
        start_date: Created after this datetime (inclusive)
        end_date: Created before this datetime (inclusive)
        compliance_status: Filter by compliance check result
        limit: Maximum items to return (default: 50)
        offset: Number of items to skip (default: 0)
        sort_by: Sort order - "score" (default), "date", or "relevance"
    """

    source: Optional[ResearchSource] = None
    tags: Optional[list[str]] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    compliance_status: Optional[ComplianceStatus] = None
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    sort_by: str = "score"


class ResearchPoolRepository:
    """Repository for Research Pool database operations.

    Provides async CRUD operations for research items.
    Accepts AsyncSession via dependency injection from Team Builder.

    CRITICAL: NEVER create sessions directly - accept via constructor injection.

    Attributes:
        _session: SQLAlchemy async session for database operations
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with async session.

        Args:
            session: SQLAlchemy AsyncSession injected by Team Builder.
                    NEVER create sessions directly in this class.
        """
        self._session = session

    async def add_item(self, item: ResearchItemCreate) -> ResearchItem:
        """Add a new research item to the pool.

        Creates a new ResearchItem from the provided schema data.
        Generates UUID and sets timestamps if not provided.

        Args:
            item: Validated research item data

        Returns:
            Created ResearchItem with generated ID

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Build model from schema
            db_item = ResearchItem(
                id=item.id or uuid4(),
                source=item.source.value,
                title=item.title,
                content=item.content,
                url=item.url,
                tags=item.tags or [],
                source_metadata=item.source_metadata or {},
                created_at=item.created_at or datetime.now(timezone.utc),
                score=item.score,
                compliance_status=item.compliance_status.value,
            )

            self._session.add(db_item)
            await self._session.commit()
            await self._session.refresh(db_item)

            return db_item

        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to add research item: %s", e)
            raise DatabaseError("add_item", e) from e

    async def get_by_id(self, item_id: UUID) -> Optional[ResearchItem]:
        """Get a research item by its ID.

        Args:
            item_id: UUID of the item to retrieve

        Returns:
            ResearchItem if found, None otherwise
        """
        stmt = select(ResearchItem).where(ResearchItem.id == item_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def query(self, filters: ResearchQueryFilters) -> Sequence[ResearchItem]:
        """Query research items with optional filters.

        Applies filters dynamically based on provided values.
        Results are sorted by score descending by default.

        Args:
            filters: Query filter parameters

        Returns:
            List of matching ResearchItem objects
        """
        stmt = select(ResearchItem)

        # Apply source filter
        if filters.source is not None:
            stmt = stmt.where(ResearchItem.source == filters.source.value)

        # Apply tags filter (ANY match - overlap)
        if filters.tags:
            stmt = stmt.where(ResearchItem.tags.overlap(filters.tags))

        # Apply score range filters
        if filters.min_score is not None:
            stmt = stmt.where(ResearchItem.score >= filters.min_score)
        if filters.max_score is not None:
            stmt = stmt.where(ResearchItem.score <= filters.max_score)

        # Apply date range filters
        if filters.start_date is not None:
            stmt = stmt.where(ResearchItem.created_at >= filters.start_date)
        if filters.end_date is not None:
            stmt = stmt.where(ResearchItem.created_at <= filters.end_date)

        # Apply compliance status filter
        if filters.compliance_status is not None:
            stmt = stmt.where(
                ResearchItem.compliance_status == filters.compliance_status.value
            )

        # Apply sorting
        if filters.sort_by == "date":
            stmt = stmt.order_by(ResearchItem.created_at.desc())
        elif filters.sort_by == "relevance":
            # Relevance sorting is handled by search() method with ts_rank
            # Default to score for regular queries
            stmt = stmt.order_by(
                ResearchItem.score.desc(),
                ResearchItem.created_at.desc(),
            )
        else:
            # Default: score DESC, then created_at DESC
            stmt = stmt.order_by(
                ResearchItem.score.desc(),
                ResearchItem.created_at.desc(),
            )

        # Apply pagination
        stmt = stmt.limit(filters.limit).offset(filters.offset)

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_score(self, item_id: UUID, score: float) -> None:
        """Update the score of a research item.

        Args:
            item_id: UUID of the item to update
            score: New score value (0-10)

        Raises:
            ItemNotFoundError: If item does not exist
            DatabaseError: If database operation fails
        """
        # Check item exists
        existing = await self.get_by_id(item_id)
        if existing is None:
            raise ItemNotFoundError(item_id)

        try:
            stmt = (
                update(ResearchItem)
                .where(ResearchItem.id == item_id)
                .values(score=score)
            )
            await self._session.execute(stmt)
            await self._session.commit()

        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to update score for item %s: %s", item_id, e)
            raise DatabaseError("update_score", e) from e

    async def update_compliance_status(
        self,
        item_id: UUID,
        status: ComplianceStatus,
    ) -> None:
        """Update the compliance status of a research item.

        Args:
            item_id: UUID of the item to update
            status: New compliance status

        Raises:
            ItemNotFoundError: If item does not exist
            DatabaseError: If database operation fails
        """
        # Check item exists
        existing = await self.get_by_id(item_id)
        if existing is None:
            raise ItemNotFoundError(item_id)

        try:
            stmt = (
                update(ResearchItem)
                .where(ResearchItem.id == item_id)
                .values(compliance_status=status.value)
            )
            await self._session.execute(stmt)
            await self._session.commit()

        except Exception as e:
            await self._session.rollback()
            logger.error(
                "Failed to update compliance status for item %s: %s", item_id, e
            )
            raise DatabaseError("update_compliance_status", e) from e

    async def count(self, filters: Optional[ResearchQueryFilters] = None) -> int:
        """Count research items matching optional filters.

        Args:
            filters: Optional query filters (same as query method)

        Returns:
            Total count of matching items
        """
        stmt = select(func.count()).select_from(ResearchItem)

        if filters:
            # Apply same filters as query method
            if filters.source is not None:
                stmt = stmt.where(ResearchItem.source == filters.source.value)
            if filters.tags:
                stmt = stmt.where(ResearchItem.tags.overlap(filters.tags))
            if filters.min_score is not None:
                stmt = stmt.where(ResearchItem.score >= filters.min_score)
            if filters.max_score is not None:
                stmt = stmt.where(ResearchItem.score <= filters.max_score)
            if filters.start_date is not None:
                stmt = stmt.where(ResearchItem.created_at >= filters.start_date)
            if filters.end_date is not None:
                stmt = stmt.where(ResearchItem.created_at <= filters.end_date)
            if filters.compliance_status is not None:
                stmt = stmt.where(
                    ResearchItem.compliance_status == filters.compliance_status.value
                )

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def bulk_insert(self, items: list[ResearchItemCreate]) -> int:
        """Bulk insert multiple research items.

        More efficient than calling add_item in a loop for large batches.
        Used primarily for seeding test data.

        Args:
            items: List of research items to insert

        Returns:
            Number of items inserted

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            db_items = [
                ResearchItem(
                    id=item.id or uuid4(),
                    source=item.source.value,
                    title=item.title,
                    content=item.content,
                    url=item.url,
                    tags=item.tags or [],
                    source_metadata=item.source_metadata or {},
                    created_at=item.created_at or datetime.now(timezone.utc),
                    score=item.score,
                    compliance_status=item.compliance_status.value,
                )
                for item in items
            ]

            self._session.add_all(db_items)
            await self._session.commit()

            return len(db_items)

        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to bulk insert research items: %s", e)
            raise DatabaseError("bulk_insert", e) from e

    async def search(
        self,
        query: str,
        filters: Optional[ResearchQueryFilters] = None,
    ) -> Sequence[ResearchItem]:
        """Full-text search on title and content fields.

        Uses PostgreSQL tsvector for efficient full-text search.
        Results are ranked by relevance using ts_rank.

        Args:
            query: Search query string (words to search for)
            filters: Optional additional filters to apply

        Returns:
            List of matching ResearchItem objects, ranked by relevance
        """
        if not query or not query.strip():
            # Empty query returns empty results
            return []

        # Build the search query using PostgreSQL full-text search
        # plainto_tsquery converts plain text to tsquery (handles spaces, etc.)
        search_query = func.plainto_tsquery("english", query)

        # Build statement with full-text search
        stmt = (
            select(ResearchItem)
            .where(ResearchItem.search_vector.op("@@")(search_query))
        )

        # Apply additional filters if provided
        if filters:
            if filters.source is not None:
                stmt = stmt.where(ResearchItem.source == filters.source.value)
            if filters.tags:
                stmt = stmt.where(ResearchItem.tags.overlap(filters.tags))
            if filters.min_score is not None:
                stmt = stmt.where(ResearchItem.score >= filters.min_score)
            if filters.max_score is not None:
                stmt = stmt.where(ResearchItem.score <= filters.max_score)
            if filters.start_date is not None:
                stmt = stmt.where(ResearchItem.created_at >= filters.start_date)
            if filters.end_date is not None:
                stmt = stmt.where(ResearchItem.created_at <= filters.end_date)
            if filters.compliance_status is not None:
                stmt = stmt.where(
                    ResearchItem.compliance_status == filters.compliance_status.value
                )

        # Order by relevance (ts_rank) descending
        stmt = stmt.order_by(
            func.ts_rank(ResearchItem.search_vector, search_query).desc(),
            ResearchItem.score.desc(),  # Secondary sort by score
        )

        # Apply pagination from filters or use defaults
        limit = filters.limit if filters else DEFAULT_LIMIT
        offset = filters.offset if filters else 0
        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete(self, item_id: UUID) -> bool:
        """Delete a research item by ID.

        Args:
            item_id: UUID of the item to delete

        Returns:
            True if item was deleted, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            stmt = delete(ResearchItem).where(ResearchItem.id == item_id)
            result = await self._session.execute(stmt)
            await self._session.commit()

            # Check if any rows were affected
            deleted = result.rowcount > 0
            if deleted:
                logger.info("Deleted research item: %s", item_id)
            else:
                logger.debug("Item not found for deletion: %s", item_id)

            return deleted

        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to delete research item %s: %s", item_id, e)
            raise DatabaseError("delete", e) from e

    async def update_item(
        self,
        item_id: UUID,
        updates: ResearchItemUpdate,
    ) -> Optional[ResearchItem]:
        """Update a research item with partial data.

        Only provided (non-None) fields in the update schema will be modified.

        Args:
            item_id: UUID of the item to update
            updates: Partial update data

        Returns:
            Updated ResearchItem if found, None if not found

        Raises:
            DatabaseError: If database operation fails
        """
        # Check item exists
        existing = await self.get_by_id(item_id)
        if existing is None:
            return None

        try:
            # Build update values from non-None fields
            update_data = {}
            if updates.title is not None:
                update_data["title"] = updates.title
            if updates.content is not None:
                update_data["content"] = updates.content
            if updates.url is not None:
                update_data["url"] = updates.url
            if updates.tags is not None:
                update_data["tags"] = updates.tags
            if updates.source_metadata is not None:
                update_data["source_metadata"] = updates.source_metadata
            if updates.score is not None:
                update_data["score"] = updates.score
            if updates.compliance_status is not None:
                update_data["compliance_status"] = updates.compliance_status.value

            if not update_data:
                # No fields to update
                return existing

            stmt = (
                update(ResearchItem)
                .where(ResearchItem.id == item_id)
                .values(**update_data)
            )
            await self._session.execute(stmt)
            await self._session.commit()

            # Refresh and return updated item
            await self._session.refresh(existing)
            logger.info("Updated research item: %s", item_id)
            return existing

        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to update research item %s: %s", item_id, e)
            raise DatabaseError("update_item", e) from e
