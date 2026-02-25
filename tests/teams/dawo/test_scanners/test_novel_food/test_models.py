"""Tests for Novel Food regulatory data models.

Story 6-2, Task 1: Extend regulatory data models for Novel Food.
Tests SQLAlchemy models, enums, and indexes for Novel Food Catalogue monitoring.
"""

import pytest

from core.regulatory.models import (
    NovelFoodEntry,
    NovelFoodSnapshot,
    NovelFoodChange,
    NovelFoodStatus,
    AuthorizationStatus,
    ChangeType,
    ChangeSeverity,
)


# === Enum Tests ===


class TestNovelFoodStatus:
    """Tests for NovelFoodStatus enum."""

    def test_novel_value(self):
        assert NovelFoodStatus.NOVEL.value == "novel"

    def test_not_novel_value(self):
        assert NovelFoodStatus.NOT_NOVEL.value == "not_novel"

    def test_not_determined_value(self):
        assert NovelFoodStatus.NOT_DETERMINED.value == "not_determined"

    def test_ambiguous_value(self):
        assert NovelFoodStatus.AMBIGUOUS.value == "ambiguous"

    def test_is_str_enum(self):
        """NovelFoodStatus must be str enum for JSON serialization."""
        assert isinstance(NovelFoodStatus.NOVEL, str)

    def test_all_values_present(self):
        assert len(NovelFoodStatus) == 4

    def test_from_string(self):
        """Can construct from string value."""
        assert NovelFoodStatus("novel") == NovelFoodStatus.NOVEL


class TestAuthorizationStatus:
    """Tests for AuthorizationStatus enum."""

    def test_authorised_value(self):
        assert AuthorizationStatus.AUTHORISED.value == "authorised"

    def test_not_authorised_value(self):
        assert AuthorizationStatus.NOT_AUTHORISED.value == "not_authorised"

    def test_pending_value(self):
        assert AuthorizationStatus.PENDING.value == "pending"

    def test_not_applicable_value(self):
        assert AuthorizationStatus.NOT_APPLICABLE.value == "not_applicable"

    def test_is_str_enum(self):
        assert isinstance(AuthorizationStatus.AUTHORISED, str)

    def test_all_values_present(self):
        assert len(AuthorizationStatus) == 4

    def test_from_string(self):
        assert AuthorizationStatus("authorised") == AuthorizationStatus.AUTHORISED


# === Model Table Configuration Tests ===


class TestNovelFoodEntryModel:
    """Tests for NovelFoodEntry SQLAlchemy model."""

    def test_tablename(self):
        assert NovelFoodEntry.__tablename__ == "novel_food_entries"

    def test_has_id_column(self):
        assert "id" in NovelFoodEntry.__table__.columns

    def test_has_snapshot_id_column(self):
        assert "snapshot_id" in NovelFoodEntry.__table__.columns

    def test_has_species_latin_column(self):
        assert "species_latin" in NovelFoodEntry.__table__.columns

    def test_has_species_common_column(self):
        assert "species_common" in NovelFoodEntry.__table__.columns

    def test_has_entry_name_column(self):
        assert "entry_name" in NovelFoodEntry.__table__.columns

    def test_has_novel_food_status_column(self):
        assert "novel_food_status" in NovelFoodEntry.__table__.columns

    def test_has_authorization_status_column(self):
        assert "authorization_status" in NovelFoodEntry.__table__.columns

    def test_has_history_of_consumption_column(self):
        assert "history_of_consumption" in NovelFoodEntry.__table__.columns

    def test_has_member_state_comments_column(self):
        assert "member_state_comments" in NovelFoodEntry.__table__.columns

    def test_has_commission_comments_column(self):
        assert "commission_comments" in NovelFoodEntry.__table__.columns

    def test_has_conditions_of_use_column(self):
        assert "conditions_of_use" in NovelFoodEntry.__table__.columns

    def test_has_regulation_reference_column(self):
        assert "regulation_reference" in NovelFoodEntry.__table__.columns

    def test_has_union_list_entry_column(self):
        assert "union_list_entry" in NovelFoodEntry.__table__.columns

    def test_has_source_url_column(self):
        assert "source_url" in NovelFoodEntry.__table__.columns

    def test_has_raw_html_hash_column(self):
        assert "raw_html_hash" in NovelFoodEntry.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in NovelFoodEntry.__table__.columns

    def test_has_updated_at_column(self):
        assert "updated_at" in NovelFoodEntry.__table__.columns

    def test_id_is_uuid_primary_key(self):
        col = NovelFoodEntry.__table__.columns["id"]
        assert col.primary_key

    def test_snapshot_id_is_foreign_key(self):
        col = NovelFoodEntry.__table__.columns["snapshot_id"]
        assert len(col.foreign_keys) > 0

    def test_species_index_exists(self):
        index_names = {idx.name for idx in NovelFoodEntry.__table__.indexes}
        assert "idx_novel_food_entries_species" in index_names

    def test_snapshot_index_exists(self):
        index_names = {idx.name for idx in NovelFoodEntry.__table__.indexes}
        assert "idx_novel_food_entries_snapshot" in index_names

    def test_repr(self):
        entry = NovelFoodEntry(
            species_latin="Hericium erinaceus",
            entry_name="Lion's Mane - fruiting body",
            novel_food_status="novel",
            snapshot_id="00000000-0000-0000-0000-000000000000",
        )
        result = repr(entry)
        assert "Hericium erinaceus" in result
        assert "novel" in result


class TestNovelFoodSnapshotModel:
    """Tests for NovelFoodSnapshot SQLAlchemy model."""

    def test_tablename(self):
        assert NovelFoodSnapshot.__tablename__ == "novel_food_snapshots"

    def test_has_id_column(self):
        assert "id" in NovelFoodSnapshot.__table__.columns

    def test_has_snapshot_hash_column(self):
        assert "snapshot_hash" in NovelFoodSnapshot.__table__.columns

    def test_has_total_entries_column(self):
        assert "total_entries" in NovelFoodSnapshot.__table__.columns

    def test_has_relevant_entries_column(self):
        assert "relevant_entries" in NovelFoodSnapshot.__table__.columns

    def test_has_species_queried_column(self):
        assert "species_queried" in NovelFoodSnapshot.__table__.columns

    def test_has_search_duration_seconds_column(self):
        assert "search_duration_seconds" in NovelFoodSnapshot.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in NovelFoodSnapshot.__table__.columns

    def test_id_is_uuid_primary_key(self):
        col = NovelFoodSnapshot.__table__.columns["id"]
        assert col.primary_key

    def test_repr(self):
        snapshot = NovelFoodSnapshot(
            snapshot_hash="abc123def456",
            total_entries=15,
            relevant_entries=6,
            species_queried=6,
            search_duration_seconds=120.5,
        )
        result = repr(snapshot)
        assert "15" in result
        assert "abc123def456" in result


class TestNovelFoodChangeModel:
    """Tests for NovelFoodChange SQLAlchemy model."""

    def test_tablename(self):
        assert NovelFoodChange.__tablename__ == "novel_food_changes"

    def test_has_id_column(self):
        assert "id" in NovelFoodChange.__table__.columns

    def test_has_snapshot_id_column(self):
        assert "snapshot_id" in NovelFoodChange.__table__.columns

    def test_has_species_latin_column(self):
        assert "species_latin" in NovelFoodChange.__table__.columns

    def test_has_entry_name_column(self):
        assert "entry_name" in NovelFoodChange.__table__.columns

    def test_has_change_type_column(self):
        assert "change_type" in NovelFoodChange.__table__.columns

    def test_has_field_changed_column(self):
        assert "field_changed" in NovelFoodChange.__table__.columns

    def test_has_old_value_column(self):
        assert "old_value" in NovelFoodChange.__table__.columns

    def test_has_new_value_column(self):
        assert "new_value" in NovelFoodChange.__table__.columns

    def test_has_severity_column(self):
        assert "severity" in NovelFoodChange.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in NovelFoodChange.__table__.columns

    def test_snapshot_id_is_foreign_key(self):
        col = NovelFoodChange.__table__.columns["snapshot_id"]
        assert len(col.foreign_keys) > 0

    def test_snapshot_index_exists(self):
        index_names = {idx.name for idx in NovelFoodChange.__table__.indexes}
        assert "idx_novel_food_changes_snapshot" in index_names

    def test_severity_index_exists(self):
        index_names = {idx.name for idx in NovelFoodChange.__table__.indexes}
        assert "idx_novel_food_changes_severity" in index_names

    def test_repr(self):
        change = NovelFoodChange(
            species_latin="Hericium erinaceus",
            entry_name="Lion's Mane",
            change_type="status_changed",
            snapshot_id="00000000-0000-0000-0000-000000000000",
        )
        result = repr(change)
        assert "Hericium erinaceus" in result


# === Module Exports Test ===


class TestNovelFoodModuleExports:
    """Tests that __all__ exports include Novel Food types."""

    def test_models_all_exports(self):
        from core.regulatory import models
        expected = [
            "NovelFoodEntry",
            "NovelFoodSnapshot",
            "NovelFoodChange",
            "NovelFoodStatus",
            "AuthorizationStatus",
        ]
        for name in expected:
            assert name in models.__all__, f"{name} missing from models.__all__"

    def test_regulatory_init_exports(self):
        from core.regulatory import __all__ as reg_all
        expected = [
            "NovelFoodEntry",
            "NovelFoodSnapshot",
            "NovelFoodChange",
            "NovelFoodStatus",
            "AuthorizationStatus",
        ]
        for name in expected:
            assert name in reg_all, f"{name} missing from core.regulatory __all__"
