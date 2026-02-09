"""Tests for ARQ job functions.

Story 4-4, Task 11.6, 11.7: Tests for ARQ job registration and cancellation.

Tests cover:
- schedule_publish_job execution
- cancel_publish_job execution
- enqueue_publish_job helper
- update_publish_job for rescheduling
- WorkerSettings configuration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from core.scheduling.jobs import (
    schedule_publish_job,
    cancel_publish_job,
    get_scheduled_jobs_status,
    enqueue_publish_job,
    update_publish_job,
    WorkerSettings,
)


class MockApprovalItem:
    """Mock ApprovalItem for testing."""

    def __init__(
        self,
        item_id: str,
        status: str = "scheduled",
        scheduled_time: datetime = None,
        arq_job_id: str = None,
    ):
        self.id = item_id
        self.status = status
        self.scheduled_publish_time = scheduled_time or datetime.utcnow() + timedelta(hours=1)
        self.arq_job_id = arq_job_id
        self.updated_at = datetime.utcnow()


class TestSchedulePublishJob:
    """Tests for schedule_publish_job function."""

    @pytest.mark.asyncio
    async def test_returns_published_on_success(self):
        """Test successful publish job execution."""
        item_id = str(uuid4())
        publish_time = datetime.utcnow()
        ctx = {"redis": AsyncMock()}

        with patch("core.scheduling.jobs.get_async_session") as mock_session:
            mock_item = MockApprovalItem(item_id, status="scheduled")

            # Setup mock session context
            session_mock = AsyncMock()
            session_mock.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_item))
            )
            session_mock.commit = AsyncMock()

            mock_session.return_value.__aenter__ = AsyncMock(return_value=session_mock)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("core.scheduling.jobs.ApprovalStatus") as mock_status:
                mock_status.SCHEDULED.value = "scheduled"
                mock_status.PUBLISHED.value = "published"

                result = await schedule_publish_job(ctx, item_id, publish_time)

        # Job returns PUBLISHED status
        assert result == "PUBLISHED"

    @pytest.mark.asyncio
    async def test_returns_item_not_found_when_missing(self):
        """Test job returns ITEM_NOT_FOUND for missing item."""
        item_id = str(uuid4())
        publish_time = datetime.utcnow()
        ctx = {"redis": AsyncMock()}

        with patch("core.scheduling.jobs.get_async_session") as mock_session:
            session_mock = AsyncMock()
            session_mock.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
            )

            mock_session.return_value.__aenter__ = AsyncMock(return_value=session_mock)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await schedule_publish_job(ctx, item_id, publish_time)

        assert result == "ITEM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_returns_invalid_status_when_not_scheduled(self):
        """Test job returns INVALID_STATUS for non-scheduled items."""
        item_id = str(uuid4())
        publish_time = datetime.utcnow()
        ctx = {"redis": AsyncMock()}

        with patch("core.scheduling.jobs.get_async_session") as mock_session:
            mock_item = MockApprovalItem(item_id, status="approved")

            session_mock = AsyncMock()
            session_mock.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_item))
            )

            mock_session.return_value.__aenter__ = AsyncMock(return_value=session_mock)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("core.scheduling.jobs.ApprovalStatus") as mock_status:
                mock_status.SCHEDULED.value = "scheduled"

                result = await schedule_publish_job(ctx, item_id, publish_time)

        assert result == "INVALID_STATUS"


class TestCancelPublishJob:
    """Tests for cancel_publish_job function."""

    @pytest.mark.asyncio
    async def test_cancels_job_successfully(self):
        """Test successful job cancellation."""
        item_id = str(uuid4())
        job_id = "arq:job:12345"
        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}

        with patch("core.scheduling.jobs.Job") as MockJob:
            mock_job = AsyncMock()
            mock_job.abort = AsyncMock()
            MockJob.return_value = mock_job

            result = await cancel_publish_job(ctx, item_id, job_id)

        assert result == "CANCELLED"
        mock_job.abort.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_no_redis_when_unavailable(self):
        """Test returns NO_REDIS when redis not in context."""
        ctx = {}  # No redis

        result = await cancel_publish_job(ctx, "item-1", "job-1")

        assert result == "NO_REDIS"


class TestEnqueuePublishJob:
    """Tests for enqueue_publish_job helper."""

    @pytest.mark.asyncio
    async def test_enqueues_job_with_defer(self):
        """Test that job is enqueued with defer_until."""
        item_id = str(uuid4())
        publish_time = datetime.utcnow() + timedelta(hours=2)
        mock_pool = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "arq:job:67890"
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

        result = await enqueue_publish_job(mock_pool, item_id, publish_time)

        assert result == "arq:job:67890"
        mock_pool.enqueue_job.assert_called_once_with(
            "schedule_publish_job",
            item_id,
            publish_time,
            _defer_until=publish_time,
        )

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self):
        """Test returns None when enqueue fails."""
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(side_effect=Exception("Redis error"))

        result = await enqueue_publish_job(
            mock_pool, "item-1", datetime.utcnow()
        )

        assert result is None


class TestUpdatePublishJob:
    """Tests for update_publish_job function."""

    @pytest.mark.asyncio
    async def test_cancels_old_and_creates_new(self):
        """Test that old job is cancelled and new is created."""
        item_id = str(uuid4())
        old_job_id = "arq:job:old"
        new_time = datetime.utcnow() + timedelta(hours=3)

        mock_pool = AsyncMock()
        mock_new_job = MagicMock()
        mock_new_job.job_id = "arq:job:new"
        mock_pool.enqueue_job = AsyncMock(return_value=mock_new_job)

        with patch("core.scheduling.jobs.Job") as MockJob:
            mock_old_job = AsyncMock()
            mock_old_job.abort = AsyncMock()
            MockJob.return_value = mock_old_job

            result = await update_publish_job(
                mock_pool, item_id, old_job_id, new_time
            )

        assert result == "arq:job:new"
        mock_old_job.abort.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_new_without_old_job(self):
        """Test creates new job when no old job ID."""
        item_id = str(uuid4())
        new_time = datetime.utcnow() + timedelta(hours=3)

        mock_pool = AsyncMock()
        mock_new_job = MagicMock()
        mock_new_job.job_id = "arq:job:new"
        mock_pool.enqueue_job = AsyncMock(return_value=mock_new_job)

        result = await update_publish_job(
            mock_pool, item_id, None, new_time
        )

        assert result == "arq:job:new"


class TestWorkerSettings:
    """Tests for WorkerSettings configuration."""

    def test_functions_are_registered(self):
        """Test that all job functions are registered."""
        assert schedule_publish_job in WorkerSettings.functions
        assert cancel_publish_job in WorkerSettings.functions
        assert get_scheduled_jobs_status in WorkerSettings.functions

    def test_no_cron_jobs_configured(self):
        """Test that no cron jobs are configured (all dynamic)."""
        assert WorkerSettings.cron_jobs == []

    def test_job_timeout_is_reasonable(self):
        """Test job timeout is set to reasonable value."""
        assert WorkerSettings.job_timeout == 300  # 5 minutes

    def test_keep_result_configured(self):
        """Test job results are kept for 1 hour."""
        assert WorkerSettings.keep_result == 3600  # 1 hour

    @pytest.mark.asyncio
    async def test_on_startup_logs_message(self):
        """Test on_startup handler runs without error."""
        ctx = {}
        # Should not raise
        await WorkerSettings.on_startup(ctx)

    @pytest.mark.asyncio
    async def test_on_shutdown_logs_message(self):
        """Test on_shutdown handler runs without error."""
        ctx = {}
        # Should not raise
        await WorkerSettings.on_shutdown(ctx)
