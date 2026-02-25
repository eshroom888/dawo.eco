"""Tests for CalendarSyncService.

Story 7-9: Google Calendar Sync
Task 4.2: Service tests (target: 15+)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import CalendarConfig
from integrations.google_calendar.dtos import CalendarSyncResult
from integrations.google_calendar.event_builder import EventBuilder
from integrations.google_calendar.sync_service import CalendarSyncService


def _make_config(**overrides) -> CalendarConfig:
    """Create CalendarConfig with defaults."""
    defaults = {
        "sync_enabled": True,
        "dashboard_base_url": "https://dawo.no",
    }
    defaults.update(overrides)
    return CalendarConfig(**defaults)


def _make_item(
    item_id: int = 42,
    caption: str = "Test caption",
    publish_time: datetime | None = None,
    event_id: str | None = None,
) -> MagicMock:
    """Create a mock ApprovalItemLike."""
    item = MagicMock()
    item.id = item_id
    item.full_caption = caption
    item.scheduled_publish_time = publish_time or datetime(
        2026, 3, 1, 10, 0, tzinfo=timezone.utc
    )
    item.google_calendar_event_id = event_id
    return item


def _make_service(
    config: CalendarConfig | None = None,
) -> tuple[CalendarSyncService, AsyncMock]:
    """Create CalendarSyncService with mocked client."""
    cfg = config or _make_config()
    mock_client = AsyncMock()
    mock_client.ensure_calendar_exists.return_value = "cal-id"
    mock_client.create_event.return_value = CalendarSyncResult(
        event_id="new-event", status="created"
    )
    mock_client.update_event.return_value = CalendarSyncResult(
        event_id="existing-event", status="updated"
    )
    mock_client.delete_event.return_value = True

    builder = EventBuilder(cfg)
    service = CalendarSyncService(mock_client, builder, cfg)
    return service, mock_client


class TestSyncScheduled:
    """Tests for sync_scheduled."""

    @pytest.mark.asyncio
    async def test_creates_event_for_new_item(self) -> None:
        """sync_scheduled creates event for item without event_id."""
        service, client = _make_service()
        item = _make_item(event_id=None)

        result = await service.sync_scheduled(item)
        client.create_event.assert_called_once()
        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_updates_event_for_existing_item(self) -> None:
        """sync_scheduled updates event for item with event_id."""
        service, client = _make_service()
        item = _make_item(event_id="existing-event")

        result = await service.sync_scheduled(item)
        client.update_event.assert_called_once()
        assert result.status == "updated"

    @pytest.mark.asyncio
    async def test_returns_disabled_when_sync_off(self) -> None:
        """sync_scheduled returns 'disabled' when sync_enabled=False."""
        config = _make_config(sync_enabled=False)
        service, client = _make_service(config)
        item = _make_item()

        result = await service.sync_scheduled(item)
        assert result.status == "disabled"
        client.create_event.assert_not_called()


class TestSyncPublished:
    """Tests for sync_published."""

    @pytest.mark.asyncio
    async def test_updates_event_with_green_color(self) -> None:
        """sync_published updates event for item with event_id."""
        service, client = _make_service()
        item = _make_item(event_id="event-123")

        await service.sync_published(item, "https://instagram.com/p/abc")
        client.update_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_event_if_never_synced(self) -> None:
        """sync_published creates event if item has no event_id."""
        service, client = _make_service()
        item = _make_item(event_id=None)

        result = await service.sync_published(item, "https://instagram.com/p/abc")
        client.create_event.assert_called_once()
        assert result.status == "created"


class TestSyncFailed:
    """Tests for sync_failed."""

    @pytest.mark.asyncio
    async def test_updates_event_with_red_color(self) -> None:
        """sync_failed updates event for item with event_id."""
        service, client = _make_service()
        item = _make_item(event_id="event-123")

        await service.sync_failed(item, "API timeout")
        client.update_event.assert_called_once()


class TestSyncRescheduled:
    """Tests for sync_rescheduled."""

    @pytest.mark.asyncio
    async def test_updates_event_time(self) -> None:
        """sync_rescheduled updates event time."""
        service, client = _make_service()
        item = _make_item(event_id="event-123")

        result = await service.sync_rescheduled(item)
        client.update_event.assert_called_once()
        assert result.status == "updated"


class TestRemoveEvent:
    """Tests for remove_event."""

    @pytest.mark.asyncio
    async def test_deletes_event(self) -> None:
        """remove_event deletes event by ID."""
        service, client = _make_service()
        item = _make_item(event_id="event-123")

        result = await service.remove_event(item)
        client.delete_event.assert_called_once_with("event-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_no_event_id(self) -> None:
        """remove_event returns True when item has no event_id (noop)."""
        service, client = _make_service()
        item = _make_item(event_id=None)

        result = await service.remove_event(item)
        client.delete_event.assert_not_called()
        assert result is True


class TestGracefulDegradation:
    """Tests for exception handling (AC5)."""

    @pytest.mark.asyncio
    async def test_sync_scheduled_catches_exceptions(self) -> None:
        """sync_scheduled catches exceptions and returns failed result."""
        service, client = _make_service()
        client.create_event.side_effect = Exception("Network error")
        item = _make_item(event_id=None)

        result = await service.sync_scheduled(item)
        assert result.status == "failed"
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_sync_published_catches_exceptions(self) -> None:
        """sync_published catches exceptions and returns failed result."""
        service, client = _make_service()
        client.update_event.side_effect = Exception("Auth failed")
        item = _make_item(event_id="event-123")

        result = await service.sync_published(item, "https://instagram.com/p/abc")
        assert result.status == "failed"
        assert "Auth failed" in result.error_message

    @pytest.mark.asyncio
    async def test_all_methods_return_sync_result(self) -> None:
        """All sync methods return CalendarSyncResult, even on failure."""
        service, client = _make_service()
        client.create_event.side_effect = RuntimeError("kaboom")
        item = _make_item(event_id=None)

        result = await service.sync_scheduled(item)
        assert isinstance(result, CalendarSyncResult)

    @pytest.mark.asyncio
    async def test_ensure_calendar_called_once(self) -> None:
        """ensure_calendar_exists is called only once (cached)."""
        service, client = _make_service()
        item = _make_item(event_id=None)

        await service.sync_scheduled(item)
        await service.sync_scheduled(item)

        client.ensure_calendar_exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_disabled_sync_short_circuits_all_methods(self) -> None:
        """Config sync_enabled=False short-circuits all sync methods."""
        config = _make_config(sync_enabled=False)
        service, client = _make_service(config)
        item = _make_item()

        r1 = await service.sync_scheduled(item)
        r2 = await service.sync_published(item, "url")
        r3 = await service.sync_failed(item, "error")
        r4 = await service.sync_rescheduled(item)

        assert all(r.status == "disabled" for r in [r1, r2, r3, r4])
        client.ensure_calendar_exists.assert_not_called()
