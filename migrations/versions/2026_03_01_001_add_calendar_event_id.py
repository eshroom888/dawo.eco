"""Add google_calendar_event_id to approval_items.

Story 7-9: Google Calendar Sync
Task 5.1: Migration to add calendar event ID column.

Adds a nullable VARCHAR(255) column to track the Google Calendar
event ID for each approval item, enabling event update/delete
on reschedule or publish.

Revision ID: 2026_03_01_001
Revises: 2026_02_28_001
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "2026_03_01_001"
down_revision = "2026_02_28_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add google_calendar_event_id column and index."""
    op.add_column(
        "approval_items",
        sa.Column(
            "google_calendar_event_id",
            sa.String(255),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_approval_items_calendar_event_id",
        "approval_items",
        ["google_calendar_event_id"],
    )


def downgrade() -> None:
    """Remove google_calendar_event_id column and index."""
    op.drop_index(
        "idx_approval_items_calendar_event_id",
        table_name="approval_items",
    )
    op.drop_column("approval_items", "google_calendar_event_id")
