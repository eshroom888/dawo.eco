"""Create evidence and evidence_audit_log tables.

Story 6-8: Evidence Collection & Screenshots.

Creates tables for immutable evidence storage with:
- evidence table (FK to competitor_violations)
- evidence_audit_log table (FK to evidence)
- Immutability trigger on evidence content fields
- All required indexes

Revision ID: 2026_02_16_003
Revises: 2026_02_16_002
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "2026_02_16_003"
down_revision = "2026_02_16_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create evidence tables and immutability trigger."""
    # Evidence table
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("violation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competitor_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_category", sa.String(50), nullable=False),
        sa.Column("violation_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("regulation_violated", sa.Text(), nullable=True),
        sa.Column("detection_reasoning", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("screenshot_path", sa.Text(), nullable=False),
        sa.Column("screenshot_hash", sa.String(64), nullable=False),
        sa.Column("screenshot_size_bytes", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("evidence_metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["violation_id"], ["competitor_violations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("violation_id"),
    )

    # Evidence indexes
    op.create_index("ix_evidence_captured_at", "evidence", ["captured_at"])
    op.create_index("ix_evidence_competitor_date", "evidence", ["competitor_name", "captured_at"])
    op.create_index("ix_evidence_violation_id", "evidence", ["violation_id"], unique=True)
    op.create_index("ix_evidence_violation_type", "evidence", ["violation_type"])
    op.create_index("ix_evidence_severity", "evidence", ["severity"])

    # Evidence audit log table
    op.create_table(
        "evidence_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("hash_verified", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_evidence_audit_evidence_id", "evidence_audit_log", ["evidence_id"])

    # Immutability trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_evidence_update()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.screenshot_hash != NEW.screenshot_hash
               OR OLD.claim_text != NEW.claim_text
               OR OLD.source_url != NEW.source_url
               OR OLD.screenshot_path != NEW.screenshot_path THEN
                RAISE EXCEPTION 'Evidence records are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Immutability trigger
    op.execute("""
        CREATE TRIGGER evidence_immutable_guard
        BEFORE UPDATE ON evidence
        FOR EACH ROW
        EXECUTE FUNCTION prevent_evidence_update();
    """)


def downgrade() -> None:
    """Drop evidence tables and trigger."""
    op.execute("DROP TRIGGER IF EXISTS evidence_immutable_guard ON evidence;")
    op.execute("DROP FUNCTION IF EXISTS prevent_evidence_update();")
    op.drop_index("ix_evidence_audit_evidence_id", table_name="evidence_audit_log")
    op.drop_table("evidence_audit_log")
    op.drop_index("ix_evidence_severity", table_name="evidence")
    op.drop_index("ix_evidence_violation_type", table_name="evidence")
    op.drop_index("ix_evidence_violation_id", table_name="evidence")
    op.drop_index("ix_evidence_competitor_date", table_name="evidence")
    op.drop_index("ix_evidence_captured_at", table_name="evidence")
    op.drop_table("evidence")
