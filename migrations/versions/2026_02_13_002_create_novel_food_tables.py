"""Create novel food tables for Story 6-2.

Revision ID: 2026_02_13_002
Revises: 2026_02_13_001
Create Date: 2026-02-13

Epic 6: CleanMarket & Regulatory Intelligence
Story 6-2: Novel Food Catalogue Monitor
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "2026_02_13_002"
down_revision: Union[str, None] = "2026_02_13_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create novel_food_snapshots, novel_food_entries, and novel_food_changes tables."""

    # Create novel_food_snapshots table (must be first — referenced by FKs)
    op.create_table(
        "novel_food_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("total_entries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevant_entries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("species_queried", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("search_duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create novel_food_entries table
    op.create_table(
        "novel_food_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("species_latin", sa.String(300), nullable=False),
        sa.Column("species_common", sa.String(300), nullable=True),
        sa.Column("entry_name", sa.String(500), nullable=False),
        sa.Column("novel_food_status", sa.String(30), nullable=False, server_default="not_determined"),
        sa.Column("authorization_status", sa.String(30), nullable=True),
        sa.Column("history_of_consumption", sa.Text(), nullable=True),
        sa.Column("member_state_comments", sa.Text(), nullable=True),
        sa.Column("commission_comments", sa.Text(), nullable=True),
        sa.Column("conditions_of_use", sa.Text(), nullable=True),
        sa.Column("regulation_reference", sa.String(500), nullable=True),
        sa.Column("union_list_entry", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("raw_html_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["novel_food_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for novel_food_entries
    op.create_index("idx_novel_food_entries_species", "novel_food_entries", ["species_latin"])
    op.create_index("idx_novel_food_entries_snapshot", "novel_food_entries", ["snapshot_id"])

    # Create novel_food_changes table
    op.create_table(
        "novel_food_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("species_latin", sa.String(300), nullable=False),
        sa.Column("entry_name", sa.String(500), nullable=False),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("field_changed", sa.String(200), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(30), nullable=False, server_default="low"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["novel_food_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for novel_food_changes
    op.create_index("idx_novel_food_changes_snapshot", "novel_food_changes", ["snapshot_id"])
    op.create_index("idx_novel_food_changes_severity", "novel_food_changes", ["severity"])


def downgrade() -> None:
    """Drop novel food tables."""
    op.drop_table("novel_food_changes")
    op.drop_table("novel_food_entries")
    op.drop_table("novel_food_snapshots")
