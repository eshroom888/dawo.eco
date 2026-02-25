"""Tests for ChangeDetector.

Story 6-1, Task 12.8-12.13: Change detection tests.
"""

import pytest

import pandas as pd

from core.regulatory.models import ChangeType, ChangeSeverity
from teams.dawo.scanners.health_claims.change_detector import ChangeDetector


@pytest.fixture
def detector():
    return ChangeDetector(
        mushroom_keywords=("beta-glucan", "ganoderma", "reishi"),
        adaptogen_keywords=("ashwagandha", "rhodiola"),
        vitamin_mineral_keywords=("vitamin c",),
    )


@pytest.fixture
def detector_no_keywords():
    return ChangeDetector()


class TestChangeDetectorNewClaims:
    """Test 12.8: Detect NEW claims."""

    def test_new_claims_detected(self, detector, sample_claims_df, sample_claims_df_modified):
        changes = detector.detect(sample_claims_df, sample_claims_df_modified)
        new_changes = [c for c in changes if c.change_type == ChangeType.NEW.value]
        # ID-006 (Rhodiola) was added
        assert len(new_changes) >= 1
        new_ids = [c.claim_id for c in new_changes]
        assert "ID-006" in new_ids

    def test_new_relevant_claim_severity_high(self, detector, sample_claims_df, sample_claims_df_modified):
        changes = detector.detect(sample_claims_df, sample_claims_df_modified)
        new_changes = [c for c in changes if c.change_type == ChangeType.NEW.value]
        rhodiola_changes = [c for c in new_changes if c.claim_id == "ID-006"]
        assert len(rhodiola_changes) == 1
        # Rhodiola is adaptogen keyword → relevant → HIGH severity
        assert rhodiola_changes[0].is_relevant
        assert rhodiola_changes[0].severity == ChangeSeverity.HIGH.value


class TestChangeDetectorRemovedClaims:
    """Test 12.9: Detect REMOVED claims."""

    def test_removed_claims_detected(self, detector, sample_claims_df, sample_claims_df_modified):
        changes = detector.detect(sample_claims_df, sample_claims_df_modified)
        removed_changes = [c for c in changes if c.change_type == ChangeType.REMOVED.value]
        # ID-005 (Ashwagandha) was removed
        assert len(removed_changes) >= 1
        removed_ids = [c.claim_id for c in removed_changes]
        assert "ID-005" in removed_ids

    def test_removed_relevant_claim_severity_medium(self, detector, sample_claims_df, sample_claims_df_modified):
        changes = detector.detect(sample_claims_df, sample_claims_df_modified)
        removed_changes = [c for c in changes if c.change_type == ChangeType.REMOVED.value and c.claim_id == "ID-005"]
        assert len(removed_changes) == 1
        # Ashwagandha is adaptogen keyword → relevant → MEDIUM severity
        assert removed_changes[0].is_relevant
        assert removed_changes[0].severity == ChangeSeverity.MEDIUM.value


class TestChangeDetectorModifiedClaims:
    """Test 12.10: Detect MODIFIED claims."""

    def test_modified_field_detected(self, detector):
        prev = pd.DataFrame({
            "claim_id": ["ID-001"],
            "substance": ["Beta-glucans"],
            "claim_text": ["Old text"],
            "status": ["Authorised"],
        })
        curr = pd.DataFrame({
            "claim_id": ["ID-001"],
            "substance": ["Beta-glucans"],
            "claim_text": ["New text"],
            "status": ["Authorised"],
        })
        changes = detector.detect(prev, curr)
        modified = [c for c in changes if c.change_type == ChangeType.MODIFIED.value]
        assert len(modified) >= 1
        assert modified[0].field_changed == "claim_text"
        assert modified[0].old_value == "Old text"
        assert modified[0].new_value == "New text"


class TestChangeDetectorStatusChanged:
    """Test 12.11: Detect STATUS_CHANGED with severity."""

    def test_status_change_detected(self, detector, sample_claims_df, sample_claims_df_modified):
        changes = detector.detect(sample_claims_df, sample_claims_df_modified)
        status_changes = [c for c in changes if c.change_type == ChangeType.STATUS_CHANGED.value]
        # ID-003 (Ganoderma) status changed from "On hold" to "Authorised"
        assert len(status_changes) >= 1

    def test_relevant_status_change_severity_critical(self, detector, sample_claims_df, sample_claims_df_modified):
        changes = detector.detect(sample_claims_df, sample_claims_df_modified)
        ganoderma_status = [
            c for c in changes
            if c.change_type == ChangeType.STATUS_CHANGED.value and c.claim_id == "ID-003"
        ]
        assert len(ganoderma_status) == 1
        # Ganoderma is mushroom keyword → relevant → CRITICAL severity
        assert ganoderma_status[0].is_relevant
        assert ganoderma_status[0].severity == ChangeSeverity.CRITICAL.value

    def test_non_relevant_status_change_severity_medium(self, detector_no_keywords):
        prev = pd.DataFrame({
            "claim_id": ["ID-001"],
            "substance": ["Unknown substance"],
            "status": ["On hold"],
        })
        curr = pd.DataFrame({
            "claim_id": ["ID-001"],
            "substance": ["Unknown substance"],
            "status": ["Authorised"],
        })
        changes = detector_no_keywords.detect(prev, curr)
        status_changes = [c for c in changes if c.change_type == ChangeType.STATUS_CHANGED.value]
        assert len(status_changes) == 1
        assert not status_changes[0].is_relevant
        assert status_changes[0].severity == ChangeSeverity.MEDIUM.value


class TestChangeDetectorEmptyPrevious:
    """Test 12.12: Handle empty previous (first run)."""

    def test_first_run_no_changes(self, detector, sample_claims_df):
        changes = detector.detect(pd.DataFrame(), sample_claims_df)
        # First run → baseline, no changes
        assert len(changes) == 0


class TestChangeDetectorNoChanges:
    """Test 12.13: Handle no changes (identical DataFrames)."""

    def test_identical_dataframes_no_changes(self, detector, sample_claims_df):
        changes = detector.detect(sample_claims_df, sample_claims_df.copy())
        assert len(changes) == 0

    def test_both_empty_no_changes(self, detector):
        changes = detector.detect(pd.DataFrame(), pd.DataFrame())
        assert len(changes) == 0
