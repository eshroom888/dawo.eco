"""Tests for CalendarClient.

Story 7-9: Google Calendar Sync
Task 2.4: Client tests (target: 15+)
"""

import asyncio
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import CalendarConfig
from integrations.google_calendar.client import CalendarClient
from integrations.google_calendar.credentials_manager import (
    CalendarCredentialsManager,
    CalendarSyncError,
)
from integrations.google_calendar.dtos import CalendarEventData, CalendarSyncResult


def _make_config(**overrides) -> CalendarConfig:
    """Create CalendarConfig with optional overrides."""
    defaults = {
        "calendar_id": "test-calendar-id",
        "calendar_name": "Test Calendar",
    }
    defaults.update(overrides)
    return CalendarConfig(**defaults)


def _make_http_error(status: int) -> Exception:
    """Create a mock HttpError with given status code."""
    from googleapiclient.errors import HttpError

    resp = MagicMock()
    resp.status = status
    return HttpError(resp=resp, content=b"error")


def _make_event_data(**overrides) -> CalendarEventData:
    """Create CalendarEventData for tests."""
    defaults = {
        "title": "Test Post",
        "start_time": datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        "end_time": datetime(2026, 3, 1, 10, 30, tzinfo=timezone.utc),
        "description": "Test description",
        "color_id": "10",
    }
    defaults.update(overrides)
    return CalendarEventData(**defaults)


class TestCalendarEventData:
    """Tests for CalendarEventData DTO."""

    def test_frozen_immutability(self) -> None:
        """CalendarEventData is frozen."""
        event = _make_event_data()
        with pytest.raises(FrozenInstanceError):
            event.title = "Changed"  # type: ignore[misc]

    def test_to_google_event_format(self) -> None:
        """to_google_event produces valid Google API format."""
        event = _make_event_data(
            extended_properties={"post_id": "123", "content_type": "instagram_post"}
        )
        result = event.to_google_event()

        assert result["summary"] == "Test Post"
        assert result["start"]["dateTime"] == event.start_time.isoformat()
        assert result["start"]["timeZone"] == "UTC"
        assert result["end"]["dateTime"] == event.end_time.isoformat()
        assert result["colorId"] == "10"
        assert result["description"] == "Test description"
        assert result["extendedProperties"]["private"]["post_id"] == "123"

    def test_to_google_event_default_end_time(self) -> None:
        """to_google_event uses start + 30 min when end_time is None."""
        start = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
        event = CalendarEventData(title="Test", start_time=start)
        result = event.to_google_event()

        expected_end = start + timedelta(minutes=30)
        assert result["end"]["dateTime"] == expected_end.isoformat()

    def test_to_google_event_no_description(self) -> None:
        """to_google_event omits description when empty."""
        event = CalendarEventData(
            title="Test",
            start_time=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
            description="",
        )
        result = event.to_google_event()
        assert "description" not in result

    def test_to_google_event_no_extended_properties(self) -> None:
        """to_google_event omits extendedProperties when empty."""
        event = CalendarEventData(
            title="Test",
            start_time=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        )
        result = event.to_google_event()
        assert "extendedProperties" not in result


class TestCalendarSyncResult:
    """Tests for CalendarSyncResult DTO."""

    def test_frozen_immutability(self) -> None:
        """CalendarSyncResult is frozen."""
        result = CalendarSyncResult(event_id="abc", status="created")
        with pytest.raises(FrozenInstanceError):
            result.status = "failed"  # type: ignore[misc]

    def test_default_synced_at_is_utc(self) -> None:
        """Default synced_at is UTC."""
        result = CalendarSyncResult()
        assert result.synced_at.tzinfo == timezone.utc

    def test_default_error_message_is_none(self) -> None:
        """Default error_message is None."""
        result = CalendarSyncResult()
        assert result.error_message is None


class TestCalendarClient:
    """Tests for CalendarClient."""

    def _make_client(self, config: CalendarConfig | None = None) -> CalendarClient:
        """Create CalendarClient with mocked credentials manager."""
        cfg = config or _make_config()
        creds_manager = MagicMock(spec=CalendarCredentialsManager)

        # Mock service chain
        mock_service = MagicMock()
        creds_manager.get_service.return_value = mock_service

        client = CalendarClient(creds_manager, cfg)
        client._service = mock_service
        return client

    @pytest.mark.asyncio
    async def test_ensure_calendar_exists_returns_existing_id(self) -> None:
        """ensure_calendar_exists returns existing ID when set and valid."""
        client = self._make_client()
        mock_execute = MagicMock(return_value={"id": "test-calendar-id"})
        client._service.calendars.return_value.get.return_value.execute = mock_execute

        result = await client.ensure_calendar_exists()
        assert result == "test-calendar-id"

    @pytest.mark.asyncio
    async def test_ensure_calendar_creates_when_id_missing(self) -> None:
        """ensure_calendar_exists creates calendar when no ID."""
        config = _make_config(calendar_id="")
        client = self._make_client(config)
        client._calendar_id = None

        mock_execute = MagicMock(return_value={"id": "new-calendar-id"})
        client._service.calendars.return_value.insert.return_value.execute = (
            mock_execute
        )

        result = await client.ensure_calendar_exists()
        assert result == "new-calendar-id"
        assert client._calendar_id == "new-calendar-id"

    @pytest.mark.asyncio
    async def test_ensure_calendar_recreates_on_404(self) -> None:
        """ensure_calendar_exists recreates when existing ID returns 404."""
        client = self._make_client()

        # First call (get) returns 404
        client._service.calendars.return_value.get.return_value.execute.side_effect = (
            _make_http_error(404)
        )
        # Second call (insert) succeeds
        client._service.calendars.return_value.insert.return_value.execute.return_value = {
            "id": "recreated-id"
        }

        result = await client.ensure_calendar_exists()
        assert result == "recreated-id"

    @pytest.mark.asyncio
    async def test_create_event_returns_sync_result(self) -> None:
        """create_event returns CalendarSyncResult with event_id."""
        client = self._make_client()
        event = _make_event_data()

        client._service.events.return_value.insert.return_value.execute.return_value = {
            "id": "event-123"
        }

        result = await client.create_event(event)
        assert result.event_id == "event-123"
        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_create_event_passes_correct_body(self) -> None:
        """create_event passes event body and calendar_id to Google API."""
        client = self._make_client()
        event = _make_event_data()

        mock_insert = client._service.events.return_value.insert
        mock_insert.return_value.execute.return_value = {"id": "event-123"}

        await client.create_event(event)

        mock_insert.assert_called_once_with(
            calendarId="test-calendar-id",
            body=event.to_google_event(),
        )

    @pytest.mark.asyncio
    async def test_create_event_includes_extended_properties(self) -> None:
        """create_event includes extended properties in body."""
        client = self._make_client()
        event = _make_event_data(
            extended_properties={"post_id": "42", "content_type": "instagram_post"}
        )

        mock_insert = client._service.events.return_value.insert
        mock_insert.return_value.execute.return_value = {"id": "event-42"}

        await client.create_event(event)

        body = mock_insert.call_args.kwargs["body"]
        assert body["extendedProperties"]["private"]["post_id"] == "42"

    @pytest.mark.asyncio
    async def test_update_event_uses_patch(self) -> None:
        """update_event uses PATCH not UPDATE."""
        client = self._make_client()
        event = _make_event_data()

        mock_patch = client._service.events.return_value.patch
        mock_patch.return_value.execute.return_value = {}

        result = await client.update_event("event-123", event)

        mock_patch.assert_called_once()
        assert result.status == "updated"
        assert result.event_id == "event-123"

    @pytest.mark.asyncio
    async def test_update_event_handles_404(self) -> None:
        """update_event raises CalendarSyncError on 404."""
        client = self._make_client()
        event = _make_event_data()

        client._service.events.return_value.patch.return_value.execute.side_effect = (
            _make_http_error(404)
        )

        with pytest.raises(CalendarSyncError, match="not found"):
            await client.update_event("missing-id", event)

    @pytest.mark.asyncio
    async def test_delete_event_returns_true(self) -> None:
        """delete_event returns True on success."""
        client = self._make_client()
        client._service.events.return_value.delete.return_value.execute.return_value = (
            None
        )

        result = await client.delete_event("event-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_event_returns_false_on_404(self) -> None:
        """delete_event returns False when event already deleted (404)."""
        client = self._make_client()
        client._service.events.return_value.delete.return_value.execute.side_effect = (
            _make_http_error(404)
        )

        result = await client.delete_event("already-gone")
        assert result is False

    @pytest.mark.asyncio
    async def test_http_error_mapped_to_sync_error(self) -> None:
        """HttpError is mapped to CalendarSyncError."""
        client = self._make_client()
        event = _make_event_data()

        client._service.events.return_value.insert.return_value.execute.side_effect = (
            _make_http_error(500)
        )

        with pytest.raises(CalendarSyncError, match="Failed to create event"):
            await client.create_event(event)

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self) -> None:
        """Context manager sets and clears service."""
        config = _make_config()
        creds_manager = MagicMock(spec=CalendarCredentialsManager)
        mock_service = MagicMock()
        creds_manager.get_service.return_value = mock_service

        client = CalendarClient(creds_manager, config)

        async with client as c:
            assert c._service is not None

        assert client._service is None
