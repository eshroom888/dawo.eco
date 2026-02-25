"""Tests for Calendar Sync router.

Story 7-9, Task 7.4: Router tests for Google Calendar sync endpoints.
Target: 10+ tests.
"""

import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routers.calendar import get_db_session, router


def _make_app(mock_session: AsyncMock | None = None) -> FastAPI:
    """Create test app with calendar router and mocked DB."""
    app = FastAPI()
    app.include_router(router)

    if mock_session is not None:
        app.dependency_overrides[get_db_session] = lambda: mock_session

    return app


def _make_mock_item(**kwargs):
    """Create mock ApprovalItem."""
    item = MagicMock()
    item.id = kwargs.get("id", uuid4())
    item.google_calendar_event_id = kwargs.get("google_calendar_event_id", None)
    item.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    item.status = kwargs.get("status", "approved")
    return item


class TestGetCalendarStatus:
    """Tests for GET /api/calendar/status."""

    def test_returns_config_when_available(self):
        """Returns calendar config with sync status."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True
        mock_config.calendar_name = "DAWO Content Schedule"
        mock_config.calendar_id = "cal_123"

        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        app = _make_app()
        client = TestClient(app)

        with patch("core.config.get_config", return_value=mock_full_config):
            response = client.get("/api/calendar/status")

        assert response.status_code == 200
        data = response.json()
        assert data["sync_enabled"] is True
        assert data["calendar_name"] == "DAWO Content Schedule"
        assert data["calendar_id"] == "cal_123"

    def test_returns_503_when_not_configured(self):
        """Returns 503 when calendar config is missing."""
        app = _make_app()
        client = TestClient(app)

        with patch(
            "core.config.get_config",
            side_effect=Exception("Config not found"),
        ):
            response = client.get("/api/calendar/status")

        assert response.status_code == 503
        assert "Calendar not configured" in response.json()["detail"]


class TestGetSyncStatus:
    """Tests for GET /api/calendar/sync/{item_id}."""

    def test_returns_synced_status(self):
        """Returns 'synced' when item has event_id."""
        item = _make_mock_item(google_calendar_event_id="evt_abc")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_config = MagicMock()
        mock_config.sync_enabled = True
        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        app = _make_app(mock_session)
        client = TestClient(app)

        with patch("core.config.get_config", return_value=mock_full_config):
            response = client.get(f"/api/calendar/sync/{item.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["sync_status"] == "synced"
        assert data["google_calendar_event_id"] == "evt_abc"

    def test_returns_pending_when_no_event_id(self):
        """Returns 'pending' when item has no event_id."""
        item = _make_mock_item(google_calendar_event_id=None)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_config = MagicMock()
        mock_config.sync_enabled = True
        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        app = _make_app(mock_session)
        client = TestClient(app)

        with patch("core.config.get_config", return_value=mock_full_config):
            response = client.get(f"/api/calendar/sync/{item.id}")

        assert response.status_code == 200
        assert response.json()["sync_status"] == "pending"

    def test_returns_404_for_missing_item(self):
        """Returns 404 when item doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _make_app(mock_session)
        client = TestClient(app)

        response = client.get(f"/api/calendar/sync/{uuid4()}")

        assert response.status_code == 404

    def test_returns_422_for_invalid_uuid(self):
        """Returns 422 for malformed item_id."""
        mock_session = AsyncMock()
        app = _make_app(mock_session)
        client = TestClient(app)

        response = client.get("/api/calendar/sync/not-a-uuid")

        assert response.status_code == 422

    def test_returns_disabled_when_sync_off(self):
        """Returns 'disabled' status when sync_enabled=False."""
        item = _make_mock_item()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_config = MagicMock()
        mock_config.sync_enabled = False
        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        app = _make_app(mock_session)
        client = TestClient(app)

        with patch("core.config.get_config", return_value=mock_full_config):
            response = client.get(f"/api/calendar/sync/{item.id}")

        assert response.status_code == 200
        assert response.json()["sync_status"] == "disabled"


class TestManualSync:
    """Tests for POST /api/calendar/sync."""

    def test_returns_queued_count(self):
        """Returns count of items queued for sync."""
        item_id_1 = str(uuid4())
        item_id_2 = str(uuid4())

        mock_session = AsyncMock()
        mock_result = MagicMock()
        # Return found IDs as rows
        mock_result.all.return_value = [
            (item_id_1,),
            (item_id_2,),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()
        mock_redis.close = AsyncMock()

        app = _make_app(mock_session)
        client = TestClient(app)

        with patch("arq.create_pool", return_value=mock_redis):
            response = client.post(
                "/api/calendar/sync",
                json={"item_ids": [item_id_1, item_id_2]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["queued"] == 2

    def test_returns_400_for_too_many_items(self):
        """Validates max 20 items per request."""
        item_ids = [str(uuid4()) for _ in range(21)]

        mock_session = AsyncMock()
        app = _make_app(mock_session)
        client = TestClient(app)

        response = client.post(
            "/api/calendar/sync",
            json={"item_ids": item_ids},
        )

        assert response.status_code == 422  # Pydantic validation

    def test_returns_404_for_missing_items(self):
        """Returns 404 when items don't exist in DB."""
        item_id = str(uuid4())

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []  # No items found
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _make_app(mock_session)
        client = TestClient(app)

        response = client.post(
            "/api/calendar/sync",
            json={"item_ids": [item_id]},
        )

        assert response.status_code == 404


class TestSetupCalendar:
    """Tests for POST /api/calendar/setup."""

    def test_returns_503_when_not_configured(self):
        """Returns 503 when calendar credentials are missing."""
        app = _make_app()
        client = TestClient(app)

        with patch(
            "core.config.get_config",
            side_effect=Exception("No calendar config"),
        ):
            response = client.post("/api/calendar/setup")

        assert response.status_code == 503

    def test_returns_calendar_id_on_success(self):
        """Returns calendar_id when setup succeeds."""
        mock_config = MagicMock()
        mock_config.calendar_name = "DAWO Content Schedule"
        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        mock_client = AsyncMock()
        mock_client.ensure_calendar_exists = AsyncMock(return_value="cal_new_123")

        app = _make_app()
        client = TestClient(app)

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "integrations.google_calendar.credentials_manager.CalendarCredentialsManager"
            ),
            patch(
                "integrations.google_calendar.client.CalendarClient",
                return_value=mock_client,
            ),
        ):
            response = client.post("/api/calendar/setup")

        assert response.status_code == 200
        data = response.json()
        assert data["calendar_id"] == "cal_new_123"
        assert data["calendar_name"] == "DAWO Content Schedule"


class TestRouterRegistration:
    """Tests for router registration in __init__.py."""

    def test_calendar_router_in_init_exports(self):
        """calendar_router is exported from routers __init__."""
        from ui.backend.routers import __all__ as router_exports

        assert "calendar_router" in router_exports

    def test_calendar_router_importable(self):
        """calendar_router is importable from package."""
        from ui.backend.routers import calendar_router

        assert calendar_router is not None
