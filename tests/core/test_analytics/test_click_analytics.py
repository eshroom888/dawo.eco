"""Tests for ClickAnalyticsService.

Story 7-2, Task 5.7: Tests for analytics computation.
Tests post analytics, average CTR, and comparison methods.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.analytics.click_analytics import (
    ClickAnalyticsService,
    ClickComparison,
    PostClickAnalytics,
)


@pytest.fixture
def mock_utm_repository() -> AsyncMock:
    """Create mock UTMRepository."""
    repo = AsyncMock()
    repo.get_by_post_id = AsyncMock(return_value=[])
    repo.get_click_stats = AsyncMock(return_value={
        "total_clicks": 0, "unique_clicks": 0,
        "clicks_by_day": [], "device_breakdown": [],
    })
    repo.get_aggregate_click_stats = AsyncMock(return_value={
        "total_clicks": 0, "unique_posts": 0, "avg_clicks_per_post": 0.0,
    })
    return repo


@pytest.fixture
def mock_metrics_query() -> AsyncMock:
    """Create mock MetricsQueryService (Story 7-1)."""
    service = AsyncMock()
    service.get_post_metrics = AsyncMock()
    service.get_average_metrics = AsyncMock()
    return service


@pytest.fixture
def service(
    mock_utm_repository: AsyncMock,
    mock_metrics_query: AsyncMock,
) -> ClickAnalyticsService:
    """Create ClickAnalyticsService with mocked dependencies."""
    return ClickAnalyticsService(
        utm_repository=mock_utm_repository,
        metrics_query_service=mock_metrics_query,
    )


class TestGetPostAnalytics:
    """Tests for get_post_analytics method."""

    @pytest.mark.asyncio
    async def test_returns_analytics_with_clicks(
        self, service: ClickAnalyticsService, mock_utm_repository: AsyncMock
    ) -> None:
        """Returns PostClickAnalytics with click data."""
        from core.analytics.utm_models import ShortLink

        link_id = uuid4()
        mock_utm_repository.get_by_post_id.return_value = [
            ShortLink(
                id=link_id, code="a1", destination_url="https://x.com",
                utm_source="ig", utm_medium="p", utm_campaign="c",
                utm_content="x", post_id="post1", source_type="instagram",
            ),
        ]
        mock_utm_repository.get_click_stats.return_value = {
            "total_clicks": 100,
            "unique_clicks": 75,
            "clicks_by_day": [{"day": "2026-02-20", "count": 50}],
            "device_breakdown": [{"device_type": "mobile", "count": 60}],
        }

        result = await service.get_post_analytics("post1")

        assert isinstance(result, PostClickAnalytics)
        assert result.post_id == "post1"
        assert result.total_clicks == 100
        assert result.unique_clicks == 75
        assert len(result.clicks_by_day) == 1
        assert len(result.device_breakdown) == 1

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_links(
        self, service: ClickAnalyticsService, mock_utm_repository: AsyncMock
    ) -> None:
        """Returns zero analytics when post has no links."""
        mock_utm_repository.get_by_post_id.return_value = []

        result = await service.get_post_analytics("unknown")

        assert result.total_clicks == 0
        assert result.unique_clicks == 0

    @pytest.mark.asyncio
    async def test_includes_impressions_ctr_when_available(
        self,
        service: ClickAnalyticsService,
        mock_utm_repository: AsyncMock,
        mock_metrics_query: AsyncMock,
    ) -> None:
        """Includes CTR when impressions data is available from Story 7-1."""
        from core.analytics.utm_models import ShortLink
        from core.analytics.metrics_query import PostMetricsResult
        from core.analytics.models import InstagramMediaMetric

        link_id = uuid4()
        mock_utm_repository.get_by_post_id.return_value = [
            ShortLink(
                id=link_id, code="a1", destination_url="https://x.com",
                utm_source="ig", utm_medium="p", utm_campaign="c",
                utm_content="x", post_id="post1", source_type="instagram",
            ),
        ]
        mock_utm_repository.get_click_stats.return_value = {
            "total_clicks": 50,
            "unique_clicks": 40,
            "clicks_by_day": [],
            "device_breakdown": [],
        }

        # Mock impressions from Story 7-1
        mock_metric = MagicMock()
        mock_metric.impressions = 1000
        mock_metrics_query.get_post_metrics.return_value = PostMetricsResult(
            media_id="post1",
            snapshots=[mock_metric],
            deltas=[],
        )

        result = await service.get_post_analytics("post1")

        assert result.total_clicks == 50
        # CTR = clicks / impressions = 50 / 1000 = 0.05
        assert result.ctr == pytest.approx(0.05)


class TestGetAverageCTR:
    """Tests for get_average_ctr method."""

    @pytest.mark.asyncio
    async def test_returns_average_ctr(
        self,
        service: ClickAnalyticsService,
        mock_utm_repository: AsyncMock,
        mock_metrics_query: AsyncMock,
    ) -> None:
        """Returns average CTR across all posts."""
        from core.analytics.metrics_query import AverageMetrics

        # Mock aggregate stats: 200 total clicks across 10 posts = 20 avg
        mock_utm_repository.get_aggregate_click_stats.return_value = {
            "total_clicks": 200, "unique_posts": 10, "avg_clicks_per_post": 20.0,
        }

        # Mock impressions: avg 2000 impressions per post
        mock_metrics_query.get_average_metrics.return_value = AverageMetrics(
            avg_impressions=2000.0,
            post_count=10,
        )

        # CTR = avg_clicks_per_post / avg_impressions = 20 / 2000 = 0.01
        result = await service.get_average_ctr(days_back=30)
        assert result == pytest.approx(0.01)

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_data(
        self, service: ClickAnalyticsService, mock_metrics_query: AsyncMock
    ) -> None:
        """Returns 0.0 when no data available."""
        from core.analytics.metrics_query import AverageMetrics

        mock_metrics_query.get_average_metrics.return_value = AverageMetrics(
            avg_impressions=0.0,
            post_count=0,
        )

        result = await service.get_average_ctr(days_back=30)
        assert result == 0.0


class TestGetComparison:
    """Tests for get_comparison method."""

    @pytest.mark.asyncio
    async def test_returns_comparison(
        self, service: ClickAnalyticsService, mock_utm_repository: AsyncMock
    ) -> None:
        """Returns ClickComparison with vs-average values."""
        from core.analytics.utm_models import ShortLink

        link_id = uuid4()
        mock_utm_repository.get_by_post_id.return_value = [
            ShortLink(
                id=link_id, code="a1", destination_url="https://x.com",
                utm_source="ig", utm_medium="p", utm_campaign="c",
                utm_content="x", post_id="post1", source_type="instagram",
            ),
        ]
        mock_utm_repository.get_click_stats.return_value = {
            "total_clicks": 200,
            "unique_clicks": 150,
            "clicks_by_day": [],
            "device_breakdown": [],
        }
        # Average is 100 clicks/post => 200 is +100% above average
        mock_utm_repository.get_aggregate_click_stats.return_value = {
            "total_clicks": 1000, "unique_posts": 10, "avg_clicks_per_post": 100.0,
        }

        result = await service.get_comparison("post1")

        assert isinstance(result, ClickComparison)
        assert result.post_id == "post1"
        assert result.total_clicks == 200
        assert result.average_clicks == pytest.approx(100.0)
        assert result.clicks_vs_avg == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_returns_none_for_no_links(
        self, service: ClickAnalyticsService, mock_utm_repository: AsyncMock
    ) -> None:
        """Returns None when post has no links."""
        mock_utm_repository.get_by_post_id.return_value = []

        result = await service.get_comparison("unknown")
        assert result is None


class TestDataclasses:
    """Tests for result dataclasses."""

    def test_post_click_analytics_defaults(self) -> None:
        """PostClickAnalytics has correct defaults."""
        analytics = PostClickAnalytics(post_id="p1")
        assert analytics.total_clicks == 0
        assert analytics.unique_clicks == 0
        assert analytics.ctr is None

    def test_click_comparison_fields(self) -> None:
        """ClickComparison has required fields."""
        comp = ClickComparison(
            post_id="p1",
            total_clicks=100,
            average_clicks=50.0,
            clicks_vs_avg=100.0,
        )
        assert comp.clicks_vs_avg == 100.0


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports(self) -> None:
        """click_analytics module exports required names."""
        from core.analytics import click_analytics

        assert hasattr(click_analytics, "__all__")
        assert "ClickAnalyticsService" in click_analytics.__all__
        assert "PostClickAnalytics" in click_analytics.__all__
        assert "ClickComparison" in click_analytics.__all__
