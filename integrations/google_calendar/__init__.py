"""Google Calendar integration package.

Story 7-9: Google Calendar Sync

Provides calendar sync capabilities for DAWO content scheduling.
Events are created/updated in a dedicated Google Calendar to give
operators visibility into their posting schedule.
"""

from core.config import CalendarConfig
from integrations.google_calendar.credentials_manager import (
    CalendarAuthError,
    CalendarCredentialsManager,
    CalendarSyncError,
)
from integrations.google_calendar.client import CalendarClient
from integrations.google_calendar.dtos import (
    CalendarEventData,
    CalendarSyncResult,
)
from integrations.google_calendar.event_builder import EventBuilder
from integrations.google_calendar.sync_service import (
    CalendarClientProtocol,
    CalendarSyncService,
)


__all__ = [
    "CalendarAuthError",
    "CalendarClient",
    "CalendarClientProtocol",
    "CalendarConfig",
    "CalendarCredentialsManager",
    "CalendarEventData",
    "CalendarSyncError",
    "CalendarSyncResult",
    "CalendarSyncService",
    "EventBuilder",
]
