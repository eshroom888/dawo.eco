"""Tests for calendar event ID migration.

Story 7-9: Google Calendar Sync
Task 5.3: Migration tests (target: 3+)

Tests verify the migration module structure and the model
column definition without requiring a live database.
"""

import importlib

import pytest
from sqlalchemy import inspect as sa_inspect

from core.approval.models import ApprovalItem


class TestMigrationModule:
    """Tests for migration module structure."""

    def test_migration_has_upgrade_and_downgrade(self) -> None:
        """Migration module has both upgrade() and downgrade() functions."""
        migration = importlib.import_module(
            "migrations.versions.2026_03_01_001_add_calendar_event_id"
        )
        assert hasattr(migration, "upgrade")
        assert hasattr(migration, "downgrade")
        assert callable(migration.upgrade)
        assert callable(migration.downgrade)

    def test_migration_revision_chain(self) -> None:
        """Migration correctly chains from previous revision."""
        migration = importlib.import_module(
            "migrations.versions.2026_03_01_001_add_calendar_event_id"
        )
        assert migration.revision == "2026_03_01_001"
        assert migration.down_revision == "2026_02_28_001"


class TestApprovalItemModel:
    """Tests for google_calendar_event_id on ApprovalItem model."""

    def test_column_exists_on_model(self) -> None:
        """ApprovalItem model has google_calendar_event_id column."""
        mapper = sa_inspect(ApprovalItem)
        column_names = [col.key for col in mapper.columns]
        assert "google_calendar_event_id" in column_names

    def test_column_is_nullable(self) -> None:
        """google_calendar_event_id column is nullable."""
        mapper = sa_inspect(ApprovalItem)
        col = mapper.columns["google_calendar_event_id"]
        assert col.nullable is True

    def test_column_is_string_255(self) -> None:
        """google_calendar_event_id column is String(255)."""
        mapper = sa_inspect(ApprovalItem)
        col = mapper.columns["google_calendar_event_id"]
        assert col.type.length == 255
