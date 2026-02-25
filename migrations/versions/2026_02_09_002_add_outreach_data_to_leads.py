"""Add outreach_data fields to leads table.

Revision ID: 2026_02_09_002
Revises: 2026_02_09_001
Create Date: 2026-02-09

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "2026_02_09_002"
down_revision: Union[str, None] = "2026_02_09_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add outreach_data and outreach_generated_at columns to leads table."""

    # Add outreach_data JSONB column
    op.add_column(
        "leads",
        sa.Column(
            "outreach_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Add outreach_generated_at timestamp column
    op.add_column(
        "leads",
        sa.Column(
            "outreach_generated_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove outreach columns from leads table."""
    op.drop_column("leads", "outreach_generated_at")
    op.drop_column("leads", "outreach_data")
