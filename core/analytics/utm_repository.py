"""UTM tracking repository.

Epic 7, Story 7-2: UTM Click-Through Tracking.
Task 2: UTMRepository with async SQLAlchemy.

Provides data access for ShortLink and LinkClick models with:
- Single-query batch lookups to prevent N+1
- Click stats aggregation (total, unique, by_day, device_breakdown)
- Async session via constructor injection
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from core.analytics.utm_models import LinkClick, ShortLink

logger = logging.getLogger(__name__)


class UTMRepository:
    """Repository for UTM short links and click tracking.

    Story 7-2, Task 2.1: Async SQLAlchemy CRUD operations.

    Accepts AsyncSession via constructor injection.

    Attributes:
        _session: Async SQLAlchemy session
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    async def create_short_link(self, link: ShortLink) -> ShortLink:
        """Persist a new short link.

        Task 2.2: create_short_link(link).

        Args:
            link: ShortLink instance to persist

        Returns:
            The persisted ShortLink
        """
        self._session.add(link)
        await self._session.flush()
        logger.info("Created short link: code=%s, post_id=%s", link.code, link.post_id)
        return link

    async def get_by_code(self, code: str) -> Optional[ShortLink]:
        """Look up a short link by its code.

        Task 2.2: get_by_code(code).

        Args:
            code: Short link code (e.g., "abc123")

        Returns:
            ShortLink or None if not found
        """
        result = await self._session.execute(
            select(ShortLink).where(ShortLink.code == code)
        )
        return result.scalar_one_or_none()

    async def get_by_post_id(self, post_id: str) -> Sequence[ShortLink]:
        """Get all short links for a post.

        Task 2.2: get_by_post_id(post_id).

        Args:
            post_id: Instagram post ID

        Returns:
            List of ShortLinks for the post
        """
        result = await self._session.execute(
            select(ShortLink)
            .where(ShortLink.post_id == post_id)
            .order_by(ShortLink.created_at)
        )
        return result.scalars().all()

    async def record_click(self, click: LinkClick) -> None:
        """Record a click event.

        Task 2.2: record_click(click).

        Args:
            click: LinkClick instance to persist
        """
        self._session.add(click)
        await self._session.flush()
        logger.debug(
            "Recorded click: link_id=%s, ip_hash=%s...",
            click.short_link_id,
            click.ip_hash[:8],
        )

    async def get_click_stats(self, short_link_id: UUID) -> dict:
        """Get aggregated click statistics for a short link.

        Task 2.3: Returns total_clicks, unique_clicks (COUNT DISTINCT ip_hash),
        clicks_by_day (GROUP BY DATE), device_breakdown (GROUP BY device_type).

        Args:
            short_link_id: UUID of the short link

        Returns:
            Dict with total_clicks, unique_clicks, clicks_by_day, device_breakdown
        """
        # Total clicks
        total_result = await self._session.execute(
            select(func.count(LinkClick.id))
            .where(LinkClick.short_link_id == short_link_id)
        )
        total_clicks = total_result.scalar_one()

        # Unique clicks by IP hash
        unique_result = await self._session.execute(
            select(func.count(func.distinct(LinkClick.ip_hash)))
            .where(LinkClick.short_link_id == short_link_id)
        )
        unique_clicks = unique_result.scalar_one()

        # Clicks by day
        by_day_result = await self._session.execute(
            select(
                cast(LinkClick.clicked_at, Date).label("day"),
                func.count(LinkClick.id).label("count"),
            )
            .where(LinkClick.short_link_id == short_link_id)
            .group_by(cast(LinkClick.clicked_at, Date))
            .order_by(cast(LinkClick.clicked_at, Date))
        )
        clicks_by_day = [
            {"day": row.day, "count": row.count}
            for row in by_day_result.mappings().all()
        ]

        # Device breakdown
        device_result = await self._session.execute(
            select(
                LinkClick.device_type,
                func.count(LinkClick.id).label("count"),
            )
            .where(LinkClick.short_link_id == short_link_id)
            .group_by(LinkClick.device_type)
        )
        device_breakdown = [
            {"device_type": row.device_type, "count": row.count}
            for row in device_result.mappings().all()
        ]

        return {
            "total_clicks": total_clicks,
            "unique_clicks": unique_clicks,
            "clicks_by_day": clicks_by_day,
            "device_breakdown": device_breakdown,
        }

    async def get_clicks_by_post(
        self, post_id: str, days_back: int = 30
    ) -> Sequence[LinkClick]:
        """Get click records for all links of a post.

        Task 2.2: get_clicks_by_post(post_id, days_back).

        Args:
            post_id: Instagram post ID
            days_back: Number of days to look back (default 30)

        Returns:
            List of LinkClick records
        """
        cutoff = datetime.now(UTC) - timedelta(days=days_back)

        result = await self._session.execute(
            select(LinkClick)
            .join(ShortLink, LinkClick.short_link_id == ShortLink.id)
            .where(ShortLink.post_id == post_id)
            .where(LinkClick.clicked_at >= cutoff)
            .order_by(LinkClick.clicked_at)
        )
        return result.scalars().all()

    async def get_clicks_by_post_ids(
        self, post_ids: list[str]
    ) -> dict[str, list[LinkClick]]:
        """Batch query clicks for multiple posts.

        Task 2.4: Prevents N+1 by using single queries with IN clauses.

        Args:
            post_ids: List of post IDs

        Returns:
            Dict mapping post_id to list of LinkClick records
        """
        if not post_ids:
            return {}

        # Single query: get all links for all posts
        links_result = await self._session.execute(
            select(ShortLink)
            .where(ShortLink.post_id.in_(post_ids))
        )
        links = links_result.scalars().all()

        if not links:
            return {pid: [] for pid in post_ids}

        # Map link_id -> post_id for reverse lookup
        link_to_post: dict[UUID, str] = {}
        for link in links:
            if link.id is not None and link.post_id is not None:
                link_to_post[link.id] = link.post_id

        link_ids = list(link_to_post.keys())

        # Single query: get all clicks for all links
        clicks_result = await self._session.execute(
            select(LinkClick)
            .where(LinkClick.short_link_id.in_(link_ids))
            .order_by(LinkClick.clicked_at)
        )
        clicks = clicks_result.scalars().all()

        # Group clicks by post_id
        grouped: dict[str, list[LinkClick]] = defaultdict(list)
        for click in clicks:
            post_id = link_to_post.get(click.short_link_id)
            if post_id:
                grouped[post_id].append(click)

        # Ensure all requested post_ids are in the result
        for pid in post_ids:
            if pid not in grouped:
                grouped[pid] = []

        return dict(grouped)

    async def get_aggregate_click_stats(self, days_back: int = 30) -> dict:
        """Get aggregate click statistics across all posts.

        Task 5.4/5.5: Provides totals for average CTR and comparison.

        Args:
            days_back: Number of days to look back

        Returns:
            Dict with total_clicks, unique_posts, avg_clicks_per_post
        """
        cutoff = datetime.now(UTC) - timedelta(days=days_back)

        # Total clicks within window
        total_result = await self._session.execute(
            select(func.count(LinkClick.id))
            .join(ShortLink, LinkClick.short_link_id == ShortLink.id)
            .where(LinkClick.clicked_at >= cutoff)
        )
        total_clicks = total_result.scalar_one()

        # Unique posts with clicks within window
        posts_result = await self._session.execute(
            select(func.count(func.distinct(ShortLink.post_id)))
            .join(LinkClick, ShortLink.id == LinkClick.short_link_id)
            .where(LinkClick.clicked_at >= cutoff)
        )
        unique_posts = posts_result.scalar_one()

        avg_clicks = total_clicks / unique_posts if unique_posts > 0 else 0.0

        return {
            "total_clicks": total_clicks,
            "unique_posts": unique_posts,
            "avg_clicks_per_post": avg_clicks,
        }

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()


__all__ = [
    "UTMRepository",
]
