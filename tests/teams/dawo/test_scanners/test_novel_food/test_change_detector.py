"""Tests for NovelFoodChangeDetector.

Story 6-2, Task 6: Create change detector.
"""

import pytest

from teams.dawo.scanners.novel_food.change_detector import NovelFoodChangeDetector
from teams.dawo.scanners.novel_food.schemas import (
    NovelFoodEntryRecord,
    CatalogueChangeRecord,
)
from teams.dawo.scanners.novel_food.config import SpeciesConfig


@pytest.fixture
def detector(species_config_dawo):
    return NovelFoodChangeDetector(species_config=species_config_dawo)


class TestDetectNewEntries:
    """Test 11.8: detect NEW entries."""

    def test_new_entry_detected(self, detector, sample_entry_records):
        current = sample_entry_records + [
            NovelFoodEntryRecord(
                species_latin="Hericium erinaceus",
                entry_name="Hericium erinaceus - mycelium",
                novel_food_status="novel",
            ),
        ]
        changes = detector.detect(sample_entry_records, current)
        new_changes = [c for c in changes if c.change_type == "new"]
        assert len(new_changes) == 1
        assert new_changes[0].entry_name == "Hericium erinaceus - mycelium"

    def test_new_entry_severity_dawo(self, detector):
        """New entries for DAWO products get HIGH severity."""
        prev: list[NovelFoodEntryRecord] = []
        curr = [
            NovelFoodEntryRecord(
                species_latin="Hericium erinaceus",
                entry_name="Test entry",
                novel_food_status="novel",
            ),
        ]
        changes = detector.detect(prev, curr)
        # First run with empty previous should return empty
        assert len(changes) == 0

    def test_new_entry_severity_non_empty_previous(self, detector, sample_entry_records):
        current = sample_entry_records + [
            NovelFoodEntryRecord(
                species_latin="Hericium erinaceus",
                entry_name="New test entry",
                novel_food_status="novel",
            ),
        ]
        changes = detector.detect(sample_entry_records, current)
        new_changes = [c for c in changes if c.change_type == "new"]
        assert len(new_changes) == 1
        assert new_changes[0].severity == "high"  # DAWO product


class TestDetectRemovedEntries:
    """Test 11.9: detect REMOVED entries."""

    def test_removed_entry_detected(self, detector, sample_entry_records):
        # Remove second entry
        current = [sample_entry_records[0]]
        changes = detector.detect(sample_entry_records, current)
        removed = [c for c in changes if c.change_type == "removed"]
        assert len(removed) == 1


class TestDetectModifiedEntries:
    """Test 11.10: detect MODIFIED entries."""

    def test_field_modification_detected(self, detector, sample_entry_records):
        modified = list(sample_entry_records)
        # Change a non-status field
        modified[0] = NovelFoodEntryRecord(
            species_latin="Hericium erinaceus",
            species_common="Lion's Mane",
            entry_name="Hericium erinaceus (Lion's Mane) - fruiting body",
            novel_food_status="novel",
            authorization_status="not_applicable",
            history_of_consumption="No history of significant consumption",
            member_state_comments="DE: Updated comment",  # CHANGED
            commission_comments="Classified as novel food",
            union_list_entry="No",
        )
        changes = detector.detect(sample_entry_records, modified)
        field_changes = [c for c in changes if c.change_type == "modified"]
        assert len(field_changes) >= 1
        assert any(c.field_changed == "member_state_comments" for c in field_changes)


class TestDetectStatusChanged:
    """Test 11.11: detect STATUS_CHANGED with correct severity."""

    def test_status_change_detected(self, detector, sample_entry_records, sample_entry_records_modified):
        changes = detector.detect(sample_entry_records, sample_entry_records_modified)
        status_changes = [c for c in changes if c.change_type == "status_changed"]
        assert len(status_changes) >= 1

    def test_status_change_severity_critical_dawo(self, detector, sample_entry_records):
        """DAWO product status change = CRITICAL."""
        modified = [
            NovelFoodEntryRecord(
                species_latin="Hericium erinaceus",
                species_common="Lion's Mane",
                entry_name="Hericium erinaceus (Lion's Mane) - fruiting body",
                novel_food_status="not_novel",  # CHANGED
                authorization_status="not_applicable",
                history_of_consumption="No history of significant consumption",
                member_state_comments="DE: Novel food",
                commission_comments="Classified as novel food",
                union_list_entry="No",
            ),
            sample_entry_records[1],
        ]
        changes = detector.detect(sample_entry_records, modified)
        status_changes = [c for c in changes if c.change_type == "status_changed"]
        assert len(status_changes) >= 1
        assert status_changes[0].severity == "critical"


class TestEmptyPrevious:
    """Test 11.12: handles empty previous (first run)."""

    def test_first_run_no_changes(self, detector, sample_entry_records):
        """First run with empty previous returns empty change list."""
        changes = detector.detect([], sample_entry_records)
        assert changes == []


class TestNoChanges:
    """Test 11.13: handles no changes."""

    def test_identical_entries_no_changes(self, detector, sample_entry_records):
        changes = detector.detect(sample_entry_records, list(sample_entry_records))
        assert changes == []


class TestSeverityAssignment:
    """Test 11.14: severity assignment (CRITICAL for DAWO products)."""

    def test_non_dawo_species_lower_severity(self):
        species_config = (
            SpeciesConfig(latin_name="Hericium erinaceus", is_dawo_product=True),
            SpeciesConfig(latin_name="Trametes versicolor", is_dawo_product=False),
        )
        detector = NovelFoodChangeDetector(species_config=species_config)

        prev = [
            NovelFoodEntryRecord(
                species_latin="Trametes versicolor",
                entry_name="Turkey Tail - extract",
                novel_food_status="novel",
            ),
        ]
        curr = [
            NovelFoodEntryRecord(
                species_latin="Trametes versicolor",
                entry_name="Turkey Tail - extract",
                novel_food_status="not_novel",
            ),
        ]
        changes = detector.detect(prev, curr)
        status_changes = [c for c in changes if c.change_type == "status_changed"]
        assert len(status_changes) == 1
        assert status_changes[0].severity == "high"  # not critical (not DAWO)
