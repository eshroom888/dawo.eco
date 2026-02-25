"""Create leads tables for Epic 5.

Revision ID: 2026_02_09_001
Revises: 2026_02_08_003
Create Date: 2026-02-09

Epic 5: B2B Sales Pipeline
Story 5-5: Lead Pipeline Status Tracking
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "2026_02_09_001"
down_revision: Union[str, None] = "2026_02_08_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create leads, lead_activities, and outreach_emails tables."""

    # Create leads table
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("job_title", sa.String(200), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("website_url", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(200), nullable=True),
        sa.Column("company_size", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("source", sa.String(30), nullable=False, server_default="cold_research"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("enrichment_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("enriched_at", sa.DateTime(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), server_default="{}", nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("last_contacted_at", sa.DateTime(), nullable=True),
        sa.Column("last_replied_at", sa.DateTime(), nullable=True),
        sa.Column("contact_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_followup_at", sa.DateTime(), nullable=True),
        sa.Column("converted_at", sa.DateTime(), nullable=True),
        sa.Column("lost_reason", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # Create indexes for leads
    op.create_index("idx_leads_email", "leads", ["email"])
    op.create_index("idx_leads_company", "leads", ["company"])
    op.create_index("idx_leads_status", "leads", ["status"])
    op.create_index("idx_leads_score", "leads", ["score"])
    op.create_index("idx_leads_pipeline", "leads", ["status", sa.text("score DESC")])
    op.create_index("idx_leads_followup", "leads", ["next_followup_at"])

    # Create lead_activities table
    op.create_table(
        "lead_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True, server_default="system"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_lead_activities_lead_id", "lead_activities", ["lead_id"])

    # Create outreach_emails table
    op.create_table(
        "outreach_emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("template_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("gmail_message_id", sa.String(100), nullable=True),
        sa.Column("gmail_thread_id", sa.String(100), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("bounce_reason", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_outreach_emails_lead_id", "outreach_emails", ["lead_id"])
    op.create_index("idx_outreach_emails_status", "outreach_emails", ["status"])
    op.create_index("idx_outreach_emails_gmail_id", "outreach_emails", ["gmail_message_id"])


def downgrade() -> None:
    """Drop leads tables."""
    op.drop_table("outreach_emails")
    op.drop_table("lead_activities")
    op.drop_table("leads")
