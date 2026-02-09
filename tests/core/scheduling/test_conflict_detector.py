"""Tests for ConflictDetector.

Story 4-4, Task 11: Backend integration tests for conflict detection.
"""

import pytest
from datetime import date, datetime, time

from core.scheduling.conflict_detector import (
    ConflictDetector,
    ConflictResult,
    ConflictSeverity,
)


class MockScheduledItem:
    """Mock scheduled item for testing."""

    def __init__(self, item_id: str, scheduled_time: datetime):
        self.id = item_id
        self.scheduled_publish_time = scheduled_time


class TestConflictDetector:
    """Tests for ConflictDetector utility class."""

    def test_init_with_defaults(self):
        """Test initialization with default limits."""
        detector = ConflictDetector()
        assert detector.max_posts_per_hour == 2
        assert detector.max_posts_per_day == 8

    def test_init_with_custom_limits(self):
        """Test initialization with custom limits."""
        detector = ConflictDetector(max_posts_per_hour=3, max_posts_per_day=10)
        assert detector.max_posts_per_hour == 3
        assert detector.max_posts_per_day == 10

    def test_no_conflict_when_no_existing_items(self):
        """Test that no conflict is detected with empty schedule."""
        detector = ConflictDetector()
        target = datetime(2026, 2, 10, 9, 0)

        result = detector.detect_conflicts(target, [])

        assert result.has_conflict is False
        assert result.hour_conflict is None
        assert result.day_conflict is None

    def test_no_conflict_with_one_existing_item(self):
        """Test that one existing item doesn't trigger conflict."""
        detector = ConflictDetector()
        target = datetime(2026, 2, 10, 9, 0)
        existing = [
            MockScheduledItem("item-1", datetime(2026, 2, 10, 10, 0))  # Different hour
        ]

        result = detector.detect_conflicts(target, existing)

        assert result.has_conflict is False

    def test_warning_at_two_posts_same_hour(self):
        """Test that warning is triggered at 2 posts in same hour."""
        detector = ConflictDetector()
        target = datetime(2026, 2, 10, 9, 0)
        existing = [
            MockScheduledItem("item-1", datetime(2026, 2, 10, 9, 30))  # Same hour
        ]

        result = detector.detect_conflicts(target, existing)

        assert result.has_conflict is True
        assert result.hour_conflict is not None
        assert result.hour_conflict["severity"] == ConflictSeverity.WARNING.value
        assert result.hour_conflict["count"] == 2

    def test_critical_at_three_posts_same_hour(self):
        """Test that critical is triggered at 3+ posts in same hour."""
        detector = ConflictDetector()
        target = datetime(2026, 2, 10, 9, 0)
        existing = [
            MockScheduledItem("item-1", datetime(2026, 2, 10, 9, 15)),
            MockScheduledItem("item-2", datetime(2026, 2, 10, 9, 45)),
        ]

        result = detector.detect_conflicts(target, existing)

        assert result.has_conflict is True
        assert result.hour_conflict is not None
        assert result.hour_conflict["severity"] == ConflictSeverity.CRITICAL.value
        assert result.hour_conflict["count"] == 3

    def test_conflicting_ids_populated(self):
        """Test that conflicting item IDs are captured."""
        detector = ConflictDetector()
        target = datetime(2026, 2, 10, 9, 0)
        existing = [
            MockScheduledItem("item-1", datetime(2026, 2, 10, 9, 15)),
            MockScheduledItem("item-2", datetime(2026, 2, 10, 9, 45)),
        ]

        result = detector.detect_conflicts(target, existing)

        assert "item-1" in result.conflicting_ids
        assert "item-2" in result.conflicting_ids

    def test_exclude_id_is_respected(self):
        """Test that excluded item is not counted in conflicts."""
        detector = ConflictDetector()
        target = datetime(2026, 2, 10, 9, 0)
        existing = [
            MockScheduledItem("item-1", datetime(2026, 2, 10, 9, 15)),
        ]

        # Without exclude - should have conflict (2 posts)
        result_with = detector.detect_conflicts(target, existing)

        # With exclude - should not have conflict
        result_without = detector.detect_conflicts(target, existing, exclude_id="item-1")

        assert result_with.has_conflict is True
        assert result_without.has_conflict is False

    def test_day_warning_at_six_posts(self):
        """Test that day warning is triggered at 6 posts."""
        detector = ConflictDetector()
        target = datetime(2026, 2, 10, 15, 0)

        # 5 existing posts on same day, different hours
        existing = [
            MockScheduledItem(f"item-{i}", datetime(2026, 2, 10, 8 + i, 0))
            for i in range(5)
        ]

        result = detector.detect_conflicts(target, existing)

        assert result.has_conflict is True
        assert result.day_conflict is not None
        assert result.day_conflict["severity"] == ConflictSeverity.WARNING.value
        assert result.day_conflict["count"] == 6

    def test_day_critical_at_eight_posts(self):
        """Test that day critical is triggered at 8 posts."""
        detector = ConflictDetector()
        target = datetime(2026, 2, 10, 17, 0)

        # 7 existing posts on same day
        existing = [
            MockScheduledItem(f"item-{i}", datetime(2026, 2, 10, 8 + i, 0))
            for i in range(7)
        ]

        result = detector.detect_conflicts(target, existing)

        assert result.has_conflict is True
        assert result.day_conflict is not None
        assert result.day_conflict["severity"] == ConflictSeverity.CRITICAL.value
        assert result.day_conflict["count"] == 8

    def test_get_conflicts_in_range_returns_only_conflicts(self):
        """Test that get_conflicts_in_range only returns hours with 2+ posts."""
        detector = ConflictDetector()
        start = date(2026, 2, 10)
        end = date(2026, 2, 10)

        existing = [
            MockScheduledItem("item-1", datetime(2026, 2, 10, 9, 0)),
            MockScheduledItem("item-2", datetime(2026, 2, 10, 9, 30)),  # Conflict
            MockScheduledItem("item-3", datetime(2026, 2, 10, 14, 0)),  # No conflict
        ]

        conflicts = detector.get_conflicts_in_range(start, end, existing)

        # Only 9am hour should be in conflicts
        assert len(conflicts) == 1
        assert "2026-02-10T09:00:00" in conflicts
        assert len(conflicts["2026-02-10T09:00:00"]) == 2

    def test_suggest_spread_avoids_occupied_hours(self):
        """Test that suggest_spread avoids already occupied hours."""
        detector = ConflictDetector()
        target = date(2026, 2, 10)

        items_to_spread = ["new-1", "new-2", "new-3"]
        existing = [
            MockScheduledItem("item-1", datetime(2026, 2, 10, 9, 0)),
            MockScheduledItem("item-2", datetime(2026, 2, 10, 14, 0)),
        ]

        suggestions = detector.suggest_spread(items_to_spread, target, existing)

        assert len(suggestions) == 3
        # Check that suggestions avoid 9am and 2pm
        suggested_hours = [s.hour for s in suggestions]
        assert 9 not in suggested_hours
        assert 14 not in suggested_hours

    def test_suggest_spread_returns_valid_hours(self):
        """Test that suggested hours are within valid range."""
        detector = ConflictDetector()
        target = date(2026, 2, 10)

        items_to_spread = ["new-1", "new-2"]
        suggestions = detector.suggest_spread(items_to_spread, target, [])

        for suggestion in suggestions:
            assert 6 <= suggestion.hour <= 22
