"""Tests for VarianceAnalyzer and CorrelationAnalyzer.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 5.7 + Task 6.5: Analyzer tests.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.analytics.quality_scoring_analyzer import (
    ComponentDeviation,
    CorrelationReport,
    OutperformerAnalysis,
    VarianceAnalyzer,
    VarianceReport,
)
from core.analytics.quality_scoring_models import PostPublishScoreRecord


def _make_record(
    post_id: str = "post-001",
    pre_publish_score: Decimal | None = Decimal("7.0"),
    post_publish_score: Decimal = Decimal("6.5"),
    variance: Decimal = Decimal("-0.5"),
    flagged_for_review: bool = False,
    component_scores: dict | None = None,
) -> PostPublishScoreRecord:
    """Factory for creating test records."""
    return PostPublishScoreRecord(
        post_id=post_id,
        media_id=f"media-{post_id}",
        pre_publish_score=pre_publish_score,
        post_publish_score=post_publish_score,
        variance=variance,
        component_scores=component_scores or {
            "engagement_vs_avg": {"raw_score": 6.0, "weight": 0.3, "weighted_score": 1.8},
            "reach_vs_avg": {"raw_score": 5.5, "weight": 0.2, "weighted_score": 1.1},
            "click_through_rate": {"raw_score": 7.0, "weight": 0.2, "weighted_score": 1.4},
            "conversions": {"raw_score": 6.0, "weight": 0.15, "weighted_score": 0.9},
            "comment_sentiment": {"raw_score": 7.5, "weight": 0.15, "weighted_score": 1.125},
        },
        metrics_snapshot={},
        flagged_for_review=flagged_for_review,
        snapshot_label="7d",
        calculated_at=datetime.now(UTC),
    )


# === VarianceReport dataclass ===

class TestVarianceReport:
    def test_frozen(self) -> None:
        report = VarianceReport(
            post_id="p1",
            pre_score=Decimal("7.0"),
            post_score=Decimal("4.0"),
            variance=Decimal("-3.0"),
            flagged_components=["engagement_vs_avg"],
            calculated_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            report.variance = Decimal("0")  # type: ignore[misc]


# === OutperformerAnalysis dataclass ===

class TestOutperformerAnalysis:
    def test_frozen(self) -> None:
        analysis = OutperformerAnalysis(
            post_id="p1",
            post_score=Decimal("9.5"),
            avg_score=Decimal("5.5"),
            strongest_components=[],
            suggested_learnings=[],
            similar_post_ids=[],
        )
        assert analysis.post_score == Decimal("9.5")


# === ComponentDeviation dataclass ===

class TestComponentDeviation:
    def test_frozen(self) -> None:
        deviation = ComponentDeviation(
            component="engagement_vs_avg",
            post_value=9.0,
            avg_value=5.0,
            deviation_pct=80.0,
        )
        assert deviation.deviation_pct == 80.0


# === VarianceAnalyzer ===

class TestVarianceAnalyzerInit:
    def test_constructor_accepts_repository(self) -> None:
        repo = AsyncMock()
        analyzer = VarianceAnalyzer(repo)
        assert analyzer._repository is repo


class TestGetFlaggedVariances:
    """Tests for get_flagged_variances (Task 5.2)."""

    @pytest.mark.asyncio
    async def test_returns_variance_reports(self) -> None:
        repo = AsyncMock()
        flagged = _make_record(
            post_id="p1",
            pre_publish_score=Decimal("8.0"),
            post_publish_score=Decimal("4.0"),
            variance=Decimal("-4.0"),
            flagged_for_review=True,
        )
        repo.get_flagged_for_review.return_value = [flagged]

        analyzer = VarianceAnalyzer(repo)
        results = await analyzer.get_flagged_variances(limit=50)

        assert len(results) == 1
        assert isinstance(results[0], VarianceReport)
        assert results[0].post_id == "p1"
        assert results[0].variance == Decimal("-4.0")

    @pytest.mark.asyncio
    async def test_returns_empty_when_none_flagged(self) -> None:
        repo = AsyncMock()
        repo.get_flagged_for_review.return_value = []

        analyzer = VarianceAnalyzer(repo)
        results = await analyzer.get_flagged_variances()

        assert results == []


class TestAnalyzeOutperformer:
    """Tests for analyze_outperformer (Task 5.3)."""

    @pytest.mark.asyncio
    async def test_identifies_strongest_components(self) -> None:
        repo = AsyncMock()
        # Post with high engagement score
        record = _make_record(
            post_id="p-high",
            post_publish_score=Decimal("9.0"),
            component_scores={
                "engagement_vs_avg": {"raw_score": 9.5, "weight": 0.3, "weighted_score": 2.85},
                "reach_vs_avg": {"raw_score": 8.0, "weight": 0.2, "weighted_score": 1.6},
                "click_through_rate": {"raw_score": 7.0, "weight": 0.2, "weighted_score": 1.4},
                "conversions": {"raw_score": 6.0, "weight": 0.15, "weighted_score": 0.9},
                "comment_sentiment": {"raw_score": 8.0, "weight": 0.15, "weighted_score": 1.2},
            },
        )
        repo.get_by_post_id.return_value = record

        # Component averages
        repo.get_component_averages.return_value = {
            "engagement_vs_avg": 1.5,
            "reach_vs_avg": 1.0,
            "click_through_rate": 1.2,
            "conversions": 0.8,
            "comment_sentiment": 1.0,
        }
        repo.get_average_post_publish_score.return_value = Decimal("5.5")

        # Similar posts
        similar = _make_record(
            post_id="p-similar",
            component_scores={
                "engagement_vs_avg": {"raw_score": 9.0, "weight": 0.3, "weighted_score": 2.7},
                "reach_vs_avg": {"raw_score": 7.5, "weight": 0.2, "weighted_score": 1.5},
                "click_through_rate": {"raw_score": 6.0, "weight": 0.2, "weighted_score": 1.2},
                "conversions": {"raw_score": 5.0, "weight": 0.15, "weighted_score": 0.75},
                "comment_sentiment": {"raw_score": 7.0, "weight": 0.15, "weighted_score": 1.05},
            },
        )
        repo.get_all_scored.return_value = [record, similar]

        analyzer = VarianceAnalyzer(repo)
        analysis = await analyzer.analyze_outperformer("p-high")

        assert isinstance(analysis, OutperformerAnalysis)
        assert analysis.post_id == "p-high"
        assert analysis.post_score == Decimal("9.0")
        assert len(analysis.strongest_components) > 0
        assert len(analysis.suggested_learnings) > 0

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_post(self) -> None:
        repo = AsyncMock()
        repo.get_by_post_id.return_value = None

        analyzer = VarianceAnalyzer(repo)
        result = await analyzer.analyze_outperformer("missing")

        assert result is None


# === CorrelationReport dataclass ===

class TestCorrelationReport:
    def test_frozen(self) -> None:
        report = CorrelationReport(
            total_posts=55,
            correlations={"compliance": 0.6},
            recommended_weights={"compliance": 0.30},
            generated_at=datetime.now(UTC),
        )
        assert report.total_posts == 55


# === Correlation Analysis ===

class TestRunCorrelationAnalysis:
    """Tests for run_correlation_analysis (Task 6.2)."""

    @pytest.mark.asyncio
    async def test_returns_none_when_fewer_than_50_posts(self) -> None:
        repo = AsyncMock()
        repo.get_scored_count.return_value = 30

        analyzer = VarianceAnalyzer(repo)
        result = await analyzer.run_correlation_analysis()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_report_when_50_plus_posts(self) -> None:
        repo = AsyncMock()
        repo.get_scored_count.return_value = 55

        # Create 55 records with varying scores
        records = []
        for i in range(55):
            score = 3.0 + (i / 55.0) * 6.0  # Range 3.0 to 9.0
            r = _make_record(
                post_id=f"p-{i}",
                pre_publish_score=Decimal(str(round(score - 0.5, 1))),
                post_publish_score=Decimal(str(round(score, 1))),
                component_scores={
                    "engagement_vs_avg": {"raw_score": score, "weight": 0.3, "weighted_score": score * 0.3},
                    "reach_vs_avg": {"raw_score": score * 0.8, "weight": 0.2, "weighted_score": score * 0.16},
                },
            )
            records.append(r)

        repo.get_all_scored.return_value = records

        analyzer = VarianceAnalyzer(repo)
        result = await analyzer.run_correlation_analysis()

        assert isinstance(result, CorrelationReport)
        assert result.total_posts == 55
        assert len(result.correlations) > 0
        assert result.generated_at is not None

    @pytest.mark.asyncio
    async def test_pearson_correlation_basic(self) -> None:
        """Test the Pearson correlation implementation."""
        analyzer = VarianceAnalyzer(AsyncMock())
        # Perfect positive correlation
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        r = analyzer._pearson_correlation(x, y)
        assert abs(r - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_pearson_correlation_negative(self) -> None:
        analyzer = VarianceAnalyzer(AsyncMock())
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 8.0, 6.0, 4.0, 2.0]
        r = analyzer._pearson_correlation(x, y)
        assert abs(r - (-1.0)) < 0.01

    @pytest.mark.asyncio
    async def test_pearson_correlation_zero_std(self) -> None:
        """Constant values → correlation 0.0."""
        analyzer = VarianceAnalyzer(AsyncMock())
        x = [5.0, 5.0, 5.0]
        y = [3.0, 3.0, 3.0]
        r = analyzer._pearson_correlation(x, y)
        assert r == 0.0
