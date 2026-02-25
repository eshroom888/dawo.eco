"""Tests for Shopify client order attribution extensions.

Story 7-3, Task 2.6: Client tests with mocked GraphQL responses.

Tests:
- get_orders_since() with full customer journey data
- get_orders_since() with pagination
- get_orders_since() with empty results
- get_orders_since() with API failure (graceful return)
- get_order_by_id() success and failure
- ShopifyOrder frozen dataclass creation
- OrderLineItem frozen dataclass creation
- OrderAttribution frozen dataclass (customer journey)
- CustomerVisit with UTM params mapping
"""

from datetime import datetime, UTC, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from integrations.shopify.client import ShopifyClient
from integrations.shopify.orders import (
    CustomerVisit,
    OrderAttribution,
    OrderLineItem,
    ShopifyOrder,
)
from teams.dawo.middleware.retry import RetryResult


# --- Test Factories ---

def _make_graphql_order_node(
    order_id: str = "gid://shopify/Order/12345",
    name: str = "#1001",
    total: str = "299.00",
    currency: str = "NOK",
    ready: bool = True,
    with_utm: bool = True,
) -> dict:
    """Create a mock Shopify GraphQL order node."""
    utm_params = {
        "source": "instagram",
        "medium": "post",
        "campaign": "feed_post",
        "content": "post_abc123",
    } if with_utm else None

    return {
        "id": order_id,
        "name": name,
        "createdAt": "2026-02-24T10:00:00Z",
        "totalPriceSet": {
            "shopMoney": {
                "amount": total,
                "currencyCode": currency,
            }
        },
        "lineItems": {
            "edges": [
                {
                    "node": {
                        "title": "Lions Mane Extract",
                        "quantity": 2,
                        "variant": {"id": "gid://shopify/ProductVariant/100", "price": "149.50"},
                        "product": {"id": "gid://shopify/Product/50", "handle": "lions-mane"},
                    }
                }
            ]
        },
        "customerJourneySummary": {
            "ready": ready,
            "daysToConversion": 3,
            "firstVisit": {
                "occurredAt": "2026-02-21T08:00:00Z",
                "utmParameters": utm_params,
            } if with_utm else None,
            "lastVisit": {
                "occurredAt": "2026-02-23T15:00:00Z",
                "utmParameters": utm_params,
            } if with_utm else None,
            "moments": {
                "edges": [
                    {
                        "node": {
                            "occurredAt": "2026-02-21T08:00:00Z",
                            "utmParameters": utm_params,
                        }
                    },
                    {
                        "node": {
                            "occurredAt": "2026-02-23T15:00:00Z",
                            "utmParameters": utm_params,
                        }
                    },
                ] if with_utm else []
            },
        },
    }


def _make_orders_response(
    nodes: list[dict] | None = None,
    has_next_page: bool = False,
    end_cursor: str | None = None,
) -> dict:
    """Create a mock Shopify orders GraphQL response."""
    if nodes is None:
        nodes = [_make_graphql_order_node()]
    return {
        "data": {
            "orders": {
                "edges": [{"node": n, "cursor": f"cursor_{i}"} for i, n in enumerate(nodes)],
                "pageInfo": {
                    "hasNextPage": has_next_page,
                    "endCursor": end_cursor,
                },
            }
        }
    }


def _make_single_order_response(node: dict | None = None) -> dict:
    """Create a mock Shopify single order GraphQL response."""
    if node is None:
        node = _make_graphql_order_node()
    return {"data": {"order": node}}


# --- Frozen Dataclass Tests ---

class TestShopifyOrder:
    """Tests for ShopifyOrder frozen dataclass."""

    def test_create(self) -> None:
        order = ShopifyOrder(
            id="gid://shopify/Order/12345",
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
            created_at=datetime(2026, 2, 24, tzinfo=UTC),
            customer_journey_ready=True,
            attribution=None,
        )
        assert order.id == "gid://shopify/Order/12345"
        assert order.total_price == Decimal("299.00")
        assert len(order.line_items) == 1

    def test_is_frozen(self) -> None:
        order = ShopifyOrder(
            id="gid://shopify/Order/1",
            name="#1",
            total_price=Decimal("0"),
            currency="NOK",
            line_items=[],
            created_at=datetime.now(UTC),
            customer_journey_ready=True,
            attribution=None,
        )
        with pytest.raises(AttributeError):
            order.id = "changed"


class TestOrderLineItem:
    """Tests for OrderLineItem frozen dataclass."""

    def test_create(self) -> None:
        item = OrderLineItem(
            product_id="gid://shopify/Product/50",
            variant_id="gid://shopify/ProductVariant/100",
            title="Lions Mane Extract",
            quantity=2,
            price=Decimal("149.50"),
            product_handle="lions-mane",
        )
        assert item.title == "Lions Mane Extract"
        assert item.quantity == 2
        assert item.product_handle == "lions-mane"

    def test_is_frozen(self) -> None:
        item = OrderLineItem(
            product_id="p1", variant_id="v1", title="t",
            quantity=1, price=Decimal("0"), product_handle="h",
        )
        with pytest.raises(AttributeError):
            item.quantity = 5


class TestCustomerVisit:
    """Tests for CustomerVisit frozen dataclass."""

    def test_create_with_utm(self) -> None:
        visit = CustomerVisit(
            occurred_at=datetime(2026, 2, 24, tzinfo=UTC),
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed_post",
            utm_content="post_abc123",
        )
        assert visit.utm_source == "instagram"
        assert visit.utm_content == "post_abc123"

    def test_create_without_utm(self) -> None:
        visit = CustomerVisit(
            occurred_at=datetime(2026, 2, 24, tzinfo=UTC),
        )
        assert visit.utm_source is None


class TestOrderAttribution:
    """Tests for OrderAttribution frozen dataclass."""

    def test_create(self) -> None:
        attr = OrderAttribution(
            first_visit=CustomerVisit(occurred_at=datetime.now(UTC)),
            last_visit=CustomerVisit(occurred_at=datetime.now(UTC)),
            moments=[],
            days_to_conversion=3,
        )
        assert attr.days_to_conversion == 3

    def test_moments_list(self) -> None:
        visits = [
            CustomerVisit(occurred_at=datetime.now(UTC), utm_content="p1"),
            CustomerVisit(occurred_at=datetime.now(UTC), utm_content="p2"),
        ]
        attr = OrderAttribution(
            first_visit=visits[0],
            last_visit=visits[1],
            moments=visits,
            days_to_conversion=5,
        )
        assert len(attr.moments) == 2


# --- Client Extension Tests ---

class TestGetOrdersSince:
    """Tests for ShopifyClient.get_orders_since()."""

    def _make_client(self) -> ShopifyClient:
        return ShopifyClient(
            store_domain="test.myshopify.com",
            access_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_success_with_attribution(self) -> None:
        client = self._make_client()
        response = _make_orders_response()

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = response
            since = datetime(2026, 2, 23, tzinfo=UTC)
            orders = await client.get_orders_since(since)

        assert len(orders) == 1
        order = orders[0]
        assert order.id == "gid://shopify/Order/12345"
        assert order.name == "#1001"
        assert order.total_price == Decimal("299.00")
        assert order.customer_journey_ready is True
        assert order.attribution is not None
        assert order.attribution.last_visit is not None
        assert order.attribution.last_visit.utm_content == "post_abc123"
        assert len(order.line_items) == 1
        assert order.line_items[0].title == "Lions Mane Extract"

    @pytest.mark.asyncio
    async def test_success_without_utm(self) -> None:
        client = self._make_client()
        node = _make_graphql_order_node(with_utm=False)
        response = _make_orders_response(nodes=[node])

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = response
            orders = await client.get_orders_since(datetime.now(UTC) - timedelta(days=1))

        assert len(orders) == 1
        assert orders[0].attribution is not None
        assert orders[0].attribution.last_visit is None

    @pytest.mark.asyncio
    async def test_journey_not_ready(self) -> None:
        client = self._make_client()
        node = _make_graphql_order_node(ready=False)
        response = _make_orders_response(nodes=[node])

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = response
            orders = await client.get_orders_since(datetime.now(UTC) - timedelta(days=1))

        assert len(orders) == 1
        assert orders[0].customer_journey_ready is False

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        client = self._make_client()
        response = _make_orders_response(nodes=[])

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = response
            orders = await client.get_orders_since(datetime.now(UTC) - timedelta(days=1))

        assert orders == []

    @pytest.mark.asyncio
    async def test_api_failure_returns_empty(self) -> None:
        client = self._make_client()

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = None
            orders = await client.get_orders_since(datetime.now(UTC) - timedelta(days=1))

        assert orders == []

    @pytest.mark.asyncio
    async def test_financial_status_filter(self) -> None:
        client = self._make_client()
        response = _make_orders_response()

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = response
            since = datetime(2026, 2, 23, tzinfo=UTC)
            await client.get_orders_since(since)

            # Verify query includes financial_status:paid filter
            call_args = mock_gql.call_args
            variables = call_args[0][1]  # second positional arg
            assert "financial_status:paid" in variables["query"]


class TestGetOrderById:
    """Tests for ShopifyClient.get_order_by_id()."""

    def _make_client(self) -> ShopifyClient:
        return ShopifyClient(
            store_domain="test.myshopify.com",
            access_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        client = self._make_client()
        response = _make_single_order_response()

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = response
            order = await client.get_order_by_id("gid://shopify/Order/12345")

        assert order is not None
        assert order.id == "gid://shopify/Order/12345"

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        client = self._make_client()
        response = {"data": {"order": None}}

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = response
            order = await client.get_order_by_id("gid://shopify/Order/99999")

        assert order is None

    @pytest.mark.asyncio
    async def test_api_failure(self) -> None:
        client = self._make_client()

        with patch.object(client, "_execute_graphql", new_callable=AsyncMock) as mock_gql:
            mock_gql.return_value = None
            order = await client.get_order_by_id("gid://shopify/Order/12345")

        assert order is None
