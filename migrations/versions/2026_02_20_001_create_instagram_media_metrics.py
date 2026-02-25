"""Create instagram_media_metrics table.

Story 7-1: Instagram Engagement Metrics Collection.

Creates table for storing Instagram post engagement metrics
at defined intervals (baseline, 24h, 48h, 7d) with:
- UNIQUE constraint on (media_id, snapshot_label) for idempotent upserts
- Indexes on media_id, collected_at, snapshot_label
- Nullable reel-specific columns (plays, avg_watch_time_ms)

Revision ID: 2026_02_20_001
Revises: 2026_02_16_003
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "2026_02_20_001"
down_revision = "2026_02_16_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create instagram_media_metrics table with indexes and constraints."""
    op.create_table(
        "instagram_media_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("media_id", sa.String(100), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_label", sa.String(20), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("saved", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("total_interactions", sa.Integer(), nullable=False),
        sa.Column("plays", sa.Integer(), nullable=True),
        sa.Column("avg_watch_time_ms", sa.Integer(), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_id", "snapshot_label", name="uq_media_snapshot"),
    )

    # Task 1.3: Required indexes
    op.create_index(
        "idx_media_metrics_media_id",
        "instagram_media_metrics",
        ["media_id"],
    )
    op.create_index(
        "idx_media_metrics_collected_at",
        "instagram_media_metrics",
        ["collected_at"],
    )
    op.create_index(
        "idx_media_metrics_snapshot_label",
        "instagram_media_metrics",
        ["snapshot_label"],
    )


def downgrade() -> None:
    """Drop instagram_media_metrics table and indexes."""
    op.drop_index("idx_media_metrics_snapshot_label", table_name="instagram_media_metrics")
    op.drop_index("idx_media_metrics_collected_at", table_name="instagram_media_metrics")
    op.drop_index("idx_media_metrics_media_id", table_name="instagram_media_metrics")
    op.drop_table("instagram_media_metrics")
