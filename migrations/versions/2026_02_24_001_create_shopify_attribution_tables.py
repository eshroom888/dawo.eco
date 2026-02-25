"""Create Shopify attribution tables (shopify_orders + order_attributions).

Story 7-3: Shopify Sales Attribution.
Task 1.3: Alembic migration for attribution models.

shopify_orders: Stores ingested Shopify orders for attribution.
order_attributions: Links orders to Instagram posts via UTM matching.

Revision ID: 2026_02_24_001
Revises: 2026_02_23_001
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "2026_02_24_001"
down_revision = "2026_02_23_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create shopify_orders and order_attributions tables with indexes."""
    # Task 1.1: shopify_orders table
    op.create_table(
        "shopify_orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("shopify_order_gid", sa.String(100), nullable=False),
        sa.Column("order_name", sa.String(50), nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("customer_email", sa.String(254), nullable=True),
        sa.Column("line_items_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("customer_journey_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for shopify_orders
    op.create_index(
        "idx_shopify_orders_gid",
        "shopify_orders",
        ["shopify_order_gid"],
        unique=True,
    )
    op.create_index(
        "idx_shopify_orders_created_at",
        "shopify_orders",
        ["created_at"],
    )

    # Task 1.2: order_attributions table
    op.create_table(
        "order_attributions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "shopify_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shopify_orders.id"),
            nullable=False,
        ),
        sa.Column("post_id", sa.String(100), nullable=False),
        sa.Column("attribution_type", sa.String(20), nullable=False),
        sa.Column("revenue_attributed", sa.Numeric(10, 2), nullable=False),
        sa.Column("touchpoint_index", sa.Integer(), nullable=False),
        sa.Column("visit_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("utm_source", sa.String(50), nullable=True),
        sa.Column("utm_medium", sa.String(50), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("utm_content", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for order_attributions
    op.create_index(
        "idx_order_attributions_order_id",
        "order_attributions",
        ["shopify_order_id"],
    )
    op.create_index(
        "idx_order_attributions_post_id",
        "order_attributions",
        ["post_id"],
    )


def downgrade() -> None:
    """Drop order_attributions and shopify_orders tables and indexes."""
    op.drop_index("idx_order_attributions_post_id", table_name="order_attributions")
    op.drop_index("idx_order_attributions_order_id", table_name="order_attributions")
    op.drop_table("order_attributions")
    op.drop_index("idx_shopify_orders_created_at", table_name="shopify_orders")
    op.drop_index("idx_shopify_orders_gid", table_name="shopify_orders")
    op.drop_table("shopify_orders")
