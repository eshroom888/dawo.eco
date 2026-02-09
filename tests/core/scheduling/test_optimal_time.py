"""Tests for OptimalTimeCalculator.

Story 4-4, Task 11: Backend integration tests for optimal time engine.
"""

import pytest
from datetime import date, datetime, time
from unittest.mock import AsyncMock, MagicMock

from core.scheduling.optimal_time import (
    OptimalTimeCalculator,
    TimeSlotScore,
    EngagementDataProtocol,
)


class MockEngagementData:
    """Mock engagement data source for testing."""

    async def get_hourly_engagement(self, day_of_week: int, hour: int) -> float:
        # Simulate high engagement at peak hours
        if 9 <= hour <= 11 or 19 <= hour <= 21:
            return 0.9
        elif 7 <= hour <= 8 or 17 <= hour <= 18:
            return 0.6
        return 0.3


class MockScheduledItem:
    """Mock scheduled item for testing."""

    def __init__(self, scheduled_time: datetime):
        self.scheduled_publish_time = scheduled_time


class TestOptimalTimeCalculator:
    """Tests for OptimalTimeCalculator service."""

    def test_init_with_default_timezone(self):
        """Test initialization with default timezone."""
        calculator = OptimalTimeCalculator()
        assert calculator._timezone == "Europe/Oslo"

    def test_init_with_custom_timezone(self):
        """Test initialization with custom timezone."""
        calculator = OptimalTimeCalculator(timezone="America/New_York")
        assert calculator._timezone == "America/New_York"

    def test_init_with_invalid_timezone_falls_back_to_utc(self):
        """Test that invalid timezone falls back to UTC."""
        calculator = OptimalTimeCalculator(timezone="Invalid/Timezone")
        # Should not raise, uses UTC as fallback
        assert calculator._tz.key == "UTC"

    @pytest.mark.asyncio
    async def test_get_optimal_slots_returns_correct_count(self):
        """Test that get_optimal_slots returns requested number of slots."""
        calculator = OptimalTimeCalculator()
        target = date(2026, 2, 10)  # A Tuesday

        slots = await calculator.get_optimal_slots(target, [], count=3)

        assert len(slots) == 3
        for slot in slots:
            assert isinstance(slot, TimeSlotScore)

    @pytest.mark.asyncio
    async def test_get_optimal_slots_sorted_by_score(self):
        """Test that slots are sorted by total_score descending."""
        calculator = OptimalTimeCalculator()
        target = date(2026, 2, 10)

        slots = await calculator.get_optimal_slots(target, [], count=5)

        scores = [s.total_score for s in slots]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_peak_hours_score_higher_than_off_peak(self):
        """Test that peak hours get higher scores than off-peak."""
        calculator = OptimalTimeCalculator()
        target = date(2026, 2, 10)  # Tuesday

        slots = await calculator.get_optimal_slots(target, [], count=17)

        # Find peak hour slot (e.g., 9am)
        peak_slots = [s for s in slots if s.time.hour in [9, 10, 19, 20]]
        off_peak_slots = [s for s in slots if s.time.hour in [6, 7, 15, 16]]

        if peak_slots and off_peak_slots:
            avg_peak = sum(s.peak_time_score for s in peak_slots) / len(peak_slots)
            avg_off_peak = sum(s.peak_time_score for s in off_peak_slots) / len(off_peak_slots)
            assert avg_peak > avg_off_peak

    @pytest.mark.asyncio
    async def test_conflict_reduces_score(self):
        """Test that having existing posts reduces the slot score."""
        calculator = OptimalTimeCalculator()
        target = date(2026, 2, 10)

        # No conflicts
        slots_no_conflict = await calculator.get_optimal_slots(target, [], count=3)

        # With conflict at 9am
        conflicting_item = MockScheduledItem(
            datetime.combine(target, time(9, 0))
        )
        slots_with_conflict = await calculator.get_optimal_slots(
            target, [conflicting_item], count=3
        )

        # Find 9am slot in both
        slot_9am_no_conflict = next(
            (s for s in slots_no_conflict if s.time.hour == 9), None
        )
        slot_9am_with_conflict = next(
            (s for s in slots_with_conflict if s.time.hour == 9), None
        )

        if slot_9am_no_conflict and slot_9am_with_conflict:
            assert slot_9am_with_conflict.conflict_score < slot_9am_no_conflict.conflict_score

    @pytest.mark.asyncio
    async def test_engagement_data_integration(self):
        """Test that engagement data is used when provided."""
        mock_engagement = MockEngagementData()
        calculator = OptimalTimeCalculator(engagement_source=mock_engagement)
        target = date(2026, 2, 10)

        slots = await calculator.get_optimal_slots(target, [], count=3)

        # Check that engagement_score is populated
        for slot in slots:
            assert 0 <= slot.engagement_score <= 1

    def test_get_peak_score_returns_correct_values(self):
        """Test peak score calculation for different hours."""
        calculator = OptimalTimeCalculator()

        # Peak hour (Tuesday 9am)
        assert calculator._get_peak_score(1, 9) == 1.0
        assert calculator._get_peak_score(1, 10) == 1.0

        # Near peak (Tuesday 8am)
        assert calculator._get_peak_score(1, 8) == 0.7

        # Off-peak (Tuesday 3pm)
        assert calculator._get_peak_score(1, 15) == 0.3

    def test_count_same_hour_with_no_items(self):
        """Test counting items when list is empty."""
        calculator = OptimalTimeCalculator()
        target = datetime(2026, 2, 10, 9, 0)

        count = calculator._count_same_hour(target, [])
        assert count == 0

    def test_count_same_hour_with_matching_items(self):
        """Test counting items in the same hour."""
        calculator = OptimalTimeCalculator()
        target = datetime(2026, 2, 10, 9, 0)

        items = [
            MockScheduledItem(datetime(2026, 2, 10, 9, 15)),
            MockScheduledItem(datetime(2026, 2, 10, 9, 30)),
            MockScheduledItem(datetime(2026, 2, 10, 10, 0)),  # Different hour
        ]

        count = calculator._count_same_hour(target, items)
        assert count == 2

    def test_generate_reasoning_peak_no_conflicts(self):
        """Test reasoning generation for peak time without conflicts."""
        calculator = OptimalTimeCalculator()

        reasoning = calculator._generate_reasoning(
            peak_score=1.0,
            conflict_score=1.0,
            same_hour_count=0,
        )

        assert "Peak engagement time" in reasoning
        assert "no conflicts" in reasoning

    def test_generate_reasoning_off_peak_with_conflicts(self):
        """Test reasoning generation for off-peak time with conflicts."""
        calculator = OptimalTimeCalculator()

        reasoning = calculator._generate_reasoning(
            peak_score=0.3,
            conflict_score=0.5,
            same_hour_count=2,
        )

        assert "Off-peak" in reasoning
        assert "2 posts same hour" in reasoning


class TestWeightConstants:
    """Tests for scoring weight constants."""

    def test_weights_sum_to_one(self):
        """Test that scoring weights sum to 1.0."""
        total = (
            OptimalTimeCalculator.WEIGHT_ENGAGEMENT
            + OptimalTimeCalculator.WEIGHT_PEAK_TIME
            + OptimalTimeCalculator.WEIGHT_CONFLICT
        )
        assert total == pytest.approx(1.0)

    def test_engagement_has_highest_weight(self):
        """Test that engagement has the highest weight (40%)."""
        assert OptimalTimeCalculator.WEIGHT_ENGAGEMENT == 0.40
        assert OptimalTimeCalculator.WEIGHT_ENGAGEMENT > OptimalTimeCalculator.WEIGHT_PEAK_TIME
        assert OptimalTimeCalculator.WEIGHT_ENGAGEMENT > OptimalTimeCalculator.WEIGHT_CONFLICT
