"""Tests for revenue analytics service.

Story 7-3, Task 5.6: Revenue analytics tests with mocked dependencies.

Tests:
- get_post_revenue() with attributed data
- get_post_revenue() with no data
- get_revenue_comparison() vs average
- get_roi_estimate() with and without cost data
- get_combined_analytics() merging metrics + clicks + revenue
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.analytics.revenue_analytics import (
    PostRevenueResult,
    RevenueAnalyticsService,
    RevenueComparison,
    ROIEstimate,
    PostAnalyticsSummary,
)


def _make_revenue_summary(
    total: str = "598.00",
    count: int = 2,
    avg: str = "299.00",
) -> dict:
    return {
        "total_revenue": Decimal(total),
        "order_count": count,
        "avg_order_value": Decimal(avg),
    }


def _make_top_products() -> list[dict]:
    return [
        {
            "product_handle": "lions-mane",
            "title": "Lions Mane",
            "total_quantity": 3,
            "total_revenue": Decimal("897.00"),
        },
        {
            "product_handle": "reishi",
            "title": "Reishi",
            "total_quantity": 1,
            "total_revenue": Decimal("249.00"),
        },
    ]


class TestGetPostRevenue:
    """Tests for get_post_revenue()."""

    @pytest.mark.asyncio
    async def test_returns_revenue_data(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary()
        attr_repo.get_top_products.return_value = _make_top_products()

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_post_revenue("post_abc")

        assert isinstance(result, PostRevenueResult)
        assert result.post_id == "post_abc"
        assert result.attributed_revenue == Decimal("598.00")
        assert result.order_count == 2
        assert result.avg_order_value == Decimal("299.00")
        assert len(result.top_products) == 2

    @pytest.mark.asyncio
    async def test_no_revenue_data(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary(
            total="0", count=0, avg="0"
        )
        attr_repo.get_top_products.return_value = []

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_post_revenue("post_none")

        assert result.attributed_revenue == Decimal("0")
        assert result.order_count == 0
        assert result.top_products == ()


class TestGetRevenueComparison:
    """Tests for get_revenue_comparison()."""

    @pytest.mark.asyncio
    async def test_above_average(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary(
            total="600.00", count=3, avg="200.00"
        )
        # Average across all posts: 300.00 revenue, 2 orders
        attr_repo.get_revenue_by_post_ids.return_value = {}

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_revenue_comparison(
            "post_abc", avg_revenue=Decimal("300.00"), avg_orders=2.0
        )

        assert isinstance(result, RevenueComparison)
        assert result.post_id == "post_abc"
        assert result.total_revenue == Decimal("600.00")
        assert result.revenue_vs_avg == 100.0  # 100% above average

    @pytest.mark.asyncio
    async def test_below_average(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary(
            total="150.00", count=1, avg="150.00"
        )

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_revenue_comparison(
            "post_abc", avg_revenue=Decimal("300.00"), avg_orders=3.0
        )

        assert result.revenue_vs_avg == -50.0  # 50% below average

    @pytest.mark.asyncio
    async def test_zero_average(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary(
            total="100.00", count=1, avg="100.00"
        )

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_revenue_comparison(
            "post_abc", avg_revenue=Decimal("0"), avg_orders=0.0
        )

        assert result.revenue_vs_avg == 0.0


class TestGetROIEstimate:
    """Tests for get_roi_estimate()."""

    @pytest.mark.asyncio
    async def test_with_cost_data(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary(
            total="1000.00", count=5, avg="200.00"
        )

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_roi_estimate(
            "post_abc", cost=Decimal("200.00")
        )

        assert isinstance(result, ROIEstimate)
        assert result.revenue == Decimal("1000.00")
        assert result.cost == Decimal("200.00")
        assert result.roi_pct == 400.0  # (1000-200)/200*100

    @pytest.mark.asyncio
    async def test_without_cost_data(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary(
            total="500.00", count=2, avg="250.00"
        )

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_roi_estimate("post_abc")

        assert result.roi_pct is None
        assert result.cost is None

    @pytest.mark.asyncio
    async def test_zero_cost(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary(
            total="300.00", count=1, avg="300.00"
        )

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_roi_estimate(
            "post_abc", cost=Decimal("0")
        )

        assert result.roi_pct is None


class TestGetCombinedAnalytics:
    """Tests for get_combined_analytics()."""

    @pytest.mark.asyncio
    async def test_merges_all_sources(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary()
        attr_repo.get_top_products.return_value = _make_top_products()

        click_service = AsyncMock()
        click_analytics = MagicMock()
        click_analytics.total_clicks = 150
        click_analytics.unique_clicks = 120
        click_analytics.ctr = 0.05
        click_service.get_post_analytics.return_value = click_analytics

        metrics_service = AsyncMock()
        metrics_result = MagicMock()
        snapshot = MagicMock()
        snapshot.impressions = 3000
        snapshot.reach = 2500
        snapshot.likes = 200
        snapshot.comments = 15
        snapshot.saved = 30
        snapshot.shares = 10
        metrics_result.snapshots = [snapshot]
        metrics_service.get_post_metrics.return_value = metrics_result

        service = RevenueAnalyticsService(
            attr_repo, click_service, metrics_service
        )
        result = await service.get_combined_analytics("post_abc")

        assert isinstance(result, PostAnalyticsSummary)
        assert result.post_id == "post_abc"
        assert result.attributed_revenue == Decimal("598.00")
        assert result.total_clicks == 150
        assert result.impressions == 3000

    @pytest.mark.asyncio
    async def test_missing_click_service(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary()
        attr_repo.get_top_products.return_value = []

        service = RevenueAnalyticsService(attr_repo)
        result = await service.get_combined_analytics("post_abc")

        assert result.attributed_revenue == Decimal("598.00")
        assert result.total_clicks == 0
        assert result.impressions == 0

    @pytest.mark.asyncio
    async def test_missing_metrics_service(self) -> None:
        attr_repo = AsyncMock()
        attr_repo.get_revenue_summary.return_value = _make_revenue_summary()
        attr_repo.get_top_products.return_value = []

        click_service = AsyncMock()
        click_analytics = MagicMock()
        click_analytics.total_clicks = 50
        click_analytics.unique_clicks = 40
        click_analytics.ctr = 0.02
        click_service.get_post_analytics.return_value = click_analytics

        service = RevenueAnalyticsService(attr_repo, click_service)
        result = await service.get_combined_analytics("post_abc")

        assert result.total_clicks == 50
        assert result.impressions == 0


class TestPostRevenueResult:
    """Tests for PostRevenueResult frozen dataclass."""

    def test_frozen(self) -> None:
        result = PostRevenueResult(
            post_id="abc",
            attributed_revenue=Decimal("100"),
            order_count=1,
            avg_order_value=Decimal("100"),
        )
        with pytest.raises(AttributeError):
            result.post_id = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        result = PostRevenueResult(post_id="abc")
        assert result.attributed_revenue == Decimal("0")
        assert result.order_count == 0
        assert result.top_products == ()
