"""SQLAlchemy models for Shopify sales attribution.

Epic 7, Story 7-3: Shopify Sales Attribution.
Task 1.1-1.2: ShopifyOrderRecord and OrderAttributionRecord models.

ShopifyOrderRecord stores ingested Shopify orders.
OrderAttributionRecord links orders to Instagram posts via UTM matching,
supporting both last-touch and multi-touch attribution.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base

# Column length constants
MAX_SHOPIFY_ORDER_GID_LENGTH = 100
MAX_ORDER_NAME_LENGTH = 50
MAX_CURRENCY_LENGTH = 10
MAX_CUSTOMER_EMAIL_LENGTH = 254
MAX_ATTRIBUTION_TYPE_LENGTH = 20
MAX_UTM_SOURCE_LENGTH = 50
MAX_UTM_MEDIUM_LENGTH = 50
MAX_UTM_CAMPAIGN_LENGTH = 100
MAX_UTM_CONTENT_LENGTH = 100
MAX_POST_ID_LENGTH = 100


class AttributionType(str, Enum):
    """Attribution model type.

    Values:
        LAST_TOUCH: Most recent visit before purchase (carries revenue)
        MULTI_TOUCH: Earlier visits that contributed to the journey (revenue=0)
    """

    LAST_TOUCH = "last_touch"
    MULTI_TOUCH = "multi_touch"


class ShopifyOrderRecord(Base):
    """Shopify order stored for attribution analysis.

    Story 7-3, Task 1.1: Stores order data from Shopify GraphQL API.
    Upserted by shopify_order_gid (idempotent).
    """

    __tablename__ = "shopify_orders"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Shopify order global ID (unique — used for idempotent upsert)
    shopify_order_gid: Mapped[str] = mapped_column(
        String(MAX_SHOPIFY_ORDER_GID_LENGTH),
        nullable=False,
    )

    # Human-readable order name (e.g., "#1001")
    order_name: Mapped[str] = mapped_column(
        String(MAX_ORDER_NAME_LENGTH),
        nullable=False,
    )

    # Financial data
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(MAX_CURRENCY_LENGTH),
        nullable=False,
    )

    # Customer info (nullable — not all orders have email)
    customer_email: Mapped[Optional[str]] = mapped_column(
        String(MAX_CUSTOMER_EMAIL_LENGTH),
        nullable=True,
    )

    # Line items as JSON array (product details for top-products analysis)
    line_items_json: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Whether customer journey data was ready at time of ingestion
    customer_journey_ready: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Record timestamp
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship to attributions
    attributions: Mapped[list["OrderAttributionRecord"]] = relationship(
        "OrderAttributionRecord",
        back_populates="order",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_shopify_orders_gid", "shopify_order_gid", unique=True),
        Index("idx_shopify_orders_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ShopifyOrderRecord(shopify_order_gid={self.shopify_order_gid!r}, "
            f"total_price={self.total_price})>"
        )


class OrderAttributionRecord(Base):
    """Links a Shopify order to an Instagram post via UTM matching.

    Story 7-3, Task 1.2: Stores attribution data.
    Each order can have one last_touch attribution (with revenue)
    and multiple multi_touch attributions (revenue=0).
    """

    __tablename__ = "order_attributions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # FK to shopify_orders
    shopify_order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("shopify_orders.id"),
        nullable=False,
    )

    # Post that contributed to the sale
    post_id: Mapped[str] = mapped_column(
        String(MAX_POST_ID_LENGTH),
        nullable=False,
    )

    # Attribution model
    attribution_type: Mapped[str] = mapped_column(
        String(MAX_ATTRIBUTION_TYPE_LENGTH),
        nullable=False,
    )

    # Revenue attributed (only non-zero for last_touch)
    revenue_attributed: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # Position in the customer journey (0 = most recent)
    touchpoint_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # When the visit occurred (from CustomerVisit.occurredAt)
    visit_occurred_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # UTM parameters from the visit
    utm_source: Mapped[Optional[str]] = mapped_column(
        String(MAX_UTM_SOURCE_LENGTH),
        nullable=True,
    )
    utm_medium: Mapped[Optional[str]] = mapped_column(
        String(MAX_UTM_MEDIUM_LENGTH),
        nullable=True,
    )
    utm_campaign: Mapped[Optional[str]] = mapped_column(
        String(MAX_UTM_CAMPAIGN_LENGTH),
        nullable=True,
    )
    utm_content: Mapped[Optional[str]] = mapped_column(
        String(MAX_UTM_CONTENT_LENGTH),
        nullable=True,
    )

    # Record timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship back to order
    order: Mapped["ShopifyOrderRecord"] = relationship(
        "ShopifyOrderRecord",
        back_populates="attributions",
    )

    __table_args__ = (
        Index("idx_order_attributions_order_id", "shopify_order_id"),
        Index("idx_order_attributions_post_id", "post_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<OrderAttributionRecord(post_id={self.post_id!r}, "
            f"attribution_type={self.attribution_type!r}, "
            f"revenue={self.revenue_attributed})>"
        )


__all__ = [
    "AttributionType",
    "OrderAttributionRecord",
    "ShopifyOrderRecord",
    "MAX_ATTRIBUTION_TYPE_LENGTH",
    "MAX_CURRENCY_LENGTH",
    "MAX_CUSTOMER_EMAIL_LENGTH",
    "MAX_ORDER_NAME_LENGTH",
    "MAX_POST_ID_LENGTH",
    "MAX_SHOPIFY_ORDER_GID_LENGTH",
    "MAX_UTM_CAMPAIGN_LENGTH",
    "MAX_UTM_CONTENT_LENGTH",
    "MAX_UTM_MEDIUM_LENGTH",
    "MAX_UTM_SOURCE_LENGTH",
]
