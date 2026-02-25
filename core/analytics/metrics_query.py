"""Metrics query service for Instagram engagement analytics.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 8: Metrics query API.

Provides computed deltas between snapshots and performance
comparisons against post averages. Instagram API returns
lifetime cumulative values, so deltas are computed at query time.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from core.analytics.models import InstagramMediaMetric, SnapshotLabel
from core.analytics.repository import InstagramMetricsRepository

logger = logging.getLogger(__name__)

# Logical ordering of snapshot labels for delta computation
SNAPSHOT_ORDER = [label.value for label in SnapshotLabel]


@dataclass(frozen=True)
class MetricsDelta:
    """Computed delta between two consecutive snapshots.

    Attributes:
        from_label: Source snapshot label
        to_label: Target snapshot label
        impressions: Impressions change
        reach: Reach change
        likes: Likes change
        comments: Comments change
        saved: Saves change
        shares: Shares change
        total_interactions: Total interactions change
    """

    from_label: str
    to_label: str
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    saved: int = 0
    shares: int = 0
    total_interactions: int = 0


@dataclass(frozen=True)
class PostMetricsResult:
    """Complete metrics result for a single post.

    Attributes:
        media_id: Instagram media ID
        snapshots: All collected snapshots (ordered)
        deltas: Computed deltas between consecutive snapshots
    """

    media_id: str
    snapshots: list[InstagramMediaMetric]
    deltas: list[MetricsDelta]


@dataclass(frozen=True)
class AverageMetrics:
    """Average metrics across all posts within a time window.

    Attributes:
        avg_impressions: Average impressions
        avg_reach: Average reach
        avg_likes: Average likes
        avg_comments: Average comments
        avg_saved: Average saves
        avg_shares: Average shares
        avg_total_interactions: Average total interactions
        post_count: Number of posts in the average
    """

    avg_impressions: float = 0.0
    avg_reach: float = 0.0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    avg_saved: float = 0.0
    avg_shares: float = 0.0
    avg_total_interactions: float = 0.0
    post_count: int = 0


@dataclass(frozen=True)
class PerformanceComparison:
    """Post performance vs average comparison.

    Values are percentage differences:
    +50.0 means 50% above average, -25.0 means 25% below average.

    Attributes:
        media_id: Instagram media ID
        impressions_vs_avg: Impressions vs average (%)
        reach_vs_avg: Reach vs average (%)
        likes_vs_avg: Likes vs average (%)
        comments_vs_avg: Comments vs average (%)
        saved_vs_avg: Saves vs average (%)
        shares_vs_avg: Shares vs average (%)
        total_interactions_vs_avg: Total interactions vs average (%)
    """

    media_id: str
    impressions_vs_avg: float = 0.0
    reach_vs_avg: float = 0.0
    likes_vs_avg: float = 0.0
    comments_vs_avg: float = 0.0
    saved_vs_avg: float = 0.0
    shares_vs_avg: float = 0.0
    total_interactions_vs_avg: float = 0.0


def _compute_pct_diff(actual: float, average: float) -> float:
    """Compute percentage difference from average.

    Args:
        actual: Actual metric value
        average: Average metric value

    Returns:
        Percentage difference (e.g., 50.0 means 50% above average)
    """
    if average == 0.0:
        return 0.0
    return ((actual - average) / average) * 100.0


class MetricsQueryService:
    """Service for querying and analyzing Instagram engagement metrics.

    Task 8.1: Provides methods for retrieving post metrics,
    computing deltas, getting averages, and comparing performance.

    Constructor injection: repository.
    """

    def __init__(self, repository: InstagramMetricsRepository) -> None:
        """Initialize query service.

        Args:
            repository: Metrics repository for data access
        """
        self._repository = repository

    async def get_post_metrics(self, media_id: str) -> PostMetricsResult:
        """Get all metrics for a post with computed deltas.

        Task 8.2: Returns all snapshots + computed deltas.

        Args:
            media_id: Instagram media ID

        Returns:
            PostMetricsResult with snapshots and deltas
        """
        snapshots = await self._repository.get_by_media_id(media_id)

        if not snapshots:
            return PostMetricsResult(
                media_id=media_id,
                snapshots=[],
                deltas=[],
            )

        # Sort by logical snapshot order
        ordered = self._sort_snapshots(snapshots)
        deltas = self._compute_deltas(ordered)

        return PostMetricsResult(
            media_id=media_id,
            snapshots=ordered,
            deltas=deltas,
        )

    async def get_average_metrics(self, days_back: int = 30) -> AverageMetrics:
        """Get average metrics across all posts.

        Task 8.2: Returns average performance metrics.

        Args:
            days_back: Number of days to look back

        Returns:
            AverageMetrics with computed averages
        """
        raw = await self._repository.get_average_metrics(days_back)

        return AverageMetrics(
            avg_impressions=raw.get("avg_impressions", 0.0),
            avg_reach=raw.get("avg_reach", 0.0),
            avg_likes=raw.get("avg_likes", 0.0),
            avg_comments=raw.get("avg_comments", 0.0),
            avg_saved=raw.get("avg_saved", 0.0),
            avg_shares=raw.get("avg_shares", 0.0),
            avg_total_interactions=raw.get("avg_total_interactions", 0.0),
            post_count=raw.get("post_count", 0),
        )

    async def get_performance_comparison(
        self, media_id: str, days_back: int = 30
    ) -> Optional[PerformanceComparison]:
        """Compare post performance against averages.

        Task 8.2: Returns vs-average comparison.

        Args:
            media_id: Instagram media ID
            days_back: Days to compute averages over

        Returns:
            PerformanceComparison or None if no metrics exist
        """
        latest = await self._repository.get_latest_snapshot(media_id)
        if not latest:
            return None

        averages = await self.get_average_metrics(days_back)

        return PerformanceComparison(
            media_id=media_id,
            impressions_vs_avg=_compute_pct_diff(
                latest.impressions, averages.avg_impressions
            ),
            reach_vs_avg=_compute_pct_diff(latest.reach, averages.avg_reach),
            likes_vs_avg=_compute_pct_diff(latest.likes, averages.avg_likes),
            comments_vs_avg=_compute_pct_diff(
                latest.comments, averages.avg_comments
            ),
            saved_vs_avg=_compute_pct_diff(latest.saved, averages.avg_saved),
            shares_vs_avg=_compute_pct_diff(latest.shares, averages.avg_shares),
            total_interactions_vs_avg=_compute_pct_diff(
                latest.total_interactions, averages.avg_total_interactions
            ),
        )

    def _sort_snapshots(
        self, snapshots: list[InstagramMediaMetric]
    ) -> list[InstagramMediaMetric]:
        """Sort snapshots by logical order (baseline -> 24h -> 48h -> 7d).

        Task 8.3: Ensures deltas are computed in correct order.

        Args:
            snapshots: Unsorted list of snapshots

        Returns:
            Sorted list of snapshots
        """
        order_map = {label: i for i, label in enumerate(SNAPSHOT_ORDER)}
        return sorted(
            snapshots,
            key=lambda s: order_map.get(s.snapshot_label, len(SNAPSHOT_ORDER)),
        )

    def _compute_deltas(
        self, ordered_snapshots: list[InstagramMediaMetric]
    ) -> list[MetricsDelta]:
        """Compute deltas between consecutive snapshots.

        Task 8.3: Diff between consecutive snapshots.

        Args:
            ordered_snapshots: Snapshots sorted by logical order

        Returns:
            List of deltas between consecutive snapshots
        """
        deltas: list[MetricsDelta] = []

        for i in range(1, len(ordered_snapshots)):
            prev = ordered_snapshots[i - 1]
            curr = ordered_snapshots[i]

            deltas.append(
                MetricsDelta(
                    from_label=prev.snapshot_label,
                    to_label=curr.snapshot_label,
                    impressions=curr.impressions - prev.impressions,
                    reach=curr.reach - prev.reach,
                    likes=curr.likes - prev.likes,
                    comments=curr.comments - prev.comments,
                    saved=curr.saved - prev.saved,
                    shares=curr.shares - prev.shares,
                    total_interactions=(
                        curr.total_interactions - prev.total_interactions
                    ),
                )
            )

        return deltas


__all__ = [
    "MetricsQueryService",
    "PostMetricsResult",
    "MetricsDelta",
    "AverageMetrics",
    "PerformanceComparison",
]
