"""Tests for Shopify sales attribution database models.

Story 7-3, Task 1.4: Model unit tests.

Tests:
- ShopifyOrderRecord model creation and field mapping
- OrderAttributionRecord model creation and field mapping
- Enum validation for attribution_type
- Table constraints (unique, indexes, FK)
- Relationship between order and attributions
"""

from datetime import datetime, UTC
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect

from core.analytics.attribution_models import (
    AttributionType,
    OrderAttributionRecord,
    ShopifyOrderRecord,
    MAX_SHOPIFY_ORDER_GID_LENGTH,
    MAX_CURRENCY_LENGTH,
    MAX_CUSTOMER_EMAIL_LENGTH,
    MAX_ATTRIBUTION_TYPE_LENGTH,
    MAX_UTM_SOURCE_LENGTH,
    MAX_UTM_MEDIUM_LENGTH,
    MAX_UTM_CAMPAIGN_LENGTH,
    MAX_UTM_CONTENT_LENGTH,
    MAX_POST_ID_LENGTH,
)


class TestAttributionType:
    """Tests for AttributionType enum."""

    def test_last_touch_value(self) -> None:
        assert AttributionType.LAST_TOUCH == "last_touch"

    def test_multi_touch_value(self) -> None:
        assert AttributionType.MULTI_TOUCH == "multi_touch"

    def test_enum_members(self) -> None:
        assert len(AttributionType) == 2

    def test_from_string(self) -> None:
        assert AttributionType("last_touch") == AttributionType.LAST_TOUCH
        assert AttributionType("multi_touch") == AttributionType.MULTI_TOUCH

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            AttributionType("invalid")


class TestShopifyOrderRecord:
    """Tests for ShopifyOrderRecord SQLAlchemy model."""

    def test_tablename(self) -> None:
        assert ShopifyOrderRecord.__tablename__ == "shopify_orders"

    def test_create_instance(self) -> None:
        order = ShopifyOrderRecord(
            shopify_order_gid="gid://shopify/Order/12345",
            order_name="#1001",
            total_price=Decimal("299.00"),
            currency="NOK",
            customer_email="test@example.com",
            line_items_json=[
                {"title": "Lions Mane Extract", "quantity": 1, "price": "299.00"}
            ],
            created_at=datetime.now(UTC),
            processed_at=datetime.now(UTC),
            customer_journey_ready=True,
        )
        assert order.shopify_order_gid == "gid://shopify/Order/12345"
        assert order.order_name == "#1001"
        assert order.total_price == Decimal("299.00")
        assert order.currency == "NOK"
        assert order.customer_email == "test@example.com"
        assert len(order.line_items_json) == 1
        assert order.customer_journey_ready is True

    def test_nullable_fields(self) -> None:
        order = ShopifyOrderRecord(
            shopify_order_gid="gid://shopify/Order/99999",
            order_name="#1002",
            total_price=Decimal("0.00"),
            currency="NOK",
            line_items_json=[],
            created_at=datetime.now(UTC),
            processed_at=datetime.now(UTC),
            customer_journey_ready=False,
        )
        # customer_email is nullable
        assert order.customer_email is None

    def test_column_types(self) -> None:
        mapper = inspect(ShopifyOrderRecord)
        columns = {c.key: c for c in mapper.columns}
        assert "id" in columns
        assert "shopify_order_gid" in columns
        assert "order_name" in columns
        assert "total_price" in columns
        assert "currency" in columns
        assert "customer_email" in columns
        assert "line_items_json" in columns
        assert "created_at" in columns
        assert "processed_at" in columns
        assert "customer_journey_ready" in columns

    def test_unique_constraint_on_shopify_order_gid(self) -> None:
        table = ShopifyOrderRecord.__table__
        unique_constraints = [
            c for c in table.constraints
            if hasattr(c, "columns") and "shopify_order_gid" in [col.name for col in c.columns]
        ]
        # Check via indexes for unique
        unique_indexes = [
            idx for idx in table.indexes
            if idx.unique and "shopify_order_gid" in [col.name for col in idx.columns]
        ]
        assert len(unique_constraints) > 0 or len(unique_indexes) > 0

    def test_indexes_exist(self) -> None:
        table = ShopifyOrderRecord.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "idx_shopify_orders_gid" in index_names
        assert "idx_shopify_orders_created_at" in index_names

    def test_repr(self) -> None:
        order = ShopifyOrderRecord(
            shopify_order_gid="gid://shopify/Order/12345",
            order_name="#1001",
            total_price=Decimal("299.00"),
            currency="NOK",
            line_items_json=[],
            created_at=datetime.now(UTC),
            processed_at=datetime.now(UTC),
            customer_journey_ready=True,
        )
        repr_str = repr(order)
        assert "ShopifyOrderRecord" in repr_str
        assert "gid://shopify/Order/12345" in repr_str


class TestOrderAttributionRecord:
    """Tests for OrderAttributionRecord SQLAlchemy model."""

    def test_tablename(self) -> None:
        assert OrderAttributionRecord.__tablename__ == "order_attributions"

    def test_create_instance(self) -> None:
        order_id = uuid4()
        attr = OrderAttributionRecord(
            shopify_order_id=order_id,
            post_id="post_abc123",
            attribution_type=AttributionType.LAST_TOUCH.value,
            revenue_attributed=Decimal("299.00"),
            touchpoint_index=0,
            visit_occurred_at=datetime.now(UTC),
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed_post",
            utm_content="post_abc123",
        )
        assert attr.shopify_order_id == order_id
        assert attr.post_id == "post_abc123"
        assert attr.attribution_type == AttributionType.LAST_TOUCH.value
        assert attr.revenue_attributed == Decimal("299.00")
        assert attr.touchpoint_index == 0

    def test_multi_touch_type(self) -> None:
        attr = OrderAttributionRecord(
            shopify_order_id=uuid4(),
            post_id="post_xyz789",
            attribution_type=AttributionType.MULTI_TOUCH.value,
            revenue_attributed=Decimal("0.00"),
            touchpoint_index=2,
            visit_occurred_at=datetime.now(UTC),
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed_post",
            utm_content="post_xyz789",
        )
        assert attr.attribution_type == "multi_touch"
        assert attr.revenue_attributed == Decimal("0.00")

    def test_nullable_fields(self) -> None:
        attr = OrderAttributionRecord(
            shopify_order_id=uuid4(),
            post_id="post_abc",
            attribution_type=AttributionType.LAST_TOUCH.value,
            revenue_attributed=Decimal("100.00"),
            touchpoint_index=0,
        )
        # Nullable UTM fields and visit_occurred_at
        assert attr.visit_occurred_at is None
        assert attr.utm_source is None
        assert attr.utm_medium is None
        assert attr.utm_campaign is None
        assert attr.utm_content is None

    def test_column_types(self) -> None:
        mapper = inspect(OrderAttributionRecord)
        columns = {c.key: c for c in mapper.columns}
        assert "id" in columns
        assert "shopify_order_id" in columns
        assert "post_id" in columns
        assert "attribution_type" in columns
        assert "revenue_attributed" in columns
        assert "touchpoint_index" in columns
        assert "visit_occurred_at" in columns
        assert "utm_source" in columns
        assert "utm_medium" in columns
        assert "utm_campaign" in columns
        assert "utm_content" in columns

    def test_foreign_key_to_shopify_orders(self) -> None:
        mapper = inspect(OrderAttributionRecord)
        columns = {c.key: c for c in mapper.columns}
        fk_cols = columns["shopify_order_id"].foreign_keys
        assert len(fk_cols) == 1
        fk = list(fk_cols)[0]
        assert fk.target_fullname == "shopify_orders.id"

    def test_indexes_exist(self) -> None:
        table = OrderAttributionRecord.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "idx_order_attributions_order_id" in index_names
        assert "idx_order_attributions_post_id" in index_names

    def test_repr(self) -> None:
        order_id = uuid4()
        attr = OrderAttributionRecord(
            shopify_order_id=order_id,
            post_id="post_abc123",
            attribution_type="last_touch",
            revenue_attributed=Decimal("100.00"),
            touchpoint_index=0,
        )
        repr_str = repr(attr)
        assert "OrderAttributionRecord" in repr_str
        assert "post_abc123" in repr_str


class TestColumnLengthConstants:
    """Tests for column length constants."""

    def test_constants_are_positive(self) -> None:
        assert MAX_SHOPIFY_ORDER_GID_LENGTH > 0
        assert MAX_CURRENCY_LENGTH > 0
        assert MAX_CUSTOMER_EMAIL_LENGTH > 0
        assert MAX_ATTRIBUTION_TYPE_LENGTH > 0
        assert MAX_UTM_SOURCE_LENGTH > 0
        assert MAX_UTM_MEDIUM_LENGTH > 0
        assert MAX_UTM_CAMPAIGN_LENGTH > 0
        assert MAX_UTM_CONTENT_LENGTH > 0
        assert MAX_POST_ID_LENGTH > 0

    def test_shopify_gid_accommodates_format(self) -> None:
        # gid://shopify/Order/123456789012 = ~40 chars
        assert MAX_SHOPIFY_ORDER_GID_LENGTH >= 60
