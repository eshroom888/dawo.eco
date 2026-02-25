"""Tests for cron expression utilities.

Story 7-6, Task 2.2: Cron utility tests covering validation,
ARQ conversion, next-run calculation, and human-readable output.
Target: 30+ tests.
"""

import pytest
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from core.scheduling.cron_utils import (
    validate_cron_expression,
    cron_expr_to_arq_kwargs,
    calculate_next_run,
    cron_to_human_readable,
)


class TestValidateCronExpression:
    """Tests for cron expression validation."""

    def test_valid_simple_weekly(self):
        """Weekly Sunday at 05:00."""
        assert validate_cron_expression("0 5 * * 0") is True

    def test_valid_daily(self):
        """Daily at 03:00."""
        assert validate_cron_expression("0 3 * * *") is True

    def test_valid_every_hour(self):
        """Every hour at :00."""
        assert validate_cron_expression("0 * * * *") is True

    def test_valid_every_minute(self):
        """Every minute."""
        assert validate_cron_expression("* * * * *") is True

    def test_valid_specific_weekday(self):
        """Monday at 07:00."""
        assert validate_cron_expression("0 7 * * 1") is True

    def test_valid_with_range(self):
        """Weekdays (Mon-Fri) at 09:00."""
        assert validate_cron_expression("0 9 * * 1-5") is True

    def test_valid_with_list(self):
        """Monday, Wednesday, Friday at 10:00."""
        assert validate_cron_expression("0 10 * * 1,3,5") is True

    def test_valid_with_step(self):
        """Every 2 hours."""
        assert validate_cron_expression("0 */2 * * *") is True

    def test_valid_complex(self):
        """Every 15 minutes on weekdays."""
        assert validate_cron_expression("*/15 * * * 1-5") is True

    def test_invalid_too_few_fields(self):
        """Only 4 fields is invalid."""
        assert validate_cron_expression("0 5 * *") is False

    def test_invalid_too_many_fields(self):
        """6 fields is invalid (no seconds support)."""
        assert validate_cron_expression("0 0 5 * * 0") is False

    def test_invalid_minute_out_of_range(self):
        """Minute 60 is invalid."""
        assert validate_cron_expression("60 5 * * *") is False

    def test_invalid_hour_out_of_range(self):
        """Hour 24 is invalid."""
        assert validate_cron_expression("0 24 * * *") is False

    def test_invalid_day_of_month_out_of_range(self):
        """Day 32 is invalid."""
        assert validate_cron_expression("0 0 32 * *") is False

    def test_invalid_month_out_of_range(self):
        """Month 13 is invalid."""
        assert validate_cron_expression("0 0 * 13 *") is False

    def test_invalid_weekday_out_of_range(self):
        """Weekday 7 is invalid (0-6 only)."""
        assert validate_cron_expression("0 0 * * 7") is False

    def test_invalid_empty_string(self):
        """Empty string is invalid."""
        assert validate_cron_expression("") is False

    def test_invalid_letters(self):
        """Alpha characters are invalid."""
        assert validate_cron_expression("0 5 * * SUN") is False

    def test_half_past_five_thirty(self):
        """30 5 * * 0 is valid."""
        assert validate_cron_expression("30 5 * * 0") is True


class TestCronExprToArqKwargs:
    """Tests for cron-to-ARQ conversion with weekday mapping."""

    def test_weekly_sunday_5am(self):
        """0 5 * * 0 → minute={0}, hour={5}, weekday={6} (Python Sunday=6)."""
        result = cron_expr_to_arq_kwargs("0 5 * * 0")
        assert result["minute"] == {0}
        assert result["hour"] == {5}
        assert result["weekday"] == {6}  # Cron 0=Sunday → Python 6=Sunday

    def test_weekly_monday_7am(self):
        """0 7 * * 1 → weekday={0} (Python Monday=0)."""
        result = cron_expr_to_arq_kwargs("0 7 * * 1")
        assert result["weekday"] == {0}  # Cron 1=Monday → Python 0=Monday

    def test_daily_3am(self):
        """0 3 * * * → minute={0}, hour={3}, weekday=None."""
        result = cron_expr_to_arq_kwargs("0 3 * * *")
        assert result["minute"] == {0}
        assert result["hour"] == {3}
        assert result["weekday"] is None

    def test_every_hour(self):
        """0 * * * * → minute={0}, hour=None."""
        result = cron_expr_to_arq_kwargs("0 * * * *")
        assert result["minute"] == {0}
        assert result["hour"] is None

    def test_every_minute(self):
        """* * * * * → all None."""
        result = cron_expr_to_arq_kwargs("* * * * *")
        assert result["minute"] is None
        assert result["hour"] is None

    def test_weekday_mapping_all_days(self):
        """Verify full cron→Python weekday mapping: 0→6, 1→0, 2→1, ..., 6→5."""
        # Cron: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
        # Python: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        expected = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
        for cron_day, python_day in expected.items():
            result = cron_expr_to_arq_kwargs(f"0 0 * * {cron_day}")
            assert result["weekday"] == {python_day}, (
                f"Cron weekday {cron_day} should map to Python {python_day}"
            )

    def test_weekday_range(self):
        """1-5 (Mon-Fri in cron) → {0,1,2,3,4} (Mon-Fri in Python)."""
        result = cron_expr_to_arq_kwargs("0 9 * * 1-5")
        assert result["weekday"] == {0, 1, 2, 3, 4}

    def test_weekday_list(self):
        """1,3,5 (Mon,Wed,Fri in cron) → {0,2,4} in Python."""
        result = cron_expr_to_arq_kwargs("0 10 * * 1,3,5")
        assert result["weekday"] == {0, 2, 4}

    def test_step_hours(self):
        """*/2 in hour field → {0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22}."""
        result = cron_expr_to_arq_kwargs("0 */2 * * *")
        assert result["hour"] == {0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22}

    def test_step_minutes(self):
        """*/15 in minute field → {0, 15, 30, 45}."""
        result = cron_expr_to_arq_kwargs("*/15 * * * *")
        assert result["minute"] == {0, 15, 30, 45}

    def test_returns_all_arq_keys(self):
        """Result always has minute, hour, day, month, weekday keys."""
        result = cron_expr_to_arq_kwargs("0 5 * * 0")
        assert "minute" in result
        assert "hour" in result
        assert "day" in result
        assert "month" in result
        assert "weekday" in result

    def test_day_and_month_wildcards(self):
        """Wildcards for day/month → None (ARQ convention)."""
        result = cron_expr_to_arq_kwargs("0 5 * * 0")
        assert result["day"] is None
        assert result["month"] is None

    def test_specific_day_of_month(self):
        """1 0 15 * * → day={15}."""
        result = cron_expr_to_arq_kwargs("0 0 15 * *")
        assert result["day"] == {15}


class TestCalculateNextRun:
    """Tests for next run time calculation."""

    def test_next_run_utc(self):
        """Calculates next run after current time in UTC."""
        after = datetime(2026, 2, 27, 10, 0, 0, tzinfo=UTC)
        # Daily at 03:00 UTC → next is 2026-02-28 03:00
        result = calculate_next_run("0 3 * * *", "UTC", after=after)
        assert result.hour == 3
        assert result.minute == 0
        assert result > after

    def test_next_run_europe_oslo(self):
        """Calculates next run in Europe/Oslo timezone."""
        after = datetime(2026, 2, 27, 10, 0, 0, tzinfo=UTC)
        result = calculate_next_run("0 7 * * 1", "Europe/Oslo", after=after)
        # Monday at 07:00 Oslo time
        assert result > after

    def test_next_run_weekly_sunday(self):
        """Weekly Sunday at 05:00 UTC."""
        # Start from a Wednesday
        after = datetime(2026, 2, 25, 10, 0, 0, tzinfo=UTC)  # Wednesday
        result = calculate_next_run("0 5 * * 0", "UTC", after=after)
        assert result.weekday() == 6  # Python Sunday = 6
        assert result.hour == 5

    def test_next_run_same_day_future_time(self):
        """If scheduled time is later today, returns today."""
        after = datetime(2026, 2, 27, 2, 0, 0, tzinfo=UTC)
        result = calculate_next_run("0 3 * * *", "UTC", after=after)
        assert result.day == 27
        assert result.hour == 3

    def test_next_run_same_day_past_time(self):
        """If scheduled time already passed today, returns tomorrow."""
        after = datetime(2026, 2, 27, 4, 0, 0, tzinfo=UTC)
        result = calculate_next_run("0 3 * * *", "UTC", after=after)
        assert result.day == 28
        assert result.hour == 3

    def test_next_run_returns_utc_aware(self):
        """Result is always UTC-aware datetime."""
        after = datetime(2026, 2, 27, 10, 0, 0, tzinfo=UTC)
        result = calculate_next_run("0 3 * * *", "UTC", after=after)
        assert result.tzinfo is not None

    def test_next_run_none_uses_now(self):
        """When after=None, uses current time."""
        result = calculate_next_run("0 3 * * *", "UTC", after=None)
        assert result > datetime.now(UTC) - timedelta(minutes=1)

    def test_next_run_every_hour(self):
        """Every hour at :00 — next is within 60 minutes."""
        after = datetime(2026, 2, 27, 10, 30, 0, tzinfo=UTC)
        result = calculate_next_run("0 * * * *", "UTC", after=after)
        assert result.hour == 11
        assert result.minute == 0


class TestCronToHumanReadable:
    """Tests for human-readable cron descriptions."""

    def test_weekly_sunday(self):
        """0 5 * * 0 → includes 'Sunday' and '05:00'."""
        result = cron_to_human_readable("0 5 * * 0")
        assert "Sunday" in result
        assert "05:00" in result

    def test_daily(self):
        """0 3 * * * → includes 'Daily' and '03:00'."""
        result = cron_to_human_readable("0 3 * * *")
        assert "Daily" in result or "daily" in result
        assert "03:00" in result

    def test_every_hour(self):
        """0 * * * * → includes 'hour' or 'Every hour'."""
        result = cron_to_human_readable("0 * * * *")
        assert "hour" in result.lower()

    def test_every_minute(self):
        """* * * * * → includes 'minute'."""
        result = cron_to_human_readable("* * * * *")
        assert "minute" in result.lower()

    def test_monday(self):
        """0 7 * * 1 → includes 'Monday'."""
        result = cron_to_human_readable("0 7 * * 1")
        assert "Monday" in result

    def test_step_hours(self):
        """0 */2 * * * → includes '2 hours' or 'every 2'."""
        result = cron_to_human_readable("0 */2 * * *")
        assert "2" in result
