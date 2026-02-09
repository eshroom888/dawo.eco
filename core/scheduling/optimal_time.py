"""Optimal time calculation for content scheduling.

Story 4-4, Task 3: OptimalTimeCalculator service class.

Calculates optimal publish times based on:
- Historical engagement data (40%) - placeholder for Epic 7
- Instagram peak times (35%) - 9-11am, 7-9pm local time
- Conflict avoidance (25%) - penalize same-hour posts

Usage:
    calculator = OptimalTimeCalculator(timezone="Europe/Oslo")
    suggestions = await calculator.get_optimal_slots(
        target_date=date(2026, 2, 10),
        scheduled_items=existing_items,
        count=3,
    )
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional, Protocol
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


@dataclass
class TimeSlotScore:
    """Score for a potential publish time slot.

    Attributes:
        time: Candidate publish time
        total_score: Weighted total score (0-1)
        engagement_score: Historical engagement score (0-1)
        peak_time_score: Instagram peak time score (0-1)
        conflict_score: Conflict avoidance score (0-1, 1 = no conflicts)
        reasoning: Human-readable explanation
    """

    time: datetime
    total_score: float
    engagement_score: float
    peak_time_score: float
    conflict_score: float
    reasoning: str


class EngagementDataProtocol(Protocol):
    """Protocol for engagement data source (Epic 7 integration).

    This protocol defines the interface for historical engagement
    data that will be implemented in Epic 7.
    """

    async def get_hourly_engagement(
        self,
        day_of_week: int,
        hour: int,
    ) -> float:
        """Get average engagement score for day/hour combination.

        Args:
            day_of_week: 0 = Monday, 6 = Sunday
            hour: 0-23 local time

        Returns:
            Engagement score 0-1 (higher is better)
        """
        ...


class OptimalTimeCalculator:
    """Calculate optimal publish times for content.

    Story 4-4, Task 3.1: OptimalTimeCalculator service class.

    Weights for scoring:
    - Historical engagement: 40%
    - Instagram peak times: 35%
    - Conflict avoidance: 25%

    Attributes:
        engagement_source: Optional engagement data provider (Epic 7)
        timezone: Operator's configured timezone
    """

    # Scoring weights
    WEIGHT_ENGAGEMENT = 0.40
    WEIGHT_PEAK_TIME = 0.35
    WEIGHT_CONFLICT = 0.25

    # Instagram peak engagement hours by day of week (local time)
    # Story 4-4, Task 3.2: Instagram peak time scoring
    PEAK_HOURS: dict[int, list[tuple[int, int]]] = {
        0: [(9, 11), (19, 21)],  # Monday
        1: [(9, 11), (19, 21)],  # Tuesday
        2: [(9, 11), (19, 21)],  # Wednesday
        3: [(9, 11), (19, 21)],  # Thursday
        4: [(9, 11), (17, 19)],  # Friday (earlier evening)
        5: [(10, 12), (17, 19)],  # Saturday
        6: [(10, 12), (19, 21)],  # Sunday
    }

    # Valid posting hours (6am to 11pm)
    MIN_HOUR = 6
    MAX_HOUR = 22

    def __init__(
        self,
        engagement_source: Optional[EngagementDataProtocol] = None,
        timezone: str = "Europe/Oslo",
    ) -> None:
        """Initialize the calculator.

        Args:
            engagement_source: Optional engagement data for scoring
            timezone: Operator's timezone for peak time calculations
        """
        self._engagement = engagement_source
        self._timezone = timezone
        try:
            self._tz = ZoneInfo(timezone)
        except Exception:
            logger.warning(f"Invalid timezone {timezone}, using UTC")
            self._tz = ZoneInfo("UTC")

    async def get_optimal_slots(
        self,
        target_date: date,
        scheduled_items: list,
        count: int = 3,
    ) -> list[TimeSlotScore]:
        """Get top N optimal time slots for a date.

        Story 4-4, Task 3.6: Return top 3 suggested time slots.

        Args:
            target_date: Date to find slots for
            scheduled_items: Existing scheduled items (for conflict check)
            count: Number of slots to return (default 3)

        Returns:
            List of TimeSlotScore sorted by total_score descending
        """
        scores: list[TimeSlotScore] = []

        for hour in range(self.MIN_HOUR, self.MAX_HOUR + 1):
            # Create candidate time in operator's timezone
            local_time = datetime.combine(target_date, time(hour, 0))
            # Convert to UTC for storage
            local_aware = local_time.replace(tzinfo=self._tz)
            slot_time = local_aware.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

            score = await self._calculate_score(
                slot_time=slot_time,
                local_hour=hour,
                day_of_week=target_date.weekday(),
                scheduled_items=scheduled_items,
            )
            scores.append(score)

        # Sort by total score descending
        scores.sort(key=lambda s: s.total_score, reverse=True)

        return scores[:count]

    async def _calculate_score(
        self,
        slot_time: datetime,
        local_hour: int,
        day_of_week: int,
        scheduled_items: list,
    ) -> TimeSlotScore:
        """Calculate score for a single time slot.

        Args:
            slot_time: UTC time for the slot
            local_hour: Hour in operator's local timezone
            day_of_week: 0 = Monday, 6 = Sunday
            scheduled_items: Existing scheduled items

        Returns:
            TimeSlotScore with all scoring components
        """
        # Peak time score
        peak_score = self._get_peak_score(day_of_week, local_hour)

        # Conflict score (1 = no conflicts, 0 = heavily conflicted)
        # Story 4-4, Task 3.3: Conflict avoidance scoring
        same_hour_count = self._count_same_hour(slot_time, scheduled_items)
        conflict_score = max(0, 1 - (same_hour_count * 0.5))

        # Engagement score (placeholder until Epic 7)
        # Story 4-4, Task 3.4: Placeholder for historical engagement
        if self._engagement:
            engagement_score = await self._engagement.get_hourly_engagement(
                day_of_week,
                local_hour,
            )
        else:
            # Fallback: use peak time as proxy for engagement
            engagement_score = peak_score

        # Weighted total
        # Story 4-4, Task 3.5: Weight factors
        total = (
            engagement_score * self.WEIGHT_ENGAGEMENT
            + peak_score * self.WEIGHT_PEAK_TIME
            + conflict_score * self.WEIGHT_CONFLICT
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            peak_score=peak_score,
            conflict_score=conflict_score,
            same_hour_count=same_hour_count,
        )

        return TimeSlotScore(
            time=slot_time,
            total_score=round(total, 3),
            engagement_score=round(engagement_score, 3),
            peak_time_score=round(peak_score, 3),
            conflict_score=round(conflict_score, 3),
            reasoning=reasoning,
        )

    def _get_peak_score(self, day_of_week: int, hour: int) -> float:
        """Get peak time score for day/hour combination.

        Args:
            day_of_week: 0 = Monday, 6 = Sunday
            hour: 0-23 local time

        Returns:
            Score: 1.0 = peak, 0.7 = near peak, 0.3 = off-peak
        """
        peak_ranges = self.PEAK_HOURS.get(day_of_week, [])

        for start, end in peak_ranges:
            if start <= hour < end:
                return 1.0  # Peak hour
            elif start - 1 <= hour < start or end <= hour < end + 1:
                return 0.7  # Near peak

        return 0.3  # Off-peak

    def _count_same_hour(
        self,
        slot_time: datetime,
        scheduled_items: list,
    ) -> int:
        """Count items scheduled in the same hour.

        Args:
            slot_time: Target time slot
            scheduled_items: Existing scheduled items

        Returns:
            Number of items in the same hour
        """
        slot_date = slot_time.date()
        slot_hour = slot_time.hour

        count = 0
        for item in scheduled_items:
            # Handle both datetime objects and items with scheduled_publish_time
            item_time = getattr(item, "scheduled_publish_time", item)
            if item_time is None:
                continue
            if isinstance(item_time, datetime):
                if item_time.date() == slot_date and item_time.hour == slot_hour:
                    count += 1

        return count

    def _generate_reasoning(
        self,
        peak_score: float,
        conflict_score: float,
        same_hour_count: int,
    ) -> str:
        """Generate human-readable reasoning.

        Args:
            peak_score: Peak time score (0-1)
            conflict_score: Conflict avoidance score (0-1)
            same_hour_count: Number of posts in same hour

        Returns:
            Explanation string like "Peak engagement time, no conflicts"
        """
        parts = []

        # Peak time explanation
        if peak_score >= 0.9:
            parts.append("Peak engagement time")
        elif peak_score >= 0.6:
            parts.append("Near peak engagement")
        else:
            parts.append("Off-peak hours")

        # Conflict explanation
        if same_hour_count == 0:
            parts.append("no conflicts")
        elif same_hour_count == 1:
            parts.append("1 other post scheduled")
        else:
            parts.append(f"{same_hour_count} posts same hour (crowded)")

        return ", ".join(parts)


__all__ = [
    "OptimalTimeCalculator",
    "TimeSlotScore",
    "EngagementDataProtocol",
]
