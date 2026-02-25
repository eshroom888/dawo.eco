"""Tests for ContentPerformanceAnalyzer.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 3.5: Write analyzer tests (target: 25+ tests covering all three
dimensions, edge cases, insufficient data).
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.analytics.content_performance_analyzer import (
    ContentPerformanceAnalyzer,
    ContentTypeAnalysis,
    ContentTypeRanking,
    HashtagAnalysis,
    HashtagRanking,
    SourcePerformanceAnalysis,
    SourceRanking,
    TimeSlot,
    TimeSlotAnalysis,
)
from core.analytics.quality_scoring_models import PostPublishScoreRecord


def _make_score_record(
    post_id: str = "post-1",
    media_id: str = "media-1",
    score: float = 7.0,
    metrics_snapshot: dict | None = None,
) -> PostPublishScoreRecord:
    """Create a PostPublishScoreRecord for testing."""
    return PostPublishScoreRecord(
        post_id=post_id,
        media_id=media_id,
        post_publish_score=Decimal(str(score)),
        variance=Decimal("0"),
        component_scores={},
        metrics_snapshot=metrics_snapshot or {},
        calculated_at=datetime.now(UTC),
    )


def _make_metric(
    media_id: str = "media-1",
    collected_at: datetime | None = None,
    snapshot_label: str = "baseline",
) -> MagicMock:
    """Create a mock InstagramMediaMetric."""
    metric = MagicMock()
    metric.media_id = media_id
    metric.collected_at = collected_at or datetime(2026, 2, 18, 14, 0, tzinfo=UTC)
    metric.snapshot_label = snapshot_label
    return metric


@pytest.fixture
def mock_quality_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_metrics_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def analyzer(
    mock_quality_repo: AsyncMock, mock_metrics_repo: AsyncMock
) -> ContentPerformanceAnalyzer:
    return ContentPerformanceAnalyzer(mock_quality_repo, mock_metrics_repo)


# ============================================================
# ContentTypeAnalysis tests (Task 3.1)
# ============================================================


class TestAnalyzeContentTypes:
    """Tests for analyze_content_types method."""

    async def test_groups_by_media_type(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
        mock_metrics_repo: AsyncMock,
    ) -> None:
        """Groups posts by media_type from InstagramMediaMetric."""
        records = [
            _make_score_record("p1", "m1", 8.0),
            _make_score_record("p2", "m2", 6.0),
            _make_score_record("p3", "m3", 9.0),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        # Mock metrics with media types
        metric1 = _make_metric("m1")
        metric1.raw_response = {"media_type": "VIDEO"}
        metric2 = _make_metric("m2")
        metric2.raw_response = {"media_type": "IMAGE"}
        metric3 = _make_metric("m3")
        metric3.raw_response = {"media_type": "VIDEO"}
        mock_metrics_repo.get_by_media_ids.return_value = {
            "m1": [metric1], "m2": [metric2], "m3": [metric3],
        }

        result = await analyzer.analyze_content_types(min_posts=3)

        assert isinstance(result, ContentTypeAnalysis)
        assert len(result.rankings) >= 1
        # VIDEO should have 2 posts with avg (8+9)/2 = 8.5
        video_rank = next(
            (r for r in result.rankings if r.content_type == "VIDEO"), None
        )
        assert video_rank is not None
        assert video_rank.count == 2
        assert video_rank.avg_score == pytest.approx(8.5, abs=0.1)

    async def test_insufficient_posts_returns_empty(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 5

        result = await analyzer.analyze_content_types(min_posts=100)

        assert isinstance(result, ContentTypeAnalysis)
        assert result.rankings == []
        assert result.insufficient_data is True

    async def test_ranks_by_avg_score_descending(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
        mock_metrics_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 5.0),
            _make_score_record("p2", "m2", 9.0),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        metric1 = _make_metric("m1")
        metric1.raw_response = {"media_type": "IMAGE"}
        metric2 = _make_metric("m2")
        metric2.raw_response = {"media_type": "VIDEO"}
        mock_metrics_repo.get_by_media_ids.return_value = {
            "m1": [metric1], "m2": [metric2],
        }

        result = await analyzer.analyze_content_types(min_posts=2)
        assert result.rankings[0].content_type == "VIDEO"

    async def test_missing_media_type_classified_as_unknown(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
        mock_metrics_repo: AsyncMock,
    ) -> None:
        records = [_make_score_record("p1", "m1", 7.0)]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        metric1 = _make_metric("m1")
        metric1.raw_response = {}
        mock_metrics_repo.get_by_media_ids.return_value = {"m1": [metric1]}

        result = await analyzer.analyze_content_types(min_posts=1)
        assert result.rankings[0].content_type == "UNKNOWN"

    async def test_no_metrics_match_returns_unknown(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
        mock_metrics_repo: AsyncMock,
    ) -> None:
        records = [_make_score_record("p1", "m1", 7.0)]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100
        mock_metrics_repo.get_by_media_ids.return_value = {}

        result = await analyzer.analyze_content_types(min_posts=1)
        assert result.rankings[0].content_type == "UNKNOWN"


# ============================================================
# TimeSlotAnalysis tests (Task 3.2)
# ============================================================


class TestAnalyzePostingTimes:
    """Tests for analyze_posting_times method."""

    async def test_groups_by_day_and_hour(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
        mock_metrics_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 8.0),
            _make_score_record("p2", "m2", 6.0),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        # Tuesday 14:00, Wednesday 10:00
        metric1 = _make_metric("m1", collected_at=datetime(2026, 2, 17, 14, 0, tzinfo=UTC))
        metric2 = _make_metric("m2", collected_at=datetime(2026, 2, 18, 10, 0, tzinfo=UTC))
        mock_metrics_repo.get_by_media_ids.return_value = {
            "m1": [metric1], "m2": [metric2],
        }

        result = await analyzer.analyze_posting_times()

        assert isinstance(result, TimeSlotAnalysis)
        assert len(result.slots) >= 1

    async def test_top_slots_limited_to_five(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
        mock_metrics_repo: AsyncMock,
    ) -> None:
        # Create 10 records with different times
        records = [
            _make_score_record(f"p{i}", f"m{i}", 5.0 + i * 0.5)
            for i in range(10)
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        metrics = {}
        for i in range(10):
            m = _make_metric(
                f"m{i}",
                collected_at=datetime(2026, 2, 16 + (i % 7), 8 + i, tzinfo=UTC),
            )
            metrics[f"m{i}"] = [m]
        mock_metrics_repo.get_by_media_ids.return_value = metrics

        result = await analyzer.analyze_posting_times()
        assert len(result.top_slots) <= 5

    async def test_insufficient_data_returns_empty(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 5

        result = await analyzer.analyze_posting_times()
        assert result.slots == []
        assert result.insufficient_data is True

    async def test_slot_has_day_hour_and_avg_score(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
        mock_metrics_repo: AsyncMock,
    ) -> None:
        records = [_make_score_record("p1", "m1", 7.5)]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        metric = _make_metric("m1", collected_at=datetime(2026, 2, 17, 18, 0, tzinfo=UTC))
        mock_metrics_repo.get_by_media_ids.return_value = {"m1": [metric]}

        result = await analyzer.analyze_posting_times()
        if result.slots:
            slot = result.slots[0]
            assert isinstance(slot, TimeSlot)
            assert isinstance(slot.day_of_week, str)
            assert 0 <= slot.hour <= 23
            assert slot.avg_score > 0


# ============================================================
# HashtagAnalysis tests (Task 3.3)
# ============================================================


class TestAnalyzeHashtags:
    """Tests for analyze_hashtags method."""

    async def test_extracts_hashtags_from_metrics_snapshot(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 8.0, {"caption": "Great #wellness #health post"}),
            _make_score_record("p2", "m2", 6.0, {"caption": "Nice #wellness #food content"}),
            _make_score_record("p3", "m3", 7.0, {"caption": "Top #health #organic pick"}),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_hashtags(min_hashtag_posts=2, top_limit=20)

        assert isinstance(result, HashtagAnalysis)
        # #wellness appears in p1(8.0) and p2(6.0) → avg 7.0
        wellness = next((r for r in result.rankings if r.hashtag == "#wellness"), None)
        assert wellness is not None
        assert wellness.count == 2
        assert wellness.avg_score == pytest.approx(7.0, abs=0.1)

    async def test_min_hashtag_posts_filter(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 8.0, {"caption": "#rare tag"}),
            _make_score_record("p2", "m2", 6.0, {"caption": "#common #common2"}),
            _make_score_record("p3", "m3", 7.0, {"caption": "#common #common2"}),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_hashtags(min_hashtag_posts=2, top_limit=20)

        # #rare only appears once, should be filtered out
        rare = next((r for r in result.rankings if r.hashtag == "#rare"), None)
        assert rare is None

    async def test_top_limit_respected(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        # 5 hashtags, limit to top 3
        records = [
            _make_score_record(f"p{i}", f"m{i}", 7.0, {"caption": f"#tag{i % 3} post"})
            for i in range(9)
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_hashtags(min_hashtag_posts=1, top_limit=2)
        assert len(result.rankings) <= 2

    async def test_no_captions_returns_insufficient_data(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 7.0, {}),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_hashtags(min_hashtag_posts=3, top_limit=20)
        assert result.insufficient_data is True

    async def test_insufficient_posts_returns_empty(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 5

        result = await analyzer.analyze_hashtags(min_hashtag_posts=3, top_limit=20)
        assert result.rankings == []
        assert result.insufficient_data is True

    async def test_ranks_by_avg_score_descending(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 9.0, {"caption": "#best post"}),
            _make_score_record("p2", "m2", 8.0, {"caption": "#best again"}),
            _make_score_record("p3", "m3", 4.0, {"caption": "#worst post"}),
            _make_score_record("p4", "m4", 3.0, {"caption": "#worst again"}),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_hashtags(min_hashtag_posts=2, top_limit=20)
        if len(result.rankings) >= 2:
            assert result.rankings[0].avg_score >= result.rankings[1].avg_score


# ============================================================
# SourcePerformanceAnalysis tests (AC3)
# ============================================================


class TestAnalyzeSourcePerformance:
    """Tests for analyze_source_performance method (AC3)."""

    async def test_groups_by_source_type(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 8.0, {"source_type": "instagram_trending"}),
            _make_score_record("p2", "m2", 6.0, {"source_type": "google_news"}),
            _make_score_record("p3", "m3", 9.0, {"source_type": "instagram_trending"}),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_source_performance()

        assert isinstance(result, SourcePerformanceAnalysis)
        ig = next((r for r in result.rankings if r.source_type == "instagram_trending"), None)
        assert ig is not None
        assert ig.count == 2
        assert ig.avg_score == pytest.approx(8.5, abs=0.1)

    async def test_insufficient_posts_returns_empty(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        mock_quality_repo.get_scored_count.return_value = 5

        result = await analyzer.analyze_source_performance()
        assert result.rankings == []
        assert result.insufficient_data is True

    async def test_no_source_type_data_returns_insufficient(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [_make_score_record("p1", "m1", 7.0, {})]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_source_performance()
        assert result.insufficient_data is True

    async def test_ranks_by_avg_score_descending(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 9.0, {"source_type": "instagram_trending"}),
            _make_score_record("p2", "m2", 5.0, {"source_type": "google_news"}),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_source_performance()
        assert result.rankings[0].source_type == "instagram_trending"

    async def test_weight_adjustment_positive_for_above_average(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 9.0, {"source_type": "top_source"}),
            _make_score_record("p2", "m2", 5.0, {"source_type": "low_source"}),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_source_performance()
        top = next(r for r in result.rankings if r.source_type == "top_source")
        low = next(r for r in result.rankings if r.source_type == "low_source")
        assert top.weight_adjustment > 0
        assert low.weight_adjustment < 0

    async def test_overall_avg_computed(
        self, analyzer: ContentPerformanceAnalyzer, mock_quality_repo: AsyncMock,
    ) -> None:
        records = [
            _make_score_record("p1", "m1", 8.0, {"source_type": "a"}),
            _make_score_record("p2", "m2", 6.0, {"source_type": "b"}),
        ]
        mock_quality_repo.get_all_scored.return_value = records
        mock_quality_repo.get_scored_count.return_value = 100

        result = await analyzer.analyze_source_performance()
        assert result.overall_avg == pytest.approx(7.0, abs=0.1)


# ============================================================
# DTO tests (Task 3.4)
# ============================================================


class TestDTOs:
    """Tests for frozen dataclass DTOs."""

    def test_content_type_ranking_frozen(self) -> None:
        ranking = ContentTypeRanking(content_type="VIDEO", avg_score=8.2, count=50)
        with pytest.raises(AttributeError):
            ranking.avg_score = 9.0  # type: ignore[misc]

    def test_content_type_ranking_trend_direction_default(self) -> None:
        ranking = ContentTypeRanking(content_type="VIDEO", avg_score=8.2, count=50)
        assert ranking.trend_direction == "stable"

    def test_content_type_ranking_trend_direction_custom(self) -> None:
        ranking = ContentTypeRanking(
            content_type="VIDEO", avg_score=8.2, count=50, trend_direction="up",
        )
        assert ranking.trend_direction == "up"

    def test_time_slot_frozen(self) -> None:
        slot = TimeSlot(day_of_week="Tuesday", hour=18, avg_score=7.8, count=10)
        with pytest.raises(AttributeError):
            slot.hour = 20  # type: ignore[misc]

    def test_hashtag_ranking_frozen(self) -> None:
        ranking = HashtagRanking(hashtag="#wellness", avg_score=7.5, count=25)
        with pytest.raises(AttributeError):
            ranking.count = 30  # type: ignore[misc]

    def test_content_type_analysis_frozen(self) -> None:
        analysis = ContentTypeAnalysis(rankings=[], total_posts=0, insufficient_data=True)
        with pytest.raises(AttributeError):
            analysis.total_posts = 100  # type: ignore[misc]

    def test_time_slot_analysis_frozen(self) -> None:
        analysis = TimeSlotAnalysis(slots=[], top_slots=[], total_posts=0, insufficient_data=True)
        with pytest.raises(AttributeError):
            analysis.total_posts = 100  # type: ignore[misc]

    def test_hashtag_analysis_frozen(self) -> None:
        analysis = HashtagAnalysis(rankings=[], total_posts=0, insufficient_data=True)
        with pytest.raises(AttributeError):
            analysis.total_posts = 100  # type: ignore[misc]

    def test_source_ranking_frozen(self) -> None:
        ranking = SourceRanking(
            source_type="instagram_trending", avg_score=8.0, count=20,
            weight_adjustment=0.1,
        )
        with pytest.raises(AttributeError):
            ranking.avg_score = 9.0  # type: ignore[misc]

    def test_source_ranking_default_weight_adjustment(self) -> None:
        ranking = SourceRanking(source_type="test", avg_score=7.0, count=10)
        assert ranking.weight_adjustment == 0.0

    def test_source_performance_analysis_frozen(self) -> None:
        analysis = SourcePerformanceAnalysis(
            rankings=[], overall_avg=0.0, total_posts=0, insufficient_data=True,
        )
        with pytest.raises(AttributeError):
            analysis.total_posts = 100  # type: ignore[misc]
