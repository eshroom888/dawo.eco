"""Create research_items table for Research Pool

Revision ID: 2026020601
Revises: None
Create Date: 2026-02-06

Story: 2-1-research-pool-database-storage
AC #1: Research item storage with all required fields
AC #2: Query performance indexes for < 500ms queries on 10k items
AC #3: Full-text search support via tsvector
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026020601"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create research_items table with indexes and full-text search trigger."""

    # Create research_items table
    op.create_table(
        "research_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(100)),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(3, 1), server_default="0.0", nullable=False),
        sa.Column(
            "compliance_status",
            sa.String(20),
            server_default="COMPLIANT",
            nullable=False,
        ),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        # Check constraints for data integrity
        sa.CheckConstraint(
            "source IN ('reddit', 'youtube', 'instagram', 'news', 'pubmed')",
            name="valid_source",
        ),
        sa.CheckConstraint(
            "compliance_status IN ('COMPLIANT', 'WARNING', 'REJECTED')",
            name="valid_compliance",
        ),
        sa.CheckConstraint("score >= 0 AND score <= 10", name="valid_score"),
    )

    # Create performance indexes (AC #2: < 500ms for 10k items)
    # B-tree index on source for equality lookups
    op.create_index("idx_research_items_source", "research_items", ["source"])

    # B-tree DESC index on score for top-content queries
    op.create_index(
        "idx_research_items_score",
        "research_items",
        [sa.text("score DESC")],
    )

    # B-tree DESC index on created_at for recent-first queries
    op.create_index(
        "idx_research_items_created_at",
        "research_items",
        [sa.text("created_at DESC")],
    )

    # B-tree index on compliance_status for filtering
    op.create_index(
        "idx_research_items_compliance",
        "research_items",
        ["compliance_status"],
    )

    # GIN index on tags for efficient array containment queries
    op.create_index(
        "idx_research_items_tags",
        "research_items",
        ["tags"],
        postgresql_using="gin",
    )

    # GIN index on search_vector for full-text search (AC #3)
    op.create_index(
        "idx_research_items_search",
        "research_items",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create full-text search trigger function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION research_items_search_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.content, '')
            );
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )

    # Create trigger to auto-update search_vector on insert/update
    op.execute(
        """
        CREATE TRIGGER research_items_search_update
            BEFORE INSERT OR UPDATE ON research_items
            FOR EACH ROW EXECUTE FUNCTION research_items_search_trigger();
        """
    )


def downgrade() -> None:
    """Drop research_items table and related objects."""

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS research_items_search_update ON research_items")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS research_items_search_trigger()")

    # Drop indexes (will be dropped with table, but explicit for clarity)
    op.drop_index("idx_research_items_search", table_name="research_items")
    op.drop_index("idx_research_items_tags", table_name="research_items")
    op.drop_index("idx_research_items_compliance", table_name="research_items")
    op.drop_index("idx_research_items_created_at", table_name="research_items")
    op.drop_index("idx_research_items_score", table_name="research_items")
    op.drop_index("idx_research_items_source", table_name="research_items")

    # Drop table
    op.drop_table("research_items")
