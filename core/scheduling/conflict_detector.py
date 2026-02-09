"""Conflict detection for content scheduling.

Story 4-4, Task 7: ConflictDetector utility class.

Detects scheduling conflicts when multiple posts are
scheduled for the same hour or when daily limits are exceeded.

Rules:
- Maximum 2 posts per hour (warning at 2, critical at 3+)
- Maximum 8 posts per day (warning at 6, critical at 8+)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ConflictSeverity(str, Enum):
    """Conflict severity levels.

    Values:
        WARNING: Approaching limit, may impact engagement
        CRITICAL: Limit exceeded, strongly discouraged
    """

    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ConflictResult:
    """Result of conflict detection for a time slot.

    Attributes:
        has_conflict: Whether any conflict was detected
        hour_conflict: Conflict info for hourly limit
        day_conflict: Conflict info for daily limit
        conflicting_ids: IDs of items causing conflicts
    """

    has_conflict: bool = False
    hour_conflict: Optional[dict] = None
    day_conflict: Optional[dict] = None
    conflicting_ids: list[str] = field(default_factory=list)


class ConflictDetector:
    """Utility class for detecting scheduling conflicts.

    Story 4-4, Task 7.1: ConflictDetector utility class.

    Attributes:
        max_posts_per_hour: Maximum recommended posts per hour
        max_posts_per_day: Maximum recommended posts per day
        warning_hour_threshold: Posts per hour to trigger warning
        warning_day_threshold: Posts per day to trigger warning
    """

    # Story 4-4, Task 7.2: Define conflict rules
    MAX_POSTS_PER_HOUR = 2
    MAX_POSTS_PER_DAY = 8
    WARNING_HOUR_THRESHOLD = 2
    CRITICAL_HOUR_THRESHOLD = 3
    WARNING_DAY_THRESHOLD = 6
    CRITICAL_DAY_THRESHOLD = 8

    def __init__(
        self,
        max_posts_per_hour: int = 2,
        max_posts_per_day: int = 8,
    ) -> None:
        """Initialize detector with custom limits.

        Args:
            max_posts_per_hour: Maximum posts per hour
            max_posts_per_day: Maximum posts per day
        """
        self.max_posts_per_hour = max_posts_per_hour
        self.max_posts_per_day = max_posts_per_day

    def detect_conflicts(
        self,
        target_time: datetime,
        scheduled_items: list,
        exclude_id: Optional[str] = None,
    ) -> ConflictResult:
        """Detect conflicts for a proposed time slot.

        Args:
            target_time: Proposed publish time
            scheduled_items: Existing scheduled items
            exclude_id: Item ID to exclude (for rescheduling)

        Returns:
            ConflictResult with detected conflicts
        """
        # Filter out excluded item
        items = [
            item for item in scheduled_items
            if str(getattr(item, "id", item)) != exclude_id
        ]

        # Check hourly conflicts
        hour_items = self._get_items_in_hour(target_time, items)
        hour_count = len(hour_items) + 1  # +1 for the new item

        # Check daily conflicts
        day_items = self._get_items_on_day(target_time.date(), items)
        day_count = len(day_items) + 1  # +1 for the new item

        result = ConflictResult()

        # Hourly conflict check
        if hour_count >= self.CRITICAL_HOUR_THRESHOLD:
            result.has_conflict = True
            result.hour_conflict = {
                "severity": ConflictSeverity.CRITICAL.value,
                "count": hour_count,
                "limit": self.max_posts_per_hour,
                "message": f"Too many posts! {hour_count} posts at this hour.",
            }
            result.conflicting_ids.extend(
                str(getattr(i, "id", i)) for i in hour_items
            )
        elif hour_count >= self.WARNING_HOUR_THRESHOLD:
            result.has_conflict = True
            result.hour_conflict = {
                "severity": ConflictSeverity.WARNING.value,
                "count": hour_count,
                "limit": self.max_posts_per_hour,
                "message": f"{hour_count} posts at this hour. Consider spreading.",
            }
            result.conflicting_ids.extend(
                str(getattr(i, "id", i)) for i in hour_items
            )

        # Daily conflict check
        if day_count >= self.CRITICAL_DAY_THRESHOLD:
            result.has_conflict = True
            result.day_conflict = {
                "severity": ConflictSeverity.CRITICAL.value,
                "count": day_count,
                "limit": self.max_posts_per_day,
                "message": f"Daily limit reached! {day_count} posts today.",
            }
        elif day_count >= self.WARNING_DAY_THRESHOLD:
            result.has_conflict = True
            result.day_conflict = {
                "severity": ConflictSeverity.WARNING.value,
                "count": day_count,
                "limit": self.max_posts_per_day,
                "message": f"{day_count} posts today. Approaching daily limit.",
            }

        return result

    def get_conflicts_in_range(
        self,
        start_date: date,
        end_date: date,
        scheduled_items: list,
    ) -> dict[str, list[str]]:
        """Get all conflicts in a date range.

        Story 4-4, Task 7.3: For calendar highlighting.

        Args:
            start_date: Start of range
            end_date: End of range
            scheduled_items: All scheduled items

        Returns:
            Dict mapping hour key (ISO string) to list of conflicting IDs
        """
        # Group items by hour
        hour_groups: dict[str, list[str]] = {}

        for item in scheduled_items:
            item_time = getattr(item, "scheduled_publish_time", None)
            if not item_time:
                continue
            if not (start_date <= item_time.date() <= end_date):
                continue

            hour_key = item_time.strftime("%Y-%m-%dT%H:00:00")
            if hour_key not in hour_groups:
                hour_groups[hour_key] = []
            hour_groups[hour_key].append(str(getattr(item, "id", item)))

        # Return only hours with conflicts
        return {
            hour: ids
            for hour, ids in hour_groups.items()
            if len(ids) >= self.WARNING_HOUR_THRESHOLD
        }

    def suggest_spread(
        self,
        items_to_spread: list,
        target_date: date,
        existing_items: list,
    ) -> list[datetime]:
        """Suggest evenly spread times for multiple items.

        Story 4-4, Task 7.6: Auto-resolve conflicts helper.

        Args:
            items_to_spread: Items needing new times
            target_date: Date to spread across
            existing_items: Already scheduled items

        Returns:
            List of suggested times (one per item)
        """
        # Find available hours (with no existing posts)
        occupied_hours = set()
        for item in existing_items:
            item_time = getattr(item, "scheduled_publish_time", None)
            if item_time and item_time.date() == target_date:
                occupied_hours.add(item_time.hour)

        # Available hours (6am to 10pm, excluding occupied)
        available = [
            h for h in range(6, 23)
            if h not in occupied_hours
        ]

        # If not enough available, use all hours
        if len(available) < len(items_to_spread):
            available = list(range(6, 23))

        # Spread items evenly across available hours
        suggestions = []
        step = max(1, len(available) // max(1, len(items_to_spread)))

        for i, _ in enumerate(items_to_spread):
            hour_idx = min(i * step, len(available) - 1)
            hour = available[hour_idx]
            suggestions.append(
                datetime.combine(target_date, datetime.min.time().replace(hour=hour))
            )

        return suggestions

    def _get_items_in_hour(
        self,
        target_time: datetime,
        items: list,
    ) -> list:
        """Get items scheduled in the same hour.

        Args:
            target_time: Target time
            items: Scheduled items

        Returns:
            Items in the same hour
        """
        target_date = target_time.date()
        target_hour = target_time.hour

        result = []
        for item in items:
            item_time = getattr(item, "scheduled_publish_time", None)
            if not item_time:
                continue
            if item_time.date() == target_date and item_time.hour == target_hour:
                result.append(item)

        return result

    def _get_items_on_day(
        self,
        target_date: date,
        items: list,
    ) -> list:
        """Get items scheduled on the same day.

        Args:
            target_date: Target date
            items: Scheduled items

        Returns:
            Items on the same day
        """
        result = []
        for item in items:
            item_time = getattr(item, "scheduled_publish_time", None)
            if not item_time:
                continue
            if item_time.date() == target_date:
                result.append(item)

        return result


__all__ = [
    "ConflictDetector",
    "ConflictResult",
    "ConflictSeverity",
]
