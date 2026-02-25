"""Tests for MetricsQueryService.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 8: Metrics query API.

TDD RED phase: Tests written before implementation.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from core.analytics.models import InstagramMediaMetric


# --- Fixtures ---


def _make_metric(
    media_id: str = "17890000001",
    snapshot_label: str = "baseline",
    impressions: int = 100,
    reach: int = 80,
    likes: int = 10,
    comments: int = 2,
    saved: int = 3,
    shares: int = 1,
    total_interactions: int = 16,
    plays: int | None = None,
    avg_watch_time_ms: int | None = None,
) -> InstagramMediaMetric:
    """Create a test InstagramMediaMetric."""
    return InstagramMediaMetric(
        id=uuid4(),
        media_id=media_id,
        collected_at=datetime.now(UTC),
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


# === Task 8.1: Module structure ===


class TestMetricsQueryModuleStructure:
    """Task 8.1: MetricsQueryService module exists."""

    def test_module_importable(self) -> None:
        """metrics_query.py module can be imported."""
        from core.analytics import metrics_query

        assert metrics_query is not None

    def test_service_class_exists(self) -> None:
        """MetricsQueryService class exists."""
        from core.analytics.metrics_query import MetricsQueryService

        assert MetricsQueryService is not None

    def test_result_dataclasses_exist(self) -> None:
        """Result dataclasses exist."""
        from core.analytics.metrics_query import (
            PostMetricsResult,
            MetricsDelta,
            AverageMetrics,
            PerformanceComparison,
        )

        assert PostMetricsResult is not None
        assert MetricsDelta is not None
        assert AverageMetrics is not None
        assert PerformanceComparison is not None

    def test_module_all_exports(self) -> None:
        """__all__ exports all public names."""
        from core.analytics.metrics_query import __all__

        expected = {
            "MetricsQueryService",
            "PostMetricsResult",
            "MetricsDelta",
            "AverageMetrics",
            "PerformanceComparison",
        }
        assert set(__all__) == expected


# === Task 8.2: get_post_metrics ===


class TestGetPostMetrics:
    """Task 8.2: get_post_metrics returns all snapshots + computed deltas."""

    @pytest.mark.asyncio
    async def test_returns_all_snapshots(self) -> None:
        """Returns all snapshots for a media_id."""
        from core.analytics.metrics_query import MetricsQueryService

        snapshots = [
            _make_metric(snapshot_label="baseline", impressions=100, likes=10),
            _make_metric(snapshot_label="24h", impressions=250, likes=30),
            _make_metric(snapshot_label="48h", impressions=400, likes=45),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_by_media_id.return_value = snapshots

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_post_metrics("media_123")

        assert result.media_id == "media_123"
        assert len(result.snapshots) == 3
        mock_repo.get_by_media_id.assert_called_once_with("media_123")

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_post(self) -> None:
        """Returns empty result for a post with no metrics."""
        from core.analytics.metrics_query import MetricsQueryService

        mock_repo = AsyncMock()
        mock_repo.get_by_media_id.return_value = []

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_post_metrics("unknown_media")

        assert result.media_id == "unknown_media"
        assert len(result.snapshots) == 0
        assert len(result.deltas) == 0


# === Task 8.3: Delta computation ===


class TestDeltaComputation:
    """Task 8.3: Delta computation between consecutive snapshots."""

    @pytest.mark.asyncio
    async def test_computes_deltas_between_snapshots(self) -> None:
        """Deltas are computed as diff between consecutive snapshots."""
        from core.analytics.metrics_query import MetricsQueryService

        snapshots = [
            _make_metric(
                snapshot_label="baseline",
                impressions=100,
                reach=80,
                likes=10,
                comments=2,
                saved=3,
                shares=1,
                total_interactions=16,
            ),
            _make_metric(
                snapshot_label="24h",
                impressions=250,
                reach=200,
                likes=30,
                comments=5,
                saved=8,
                shares=3,
                total_interactions=46,
            ),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_by_media_id.return_value = snapshots

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_post_metrics("media_123")

        assert len(result.deltas) == 1
        delta = result.deltas[0]
        assert delta.from_label == "baseline"
        assert delta.to_label == "24h"
        assert delta.impressions == 150  # 250 - 100
        assert delta.reach == 120  # 200 - 80
        assert delta.likes == 20  # 30 - 10
        assert delta.comments == 3  # 5 - 2
        assert delta.saved == 5  # 8 - 3
        assert delta.shares == 2  # 3 - 1
        assert delta.total_interactions == 30  # 46 - 16

    @pytest.mark.asyncio
    async def test_computes_multiple_deltas(self) -> None:
        """Multiple deltas for 3+ snapshots."""
        from core.analytics.metrics_query import MetricsQueryService

        snapshots = [
            _make_metric(snapshot_label="baseline", impressions=100, likes=10),
            _make_metric(snapshot_label="24h", impressions=250, likes=30),
            _make_metric(snapshot_label="48h", impressions=400, likes=45),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_by_media_id.return_value = snapshots

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_post_metrics("media_123")

        assert len(result.deltas) == 2
        assert result.deltas[0].from_label == "baseline"
        assert result.deltas[0].to_label == "24h"
        assert result.deltas[0].impressions == 150
        assert result.deltas[1].from_label == "24h"
        assert result.deltas[1].to_label == "48h"
        assert result.deltas[1].impressions == 150

    @pytest.mark.asyncio
    async def test_no_deltas_for_single_snapshot(self) -> None:
        """No deltas when only one snapshot exists."""
        from core.analytics.metrics_query import MetricsQueryService

        snapshots = [
            _make_metric(snapshot_label="baseline", impressions=100),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_by_media_id.return_value = snapshots

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_post_metrics("media_123")

        assert len(result.deltas) == 0

    @pytest.mark.asyncio
    async def test_snapshots_ordered_by_label_sequence(self) -> None:
        """Snapshots are ordered by defined sequence, not alphabetical."""
        from core.analytics.metrics_query import MetricsQueryService

        # Provide snapshots out of order
        snapshots = [
            _make_metric(snapshot_label="48h", impressions=400),
            _make_metric(snapshot_label="baseline", impressions=100),
            _make_metric(snapshot_label="24h", impressions=250),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_by_media_id.return_value = snapshots

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_post_metrics("media_123")

        # Deltas should follow logical order
        assert result.deltas[0].from_label == "baseline"
        assert result.deltas[0].to_label == "24h"
        assert result.deltas[1].from_label == "24h"
        assert result.deltas[1].to_label == "48h"


# === Task 8.2: get_average_metrics ===


class TestGetAverageMetrics:
    """Task 8.2: get_average_metrics returns averages across all posts."""

    @pytest.mark.asyncio
    async def test_returns_averages(self) -> None:
        """Returns average metrics from repository."""
        from core.analytics.metrics_query import MetricsQueryService, AverageMetrics

        mock_repo = AsyncMock()
        mock_repo.get_average_metrics.return_value = {
            "avg_impressions": 200.0,
            "avg_reach": 150.0,
            "avg_likes": 25.0,
            "avg_comments": 5.0,
            "avg_saved": 8.0,
            "avg_shares": 3.0,
            "avg_total_interactions": 41.0,
            "post_count": 10,
        }

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_average_metrics(days_back=30)

        assert isinstance(result, AverageMetrics)
        assert result.avg_impressions == 200.0
        assert result.avg_likes == 25.0
        assert result.post_count == 10
        mock_repo.get_average_metrics.assert_called_once_with(30)

    @pytest.mark.asyncio
    async def test_returns_zeros_when_no_data(self) -> None:
        """Returns zero averages when no posts exist."""
        from core.analytics.metrics_query import MetricsQueryService

        mock_repo = AsyncMock()
        mock_repo.get_average_metrics.return_value = {
            "avg_impressions": 0.0,
            "avg_reach": 0.0,
            "avg_likes": 0.0,
            "avg_comments": 0.0,
            "avg_saved": 0.0,
            "avg_shares": 0.0,
            "avg_total_interactions": 0.0,
            "post_count": 0,
        }

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_average_metrics()

        assert result.post_count == 0
        assert result.avg_impressions == 0.0


# === Task 8.2: get_performance_comparison ===


class TestGetPerformanceComparison:
    """Task 8.2: get_performance_comparison returns vs-average comparison."""

    @pytest.mark.asyncio
    async def test_comparison_above_average(self) -> None:
        """Post performing above average shows positive percentages."""
        from core.analytics.metrics_query import MetricsQueryService

        # Latest snapshot: 300 impressions, 50 likes
        latest = _make_metric(
            snapshot_label="24h", impressions=300, likes=50, total_interactions=60
        )
        mock_repo = AsyncMock()
        mock_repo.get_latest_snapshot.return_value = latest
        mock_repo.get_average_metrics.return_value = {
            "avg_impressions": 200.0,
            "avg_reach": 150.0,
            "avg_likes": 25.0,
            "avg_comments": 5.0,
            "avg_saved": 8.0,
            "avg_shares": 3.0,
            "avg_total_interactions": 41.0,
            "post_count": 10,
        }

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_performance_comparison("media_123")

        assert result is not None
        assert result.impressions_vs_avg > 0  # 300 vs 200 = +50%
        assert result.likes_vs_avg > 0  # 50 vs 25 = +100%

    @pytest.mark.asyncio
    async def test_comparison_below_average(self) -> None:
        """Post performing below average shows negative percentages."""
        from core.analytics.metrics_query import MetricsQueryService

        latest = _make_metric(
            snapshot_label="24h", impressions=100, likes=10, total_interactions=15
        )
        mock_repo = AsyncMock()
        mock_repo.get_latest_snapshot.return_value = latest
        mock_repo.get_average_metrics.return_value = {
            "avg_impressions": 200.0,
            "avg_reach": 150.0,
            "avg_likes": 25.0,
            "avg_comments": 5.0,
            "avg_saved": 8.0,
            "avg_shares": 3.0,
            "avg_total_interactions": 41.0,
            "post_count": 10,
        }

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_performance_comparison("media_123")

        assert result is not None
        assert result.impressions_vs_avg < 0  # 100 vs 200 = -50%
        assert result.likes_vs_avg < 0  # 10 vs 25 = -60%

    @pytest.mark.asyncio
    async def test_comparison_returns_none_when_no_metrics(self) -> None:
        """Returns None when post has no metrics."""
        from core.analytics.metrics_query import MetricsQueryService

        mock_repo = AsyncMock()
        mock_repo.get_latest_snapshot.return_value = None

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_performance_comparison("unknown_media")

        assert result is None

    @pytest.mark.asyncio
    async def test_comparison_handles_zero_average(self) -> None:
        """Handles division by zero when no average data exists."""
        from core.analytics.metrics_query import MetricsQueryService

        latest = _make_metric(snapshot_label="24h", impressions=100, likes=10)
        mock_repo = AsyncMock()
        mock_repo.get_latest_snapshot.return_value = latest
        mock_repo.get_average_metrics.return_value = {
            "avg_impressions": 0.0,
            "avg_reach": 0.0,
            "avg_likes": 0.0,
            "avg_comments": 0.0,
            "avg_saved": 0.0,
            "avg_shares": 0.0,
            "avg_total_interactions": 0.0,
            "post_count": 0,
        }

        service = MetricsQueryService(repository=mock_repo)
        result = await service.get_performance_comparison("media_123")

        # Should not raise, returns 0.0 for all comparisons
        assert result is not None
        assert result.impressions_vs_avg == 0.0
        assert result.likes_vs_avg == 0.0
