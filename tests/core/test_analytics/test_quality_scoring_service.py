"""Tests for PostPublishScoringService.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 4.7: Write scoring service tests (15+ tests).
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.analytics.comment_sentiment import CommentSentimentResult, CommentSentimentScorer
from core.analytics.quality_scoring_service import (
    ComponentScoreDetail,
    PostPublishScoreResult,
    PostPublishScoringService,
)
from integrations.instagram.client import InstagramComment


def _make_config() -> MagicMock:
    """Create a mock QualityScoringConfig."""
    config = MagicMock()
    config.variance_threshold = 3.0
    config.weights = {
        "engagement_vs_avg": 0.30,
        "reach_vs_avg": 0.20,
        "click_through_rate": 0.20,
        "conversions": 0.15,
        "comment_sentiment": 0.15,
    }
    config.ctr_scale = MagicMock()
    config.ctr_scale.max_ctr_pct = 5.0
    config.ctr_scale.min_score = 1.0
    config.ctr_scale.max_score = 10.0
    config.conversion_scale = MagicMock()
    config.conversion_scale.max_orders = 5
    config.conversion_scale.min_score = 2.0
    config.conversion_scale.max_score = 10.0
    return config


def _make_performance_comparison(
    total_interactions_vs_avg: float = 0.0,
    reach_vs_avg: float = 0.0,
) -> MagicMock:
    """Create a mock PerformanceComparison."""
    pc = MagicMock()
    pc.total_interactions_vs_avg = total_interactions_vs_avg
    pc.reach_vs_avg = reach_vs_avg
    return pc


def _make_click_analytics(
    total_clicks: int = 10,
    ctr: float = 0.03,
) -> MagicMock:
    """Create a mock PostClickAnalytics."""
    ca = MagicMock()
    ca.total_clicks = total_clicks
    ca.ctr = ctr
    return ca


def _make_revenue_result(
    order_count: int = 2,
    attributed_revenue: Decimal = Decimal("150.00"),
) -> MagicMock:
    """Create a mock PostRevenueResult."""
    rr = MagicMock()
    rr.order_count = order_count
    rr.attributed_revenue = attributed_revenue
    return rr


def _make_service(
    performance_comparison=None,
    click_analytics=None,
    revenue_result=None,
    comments=None,
    config=None,
) -> PostPublishScoringService:
    """Build a service with mocked dependencies."""
    metrics_service = AsyncMock()
    if performance_comparison is not None:
        metrics_service.get_performance_comparison.return_value = performance_comparison
    else:
        metrics_service.get_performance_comparison.return_value = _make_performance_comparison()

    click_service = AsyncMock()
    if click_analytics is not None:
        click_service.get_post_analytics.return_value = click_analytics
    else:
        click_service.get_post_analytics.return_value = _make_click_analytics()

    revenue_service = AsyncMock()
    if revenue_result is not None:
        revenue_service.get_post_revenue.return_value = revenue_result
    else:
        revenue_service.get_post_revenue.return_value = _make_revenue_result()

    sentiment_scorer = CommentSentimentScorer()
    repository = AsyncMock()
    repository.save_score.return_value = MagicMock()

    instagram_client = AsyncMock()
    if comments is not None:
        instagram_client.get_comments.return_value = comments
    else:
        instagram_client.get_comments.return_value = []

    return PostPublishScoringService(
        metrics_query_service=metrics_service,
        click_analytics_service=click_service,
        revenue_analytics_service=revenue_service,
        comment_sentiment_scorer=sentiment_scorer,
        quality_scoring_repository=repository,
        config=config or _make_config(),
        instagram_client=instagram_client,
    )


class TestPostPublishScoreResult:
    """Tests for PostPublishScoreResult frozen dataclass (Task 4.3)."""

    def test_frozen(self) -> None:
        result = PostPublishScoreResult(
            post_id="p1",
            media_id="m1",
            post_publish_score=Decimal("7.0"),
            component_scores={},
            metrics_snapshot={},
            calculated_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            result.post_publish_score = Decimal("8.0")  # type: ignore[misc]


class TestComponentScoreDetail:
    """Tests for ComponentScoreDetail frozen dataclass (Task 4.4)."""

    def test_frozen(self) -> None:
        detail = ComponentScoreDetail(
            name="engagement_vs_avg",
            raw_score=8.0,
            weight=0.30,
            weighted_score=2.4,
            raw_value=50.0,
        )
        assert detail.weighted_score == 2.4


class TestScorePost:
    """Tests for score_post method (Task 4.2)."""

    @pytest.mark.asyncio
    async def test_full_score_calculation(self) -> None:
        """All data sources available → weighted score computed."""
        service = _make_service(
            performance_comparison=_make_performance_comparison(
                total_interactions_vs_avg=50.0,  # +50% → ~7.5
                reach_vs_avg=20.0,  # +20% → ~6.0
            ),
            click_analytics=_make_click_analytics(ctr=0.03),  # 3% → ~7.0
            revenue_result=_make_revenue_result(order_count=3),  # 3 orders → 8.0
            comments=[],  # No comments → 5.0 neutral
        )

        result = await service.score_post("post-1", "media-1", Decimal("8.0"))

        assert isinstance(result, PostPublishScoreResult)
        assert result.post_id == "post-1"
        assert result.media_id == "media-1"
        assert 1.0 <= float(result.post_publish_score) <= 10.0
        assert result.pre_publish_score == Decimal("8.0")
        assert result.variance is not None
        assert len(result.component_scores) == 5

    @pytest.mark.asyncio
    async def test_no_pre_publish_score(self) -> None:
        """Without pre-publish score, variance should be None/zero."""
        service = _make_service()
        result = await service.score_post("post-1", "media-1")

        assert result.pre_publish_score is None
        # Variance should be Decimal("0") when no pre-publish score
        assert result.variance == Decimal("0")
        assert result.flagged_for_review is False

    @pytest.mark.asyncio
    async def test_variance_flagged_when_large(self) -> None:
        """abs(variance) > 3.0 → flagged_for_review=True."""
        service = _make_service(
            performance_comparison=_make_performance_comparison(
                total_interactions_vs_avg=-80.0,
                reach_vs_avg=-80.0,
            ),
            click_analytics=_make_click_analytics(ctr=0.001),
            revenue_result=_make_revenue_result(order_count=0),
        )
        # Pre-publish score high, actual will be low → big variance
        result = await service.score_post("post-1", "media-1", Decimal("9.0"))

        assert result.flagged_for_review is True
        assert abs(float(result.variance)) > 3.0

    @pytest.mark.asyncio
    async def test_variance_not_flagged_when_small(self) -> None:
        """Small variance → flagged_for_review=False."""
        service = _make_service(
            performance_comparison=_make_performance_comparison(
                total_interactions_vs_avg=0.0,
                reach_vs_avg=0.0,
            ),
        )
        result = await service.score_post("post-1", "media-1", Decimal("5.5"))

        assert result.flagged_for_review is False

    @pytest.mark.asyncio
    async def test_score_clamped_to_range(self) -> None:
        """Score always between 1.0 and 10.0."""
        service = _make_service(
            performance_comparison=_make_performance_comparison(
                total_interactions_vs_avg=200.0,
                reach_vs_avg=200.0,
            ),
            click_analytics=_make_click_analytics(ctr=0.10),
            revenue_result=_make_revenue_result(order_count=10),
        )
        result = await service.score_post("post-1", "media-1")

        assert float(result.post_publish_score) <= 10.0
        assert float(result.post_publish_score) >= 1.0

    @pytest.mark.asyncio
    async def test_component_scores_populated(self) -> None:
        """All 5 component scores present in result."""
        service = _make_service()
        result = await service.score_post("post-1", "media-1")

        assert "engagement_vs_avg" in result.component_scores
        assert "reach_vs_avg" in result.component_scores
        assert "click_through_rate" in result.component_scores
        assert "conversions" in result.component_scores
        assert "comment_sentiment" in result.component_scores

    @pytest.mark.asyncio
    async def test_metrics_snapshot_populated(self) -> None:
        """metrics_snapshot contains raw data used."""
        service = _make_service()
        result = await service.score_post("post-1", "media-1")

        assert isinstance(result.metrics_snapshot, dict)
        assert len(result.metrics_snapshot) > 0

    @pytest.mark.asyncio
    async def test_calculated_at_set(self) -> None:
        service = _make_service()
        before = datetime.now(UTC)
        result = await service.score_post("post-1", "media-1")
        after = datetime.now(UTC)

        assert before <= result.calculated_at <= after


class TestGracefulDegradation:
    """Tests for graceful degradation when data sources fail (Task 4.6)."""

    @pytest.mark.asyncio
    async def test_no_metrics_uses_neutral(self) -> None:
        """Metrics service fails → neutral 5.0 for engagement and reach."""
        service = _make_service()
        service._metrics_query_service.get_performance_comparison.side_effect = Exception("API down")

        result = await service.score_post("post-1", "media-1")

        assert isinstance(result, PostPublishScoreResult)
        engagement = result.component_scores["engagement_vs_avg"]
        assert engagement["raw_score"] == 5.0
        reach = result.component_scores["reach_vs_avg"]
        assert reach["raw_score"] == 5.0

    @pytest.mark.asyncio
    async def test_no_click_data_uses_neutral(self) -> None:
        """Click service fails → neutral 5.0 for CTR."""
        service = _make_service()
        service._click_analytics_service.get_post_analytics.side_effect = Exception("no clicks")

        result = await service.score_post("post-1", "media-1")

        ctr = result.component_scores["click_through_rate"]
        assert ctr["raw_score"] == 5.0

    @pytest.mark.asyncio
    async def test_no_revenue_data_uses_neutral(self) -> None:
        """Revenue service fails → neutral 5.0 for conversions."""
        service = _make_service()
        service._revenue_analytics_service.get_post_revenue.side_effect = Exception("no revenue")

        result = await service.score_post("post-1", "media-1")

        conv = result.component_scores["conversions"]
        assert conv["raw_score"] == 5.0

    @pytest.mark.asyncio
    async def test_no_comments_uses_neutral(self) -> None:
        """Instagram client fails → neutral 5.0 for sentiment."""
        service = _make_service()
        service._instagram_client.get_comments.side_effect = Exception("API error")

        result = await service.score_post("post-1", "media-1")

        sentiment = result.component_scores["comment_sentiment"]
        assert sentiment["raw_score"] == 5.0

    @pytest.mark.asyncio
    async def test_all_sources_fail_still_returns_result(self) -> None:
        """All data sources fail → all neutral scores, result still valid."""
        service = _make_service()
        service._metrics_query_service.get_performance_comparison.side_effect = Exception()
        service._click_analytics_service.get_post_analytics.side_effect = Exception()
        service._revenue_analytics_service.get_post_revenue.side_effect = Exception()
        service._instagram_client.get_comments.side_effect = Exception()

        result = await service.score_post("post-1", "media-1")

        assert isinstance(result, PostPublishScoreResult)
        assert float(result.post_publish_score) == 5.0


class TestScoreBatch:
    """Tests for score_batch method (Task 4.5)."""

    @pytest.mark.asyncio
    async def test_batch_processes_multiple(self) -> None:
        service = _make_service()
        posts = [
            ("post-1", "media-1", Decimal("7.0")),
            ("post-2", "media-2", Decimal("8.0")),
        ]
        results = await service.score_batch(posts)

        assert len(results) == 2
        assert results[0].post_id == "post-1"
        assert results[1].post_id == "post-2"

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self) -> None:
        """One post fails scoring → other posts still scored."""
        service = _make_service()

        # Make second call to metrics fail
        call_count = 0
        original = service._metrics_query_service.get_performance_comparison

        async def fail_on_second(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("metrics unavailable")
            return _make_performance_comparison()

        service._metrics_query_service.get_performance_comparison.side_effect = fail_on_second

        posts = [
            ("post-1", "media-1", None),
            ("post-2", "media-2", None),
        ]
        results = await service.score_batch(posts)

        # Both should still produce results (graceful degradation)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_empty_batch(self) -> None:
        service = _make_service()
        results = await service.score_batch([])
        assert results == []
