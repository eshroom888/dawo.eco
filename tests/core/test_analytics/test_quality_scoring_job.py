"""Tests for post-publish quality scoring ARQ job.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 7.4: _run_post_publish_scoring cron job in core/scheduling/jobs.py.

TDD RED phase: Tests written before implementation (already GREEN).
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


def _make_published_item(
    item_id: str | None = None,
    media_id: str = "17890000001",
    published_at: datetime | None = None,
) -> MagicMock:
    """Create a mock published ApprovalItem."""
    item = MagicMock()
    item.id = item_id or str(uuid4())
    item.instagram_post_id = media_id
    item.published_at = published_at or (datetime.now(UTC) - timedelta(days=10))
    item.status = "PUBLISHED"
    return item


# === Task 7.4: _run_post_publish_scoring job registration ===


class TestPostPublishScoringJobRegistration:
    """Task 7.4: Job registered in WorkerSettings."""

    def test_job_function_exists(self) -> None:
        """_run_post_publish_scoring function exists in jobs module."""
        from core.scheduling.jobs import _run_post_publish_scoring

        assert callable(_run_post_publish_scoring)

    def test_registered_in_worker_functions(self) -> None:
        """Job is registered in WorkerSettings.functions."""
        from core.scheduling.jobs import WorkerSettings, _run_post_publish_scoring

        assert _run_post_publish_scoring in WorkerSettings.functions

    def test_cron_schedule_configured(self) -> None:
        """Cron schedule has at least 2 entries (Shopify + quality scoring)."""
        from core.scheduling.jobs import WorkerSettings

        cron_jobs = WorkerSettings.cron_jobs
        assert len(cron_jobs) >= 2

    def test_exported_in_all(self) -> None:
        """Job function is in __all__."""
        from core.scheduling.jobs import __all__

        assert "_run_post_publish_scoring" in __all__


# === Task 7.4: _run_post_publish_scoring execution ===


class TestPostPublishScoringJobExecution:
    """Task 7.4: Job execution error-handling tests.

    Since the job uses lazy imports (inside function body), we test:
    - Error handling returns correct dict shape
    - Graceful degradation on import/runtime errors
    """

    @pytest.mark.asyncio
    async def test_job_handles_exception_gracefully(self) -> None:
        """Job catches unexpected errors and returns error dict."""
        from core.scheduling.jobs import _run_post_publish_scoring

        ctx = {"redis": AsyncMock()}

        # Patch the first lazy import to fail
        with patch.dict("sys.modules", {
            "core.analytics.quality_scoring_service": None,
        }):
            # Force the import inside the function to fail
            result = await _run_post_publish_scoring(ctx)

        assert isinstance(result, dict)
        assert result["scored"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_job_returns_error_dict_on_failure(self) -> None:
        """Job returns error dict with scored=0 and error key on failure."""
        from core.scheduling.jobs import _run_post_publish_scoring

        ctx = {"redis": AsyncMock()}

        # The function will fail on lazy imports (e.g., core.database)
        # in test environment, but should catch and return error dict
        result = await _run_post_publish_scoring(ctx)

        assert isinstance(result, dict)
        assert result["scored"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_job_is_async(self) -> None:
        """Job function is a coroutine function."""
        import inspect
        from core.scheduling.jobs import _run_post_publish_scoring

        assert inspect.iscoroutinefunction(_run_post_publish_scoring)
