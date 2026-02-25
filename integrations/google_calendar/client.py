"""Google Calendar API client.

Story 7-9: Google Calendar Sync
Task 2.2: CalendarClient — async wrapper around Google Calendar API.

All sync Google API calls are wrapped with run_in_executor for async compat.
Uses PATCH (not UPDATE) to avoid clearing unset fields.
"""

import asyncio
import logging
from datetime import datetime, timezone
from types import TracebackType
from typing import Self

from googleapiclient.errors import HttpError

from core.config import CalendarConfig
from integrations.google_calendar.credentials_manager import (
    CalendarCredentialsManager,
    CalendarSyncError,
)
from integrations.google_calendar.dtos import CalendarEventData, CalendarSyncResult

logger = logging.getLogger(__name__)


class CalendarClient:
    """Async Google Calendar API client.

    Wraps synchronous Google Calendar API calls using run_in_executor.
    Manages calendar lifecycle (ensure exists, create/update/delete events).

    Attributes:
        _credentials_manager: OAuth2 credentials manager
        _config: Calendar configuration
        _calendar_id: Cached calendar ID after first lookup
        _service: Cached Google Calendar API service
    """

    def __init__(
        self,
        credentials_manager: CalendarCredentialsManager,
        config: CalendarConfig,
    ) -> None:
        """Initialize with injected dependencies.

        Args:
            credentials_manager: Manages OAuth2 token lifecycle
            config: Calendar configuration
        """
        self._credentials_manager = credentials_manager
        self._config = config
        self._calendar_id: str | None = config.calendar_id or None
        self._service = None

    async def __aenter__(self) -> Self:
        """Enter async context — initialize service."""
        self._service = await asyncio.get_running_loop().run_in_executor(
            None, self._credentials_manager.get_service
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context — cleanup."""
        self._service = None

    def _get_service(self):
        """Get or create the Calendar API service."""
        if self._service is None:
            self._service = self._credentials_manager.get_service()
        return self._service

    async def ensure_calendar_exists(self) -> str:
        """Ensure the dedicated DAWO calendar exists.

        Checks if calendar_id is set and valid. If not, creates a new calendar.
        Result is cached for subsequent calls.

        Returns:
            The calendar ID string

        Raises:
            CalendarSyncError: If calendar creation fails
        """
        if self._calendar_id:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._get_service()
                    .calendars()
                    .get(calendarId=self._calendar_id)
                    .execute(),
                )
                return self._calendar_id
            except HttpError as e:
                if e.resp.status == 404:
                    logger.warning(
                        f"Calendar {self._calendar_id} not found, recreating"
                    )
                    self._calendar_id = None
                else:
                    raise CalendarSyncError(
                        f"Failed to verify calendar: {e}"
                    ) from e

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._get_service()
                .calendars()
                .insert(body={"summary": self._config.calendar_name})
                .execute(),
            )
            self._calendar_id = result["id"]
            logger.info(
                f"Created calendar '{self._config.calendar_name}' "
                f"with ID: {self._calendar_id}"
            )
            return self._calendar_id
        except HttpError as e:
            raise CalendarSyncError(f"Failed to create calendar: {e}") from e

    async def create_event(self, event: CalendarEventData) -> CalendarSyncResult:
        """Create a new calendar event.

        Args:
            event: Event data to create

        Returns:
            CalendarSyncResult with event_id and status

        Raises:
            CalendarSyncError: If event creation fails
        """
        calendar_id = self._calendar_id
        if not calendar_id:
            calendar_id = await self.ensure_calendar_exists()

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._get_service()
                .events()
                .insert(calendarId=calendar_id, body=event.to_google_event())
                .execute(),
            )
            return CalendarSyncResult(
                event_id=result["id"],
                status="created",
                synced_at=datetime.now(timezone.utc),
            )
        except HttpError as e:
            raise CalendarSyncError(f"Failed to create event: {e}") from e

    async def update_event(
        self, event_id: str, updates: CalendarEventData
    ) -> CalendarSyncResult:
        """Update an existing calendar event using PATCH.

        Uses PATCH (not UPDATE) to only modify specified fields.

        Args:
            event_id: Google Calendar event ID
            updates: Updated event data

        Returns:
            CalendarSyncResult with updated status

        Raises:
            CalendarSyncError: If event update fails
        """
        calendar_id = self._calendar_id
        if not calendar_id:
            calendar_id = await self.ensure_calendar_exists()

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._get_service()
                .events()
                .patch(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=updates.to_google_event(),
                )
                .execute(),
            )
            return CalendarSyncResult(
                event_id=event_id,
                status="updated",
                synced_at=datetime.now(timezone.utc),
            )
        except HttpError as e:
            if e.resp.status == 404:
                raise CalendarSyncError(
                    f"Event {event_id} not found (deleted externally)"
                ) from e
            raise CalendarSyncError(f"Failed to update event: {e}") from e

    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event.

        Args:
            event_id: Google Calendar event ID

        Returns:
            True if deleted, False if event was already gone (404)
        """
        calendar_id = self._calendar_id
        if not calendar_id:
            calendar_id = await self.ensure_calendar_exists()

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._get_service()
                .events()
                .delete(calendarId=calendar_id, eventId=event_id)
                .execute(),
            )
            return True
        except HttpError as e:
            if e.resp.status == 404:
                logger.info(f"Event {event_id} already deleted")
                return False
            raise CalendarSyncError(f"Failed to delete event: {e}") from e


__all__ = [
    "CalendarClient",
]
