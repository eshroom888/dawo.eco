"""Cron expression utilities for agent scheduling.

Story 7-6, Task 2.1: Validation, ARQ conversion, next-run calculation,
and human-readable formatting for 5-field cron expressions.

CRITICAL: Cron uses 0=Sunday, Python/ARQ uses 0=Monday, 6=Sunday.
Mapping formula: python_weekday = (cron_weekday + 6) % 7

Usage:
    from core.scheduling.cron_utils import (
        validate_cron_expression,
        cron_expr_to_arq_kwargs,
        calculate_next_run,
        cron_to_human_readable,
    )
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Cron field definitions: (name, min, max)
_CRON_FIELDS = [
    ("minute", 0, 59),
    ("hour", 0, 23),
    ("day", 1, 31),
    ("month", 1, 12),
    ("weekday", 0, 6),
]

# Days of week for human-readable output (cron convention: 0=Sunday)
_CRON_DAY_NAMES = [
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday",
]


def _parse_cron_field(field: str, min_val: int, max_val: int) -> set[int] | None:
    """Parse a single cron field into a set of values.

    Args:
        field: Cron field string (e.g. "5", "*", "1-5", "*/2", "1,3,5")
        min_val: Minimum valid value
        max_val: Maximum valid value

    Returns:
        Set of integer values, or None for wildcard (*).

    Raises:
        ValueError: If field contains invalid values.
    """
    if field == "*":
        return None

    # Step: */N or range/N
    if "/" in field:
        parts = field.split("/", 1)
        step = int(parts[1])
        if step <= 0:
            raise ValueError(f"Step must be positive: {field}")
        if parts[0] == "*":
            return {v for v in range(min_val, max_val + 1, step)}
        elif "-" in parts[0]:
            start, end = parts[0].split("-", 1)
            return {v for v in range(int(start), int(end) + 1, step)}
        else:
            raise ValueError(f"Invalid step field: {field}")

    # Range: N-M
    if "-" in field:
        start, end = field.split("-", 1)
        start_val, end_val = int(start), int(end)
        if start_val < min_val or end_val > max_val or start_val > end_val:
            raise ValueError(f"Invalid range: {field}")
        return set(range(start_val, end_val + 1))

    # List: N,M,P
    if "," in field:
        values = set()
        for part in field.split(","):
            val = int(part)
            if val < min_val or val > max_val:
                raise ValueError(f"Value out of range: {val}")
            values.add(val)
        return values

    # Single value
    val = int(field)
    if val < min_val or val > max_val:
        raise ValueError(f"Value out of range: {val}")
    return {val}


def _cron_weekday_to_python(cron_weekday: int) -> int:
    """Convert cron weekday to Python weekday.

    Cron: 0=Sunday, 1=Monday, ..., 6=Saturday
    Python: 0=Monday, 1=Tuesday, ..., 6=Sunday

    Args:
        cron_weekday: Cron weekday value (0-6)

    Returns:
        Python weekday value (0-6)
    """
    return (cron_weekday + 6) % 7


def validate_cron_expression(expr: str) -> bool:
    """Validate a 5-field cron expression.

    Fields: minute hour day-of-month month weekday
    Supports: exact values, wildcards (*), ranges (1-5),
    lists (1,3,5), step values (*/2).

    Args:
        expr: Cron expression string

    Returns:
        True if valid, False otherwise
    """
    if not expr or not expr.strip():
        return False

    parts = expr.strip().split()
    if len(parts) != 5:
        return False

    # Reject alpha characters (no named days/months)
    if re.search(r"[a-zA-Z]", expr):
        return False

    for part, (name, min_val, max_val) in zip(parts, _CRON_FIELDS):
        try:
            _parse_cron_field(part, min_val, max_val)
        except (ValueError, TypeError):
            return False

    return True


def cron_expr_to_arq_kwargs(expr: str) -> dict:
    """Convert a cron expression to ARQ cron keyword arguments.

    Maps cron fields to ARQ sets. Wildcards become None (ARQ convention).
    CRITICAL: Weekday mapping converts cron convention (0=Sunday)
    to Python convention (0=Monday).

    Args:
        expr: Valid 5-field cron expression

    Returns:
        Dict with keys: minute, hour, day, month, weekday.
        Values are set[int] or None for wildcards.
    """
    parts = expr.strip().split()
    arq_keys = ["minute", "hour", "day", "month", "weekday"]
    result = {}

    for part, key, (_, min_val, max_val) in zip(parts, arq_keys, _CRON_FIELDS):
        parsed = _parse_cron_field(part, min_val, max_val)

        if parsed is not None and key == "weekday":
            # Convert cron weekdays to Python weekdays
            parsed = {_cron_weekday_to_python(d) for d in parsed}

        result[key] = parsed

    return result


def calculate_next_run(
    cron_expr: str,
    timezone: str,
    after: datetime | None = None,
) -> datetime:
    """Calculate the next execution time from a cron expression.

    Pure computation using zoneinfo. Scans forward minute-by-minute
    for simple cases, hour-by-hour for daily/weekly patterns.

    Args:
        cron_expr: Valid 5-field cron expression
        timezone: IANA timezone string (e.g. "UTC", "Europe/Oslo")
        after: Start searching after this time. Uses now(UTC) if None.

    Returns:
        Next execution time as UTC-aware datetime.
    """
    if after is None:
        after = datetime.now(UTC)

    tz = ZoneInfo(timezone)
    parts = cron_expr.strip().split()

    # Parse each field
    parsed_fields = []
    for part, (_, min_val, max_val) in zip(parts, _CRON_FIELDS):
        parsed_fields.append(_parse_cron_field(part, min_val, max_val))

    minute_set, hour_set, day_set, month_set, weekday_set = parsed_fields

    # Convert weekday set to Python convention
    if weekday_set is not None:
        weekday_set = {_cron_weekday_to_python(d) for d in weekday_set}

    # Start from the next minute after 'after' in the target timezone
    local_after = after.astimezone(tz)
    candidate = local_after.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Smart skip: jump past non-matching months/days/hours instead of minute-by-minute
    max_iterations = 366 * 24 * 60  # safety bound
    iterations = 0
    while iterations < max_iterations:
        iterations += 1

        # Month — skip to 1st of next valid month
        if month_set is not None and candidate.month not in month_set:
            if candidate.month == 12:
                candidate = candidate.replace(
                    year=candidate.year + 1, month=1, day=1, hour=0, minute=0,
                )
            else:
                candidate = candidate.replace(
                    month=candidate.month + 1, day=1, hour=0, minute=0,
                )
            continue

        # Day-of-month / weekday — skip to next day
        day_ok = day_set is None or candidate.day in day_set
        weekday_ok = weekday_set is None or candidate.weekday() in weekday_set
        if not day_ok or not weekday_ok:
            candidate = (candidate + timedelta(days=1)).replace(hour=0, minute=0)
            continue

        # Hour — skip to next hour
        if hour_set is not None and candidate.hour not in hour_set:
            candidate = (candidate + timedelta(hours=1)).replace(minute=0)
            continue

        # Minute — advance one minute
        if minute_set is not None and candidate.minute not in minute_set:
            candidate += timedelta(minutes=1)
            continue

        # All fields match
        return candidate.astimezone(UTC)

    # Should never reach here for valid cron expressions
    raise ValueError(f"Could not find next run for '{cron_expr}' within 366 days")


def _matches_cron(
    dt: datetime,
    minute_set: set[int] | None,
    hour_set: set[int] | None,
    day_set: set[int] | None,
    month_set: set[int] | None,
    weekday_set: set[int] | None,
) -> bool:
    """Check if a datetime matches all cron field constraints.

    Args:
        dt: Datetime to check (in local timezone)
        minute_set: Allowed minutes, or None for all
        hour_set: Allowed hours, or None for all
        day_set: Allowed days of month, or None for all
        month_set: Allowed months, or None for all
        weekday_set: Allowed weekdays (Python convention), or None for all

    Returns:
        True if dt matches all constraints.
    """
    if minute_set is not None and dt.minute not in minute_set:
        return False
    if hour_set is not None and dt.hour not in hour_set:
        return False
    if day_set is not None and dt.day not in day_set:
        return False
    if month_set is not None and dt.month not in month_set:
        return False
    if weekday_set is not None and dt.weekday() not in weekday_set:
        return False
    return True


def cron_to_human_readable(expr: str) -> str:
    """Convert a cron expression to human-readable description.

    Args:
        expr: Valid 5-field cron expression

    Returns:
        Human-readable description string.

    Examples:
        "0 5 * * 0" → "Weekly on Sunday at 05:00"
        "0 3 * * *" → "Daily at 03:00"
        "0 * * * *" → "Every hour at :00"
        "* * * * *" → "Every minute"
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return expr

    minute, hour, day, month, weekday = parts

    # Every minute
    if all(p == "*" for p in parts):
        return "Every minute"

    # Step patterns
    if "/" in minute:
        step = minute.split("/")[1]
        return f"Every {step} minutes"

    if "/" in hour:
        step = hour.split("/")[1]
        time_str = f" at :{minute.zfill(2)}" if minute != "*" else ""
        return f"Every {step} hours{time_str}"

    # Build time string
    time_str = ""
    if hour != "*" and minute != "*":
        time_str = f" at {hour.zfill(2)}:{minute.zfill(2)}"
    elif hour != "*":
        time_str = f" at {hour.zfill(2)}:00"
    elif minute != "*":
        time_str = f" at :{minute.zfill(2)}"

    # Every hour
    if hour == "*" and minute != "*":
        return f"Every hour at :{minute.zfill(2)}"

    # Specific weekday
    if weekday != "*" and day == "*" and month == "*":
        if "," in weekday:
            day_names = [_CRON_DAY_NAMES[int(d)] for d in weekday.split(",")]
            return f"Weekly on {', '.join(day_names)}{time_str}"
        elif "-" in weekday:
            start, end = weekday.split("-")
            return f"Weekly {_CRON_DAY_NAMES[int(start)]}-{_CRON_DAY_NAMES[int(end)]}{time_str}"
        else:
            return f"Weekly on {_CRON_DAY_NAMES[int(weekday)]}{time_str}"

    # Daily
    if weekday == "*" and day == "*" and month == "*":
        return f"Daily{time_str}"

    # Specific day of month
    if day != "*":
        return f"Monthly on day {day}{time_str}"

    return f"Cron: {expr}"


__all__ = [
    "validate_cron_expression",
    "cron_expr_to_arq_kwargs",
    "calculate_next_run",
    "cron_to_human_readable",
]
