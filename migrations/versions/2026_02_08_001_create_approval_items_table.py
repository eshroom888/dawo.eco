"""Create approval_items table.

Revision ID: 2026_02_08_001
Revises: 2026_02_06_001
Create Date: 2026-02-08

Story: 4-1-content-approval-queue-ui
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2026_02_08_001"
down_revision = "2026_02_06_001_create_research_items_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create approval_items table with indexes."""
    op.create_table(
        "approval_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("thumbnail_url", sa.String(2048), nullable=False),
        sa.Column("full_caption", sa.Text(), nullable=False),
        sa.Column(
            "hashtags",
            postgresql.ARRAY(sa.String(100)),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "compliance_status",
            sa.String(20),
            nullable=False,
            server_default="COMPLIANT",
        ),
        sa.Column("compliance_details", postgresql.JSONB(), nullable=True),
        sa.Column("quality_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column(
            "would_auto_publish",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("suggested_publish_time", sa.DateTime(), nullable=True),
        sa.Column(
            "source_type",
            sa.String(50),
            nullable=False,
            server_default="instagram_post",
        ),
        sa.Column(
            "source_priority",
            sa.Integer(),
            nullable=False,
            server_default="3",  # EVERGREEN
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for query performance
    op.create_index(
        "idx_approval_items_status",
        "approval_items",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_approval_items_priority",
        "approval_items",
        ["source_priority"],
        unique=False,
    )
    op.create_index(
        "idx_approval_items_queue",
        "approval_items",
        ["status", "source_priority", "suggested_publish_time"],
        unique=False,
    )


def downgrade() -> None:
    """Drop approval_items table and indexes."""
    op.drop_index("idx_approval_items_queue", table_name="approval_items")
    op.drop_index("idx_approval_items_priority", table_name="approval_items")
    op.drop_index("idx_approval_items_status", table_name="approval_items")
    op.drop_table("approval_items")
