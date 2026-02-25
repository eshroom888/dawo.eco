"""Create competitor_violations table.

Revision ID: 2026_02_16_002
Revises: 2026_02_16_001
Create Date: 2026-02-16

Epic 6: CleanMarket & Regulatory Intelligence
Story 6-7: EU Violation Detection
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "2026_02_16_002"
down_revision: Union[str, None] = "2026_02_16_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create competitor_violations table with indexes."""

    op.create_table(
        "competitor_violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("extracted_claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("violation_status", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("regulation_article", sa.String(500), nullable=False),
        sa.Column("violation_type", sa.String(100), nullable=False),
        sa.Column("detection_reasoning", sa.String(2000), nullable=False),
        sa.Column("authorized_claims_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nearest_authorized_claim", sa.String(1000), nullable=True),
        sa.Column("competitor_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("evidence_status", sa.String(30), nullable=False, server_default="'pending_collection'"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["extracted_claim_id"],
            ["extracted_health_claims.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("extracted_claim_id", name="uq_violations_claim"),
    )

    # Indexes from Task 2.4
    op.create_index("idx_violations_claim", "competitor_violations", ["extracted_claim_id"], unique=True)
    op.create_index("idx_violations_status", "competitor_violations", ["violation_status"])
    op.create_index("idx_violations_severity", "competitor_violations", ["severity"])
    op.create_index("idx_violations_competitor", "competitor_violations", ["competitor_name"])
    op.create_index("idx_violations_evidence", "competitor_violations", ["evidence_status"])


def downgrade() -> None:
    """Drop competitor_violations table."""
    op.drop_index("idx_violations_evidence", table_name="competitor_violations")
    op.drop_index("idx_violations_competitor", table_name="competitor_violations")
    op.drop_index("idx_violations_severity", table_name="competitor_violations")
    op.drop_index("idx_violations_status", table_name="competitor_violations")
    op.drop_index("idx_violations_claim", table_name="competitor_violations")
    op.drop_table("competitor_violations")
