"""Calendar event builder.

Story 7-9: Google Calendar Sync
Task 3.1: EventBuilder — maps approval items to calendar events.

Converts DAWO content items into Google Calendar event data
with proper titles, descriptions, colors, and metadata.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

from core.config import CalendarConfig
from integrations.google_calendar.dtos import CalendarEventData

logger = logging.getLogger(__name__)


@runtime_checkable
class ApprovalItemLike(Protocol):
    """Minimal protocol for approval item fields needed by EventBuilder.

    Enables testability without importing actual ApprovalItem model.
    """

    @property
    def id(self) -> int | str:
        """Item identifier."""
        ...

    @property
    def full_caption(self) -> str:
        """Full caption text."""
        ...

    @property
    def scheduled_publish_time(self) -> datetime | None:
        """Scheduled publish time."""
        ...


class EventBuilder:
    """Builds CalendarEventData from approval items.

    Maps content scheduling/publishing events to Google Calendar format
    with appropriate titles, colors, descriptions, and metadata.

    Attributes:
        _config: Calendar configuration (color_ids, dashboard_base_url, max_title_length)
    """

    def __init__(self, config: CalendarConfig) -> None:
        """Initialize with injected configuration.

        Args:
            config: Calendar configuration
        """
        self._config = config

    def _truncate_title(self, caption: str, reserve: int = 0) -> str:
        """Truncate caption to max_title_length at word boundary.

        Args:
            caption: Full caption text
            reserve: Characters to reserve for prefix (e.g. "✓ " = 2)

        Returns:
            Truncated title string
        """
        max_len = self._config.max_title_length - reserve
        if len(caption) <= max_len:
            return caption

        truncated = caption[:max_len]
        last_space = truncated.rfind(" ")
        if last_space > max_len // 2:
            truncated = truncated[:last_space]

        return truncated.rstrip() + "..."

    def build_scheduled_event(self, item: ApprovalItemLike) -> CalendarEventData:
        """Build calendar event for a scheduled content item.

        Args:
            item: Approval item with scheduled_publish_time

        Returns:
            CalendarEventData with blue color (scheduled)
        """
        title = self._truncate_title(item.full_caption)
        start_time = item.scheduled_publish_time or datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=30)

        caption_preview = item.full_caption[:200]
        if len(item.full_caption) > 200:
            caption_preview += "..."

        description = (
            f"Content scheduled for Instagram\n\n"
            f"Dashboard: {self._config.dashboard_base_url}/content/{item.id}\n\n"
            f"Caption preview: {caption_preview}"
        )

        return CalendarEventData(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            color_id=self._config.color_ids.get("scheduled", "10"),
            extended_properties={
                "post_id": str(item.id),
                "content_type": "instagram_post",
            },
        )

    def build_published_update(
        self, item: ApprovalItemLike, instagram_url: str
    ) -> CalendarEventData:
        """Build calendar event update for a published item.

        Args:
            item: Published approval item
            instagram_url: Instagram permalink

        Returns:
            CalendarEventData with green color (published)
        """
        title = f"✓ {self._truncate_title(item.full_caption, reserve=2)}"
        start_time = item.scheduled_publish_time or datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=30)

        description = (
            f"Published to Instagram\n\n"
            f"Instagram: {instagram_url}\n"
            f"Dashboard: {self._config.dashboard_base_url}/content/{item.id}"
        )

        return CalendarEventData(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            color_id=self._config.color_ids.get("published", "9"),
            extended_properties={
                "post_id": str(item.id),
                "content_type": "instagram_post",
            },
        )

    def build_failed_update(
        self, item: ApprovalItemLike, error: str
    ) -> CalendarEventData:
        """Build calendar event update for a failed publish.

        Args:
            item: Failed approval item
            error: Error message

        Returns:
            CalendarEventData with red color (failed)
        """
        title = f"FAILED: {self._truncate_title(item.full_caption, reserve=8)}"
        start_time = item.scheduled_publish_time or datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=30)

        description = (
            f"Publish FAILED\n\n"
            f"Error: {error}\n\n"
            f"Dashboard: {self._config.dashboard_base_url}/content/{item.id}"
        )

        return CalendarEventData(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            color_id=self._config.color_ids.get("failed", "11"),
            extended_properties={
                "post_id": str(item.id),
                "content_type": "instagram_post",
            },
        )


__all__ = [
    "ApprovalItemLike",
    "EventBuilder",
]
