"""Tests for InstagramMetricsRepository.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 2.5: Write tests for all repository methods.

Uses in-memory mocking of AsyncSession since repository tests
verify query construction and logic, not database integration.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.analytics.models import InstagramMediaMetric, SnapshotLabel
from core.analytics.repository import InstagramMetricsRepository


def _make_metric(
    media_id: str = "17890012345678901",
    snapshot_label: str = "baseline",
    impressions: int = 100,
    reach: int = 80,
    likes: int = 50,
    comments: int = 10,
    saved: int = 5,
    shares: int = 3,
    total_interactions: int = 68,
    collected_at: datetime | None = None,
    plays: int | None = None,
    avg_watch_time_ms: int | None = None,
) -> InstagramMediaMetric:
    """Factory for test InstagramMediaMetric instances."""
    return InstagramMediaMetric(
        id=uuid4(),
        media_id=media_id,
        collected_at=collected_at or datetime.now(UTC),
        snapshot_label=snapshot_label,
        impressions=impressions,
        reach=reach,
        likes=likes,
        comments=comments,
        saved=saved,
        shares=shares,
        total_interactions=total_interactions,
        plays=plays,
        avg_watch_time_ms=avg_watch_time_ms,
    )


class TestInstagramMetricsRepositoryInit:
    """Tests for repository initialization."""

    def test_constructor_accepts_session(self) -> None:
        session = AsyncMock()
        repo = InstagramMetricsRepository(session)
        assert repo._session is session


class TestSaveSnapshot:
    """Tests for save_snapshot method (Task 2.1, 2.3)."""

    @pytest.mark.asyncio
    async def test_save_snapshot_calls_merge(self) -> None:
        """Verify save_snapshot uses merge for upsert behavior."""
        session = AsyncMock()
        session.merge = AsyncMock(return_value=_make_metric())
        repo = InstagramMetricsRepository(session)
        metric = _make_metric()

        result = await repo.save_snapshot(metric)

        session.merge.assert_awaited_once_with(metric)
        session.flush.assert_awaited_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_save_snapshot_returns_merged_metric(self) -> None:
        session = AsyncMock()
        merged = _make_metric(likes=999)
        session.merge = AsyncMock(return_value=merged)
        repo = InstagramMetricsRepository(session)

        result = await repo.save_snapshot(_make_metric())

        assert result.likes == 999


class TestGetByMediaId:
    """Tests for get_by_media_id method (Task 2.2)."""

    @pytest.mark.asyncio
    async def test_get_by_media_id_executes_query(self) -> None:
        session = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [_make_metric()]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        repo = InstagramMetricsRepository(session)
        results = await repo.get_by_media_id("17890012345678901")

        session.execute.assert_awaited_once()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_by_media_id_returns_empty_for_unknown(self) -> None:
        session = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        repo = InstagramMetricsRepository(session)
        results = await repo.get_by_media_id("nonexistent")

        assert results == []


class TestGetLatestSnapshot:
    """Tests for get_latest_snapshot method (Task 2.2)."""

    @pytest.mark.asyncio
    async def test_get_latest_snapshot_returns_one(self) -> None:
        session = AsyncMock()
        expected = _make_metric(snapshot_label="7d")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = expected
        session.execute = AsyncMock(return_value=result_mock)

        repo = InstagramMetricsRepository(session)
        result = await repo.get_latest_snapshot("17890012345678901")

        assert result is expected

    @pytest.mark.asyncio
    async def test_get_latest_snapshot_returns_none_when_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = InstagramMetricsRepository(session)
        result = await repo.get_latest_snapshot("nonexistent")

        assert result is None


class TestGetByMediaIds:
    """Tests for get_by_media_ids batch method (Task 2.4)."""

    @pytest.mark.asyncio
    async def test_batch_query_returns_grouped(self) -> None:
        session = AsyncMock()
        metrics = [
            _make_metric(media_id="post1"),
            _make_metric(media_id="post2"),
        ]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = metrics
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        repo = InstagramMetricsRepository(session)
        results = await repo.get_by_media_ids(["post1", "post2"])

        assert "post1" in results
        assert "post2" in results
        assert len(results["post1"]) == 1
        assert len(results["post2"]) == 1

    @pytest.mark.asyncio
    async def test_batch_query_empty_input_returns_empty(self) -> None:
        session = AsyncMock()
        repo = InstagramMetricsRepository(session)

        results = await repo.get_by_media_ids([])

        assert results == {}
        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_batch_query_single_execute(self) -> None:
        """Verify batch uses single query, not N+1."""
        session = AsyncMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        repo = InstagramMetricsRepository(session)
        await repo.get_by_media_ids(["a", "b", "c"])

        # Single execute call, not 3
        assert session.execute.await_count == 1


class TestGetAverageMetrics:
    """Tests for get_average_metrics method (Task 2.2)."""

    @pytest.mark.asyncio
    async def test_get_average_metrics_returns_dict(self) -> None:
        session = AsyncMock()
        row_mock = MagicMock()
        row_mock._mapping = {
            "avg_impressions": 150.0,
            "avg_reach": 120.0,
            "avg_likes": 60.0,
            "avg_comments": 12.0,
            "avg_saved": 8.0,
            "avg_shares": 4.0,
            "avg_total_interactions": 84.0,
            "post_count": 10,
        }
        result_mock = MagicMock()
        result_mock.one_or_none.return_value = row_mock
        session.execute = AsyncMock(return_value=result_mock)

        repo = InstagramMetricsRepository(session)
        result = await repo.get_average_metrics(days_back=30)

        assert result["avg_impressions"] == 150.0
        assert result["post_count"] == 10

    @pytest.mark.asyncio
    async def test_get_average_metrics_empty_returns_zeros(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = InstagramMetricsRepository(session)
        result = await repo.get_average_metrics()

        assert result["post_count"] == 0
        assert result["avg_impressions"] == 0.0


class TestCommit:
    """Tests for commit method."""

    @pytest.mark.asyncio
    async def test_commit_delegates_to_session(self) -> None:
        session = AsyncMock()
        repo = InstagramMetricsRepository(session)

        await repo.commit()

        session.commit.assert_awaited_once()
