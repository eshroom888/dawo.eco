"""Create competitor content scanner tables.

Revision ID: 2026_02_15_001
Revises: 2026_02_13_003
Create Date: 2026-02-15

Epic 6: CleanMarket & Regulatory Intelligence
Story 6-5: Competitor Content Scanner
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "2026_02_15_001"
down_revision: Union[str, None] = "2026_02_13_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create competitor_scan_snapshots and competitor_content tables."""

    # Create competitor_scan_snapshots table (must be first — referenced by FKs)
    op.create_table(
        "competitor_scan_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("competitor_name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("scan_started_at", sa.DateTime(), nullable=False),
        sa.Column("scan_completed_at", sa.DateTime(), nullable=True),
        sa.Column("total_items_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_with_health_language", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="'in_progress'"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create competitor_content table
    op.create_table(
        "competitor_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competitor_name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("hashtags", postgresql.JSONB(), nullable=True),
        sa.Column("account_or_domain", sa.String(500), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("has_health_language", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("health_keywords_matched", postgresql.JSONB(), nullable=True),
        sa.Column("extraction_status", sa.String(30), nullable=False, server_default="'no_claims'"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["competitor_scan_snapshots.id"], ondelete="CASCADE"),
    )

    # Create indexes for competitor_content
    op.create_index("idx_competitor_content_snapshot", "competitor_content", ["snapshot_id"])
    op.create_index("idx_competitor_content_extraction", "competitor_content", ["extraction_status"])
    op.create_index("idx_competitor_content_hash", "competitor_content", ["content_hash", "competitor_name"], unique=True)
    op.create_index("idx_competitor_content_source", "competitor_content", ["source_type", "competitor_name"])


def downgrade() -> None:
    """Drop all competitor tables."""
    op.drop_index("idx_competitor_content_source", table_name="competitor_content")
    op.drop_index("idx_competitor_content_hash", table_name="competitor_content")
    op.drop_index("idx_competitor_content_extraction", table_name="competitor_content")
    op.drop_index("idx_competitor_content_snapshot", table_name="competitor_content")
    op.drop_table("competitor_content")
    op.drop_table("competitor_scan_snapshots")
