"""Create Mattilsynet regulatory monitor tables.

Revision ID: 2026_02_13_003
Revises: 2026_02_13_002
Create Date: 2026-02-13

Epic 6: CleanMarket & Regulatory Intelligence
Story 6-3: Mattilsynet Regulatory Monitor
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "2026_02_13_003"
down_revision: Union[str, None] = "2026_02_13_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create mattilsynet_snapshots, mattilsynet_updates, and mattilsynet_page_hashes tables."""

    # Create mattilsynet_snapshots table (must be first — referenced by FKs)
    op.create_table(
        "mattilsynet_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("total_updates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevant_updates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feeds_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scan_duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create mattilsynet_updates table
    op.create_table(
        "mattilsynet_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("category", sa.String(200), nullable=True),
        sa.Column("keywords_matched", postgresql.JSONB(), nullable=True),
        sa.Column("relevance_tier", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("severity", sa.String(30), nullable=False, server_default="'low'"),
        sa.Column("is_relevant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("raw_content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["mattilsynet_snapshots.id"], ondelete="CASCADE"),
    )

    # Create indexes for mattilsynet_updates
    op.create_index("idx_mattilsynet_updates_snapshot", "mattilsynet_updates", ["snapshot_id"])
    op.create_index("idx_mattilsynet_updates_relevant", "mattilsynet_updates", ["is_relevant", "severity"])
    op.create_index("idx_mattilsynet_updates_url", "mattilsynet_updates", ["url", "snapshot_id"], unique=True)

    # Create mattilsynet_page_hashes table
    op.create_table(
        "mattilsynet_page_hashes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("page_name", sa.String(200), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("last_checked", sa.DateTime(), nullable=False),
        sa.Column("last_changed", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create unique index on url for page_hashes
    op.create_index("idx_mattilsynet_page_hashes_url", "mattilsynet_page_hashes", ["url"], unique=True)


def downgrade() -> None:
    """Drop all Mattilsynet tables."""
    op.drop_index("idx_mattilsynet_page_hashes_url", table_name="mattilsynet_page_hashes")
    op.drop_table("mattilsynet_page_hashes")
    op.drop_index("idx_mattilsynet_updates_url", table_name="mattilsynet_updates")
    op.drop_index("idx_mattilsynet_updates_relevant", table_name="mattilsynet_updates")
    op.drop_index("idx_mattilsynet_updates_snapshot", table_name="mattilsynet_updates")
    op.drop_table("mattilsynet_updates")
    op.drop_table("mattilsynet_snapshots")
