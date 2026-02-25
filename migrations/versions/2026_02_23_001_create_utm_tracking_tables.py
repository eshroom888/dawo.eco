"""Create UTM tracking tables (short_links + link_clicks).

Story 7-2: UTM Click-Through Tracking.
Task 1.1-1.2: Creates short_links and link_clicks tables with indexes.

short_links: Stores short redirect codes with UTM parameters.
link_clicks: Records click events with hashed IPs (GDPR compliant).

Revision ID: 2026_02_23_001
Revises: 2026_02_20_001
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "2026_02_23_001"
down_revision = "2026_02_20_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create short_links and link_clicks tables with indexes."""
    # Task 1.1: short_links table
    op.create_table(
        "short_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(12), nullable=False),
        sa.Column("destination_url", sa.Text(), nullable=False),
        sa.Column("utm_source", sa.String(50), nullable=False),
        sa.Column("utm_medium", sa.String(50), nullable=False),
        sa.Column("utm_campaign", sa.String(100), nullable=False),
        sa.Column("utm_content", sa.String(100), nullable=False),
        sa.Column("post_id", sa.String(100), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="instagram"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Task 1.2: short_links indexes
    op.create_index(
        "idx_short_links_code",
        "short_links",
        ["code"],
        unique=True,
    )
    op.create_index(
        "idx_short_links_post_id",
        "short_links",
        ["post_id"],
    )

    # Task 1.1: link_clicks table
    op.create_table(
        "link_clicks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "short_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("short_links.id"),
            nullable=False,
        ),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=True),
        sa.Column("referer", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Task 1.2: link_clicks indexes
    op.create_index(
        "idx_link_clicks_short_link_id",
        "link_clicks",
        ["short_link_id"],
    )
    op.create_index(
        "idx_link_clicks_clicked_at",
        "link_clicks",
        ["clicked_at"],
    )


def downgrade() -> None:
    """Drop link_clicks and short_links tables and indexes."""
    op.drop_index("idx_link_clicks_clicked_at", table_name="link_clicks")
    op.drop_index("idx_link_clicks_short_link_id", table_name="link_clicks")
    op.drop_table("link_clicks")
    op.drop_index("idx_short_links_post_id", table_name="short_links")
    op.drop_index("idx_short_links_code", table_name="short_links")
    op.drop_table("short_links")
