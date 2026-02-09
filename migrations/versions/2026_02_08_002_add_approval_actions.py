"""Add approval actions and edit history tables.

Story 4-2: Approve, Reject, Edit Actions

Adds:
- Rejection tracking columns to approval_items
- Approval tracking columns to approval_items
- Original caption storage for revert
- AI rewrite suggestions storage
- approval_item_edits table for edit history

Revision ID: 2026_02_08_002
Revises: 2026_02_08_001
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2026_02_08_002"
down_revision = "2026_02_08_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add approval action columns and edit history table."""

    # Add rejection tracking columns
    op.add_column(
        "approval_items",
        sa.Column("rejection_reason", sa.String(50), nullable=True),
    )
    op.add_column(
        "approval_items",
        sa.Column("rejection_text", sa.String(500), nullable=True),
    )
    op.add_column(
        "approval_items",
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )

    # Add approval tracking columns
    op.add_column(
        "approval_items",
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "approval_items",
        sa.Column("approved_by", sa.String(100), nullable=True),
    )

    # Add scheduled publish time (confirmed)
    op.add_column(
        "approval_items",
        sa.Column("scheduled_publish_time", sa.DateTime(), nullable=True),
    )

    # Add original caption storage for revert
    op.add_column(
        "approval_items",
        sa.Column("original_caption", sa.Text(), nullable=True),
    )

    # Add AI rewrite suggestions storage
    op.add_column(
        "approval_items",
        sa.Column(
            "rewrite_suggestions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Create edit history table
    op.create_table(
        "approval_item_edits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approval_items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("previous_caption", sa.Text(), nullable=False),
        sa.Column("new_caption", sa.Text(), nullable=False),
        sa.Column(
            "edited_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "editor",
            sa.String(100),
            server_default="operator",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove approval action columns and edit history table."""

    # Drop edit history table
    op.drop_table("approval_item_edits")

    # Remove AI rewrite suggestions storage
    op.drop_column("approval_items", "rewrite_suggestions")

    # Remove original caption storage
    op.drop_column("approval_items", "original_caption")

    # Remove scheduled publish time
    op.drop_column("approval_items", "scheduled_publish_time")

    # Remove approval tracking columns
    op.drop_column("approval_items", "approved_by")
    op.drop_column("approval_items", "approved_at")

    # Remove rejection tracking columns
    op.drop_column("approval_items", "archived_at")
    op.drop_column("approval_items", "rejection_text")
    op.drop_column("approval_items", "rejection_reason")
