"""Tests for attribution repository.

Story 7-3, Task 3.9: Repository tests.

Tests:
- save_order() — upsert by shopify_order_gid
- save_attributions() — batch insert
- get_attributions_by_post_id() — single post lookup
- get_attributions_by_post_ids() — batch query (IN clause)
- get_revenue_summary() — SQL aggregation
- get_revenue_by_post_ids() — batch revenue summary
- get_top_products() — GROUP BY product from line_items_json
"""

from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.analytics.attribution_models import (
    AttributionType,
    OrderAttributionRecord,
    ShopifyOrderRecord,
)
from core.analytics.attribution_repository import AttributionRepository


def _make_order(
    gid: str = "gid://shopify/Order/12345",
    total: Decimal = Decimal("299.00"),
    line_items: list | None = None,
) -> ShopifyOrderRecord:
    """Create a test ShopifyOrderRecord."""
    return ShopifyOrderRecord(
        id=uuid4(),
        shopify_order_gid=gid,
        order_name="#1001",
        total_price=total,
        currency="NOK",
        customer_email="test@example.com",
        line_items_json=line_items or [
            {"title": "Lions Mane", "product_handle": "lions-mane", "quantity": 1, "price": "299.00"}
        ],
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
        customer_journey_ready=True,
    )


def _make_attribution(
    order_id=None,
    post_id: str = "post_abc",
    attr_type: str = AttributionType.LAST_TOUCH.value,
    revenue: Decimal = Decimal("299.00"),
) -> OrderAttributionRecord:
    """Create a test OrderAttributionRecord."""
    return OrderAttributionRecord(
        shopify_order_id=order_id or uuid4(),
        post_id=post_id,
        attribution_type=attr_type,
        revenue_attributed=revenue,
        touchpoint_index=0,
        visit_occurred_at=datetime.now(UTC),
        utm_source="instagram",
        utm_medium="post",
        utm_campaign="feed_post",
        utm_content=post_id,
    )


class TestAttributionRepositoryInit:
    """Tests for AttributionRepository initialization."""

    def test_accepts_session(self) -> None:
        session = AsyncMock()
        repo = AttributionRepository(session)
        assert repo._session is session


class TestSaveOrder:
    """Tests for save_order() — upsert by shopify_order_gid."""

    @pytest.mark.asyncio
    async def test_save_new_order(self) -> None:
        session = AsyncMock()
        # Simulate no existing order
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        repo = AttributionRepository(session)
        order = _make_order()
        saved = await repo.save_order(order)

        session.add.assert_called_once_with(order)
        session.flush.assert_awaited_once()
        assert saved is order

    @pytest.mark.asyncio
    async def test_upsert_existing_order(self) -> None:
        existing = _make_order(gid="gid://shopify/Order/999")
        existing.id = uuid4()

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        session.execute.return_value = result_mock

        repo = AttributionRepository(session)
        new_data = _make_order(gid="gid://shopify/Order/999", total=Decimal("599.00"))
        saved = await repo.save_order(new_data)

        # Should update existing, not add new
        assert saved.total_price == Decimal("599.00")
        session.flush.assert_awaited()


class TestSaveAttributions:
    """Tests for save_attributions()."""

    @pytest.mark.asyncio
    async def test_batch_insert(self) -> None:
        session = AsyncMock()
        repo = AttributionRepository(session)

        order_id = uuid4()
        attributions = [
            _make_attribution(order_id=order_id, post_id="p1", attr_type="last_touch"),
            _make_attribution(order_id=order_id, post_id="p2", attr_type="multi_touch", revenue=Decimal("0")),
        ]

        await repo.save_attributions(attributions)

        assert session.add_all.called
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        session = AsyncMock()
        repo = AttributionRepository(session)

        await repo.save_attributions([])
        session.add_all.assert_not_called()


class TestGetAttributionsByPostId:
    """Tests for get_attributions_by_post_id()."""

    @pytest.mark.asyncio
    async def test_returns_attributions(self) -> None:
        attr1 = _make_attribution(post_id="post_abc")
        attr2 = _make_attribution(post_id="post_abc", attr_type="multi_touch", revenue=Decimal("0"))

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [attr1, attr2]
        session.execute.return_value = result_mock

        repo = AttributionRepository(session)
        result = await repo.get_attributions_by_post_id("post_abc")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_empty_result(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute.return_value = result_mock

        repo = AttributionRepository(session)
        result = await repo.get_attributions_by_post_id("no_such_post")

        assert result == []


class TestGetAttributionsByPostIds:
    """Tests for get_attributions_by_post_ids() — batch query."""

    @pytest.mark.asyncio
    async def test_batch_returns_grouped(self) -> None:
        attr_p1 = _make_attribution(post_id="p1")
        attr_p2 = _make_attribution(post_id="p2")

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [attr_p1, attr_p2]
        session.execute.return_value = result_mock

        repo = AttributionRepository(session)
        result = await repo.get_attributions_by_post_ids(["p1", "p2", "p3"])

        assert "p1" in result
        assert "p2" in result
        assert "p3" in result
        assert result["p3"] == []

    @pytest.mark.asyncio
    async def test_empty_input(self) -> None:
        session = AsyncMock()
        repo = AttributionRepository(session)
        result = await repo.get_attributions_by_post_ids([])
        assert result == {}


class TestGetRevenueSummary:
    """Tests for get_revenue_summary()."""

    @pytest.mark.asyncio
    async def test_returns_aggregates(self) -> None:
        session = AsyncMock()
        # Mock aggregate query result
        row_mock = MagicMock()
        row_mock.total_revenue = Decimal("598.00")
        row_mock.order_count = 2
        row_mock.avg_order_value = Decimal("299.00")
        result_mock = MagicMock()
        result_mock.one_or_none.return_value = row_mock
        session.execute.return_value = result_mock

        repo = AttributionRepository(session)
        summary = await repo.get_revenue_summary("post_abc")

        assert summary["total_revenue"] == Decimal("598.00")
        assert summary["order_count"] == 2
        assert summary["avg_order_value"] == Decimal("299.00")

    @pytest.mark.asyncio
    async def test_no_data_returns_zeros(self) -> None:
        session = AsyncMock()
        row_mock = MagicMock()
        row_mock.total_revenue = None
        row_mock.order_count = 0
        row_mock.avg_order_value = None
        result_mock = MagicMock()
        result_mock.one_or_none.return_value = row_mock
        session.execute.return_value = result_mock

        repo = AttributionRepository(session)
        summary = await repo.get_revenue_summary("no_data_post")

        assert summary["total_revenue"] == Decimal("0")
        assert summary["order_count"] == 0
        assert summary["avg_order_value"] == Decimal("0")


class TestGetRevenueByPostIds:
    """Tests for get_revenue_by_post_ids()."""

    @pytest.mark.asyncio
    async def test_batch_returns_dict(self) -> None:
        session = AsyncMock()
        # Mock returns rows for p1 and p2
        row1 = MagicMock()
        row1.post_id = "p1"
        row1.total_revenue = Decimal("299.00")
        row1.order_count = 1
        row1.avg_order_value = Decimal("299.00")
        row2 = MagicMock()
        row2.post_id = "p2"
        row2.total_revenue = Decimal("598.00")
        row2.order_count = 2
        row2.avg_order_value = Decimal("299.00")

        result_mock = MagicMock()
        result_mock.all.return_value = [row1, row2]
        session.execute.return_value = result_mock

        repo = AttributionRepository(session)
        result = await repo.get_revenue_by_post_ids(["p1", "p2", "p3"])

        assert result["p1"]["total_revenue"] == Decimal("299.00")
        assert result["p2"]["order_count"] == 2
        assert result["p3"]["total_revenue"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_empty_input(self) -> None:
        session = AsyncMock()
        repo = AttributionRepository(session)
        result = await repo.get_revenue_by_post_ids([])
        assert result == {}


class TestGetTopProducts:
    """Tests for get_top_products()."""

    @pytest.mark.asyncio
    async def test_returns_products(self) -> None:
        # Mock orders with line_items_json
        order1 = _make_order(line_items=[
            {"title": "Lions Mane", "product_handle": "lions-mane", "quantity": 2, "price": "149.50"},
            {"title": "Chaga", "product_handle": "chaga", "quantity": 1, "price": "199.00"},
        ])
        order2 = _make_order(gid="gid://shopify/Order/99999", line_items=[
            {"title": "Lions Mane", "product_handle": "lions-mane", "quantity": 1, "price": "149.50"},
        ])

        session = AsyncMock()
        # First call: get attribution order IDs
        attr_result = MagicMock()
        attr_result.scalars.return_value.all.return_value = [order1.id, order2.id]
        # Second call: get orders
        orders_result = MagicMock()
        orders_result.scalars.return_value.all.return_value = [order1, order2]

        session.execute.side_effect = [attr_result, orders_result]

        repo = AttributionRepository(session)
        products = await repo.get_top_products("post_abc", limit=5)

        assert isinstance(products, list)
        # Should aggregate Lions Mane: 3 units, Chaga: 1 unit
        assert len(products) >= 1


class TestCommit:
    """Tests for commit()."""

    @pytest.mark.asyncio
    async def test_delegates_to_session(self) -> None:
        session = AsyncMock()
        repo = AttributionRepository(session)
        await repo.commit()
        session.commit.assert_awaited_once()
