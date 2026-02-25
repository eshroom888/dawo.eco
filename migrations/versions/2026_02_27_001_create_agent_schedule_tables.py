"""Create agent_schedules and schedule_change_logs tables.

Story 7-6: Agent Schedule Configuration.
Task 1.3: Alembic migration for AgentSchedule and ScheduleChangeLog.

Stores per-agent scheduling configuration with cron expressions,
run status tracking, dependency chains, and audit trail for
schedule modifications.

Tables:
    - agent_schedules: Agent scheduling config and run status
    - schedule_change_logs: Audit trail for schedule changes

Revision ID: 2026_02_27_001
Revises: 2026_02_26_001
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "2026_02_27_001"
down_revision = "2026_02_26_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create agent_schedules and schedule_change_logs tables."""

    # --- agent_schedules ---
    op.create_table(
        "agent_schedules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("schedule_cron", sa.String(50), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(20), nullable=True),
        sa.Column("last_run_duration_seconds", sa.Float(), nullable=True),
        sa.Column("last_run_summary", postgresql.JSONB(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "dependencies",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("config_source", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_name", name="uq_agent_schedules_agent_name"),
    )

    # Indexes for agent_schedules
    op.create_index(
        "idx_agent_schedules_agent_name",
        "agent_schedules",
        ["agent_name"],
    )
    op.create_index(
        "idx_agent_schedules_next_run_at",
        "agent_schedules",
        ["next_run_at"],
    )
    op.create_index(
        "idx_agent_schedules_enabled",
        "agent_schedules",
        ["enabled"],
        postgresql_where=sa.text("enabled = true"),
    )

    # --- schedule_change_logs ---
    op.create_table(
        "schedule_change_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("field_changed", sa.String(50), nullable=False),
        sa.Column("old_value", sa.String(500), nullable=True),
        sa.Column("new_value", sa.String(500), nullable=False),
        sa.Column(
            "changed_by",
            sa.String(50),
            nullable=False,
            server_default="operator",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index for schedule_change_logs
    op.create_index(
        "idx_schedule_change_logs_agent_name",
        "schedule_change_logs",
        ["agent_name"],
    )


def downgrade() -> None:
    """Drop indexes first, then tables."""
    # schedule_change_logs
    op.drop_index(
        "idx_schedule_change_logs_agent_name",
        table_name="schedule_change_logs",
    )
    op.drop_table("schedule_change_logs")

    # agent_schedules
    op.drop_index("idx_agent_schedules_enabled", table_name="agent_schedules")
    op.drop_index("idx_agent_schedules_next_run_at", table_name="agent_schedules")
    op.drop_index("idx_agent_schedules_agent_name", table_name="agent_schedules")
    op.drop_table("agent_schedules")
