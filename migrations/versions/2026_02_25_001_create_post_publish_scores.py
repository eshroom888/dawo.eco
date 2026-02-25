"""Create post_publish_scores table.

Story 7-4: Post-Publish Quality Scoring.
Task 1.2: Alembic migration for PostPublishScoreRecord model.

Stores computed performance scores and variance tracking
for published posts, supporting quality prediction validation.

Revision ID: 2026_02_25_001
Revises: 2026_02_24_001
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "2026_02_25_001"
down_revision = "2026_02_24_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create post_publish_scores table with indexes."""
    op.create_table(
        "post_publish_scores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("post_id", sa.String(100), nullable=False),
        sa.Column("media_id", sa.String(100), nullable=True),
        sa.Column("pre_publish_score", sa.Numeric(4, 1), nullable=True),
        sa.Column("post_publish_score", sa.Numeric(4, 1), nullable=False),
        sa.Column("variance", sa.Numeric(5, 1), nullable=False),
        sa.Column("component_scores", postgresql.JSONB(), nullable=False),
        sa.Column("metrics_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "flagged_for_review",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "snapshot_label",
            sa.String(20),
            nullable=False,
            server_default="7d",
        ),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes
    op.create_index(
        "idx_post_publish_scores_post_id",
        "post_publish_scores",
        ["post_id"],
        unique=True,
    )
    op.create_index(
        "idx_post_publish_scores_calculated_at",
        "post_publish_scores",
        ["calculated_at"],
    )
    op.create_index(
        "idx_post_publish_scores_flagged",
        "post_publish_scores",
        ["flagged_for_review"],
    )


def downgrade() -> None:
    """Drop post_publish_scores table and indexes."""
    op.drop_index("idx_post_publish_scores_flagged", table_name="post_publish_scores")
    op.drop_index(
        "idx_post_publish_scores_calculated_at", table_name="post_publish_scores"
    )
    op.drop_index(
        "idx_post_publish_scores_post_id", table_name="post_publish_scores"
    )
    op.drop_table("post_publish_scores")
