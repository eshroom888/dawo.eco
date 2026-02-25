"""Integration tests for performance feedback loop pipeline.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 8: End-to-end integration tests.

Tests the integration between:
- FeedbackLoopService (orchestrator)
- ContentPerformanceAnalyzer (content/time/hashtag analysis)
- WeightAdjuster (weight proposal generation)
- FeedbackLoopRepository (data persistence)
- QualityScoringRepository + InstagramMetricsRepository (data sources)
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.analytics.content_performance_analyzer import ContentPerformanceAnalyzer
from core.analytics.feedback_loop_models import FeedbackReport
from core.analytics.feedback_loop_service import FeedbackLoopService
from core.analytics.quality_scoring_analyzer import CorrelationReport, VarianceAnalyzer
from core.analytics.quality_scoring_models import PostPublishScoreRecord
from core.analytics.weight_adjuster import WeightAdjuster
from core.config import QualityScoringConfig


@dataclass(frozen=True)
class _FeedbackLoopConfig:
    min_posts_threshold: int = 10
    weight_change_threshold: float = 0.05
    min_hashtag_posts: int = 2
    top_hashtags_limit: int = 20
    enabled: bool = True


def _make_score_record(
    post_id: str,
    media_id: str,
    score: float,
    caption: str = "",
) -> PostPublishScoreRecord:
    return PostPublishScoreRecord(
        post_id=post_id,
        media_id=media_id,
        post_publish_score=Decimal(str(score)),
        variance=Decimal("0"),
        component_scores={},
        metrics_snapshot={"caption": caption} if caption else {},
        calculated_at=datetime.now(UTC),
    )


def _make_metric(media_id: str, media_type: str = "IMAGE", hour: int = 14, day: int = 17) -> MagicMock:
    metric = MagicMock()
    metric.media_id = media_id
    metric.collected_at = datetime(2026, 2, day, hour, 0, tzinfo=UTC)
    metric.snapshot_label = "baseline"
    metric.raw_response = {"media_type": media_type}
    return metric


def _build_full_pipeline(
    records: list[PostPublishScoreRecord],
    metrics_by_id: dict,
    correlation_report: CorrelationReport | None = None,
) -> tuple[FeedbackLoopService, AsyncMock]:
    """Build a fully wired service pipeline with mocked repos."""
    quality_repo = AsyncMock()
    quality_repo.get_scored_count.return_value = len(records)
    quality_repo.get_all_scored.return_value = records

    metrics_repo = AsyncMock()
    metrics_repo.get_by_media_ids.return_value = metrics_by_id

    feedback_repo = AsyncMock()
    feedback_repo.save_report.side_effect = lambda r: r
    feedback_repo.save_weight_adjustment.side_effect = lambda r: r

    # Real ContentPerformanceAnalyzer with mocked repos
    content_analyzer = ContentPerformanceAnalyzer(quality_repo, metrics_repo)

    # Real VarianceAnalyzer (mocked) → WeightAdjuster
    variance_analyzer = AsyncMock(spec=VarianceAnalyzer)
    variance_analyzer.run_correlation_analysis.return_value = correlation_report

    config = QualityScoringConfig()
    weight_adjuster = WeightAdjuster(variance_analyzer, feedback_repo, config)

    service = FeedbackLoopService(
        content_analyzer, weight_adjuster, feedback_repo,
        quality_repo, _FeedbackLoopConfig(),
    )

    return service, feedback_repo


class TestEndToEndWeeklyAnalysis:
    """E2E: Seed 100+ PostPublishScoreRecords → run → verify report."""

    async def test_full_pipeline_produces_complete_report(self) -> None:
        records = [
            _make_score_record(f"p{i}", f"m{i}", 5.0 + (i % 5), f"Great #wellness #eco post #{i}")
            for i in range(20)
        ]
        metrics = {
            f"m{i}": [_make_metric(f"m{i}", "VIDEO" if i % 2 == 0 else "IMAGE", hour=10 + (i % 12))]
            for i in range(20)
        }

        service, feedback_repo = _build_full_pipeline(records, metrics)
        report = await service.run_weekly_analysis()

        assert report.status == "complete"
        assert report.total_posts_analyzed == 20
        assert report.content_type_rankings is not None
        assert report.time_slot_analysis is not None
        assert report.hashtag_rankings is not None
        assert report.recommendations is not None
        assert len(report.recommendations) > 0
        feedback_repo.save_report.assert_awaited_once()

    async def test_report_contains_content_type_rankings(self) -> None:
        records = [
            _make_score_record(f"p{i}", f"m{i}", 7.0 + (i % 3))
            for i in range(15)
        ]
        metrics = {
            f"m{i}": [_make_metric(f"m{i}", "CAROUSEL_ALBUM" if i < 5 else "VIDEO")]
            for i in range(15)
        }

        service, _ = _build_full_pipeline(records, metrics)
        report = await service.run_weekly_analysis()

        assert report.content_type_rankings is not None
        rankings = report.content_type_rankings.get("rankings", [])
        assert len(rankings) >= 1

    async def test_report_contains_hashtag_analysis(self) -> None:
        records = [
            _make_score_record(f"p{i}", f"m{i}", 8.0, "#eco #health")
            for i in range(15)
        ]
        metrics = {f"m{i}": [_make_metric(f"m{i}")] for i in range(15)}

        service, _ = _build_full_pipeline(records, metrics)
        report = await service.run_weekly_analysis()

        assert report.hashtag_rankings is not None


class TestPartialFailure:
    """Missing metrics data → report still generated with missing sections."""

    async def test_no_metrics_still_generates_report(self) -> None:
        records = [
            _make_score_record(f"p{i}", f"m{i}", 7.0)
            for i in range(15)
        ]
        # Empty metrics — content type analysis will classify as UNKNOWN
        metrics: dict = {}

        service, _ = _build_full_pipeline(records, metrics)
        report = await service.run_weekly_analysis()

        assert report.status == "complete"
        assert report.content_type_rankings is not None


class TestWeightProposalIntegration:
    """Seed correlated data → verify proposal generated."""

    async def test_weight_proposal_saved_when_significant(self) -> None:
        records = [_make_score_record(f"p{i}", f"m{i}", 7.0) for i in range(15)]
        metrics = {f"m{i}": [_make_metric(f"m{i}")] for i in range(15)}

        correlation = CorrelationReport(
            total_posts=100,
            correlations={
                "engagement_vs_avg": 0.9,
                "reach_vs_avg": 0.2,
                "click_through_rate": 0.5,
                "conversions": 0.1,
                "comment_sentiment": 0.1,
            },
            recommended_weights={
                "engagement_vs_avg": 0.50,
                "reach_vs_avg": 0.10,
                "click_through_rate": 0.20,
                "conversions": 0.10,
                "comment_sentiment": 0.10,
            },
            generated_at=datetime.now(UTC),
        )

        service, feedback_repo = _build_full_pipeline(records, metrics, correlation)
        report = await service.run_weekly_analysis()

        assert report.weight_adjustment_proposal is not None
        feedback_repo.save_weight_adjustment.assert_awaited_once()

    async def test_no_proposal_when_correlation_insignificant(self) -> None:
        records = [_make_score_record(f"p{i}", f"m{i}", 7.0) for i in range(15)]
        metrics = {f"m{i}": [_make_metric(f"m{i}")] for i in range(15)}

        # Very close to current weights → no significant change
        correlation = CorrelationReport(
            total_posts=100,
            correlations={
                "engagement_vs_avg": 0.6,
                "reach_vs_avg": 0.4,
                "click_through_rate": 0.4,
                "conversions": 0.3,
                "comment_sentiment": 0.3,
            },
            recommended_weights={
                "engagement_vs_avg": 0.31,
                "reach_vs_avg": 0.20,
                "click_through_rate": 0.20,
                "conversions": 0.15,
                "comment_sentiment": 0.14,
            },
            generated_at=datetime.now(UTC),
        )

        service, feedback_repo = _build_full_pipeline(records, metrics, correlation)
        report = await service.run_weekly_analysis()

        assert report.weight_adjustment_proposal is None
        feedback_repo.save_weight_adjustment.assert_not_awaited()


class TestIdempotentReport:
    """Running twice on same week → verify report_date is consistent."""

    async def test_report_date_consistent_across_runs(self) -> None:
        records = [_make_score_record(f"p{i}", f"m{i}", 7.0) for i in range(15)]
        metrics = {f"m{i}": [_make_metric(f"m{i}")] for i in range(15)}

        service, _ = _build_full_pipeline(records, metrics)
        report1 = await service.run_weekly_analysis()
        report2 = await service.run_weekly_analysis()

        assert report1.report_date == report2.report_date == date.today()

    async def test_report_saved_on_each_run(self) -> None:
        records = [_make_score_record(f"p{i}", f"m{i}", 7.0) for i in range(15)]
        metrics = {f"m{i}": [_make_metric(f"m{i}")] for i in range(15)}

        service, feedback_repo = _build_full_pipeline(records, metrics)
        await service.run_weekly_analysis()
        await service.run_weekly_analysis()

        # save_report called twice (real DB would upsert by report_date)
        assert feedback_repo.save_report.await_count == 2
