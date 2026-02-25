"""Integration tests for Google Calendar Sync.

Story 7-9, Task 10.1: End-to-end integration tests covering full sync flows.
Tests the complete pipeline from item events through sync service to calendar API.
Target: 12+ tests.

All tests use mocked Google Calendar API (no real API calls).
"""

import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from integrations.google_calendar.dtos import CalendarEventData, CalendarSyncResult
from integrations.google_calendar.event_builder import EventBuilder
from integrations.google_calendar.sync_service import CalendarSyncService


def _make_config(**overrides):
    """Create a mock CalendarConfig."""
    config = MagicMock()
    config.sync_enabled = overrides.get("sync_enabled", True)
    config.calendar_name = overrides.get("calendar_name", "DAWO Content Schedule")
    config.calendar_id = overrides.get("calendar_id", "cal_test_123")
    config.dashboard_base_url = overrides.get("dashboard_base_url", "http://localhost:3000")
    config.max_title_length = overrides.get("max_title_length", 60)
    config.color_ids = overrides.get("color_ids", {
        "scheduled": "10",
        "published": "9",
        "failed": "11",
    })
    return config


def _make_item(**overrides):
    """Create a mock ApprovalItem-like object."""
    item = MagicMock()
    item.id = overrides.get("id", uuid4())
    item.full_caption = overrides.get("full_caption", "Test eco product post about organic supplements")
    item.scheduled_publish_time = overrides.get(
        "scheduled_publish_time",
        datetime.now(UTC) + timedelta(hours=2),
    )
    item.google_calendar_event_id = overrides.get("google_calendar_event_id", None)
    item.status = overrides.get("status", "approved")
    return item


class TestScheduledItemSyncFlow:
    """E2E: item scheduled → calendar event created → event_id stored."""

    @pytest.mark.asyncio
    async def test_scheduled_item_creates_event(self):
        """Scheduling an item creates a calendar event with blue color."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_123")
        mock_client.create_event = AsyncMock(
            return_value=CalendarSyncResult(
                event_id="evt_new_1",
                status="created",
                synced_at=datetime.now(UTC),
            )
        )

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item()
        result = await service.sync_scheduled(item)

        assert result.event_id == "evt_new_1"
        assert result.status == "created"
        mock_client.create_event.assert_called_once()

        # Verify event data has scheduled color
        call_args = mock_client.create_event.call_args
        event_data = call_args[0][0] if call_args[0] else call_args[1].get("event")
        assert event_data.color_id == "10"  # Blue for scheduled

    @pytest.mark.asyncio
    async def test_scheduled_item_with_existing_event_updates(self):
        """Re-scheduling an already-synced item updates the event."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_123")
        mock_client.update_event = AsyncMock(
            return_value=CalendarSyncResult(
                event_id="evt_existing",
                status="updated",
                synced_at=datetime.now(UTC),
            )
        )

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item(google_calendar_event_id="evt_existing")
        result = await service.sync_scheduled(item)

        assert result.status == "updated"
        mock_client.update_event.assert_called_once()


class TestRescheduleSyncFlow:
    """E2E: item rescheduled → calendar event updated with new time."""

    @pytest.mark.asyncio
    async def test_rescheduled_item_updates_time(self):
        """Rescheduling updates calendar event time."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_123")
        mock_client.update_event = AsyncMock(
            return_value=CalendarSyncResult(
                event_id="evt_resched",
                status="updated",
                synced_at=datetime.now(UTC),
            )
        )

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        new_time = datetime.now(UTC) + timedelta(hours=5)
        item = _make_item(
            google_calendar_event_id="evt_resched",
            scheduled_publish_time=new_time,
        )
        result = await service.sync_rescheduled(item)

        assert result.status == "updated"
        call_args = mock_client.update_event.call_args
        event_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("updates")
        assert event_data.start_time == new_time


class TestPublishedSyncFlow:
    """E2E: item published → event updated with green color + permalink."""

    @pytest.mark.asyncio
    async def test_published_item_updates_to_green(self):
        """Publishing updates event to green color with permalink."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_123")
        mock_client.update_event = AsyncMock(
            return_value=CalendarSyncResult(
                event_id="evt_pub",
                status="updated",
                synced_at=datetime.now(UTC),
            )
        )

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item(google_calendar_event_id="evt_pub")
        result = await service.sync_published(
            item, "https://instagram.com/p/abc123"
        )

        assert result.status == "updated"
        call_args = mock_client.update_event.call_args
        event_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("updates")
        assert event_data.color_id == "9"  # Green for published

    @pytest.mark.asyncio
    async def test_published_item_without_event_creates_new(self):
        """Publishing an unsynced item creates a new event."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_123")
        mock_client.create_event = AsyncMock(
            return_value=CalendarSyncResult(
                event_id="evt_new_pub",
                status="created",
                synced_at=datetime.now(UTC),
            )
        )

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item(google_calendar_event_id=None)
        result = await service.sync_published(
            item, "https://instagram.com/p/xyz789"
        )

        assert result.event_id == "evt_new_pub"
        mock_client.create_event.assert_called_once()


class TestFailedPublishSyncFlow:
    """E2E: item publish failed → event updated with red color."""

    @pytest.mark.asyncio
    async def test_failed_publish_updates_to_red(self):
        """Failed publish marks event red with error message."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_123")
        mock_client.update_event = AsyncMock(
            return_value=CalendarSyncResult(
                event_id="evt_fail",
                status="updated",
                synced_at=datetime.now(UTC),
            )
        )

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item(google_calendar_event_id="evt_fail")
        result = await service.sync_failed(item, "Rate limit exceeded")

        assert result.status == "updated"
        call_args = mock_client.update_event.call_args
        event_data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("updates")
        assert event_data.color_id == "11"  # Red for failed


class TestGracefulDegradation:
    """Graceful degradation: sync failures never block operations."""

    @pytest.mark.asyncio
    async def test_client_error_returns_failed_result(self):
        """Client exception → CalendarSyncResult with failed status, never raises."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(
            side_effect=Exception("Google API down")
        )

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item()
        result = await service.sync_scheduled(item)

        # Service catches exception, returns failed result
        assert result.status == "failed"
        assert result.error_message is not None
        assert "Google API down" in result.error_message

    @pytest.mark.asyncio
    async def test_sync_disabled_returns_immediately(self):
        """sync_enabled=False returns disabled status without calling API."""
        config = _make_config(sync_enabled=False)
        mock_client = AsyncMock()

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item()
        result = await service.sync_scheduled(item)

        assert result.status == "disabled"
        mock_client.ensure_calendar_exists.assert_not_called()
        mock_client.create_event.assert_not_called()


class TestCalendarAutoCreation:
    """Calendar auto-creation: first sync creates calendar if missing."""

    @pytest.mark.asyncio
    async def test_ensure_calendar_called_on_first_sync(self):
        """First sync calls ensure_calendar_exists, subsequent calls use cache."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_auto")
        mock_client.create_event = AsyncMock(
            return_value=CalendarSyncResult(
                event_id="evt_1",
                status="created",
                synced_at=datetime.now(UTC),
            )
        )

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item1 = _make_item()
        item2 = _make_item()

        await service.sync_scheduled(item1)
        await service.sync_scheduled(item2)

        # ensure_calendar_exists called once (cached after first call)
        mock_client.ensure_calendar_exists.assert_called_once()


class TestEventRemoval:
    """Delete event when item is removed."""

    @pytest.mark.asyncio
    async def test_remove_event_deletes_calendar_event(self):
        """Removing an item deletes its calendar event."""
        config = _make_config()
        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_123")
        mock_client.delete_event = AsyncMock(return_value=True)

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item(google_calendar_event_id="evt_to_delete")
        result = await service.remove_event(item)

        assert result is True
        mock_client.delete_event.assert_called_once_with("evt_to_delete")

    @pytest.mark.asyncio
    async def test_remove_event_noop_when_no_event_id(self):
        """Removing an item with no event_id is a no-op."""
        config = _make_config()
        mock_client = AsyncMock()

        builder = EventBuilder(config)
        service = CalendarSyncService(mock_client, builder, config)

        item = _make_item(google_calendar_event_id=None)
        result = await service.remove_event(item)

        assert result is True
        mock_client.delete_event.assert_not_called()


class TestEventBuilderIntegration:
    """EventBuilder produces correct data for different actions."""

    def test_scheduled_event_has_correct_format(self):
        """Scheduled event has title, blue color, dashboard link."""
        config = _make_config()
        builder = EventBuilder(config)

        item = _make_item(full_caption="Amazing organic supplement for wellness")

        event = builder.build_scheduled_event(item)

        assert isinstance(event, CalendarEventData)
        assert event.color_id == "10"  # Blue
        assert "localhost:3000" in event.description
        assert len(event.title) <= 60

    def test_published_event_has_green_color(self):
        """Published event update has green color and permalink."""
        config = _make_config()
        builder = EventBuilder(config)

        item = _make_item()

        event = builder.build_published_update(
            item, "https://instagram.com/p/test123"
        )

        assert event.color_id == "9"  # Green
        assert event.title.startswith("\u2713 ")  # AC3: checkmark prefix
        assert "instagram.com" in event.description

    def test_failed_event_has_red_color(self):
        """Failed event update has red color and error info."""
        config = _make_config()
        builder = EventBuilder(config)

        item = _make_item()

        event = builder.build_failed_update(item, "API timeout")

        assert event.color_id == "11"  # Red
        assert "FAILED" in event.title
        assert "API timeout" in event.description
