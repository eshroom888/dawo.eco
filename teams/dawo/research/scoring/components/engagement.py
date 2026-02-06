"""Engagement scoring component for research items.

Scores items based on engagement metrics per source:
- Reddit: upvotes (100+ = 10, linear scale)
- YouTube: views (10,000+ = 10, log scale)
- Instagram: likes (500+ = 10, linear scale)
- PubMed: citations (50+ = 10, linear scale)
- News: Default score 5 (no engagement metrics)

Missing engagement data defaults to 5.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from ..schemas import ComponentScore

logger = logging.getLogger(__name__)

# Default engagement score for missing data or sources without metrics
DEFAULT_ENGAGEMENT_SCORE: float = 5.0

# Max engagement score
MAX_ENGAGEMENT_SCORE: float = 10.0

# Min engagement score
MIN_ENGAGEMENT_SCORE: float = 0.0


@dataclass
class EngagementConfig:
    """Configuration for engagement scoring.

    Attributes:
        reddit_max_upvotes: Upvotes for max score (default 100).
        youtube_max_views: Views for max score (default 10000).
        instagram_max_likes: Likes for max score (default 500).
        pubmed_max_citations: Citations for max score (default 50).
    """

    reddit_max_upvotes: int = 100
    youtube_max_views: int = 10000
    instagram_max_likes: int = 500
    pubmed_max_citations: int = 50


class EngagementScorer:
    """Scores research items based on engagement metrics.

    Uses source-specific metrics and normalization:
    - Reddit: Linear scale based on upvotes
    - YouTube: Log scale based on views
    - Instagram: Linear scale based on likes
    - PubMed: Linear scale based on citations
    - News: Default score (no metrics)

    Attributes:
        _config: EngagementConfig with threshold settings.
    """

    def __init__(self, config: EngagementConfig) -> None:
        """Initialize with configuration.

        Args:
            config: EngagementConfig with threshold settings.
        """
        self._config = config

    def score(self, item: dict[str, Any]) -> ComponentScore:
        """Calculate engagement score for a research item.

        Args:
            item: Dictionary with 'source' and 'source_metadata' fields.

        Returns:
            ComponentScore with engagement score (0-10).
        """
        source = item.get("source", "").lower()
        source_metadata = item.get("source_metadata", {})

        raw_score, notes = self._calculate_score_for_source(source, source_metadata)

        logger.debug(f"Engagement score: {raw_score} for source={source}")

        return ComponentScore(
            component_name="engagement",
            raw_score=raw_score,
            notes=notes,
        )

    def _calculate_score_for_source(
        self, source: str, metadata: dict[str, Any]
    ) -> tuple[float, str]:
        """Calculate engagement score based on source type.

        Args:
            source: Research source type.
            metadata: Source-specific metadata.

        Returns:
            Tuple of (score, notes).
        """
        if source == "reddit":
            return self._score_reddit(metadata)
        elif source == "youtube":
            return self._score_youtube(metadata)
        elif source == "instagram":
            return self._score_instagram(metadata)
        elif source == "pubmed":
            return self._score_pubmed(metadata)
        elif source == "news":
            return DEFAULT_ENGAGEMENT_SCORE, "News source (no engagement metrics)"
        else:
            return DEFAULT_ENGAGEMENT_SCORE, f"Unknown source '{source}'"

    def _score_reddit(self, metadata: dict[str, Any]) -> tuple[float, str]:
        """Score Reddit engagement based on upvotes."""
        upvotes = metadata.get("upvotes")
        if upvotes is None:
            return DEFAULT_ENGAGEMENT_SCORE, "Missing upvotes data"

        score = self._linear_scale(upvotes, self._config.reddit_max_upvotes)
        return score, f"Reddit: {upvotes} upvotes"

    def _score_youtube(self, metadata: dict[str, Any]) -> tuple[float, str]:
        """Score YouTube engagement based on views (log scale)."""
        views = metadata.get("views")
        if views is None:
            return DEFAULT_ENGAGEMENT_SCORE, "Missing views data"

        score = self._log_scale(views, self._config.youtube_max_views)
        return score, f"YouTube: {views} views (log scale)"

    def _score_instagram(self, metadata: dict[str, Any]) -> tuple[float, str]:
        """Score Instagram engagement based on likes."""
        likes = metadata.get("likes")
        if likes is None:
            return DEFAULT_ENGAGEMENT_SCORE, "Missing likes data"

        score = self._linear_scale(likes, self._config.instagram_max_likes)
        return score, f"Instagram: {likes} likes"

    def _score_pubmed(self, metadata: dict[str, Any]) -> tuple[float, str]:
        """Score PubMed engagement based on citations."""
        citations = metadata.get("citation_count")
        if citations is None:
            return DEFAULT_ENGAGEMENT_SCORE, "Missing citation data"

        score = self._linear_scale(citations, self._config.pubmed_max_citations)
        return score, f"PubMed: {citations} citations"

    def _linear_scale(self, value: int, max_threshold: int) -> float:
        """Calculate linear scale score.

        Args:
            value: The engagement value.
            max_threshold: Value at which score reaches 10.

        Returns:
            Score from 0-10.
        """
        if value <= 0:
            return MIN_ENGAGEMENT_SCORE
        if value >= max_threshold:
            return MAX_ENGAGEMENT_SCORE

        return round((value / max_threshold) * MAX_ENGAGEMENT_SCORE, 2)

    def _log_scale(self, value: int, max_threshold: int) -> float:
        """Calculate logarithmic scale score.

        Args:
            value: The engagement value.
            max_threshold: Value at which score reaches 10.

        Returns:
            Score from 0-10.
        """
        if value <= 0:
            return MIN_ENGAGEMENT_SCORE
        if value >= max_threshold:
            return MAX_ENGAGEMENT_SCORE

        # Log scale: log10(value) / log10(max) * 10
        log_value = math.log10(value)
        log_max = math.log10(max_threshold)
        score = (log_value / log_max) * MAX_ENGAGEMENT_SCORE

        return round(min(score, MAX_ENGAGEMENT_SCORE), 2)
