"""Tests for source quality scoring component.

Tests:
    - SourceQualityScorer class creation with config injection
    - Source tier base scores: PubMed(8), News(6), YouTube(4), Reddit(3), Instagram(3)
    - PubMed study type bonuses: RCT(+2), Meta-analysis(+2), Systematic review(+1), Other(+0)
    - Extraction of study_type from source_metadata
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from teams.dawo.research.models import ResearchSource, ComplianceStatus
from teams.dawo.research.scoring.components.source_quality import (
    SourceQualityScorer,
    SourceQualityConfig,
    SOURCE_TIER_SCORES,
    PUBMED_STUDY_BONUSES,
)


@pytest.fixture
def default_source_quality_config() -> SourceQualityConfig:
    """Default source quality configuration."""
    return SourceQualityConfig()


@pytest.fixture
def source_quality_scorer(default_source_quality_config: SourceQualityConfig) -> SourceQualityScorer:
    """SourceQualityScorer with default configuration."""
    return SourceQualityScorer(config=default_source_quality_config)


class TestSourceQualityConfig:
    """Tests for SourceQualityConfig dataclass."""

    def test_default_source_tiers(self):
        """Config should have default source tier scores."""
        config = SourceQualityConfig()

        assert config.source_tiers["pubmed"] == 8
        assert config.source_tiers["news"] == 6
        assert config.source_tiers["youtube"] == 4
        assert config.source_tiers["reddit"] == 3
        assert config.source_tiers["instagram"] == 3

    def test_default_study_bonuses(self):
        """Config should have default PubMed study type bonuses."""
        config = SourceQualityConfig()

        assert config.study_bonuses["RCT"] == 2
        assert config.study_bonuses["meta-analysis"] == 2
        assert config.study_bonuses["systematic_review"] == 1


class TestSourceQualityScorer:
    """Tests for SourceQualityScorer class."""

    def test_create_with_config(self, default_source_quality_config: SourceQualityConfig):
        """SourceQualityScorer should accept config via constructor injection."""
        scorer = SourceQualityScorer(config=default_source_quality_config)
        assert scorer._config is not None

    def test_score_pubmed_source(self, source_quality_scorer: SourceQualityScorer):
        """PubMed source should score base 8."""
        item = _create_test_item(source=ResearchSource.PUBMED.value)

        result = source_quality_scorer.score(item)

        assert result.raw_score == 8.0

    def test_score_news_source(self, source_quality_scorer: SourceQualityScorer):
        """News source should score 6."""
        item = _create_test_item(source=ResearchSource.NEWS.value)

        result = source_quality_scorer.score(item)

        assert result.raw_score == 6.0

    def test_score_youtube_source(self, source_quality_scorer: SourceQualityScorer):
        """YouTube source should score 4."""
        item = _create_test_item(source=ResearchSource.YOUTUBE.value)

        result = source_quality_scorer.score(item)

        assert result.raw_score == 4.0

    def test_score_reddit_source(self, source_quality_scorer: SourceQualityScorer):
        """Reddit source should score 3."""
        item = _create_test_item(source=ResearchSource.REDDIT.value)

        result = source_quality_scorer.score(item)

        assert result.raw_score == 3.0

    def test_score_instagram_source(self, source_quality_scorer: SourceQualityScorer):
        """Instagram source should score 3."""
        item = _create_test_item(source=ResearchSource.INSTAGRAM.value)

        result = source_quality_scorer.score(item)

        assert result.raw_score == 3.0

    def test_score_pubmed_rct_study(self, source_quality_scorer: SourceQualityScorer):
        """PubMed RCT study should score 10 (8 + 2 bonus)."""
        item = _create_test_item(
            source=ResearchSource.PUBMED.value,
            source_metadata={"study_type": "RCT"},
        )

        result = source_quality_scorer.score(item)

        assert result.raw_score == 10.0

    def test_score_pubmed_meta_analysis(self, source_quality_scorer: SourceQualityScorer):
        """PubMed meta-analysis should score 10 (8 + 2 bonus)."""
        item = _create_test_item(
            source=ResearchSource.PUBMED.value,
            source_metadata={"study_type": "meta-analysis"},
        )

        result = source_quality_scorer.score(item)

        assert result.raw_score == 10.0

    def test_score_pubmed_systematic_review(self, source_quality_scorer: SourceQualityScorer):
        """PubMed systematic review should score 9 (8 + 1 bonus)."""
        item = _create_test_item(
            source=ResearchSource.PUBMED.value,
            source_metadata={"study_type": "systematic_review"},
        )

        result = source_quality_scorer.score(item)

        assert result.raw_score == 9.0

    def test_score_pubmed_other_study_type(self, source_quality_scorer: SourceQualityScorer):
        """PubMed other study type should score 8 (no bonus)."""
        item = _create_test_item(
            source=ResearchSource.PUBMED.value,
            source_metadata={"study_type": "observational"},
        )

        result = source_quality_scorer.score(item)

        assert result.raw_score == 8.0

    def test_score_unknown_source_defaults_to_5(self, source_quality_scorer: SourceQualityScorer):
        """Unknown source should default to score 5."""
        item = _create_test_item(source="unknown_source")

        result = source_quality_scorer.score(item)

        assert result.raw_score == 5.0

    def test_score_includes_component_name(self, source_quality_scorer: SourceQualityScorer):
        """Result should include component name."""
        item = _create_test_item(source=ResearchSource.REDDIT.value)

        result = source_quality_scorer.score(item)

        assert result.component_name == "source_quality"

    def test_score_includes_notes(self, source_quality_scorer: SourceQualityScorer):
        """Result notes should mention source."""
        item = _create_test_item(source=ResearchSource.PUBMED.value)

        result = source_quality_scorer.score(item)

        assert "pubmed" in result.notes.lower()


class TestSourceQualityConstants:
    """Tests for source quality scoring constants."""

    def test_source_tier_scores(self):
        """SOURCE_TIER_SCORES should have correct values."""
        assert SOURCE_TIER_SCORES["pubmed"] == 8
        assert SOURCE_TIER_SCORES["news"] == 6
        assert SOURCE_TIER_SCORES["youtube"] == 4
        assert SOURCE_TIER_SCORES["reddit"] == 3
        assert SOURCE_TIER_SCORES["instagram"] == 3

    def test_pubmed_study_bonuses(self):
        """PUBMED_STUDY_BONUSES should have correct values."""
        assert PUBMED_STUDY_BONUSES["RCT"] == 2
        assert PUBMED_STUDY_BONUSES["meta-analysis"] == 2
        assert PUBMED_STUDY_BONUSES["systematic_review"] == 1


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
