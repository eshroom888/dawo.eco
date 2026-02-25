"""Create agent_execution_logs table.

Story 7-8: Execution Logs & Status Dashboard.
Task 1.3: Alembic migration for AgentExecutionLog.

Stores historical execution log entries for agent runs with
status tracking, error details, captured log output, and
performance metrics for the execution dashboard.

Tables:
    - agent_execution_logs: Historical execution log entries

Revision ID: 2026_02_28_001
Revises: 2026_02_27_001
Create Date: 2026-02-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "2026_02_28_001"
down_revision = "2026_02_27_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create agent_execution_logs table with indexes."""

    op.create_table(
        "agent_execution_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="running",
        ),
        sa.Column(
            "trigger_type",
            sa.String(20),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column(
            "triggered_by",
            sa.String(50),
            nullable=False,
            server_default="scheduler",
        ),
        sa.Column("summary", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column("log_output", sa.Text(), nullable=True),
        sa.Column(
            "items_processed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes
    op.create_index(
        "idx_execution_logs_agent_name",
        "agent_execution_logs",
        ["agent_name"],
    )
    op.create_index(
        "idx_execution_logs_started_at",
        "agent_execution_logs",
        [sa.text("started_at DESC")],
    )
    op.create_index(
        "idx_execution_logs_status",
        "agent_execution_logs",
        ["status"],
    )
    op.create_index(
        "idx_execution_logs_agent_started",
        "agent_execution_logs",
        ["agent_name", sa.text("started_at DESC")],
    )


def downgrade() -> None:
    """Drop indexes first, then table."""
    op.drop_index("idx_execution_logs_agent_started", table_name="agent_execution_logs")
    op.drop_index("idx_execution_logs_status", table_name="agent_execution_logs")
    op.drop_index("idx_execution_logs_started_at", table_name="agent_execution_logs")
    op.drop_index("idx_execution_logs_agent_name", table_name="agent_execution_logs")
    op.drop_table("agent_execution_logs")
