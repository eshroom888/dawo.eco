"""Tests for engagement scoring component.

Tests:
    - EngagementScorer class creation with config injection
    - Per-source engagement metrics extraction
    - Normalization to 0-10 scale
    - Reddit: 100+ upvotes = 10, linear scale
    - YouTube: 10,000+ views = 10, log scale
    - Instagram: 500+ likes = 10, linear scale
    - PubMed: 50+ citations = 10, linear scale
    - News: Default score 5 (no engagement metrics)
    - Missing engagement data defaults to 5
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from teams.dawo.research.models import ResearchSource, ComplianceStatus
from teams.dawo.research.scoring.components.engagement import (
    EngagementScorer,
    EngagementConfig,
    DEFAULT_ENGAGEMENT_SCORE,
)


@pytest.fixture
def default_engagement_config() -> EngagementConfig:
    """Default engagement configuration."""
    return EngagementConfig()


@pytest.fixture
def engagement_scorer(default_engagement_config: EngagementConfig) -> EngagementScorer:
    """EngagementScorer with default configuration."""
    return EngagementScorer(config=default_engagement_config)


class TestEngagementConfig:
    """Tests for EngagementConfig dataclass."""

    def test_default_thresholds(self):
        """Config should have default engagement thresholds."""
        config = EngagementConfig()

        assert config.reddit_max_upvotes == 100
        assert config.youtube_max_views == 10000
        assert config.instagram_max_likes == 500
        assert config.pubmed_max_citations == 50


class TestEngagementScorer:
    """Tests for EngagementScorer class."""

    def test_create_with_config(self, default_engagement_config: EngagementConfig):
        """EngagementScorer should accept config via constructor injection."""
        scorer = EngagementScorer(config=default_engagement_config)
        assert scorer._config is not None

    # Reddit tests
    def test_score_reddit_max_engagement(self, engagement_scorer: EngagementScorer):
        """Reddit with 100+ upvotes should score 10."""
        item = _create_test_item(
            source=ResearchSource.REDDIT.value,
            source_metadata={"upvotes": 150},
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == 10.0

    def test_score_reddit_half_engagement(self, engagement_scorer: EngagementScorer):
        """Reddit with 50 upvotes should score 5 (linear scale)."""
        item = _create_test_item(
            source=ResearchSource.REDDIT.value,
            source_metadata={"upvotes": 50},
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == 5.0

    def test_score_reddit_zero_engagement(self, engagement_scorer: EngagementScorer):
        """Reddit with 0 upvotes should score 0."""
        item = _create_test_item(
            source=ResearchSource.REDDIT.value,
            source_metadata={"upvotes": 0},
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == 0.0

    # Instagram tests
    def test_score_instagram_max_engagement(self, engagement_scorer: EngagementScorer):
        """Instagram with 500+ likes should score 10."""
        item = _create_test_item(
            source=ResearchSource.INSTAGRAM.value,
            source_metadata={"likes": 600},
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == 10.0

    def test_score_instagram_half_engagement(self, engagement_scorer: EngagementScorer):
        """Instagram with 250 likes should score 5 (linear scale)."""
        item = _create_test_item(
            source=ResearchSource.INSTAGRAM.value,
            source_metadata={"likes": 250},
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == 5.0

    # PubMed tests
    def test_score_pubmed_max_engagement(self, engagement_scorer: EngagementScorer):
        """PubMed with 50+ citations should score 10."""
        item = _create_test_item(
            source=ResearchSource.PUBMED.value,
            source_metadata={"citation_count": 75},
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == 10.0

    def test_score_pubmed_half_engagement(self, engagement_scorer: EngagementScorer):
        """PubMed with 25 citations should score 5 (linear scale)."""
        item = _create_test_item(
            source=ResearchSource.PUBMED.value,
            source_metadata={"citation_count": 25},
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == 5.0

    # YouTube tests (log scale)
    def test_score_youtube_max_engagement(self, engagement_scorer: EngagementScorer):
        """YouTube with 10,000+ views should score 10."""
        item = _create_test_item(
            source=ResearchSource.YOUTUBE.value,
            source_metadata={"views": 15000},
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == 10.0

    def test_score_youtube_log_scale(self, engagement_scorer: EngagementScorer):
        """YouTube engagement should use log scale."""
        item = _create_test_item(
            source=ResearchSource.YOUTUBE.value,
            source_metadata={"views": 1000},  # 10% of max, but log scale
        )

        result = engagement_scorer.score(item)

        # Log scale: log10(1000) / log10(10000) * 10 = 3/4 * 10 = 7.5
        assert 7.0 <= result.raw_score <= 8.0

    # News tests
    def test_score_news_default(self, engagement_scorer: EngagementScorer):
        """News source should default to score 5 (no engagement metrics)."""
        item = _create_test_item(source=ResearchSource.NEWS.value)

        result = engagement_scorer.score(item)

        assert result.raw_score == DEFAULT_ENGAGEMENT_SCORE

    # Missing data tests
    def test_score_missing_engagement_data(self, engagement_scorer: EngagementScorer):
        """Missing engagement data should default to 5."""
        item = _create_test_item(
            source=ResearchSource.REDDIT.value,
            source_metadata={},  # No upvotes
        )

        result = engagement_scorer.score(item)

        assert result.raw_score == DEFAULT_ENGAGEMENT_SCORE

    def test_score_includes_component_name(self, engagement_scorer: EngagementScorer):
        """Result should include component name."""
        item = _create_test_item(source=ResearchSource.REDDIT.value)

        result = engagement_scorer.score(item)

        assert result.component_name == "engagement"


class TestEngagementConstants:
    """Tests for engagement scoring constants."""

    def test_default_engagement_score(self):
        """Default engagement score should be 5."""
        assert DEFAULT_ENGAGEMENT_SCORE == 5.0


def _create_test_item(
    source: str,
    source_metadata: dict = None,
) -> dict:
    """Create a test research item dictionary for scoring.

    Args:
        source: Research source.
        source_metadata: Optional source-specific metadata.

    Returns:
        Dictionary with item data for scoring.
    """
    return {
        "id": uuid4(),
        "source": source,
        "title": "Test article",
        "content": "Test content.",
        "url": "https://example.com/test",
        "tags": [],
        "source_metadata": source_metadata or {},
        "created_at": datetime.now(timezone.utc),
        "score": 0.0,
        "compliance_status": ComplianceStatus.COMPLIANT.value,
    }
