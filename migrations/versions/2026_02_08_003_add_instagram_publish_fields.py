"""Add Instagram publishing fields to approval_items.

Story 4-5: Instagram Graph API Auto-Publishing

Adds:
- instagram_post_id: Instagram media ID after successful publish
- instagram_permalink: Instagram post URL
- published_at: Timestamp when post was published
- publish_error: Error message if publish failed
- publish_attempts: Counter for retry tracking

Revision ID: 2026_02_08_003
Revises: 2026_02_08_002
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2026_02_08_003"
down_revision = "2026_02_08_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Instagram publishing columns to approval_items."""

    # Instagram post ID (returned from Graph API after successful publish)
    op.add_column(
        "approval_items",
        sa.Column("instagram_post_id", sa.String(100), nullable=True),
    )

    # Instagram permalink (direct link to the post)
    op.add_column(
        "approval_items",
        sa.Column("instagram_permalink", sa.String(500), nullable=True),
    )

    # Timestamp when successfully published
    op.add_column(
        "approval_items",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Error message if publish failed
    op.add_column(
        "approval_items",
        sa.Column("publish_error", sa.Text(), nullable=True),
    )

    # Counter for publish attempts (for retry tracking)
    op.add_column(
        "approval_items",
        sa.Column(
            "publish_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # Index for querying posts by Instagram ID
    op.create_index(
        "ix_approval_items_instagram_post_id",
        "approval_items",
        ["instagram_post_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Instagram publishing columns from approval_items."""

    # Drop index first
    op.drop_index("ix_approval_items_instagram_post_id", "approval_items")

    # Remove columns in reverse order
    op.drop_column("approval_items", "publish_attempts")
    op.drop_column("approval_items", "publish_error")
    op.drop_column("approval_items", "published_at")
    op.drop_column("approval_items", "instagram_permalink")
    op.drop_column("approval_items", "instagram_post_id")
