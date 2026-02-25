"""Frozen dataclasses for Shopify order attribution data.

Story 7-3, Task 2.3-2.5: API response DTOs (NOT SQLAlchemy models).

These represent the structured data from Shopify GraphQL API responses
for orders with customer journey attribution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class OrderLineItem:
    """A single line item from a Shopify order.

    Task 2.4: Frozen dataclass for line item data.

    Attributes:
        product_id: Shopify product global ID
        variant_id: Shopify variant global ID
        title: Product title
        quantity: Quantity ordered
        price: Variant price
        product_handle: Product URL handle
    """

    product_id: str
    variant_id: str
    title: str
    quantity: int
    price: Decimal
    product_handle: str


@dataclass(frozen=True)
class CustomerVisit:
    """A customer visit with UTM parameters.

    Task 2.5: Represents a visit from CustomerJourneySummary.

    Attributes:
        occurred_at: When the visit occurred
        utm_source: UTM source parameter
        utm_medium: UTM medium parameter
        utm_campaign: UTM campaign parameter
        utm_content: UTM content parameter (contains post_id)
    """

    occurred_at: datetime
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None


@dataclass(frozen=True)
class OrderAttribution:
    """Customer journey attribution data for an order.

    Task 2.5: Structured customer journey from Shopify GraphQL.

    Attributes:
        first_visit: First recorded visit (may be None if no journey data)
        last_visit: Most recent visit before purchase (used for last-touch)
        moments: All recorded customer visits (for multi-touch)
        days_to_conversion: Days between first visit and order
    """

    first_visit: Optional[CustomerVisit] = None
    last_visit: Optional[CustomerVisit] = None
    moments: list[CustomerVisit] = field(default_factory=list)
    days_to_conversion: Optional[int] = None


@dataclass(frozen=True)
class ShopifyOrder:
    """Shopify order with customer journey attribution.

    Task 2.3: Frozen dataclass for order API response.
    NOT the SQLAlchemy model — this is the DTO from Shopify GraphQL.

    Attributes:
        id: Shopify order global ID
        name: Human-readable order name (e.g., "#1001")
        total_price: Total order price
        currency: Currency code (e.g., "NOK")
        line_items: Products purchased
        created_at: When the order was created
        customer_journey_ready: Whether attribution data is final
        attribution: Customer journey data (None if unavailable)
        customer_email: Customer email (optional)
    """

    id: str
    name: str
    total_price: Decimal
    currency: str
    line_items: list[OrderLineItem]
    created_at: datetime
    customer_journey_ready: bool
    attribution: Optional[OrderAttribution] = None
    customer_email: Optional[str] = None


__all__ = [
    "CustomerVisit",
    "OrderAttribution",
    "OrderLineItem",
    "ShopifyOrder",
]
