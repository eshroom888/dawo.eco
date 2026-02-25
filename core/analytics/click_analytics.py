"""Click analytics query service.

Epic 7, Story 7-2: UTM Click-Through Tracking.
Task 5: ClickAnalyticsService — aggregation, CTR computation, comparisons.

Integrates with MetricsQueryService (Story 7-1) for impressions-based
CTR calculation: CTR = total_clicks / impressions.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from core.analytics.utm_repository import UTMRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostClickAnalytics:
    """Aggregated click analytics for a single post.

    Attributes:
        post_id: Instagram post ID
        total_clicks: Total clicks across all links
        unique_clicks: Unique clicks by IP hash
        clicks_by_day: Daily click breakdown
        device_breakdown: Clicks by device type
        ctr: Click-through rate (clicks/impressions) if impressions available
    """

    post_id: str
    total_clicks: int = 0
    unique_clicks: int = 0
    clicks_by_day: tuple = ()
    device_breakdown: tuple = ()
    ctr: Optional[float] = None


@dataclass(frozen=True)
class ClickComparison:
    """Post click performance vs average comparison.

    Attributes:
        post_id: Instagram post ID
        total_clicks: Post's total clicks
        average_clicks: Average clicks across all posts
        clicks_vs_avg: Percentage difference from average
    """

    post_id: str
    total_clicks: int = 0
    average_clicks: float = 0.0
    clicks_vs_avg: float = 0.0


class ClickAnalyticsService:
    """Service for querying and analyzing click-through data.

    Story 7-2, Task 5.1: Provides methods for post analytics,
    average CTR, and performance comparisons.

    Constructor injection: UTMRepository, MetricsQueryService (optional).
    """

    def __init__(
        self,
        utm_repository: UTMRepository,
        metrics_query_service=None,
    ) -> None:
        """Initialize analytics service.

        Args:
            utm_repository: UTM repository for click data
            metrics_query_service: MetricsQueryService (Story 7-1) for impressions
        """
        self._utm_repository = utm_repository
        self._metrics_query_service = metrics_query_service

    async def get_post_analytics(self, post_id: str) -> PostClickAnalytics:
        """Get aggregated click analytics for a post.

        Task 5.3: Total, unique, by_day, by_device, CTR.

        Args:
            post_id: Instagram post ID

        Returns:
            PostClickAnalytics with aggregated data
        """
        links = await self._utm_repository.get_by_post_id(post_id)

        if not links:
            return PostClickAnalytics(post_id=post_id)

        total_clicks = 0
        total_unique = 0
        all_by_day: list = []
        all_device: list = []

        for link in links:
            if link.id is None:
                continue
            stats = await self._utm_repository.get_click_stats(link.id)
            total_clicks += stats["total_clicks"]
            total_unique += stats["unique_clicks"]
            all_by_day.extend(stats["clicks_by_day"])
            all_device.extend(stats["device_breakdown"])

        # Try to compute CTR from impressions (Story 7-1 integration)
        ctr = await self._compute_ctr(post_id, total_clicks)

        return PostClickAnalytics(
            post_id=post_id,
            total_clicks=total_clicks,
            unique_clicks=total_unique,
            clicks_by_day=tuple(all_by_day),
            device_breakdown=tuple(all_device),
            ctr=ctr,
        )

    async def get_average_ctr(self, days_back: int = 30) -> float:
        """Get average CTR across all posts.

        Task 5.4: Average CTR within the time window.
        CTR = avg_clicks_per_post / avg_impressions.

        Args:
            days_back: Number of days to look back

        Returns:
            Average CTR as float (0.0 if no data)
        """
        if self._metrics_query_service is None:
            return 0.0

        # Get aggregate click stats from repository
        agg = await self._utm_repository.get_aggregate_click_stats(days_back)
        if agg["unique_posts"] == 0:
            return 0.0

        # Get average impressions from metrics service (Story 7-1)
        avg_metrics = await self._metrics_query_service.get_average_metrics(days_back)
        if avg_metrics.post_count == 0 or avg_metrics.avg_impressions == 0.0:
            return 0.0

        # Average CTR = avg_clicks_per_post / avg_impressions
        return agg["avg_clicks_per_post"] / avg_metrics.avg_impressions

    async def get_comparison(self, post_id: str) -> Optional[ClickComparison]:
        """Compare post click performance against average.

        Task 5.5: Post vs average comparison.

        Args:
            post_id: Instagram post ID

        Returns:
            ClickComparison or None if no data
        """
        analytics = await self.get_post_analytics(post_id)

        if analytics.total_clicks == 0:
            links = await self._utm_repository.get_by_post_id(post_id)
            if not links:
                return None

        # Get average clicks across all posts
        agg = await self._utm_repository.get_aggregate_click_stats(30)
        avg_clicks = agg["avg_clicks_per_post"]

        # Compute percentage difference from average
        if avg_clicks > 0:
            clicks_vs_avg = ((analytics.total_clicks - avg_clicks) / avg_clicks) * 100.0
        else:
            clicks_vs_avg = 0.0

        return ClickComparison(
            post_id=post_id,
            total_clicks=analytics.total_clicks,
            average_clicks=avg_clicks,
            clicks_vs_avg=clicks_vs_avg,
        )

    async def _compute_ctr(
        self, post_id: str, total_clicks: int
    ) -> Optional[float]:
        """Compute CTR from clicks and impressions.

        Task 5.6: Integration with MetricsQueryService (Story 7-1).

        Args:
            post_id: Instagram post ID (used as media_id)
            total_clicks: Total clicks for the post

        Returns:
            CTR as float, or None if impressions unavailable
        """
        if self._metrics_query_service is None:
            return None

        try:
            post_metrics = await self._metrics_query_service.get_post_metrics(post_id)
            if not post_metrics.snapshots:
                return None

            # Use latest snapshot's impressions
            latest = post_metrics.snapshots[-1]
            if latest.impressions == 0:
                return 0.0

            return total_clicks / latest.impressions

        except Exception:
            logger.debug(
                "Could not compute CTR for post %s: metrics unavailable",
                post_id,
            )
            return None


__all__ = [
    "ClickAnalyticsService",
    "ClickComparison",
    "PostClickAnalytics",
]
