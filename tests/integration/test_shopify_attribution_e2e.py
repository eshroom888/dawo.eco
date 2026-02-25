"""Integration tests for Shopify sales attribution end-to-end.

Story 7-3, Task 8: Integration tests covering the full attribution flow.

Tests:
- 8.1 End-to-end: order → attribution → revenue query
- 8.2 Multi-touch scenario: 3 visits from different posts
- 8.3 No-UTM scenario: order without UTM params
- 8.4 Attribution window: order outside window → skipped
- 8.5 Polling fallback: polls recent orders
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.analytics.attribution_models import AttributionType
from core.analytics.attribution_service import (
    AttributionService,
    BatchAttributionResult,
)
from core.analytics.revenue_analytics import RevenueAnalyticsService
from core.config import AttributionConfig
from integrations.shopify.orders import (
    CustomerVisit,
    OrderAttribution,
    OrderLineItem,
    ShopifyOrder,
)
from ui.backend.routers.webhooks import poll_shopify_orders


def _config(window_days: int = 30) -> AttributionConfig:
    return AttributionConfig(
        webhook_secret="test_secret",
        polling_interval_hours=1,
        attribution_window_days=window_days,
        max_touchpoints=50,
    )


def _make_line_item(handle: str = "lions-mane", price: str = "299.00") -> OrderLineItem:
    return OrderLineItem(
        product_id=f"gid://shopify/Product/{uuid4().hex[:8]}",
        variant_id=f"gid://shopify/ProductVariant/{uuid4().hex[:8]}",
        title=handle.replace("-", " ").title(),
        quantity=1,
        price=Decimal(price),
        product_handle=handle,
    )


class TestEndToEndAttribution:
    """8.1: Order → Attribution → Revenue query."""

    @pytest.mark.asyncio
    async def test_full_flow(self) -> None:
        # Setup mocked repos
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()

        # UTM repo confirms post exists
        link_mock = MagicMock()
        link_mock.post_id = "post_abc123"
        utm_repo.get_by_post_id.return_value = [link_mock]

        # save_order returns mock with ID
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        # Create the order
        now = datetime.now(UTC)
        visit = CustomerVisit(
            occurred_at=now - timedelta(hours=2),
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed_post",
            utm_content="post_abc123",
        )
        order = ShopifyOrder(
            id="gid://shopify/Order/100",
            name="#1001",
            total_price=Decimal("599.00"),
            currency="NOK",
            line_items=[_make_line_item()],
            created_at=now,
            customer_journey_ready=True,
            attribution=OrderAttribution(
                first_visit=visit,
                last_visit=visit,
                moments=[visit],
                days_to_conversion=0,
            ),
        )

        # Process order
        service = AttributionService(attr_repo, utm_repo, _config())
        result = await service.process_order(order)

        assert result.success is True
        assert result.attributed is True
        assert result.order_gid == "gid://shopify/Order/100"

        # Verify attribution was saved
        attr_repo.save_attributions.assert_awaited_once()
        saved_attrs = attr_repo.save_attributions.call_args[0][0]
        assert len(saved_attrs) >= 1
        last_touch = saved_attrs[0]
        assert last_touch.attribution_type == AttributionType.LAST_TOUCH.value
        assert last_touch.revenue_attributed == Decimal("599.00")

        # Now verify revenue query
        attr_repo.get_revenue_summary.return_value = {
            "total_revenue": Decimal("599.00"),
            "order_count": 1,
            "avg_order_value": Decimal("599.00"),
        }
        attr_repo.get_top_products.return_value = [
            {
                "product_handle": "lions-mane",
                "title": "Lions Mane",
                "total_quantity": 1,
                "total_revenue": Decimal("599.00"),
            }
        ]

        revenue_service = RevenueAnalyticsService(attr_repo)
        revenue = await revenue_service.get_post_revenue("post_abc123")
        assert revenue.attributed_revenue == Decimal("599.00")
        assert revenue.order_count == 1
        assert len(revenue.top_products) == 1


class TestMultiTouchScenario:
    """8.2: 3 visits from different posts → last-touch wins, all recorded."""

    @pytest.mark.asyncio
    async def test_three_posts_last_touch_wins(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()

        # All 3 posts exist
        link_mock = MagicMock()
        link_mock.post_id = "post_3"
        utm_repo.get_by_post_id.return_value = [link_mock]

        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        now = datetime.now(UTC)

        # 3 visits from different posts
        visit1 = CustomerVisit(
            occurred_at=now - timedelta(days=5),
            utm_content="post_1",
            utm_source="instagram",
        )
        visit2 = CustomerVisit(
            occurred_at=now - timedelta(days=2),
            utm_content="post_2",
            utm_source="instagram",
        )
        visit3 = CustomerVisit(
            occurred_at=now,
            utm_content="post_3",
            utm_source="instagram",
        )

        order = ShopifyOrder(
            id="gid://shopify/Order/200",
            name="#1002",
            total_price=Decimal("450.00"),
            currency="NOK",
            line_items=[_make_line_item("reishi", "450.00")],
            created_at=now,
            customer_journey_ready=True,
            attribution=OrderAttribution(
                first_visit=visit1,
                last_visit=visit3,  # Most recent
                moments=[visit1, visit2, visit3],
                days_to_conversion=5,
            ),
        )

        service = AttributionService(attr_repo, utm_repo, _config())
        result = await service.process_order(order)

        assert result.success is True
        assert result.attributed is True

        # Verify attributions
        saved_attrs = attr_repo.save_attributions.call_args[0][0]

        # Last-touch should be post_3 with full revenue
        last_touch_attrs = [
            a for a in saved_attrs
            if a.attribution_type == AttributionType.LAST_TOUCH.value
        ]
        assert len(last_touch_attrs) == 1
        assert last_touch_attrs[0].post_id == "post_3"
        assert last_touch_attrs[0].revenue_attributed == Decimal("450.00")

        # Multi-touch should have post_1 and post_2 with revenue=0
        multi_touch_attrs = [
            a for a in saved_attrs
            if a.attribution_type == AttributionType.MULTI_TOUCH.value
        ]
        multi_post_ids = {a.post_id for a in multi_touch_attrs}
        assert "post_1" in multi_post_ids or "post_2" in multi_post_ids
        for mt in multi_touch_attrs:
            assert mt.revenue_attributed == Decimal("0.00")


class TestNoUtmScenario:
    """8.3: Order without UTM params → no attribution (no error)."""

    @pytest.mark.asyncio
    async def test_no_utm_no_error(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()

        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        # Order with no UTM data
        order = ShopifyOrder(
            id="gid://shopify/Order/300",
            name="#1003",
            total_price=Decimal("199.00"),
            currency="NOK",
            line_items=[_make_line_item()],
            created_at=datetime.now(UTC),
            customer_journey_ready=True,
            attribution=OrderAttribution(
                first_visit=None,
                last_visit=None,
                moments=[],
                days_to_conversion=None,
            ),
        )

        service = AttributionService(attr_repo, utm_repo, _config())
        result = await service.process_order(order)

        # Should succeed without attribution (no error)
        assert result.success is True
        assert result.attributed is False
        # Order still saved
        attr_repo.save_order.assert_awaited_once()
        # No attributions saved
        attr_repo.save_attributions.assert_not_awaited()


class TestAttributionWindow:
    """8.4: Order outside window → skipped."""

    @pytest.mark.asyncio
    async def test_old_order_skipped(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()

        # Order from 45 days ago, window is 30 days
        old_date = datetime.now(UTC) - timedelta(days=45)
        visit = CustomerVisit(
            occurred_at=old_date,
            utm_content="post_old",
        )
        order = ShopifyOrder(
            id="gid://shopify/Order/400",
            name="#1004",
            total_price=Decimal("100.00"),
            currency="NOK",
            line_items=[],
            created_at=old_date,
            customer_journey_ready=True,
            attribution=OrderAttribution(
                first_visit=visit,
                last_visit=visit,
                moments=[visit],
                days_to_conversion=0,
            ),
        )

        service = AttributionService(attr_repo, utm_repo, _config(window_days=30))
        result = await service.process_order(order)

        assert result.success is True
        assert result.skipped is True
        assert "window" in (result.skip_reason or "").lower()
        # Should NOT save the order
        attr_repo.save_order.assert_not_awaited()


class TestPollingFallback:
    """8.5: Polling catches missed webhook orders."""

    @pytest.mark.asyncio
    async def test_polling_processes_orders(self) -> None:
        # Mock ShopifyClient returning 2 orders
        mock_client = AsyncMock()
        mock_orders = [
            ShopifyOrder(
                id=f"gid://shopify/Order/{i}",
                name=f"#{2000 + i}",
                total_price=Decimal("100.00"),
                currency="NOK",
                line_items=[],
                created_at=datetime.now(UTC),
                customer_journey_ready=True,
                attribution=OrderAttribution(
                    first_visit=None,
                    last_visit=None,
                    moments=[],
                    days_to_conversion=None,
                ),
            )
            for i in range(2)
        ]
        mock_client.get_orders_since.return_value = mock_orders

        # Mock AttributionService
        mock_service = AsyncMock()
        batch_result = BatchAttributionResult(total=2, succeeded=2, failed=0)
        mock_service.process_orders_batch.return_value = batch_result

        result = await poll_shopify_orders(
            shopify_client=mock_client,
            attribution_service=mock_service,
            hours_back=2,
        )

        assert result["succeeded"] == 2
        assert result["failed"] == 0
        mock_client.get_orders_since.assert_awaited_once()
        mock_service.process_orders_batch.assert_awaited_once_with(mock_orders)

    @pytest.mark.asyncio
    async def test_polling_handles_empty(self) -> None:
        mock_client = AsyncMock()
        mock_client.get_orders_since.return_value = []
        mock_service = AsyncMock()

        result = await poll_shopify_orders(
            shopify_client=mock_client,
            attribution_service=mock_service,
        )

        assert result["succeeded"] == 0
        mock_service.process_orders_batch.assert_not_awaited()
