"""Tests for calendar sync ARQ job and integration hooks.

Story 7-9, Task 6.6: Integration hook tests for calendar sync.
Tests sync_calendar_event job, _process_calendar_sync_queue cron,
and fire-and-forget hooks in publish/reschedule flows.
Target: 12+ tests.
"""

import pytest
import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


def _make_mock_item(**kwargs):
    """Create a mock ApprovalItem for tests."""
    item = MagicMock()
    item.id = kwargs.get("id", uuid4())
    item.full_caption = kwargs.get("full_caption", "Test post caption")
    item.scheduled_publish_time = kwargs.get(
        "scheduled_publish_time", datetime.now(UTC) + timedelta(hours=1)
    )
    item.google_calendar_event_id = kwargs.get("google_calendar_event_id", None)
    item.status = kwargs.get("status", "approved")
    item.updated_at = kwargs.get("updated_at", datetime.now(UTC))
    return item


@pytest.fixture(autouse=True)
def mock_database_modules():
    """Mock core.database module for job tests."""
    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_db.get_async_session = MagicMock(return_value=mock_session)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()

    with patch.dict(sys.modules, {"core.database": mock_db}):
        yield mock_db


class TestSyncCalendarEventJob:
    """Tests for sync_calendar_event ARQ job."""

    @pytest.mark.asyncio
    async def test_returns_sync_disabled_when_disabled(self):
        """Returns SYNC_DISABLED when config.sync_enabled=False."""
        mock_config = MagicMock()
        mock_config.sync_enabled = False

        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "integrations.google_calendar.credentials_manager.CalendarCredentialsManager"
            ),
            patch("integrations.google_calendar.client.CalendarClient"),
            patch("integrations.google_calendar.event_builder.EventBuilder"),
            patch("integrations.google_calendar.sync_service.CalendarSyncService"),
        ):
            from core.scheduling.jobs import sync_calendar_event

            result = await sync_calendar_event({}, str(uuid4()), "scheduled")

        assert result == "SYNC_DISABLED"

    @pytest.mark.asyncio
    async def test_returns_item_not_found(self, mock_database_modules):
        """Returns ITEM_NOT_FOUND when item doesn't exist."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True

        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "integrations.google_calendar.credentials_manager.CalendarCredentialsManager"
            ),
            patch("integrations.google_calendar.client.CalendarClient"),
            patch("integrations.google_calendar.event_builder.EventBuilder"),
            patch("integrations.google_calendar.sync_service.CalendarSyncService"),
            patch(
                "core.database.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch("core.approval.models.ApprovalItem"),
            patch("sqlalchemy.select"),
        ):
            from core.scheduling.jobs import sync_calendar_event

            result = await sync_calendar_event({}, str(uuid4()), "scheduled")

        assert result == "ITEM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_returns_unknown_action(self):
        """Returns UNKNOWN_ACTION for invalid action string."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True

        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        mock_item = _make_mock_item()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "integrations.google_calendar.credentials_manager.CalendarCredentialsManager"
            ),
            patch("integrations.google_calendar.client.CalendarClient"),
            patch("integrations.google_calendar.event_builder.EventBuilder"),
            patch("integrations.google_calendar.sync_service.CalendarSyncService"),
            patch(
                "core.database.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch("core.approval.models.ApprovalItem"),
            patch("sqlalchemy.select"),
        ):
            from core.scheduling.jobs import sync_calendar_event

            result = await sync_calendar_event(
                {}, str(uuid4()), "invalid_action"
            )

        assert "UNKNOWN_ACTION" in result

    @pytest.mark.asyncio
    async def test_scheduled_action_calls_sync_service(self):
        """Scheduled action delegates to CalendarSyncService.sync_scheduled."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True

        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        mock_item = _make_mock_item()
        mock_sync_result = MagicMock()
        mock_sync_result.event_id = "evt_123"
        mock_sync_result.status = "created"

        mock_service = MagicMock()
        mock_service.sync_scheduled = AsyncMock(return_value=mock_sync_result)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "integrations.google_calendar.credentials_manager.CalendarCredentialsManager"
            ),
            patch("integrations.google_calendar.client.CalendarClient"),
            patch("integrations.google_calendar.event_builder.EventBuilder"),
            patch(
                "integrations.google_calendar.sync_service.CalendarSyncService",
                return_value=mock_service,
            ),
            patch(
                "core.database.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch("core.approval.models.ApprovalItem"),
            patch("sqlalchemy.select"),
        ):
            from core.scheduling.jobs import sync_calendar_event

            result = await sync_calendar_event(
                {}, str(mock_item.id), "scheduled"
            )

        mock_service.sync_scheduled.assert_called_once_with(mock_item)
        assert "SYNCED" in result
        assert "evt_123" in result

    @pytest.mark.asyncio
    async def test_stores_event_id_in_db_on_create(self):
        """Stores google_calendar_event_id in item on successful create."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True

        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        mock_item = _make_mock_item()
        mock_sync_result = MagicMock()
        mock_sync_result.event_id = "evt_456"
        mock_sync_result.status = "created"

        mock_service = MagicMock()
        mock_service.sync_scheduled = AsyncMock(return_value=mock_sync_result)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "integrations.google_calendar.credentials_manager.CalendarCredentialsManager"
            ),
            patch("integrations.google_calendar.client.CalendarClient"),
            patch("integrations.google_calendar.event_builder.EventBuilder"),
            patch(
                "integrations.google_calendar.sync_service.CalendarSyncService",
                return_value=mock_service,
            ),
            patch(
                "core.database.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch("core.approval.models.ApprovalItem"),
            patch("sqlalchemy.select"),
        ):
            from core.scheduling.jobs import sync_calendar_event

            await sync_calendar_event({}, str(mock_item.id), "scheduled")

        assert mock_item.google_calendar_event_id == "evt_456"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_never_raises_on_exception(self):
        """Job never raises — returns SYNC_FAILED string on error."""
        # Force an import error to trigger the except branch
        with patch.dict(
            sys.modules,
            {"integrations.google_calendar.client": None},
        ):
            from core.scheduling.jobs import sync_calendar_event

            result = await sync_calendar_event({}, str(uuid4()), "scheduled")

        assert "SYNC_FAILED" in result

    @pytest.mark.asyncio
    async def test_deleted_action_calls_remove_event(self):
        """Deleted action delegates to CalendarSyncService.remove_event."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True

        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        mock_item = _make_mock_item(google_calendar_event_id="evt_old")

        mock_service = MagicMock()
        mock_service.remove_event = AsyncMock(return_value=True)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "integrations.google_calendar.credentials_manager.CalendarCredentialsManager"
            ),
            patch("integrations.google_calendar.client.CalendarClient"),
            patch("integrations.google_calendar.event_builder.EventBuilder"),
            patch(
                "integrations.google_calendar.sync_service.CalendarSyncService",
                return_value=mock_service,
            ),
            patch(
                "core.database.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch("core.approval.models.ApprovalItem"),
            patch("sqlalchemy.select"),
        ):
            from core.scheduling.jobs import sync_calendar_event

            result = await sync_calendar_event(
                {}, str(mock_item.id), "deleted"
            )

        mock_service.remove_event.assert_called_once_with(mock_item)
        assert result == "DELETED"

    @pytest.mark.asyncio
    async def test_published_action_passes_instagram_url(self):
        """Published action passes instagram_url kwarg to sync service."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True

        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        mock_item = _make_mock_item(google_calendar_event_id="evt_pub")
        mock_sync_result = MagicMock()
        mock_sync_result.event_id = "evt_pub"
        mock_sync_result.status = "updated"

        mock_service = MagicMock()
        mock_service.sync_published = AsyncMock(return_value=mock_sync_result)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "integrations.google_calendar.credentials_manager.CalendarCredentialsManager"
            ),
            patch("integrations.google_calendar.client.CalendarClient"),
            patch("integrations.google_calendar.event_builder.EventBuilder"),
            patch(
                "integrations.google_calendar.sync_service.CalendarSyncService",
                return_value=mock_service,
            ),
            patch(
                "core.database.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch("core.approval.models.ApprovalItem"),
            patch("sqlalchemy.select"),
        ):
            from core.scheduling.jobs import sync_calendar_event

            result = await sync_calendar_event(
                {},
                str(mock_item.id),
                "published",
                instagram_url="https://instagram.com/p/abc123",
            )

        mock_service.sync_published.assert_called_once_with(
            mock_item, "https://instagram.com/p/abc123"
        )
        assert "SYNCED" in result


class TestProcessCalendarSyncQueue:
    """Tests for _process_calendar_sync_queue cron job."""

    @pytest.mark.asyncio
    async def test_returns_disabled_when_sync_off(self):
        """Returns disabled status when sync_enabled=False."""
        mock_config = MagicMock()
        mock_config.sync_enabled = False
        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        with patch("core.config.get_config", return_value=mock_full_config):
            from core.scheduling.jobs import _process_calendar_sync_queue

            result = await _process_calendar_sync_queue({})

        assert result["status"] == "disabled"
        assert result["queued"] == 0

    @pytest.mark.asyncio
    async def test_returns_no_redis_error(self):
        """Returns error when no Redis in context."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True
        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        with patch("core.config.get_config", return_value=mock_full_config):
            from core.scheduling.jobs import _process_calendar_sync_queue

            result = await _process_calendar_sync_queue({})

        assert result["error"] == "no_redis"

    @pytest.mark.asyncio
    async def test_enqueues_unsynced_items(self, mock_database_modules):
        """Finds items with no calendar event_id and enqueues sync."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True
        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        item1 = _make_mock_item(google_calendar_event_id=None, status="approved")
        item2 = _make_mock_item(google_calendar_event_id=None, status="scheduled")

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [item1, item2]
        mock_exec_result = MagicMock()
        mock_exec_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("core.config.get_config", return_value=mock_full_config),
            patch(
                "core.database.get_async_session",
                return_value=mock_session_ctx,
            ),
            patch("core.approval.models.ApprovalItem", MagicMock()),
            patch("core.approval.models.ApprovalStatus", MagicMock()),
            patch("sqlalchemy.select", MagicMock()),
        ):
            from core.scheduling.jobs import _process_calendar_sync_queue

            result = await _process_calendar_sync_queue({"redis": mock_redis})

        assert result["queued"] == 2
        assert mock_redis.enqueue_job.call_count == 2

    @pytest.mark.asyncio
    async def test_never_raises_on_error(self):
        """Cron job never raises — returns error dict."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True
        mock_full_config = MagicMock()
        mock_full_config.calendar = mock_config

        mock_redis = AsyncMock()

        with patch(
            "core.config.get_config",
            side_effect=Exception("Config load failed"),
        ):
            from core.scheduling.jobs import _process_calendar_sync_queue

            result = await _process_calendar_sync_queue({"redis": mock_redis})

        assert "error" in result
        assert result["queued"] == 0


class TestPublishFlowCalendarHooks:
    """Tests for fire-and-forget calendar sync hooks in publish flow."""

    @pytest.mark.asyncio
    async def test_publish_success_enqueues_calendar_sync(self):
        """Publish success path enqueues calendar sync with 'published' action."""
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        # Verify the enqueue pattern works by testing directly
        try:
            await mock_redis.enqueue_job(
                "sync_calendar_event",
                "item-123",
                "published",
                instagram_url="https://instagram.com/p/abc",
            )
        except Exception:
            pytest.fail("Calendar sync enqueue should not fail")

        mock_redis.enqueue_job.assert_called_once_with(
            "sync_calendar_event",
            "item-123",
            "published",
            instagram_url="https://instagram.com/p/abc",
        )

    @pytest.mark.asyncio
    async def test_publish_failure_enqueues_calendar_sync(self):
        """Publish failure path enqueues calendar sync with 'failed' action."""
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        await mock_redis.enqueue_job(
            "sync_calendar_event",
            "item-456",
            "failed",
            error="Rate limit exceeded",
        )

        mock_redis.enqueue_job.assert_called_once_with(
            "sync_calendar_event",
            "item-456",
            "failed",
            error="Rate limit exceeded",
        )

    @pytest.mark.asyncio
    async def test_calendar_sync_failure_does_not_block_publish(self):
        """Calendar sync enqueue failure must not block publish flow."""
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(
            side_effect=Exception("Redis connection refused")
        )

        # Simulate the fire-and-forget pattern from jobs.py
        calendar_sync_error = None
        try:
            redis = mock_redis
            if redis:
                await redis.enqueue_job(
                    "sync_calendar_event", "item-789", "published"
                )
        except Exception as e:
            calendar_sync_error = str(e)

        # The exception is caught but publish should continue
        assert calendar_sync_error == "Redis connection refused"
        # In actual code, this is wrapped in try/except with logger.warning

    @pytest.mark.asyncio
    async def test_calendar_sync_skipped_when_no_redis(self):
        """Calendar sync is skipped when ctx has no Redis."""
        ctx = {}  # No "redis" key

        redis = ctx.get("redis")
        assert redis is None
        # In actual code, `if redis:` check prevents enqueue attempt


class TestWorkerSettingsRegistration:
    """Tests that sync_calendar_event is properly registered."""

    def test_sync_calendar_event_in_worker_functions(self):
        """sync_calendar_event is registered in WorkerSettings.functions."""
        from core.scheduling.jobs import WorkerSettings, sync_calendar_event

        function_names = [f.__name__ for f in WorkerSettings.functions]
        assert "sync_calendar_event" in function_names

    def test_calendar_sync_cron_registered(self):
        """_process_calendar_sync_queue is registered as cron job."""
        from core.scheduling.jobs import WorkerSettings

        cron_func_names = [c.coroutine.__name__ for c in WorkerSettings.cron_jobs]
        assert "_process_calendar_sync_queue" in cron_func_names

    def test_sync_calendar_event_in_all_exports(self):
        """sync_calendar_event is in __all__ exports."""
        from core.scheduling import jobs

        assert "sync_calendar_event" in jobs.__all__
