"""Create regulatory tables for Epic 6.

Revision ID: 2026_02_13_001
Revises: 2026_02_09_002
Create Date: 2026-02-13

Epic 6: CleanMarket & Regulatory Intelligence
Story 6-1: EU Health Claims Register Monitor
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "2026_02_13_001"
down_revision: Union[str, None] = "2026_02_09_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create claim_snapshots, health_claims, and claim_changes tables."""

    # Create claim_snapshots table (must be first — referenced by FKs)
    op.create_table(
        "claim_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevant_claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create health_claims table
    op.create_table(
        "health_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", sa.String(50), nullable=False),
        sa.Column("claim_type", sa.String(200), nullable=True),
        sa.Column("substance", sa.String(500), nullable=False),
        sa.Column("health_relationship", sa.Text(), nullable=True),
        sa.Column("claim_text", sa.Text(), nullable=True),
        sa.Column("conditions_of_use", sa.Text(), nullable=True),
        sa.Column("food_category", sa.String(200), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="on_hold"),
        sa.Column("efsa_opinion", sa.Text(), nullable=True),
        sa.Column("commission_regulation", sa.String(500), nullable=True),
        sa.Column("date_of_entry", sa.DateTime(), nullable=True),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("restrictions", sa.Text(), nullable=True),
        sa.Column("is_relevant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("relevance_category", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["claim_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for health_claims
    op.create_index("idx_health_claims_snapshot_id", "health_claims", ["snapshot_id"])
    op.create_index("idx_health_claims_claim_id", "health_claims", ["claim_id"])
    op.create_index("idx_health_claims_substance", "health_claims", ["substance"])
    op.create_index("idx_health_claims_status", "health_claims", ["status"])

    # Create claim_changes table
    op.create_table(
        "claim_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", sa.String(50), nullable=False),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("field_changed", sa.String(200), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("is_relevant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("severity", sa.String(30), nullable=False, server_default="low"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["claim_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for claim_changes
    op.create_index("idx_claim_changes_snapshot", "claim_changes", ["snapshot_id"])
    op.create_index("idx_claim_changes_relevant", "claim_changes", ["is_relevant", "severity"])


def downgrade() -> None:
    """Drop regulatory tables."""
    op.drop_table("claim_changes")
    op.drop_table("health_claims")
    op.drop_table("claim_snapshots")
