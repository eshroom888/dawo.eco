"""Content performance analysis for feedback loop.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 3: ContentPerformanceAnalyzer — content types, posting times, hashtags.
AC3: Source performance tracking by research source_type.

Analyzes post-publish performance data to identify patterns in:
- Content type effectiveness (IMAGE vs VIDEO vs CAROUSEL_ALBUM)
- Optimal posting times (day-of-week + hour heatmap)
- Hashtag performance (which hashtags correlate with higher scores)
- Source performance (which research sources produce best-performing content)

All analysis is pure Python — no external ML/data libraries.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from core.analytics.quality_scoring_repository import QualityScoringRepository
from core.analytics.repository import InstagramMetricsRepository

logger = logging.getLogger(__name__)

# Days of week for time slot analysis
_DAYS_OF_WEEK = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

# Regex for hashtag extraction
_HASHTAG_PATTERN = re.compile(r"#\w+")

# Default max records to analyze (overridable via parameter)
DEFAULT_ANALYSIS_LIMIT = 2000


@dataclass(frozen=True)
class ContentTypeRanking:
    """Ranking entry for a content type.

    Task 3.4: Frozen dataclass for content type performance.
    """

    content_type: str
    avg_score: float
    count: int
    trend_direction: str = "stable"  # "up", "down", or "stable"


@dataclass(frozen=True)
class ContentTypeAnalysis:
    """Analysis of content type performance.

    Task 3.1: Groups scored posts by content type and ranks them.
    """

    rankings: list[ContentTypeRanking]
    total_posts: int
    insufficient_data: bool = False


@dataclass(frozen=True)
class TimeSlot:
    """A day+hour time slot with average performance.

    Task 3.4: Frozen dataclass for time slot analysis.
    """

    day_of_week: str
    hour: int
    avg_score: float
    count: int


@dataclass(frozen=True)
class TimeSlotAnalysis:
    """Analysis of posting time performance.

    Task 3.2: Heatmap of avg scores by day-of-week and hour.
    """

    slots: list[TimeSlot]
    top_slots: list[TimeSlot]
    total_posts: int
    insufficient_data: bool = False


@dataclass(frozen=True)
class HashtagRanking:
    """Ranking entry for a hashtag.

    Task 3.4: Frozen dataclass for hashtag performance.
    """

    hashtag: str
    avg_score: float
    count: int


@dataclass(frozen=True)
class HashtagAnalysis:
    """Analysis of hashtag performance.

    Task 3.3: Top hashtags ranked by associated post performance.
    """

    rankings: list[HashtagRanking]
    total_posts: int
    insufficient_data: bool = False


@dataclass(frozen=True)
class SourceRanking:
    """Ranking entry for a research source type.

    AC3: Tracks which research sources produce best-performing content.
    """

    source_type: str
    avg_score: float
    count: int
    weight_adjustment: float = 0.0  # positive = boost, negative = penalty


@dataclass(frozen=True)
class SourcePerformanceAnalysis:
    """Analysis of research source performance.

    AC3: Source performance tracking by research source_type.
    High-performers get +weight, low-performers get -weight.
    """

    rankings: list[SourceRanking]
    overall_avg: float
    total_posts: int
    insufficient_data: bool = False


class ContentPerformanceAnalyzer:
    """Analyzes content performance across dimensions.

    Story 7-5, Task 3: Analyzes content type, posting time, hashtag,
    and source performance from post-publish scoring data.

    Constructor injection of repositories for testability.
    """

    def __init__(
        self,
        quality_scoring_repository: QualityScoringRepository,
        instagram_metrics_repository: InstagramMetricsRepository,
    ) -> None:
        """Initialize with data repositories.

        Args:
            quality_scoring_repository: Access to post-publish scores.
            instagram_metrics_repository: Access to Instagram metrics.
        """
        self._quality_repo = quality_scoring_repository
        self._metrics_repo = instagram_metrics_repository

    async def analyze_content_types(
        self, min_posts: int = 100, limit: int = DEFAULT_ANALYSIS_LIMIT
    ) -> ContentTypeAnalysis:
        """Analyze performance by content type.

        Task 3.1: Groups scored posts by media_type from Instagram metrics.
        Falls back to "UNKNOWN" when media_type unavailable.

        Args:
            min_posts: Minimum scored posts required to run analysis.
            limit: Maximum records to fetch for analysis.

        Returns:
            ContentTypeAnalysis with rankings sorted by avg_score desc.
        """
        count = await self._quality_repo.get_scored_count()
        if count < min_posts:
            logger.debug("Only %d scored posts, need %d+ for content type analysis", count, min_posts)
            return ContentTypeAnalysis(rankings=[], total_posts=count, insufficient_data=True)

        records = await self._quality_repo.get_all_scored(limit=limit)
        if not records:
            return ContentTypeAnalysis(rankings=[], total_posts=0, insufficient_data=True)

        # Batch query metrics for media_type extraction
        media_ids = [r.media_id for r in records if r.media_id]
        metrics_by_id = await self._metrics_repo.get_by_media_ids(media_ids) if media_ids else {}

        # Group scores by content type
        type_scores: dict[str, list[float]] = defaultdict(list)
        for record in records:
            media_type = "UNKNOWN"
            if record.media_id and record.media_id in metrics_by_id:
                metric_list = metrics_by_id[record.media_id]
                if metric_list:
                    first_metric = metric_list[0]
                    raw: dict = first_metric.raw_response if hasattr(first_metric, "raw_response") else {}
                    if raw is None:
                        raw = {}
                    media_type = raw.get("media_type", "UNKNOWN")
            type_scores[media_type].append(float(record.post_publish_score))

        # Compute overall average for trend comparison
        all_scores = [s for scores in type_scores.values() for s in scores]
        overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # Build rankings with trend direction
        rankings = [
            ContentTypeRanking(
                content_type=ct,
                avg_score=round(sum(scores) / len(scores), 1),
                count=len(scores),
                trend_direction=_compute_trend(scores, overall_avg),
            )
            for ct, scores in type_scores.items()
        ]
        rankings.sort(key=lambda r: r.avg_score, reverse=True)

        return ContentTypeAnalysis(
            rankings=rankings,
            total_posts=len(records),
        )

    async def analyze_posting_times(
        self, limit: int = DEFAULT_ANALYSIS_LIMIT
    ) -> TimeSlotAnalysis:
        """Analyze performance by posting time.

        Task 3.2: Joins PostPublishScoreRecord with InstagramMediaMetric
        via media_id. Uses baseline snapshot's collected_at minus ~1 hour
        to approximate publish time.

        Args:
            limit: Maximum records to fetch for analysis.

        Returns:
            TimeSlotAnalysis with heatmap slots and top 5 highlighted.
        """
        count = await self._quality_repo.get_scored_count()
        if count < 10:
            return TimeSlotAnalysis(
                slots=[], top_slots=[], total_posts=count, insufficient_data=True,
            )

        records = await self._quality_repo.get_all_scored(limit=limit)
        if not records:
            return TimeSlotAnalysis(
                slots=[], top_slots=[], total_posts=0, insufficient_data=True,
            )

        # Batch query metrics for publish time extraction
        media_ids = [r.media_id for r in records if r.media_id]
        metrics_by_id = await self._metrics_repo.get_by_media_ids(media_ids) if media_ids else {}

        # Group scores by day_of_week + hour
        slot_scores: dict[tuple[str, int], list[float]] = defaultdict(list)
        for record in records:
            if not record.media_id or record.media_id not in metrics_by_id:
                continue
            metric_list = metrics_by_id[record.media_id]
            if not metric_list:
                continue

            # Use earliest snapshot (baseline) as approximate publish time
            earliest = min(metric_list, key=lambda m: m.collected_at)
            publish_approx = earliest.collected_at
            day_name = _DAYS_OF_WEEK[publish_approx.weekday()]
            hour = publish_approx.hour

            slot_scores[(day_name, hour)].append(float(record.post_publish_score))

        # Build slots
        slots = [
            TimeSlot(
                day_of_week=day,
                hour=hour,
                avg_score=round(sum(scores) / len(scores), 1),
                count=len(scores),
            )
            for (day, hour), scores in slot_scores.items()
        ]
        slots.sort(key=lambda s: s.avg_score, reverse=True)

        # Top 5 slots
        top_slots = slots[:5]

        return TimeSlotAnalysis(
            slots=slots,
            top_slots=top_slots,
            total_posts=len(records),
        )

    async def analyze_hashtags(
        self,
        min_hashtag_posts: int = 3,
        top_limit: int = 20,
        limit: int = DEFAULT_ANALYSIS_LIMIT,
    ) -> HashtagAnalysis:
        """Analyze performance by hashtag.

        Task 3.3: Extracts hashtags from metrics_snapshot.caption,
        groups by individual hashtag, computes avg post score per hashtag.

        Args:
            min_hashtag_posts: Minimum posts per hashtag to qualify.
            top_limit: Maximum hashtags to return.
            limit: Maximum records to fetch for analysis.

        Returns:
            HashtagAnalysis with rankings sorted by avg_score desc.
        """
        count = await self._quality_repo.get_scored_count()
        if count < 10:
            return HashtagAnalysis(rankings=[], total_posts=count, insufficient_data=True)

        records = await self._quality_repo.get_all_scored(limit=limit)
        if not records:
            return HashtagAnalysis(rankings=[], total_posts=0, insufficient_data=True)

        # Extract hashtags from metrics_snapshot caption
        hashtag_scores: dict[str, list[float]] = defaultdict(list)
        posts_with_hashtags = 0

        for record in records:
            caption = record.metrics_snapshot.get("caption", "")
            if not caption:
                continue
            tags = _HASHTAG_PATTERN.findall(caption)
            if not tags:
                continue
            posts_with_hashtags += 1
            score = float(record.post_publish_score)
            for tag in set(tags):  # dedupe within same post
                hashtag_scores[tag.lower()].append(score)

        if not hashtag_scores:
            return HashtagAnalysis(
                rankings=[], total_posts=len(records), insufficient_data=True,
            )

        # Filter by minimum posts and build rankings
        rankings = [
            HashtagRanking(
                hashtag=tag,
                avg_score=round(sum(scores) / len(scores), 1),
                count=len(scores),
            )
            for tag, scores in hashtag_scores.items()
            if len(scores) >= min_hashtag_posts
        ]
        rankings.sort(key=lambda r: r.avg_score, reverse=True)

        # Limit to top N
        rankings = rankings[:top_limit]

        return HashtagAnalysis(
            rankings=rankings,
            total_posts=len(records),
        )

    async def analyze_source_performance(
        self, limit: int = DEFAULT_ANALYSIS_LIMIT
    ) -> SourcePerformanceAnalysis:
        """Analyze performance by research source type.

        AC3: Tracks which research sources produce best content post-publish.
        Extracts source_type from metrics_snapshot (populated during scoring).
        High-performers get +weight boost, low-performers get -weight.

        Args:
            limit: Maximum records to fetch for analysis.

        Returns:
            SourcePerformanceAnalysis with rankings and weight adjustments.
        """
        count = await self._quality_repo.get_scored_count()
        if count < 10:
            return SourcePerformanceAnalysis(
                rankings=[], overall_avg=0.0, total_posts=count,
                insufficient_data=True,
            )

        records = await self._quality_repo.get_all_scored(limit=limit)
        if not records:
            return SourcePerformanceAnalysis(
                rankings=[], overall_avg=0.0, total_posts=0,
                insufficient_data=True,
            )

        # Group scores by source_type from metrics_snapshot
        source_scores: dict[str, list[float]] = defaultdict(list)
        for record in records:
            source_type = record.metrics_snapshot.get("source_type", "")
            if not source_type:
                continue
            source_scores[source_type].append(float(record.post_publish_score))

        if not source_scores:
            logger.debug("No source_type data in metrics_snapshot — insufficient data")
            return SourcePerformanceAnalysis(
                rankings=[], overall_avg=0.0, total_posts=len(records),
                insufficient_data=True,
            )

        # Compute overall average for weight adjustment calculation
        all_scores = [s for scores in source_scores.values() for s in scores]
        overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # Build rankings with weight adjustments
        rankings = [
            SourceRanking(
                source_type=src,
                avg_score=round(sum(scores) / len(scores), 1),
                count=len(scores),
                weight_adjustment=_compute_weight_adjustment(scores, overall_avg),
            )
            for src, scores in source_scores.items()
        ]
        rankings.sort(key=lambda r: r.avg_score, reverse=True)

        return SourcePerformanceAnalysis(
            rankings=rankings,
            overall_avg=round(overall_avg, 1),
            total_posts=len(records),
        )


def _compute_trend(scores: list[float], overall_avg: float) -> str:
    """Compute trend direction relative to overall average.

    Returns "up" if type avg is >5% above overall, "down" if >5% below,
    "stable" otherwise.
    """
    if not scores or overall_avg == 0:
        return "stable"
    type_avg = sum(scores) / len(scores)
    delta_pct = (type_avg - overall_avg) / overall_avg
    if delta_pct > 0.05:
        return "up"
    if delta_pct < -0.05:
        return "down"
    return "stable"


def _compute_weight_adjustment(scores: list[float], overall_avg: float) -> float:
    """Compute source weight adjustment based on performance vs average.

    AC3: High-performers get +weight boost, low-performers get -weight.
    Scale: proportional to deviation from mean, capped at +/-0.2.
    """
    if not scores or overall_avg == 0:
        return 0.0
    source_avg = sum(scores) / len(scores)
    delta = (source_avg - overall_avg) / overall_avg
    # Cap at +/-0.2
    return round(max(-0.2, min(0.2, delta)), 3)


__all__ = [
    "ContentPerformanceAnalyzer",
    "ContentTypeAnalysis",
    "ContentTypeRanking",
    "HashtagAnalysis",
    "HashtagRanking",
    "SourcePerformanceAnalysis",
    "SourceRanking",
    "TimeSlot",
    "TimeSlotAnalysis",
]
