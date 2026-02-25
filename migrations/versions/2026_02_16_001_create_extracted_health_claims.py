"""Create extracted_health_claims table.

Revision ID: 2026_02_16_001
Revises: 2026_02_15_001
Create Date: 2026-02-16

Epic 6: CleanMarket & Regulatory Intelligence
Story 6-6: Health Claim Extraction Engine
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "2026_02_16_001"
down_revision: Union[str, None] = "2026_02_15_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create extracted_health_claims table with indexes."""

    op.create_table(
        "extracted_health_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("competitor_content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_text", sa.String(1000), nullable=False),
        sa.Column("surrounding_context", sa.String(500), nullable=True),
        sa.Column("claim_category", sa.String(30), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("language_detected", sa.String(10), nullable=False, server_default="'unknown'"),
        sa.Column("extraction_method", sa.String(30), nullable=False),
        sa.Column("eu_article_reference", sa.String(50), nullable=True),
        sa.Column("matched_pattern", sa.String(1000), nullable=True),
        sa.Column("llm_reasoning", sa.String(2000), nullable=True),
        sa.Column("review_status", sa.String(30), nullable=False, server_default="'manual_review'"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["competitor_content_id"],
            ["competitor_content.id"],
            ondelete="CASCADE",
        ),
    )

    # Indexes from Task 2.4
    op.create_index("idx_extracted_claims_content", "extracted_health_claims", ["competitor_content_id"])
    op.create_index("idx_extracted_claims_category", "extracted_health_claims", ["claim_category"])
    op.create_index("idx_extracted_claims_confidence", "extracted_health_claims", ["confidence_score"])
    op.create_index("idx_extracted_claims_review", "extracted_health_claims", ["review_status"])


def downgrade() -> None:
    """Drop extracted_health_claims table."""
    op.drop_index("idx_extracted_claims_review", table_name="extracted_health_claims")
    op.drop_index("idx_extracted_claims_confidence", table_name="extracted_health_claims")
    op.drop_index("idx_extracted_claims_category", table_name="extracted_health_claims")
    op.drop_index("idx_extracted_claims_content", table_name="extracted_health_claims")
    op.drop_table("extracted_health_claims")
