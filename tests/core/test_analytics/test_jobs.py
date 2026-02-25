"""Tests for analytics ARQ job functions.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 5: ARQ scheduling jobs.

TDD RED phase: Tests written before implementation.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# --- Fixtures ---


def _make_published_item(
    media_id: str = "17890000001",
    published_at: datetime | None = None,
    item_id: str | None = None,
) -> MagicMock:
    """Create a mock published ApprovalItem."""
    item = MagicMock()
    item.id = item_id or str(uuid4())
    item.instagram_post_id = media_id
    item.published_at = published_at or datetime.now(UTC) - timedelta(hours=2)
    item.status = "PUBLISHED"
    return item


def _make_mock_collector(
    batch_succeeded: int = 3,
    batch_failed: int = 0,
    batch_errors: dict | None = None,
) -> AsyncMock:
    """Create a mock InstagramMetricsCollector."""
    from core.analytics.metrics_collector import BatchCollectionResult, CollectionResult

    collector = AsyncMock()
    collector.collect_batch.return_value = BatchCollectionResult(
        total=batch_succeeded + batch_failed,
        succeeded=batch_succeeded,
        failed=batch_failed,
        errors=batch_errors or {},
    )
    collector.collect_metrics.return_value = CollectionResult(
        success=True,
        media_id="17890000001",
        snapshot_label="baseline",
    )
    return collector


# === Task 5.1: Module structure ===


class TestJobModuleStructure:
    """Task 5.1: Core analytics/jobs.py module exists with expected exports."""

    def test_module_importable(self) -> None:
        """jobs.py module can be imported."""
        from core.analytics import jobs

        assert jobs is not None

    def test_collect_metrics_job_exists(self) -> None:
        """collect_metrics_job function exists."""
        from core.analytics.jobs import collect_metrics_job

        assert callable(collect_metrics_job)

    def test_schedule_metrics_collection_exists(self) -> None:
        """schedule_metrics_collection function exists."""
        from core.analytics.jobs import schedule_metrics_collection

        assert callable(schedule_metrics_collection)

    def test_collect_single_metrics_job_exists(self) -> None:
        """collect_single_metrics_job function exists (called by deferred jobs)."""
        from core.analytics.jobs import collect_single_metrics_job

        assert callable(collect_single_metrics_job)

    def test_analytics_job_settings_exists(self) -> None:
        """ANALYTICS_JOB_SETTINGS dict exists."""
        from core.analytics.jobs import ANALYTICS_JOB_SETTINGS

        assert isinstance(ANALYTICS_JOB_SETTINGS, dict)
        assert "cron_jobs" in ANALYTICS_JOB_SETTINGS
        assert "functions" in ANALYTICS_JOB_SETTINGS

    def test_module_all_exports(self) -> None:
        """__all__ exports all public names."""
        from core.analytics.jobs import __all__

        expected = {
            "collect_metrics_job",
            "collect_single_metrics_job",
            "schedule_metrics_collection",
            "ANALYTICS_JOB_SETTINGS",
        }
        assert set(__all__) == expected


# === Task 5.2: collect_metrics_job ===


class TestCollectMetricsJob:
    """Task 5.2: Cron job that finds pending posts and collects metrics."""

    @pytest.mark.asyncio
    async def test_collect_metrics_job_finds_pending_posts(self) -> None:
        """Job queries published posts that need metrics at given snapshot_label."""
        from core.analytics.jobs import collect_metrics_job

        # Mock published items (>1h old, no baseline metric yet)
        items = [
            _make_published_item("media_1"),
            _make_published_item("media_2"),
            _make_published_item("media_3"),
        ]
        mock_collector = _make_mock_collector(batch_succeeded=3)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = items
        mock_session.execute.return_value = mock_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session

        # Mock existing metrics (none exist yet)
        mock_repo = AsyncMock()
        mock_repo.get_by_media_ids.return_value = {}

        ctx = {"redis": AsyncMock()}

        with (
            patch("core.analytics.jobs._get_session", return_value=mock_cm),
            patch("core.analytics.jobs._build_collector", return_value=(mock_collector, mock_repo)),
        ):
            result = await collect_metrics_job(ctx, "baseline")

        assert "COLLECTED" in result
        mock_collector.collect_batch.assert_called_once()
        call_args = mock_collector.collect_batch.call_args
        assert len(call_args[1]["media_ids"]) == 3 or len(call_args[0][0]) == 3

    @pytest.mark.asyncio
    async def test_collect_metrics_job_skips_already_collected(self) -> None:
        """Job skips posts that already have metrics for the given snapshot_label."""
        from core.analytics.jobs import collect_metrics_job

        items = [
            _make_published_item("media_1"),
            _make_published_item("media_2"),
        ]
        mock_collector = _make_mock_collector(batch_succeeded=1)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = items
        mock_session.execute.return_value = mock_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session

        # media_1 already has baseline metric
        mock_metric = MagicMock()
        mock_metric.snapshot_label = "baseline"
        mock_repo = AsyncMock()
        mock_repo.get_by_media_ids.return_value = {"media_1": [mock_metric]}

        ctx = {"redis": AsyncMock()}

        with (
            patch("core.analytics.jobs._get_session", return_value=mock_cm),
            patch("core.analytics.jobs._build_collector", return_value=(mock_collector, mock_repo)),
        ):
            result = await collect_metrics_job(ctx, "baseline")

        # Should only collect for media_2
        call_args = mock_collector.collect_batch.call_args
        media_ids = call_args[1].get("media_ids") or call_args[0][0]
        assert "media_2" in media_ids
        assert "media_1" not in media_ids

    @pytest.mark.asyncio
    async def test_collect_metrics_job_skips_too_recent_posts(self) -> None:
        """Job skips posts that haven't reached the required delay for snapshot_label."""
        from core.analytics.jobs import collect_metrics_job

        # Post published 30 min ago (not yet 1h for baseline)
        recent_item = _make_published_item(
            "media_recent",
            published_at=datetime.now(UTC) - timedelta(minutes=30),
        )
        # Post published 2h ago (ready for baseline)
        old_item = _make_published_item(
            "media_old",
            published_at=datetime.now(UTC) - timedelta(hours=2),
        )

        mock_collector = _make_mock_collector(batch_succeeded=1)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [recent_item, old_item]
        mock_session.execute.return_value = mock_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session

        mock_repo = AsyncMock()
        mock_repo.get_by_media_ids.return_value = {}

        ctx = {"redis": AsyncMock()}

        with (
            patch("core.analytics.jobs._get_session", return_value=mock_cm),
            patch("core.analytics.jobs._build_collector", return_value=(mock_collector, mock_repo)),
        ):
            result = await collect_metrics_job(ctx, "baseline")

        call_args = mock_collector.collect_batch.call_args
        media_ids = call_args[1].get("media_ids") or call_args[0][0]
        assert "media_old" in media_ids
        assert "media_recent" not in media_ids

    @pytest.mark.asyncio
    async def test_collect_metrics_job_no_pending_posts(self) -> None:
        """Job returns NO_WORK when no posts need collection."""
        from core.analytics.jobs import collect_metrics_job

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session

        mock_repo = AsyncMock()
        mock_repo.get_by_media_ids.return_value = {}

        ctx = {"redis": AsyncMock()}

        with (
            patch("core.analytics.jobs._get_session", return_value=mock_cm),
            patch("core.analytics.jobs._build_collector", return_value=(AsyncMock(), mock_repo)),
        ):
            result = await collect_metrics_job(ctx, "baseline")

        assert result == "NO_WORK"


# === Task 5.3: Cron schedule ===


class TestCronSchedule:
    """Task 5.3: Cron schedule for metrics collection."""

    def test_cron_jobs_defined(self) -> None:
        """ANALYTICS_JOB_SETTINGS has cron_jobs configured."""
        from core.analytics.jobs import ANALYTICS_JOB_SETTINGS

        cron_jobs = ANALYTICS_JOB_SETTINGS["cron_jobs"]
        assert len(cron_jobs) >= 1

    def test_baseline_check_runs_hourly(self) -> None:
        """Baseline collection check runs hourly."""
        from core.analytics.jobs import ANALYTICS_JOB_SETTINGS

        cron_jobs = ANALYTICS_JOB_SETTINGS["cron_jobs"]
        baseline_job = next(
            (j for j in cron_jobs if j["name"] == "collect_baseline_metrics"),
            None,
        )
        assert baseline_job is not None
        assert baseline_job["minute"] == {0}  # Top of every hour


# === Task 5.4: schedule_metrics_collection ===


class TestScheduleMetricsCollection:
    """Task 5.4: Enqueue deferred jobs at T+1h, T+24h, T+48h, T+7d."""

    @pytest.mark.asyncio
    async def test_enqueues_four_deferred_jobs(self) -> None:
        """Enqueues 4 deferred collection jobs for all intervals."""
        from core.analytics.jobs import schedule_metrics_collection

        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        mock_redis.enqueue_job.return_value = mock_job

        published_at = datetime.now(UTC)

        result = await schedule_metrics_collection(
            mock_redis, "media_123", published_at
        )

        # Should enqueue 4 jobs (baseline/1h, 24h, 48h, 7d)
        assert mock_redis.enqueue_job.call_count == 4
        assert result is not None
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_deferred_times_are_correct(self) -> None:
        """Each job is deferred to the correct time offset."""
        from core.analytics.jobs import schedule_metrics_collection

        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        mock_redis.enqueue_job.return_value = mock_job

        published_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=UTC)

        await schedule_metrics_collection(mock_redis, "media_123", published_at)

        # Verify _defer_until times
        calls = mock_redis.enqueue_job.call_args_list
        defer_times = [c.kwargs["_defer_until"] for c in calls]

        expected_offsets = [1, 24, 48, 168]  # hours
        for offset, defer_time in zip(expected_offsets, defer_times):
            expected = published_at + timedelta(hours=offset)
            assert defer_time == expected, (
                f"Expected defer at +{offset}h ({expected}), got {defer_time}"
            )

    @pytest.mark.asyncio
    async def test_deferred_jobs_call_correct_function(self) -> None:
        """All deferred jobs call collect_single_metrics_job."""
        from core.analytics.jobs import schedule_metrics_collection

        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        mock_redis.enqueue_job.return_value = mock_job

        await schedule_metrics_collection(
            mock_redis, "media_123", datetime.now(UTC)
        )

        for c in mock_redis.enqueue_job.call_args_list:
            assert c.args[0] == "collect_single_metrics_job"

    @pytest.mark.asyncio
    async def test_handles_enqueue_failure(self) -> None:
        """Returns partial results when some enqueues fail."""
        from core.analytics.jobs import schedule_metrics_collection

        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        # First call succeeds, rest fail
        mock_redis.enqueue_job.side_effect = [
            mock_job,
            Exception("Redis error"),
            mock_job,
            Exception("Redis error"),
        ]

        result = await schedule_metrics_collection(
            mock_redis, "media_123", datetime.now(UTC)
        )

        # Should still return results for successful enqueues
        assert result is not None
        assert len(result) == 2  # 2 out of 4 succeeded


# === Task 5.4 (sub): collect_single_metrics_job ===


class TestCollectSingleMetricsJob:
    """Tests for the single-post collection job called by deferred jobs."""

    @pytest.mark.asyncio
    async def test_collect_single_success(self) -> None:
        """Collects metrics for a single media_id + snapshot_label."""
        from core.analytics.jobs import collect_single_metrics_job
        from core.analytics.metrics_collector import CollectionResult

        mock_collector = AsyncMock()
        mock_collector.collect_metrics.return_value = CollectionResult(
            success=True,
            media_id="media_123",
            snapshot_label="baseline",
        )
        mock_repo = AsyncMock()

        ctx = {"redis": AsyncMock()}

        with (
            patch("core.analytics.jobs._get_session", return_value=AsyncMock()),
            patch(
                "core.analytics.jobs._build_collector",
                return_value=(mock_collector, mock_repo),
            ),
        ):
            result = await collect_single_metrics_job(ctx, "media_123", "baseline")

        assert result == "COLLECTED"
        mock_collector.collect_metrics.assert_called_once_with(
            media_id="media_123",
            snapshot_label="baseline",
        )
        mock_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_single_failure_sends_discord(self) -> None:
        """Failed collection sends Discord alert."""
        from core.analytics.jobs import collect_single_metrics_job
        from core.analytics.metrics_collector import CollectionResult

        mock_collector = AsyncMock()
        mock_collector.collect_metrics.return_value = CollectionResult(
            success=False,
            media_id="media_123",
            snapshot_label="baseline",
            error_message="API rate limit exceeded",
        )

        ctx = {"redis": AsyncMock()}

        with (
            patch("core.analytics.jobs._get_session", return_value=AsyncMock()),
            patch(
                "core.analytics.jobs._build_collector",
                return_value=(mock_collector, AsyncMock()),
            ),
            patch(
                "core.analytics.jobs._send_analytics_discord_alert"
            ) as mock_discord,
        ):
            result = await collect_single_metrics_job(ctx, "media_123", "baseline")

        assert result == "FAILED"
        mock_discord.assert_called_once()


# === Task 5.5: Worker settings ===


class TestAnalyticsWorkerSettings:
    """Task 5.5: ANALYTICS_JOB_SETTINGS registration."""

    def test_functions_registered(self) -> None:
        """All job functions are registered in ANALYTICS_JOB_SETTINGS."""
        from core.analytics.jobs import (
            ANALYTICS_JOB_SETTINGS,
            collect_metrics_job,
            collect_single_metrics_job,
        )

        functions = ANALYTICS_JOB_SETTINGS["functions"]
        assert collect_metrics_job in functions
        assert collect_single_metrics_job in functions

    def test_cron_jobs_have_required_fields(self) -> None:
        """Each cron job has name, coroutine, and schedule fields."""
        from core.analytics.jobs import ANALYTICS_JOB_SETTINGS

        for job in ANALYTICS_JOB_SETTINGS["cron_jobs"]:
            assert "name" in job
            assert "coroutine" in job
            assert "minute" in job


# === Task 5.6: Discord notification ===


class TestDiscordAlerts:
    """Task 5.6: Discord notification on collection failure."""

    @pytest.mark.asyncio
    async def test_send_analytics_discord_alert(self) -> None:
        """_send_analytics_discord_alert sends formatted message."""
        from core.analytics.jobs import _send_analytics_discord_alert

        mock_client = AsyncMock()
        mock_discord_cls = MagicMock()
        mock_discord_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_discord_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("core.analytics.jobs.os") as mock_os,
            patch.dict("sys.modules", {"integrations.discord": MagicMock(DiscordWebhookClient=mock_discord_cls)}),
        ):
            mock_os.environ.get.return_value = "https://discord.webhook/url"

            await _send_analytics_discord_alert(
                media_id="media_123",
                snapshot_label="baseline",
                error="API error: rate limited",
            )

            mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_discord_alert_skips_when_no_webhook(self) -> None:
        """Skips alert when discord webhook URL is not configured."""
        from core.analytics.jobs import _send_analytics_discord_alert

        with patch("core.analytics.jobs.os") as mock_os:
            mock_os.environ.get.return_value = ""

            # Should not raise, just skip
            await _send_analytics_discord_alert(
                media_id="media_123",
                snapshot_label="baseline",
                error="API error",
            )
