"""Tests for FeedbackLoopService orchestrator.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 5.2: Write service tests (target: 20+ tests including partial failure).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.analytics.content_performance_analyzer import (
    ContentTypeAnalysis,
    ContentTypeRanking,
    HashtagAnalysis,
    HashtagRanking,
    SourcePerformanceAnalysis,
    SourceRanking,
    TimeSlot,
    TimeSlotAnalysis,
)
from core.analytics.feedback_loop_service import FeedbackLoopService
from core.analytics.weight_adjuster import WeightAdjustmentProposal


@dataclass(frozen=True)
class _StubFeedbackLoopConfig:
    """Minimal stub matching FeedbackLoopConfig shape."""

    min_posts_threshold: int = 100
    weight_change_threshold: float = 0.05
    min_hashtag_posts: int = 3
    top_hashtags_limit: int = 20
    enabled: bool = True


@pytest.fixture
def mock_content_analyzer() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_weight_adjuster() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_feedback_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_quality_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def config() -> _StubFeedbackLoopConfig:
    return _StubFeedbackLoopConfig()


@pytest.fixture
def service(
    mock_content_analyzer: AsyncMock,
    mock_weight_adjuster: AsyncMock,
    mock_feedback_repo: AsyncMock,
    mock_quality_repo: AsyncMock,
    config: _StubFeedbackLoopConfig,
) -> FeedbackLoopService:
    return FeedbackLoopService(
        mock_content_analyzer,
        mock_weight_adjuster,
        mock_feedback_repo,
        mock_quality_repo,
        config,
    )


def _content_type_analysis(rankings: list | None = None) -> ContentTypeAnalysis:
    return ContentTypeAnalysis(
        rankings=rankings or [ContentTypeRanking("VIDEO", 8.2, 50)],
        total_posts=100,
    )


def _time_slot_analysis(slots: list | None = None) -> TimeSlotAnalysis:
    top = slots or [TimeSlot("Tuesday", 18, 7.8, 10)]
    return TimeSlotAnalysis(
        slots=top, top_slots=top[:5], total_posts=100,
    )


def _hashtag_analysis(rankings: list | None = None) -> HashtagAnalysis:
    return HashtagAnalysis(
        rankings=rankings or [HashtagRanking("#wellness", 7.5, 25)],
        total_posts=100,
    )


def _source_performance_analysis(
    rankings: list | None = None,
) -> SourcePerformanceAnalysis:
    return SourcePerformanceAnalysis(
        rankings=rankings or [SourceRanking("instagram_trending", 7.8, 40, 0.05)],
        overall_avg=7.0,
        total_posts=100,
    )


def _setup_happy_path(
    mock_quality_repo: AsyncMock,
    mock_content_analyzer: AsyncMock,
    mock_weight_adjuster: AsyncMock,
    mock_feedback_repo: AsyncMock,
) -> None:
    """Configure all mocks for a successful full analysis."""
    mock_quality_repo.get_scored_count.return_value = 150
    mock_content_analyzer.analyze_content_types.return_value = _content_type_analysis()
    mock_content_analyzer.analyze_posting_times.return_value = _time_slot_analysis()
    mock_content_analyzer.analyze_hashtags.return_value = _hashtag_analysis()
    mock_content_analyzer.analyze_source_performance.return_value = _source_performance_analysis()
    mock_weight_adjuster.propose_weight_adjustment.return_value = None
    mock_feedback_repo.save_report.side_effect = lambda r: r


# ============================================================
# Happy Path Tests
# ============================================================


class TestRunWeeklyAnalysis:
    """Tests for run_weekly_analysis orchestration."""

    async def test_returns_complete_report(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            mock_quality_repo, mock_content_analyzer,
            mock_weight_adjuster, mock_feedback_repo,
        )
        report = await service.run_weekly_analysis()

        assert report is not None
        assert report.status == "complete"
        assert report.total_posts_analyzed == 150
        assert report.content_type_rankings is not None
        assert report.time_slot_analysis is not None
        assert report.hashtag_rankings is not None

    async def test_saves_report_to_repository(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            mock_quality_repo, mock_content_analyzer,
            mock_weight_adjuster, mock_feedback_repo,
        )
        await service.run_weekly_analysis()

        mock_feedback_repo.save_report.assert_awaited_once()

    async def test_calls_all_analyzers(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            mock_quality_repo, mock_content_analyzer,
            mock_weight_adjuster, mock_feedback_repo,
        )
        await service.run_weekly_analysis()

        mock_content_analyzer.analyze_content_types.assert_awaited_once()
        mock_content_analyzer.analyze_posting_times.assert_awaited_once()
        mock_content_analyzer.analyze_hashtags.assert_awaited_once()
        mock_content_analyzer.analyze_source_performance.assert_awaited_once()
        mock_weight_adjuster.propose_weight_adjustment.assert_awaited_once()

    async def test_report_includes_source_performance(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            mock_quality_repo, mock_content_analyzer,
            mock_weight_adjuster, mock_feedback_repo,
        )
        report = await service.run_weekly_analysis()
        assert report.source_performance is not None

    async def test_report_date_is_today(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            mock_quality_repo, mock_content_analyzer,
            mock_weight_adjuster, mock_feedback_repo,
        )
        report = await service.run_weekly_analysis()

        assert report.report_date == date.today()

    async def test_includes_weight_proposal_when_significant(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            mock_quality_repo, mock_content_analyzer,
            mock_weight_adjuster, mock_feedback_repo,
        )
        proposal = WeightAdjustmentProposal(
            current_weights={"a": 0.5},
            proposed_weights={"a": 0.6},
            correlations={"a": 0.8},
            change_rationale=["Increase a"],
        )
        mock_weight_adjuster.propose_weight_adjustment.return_value = proposal

        report = await service.run_weekly_analysis()
        assert report.weight_adjustment_proposal is not None

    async def test_saves_weight_adjustment_record(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            mock_quality_repo, mock_content_analyzer,
            mock_weight_adjuster, mock_feedback_repo,
        )
        proposal = WeightAdjustmentProposal(
            current_weights={"a": 0.5},
            proposed_weights={"a": 0.6},
            correlations={"a": 0.8},
            change_rationale=["Increase a"],
        )
        mock_weight_adjuster.propose_weight_adjustment.return_value = proposal

        await service.run_weekly_analysis()
        mock_feedback_repo.save_weight_adjustment.assert_awaited_once()


# ============================================================
# Insufficient Data Tests
# ============================================================


class TestInsufficientData:
    """Tests for threshold gate behavior."""

    async def test_insufficient_posts_returns_partial(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 50
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await service.run_weekly_analysis()
        assert report.status == "partial"
        assert "insufficient_posts" in (report.missing_sections or [])

    async def test_insufficient_posts_skips_analysis(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 50
        mock_feedback_repo.save_report.side_effect = lambda r: r

        await service.run_weekly_analysis()
        mock_content_analyzer.analyze_content_types.assert_not_awaited()


# ============================================================
# Graceful Degradation (AC6)
# ============================================================


class TestGracefulDegradation:
    """Tests that individual analysis failures don't break the report."""

    async def test_content_type_failure_still_produces_report(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 150
        mock_content_analyzer.analyze_content_types.side_effect = Exception("boom")
        mock_content_analyzer.analyze_posting_times.return_value = _time_slot_analysis()
        mock_content_analyzer.analyze_hashtags.return_value = _hashtag_analysis()
        mock_weight_adjuster.propose_weight_adjustment.return_value = None
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await service.run_weekly_analysis()
        assert report.status == "partial"
        assert "content_type_rankings" in (report.missing_sections or [])
        # Other sections still populated
        assert report.time_slot_analysis is not None
        assert report.hashtag_rankings is not None

    async def test_posting_time_failure_still_produces_report(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 150
        mock_content_analyzer.analyze_content_types.return_value = _content_type_analysis()
        mock_content_analyzer.analyze_posting_times.side_effect = Exception("timeout")
        mock_content_analyzer.analyze_hashtags.return_value = _hashtag_analysis()
        mock_weight_adjuster.propose_weight_adjustment.return_value = None
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await service.run_weekly_analysis()
        assert report.status == "partial"
        assert "time_slot_analysis" in (report.missing_sections or [])

    async def test_hashtag_failure_still_produces_report(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 150
        mock_content_analyzer.analyze_content_types.return_value = _content_type_analysis()
        mock_content_analyzer.analyze_posting_times.return_value = _time_slot_analysis()
        mock_content_analyzer.analyze_hashtags.side_effect = Exception("fail")
        mock_weight_adjuster.propose_weight_adjustment.return_value = None
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await service.run_weekly_analysis()
        assert report.status == "partial"
        assert "hashtag_rankings" in (report.missing_sections or [])

    async def test_weight_adjuster_failure_still_produces_report(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 150
        mock_content_analyzer.analyze_content_types.return_value = _content_type_analysis()
        mock_content_analyzer.analyze_posting_times.return_value = _time_slot_analysis()
        mock_content_analyzer.analyze_hashtags.return_value = _hashtag_analysis()
        mock_weight_adjuster.propose_weight_adjustment.side_effect = Exception("no data")
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await service.run_weekly_analysis()
        assert report.status == "partial"
        assert "weight_adjustment_proposal" in (report.missing_sections or [])

    async def test_source_performance_failure_still_produces_report(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 150
        mock_content_analyzer.analyze_content_types.return_value = _content_type_analysis()
        mock_content_analyzer.analyze_posting_times.return_value = _time_slot_analysis()
        mock_content_analyzer.analyze_hashtags.return_value = _hashtag_analysis()
        mock_content_analyzer.analyze_source_performance.side_effect = Exception("src fail")
        mock_weight_adjuster.propose_weight_adjustment.return_value = None
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await service.run_weekly_analysis()
        assert report.status == "partial"
        assert "source_performance" in (report.missing_sections or [])
        # Other sections still populated
        assert report.content_type_rankings is not None

    async def test_source_performance_insufficient_data_marks_missing(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 150
        mock_content_analyzer.analyze_content_types.return_value = _content_type_analysis()
        mock_content_analyzer.analyze_posting_times.return_value = _time_slot_analysis()
        mock_content_analyzer.analyze_hashtags.return_value = _hashtag_analysis()
        mock_content_analyzer.analyze_source_performance.return_value = SourcePerformanceAnalysis(
            rankings=[], overall_avg=0.0, total_posts=0, insufficient_data=True,
        )
        mock_weight_adjuster.propose_weight_adjustment.return_value = None
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await service.run_weekly_analysis()
        assert "source_performance" in (report.missing_sections or [])
        assert report.source_performance is None

    async def test_all_analyses_fail_still_saves_report(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 150
        mock_content_analyzer.analyze_content_types.side_effect = Exception("1")
        mock_content_analyzer.analyze_posting_times.side_effect = Exception("2")
        mock_content_analyzer.analyze_hashtags.side_effect = Exception("3")
        mock_content_analyzer.analyze_source_performance.side_effect = Exception("4")
        mock_weight_adjuster.propose_weight_adjustment.side_effect = Exception("5")
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await service.run_weekly_analysis()
        assert report.status == "partial"
        assert len(report.missing_sections) >= 5
        mock_feedback_repo.save_report.assert_awaited_once()


# ============================================================
# Recommendation Generation (Task 5.1)
# ============================================================


class TestGenerateRecommendations:
    """Tests for generate_recommendations method."""

    async def test_generates_content_type_recommendation(
        self, service: FeedbackLoopService,
    ) -> None:
        content = _content_type_analysis([
            ContentTypeRanking("REEL", 8.2, 40),
            ContentTypeRanking("IMAGE", 6.1, 60),
        ])
        time = _time_slot_analysis()
        hashtags = _hashtag_analysis()

        recs = service.generate_recommendations(content, time, hashtags)
        assert any("REEL" in r for r in recs)

    async def test_generates_time_slot_recommendation(
        self, service: FeedbackLoopService,
    ) -> None:
        content = _content_type_analysis()
        time = _time_slot_analysis([TimeSlot("Tuesday", 18, 8.5, 15)])
        hashtags = _hashtag_analysis()

        recs = service.generate_recommendations(content, time, hashtags)
        assert any("Tuesday" in r for r in recs)

    async def test_generates_hashtag_recommendation(
        self, service: FeedbackLoopService,
    ) -> None:
        content = _content_type_analysis()
        time = _time_slot_analysis()
        hashtags = _hashtag_analysis([HashtagRanking("#wellness", 8.5, 30)])

        recs = service.generate_recommendations(content, time, hashtags)
        assert any("#wellness" in r for r in recs)

    async def test_empty_rankings_no_crash(
        self, service: FeedbackLoopService,
    ) -> None:
        content = ContentTypeAnalysis(rankings=[], total_posts=0, insufficient_data=True)
        time = TimeSlotAnalysis(slots=[], top_slots=[], total_posts=0, insufficient_data=True)
        hashtags = HashtagAnalysis(rankings=[], total_posts=0, insufficient_data=True)

        recs = service.generate_recommendations(content, time, hashtags)
        assert isinstance(recs, list)

    async def test_recommendations_are_strings(
        self, service: FeedbackLoopService,
    ) -> None:
        content = _content_type_analysis()
        time = _time_slot_analysis()
        hashtags = _hashtag_analysis()

        recs = service.generate_recommendations(content, time, hashtags)
        for r in recs:
            assert isinstance(r, str)

    async def test_single_content_type_recommendation(
        self, service: FeedbackLoopService,
    ) -> None:
        """Single content type still generates a recommendation."""
        content = _content_type_analysis([ContentTypeRanking("IMAGE", 7.0, 100)])
        time = TimeSlotAnalysis(slots=[], top_slots=[], total_posts=0, insufficient_data=True)
        hashtags = HashtagAnalysis(rankings=[], total_posts=0, insufficient_data=True)

        recs = service.generate_recommendations(content, time, hashtags)
        assert any("IMAGE" in r for r in recs)


class TestMinPostsThreshold:
    """Tests for configurable min_posts_threshold."""

    async def test_custom_threshold_respected(
        self,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
        mock_quality_repo: AsyncMock,
    ) -> None:
        """Custom threshold of 200 rejects 150 posts."""
        cfg = _StubFeedbackLoopConfig(min_posts_threshold=200)
        svc = FeedbackLoopService(
            mock_content_analyzer, mock_weight_adjuster,
            mock_feedback_repo, mock_quality_repo, cfg,
        )
        mock_quality_repo.get_scored_count.return_value = 150
        mock_feedback_repo.save_report.side_effect = lambda r: r

        report = await svc.run_weekly_analysis()
        assert report.status == "partial"
        assert "insufficient_posts" in (report.missing_sections or [])

    async def test_report_stores_min_posts_threshold(
        self,
        service: FeedbackLoopService,
        mock_quality_repo: AsyncMock,
        mock_content_analyzer: AsyncMock,
        mock_weight_adjuster: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        _setup_happy_path(
            mock_quality_repo, mock_content_analyzer,
            mock_weight_adjuster, mock_feedback_repo,
        )
        report = await service.run_weekly_analysis()
        assert report.min_posts_threshold == 100
