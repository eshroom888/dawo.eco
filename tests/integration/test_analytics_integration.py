"""Integration test for publish -> analytics metrics scheduling flow.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 6.3: Verifies that successful Instagram publish triggers
metrics collection scheduling.

Tests the integration between:
1. core/scheduling/jobs.py (_schedule_post_metrics)
2. core/analytics/jobs.py (schedule_metrics_collection)
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch


class TestSchedulePostMetrics:
    """Tests for the _schedule_post_metrics helper in scheduling jobs."""

    @pytest.mark.asyncio
    async def test_schedules_metrics_with_valid_args(self) -> None:
        """_schedule_post_metrics calls schedule_metrics_collection with correct args."""
        from core.scheduling.jobs import _schedule_post_metrics

        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "metrics-job-1"
        mock_redis.enqueue_job.return_value = mock_job

        ctx = {"redis": mock_redis}
        media_id = "17890123456789"
        published_at = datetime.now(UTC)

        with patch(
            "core.analytics.jobs.schedule_metrics_collection",
            new_callable=AsyncMock,
            return_value=["job-1", "job-2", "job-3", "job-4"],
        ) as mock_schedule:
            await _schedule_post_metrics(ctx, media_id, published_at)

            mock_schedule.assert_called_once_with(
                mock_redis, media_id, published_at
            )

    @pytest.mark.asyncio
    async def test_uses_utc_now_when_published_at_is_none(self) -> None:
        """Falls back to datetime.now(UTC) when published_at is None."""
        from core.scheduling.jobs import _schedule_post_metrics

        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}

        with patch(
            "core.analytics.jobs.schedule_metrics_collection",
            new_callable=AsyncMock,
            return_value=["job-1"],
        ) as mock_schedule:
            await _schedule_post_metrics(ctx, "media_123", None)

            mock_schedule.assert_called_once()
            call_args = mock_schedule.call_args[0]
            # Third arg should be a recent datetime
            assert isinstance(call_args[2], datetime)
            assert (datetime.now(UTC) - call_args[2]) < timedelta(seconds=5)

    @pytest.mark.asyncio
    async def test_skips_when_no_redis_in_context(self) -> None:
        """Skips scheduling when redis is not in context."""
        from core.scheduling.jobs import _schedule_post_metrics

        ctx = {}  # No redis

        with patch(
            "core.analytics.jobs.schedule_metrics_collection",
            new_callable=AsyncMock,
        ) as mock_schedule:
            await _schedule_post_metrics(ctx, "media_123", datetime.now(UTC))

            mock_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_raise_on_schedule_failure(self) -> None:
        """Scheduling failure is caught -- doesn't propagate."""
        from core.scheduling.jobs import _schedule_post_metrics

        ctx = {"redis": AsyncMock()}

        with patch(
            "core.analytics.jobs.schedule_metrics_collection",
            new_callable=AsyncMock,
            side_effect=Exception("Redis connection lost"),
        ):
            # Should not raise
            await _schedule_post_metrics(ctx, "media_123", datetime.now(UTC))


class TestPublishFlowMetricsIntegration:
    """Integration: verifies _schedule_post_metrics is wired into publish flow."""

    def test_schedule_post_metrics_called_in_success_path(self) -> None:
        """Verify _schedule_post_metrics is called in the success branch of schedule_publish_job."""
        import inspect
        from core.scheduling.jobs import schedule_publish_job

        source = inspect.getsource(schedule_publish_job)
        assert "_schedule_post_metrics" in source
        assert "publish_result.instagram_post_id" in source

    def test_schedule_post_metrics_not_in_failure_path(self) -> None:
        """Verify _schedule_post_metrics is NOT called in the failure branch."""
        import inspect
        from core.scheduling.jobs import schedule_publish_job

        source = inspect.getsource(schedule_publish_job)
        # Find the success block (between "publish_result.success:" and "else:")
        success_idx = source.index("if publish_result.success:")
        else_idx = source.index("else:", success_idx)

        success_block = source[success_idx:else_idx]
        failure_block = source[else_idx:]

        assert "_schedule_post_metrics" in success_block
        assert "_schedule_post_metrics" not in failure_block

    @pytest.mark.asyncio
    async def test_end_to_end_schedule_metrics_collection(self) -> None:
        """End-to-end: schedule_metrics_collection enqueues 4 deferred jobs."""
        from core.analytics.jobs import schedule_metrics_collection

        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "job-abc"
        mock_redis.enqueue_job.return_value = mock_job

        published_at = datetime(2026, 2, 20, 14, 0, 0, tzinfo=UTC)

        job_ids = await schedule_metrics_collection(
            mock_redis, "media_999", published_at
        )

        assert len(job_ids) == 4
        assert mock_redis.enqueue_job.call_count == 4

        # Verify deferred times
        calls = mock_redis.enqueue_job.call_args_list
        expected_offsets = [1, 24, 48, 168]
        for i, offset in enumerate(expected_offsets):
            defer_time = calls[i].kwargs["_defer_until"]
            assert defer_time == published_at + timedelta(hours=offset)

        # All calls use collect_single_metrics_job
        for c in calls:
            assert c.args[0] == "collect_single_metrics_job"
            assert c.args[1] == "media_999"
