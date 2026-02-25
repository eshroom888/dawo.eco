"""Create feedback_reports and weight_adjustment_records tables.

Story 7-5: Performance Feedback Loop.
Task 1.3: Alembic migration for FeedbackReport and WeightAdjustmentRecord.

Stores weekly performance analysis reports and weight adjustment
proposals for operator-reviewed quality scoring improvements.

Revision ID: 2026_02_26_001
Revises: 2026_02_25_001
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "2026_02_26_001"
down_revision = "2026_02_25_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create feedback_reports and weight_adjustment_records tables."""
    # feedback_reports table
    op.create_table(
        "feedback_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("min_posts_threshold", sa.Integer(), nullable=False),
        sa.Column("total_posts_analyzed", sa.Integer(), nullable=False),
        sa.Column("content_type_rankings", postgresql.JSONB(), nullable=True),
        sa.Column("time_slot_analysis", postgresql.JSONB(), nullable=True),
        sa.Column("hashtag_rankings", postgresql.JSONB(), nullable=True),
        sa.Column("weight_adjustment_proposal", postgresql.JSONB(), nullable=True),
        sa.Column("source_performance", postgresql.JSONB(), nullable=True),
        sa.Column("recommendations", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("missing_sections", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_feedback_reports_report_date",
        "feedback_reports",
        ["report_date"],
        unique=True,
    )
    op.create_index(
        "idx_feedback_reports_created_at",
        "feedback_reports",
        ["created_at"],
    )

    # weight_adjustment_records table
    op.create_table(
        "weight_adjustment_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("adjustment_type", sa.String(50), nullable=False),
        sa.Column("previous_weights", postgresql.JSONB(), nullable=False),
        sa.Column("new_weights", postgresql.JSONB(), nullable=False),
        sa.Column("correlation_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "applied",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "feedback_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("feedback_reports.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_weight_adj_feedback_report_id",
        "weight_adjustment_records",
        ["feedback_report_id"],
    )
    op.create_index(
        "idx_weight_adj_adjustment_type",
        "weight_adjustment_records",
        ["adjustment_type"],
    )


def downgrade() -> None:
    """Drop weight_adjustment_records and feedback_reports tables."""
    op.drop_index(
        "idx_weight_adj_adjustment_type",
        table_name="weight_adjustment_records",
    )
    op.drop_index(
        "idx_weight_adj_feedback_report_id",
        table_name="weight_adjustment_records",
    )
    op.drop_table("weight_adjustment_records")

    op.drop_index(
        "idx_feedback_reports_created_at",
        table_name="feedback_reports",
    )
    op.drop_index(
        "idx_feedback_reports_report_date",
        table_name="feedback_reports",
    )
    op.drop_table("feedback_reports")
