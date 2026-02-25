"""Calendar sync service.

Story 7-9: Google Calendar Sync
Task 4.1: CalendarSyncService — orchestrator for calendar sync operations.

All methods are wrapped in try/except — NEVER raises to caller.
Graceful degradation is mandatory per AC5.
"""

import logging
from datetime import datetime, timezone

from core.config import CalendarConfig
from typing import Protocol, runtime_checkable

from integrations.google_calendar.dtos import CalendarEventData, CalendarSyncResult
from integrations.google_calendar.event_builder import ApprovalItemLike, EventBuilder

logger = logging.getLogger(__name__)


@runtime_checkable
class CalendarClientProtocol(Protocol):
    """Protocol for calendar client used by sync service.

    Canonical definition — imported by __init__.py to avoid duplication.
    """

    async def ensure_calendar_exists(self) -> str: ...
    async def create_event(self, event: CalendarEventData) -> CalendarSyncResult: ...
    async def update_event(self, event_id: str, updates: CalendarEventData) -> CalendarSyncResult: ...
    async def delete_event(self, event_id: str) -> bool: ...


class CalendarSyncService:
    """Orchestrates calendar sync operations.

    Routes sync requests to the appropriate CalendarClient method
    via EventBuilder transformations. All methods catch exceptions
    and return CalendarSyncResult with status="failed" — never raises.

    Attributes:
        _client: Calendar API client (Protocol-based for testability)
        _builder: Event builder for mapping items to calendar events
        _config: Calendar configuration
        _calendar_ensured: Whether ensure_calendar_exists has been called
    """

    def __init__(
        self,
        client: CalendarClientProtocol,
        builder: EventBuilder,
        config: CalendarConfig,
    ) -> None:
        """Initialize with injected dependencies.

        Args:
            client: Calendar API client
            builder: Event builder
            config: Calendar configuration
        """
        self._client = client
        self._builder = builder
        self._config = config
        self._calendar_ensured = False

    async def _ensure_calendar(self) -> None:
        """Lazily ensure calendar exists (cached after first call)."""
        if not self._calendar_ensured:
            await self._client.ensure_calendar_exists()
            self._calendar_ensured = True

    async def sync_scheduled(self, item: ApprovalItemLike) -> CalendarSyncResult:
        """Sync a scheduled content item to calendar.

        Creates new event or updates existing one.

        Args:
            item: Approval item with scheduled_publish_time

        Returns:
            CalendarSyncResult (never raises)
        """
        if not self._config.sync_enabled:
            return CalendarSyncResult(
                status="disabled",
                synced_at=datetime.now(timezone.utc),
            )

        try:
            await self._ensure_calendar()
            event_data = self._builder.build_scheduled_event(item)

            event_id = getattr(item, "google_calendar_event_id", None)
            if event_id:
                return await self._client.update_event(event_id, event_data)
            else:
                return await self._client.create_event(event_data)
        except Exception as e:
            logger.warning(f"Calendar sync_scheduled failed for item {item.id}: {e}")
            return CalendarSyncResult(
                status="failed",
                synced_at=datetime.now(timezone.utc),
                error_message=str(e),
            )

    async def sync_published(
        self, item: ApprovalItemLike, instagram_url: str
    ) -> CalendarSyncResult:
        """Sync a published item to calendar.

        Updates existing event or creates new one if never synced.

        Args:
            item: Published approval item
            instagram_url: Instagram permalink

        Returns:
            CalendarSyncResult (never raises)
        """
        if not self._config.sync_enabled:
            return CalendarSyncResult(
                status="disabled",
                synced_at=datetime.now(timezone.utc),
            )

        try:
            await self._ensure_calendar()
            event_data = self._builder.build_published_update(item, instagram_url)

            event_id = getattr(item, "google_calendar_event_id", None)
            if event_id:
                return await self._client.update_event(event_id, event_data)
            else:
                return await self._client.create_event(event_data)
        except Exception as e:
            logger.warning(f"Calendar sync_published failed for item {item.id}: {e}")
            return CalendarSyncResult(
                status="failed",
                synced_at=datetime.now(timezone.utc),
                error_message=str(e),
            )

    async def sync_failed(
        self, item: ApprovalItemLike, error: str
    ) -> CalendarSyncResult:
        """Sync a failed publish to calendar.

        Args:
            item: Failed approval item
            error: Error message

        Returns:
            CalendarSyncResult (never raises)
        """
        if not self._config.sync_enabled:
            return CalendarSyncResult(
                status="disabled",
                synced_at=datetime.now(timezone.utc),
            )

        try:
            await self._ensure_calendar()
            event_data = self._builder.build_failed_update(item, error)

            event_id = getattr(item, "google_calendar_event_id", None)
            if event_id:
                return await self._client.update_event(event_id, event_data)
            else:
                return await self._client.create_event(event_data)
        except Exception as e:
            logger.warning(f"Calendar sync_failed failed for item {item.id}: {e}")
            return CalendarSyncResult(
                status="failed",
                synced_at=datetime.now(timezone.utc),
                error_message=str(e),
            )

    async def sync_rescheduled(self, item: ApprovalItemLike) -> CalendarSyncResult:
        """Sync a rescheduled item (update event time).

        Args:
            item: Rescheduled approval item

        Returns:
            CalendarSyncResult (never raises)
        """
        if not self._config.sync_enabled:
            return CalendarSyncResult(
                status="disabled",
                synced_at=datetime.now(timezone.utc),
            )

        try:
            await self._ensure_calendar()
            event_data = self._builder.build_scheduled_event(item)

            event_id = getattr(item, "google_calendar_event_id", None)
            if event_id:
                return await self._client.update_event(event_id, event_data)
            else:
                return await self._client.create_event(event_data)
        except Exception as e:
            logger.warning(
                f"Calendar sync_rescheduled failed for item {item.id}: {e}"
            )
            return CalendarSyncResult(
                status="failed",
                synced_at=datetime.now(timezone.utc),
                error_message=str(e),
            )

    async def remove_event(self, item: ApprovalItemLike) -> bool:
        """Remove calendar event for an item.

        Args:
            item: Item whose event should be removed

        Returns:
            True if deleted, sync disabled, or no event existed; False on error
        """
        if not self._config.sync_enabled:
            return True

        event_id = getattr(item, "google_calendar_event_id", None)
        if not event_id:
            return True  # Nothing to remove

        try:
            return await self._client.delete_event(event_id)
        except Exception as e:
            logger.warning(f"Calendar remove_event failed for item {item.id}: {e}")
            return False


__all__ = [
    "CalendarClientProtocol",
    "CalendarSyncService",
]
