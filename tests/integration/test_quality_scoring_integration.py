"""Integration tests for post-publish quality scoring pipeline.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 9: End-to-end integration tests.

Tests the integration between:
- PostPublishScoringService (scoring engine)
- QualityScoringRepository (data access)
- CommentSentimentScorer (sentiment analysis)
- VarianceAnalyzer (variance + correlation analysis)
- QualityScoringConfig (configuration)
"""

import pytest
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from core.analytics.comment_sentiment import CommentSentimentScorer
from core.analytics.quality_scoring_analyzer import VarianceAnalyzer
from core.analytics.quality_scoring_models import PostPublishScoreRecord
from core.analytics.quality_scoring_repository import QualityScoringRepository
from core.analytics.quality_scoring_service import PostPublishScoringService
from core.config import CTRScale, ConversionScale, QualityScoringConfig
from integrations.instagram.client import InstagramComment


def _make_config(
    variance_threshold: float = 3.0,
) -> QualityScoringConfig:
    """Build a QualityScoringConfig for testing."""
    return QualityScoringConfig(
        variance_threshold=variance_threshold,
        min_posts_for_correlation=50,
        scoring_delay_days=7,
    )


def _make_metrics_service(
    total_interactions_vs_avg: float = 0.0,
    reach_vs_avg: float = 0.0,
) -> AsyncMock:
    """Create a mock MetricsQueryService."""
    service = AsyncMock()
    comparison = MagicMock()
    comparison.total_interactions_vs_avg = total_interactions_vs_avg
    comparison.reach_vs_avg = reach_vs_avg
    service.get_performance_comparison.return_value = comparison
    return service


def _make_click_service(
    total_clicks: int = 0,
    ctr: float = 0.0,
) -> AsyncMock:
    """Create a mock ClickAnalyticsService."""
    service = AsyncMock()
    analytics = MagicMock()
    analytics.total_clicks = total_clicks
    analytics.ctr = ctr
    service.get_post_analytics.return_value = analytics
    return service


def _make_revenue_service(
    order_count: int = 0,
    attributed_revenue: str = "0",
) -> AsyncMock:
    """Create a mock RevenueAnalyticsService."""
    service = AsyncMock()
    revenue = MagicMock()
    revenue.order_count = order_count
    revenue.attributed_revenue = Decimal(attributed_revenue)
    service.get_post_revenue.return_value = revenue
    return service


def _make_instagram_client(comments: list[InstagramComment] | None = None) -> AsyncMock:
    """Create a mock Instagram client with comments."""
    client = AsyncMock()
    client.get_comments.return_value = comments or []
    return client


# === Task 9.1: End-to-end scoring flow ===


class TestEndToEndScoringFlow:
    """Task 9.1: Published post → metrics → score → variance recorded."""

    @pytest.mark.asyncio
    async def test_full_scoring_pipeline(self) -> None:
        """Score a post with all data sources providing data."""
        config = _make_config()
        mock_repo = AsyncMock(spec=QualityScoringRepository)
        sentiment_scorer = CommentSentimentScorer()

        comments = [
            InstagramComment(comment_id="c1", text="Great product!", username="user1", timestamp=datetime.now(UTC)),
            InstagramComment(comment_id="c2", text="Elsker dette!", username="user2", timestamp=datetime.now(UTC)),
        ]
        instagram_client = _make_instagram_client(comments)

        service = PostPublishScoringService(
            metrics_query_service=_make_metrics_service(
                total_interactions_vs_avg=50.0,  # 50% above avg
                reach_vs_avg=30.0,  # 30% above avg
            ),
            click_analytics_service=_make_click_service(
                total_clicks=100,
                ctr=0.025,  # 2.5%
            ),
            revenue_analytics_service=_make_revenue_service(
                order_count=3,
                attributed_revenue="450.00",
            ),
            comment_sentiment_scorer=sentiment_scorer,
            quality_scoring_repository=mock_repo,
            config=config,
            instagram_client=instagram_client,
        )

        result = await service.score_post(
            post_id="post-123",
            media_id="17890000001",
            pre_publish_score=Decimal("7.0"),
        )

        # Verify score shape
        assert result.post_id == "post-123"
        assert result.media_id == "17890000001"
        assert result.pre_publish_score == Decimal("7.0")
        assert 1.0 <= float(result.post_publish_score) <= 10.0
        assert result.variance is not None
        assert result.calculated_at is not None

        # Verify 5 components present
        assert len(result.component_scores) == 5
        assert "engagement_vs_avg" in result.component_scores
        assert "reach_vs_avg" in result.component_scores
        assert "click_through_rate" in result.component_scores
        assert "conversions" in result.component_scores
        assert "comment_sentiment" in result.component_scores

        # Verify metrics snapshot
        assert "engagement" in result.metrics_snapshot
        assert "clicks" in result.metrics_snapshot
        assert "revenue" in result.metrics_snapshot
        assert "sentiment" in result.metrics_snapshot


# === Task 9.2: Partial data scenario ===


class TestPartialDataGracefulDegradation:
    """Task 9.2: Post with partial data → score still calculated."""

    @pytest.mark.asyncio
    async def test_score_with_no_clicks_or_revenue(self) -> None:
        """Score calculated with neutral defaults when clicks/revenue fail."""
        config = _make_config()
        mock_repo = AsyncMock(spec=QualityScoringRepository)
        sentiment_scorer = CommentSentimentScorer()

        # Click and revenue services fail
        failing_click_service = AsyncMock()
        failing_click_service.get_post_analytics.side_effect = Exception("Service down")
        failing_revenue_service = AsyncMock()
        failing_revenue_service.get_post_revenue.side_effect = Exception("Service down")

        service = PostPublishScoringService(
            metrics_query_service=_make_metrics_service(
                total_interactions_vs_avg=20.0,
                reach_vs_avg=10.0,
            ),
            click_analytics_service=failing_click_service,
            revenue_analytics_service=failing_revenue_service,
            comment_sentiment_scorer=sentiment_scorer,
            quality_scoring_repository=mock_repo,
            config=config,
            instagram_client=None,  # No Instagram client either
        )

        result = await service.score_post(
            post_id="post-partial",
            media_id="17890000002",
        )

        # Score should still be calculated
        assert 1.0 <= float(result.post_publish_score) <= 10.0
        # CTR and conversions should use neutral 5.0 (fallback)
        ctr_comp = result.component_scores["click_through_rate"]
        conv_comp = result.component_scores["conversions"]
        assert ctr_comp["raw_score"] == 5.0  # Neutral fallback
        assert conv_comp["raw_score"] == 5.0  # Neutral fallback

    @pytest.mark.asyncio
    async def test_score_with_no_instagram_client(self) -> None:
        """Score calculated with neutral sentiment when no Instagram client."""
        config = _make_config()
        mock_repo = AsyncMock(spec=QualityScoringRepository)
        sentiment_scorer = CommentSentimentScorer()

        service = PostPublishScoringService(
            metrics_query_service=_make_metrics_service(),
            click_analytics_service=_make_click_service(),
            revenue_analytics_service=_make_revenue_service(),
            comment_sentiment_scorer=sentiment_scorer,
            quality_scoring_repository=mock_repo,
            config=config,
            instagram_client=None,  # No client
        )

        result = await service.score_post("post-no-ig", "17890000003")

        sentiment_comp = result.component_scores["comment_sentiment"]
        assert sentiment_comp["raw_score"] == 5.0  # Neutral


# === Task 9.3: Variance flagging ===


class TestVarianceFlagging:
    """Task 9.3: Large variance → flagged_for_review=True."""

    @pytest.mark.asyncio
    async def test_large_positive_variance_flagged(self) -> None:
        """Post with pre=9.0 and post≈4.0 → flagged (variance > 3)."""
        config = _make_config(variance_threshold=3.0)
        mock_repo = AsyncMock(spec=QualityScoringRepository)
        sentiment_scorer = CommentSentimentScorer()

        # All metrics below average to get low post-publish score
        service = PostPublishScoringService(
            metrics_query_service=_make_metrics_service(
                total_interactions_vs_avg=-60.0,  # 60% below avg
                reach_vs_avg=-50.0,
            ),
            click_analytics_service=_make_click_service(ctr=0.001),  # Very low
            revenue_analytics_service=_make_revenue_service(order_count=0),
            comment_sentiment_scorer=sentiment_scorer,
            quality_scoring_repository=mock_repo,
            config=config,
            instagram_client=_make_instagram_client([
                InstagramComment("c1", "Terrible product!", "user1", datetime.now(UTC)),
                InstagramComment("c2", "Dårlig kvalitet", "user2", datetime.now(UTC)),
            ]),
        )

        result = await service.score_post(
            post_id="post-flagged",
            media_id="17890000004",
            pre_publish_score=Decimal("9.0"),
        )

        # Score should be low (poor performance)
        assert float(result.post_publish_score) < 6.0
        # Variance should be negative and large (post_publish - pre_publish)
        assert result.variance is not None
        assert abs(float(result.variance)) > 3.0
        # Should be flagged
        assert result.flagged_for_review is True

    @pytest.mark.asyncio
    async def test_small_variance_not_flagged(self) -> None:
        """Post with small variance (< 3) → not flagged."""
        config = _make_config(variance_threshold=3.0)
        mock_repo = AsyncMock(spec=QualityScoringRepository)
        sentiment_scorer = CommentSentimentScorer()

        # Average performance → score ≈ 5.0
        service = PostPublishScoringService(
            metrics_query_service=_make_metrics_service(
                total_interactions_vs_avg=0.0,
                reach_vs_avg=0.0,
            ),
            click_analytics_service=_make_click_service(ctr=0.025),
            revenue_analytics_service=_make_revenue_service(order_count=2),
            comment_sentiment_scorer=sentiment_scorer,
            quality_scoring_repository=mock_repo,
            config=config,
            instagram_client=None,
        )

        result = await service.score_post(
            post_id="post-normal",
            media_id="17890000005",
            pre_publish_score=Decimal("5.0"),
        )

        # Close to prediction → not flagged
        assert result.flagged_for_review is False


# === Task 9.4: Outperformer analysis ===


class TestOutperformerAnalysis:
    """Task 9.4: High-scoring post → component breakdown shows success drivers."""

    @pytest.mark.asyncio
    async def test_outperformer_analysis_with_component_breakdown(self) -> None:
        """VarianceAnalyzer returns component deviations for outperformer."""
        mock_repo = AsyncMock(spec=QualityScoringRepository)

        # Create a high-scoring record
        high_record = MagicMock()
        high_record.post_id = "post-star"
        high_record.post_publish_score = Decimal("9.5")
        high_record.pre_publish_score = Decimal("5.0")
        high_record.component_scores = {
            "engagement_vs_avg": {"raw_score": 9.0, "weight": 0.30, "weighted_score": 2.7},
            "reach_vs_avg": {"raw_score": 8.0, "weight": 0.20, "weighted_score": 1.6},
            "click_through_rate": {"raw_score": 7.0, "weight": 0.20, "weighted_score": 1.4},
            "conversions": {"raw_score": 8.0, "weight": 0.15, "weighted_score": 1.2},
            "comment_sentiment": {"raw_score": 9.0, "weight": 0.15, "weighted_score": 1.35},
        }

        mock_repo.get_by_post_id.return_value = high_record
        mock_repo.get_average_post_publish_score.return_value = Decimal("5.5")
        mock_repo.get_component_averages.return_value = {
            "engagement_vs_avg": 1.5,
            "reach_vs_avg": 1.0,
            "click_through_rate": 1.0,
            "conversions": 0.75,
            "comment_sentiment": 0.75,
        }
        mock_repo.get_all_scored.return_value = []

        analyzer = VarianceAnalyzer(mock_repo)
        result = await analyzer.analyze_outperformer("post-star")

        assert result is not None
        assert result.post_id == "post-star"
        assert result.post_score == Decimal("9.5")
        assert result.avg_score == Decimal("5.5")
        # Should have component breakdown
        assert len(result.strongest_components) == 5
        # Top component should have positive deviation
        assert result.strongest_components[0].deviation_pct > 0
        # Should have suggested learnings
        assert len(result.suggested_learnings) > 0


# === Task 9.5: Correlation trigger ===


class TestCorrelationAnalysisTrigger:
    """Task 9.5: 50+ scored records → correlation analysis + weight recommendations."""

    @pytest.mark.asyncio
    async def test_correlation_runs_with_50_plus_records(self) -> None:
        """Correlation analysis produces weight recommendations with 50+ records."""
        mock_repo = AsyncMock(spec=QualityScoringRepository)
        mock_repo.get_scored_count.return_value = 60

        # Generate 60 mock scored records with synthetic data
        records = []
        for i in range(60):
            record = MagicMock()
            record.post_publish_score = Decimal(str(3.0 + (i % 7)))  # Vary 3.0-9.0
            record.pre_publish_score = Decimal(str(4.0 + (i % 5)))  # Vary 4.0-8.0
            record.component_scores = {
                "engagement_vs_avg": {"weighted_score": 0.3 + (i % 10) * 0.2},
                "reach_vs_avg": {"weighted_score": 0.2 + (i % 8) * 0.15},
                "click_through_rate": {"weighted_score": 0.1 + (i % 6) * 0.1},
                "conversions": {"weighted_score": 0.05 + (i % 4) * 0.15},
                "comment_sentiment": {"weighted_score": 0.1 + (i % 5) * 0.12},
            }
            records.append(record)

        mock_repo.get_all_scored.return_value = records

        analyzer = VarianceAnalyzer(mock_repo)
        result = await analyzer.run_correlation_analysis()

        assert result is not None
        assert result.total_posts == 60
        # Should have correlations for all 5 components
        assert len(result.correlations) == 5
        assert "engagement_vs_avg" in result.correlations
        assert "reach_vs_avg" in result.correlations
        assert "click_through_rate" in result.correlations
        assert "conversions" in result.correlations
        assert "comment_sentiment" in result.correlations
        # Should have weight recommendations
        assert len(result.recommended_weights) == 5
        # Recommended weights should sum to ~1.0
        total_weight = sum(result.recommended_weights.values())
        assert abs(total_weight - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_correlation_skipped_below_50_posts(self) -> None:
        """Correlation analysis returns None with fewer than 50 records."""
        mock_repo = AsyncMock(spec=QualityScoringRepository)
        mock_repo.get_scored_count.return_value = 30

        analyzer = VarianceAnalyzer(mock_repo)
        result = await analyzer.run_correlation_analysis()

        assert result is None
