"""Revenue analytics service for Shopify sales attribution.

Epic 7, Story 7-3: Shopify Sales Attribution.
Task 5: RevenueAnalyticsService — revenue queries, comparisons, ROI, combined analytics.

Integrates ClickAnalyticsService (Story 7-2) and MetricsQueryService (Story 7-1)
to provide a unified PostAnalyticsSummary combining metrics + clicks + revenue.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from core.analytics.attribution_repository import AttributionRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostRevenueResult:
    """Revenue analytics for a single post.

    Task 5.2: Attributed revenue, order count, AOV, top products.

    Attributes:
        post_id: Instagram post ID
        attributed_revenue: Total attributed revenue (last-touch)
        order_count: Number of attributed orders
        avg_order_value: Average order value
        top_products: Top products by revenue (tuple of dicts)
    """

    post_id: str
    attributed_revenue: Decimal = Decimal("0")
    order_count: int = 0
    avg_order_value: Decimal = Decimal("0")
    top_products: tuple = ()


@dataclass(frozen=True)
class RevenueComparison:
    """Post revenue performance vs average.

    Task 5.3: Revenue comparison result.

    Attributes:
        post_id: Instagram post ID
        total_revenue: Post's total attributed revenue
        average_revenue: Average revenue across all posts
        revenue_vs_avg: Percentage difference from average
        order_count: Number of attributed orders
    """

    post_id: str
    total_revenue: Decimal = Decimal("0")
    average_revenue: Decimal = Decimal("0")
    revenue_vs_avg: float = 0.0
    order_count: int = 0


@dataclass(frozen=True)
class ROIEstimate:
    """ROI estimate for a post.

    Task 5.4: ROI = (revenue - cost) / cost * 100.

    Attributes:
        post_id: Instagram post ID
        revenue: Total attributed revenue
        cost: Cost of the post (if available)
        roi_pct: ROI percentage (None if cost unavailable)
    """

    post_id: str
    revenue: Decimal = Decimal("0")
    cost: Optional[Decimal] = None
    roi_pct: Optional[float] = None


@dataclass(frozen=True)
class PostAnalyticsSummary:
    """Combined analytics merging metrics + clicks + revenue.

    Task 5.5: Unified summary from Stories 7-1, 7-2, 7-3.

    Attributes:
        post_id: Instagram post ID
        impressions: Latest impressions (Story 7-1)
        reach: Latest reach (Story 7-1)
        likes: Latest likes (Story 7-1)
        comments: Latest comments (Story 7-1)
        saved: Latest saves (Story 7-1)
        shares: Latest shares (Story 7-1)
        total_clicks: Total clicks (Story 7-2)
        unique_clicks: Unique clicks (Story 7-2)
        ctr: Click-through rate (Story 7-2)
        attributed_revenue: Revenue from attributions (Story 7-3)
        order_count: Orders attributed (Story 7-3)
        avg_order_value: AOV (Story 7-3)
        top_products: Top products (Story 7-3)
    """

    post_id: str
    # Metrics (Story 7-1)
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    saved: int = 0
    shares: int = 0
    # Clicks (Story 7-2)
    total_clicks: int = 0
    unique_clicks: int = 0
    ctr: Optional[float] = None
    # Revenue (Story 7-3)
    attributed_revenue: Decimal = Decimal("0")
    order_count: int = 0
    avg_order_value: Decimal = Decimal("0")
    top_products: tuple = ()


class RevenueAnalyticsService:
    """Service for revenue analytics and combined post performance.

    Story 7-3, Task 5.1: Constructor injection pattern.

    Attributes:
        _attr_repo: Attribution repository for revenue data
        _click_service: ClickAnalyticsService (optional, Story 7-2)
        _metrics_service: MetricsQueryService (optional, Story 7-1)
    """

    def __init__(
        self,
        attribution_repository: AttributionRepository,
        click_analytics_service: Optional[Any] = None,
        metrics_query_service: Optional[Any] = None,
    ) -> None:
        """Initialize revenue analytics service.

        Args:
            attribution_repository: Repository for order/attribution data
            click_analytics_service: ClickAnalyticsService (optional, Story 7-2)
            metrics_query_service: MetricsQueryService (optional, Story 7-1)
        """
        self._attr_repo = attribution_repository
        self._click_service = click_analytics_service
        self._metrics_service = metrics_query_service

    async def get_post_revenue(self, post_id: str) -> PostRevenueResult:
        """Get revenue analytics for a single post.

        Task 5.2: Queries AttributionRepository for revenue + top products.

        Args:
            post_id: Instagram post ID

        Returns:
            PostRevenueResult with attributed revenue data
        """
        summary = await self._attr_repo.get_revenue_summary(post_id)
        products = await self._attr_repo.get_top_products(post_id)

        return PostRevenueResult(
            post_id=post_id,
            attributed_revenue=summary["total_revenue"],
            order_count=summary["order_count"],
            avg_order_value=summary["avg_order_value"],
            top_products=tuple(products),
        )

    async def get_revenue_comparison(
        self,
        post_id: str,
        avg_revenue: Decimal = Decimal("0"),
        avg_orders: float = 0.0,
    ) -> RevenueComparison:
        """Compare post revenue performance against average.

        Task 5.3: Same percentage-diff pattern as ClickAnalyticsService.

        Args:
            post_id: Instagram post ID
            avg_revenue: Average revenue across all posts
            avg_orders: Average order count across all posts

        Returns:
            RevenueComparison with vs-average percentage
        """
        summary = await self._attr_repo.get_revenue_summary(post_id)
        total = summary["total_revenue"]

        if avg_revenue > 0:
            pct_diff = float((total - avg_revenue) / avg_revenue * 100)
        else:
            pct_diff = 0.0

        return RevenueComparison(
            post_id=post_id,
            total_revenue=total,
            average_revenue=avg_revenue,
            revenue_vs_avg=pct_diff,
            order_count=summary["order_count"],
        )

    async def get_roi_estimate(
        self,
        post_id: str,
        cost: Optional[Decimal] = None,
    ) -> ROIEstimate:
        """Estimate ROI for a post.

        Task 5.4: ROI = (revenue - cost) / cost * 100.

        Args:
            post_id: Instagram post ID
            cost: Cost of the post (optional)

        Returns:
            ROIEstimate with revenue and ROI percentage
        """
        summary = await self._attr_repo.get_revenue_summary(post_id)
        revenue = summary["total_revenue"]

        roi_pct = None
        if cost is not None and cost > 0:
            roi_pct = float((revenue - cost) / cost * 100)

        return ROIEstimate(
            post_id=post_id,
            revenue=revenue,
            cost=cost,
            roi_pct=roi_pct,
        )

    async def get_combined_analytics(
        self, post_id: str
    ) -> PostAnalyticsSummary:
        """Get unified analytics merging metrics + clicks + revenue.

        Task 5.5: Integrates MetricsQueryService (7-1),
        ClickAnalyticsService (7-2), and revenue data (7-3).

        Args:
            post_id: Instagram post ID

        Returns:
            PostAnalyticsSummary with all available data
        """
        # Revenue data (always available)
        summary = await self._attr_repo.get_revenue_summary(post_id)
        products = await self._attr_repo.get_top_products(post_id)

        # Click data (optional, from Story 7-2)
        total_clicks = 0
        unique_clicks = 0
        ctr = None
        if self._click_service is not None:
            try:
                click_data = await self._click_service.get_post_analytics(post_id)
                total_clicks = click_data.total_clicks
                unique_clicks = click_data.unique_clicks
                ctr = click_data.ctr
            except Exception:
                logger.debug("Click data unavailable for post %s", post_id)

        # Metrics data (optional, from Story 7-1)
        impressions = 0
        reach = 0
        likes = 0
        comments = 0
        saved = 0
        shares = 0
        if self._metrics_service is not None:
            try:
                metrics = await self._metrics_service.get_post_metrics(post_id)
                if metrics.snapshots:
                    latest = metrics.snapshots[-1]
                    impressions = latest.impressions
                    reach = latest.reach
                    likes = latest.likes
                    comments = latest.comments
                    saved = latest.saved
                    shares = latest.shares
            except Exception:
                logger.debug("Metrics data unavailable for post %s", post_id)

        return PostAnalyticsSummary(
            post_id=post_id,
            impressions=impressions,
            reach=reach,
            likes=likes,
            comments=comments,
            saved=saved,
            shares=shares,
            total_clicks=total_clicks,
            unique_clicks=unique_clicks,
            ctr=ctr,
            attributed_revenue=summary["total_revenue"],
            order_count=summary["order_count"],
            avg_order_value=summary["avg_order_value"],
            top_products=tuple(products),
        )


__all__ = [
    "PostAnalyticsSummary",
    "PostRevenueResult",
    "RevenueAnalyticsService",
    "RevenueComparison",
    "ROIEstimate",
]
