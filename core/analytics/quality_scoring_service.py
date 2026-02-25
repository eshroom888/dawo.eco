"""Post-publish quality scoring service.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 4: PostPublishScoringService — core scoring logic.

Gathers metrics from all sources in parallel, computes weighted
component scores, and produces a final post-publish quality score.
Graceful degradation: if any single data source fails, neutral
score (5.0) is used for that component.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from core.analytics.comment_sentiment import CommentSentimentScorer
from core.analytics.quality_scoring_repository import QualityScoringRepository
from core.analytics.quality_scoring_models import PostPublishScoreRecord
from core.config import QualityScoringConfig

if TYPE_CHECKING:
    from core.analytics.metrics_query import MetricsQueryService
    from core.analytics.click_analytics import ClickAnalyticsService
    from integrations.instagram.client import InstagramPublishClientProtocol

logger = logging.getLogger(__name__)

# Neutral fallback score when a data source is unavailable
_NEUTRAL_SCORE = 5.0


@dataclass(frozen=True)
class ComponentScoreDetail:
    """Detail for a single scoring component.

    Task 4.4: Frozen dataclass with raw value, weight, and computed score.

    Attributes:
        name: Component identifier (e.g., "engagement_vs_avg")
        raw_score: Score on 1-10 scale before weighting
        weight: Component weight (0.0-1.0)
        weighted_score: raw_score * weight
        raw_value: Original metric value used for scoring
    """

    name: str
    raw_score: float
    weight: float
    weighted_score: float
    raw_value: Any


@dataclass(frozen=True)
class PostPublishScoreResult:
    """Result of post-publish scoring.

    Task 4.3: Frozen dataclass with score, components, and variance.

    Attributes:
        post_id: Internal post identifier
        media_id: Instagram media ID
        post_publish_score: Weighted score (1.0-10.0)
        pre_publish_score: Pre-publish prediction (if available)
        variance: post_publish - pre_publish (0 if no pre-publish)
        flagged_for_review: True if abs(variance) > threshold
        component_scores: Detail per component
        metrics_snapshot: Raw data used for scoring
        calculated_at: When the score was computed
    """

    post_id: str
    media_id: str
    post_publish_score: Decimal
    component_scores: dict[str, dict[str, Any]]
    metrics_snapshot: dict
    calculated_at: datetime
    pre_publish_score: Optional[Decimal] = None
    variance: Optional[Decimal] = None
    flagged_for_review: bool = False


class PostPublishScoringService:
    """Scores published posts based on actual performance metrics.

    Task 4.1: Constructor injection for all dependencies.
    Gathers data from MetricsQueryService, ClickAnalyticsService,
    RevenueAnalyticsService, and CommentSentimentScorer in parallel.

    Graceful degradation: each data source can fail independently;
    neutral score (5.0) is used for unavailable components.
    """

    def __init__(
        self,
        metrics_query_service: "MetricsQueryService",
        click_analytics_service: "ClickAnalyticsService",
        revenue_analytics_service: Any,
        comment_sentiment_scorer: CommentSentimentScorer,
        quality_scoring_repository: QualityScoringRepository,
        config: QualityScoringConfig,
        instagram_client: Optional["InstagramPublishClientProtocol"] = None,
    ) -> None:
        """Initialize with injected dependencies.

        Args:
            metrics_query_service: Story 7-1 MetricsQueryService
            click_analytics_service: Story 7-2 ClickAnalyticsService
            revenue_analytics_service: Story 7-3 RevenueAnalyticsService
            comment_sentiment_scorer: Keyword-based sentiment scorer
            quality_scoring_repository: Data access for score records
            config: QualityScoringConfig with weights and thresholds
            instagram_client: Optional Instagram client for comments
        """
        self._metrics_query_service = metrics_query_service
        self._click_analytics_service = click_analytics_service
        self._revenue_analytics_service = revenue_analytics_service
        self._sentiment_scorer = comment_sentiment_scorer
        self._repository = quality_scoring_repository
        self._config = config
        self._instagram_client = instagram_client

    async def score_post(
        self,
        post_id: str,
        media_id: str,
        pre_publish_score: Optional[Decimal] = None,
    ) -> PostPublishScoreResult:
        """Score a single post based on actual performance.

        Task 4.2: Gathers metrics in parallel, computes weighted score.

        Args:
            post_id: Internal post identifier
            media_id: Instagram media ID
            pre_publish_score: Pre-publish quality score (if available)

        Returns:
            PostPublishScoreResult with computed score and breakdown
        """
        # Gather all data sources in parallel
        metrics_task = self._fetch_metrics(media_id)
        clicks_task = self._fetch_clicks(post_id)
        revenue_task = self._fetch_revenue(post_id)
        comments_task = self._fetch_comments(media_id)

        metrics_data, click_data, revenue_data, sentiment_data = await asyncio.gather(
            metrics_task, clicks_task, revenue_task, comments_task
        )

        # Compute component scores
        weights = self._config.weights
        components: dict[str, dict[str, Any]] = {}

        # Engagement vs average
        eng_score = self._pct_to_score(metrics_data.get("total_interactions_vs_avg", 0.0))
        components["engagement_vs_avg"] = {
            "name": "engagement_vs_avg",
            "raw_score": eng_score,
            "weight": weights["engagement_vs_avg"],
            "weighted_score": round(eng_score * weights["engagement_vs_avg"], 3),
            "raw_value": metrics_data.get("total_interactions_vs_avg", 0.0),
        }

        # Reach vs average
        reach_score = self._pct_to_score(metrics_data.get("reach_vs_avg", 0.0))
        components["reach_vs_avg"] = {
            "name": "reach_vs_avg",
            "raw_score": reach_score,
            "weight": weights["reach_vs_avg"],
            "weighted_score": round(reach_score * weights["reach_vs_avg"], 3),
            "raw_value": metrics_data.get("reach_vs_avg", 0.0),
        }

        # Click-through rate (neutral if data source unavailable)
        if click_data.get("fallback"):
            ctr_score = _NEUTRAL_SCORE
        else:
            ctr_score = self._ctr_to_score(click_data.get("ctr", 0.0))
        components["click_through_rate"] = {
            "name": "click_through_rate",
            "raw_score": ctr_score,
            "weight": weights["click_through_rate"],
            "weighted_score": round(ctr_score * weights["click_through_rate"], 3),
            "raw_value": click_data.get("ctr", 0.0),
        }

        # Conversions (neutral if data source unavailable)
        if revenue_data.get("fallback"):
            conv_score = _NEUTRAL_SCORE
        else:
            conv_score = self._orders_to_score(revenue_data.get("order_count", 0))
        components["conversions"] = {
            "name": "conversions",
            "raw_score": conv_score,
            "weight": weights["conversions"],
            "weighted_score": round(conv_score * weights["conversions"], 3),
            "raw_value": revenue_data.get("order_count", 0),
        }

        # Comment sentiment
        sent_score = sentiment_data.get("score", _NEUTRAL_SCORE)
        components["comment_sentiment"] = {
            "name": "comment_sentiment",
            "raw_score": sent_score,
            "weight": weights["comment_sentiment"],
            "weighted_score": round(sent_score * weights["comment_sentiment"], 3),
            "raw_value": sentiment_data,
        }

        # Final weighted sum
        total = sum(c["weighted_score"] for c in components.values())
        final_score = Decimal(str(max(1.0, min(10.0, round(total, 1)))))

        # Variance calculation
        if pre_publish_score is not None:
            variance = final_score - pre_publish_score
            flagged = abs(float(variance)) > self._config.variance_threshold
        else:
            variance = Decimal("0")
            flagged = False

        now = datetime.now(UTC)

        # Build metrics snapshot
        metrics_snapshot = {
            "engagement": metrics_data,
            "clicks": click_data,
            "revenue": revenue_data,
            "sentiment": sentiment_data,
        }

        return PostPublishScoreResult(
            post_id=post_id,
            media_id=media_id,
            post_publish_score=final_score,
            pre_publish_score=pre_publish_score,
            variance=variance,
            flagged_for_review=flagged,
            component_scores=components,
            metrics_snapshot=metrics_snapshot,
            calculated_at=now,
        )

    async def score_batch(
        self,
        posts: list[tuple[str, str, Optional[Decimal]]],
    ) -> list[PostPublishScoreResult]:
        """Score multiple posts with partial failure handling.

        Task 4.5: Same pattern as InstagramMetricsCollector.collect_batch()
        and AttributionService.process_orders_batch().

        Args:
            posts: List of (post_id, media_id, pre_publish_score) tuples.

        Returns:
            List of PostPublishScoreResult for successfully scored posts.
        """
        if not posts:
            return []

        results: list[PostPublishScoreResult] = []
        for post_id, media_id, pre_score in posts:
            try:
                result = await self.score_post(post_id, media_id, pre_score)
                results.append(result)
            except Exception:
                logger.error("Failed to score post %s, skipping", post_id)

        return results

    # --- Data fetching with graceful degradation ---

    async def _fetch_metrics(self, media_id: str) -> dict:
        """Fetch performance comparison from MetricsQueryService."""
        try:
            comparison = await self._metrics_query_service.get_performance_comparison(media_id)
            if comparison is None:
                logger.debug("No metrics data for %s, using neutral", media_id)
                return {"total_interactions_vs_avg": 0.0, "reach_vs_avg": 0.0, "fallback": True}
            return {
                "total_interactions_vs_avg": comparison.total_interactions_vs_avg,
                "reach_vs_avg": comparison.reach_vs_avg,
            }
        except Exception:
            logger.warning("Metrics unavailable for %s, using neutral", media_id)
            return {"total_interactions_vs_avg": 0.0, "reach_vs_avg": 0.0, "fallback": True}

    async def _fetch_clicks(self, post_id: str) -> dict:
        """Fetch click analytics from ClickAnalyticsService."""
        try:
            analytics = await self._click_analytics_service.get_post_analytics(post_id)
            return {
                "total_clicks": analytics.total_clicks,
                "ctr": analytics.ctr if analytics.ctr is not None else 0.0,
            }
        except Exception:
            logger.warning("Click data unavailable for %s, using neutral", post_id)
            return {"total_clicks": 0, "ctr": 0.0, "fallback": True}

    async def _fetch_revenue(self, post_id: str) -> dict:
        """Fetch revenue data from RevenueAnalyticsService."""
        try:
            revenue = await self._revenue_analytics_service.get_post_revenue(post_id)
            return {
                "order_count": revenue.order_count,
                "attributed_revenue": str(revenue.attributed_revenue),
            }
        except Exception:
            logger.warning("Revenue data unavailable for %s, using neutral", post_id)
            return {"order_count": 0, "attributed_revenue": "0", "fallback": True}

    async def _fetch_comments(self, media_id: str) -> dict:
        """Fetch and score comments via Instagram client + sentiment scorer."""
        try:
            if self._instagram_client is None:
                return {"score": _NEUTRAL_SCORE, "total": 0, "fallback": True}

            comments = await self._instagram_client.get_comments(media_id)
            result = self._sentiment_scorer.score_comments(comments)
            return {
                "score": result.score,
                "positive": result.positive_count,
                "negative": result.negative_count,
                "neutral": result.neutral_count,
                "total": result.total_count,
                "sentiment_ratio": result.sentiment_ratio,
            }
        except Exception:
            logger.warning("Comments unavailable for %s, using neutral", media_id)
            return {"score": _NEUTRAL_SCORE, "total": 0, "fallback": True}

    # --- Score mapping functions ---

    @staticmethod
    def _pct_to_score(pct_vs_avg: float) -> float:
        """Map percentage vs average to 1-10 scale.

        +100% above avg = 10, exactly average (0%) = 5, -100% below = 1.
        Clamped to [1.0, 10.0].
        """
        score = 5.0 + (pct_vs_avg / 100.0) * 5.0
        return max(1.0, min(10.0, round(score, 1)))

    def _ctr_to_score(self, ctr: float) -> float:
        """Map click-through rate to 1-10 scale.

        Uses configurable scale: max_ctr_pct=5% → 10, 0% → min_score.
        """
        scale = self._config.ctr_scale
        if ctr <= 0:
            return scale.min_score

        # Linear interpolation: 0% → min_score, max_ctr% → max_score
        ratio = min(ctr / (scale.max_ctr_pct / 100.0), 1.0)
        score = scale.min_score + ratio * (scale.max_score - scale.min_score)
        return round(max(scale.min_score, min(scale.max_score, score)), 1)

    def _orders_to_score(self, order_count: int) -> float:
        """Map order count to 1-10 scale.

        Uses configurable scale: max_orders=5 → 10, 0 → min_score.
        """
        scale = self._config.conversion_scale
        if order_count <= 0:
            return scale.min_score

        ratio = min(order_count / scale.max_orders, 1.0)
        score = scale.min_score + ratio * (scale.max_score - scale.min_score)
        return round(max(scale.min_score, min(scale.max_score, score)), 1)


__all__ = [
    "ComponentScoreDetail",
    "PostPublishScoreResult",
    "PostPublishScoringService",
]
