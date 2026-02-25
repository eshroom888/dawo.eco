"""Tests for regulatory data models.

Story 6-1, Task 1: Create regulatory data models.
Tests SQLAlchemy models, enums, and indexes for EU Health Claims.
"""

import pytest
from datetime import datetime, UTC
from uuid import UUID

from core.regulatory.models import (
    HealthClaim,
    ClaimSnapshot,
    ClaimChange,
    ClaimStatus,
    ChangeType,
    ChangeSeverity,
)


# === Enum Tests ===


class TestClaimStatus:
    """Tests for ClaimStatus enum."""

    def test_authorised_value(self):
        assert ClaimStatus.AUTHORISED.value == "authorised"

    def test_non_authorised_value(self):
        assert ClaimStatus.NON_AUTHORISED.value == "non_authorised"

    def test_on_hold_value(self):
        assert ClaimStatus.ON_HOLD.value == "on_hold"

    def test_withdrawn_value(self):
        assert ClaimStatus.WITHDRAWN.value == "withdrawn"

    def test_is_str_enum(self):
        """ClaimStatus must be str enum for JSON serialization."""
        assert isinstance(ClaimStatus.AUTHORISED, str)

    def test_all_values_present(self):
        assert len(ClaimStatus) == 4

    def test_from_string(self):
        """Can construct from string value."""
        assert ClaimStatus("authorised") == ClaimStatus.AUTHORISED


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_new_value(self):
        assert ChangeType.NEW.value == "new"

    def test_removed_value(self):
        assert ChangeType.REMOVED.value == "removed"

    def test_modified_value(self):
        assert ChangeType.MODIFIED.value == "modified"

    def test_status_changed_value(self):
        assert ChangeType.STATUS_CHANGED.value == "status_changed"

    def test_is_str_enum(self):
        assert isinstance(ChangeType.NEW, str)

    def test_all_values_present(self):
        assert len(ChangeType) == 4


class TestChangeSeverity:
    """Tests for ChangeSeverity enum."""

    def test_low_value(self):
        assert ChangeSeverity.LOW.value == "low"

    def test_medium_value(self):
        assert ChangeSeverity.MEDIUM.value == "medium"

    def test_high_value(self):
        assert ChangeSeverity.HIGH.value == "high"

    def test_critical_value(self):
        assert ChangeSeverity.CRITICAL.value == "critical"

    def test_is_str_enum(self):
        assert isinstance(ChangeSeverity.LOW, str)

    def test_all_values_present(self):
        assert len(ChangeSeverity) == 4


# === Model Table Configuration Tests ===


class TestHealthClaimModel:
    """Tests for HealthClaim SQLAlchemy model."""

    def test_tablename(self):
        assert HealthClaim.__tablename__ == "health_claims"

    def test_has_id_column(self):
        assert "id" in HealthClaim.__table__.columns

    def test_has_claim_id_column(self):
        assert "claim_id" in HealthClaim.__table__.columns

    def test_has_claim_type_column(self):
        assert "claim_type" in HealthClaim.__table__.columns

    def test_has_substance_column(self):
        assert "substance" in HealthClaim.__table__.columns

    def test_has_health_relationship_column(self):
        assert "health_relationship" in HealthClaim.__table__.columns

    def test_has_claim_text_column(self):
        assert "claim_text" in HealthClaim.__table__.columns

    def test_has_conditions_of_use_column(self):
        assert "conditions_of_use" in HealthClaim.__table__.columns

    def test_has_food_category_column(self):
        assert "food_category" in HealthClaim.__table__.columns

    def test_has_status_column(self):
        assert "status" in HealthClaim.__table__.columns

    def test_has_efsa_opinion_column(self):
        assert "efsa_opinion" in HealthClaim.__table__.columns

    def test_has_commission_regulation_column(self):
        assert "commission_regulation" in HealthClaim.__table__.columns

    def test_has_date_of_entry_column(self):
        assert "date_of_entry" in HealthClaim.__table__.columns

    def test_has_last_update_column(self):
        assert "last_update" in HealthClaim.__table__.columns

    def test_has_restrictions_column(self):
        assert "restrictions" in HealthClaim.__table__.columns

    def test_has_is_relevant_column(self):
        assert "is_relevant" in HealthClaim.__table__.columns

    def test_has_relevance_category_column(self):
        assert "relevance_category" in HealthClaim.__table__.columns

    def test_has_snapshot_id_column(self):
        assert "snapshot_id" in HealthClaim.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in HealthClaim.__table__.columns

    def test_has_updated_at_column(self):
        assert "updated_at" in HealthClaim.__table__.columns

    def test_id_is_uuid_primary_key(self):
        col = HealthClaim.__table__.columns["id"]
        assert col.primary_key

    def test_substance_index_exists(self):
        index_names = {idx.name for idx in HealthClaim.__table__.indexes}
        assert "idx_health_claims_substance" in index_names

    def test_status_index_exists(self):
        index_names = {idx.name for idx in HealthClaim.__table__.indexes}
        assert "idx_health_claims_status" in index_names

    def test_repr(self):
        """Model __repr__ includes key fields."""
        claim = HealthClaim(
            claim_id="ID-001",
            substance="Beta-glucans",
            status="authorised",
            snapshot_id="00000000-0000-0000-0000-000000000000",
        )
        result = repr(claim)
        assert "ID-001" in result
        assert "Beta-glucans" in result


class TestClaimSnapshotModel:
    """Tests for ClaimSnapshot SQLAlchemy model."""

    def test_tablename(self):
        assert ClaimSnapshot.__tablename__ == "claim_snapshots"

    def test_has_id_column(self):
        assert "id" in ClaimSnapshot.__table__.columns

    def test_has_snapshot_hash_column(self):
        assert "snapshot_hash" in ClaimSnapshot.__table__.columns

    def test_has_claim_count_column(self):
        assert "claim_count" in ClaimSnapshot.__table__.columns

    def test_has_relevant_claim_count_column(self):
        assert "relevant_claim_count" in ClaimSnapshot.__table__.columns

    def test_has_source_url_column(self):
        assert "source_url" in ClaimSnapshot.__table__.columns

    def test_has_downloaded_at_column(self):
        assert "downloaded_at" in ClaimSnapshot.__table__.columns

    def test_has_file_size_bytes_column(self):
        assert "file_size_bytes" in ClaimSnapshot.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in ClaimSnapshot.__table__.columns

    def test_id_is_uuid_primary_key(self):
        col = ClaimSnapshot.__table__.columns["id"]
        assert col.primary_key

    def test_repr(self):
        from datetime import datetime, UTC
        snapshot = ClaimSnapshot(
            snapshot_hash="abc123",
            claim_count=100,
            relevant_claim_count=5,
            source_url="https://example.com",
            downloaded_at=datetime.now(UTC),
            file_size_bytes=1024,
        )
        result = repr(snapshot)
        assert "100" in result
        assert "abc123" in result


class TestClaimChangeModel:
    """Tests for ClaimChange SQLAlchemy model."""

    def test_tablename(self):
        assert ClaimChange.__tablename__ == "claim_changes"

    def test_has_id_column(self):
        assert "id" in ClaimChange.__table__.columns

    def test_has_snapshot_id_column(self):
        assert "snapshot_id" in ClaimChange.__table__.columns

    def test_has_claim_id_column(self):
        assert "claim_id" in ClaimChange.__table__.columns

    def test_has_change_type_column(self):
        assert "change_type" in ClaimChange.__table__.columns

    def test_has_field_changed_column(self):
        assert "field_changed" in ClaimChange.__table__.columns

    def test_has_old_value_column(self):
        assert "old_value" in ClaimChange.__table__.columns

    def test_has_new_value_column(self):
        assert "new_value" in ClaimChange.__table__.columns

    def test_has_is_relevant_column(self):
        assert "is_relevant" in ClaimChange.__table__.columns

    def test_has_severity_column(self):
        assert "severity" in ClaimChange.__table__.columns

    def test_has_created_at_column(self):
        assert "created_at" in ClaimChange.__table__.columns

    def test_snapshot_id_is_foreign_key(self):
        col = ClaimChange.__table__.columns["snapshot_id"]
        assert len(col.foreign_keys) > 0

    def test_snapshot_index_exists(self):
        index_names = {idx.name for idx in ClaimChange.__table__.indexes}
        assert "idx_claim_changes_snapshot" in index_names

    def test_relevant_severity_index_exists(self):
        index_names = {idx.name for idx in ClaimChange.__table__.indexes}
        assert "idx_claim_changes_relevant" in index_names

    def test_repr(self):
        change = ClaimChange(
            claim_id="ID-001",
            change_type="new",
            snapshot_id="00000000-0000-0000-0000-000000000000",
        )
        result = repr(change)
        assert "ID-001" in result


# === Module Exports Test ===


class TestModuleExports:
    """Tests that __all__ exports are complete."""

    def test_all_exports_exist(self):
        from core.regulatory import models
        expected = [
            "HealthClaim",
            "ClaimSnapshot",
            "ClaimChange",
            "ClaimStatus",
            "ChangeType",
            "ChangeSeverity",
        ]
        for name in expected:
            assert name in models.__all__, f"{name} missing from __all__"

    def test_regulatory_init_exports(self):
        from core.regulatory import __all__ as reg_all
        expected = [
            "HealthClaim",
            "ClaimSnapshot",
            "ClaimChange",
            "ClaimStatus",
            "ChangeType",
            "ChangeSeverity",
        ]
        for name in expected:
            assert name in reg_all, f"{name} missing from core.regulatory __all__"
