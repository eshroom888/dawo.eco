"""Tests for relevance scoring component.

Tests:
    - RelevanceScorer class creation with config injection
    - Primary keyword matching (mushroom types) with +2 bonus each (max +6)
    - Secondary keyword matching (wellness themes) with +1 bonus each (max +4)
    - Score calculation 0-10 based on match density
    - Case-insensitive matching
    - Matching in both title and content
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from teams.dawo.research.models import ResearchSource, ComplianceStatus
from teams.dawo.research.scoring.components.relevance import (
    RelevanceScorer,
    RelevanceConfig,
    PRIMARY_KEYWORD_BONUS,
    SECONDARY_KEYWORD_BONUS,
    MAX_PRIMARY_BONUS,
    MAX_SECONDARY_BONUS,
    MAX_SCORE,
)


# Test fixtures
@pytest.fixture
def default_relevance_config() -> RelevanceConfig:
    """Default relevance configuration with standard keywords."""
    return RelevanceConfig()


@pytest.fixture
def relevance_scorer(default_relevance_config: RelevanceConfig) -> RelevanceScorer:
    """RelevanceScorer with default configuration."""
    return RelevanceScorer(config=default_relevance_config)


class TestRelevanceConfig:
    """Tests for RelevanceConfig dataclass."""

    def test_default_primary_keywords(self):
        """Config should include all DAWO mushroom product keywords."""
        config = RelevanceConfig()

        # Should have the 6 mushroom types
        assert "lion's mane" in config.primary_keywords
        assert "chaga" in config.primary_keywords
        assert "reishi" in config.primary_keywords
        assert "cordyceps" in config.primary_keywords
        assert "shiitake" in config.primary_keywords
        assert "maitake" in config.primary_keywords

        # Should include Latin names
        assert "hericium erinaceus" in config.primary_keywords
        assert "ganoderma lucidum" in config.primary_keywords

    def test_default_secondary_keywords(self):
        """Config should include wellness theme keywords."""
        config = RelevanceConfig()

        assert "cognition" in config.secondary_keywords
        assert "immunity" in config.secondary_keywords
        assert "energy" in config.secondary_keywords
        assert "stress" in config.secondary_keywords
        assert "sleep" in config.secondary_keywords
        assert "adaptogen" in config.secondary_keywords

    def test_custom_keywords(self):
        """Config should accept custom keyword lists."""
        config = RelevanceConfig(
            primary_keywords=["custom1", "custom2"],
            secondary_keywords=["theme1", "theme2"],
        )

        assert config.primary_keywords == ["custom1", "custom2"]
        assert config.secondary_keywords == ["theme1", "theme2"]


class TestRelevanceScorer:
    """Tests for RelevanceScorer class."""

    def test_create_with_config(self, default_relevance_config: RelevanceConfig):
        """RelevanceScorer should accept config via constructor injection."""
        scorer = RelevanceScorer(config=default_relevance_config)

        assert scorer._config is not None

    def test_score_with_no_keywords(self, relevance_scorer: RelevanceScorer):
        """Item with no relevant keywords should score 0."""
        item = _create_test_item(
            title="Unrelated article about finance",
            content="Stock market news and cryptocurrency updates.",
        )

        result = relevance_scorer.score(item)

        assert result.raw_score == 0.0

    def test_score_with_single_primary_keyword(self, relevance_scorer: RelevanceScorer):
        """Single primary keyword match should add +2."""
        item = _create_test_item(
            title="Lion's mane research update",
            content="General research findings.",
        )

        result = relevance_scorer.score(item)

        assert result.raw_score == PRIMARY_KEYWORD_BONUS  # 2.0

    def test_score_with_multiple_primary_keywords(self, relevance_scorer: RelevanceScorer):
        """Multiple primary keywords should add +2 each (max +6)."""
        item = _create_test_item(
            title="Lion's mane and chaga comparison",
            content="Comparing lion's mane with reishi and cordyceps extracts.",
        )

        result = relevance_scorer.score(item)

        # 4 unique primary keywords: lion's mane, chaga, reishi, cordyceps
        # Max bonus is 6 (3 keywords worth)
        assert result.raw_score == MAX_PRIMARY_BONUS  # 6.0

    def test_score_with_single_secondary_keyword(self, relevance_scorer: RelevanceScorer):
        """Single secondary keyword match should add +1."""
        item = _create_test_item(
            title="Mushroom supplements for cognition",
            content="General supplement information.",
        )

        result = relevance_scorer.score(item)

        # "cognition" is secondary
        assert result.raw_score == SECONDARY_KEYWORD_BONUS  # 1.0

    def test_score_with_multiple_secondary_keywords(self, relevance_scorer: RelevanceScorer):
        """Multiple secondary keywords should add +1 each (max +4)."""
        item = _create_test_item(
            title="Mushrooms for energy and cognition",
            content="Supplements for immunity, stress relief, and better sleep.",
        )

        result = relevance_scorer.score(item)

        # 5 secondary keywords: energy, cognition, immunity, stress, sleep
        # Max bonus is 4
        assert result.raw_score == MAX_SECONDARY_BONUS  # 4.0

    def test_score_with_primary_and_secondary_keywords(self, relevance_scorer: RelevanceScorer):
        """Combined primary and secondary keywords should stack."""
        item = _create_test_item(
            title="Lion's mane for cognitive enhancement",
            content="Research on lion's mane mushroom benefits for brain health.",
        )

        result = relevance_scorer.score(item)

        # Primary: lion's mane (+2)
        # Secondary: cognitive, brain (+2 for 2 matches, but cognition/cognitive is 1 keyword group)
        # Expecting at least 3.0
        assert result.raw_score >= 3.0

    def test_score_capped_at_max(self, relevance_scorer: RelevanceScorer):
        """Score should not exceed MAX_SCORE (10)."""
        item = _create_test_item(
            title="Lion's mane chaga reishi cordyceps shiitake maitake",
            content="cognition immunity energy stress sleep focus brain memory",
        )

        result = relevance_scorer.score(item)

        assert result.raw_score <= MAX_SCORE

    def test_case_insensitive_matching(self, relevance_scorer: RelevanceScorer):
        """Keyword matching should be case-insensitive."""
        item = _create_test_item(
            title="LION'S MANE Research",
            content="CHAGA and REISHI supplements.",
        )

        result = relevance_scorer.score(item)

        assert result.raw_score >= 6.0  # 3 primary keywords

    def test_score_includes_component_name(self, relevance_scorer: RelevanceScorer):
        """Result should include component name."""
        item = _create_test_item(
            title="Test article",
            content="Test content.",
        )

        result = relevance_scorer.score(item)

        assert result.component_name == "relevance"

    def test_score_includes_notes(self, relevance_scorer: RelevanceScorer):
        """Result should include reasoning notes."""
        item = _create_test_item(
            title="Lion's mane research",
            content="Content about cognition.",
        )

        result = relevance_scorer.score(item)

        assert "lion's mane" in result.notes.lower()

    def test_latin_name_matching(self, relevance_scorer: RelevanceScorer):
        """Latin names should match as primary keywords."""
        item = _create_test_item(
            title="Hericium erinaceus study",
            content="Effects of Ganoderma lucidum on health.",
        )

        result = relevance_scorer.score(item)

        # 2 primary keywords via Latin names
        assert result.raw_score >= 4.0


class TestRelevanceConstants:
    """Tests for relevance scoring constants."""

    def test_primary_keyword_bonus(self):
        """Primary keyword bonus should be +2."""
        assert PRIMARY_KEYWORD_BONUS == 2.0

    def test_secondary_keyword_bonus(self):
        """Secondary keyword bonus should be +1."""
        assert SECONDARY_KEYWORD_BONUS == 1.0

    def test_max_primary_bonus(self):
        """Max primary bonus should be +6 (3 keywords)."""
        assert MAX_PRIMARY_BONUS == 6.0

    def test_max_secondary_bonus(self):
        """Max secondary bonus should be +4 (4 keywords)."""
        assert MAX_SECONDARY_BONUS == 4.0

    def test_max_score(self):
        """Max score should be 10."""
        assert MAX_SCORE == 10.0


def _create_test_item(
    title: str,
    content: str,
    source: str = ResearchSource.REDDIT.value,
) -> dict:
    """Create a test research item dictionary for scoring.

    Args:
        title: Item title.
        content: Item content.
        source: Research source.

    Returns:
        Dictionary with item data for scoring.
    """
    return {
        "id": uuid4(),
        "source": source,
        "title": title,
        "content": content,
        "url": "https://example.com/test",
        "tags": [],
        "source_metadata": {},
        "created_at": datetime.now(timezone.utc),
        "score": 0.0,
        "compliance_status": ComplianceStatus.COMPLIANT.value,
    }
