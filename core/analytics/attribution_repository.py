"""Attribution repository for Shopify sales attribution.

Epic 7, Story 7-3: Shopify Sales Attribution.
Task 3: AttributionRepository with async SQLAlchemy.

Provides data access for ShopifyOrderRecord and OrderAttributionRecord
with batch queries (IN clauses), SQL aggregations, and idempotent upserts.
"""

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.analytics.attribution_models import (
    OrderAttributionRecord,
    ShopifyOrderRecord,
)

logger = logging.getLogger(__name__)


class AttributionRepository:
    """Repository for Shopify order attributions.

    Story 7-3, Task 3.1: Async SQLAlchemy CRUD operations.

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

    async def save_order(self, order: ShopifyOrderRecord) -> ShopifyOrderRecord:
        """Upsert order by shopify_order_gid (idempotent).

        Task 3.2: If order with same GID exists, update it.
        Otherwise insert new record.

        Args:
            order: ShopifyOrderRecord to save

        Returns:
            The saved/updated record
        """
        result = await self._session.execute(
            select(ShopifyOrderRecord).where(
                ShopifyOrderRecord.shopify_order_gid == order.shopify_order_gid
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing order
            existing.order_name = order.order_name
            existing.total_price = order.total_price
            existing.currency = order.currency
            existing.customer_email = order.customer_email
            existing.line_items_json = order.line_items_json
            existing.processed_at = order.processed_at
            existing.customer_journey_ready = order.customer_journey_ready
            await self._session.flush()
            logger.info("Updated order: %s", order.shopify_order_gid)
            return existing

        self._session.add(order)
        await self._session.flush()
        logger.info("Saved new order: %s", order.shopify_order_gid)
        return order

    async def save_attributions(
        self, attributions: list[OrderAttributionRecord]
    ) -> None:
        """Batch insert attributions for an order.

        Task 3.3: Saves all touchpoints in one flush.

        Args:
            attributions: List of attribution records to persist
        """
        if not attributions:
            return

        self._session.add_all(attributions)
        await self._session.flush()
        logger.info("Saved %d attributions", len(attributions))

    async def get_attributions_by_post_id(
        self, post_id: str
    ) -> Sequence[OrderAttributionRecord]:
        """Get all attributions for a single post.

        Task 3.4: Single post lookup.

        Args:
            post_id: Instagram post ID

        Returns:
            List of OrderAttributionRecord
        """
        result = await self._session.execute(
            select(OrderAttributionRecord)
            .where(OrderAttributionRecord.post_id == post_id)
            .order_by(OrderAttributionRecord.created_at)
        )
        return result.scalars().all()

    async def get_attributions_by_post_ids(
        self, post_ids: list[str]
    ) -> dict[str, list[OrderAttributionRecord]]:
        """Batch query attributions for multiple posts.

        Task 3.5: Uses IN clause to prevent N+1.

        Args:
            post_ids: List of post IDs

        Returns:
            Dict mapping post_id to list of attributions
        """
        if not post_ids:
            return {}

        result = await self._session.execute(
            select(OrderAttributionRecord)
            .where(OrderAttributionRecord.post_id.in_(post_ids))
            .order_by(OrderAttributionRecord.created_at)
        )
        all_attrs = result.scalars().all()

        grouped: dict[str, list[OrderAttributionRecord]] = defaultdict(list)
        for attr in all_attrs:
            grouped[attr.post_id].append(attr)

        # Ensure all requested IDs are in result
        for pid in post_ids:
            if pid not in grouped:
                grouped[pid] = []

        return dict(grouped)

    async def get_revenue_summary(self, post_id: str) -> dict:
        """Get revenue aggregation for a single post.

        Task 3.6: SQL aggregation — total_revenue, order_count, avg_order_value.
        Only counts last_touch attributions for revenue (multi_touch revenue=0).

        Args:
            post_id: Instagram post ID

        Returns:
            Dict with total_revenue, order_count, avg_order_value
        """
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(OrderAttributionRecord.revenue_attributed), 0).label("total_revenue"),
                func.count(OrderAttributionRecord.id).label("order_count"),
                func.coalesce(func.avg(OrderAttributionRecord.revenue_attributed), 0).label("avg_order_value"),
            )
            .where(OrderAttributionRecord.post_id == post_id)
            .where(OrderAttributionRecord.attribution_type == "last_touch")
        )
        row = result.one_or_none()

        if not row:
            return {
                "total_revenue": Decimal("0"),
                "order_count": 0,
                "avg_order_value": Decimal("0"),
            }

        return {
            "total_revenue": Decimal(str(row.total_revenue)) if row.total_revenue else Decimal("0"),
            "order_count": row.order_count or 0,
            "avg_order_value": Decimal(str(row.avg_order_value)) if row.avg_order_value else Decimal("0"),
        }

    async def get_revenue_by_post_ids(self, post_ids: list[str]) -> dict[str, dict]:
        """Batch revenue summary for multiple posts.

        Task 3.7: Single query with GROUP BY post_id.

        Args:
            post_ids: List of post IDs

        Returns:
            Dict mapping post_id to revenue summary
        """
        if not post_ids:
            return {}

        result = await self._session.execute(
            select(
                OrderAttributionRecord.post_id,
                func.coalesce(func.sum(OrderAttributionRecord.revenue_attributed), 0).label("total_revenue"),
                func.count(OrderAttributionRecord.id).label("order_count"),
                func.coalesce(func.avg(OrderAttributionRecord.revenue_attributed), 0).label("avg_order_value"),
            )
            .where(OrderAttributionRecord.post_id.in_(post_ids))
            .where(OrderAttributionRecord.attribution_type == "last_touch")
            .group_by(OrderAttributionRecord.post_id)
        )
        rows = result.all()

        grouped: dict[str, dict] = {}
        for row in rows:
            grouped[row.post_id] = {
                "total_revenue": Decimal(str(row.total_revenue)) if row.total_revenue else Decimal("0"),
                "order_count": row.order_count or 0,
                "avg_order_value": Decimal(str(row.avg_order_value)) if row.avg_order_value else Decimal("0"),
            }

        # Fill missing posts with zeros
        for pid in post_ids:
            if pid not in grouped:
                grouped[pid] = {
                    "total_revenue": Decimal("0"),
                    "order_count": 0,
                    "avg_order_value": Decimal("0"),
                }

        return grouped

    async def get_top_products(
        self, post_id: str, limit: int = 10
    ) -> list[dict]:
        """Get top products by revenue from attributed orders.

        Task 3.8: Aggregates product data from line_items_json
        across all orders attributed to the post.

        Args:
            post_id: Instagram post ID
            limit: Max products to return

        Returns:
            List of dicts: {product_handle, title, total_quantity, total_revenue}
            sorted by total_revenue descending
        """
        # Get order IDs attributed to this post (last_touch only)
        attr_result = await self._session.execute(
            select(OrderAttributionRecord.shopify_order_id)
            .where(OrderAttributionRecord.post_id == post_id)
            .where(OrderAttributionRecord.attribution_type == "last_touch")
        )
        order_ids = attr_result.scalars().all()

        if not order_ids:
            return []

        # Get orders with line items
        orders_result = await self._session.execute(
            select(ShopifyOrderRecord)
            .where(ShopifyOrderRecord.id.in_(order_ids))
        )
        orders = orders_result.scalars().all()

        # Aggregate products from line_items_json
        product_map: dict[str, dict] = {}
        for order in orders:
            for item in (order.line_items_json or []):
                handle = item.get("product_handle", "unknown")
                if handle not in product_map:
                    product_map[handle] = {
                        "product_handle": handle,
                        "title": item.get("title", ""),
                        "total_quantity": 0,
                        "total_revenue": Decimal("0"),
                    }
                qty = item.get("quantity", 0)
                price = Decimal(str(item.get("price", "0")))
                product_map[handle]["total_quantity"] += qty
                product_map[handle]["total_revenue"] += price * qty

        # Sort by revenue descending
        sorted_products = sorted(
            product_map.values(),
            key=lambda p: p["total_revenue"],
            reverse=True,
        )

        return sorted_products[:limit]

    async def get_order_by_gid(
        self, shopify_order_gid: str
    ) -> ShopifyOrderRecord | None:
        """Look up an order by Shopify global ID.

        Args:
            shopify_order_gid: Shopify order GID

        Returns:
            ShopifyOrderRecord or None
        """
        result = await self._session.execute(
            select(ShopifyOrderRecord).where(
                ShopifyOrderRecord.shopify_order_gid == shopify_order_gid
            )
        )
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()


__all__ = [
    "AttributionRepository",
]
