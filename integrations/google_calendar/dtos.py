"""Calendar sync data transfer objects.

Story 7-9: Google Calendar Sync
Task 2.3: DTOs for calendar event data and sync results.

Frozen dataclasses for immutable API contracts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class CalendarEventData:
    """Data for creating or updating a Google Calendar event.

    Attributes:
        title: Event summary/title
        start_time: Event start (UTC)
        end_time: Event end (UTC, default: start + 30 min)
        description: Event description body
        color_id: Google Calendar color ID string
        extended_properties: Private metadata (post_id, content_type)
    """

    title: str
    start_time: datetime
    end_time: datetime | None = None
    description: str = ""
    color_id: str = "10"
    extended_properties: dict[str, str] = field(default_factory=dict)

    def to_google_event(self) -> dict:
        """Convert to Google Calendar API event body.

        Returns:
            Dictionary matching Google Calendar events.insert/patch format
        """
        end = self.end_time or (self.start_time + timedelta(minutes=30))

        event: dict = {
            "summary": self.title,
            "start": {
                "dateTime": self.start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "UTC",
            },
            "colorId": self.color_id,
        }

        if self.description:
            event["description"] = self.description

        if self.extended_properties:
            event["extendedProperties"] = {
                "private": self.extended_properties,
            }

        return event


@dataclass(frozen=True)
class CalendarSyncResult:
    """Result of a calendar sync operation.

    Attributes:
        event_id: Google Calendar event ID (empty on failure)
        status: Operation result ("created", "updated", "deleted", "failed", "disabled")
        synced_at: Timestamp of the sync operation
        error_message: Error details if status is "failed"
    """

    event_id: str = ""
    status: str = "failed"
    synced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str | None = None


__all__ = [
    "CalendarEventData",
    "CalendarSyncResult",
]
