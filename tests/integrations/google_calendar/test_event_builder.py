"""Tests for EventBuilder.

Story 7-9: Google Calendar Sync
Task 3.2: Event builder tests (target: 10+)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from core.config import CalendarConfig
from integrations.google_calendar.event_builder import (
    ApprovalItemLike,
    EventBuilder,
)


def _make_config(**overrides) -> CalendarConfig:
    """Create CalendarConfig with defaults."""
    defaults = {
        "dashboard_base_url": "https://dawo.no",
        "max_title_length": 60,
        "color_ids": {"scheduled": "10", "published": "9", "failed": "11"},
    }
    defaults.update(overrides)
    return CalendarConfig(**defaults)


def _make_item(
    item_id: int = 42,
    caption: str = "Short caption",
    publish_time: datetime | None = None,
) -> MagicMock:
    """Create a mock ApprovalItemLike."""
    item = MagicMock()
    item.id = item_id
    item.full_caption = caption
    item.scheduled_publish_time = publish_time or datetime(
        2026, 3, 1, 10, 0, tzinfo=timezone.utc
    )
    return item


class TestEventBuilderTruncation:
    """Tests for title truncation logic."""

    def test_short_title_no_truncation(self) -> None:
        """Titles shorter than max_title_length are not truncated."""
        builder = EventBuilder(_make_config())
        item = _make_item(caption="Short caption")

        event = builder.build_scheduled_event(item)
        assert event.title == "Short caption"

    def test_title_truncation_at_word_boundary(self) -> None:
        """Titles are truncated at word boundary with ellipsis."""
        builder = EventBuilder(_make_config(max_title_length=20))
        item = _make_item(caption="This is a very long caption that exceeds limit")

        event = builder.build_scheduled_event(item)
        assert len(event.title) <= 23  # 20 + "..."
        assert event.title.endswith("...")
        assert " " not in event.title[-4:]  # No trailing space before "..."

    def test_title_truncation_at_exact_max(self) -> None:
        """Title at exactly max_title_length is not truncated."""
        config = _make_config(max_title_length=13)
        builder = EventBuilder(config)
        item = _make_item(caption="Exactly right")

        event = builder.build_scheduled_event(item)
        assert event.title == "Exactly right"


class TestScheduledEvent:
    """Tests for build_scheduled_event."""

    def test_scheduled_event_color_id(self) -> None:
        """Scheduled event has correct color_id (blue=10)."""
        builder = EventBuilder(_make_config())
        item = _make_item()

        event = builder.build_scheduled_event(item)
        assert event.color_id == "10"

    def test_scheduled_event_description_includes_dashboard(self) -> None:
        """Scheduled event description includes dashboard link."""
        builder = EventBuilder(_make_config())
        item = _make_item(item_id=42)

        event = builder.build_scheduled_event(item)
        assert "https://dawo.no/content/42" in event.description

    def test_scheduled_event_extended_properties(self) -> None:
        """Scheduled event includes post_id in extended properties."""
        builder = EventBuilder(_make_config())
        item = _make_item(item_id=99)

        event = builder.build_scheduled_event(item)
        assert event.extended_properties["post_id"] == "99"
        assert event.extended_properties["content_type"] == "instagram_post"

    def test_scheduled_event_time(self) -> None:
        """Scheduled event uses item's scheduled_publish_time."""
        publish_time = datetime(2026, 4, 15, 14, 0, tzinfo=timezone.utc)
        builder = EventBuilder(_make_config())
        item = _make_item(publish_time=publish_time)

        event = builder.build_scheduled_event(item)
        assert event.start_time == publish_time
        assert event.end_time == publish_time + timedelta(minutes=30)


class TestPublishedUpdate:
    """Tests for build_published_update."""

    def test_published_update_green_color(self) -> None:
        """Published update has green color_id (9)."""
        builder = EventBuilder(_make_config())
        item = _make_item()

        event = builder.build_published_update(item, "https://instagram.com/p/abc")
        assert event.color_id == "9"

    def test_published_update_title_prefix(self) -> None:
        """Published update title starts with checkmark (AC3)."""
        builder = EventBuilder(_make_config())
        item = _make_item(caption="Test post")

        event = builder.build_published_update(item, "https://instagram.com/p/abc")
        assert event.title.startswith("\u2713 ")

    def test_published_update_description_includes_permalink(self) -> None:
        """Published update description includes Instagram permalink."""
        builder = EventBuilder(_make_config())
        item = _make_item()

        event = builder.build_published_update(item, "https://instagram.com/p/abc")
        assert "https://instagram.com/p/abc" in event.description


class TestFailedUpdate:
    """Tests for build_failed_update."""

    def test_failed_update_red_color(self) -> None:
        """Failed update has red color_id (11)."""
        builder = EventBuilder(_make_config())
        item = _make_item()

        event = builder.build_failed_update(item, "API timeout")
        assert event.color_id == "11"

    def test_failed_update_title_prefix(self) -> None:
        """Failed update title starts with 'FAILED:'."""
        builder = EventBuilder(_make_config())
        item = _make_item(caption="My post")

        event = builder.build_failed_update(item, "Error")
        assert event.title.startswith("FAILED:")

    def test_failed_update_description_includes_error(self) -> None:
        """Failed update description includes error message."""
        builder = EventBuilder(_make_config())
        item = _make_item()

        event = builder.build_failed_update(item, "Rate limit exceeded")
        assert "Rate limit exceeded" in event.description


class TestToGoogleEventFormat:
    """Tests for to_google_event() from built events."""

    def test_to_google_event_produces_valid_format(self) -> None:
        """Built events produce valid Google Calendar API format."""
        builder = EventBuilder(_make_config())
        item = _make_item()

        event = builder.build_scheduled_event(item)
        google_event = event.to_google_event()

        assert "summary" in google_event
        assert "start" in google_event
        assert "end" in google_event
        assert "dateTime" in google_event["start"]
        assert google_event["start"]["timeZone"] == "UTC"
        assert "colorId" in google_event

    def test_to_google_event_utc_timezone(self) -> None:
        """Event times use UTC timezone."""
        builder = EventBuilder(_make_config())
        item = _make_item()

        event = builder.build_scheduled_event(item)
        google_event = event.to_google_event()

        assert google_event["start"]["timeZone"] == "UTC"
        assert google_event["end"]["timeZone"] == "UTC"
