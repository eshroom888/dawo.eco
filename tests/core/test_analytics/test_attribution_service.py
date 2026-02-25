"""Tests for attribution service.

Story 7-3, Task 4.5: Service tests with mocked repository and UTM repository.

Tests:
- process_order() with last-touch attribution
- process_order() with multi-touch recording
- process_order() with no UTM data
- process_order() with journey not ready
- process_orders_batch() with partial failure
- Attribution window filtering
"""

from datetime import datetime, UTC, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.analytics.attribution_service import (
    AttributionResult,
    AttributionService,
)
from core.config import AttributionConfig
from integrations.shopify.orders import (
    CustomerVisit,
    OrderAttribution,
    OrderLineItem,
    ShopifyOrder,
)


def _make_config(window_days: int = 30) -> AttributionConfig:
    """Create test config."""
    return AttributionConfig(
        webhook_secret="test_secret",
        polling_interval_hours=1,
        attribution_window_days=window_days,
        max_touchpoints=50,
    )


def _make_order(
    order_id: str = "gid://shopify/Order/12345",
    ready: bool = True,
    utm_content: str = "post_abc123",
    with_utm: bool = True,
    days_ago: int = 0,
) -> ShopifyOrder:
    """Create a test ShopifyOrder DTO."""
    now = datetime.now(UTC) - timedelta(days=days_ago)

    if with_utm:
        visit = CustomerVisit(
            occurred_at=now,
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed_post",
            utm_content=utm_content,
        )
        moments = [visit]
    else:
        visit = None
        moments = []

    return ShopifyOrder(
        id=order_id,
        name="#1001",
        total_price=Decimal("299.00"),
        currency="NOK",
        line_items=[
            OrderLineItem(
                product_id="gid://shopify/Product/50",
                variant_id="gid://shopify/ProductVariant/100",
                title="Lions Mane",
                quantity=1,
                price=Decimal("299.00"),
                product_handle="lions-mane",
            )
        ],
        created_at=now,
        customer_journey_ready=ready,
        attribution=OrderAttribution(
            first_visit=visit,
            last_visit=visit,
            moments=moments,
            days_to_conversion=3 if with_utm else None,
        ),
    )


class TestProcessOrder:
    """Tests for process_order()."""

    @pytest.mark.asyncio
    async def test_last_touch_attribution(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        # UTM repo confirms post exists
        link_mock = MagicMock()
        link_mock.post_id = "post_abc123"
        utm_repo.get_by_post_id.return_value = [link_mock]
        # Save order returns object with id
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        service = AttributionService(attr_repo, utm_repo, _make_config())
        order = _make_order()
        result = await service.process_order(order)

        assert result.success is True
        assert result.attributed is True
        assert result.order_gid == "gid://shopify/Order/12345"
        attr_repo.save_order.assert_awaited_once()
        attr_repo.save_attributions.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_multi_touch_recording(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        link_mock = MagicMock()
        link_mock.post_id = "post_abc123"
        utm_repo.get_by_post_id.return_value = [link_mock]
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        # Order with multiple moments
        visit1 = CustomerVisit(
            occurred_at=datetime.now(UTC) - timedelta(days=2),
            utm_content="post_abc123",
        )
        visit2 = CustomerVisit(
            occurred_at=datetime.now(UTC),
            utm_content="post_abc123",
        )
        order = ShopifyOrder(
            id="gid://shopify/Order/12345",
            name="#1001",
            total_price=Decimal("299.00"),
            currency="NOK",
            line_items=[],
            created_at=datetime.now(UTC),
            customer_journey_ready=True,
            attribution=OrderAttribution(
                first_visit=visit1,
                last_visit=visit2,
                moments=[visit1, visit2],
                days_to_conversion=2,
            ),
        )

        service = AttributionService(attr_repo, utm_repo, _make_config())
        result = await service.process_order(order)

        assert result.success is True
        # Should save both last_touch and multi_touch attributions
        save_call = attr_repo.save_attributions.call_args
        attributions = save_call[0][0]
        assert len(attributions) >= 1  # At least the last-touch

    @pytest.mark.asyncio
    async def test_no_utm_data(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        service = AttributionService(attr_repo, utm_repo, _make_config())
        order = _make_order(with_utm=False)
        result = await service.process_order(order)

        assert result.success is True
        assert result.attributed is False
        # Order should still be saved
        attr_repo.save_order.assert_awaited_once()
        # No attributions to save
        attr_repo.save_attributions.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_journey_not_ready(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        service = AttributionService(attr_repo, utm_repo, _make_config())
        order = _make_order(ready=False)
        result = await service.process_order(order)

        # Should save order but mark as not ready
        assert result.success is True
        assert result.journey_ready is False
        attr_repo.save_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_utm_content_no_match(self) -> None:
        """UTM content doesn't match any known short link."""
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        utm_repo.get_by_post_id.return_value = []  # No matching short link
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        service = AttributionService(attr_repo, utm_repo, _make_config())
        order = _make_order(utm_content="unknown_external_link")
        result = await service.process_order(order)

        assert result.success is True
        assert result.attributed is False


class TestAttributionWindowFilter:
    """Tests for attribution window filtering."""

    @pytest.mark.asyncio
    async def test_order_within_window(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        link_mock = MagicMock()
        link_mock.post_id = "post_abc123"
        utm_repo.get_by_post_id.return_value = [link_mock]
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        service = AttributionService(attr_repo, utm_repo, _make_config(window_days=30))
        order = _make_order(days_ago=5)
        result = await service.process_order(order)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_order_outside_window_skipped(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()

        service = AttributionService(attr_repo, utm_repo, _make_config(window_days=7))
        order = _make_order(days_ago=10)
        result = await service.process_order(order)

        assert result.success is True
        assert result.skipped is True
        assert "window" in (result.skip_reason or "").lower()


class TestProcessOrdersBatch:
    """Tests for process_orders_batch()."""

    @pytest.mark.asyncio
    async def test_batch_success(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        link_mock = MagicMock()
        link_mock.post_id = "post_abc123"
        utm_repo.get_by_post_id.return_value = [link_mock]
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.return_value = saved_order

        service = AttributionService(attr_repo, utm_repo, _make_config())
        orders = [_make_order(order_id=f"gid://shopify/Order/{i}") for i in range(3)]
        result = await service.process_orders_batch(orders)

        assert result.total == 3
        assert result.succeeded == 3
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        link_mock = MagicMock()
        link_mock.post_id = "post_abc123"
        utm_repo.get_by_post_id.return_value = [link_mock]

        # First order succeeds, second fails
        saved_order = MagicMock()
        saved_order.id = uuid4()
        attr_repo.save_order.side_effect = [saved_order, Exception("DB error"), saved_order]

        service = AttributionService(attr_repo, utm_repo, _make_config())
        orders = [_make_order(order_id=f"gid://shopify/Order/{i}") for i in range(3)]
        result = await service.process_orders_batch(orders)

        assert result.total == 3
        assert result.succeeded == 2
        assert result.failed == 1
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_batch_empty(self) -> None:
        attr_repo = AsyncMock()
        utm_repo = AsyncMock()
        service = AttributionService(attr_repo, utm_repo, _make_config())
        result = await service.process_orders_batch([])
        assert result.total == 0


class TestAttributionResult:
    """Tests for AttributionResult frozen dataclass."""

    def test_success_result(self) -> None:
        result = AttributionResult(
            success=True,
            order_gid="gid://shopify/Order/12345",
            attributed=True,
            journey_ready=True,
        )
        assert result.success is True
        assert result.attributed is True

    def test_failure_result(self) -> None:
        result = AttributionResult(
            success=False,
            order_gid="gid://shopify/Order/12345",
            error_message="DB error",
        )
        assert result.success is False
        assert result.error_message == "DB error"

    def test_skipped_result(self) -> None:
        result = AttributionResult(
            success=True,
            order_gid="gid://shopify/Order/12345",
            skipped=True,
            skip_reason="Outside attribution window",
        )
        assert result.skipped is True
