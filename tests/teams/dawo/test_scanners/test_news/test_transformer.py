"""Tests for news transformer."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from teams.dawo.scanners.news.schemas import (
    HarvestedArticle,
    NewsCategory,
    PriorityLevel,
    CategoryResult,
    PriorityScore,
)
from teams.dawo.scanners.news.transformer import NewsTransformer


class TestNewsTransformer:
    """Tests for NewsTransformer."""

    @pytest.fixture
    def mock_categorizer(self) -> MagicMock:
        """Create mock categorizer."""
        categorizer = MagicMock()
        categorizer.categorize.return_value = CategoryResult(
            category=NewsCategory.GENERAL,
            confidence=0.7,
            is_regulatory=False,
            priority_level=PriorityLevel.LOW,
            matched_patterns=[],
            requires_operator_attention=False,
        )
        return categorizer

    @pytest.fixture
    def mock_priority_scorer(self) -> MagicMock:
        """Create mock priority scorer."""
        scorer = MagicMock()
        scorer.calculate_priority.return_value = PriorityScore(
            base_score=2.0,
            final_score=3.0,
            boosters_applied=["tier_1_source"],
            requires_attention=False,
        )
        return scorer

    @pytest.fixture
    def transformer(
        self,
        mock_categorizer: MagicMock,
        mock_priority_scorer: MagicMock,
    ) -> NewsTransformer:
        """Create transformer instance."""
        return NewsTransformer(mock_categorizer, mock_priority_scorer)

    def _make_article(
        self,
        title: str = "Test Article",
        summary: str = "Test summary",
        is_tier_1: bool = False,
        is_regulatory: bool = False,
    ) -> HarvestedArticle:
        """Helper to create harvested article."""
        return HarvestedArticle(
            title=title,
            summary=summary,
            url="https://example.com/article",
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=is_tier_1,
        )

    def test_transform_single_article(
        self,
        transformer: NewsTransformer,
    ) -> None:
        """Test transforming a single article."""
        article = self._make_article()

        result = transformer.transform([article])

        assert len(result) == 1
        research, category, priority = result[0]
        assert research.source == "news"
        assert research.title == "Test Article"
        assert research.url == "https://example.com/article"

    def test_transform_multiple_articles(
        self,
        transformer: NewsTransformer,
    ) -> None:
        """Test transforming multiple articles."""
        articles = [
            self._make_article(title=f"Article {i}")
            for i in range(3)
        ]

        result = transformer.transform(articles)

        assert len(result) == 3

    def test_transform_includes_category_result(
        self,
        transformer: NewsTransformer,
        mock_categorizer: MagicMock,
    ) -> None:
        """Test that category result is returned."""
        article = self._make_article()

        result = transformer.transform([article])

        assert len(result) == 1
        _, category, _ = result[0]
        assert isinstance(category, CategoryResult)
        mock_categorizer.categorize.assert_called_once()

    def test_transform_includes_priority_score(
        self,
        transformer: NewsTransformer,
        mock_priority_scorer: MagicMock,
    ) -> None:
        """Test that priority score is returned."""
        article = self._make_article()

        result = transformer.transform([article])

        assert len(result) == 1
        _, _, priority = result[0]
        assert isinstance(priority, PriorityScore)
        mock_priority_scorer.calculate_priority.assert_called_once()

    def test_transform_generates_tags(
        self,
        transformer: NewsTransformer,
    ) -> None:
        """Test that tags are generated."""
        article = self._make_article(is_tier_1=True)

        result = transformer.transform([article])

        research, _, _ = result[0]
        assert "news" in research.tags
        assert "general" in research.tags
        assert "tier_1_source" in research.tags

    def test_transform_builds_source_metadata(
        self,
        transformer: NewsTransformer,
    ) -> None:
        """Test that source metadata is built correctly."""
        article = self._make_article(is_tier_1=True)

        result = transformer.transform([article])

        research, _, _ = result[0]
        assert research.source_metadata["source_name"] == "TestSource"
        assert research.source_metadata["is_tier_1"] is True
        assert "category" in research.source_metadata

    def test_transform_regulatory_adds_context(
        self,
        transformer: NewsTransformer,
        mock_categorizer: MagicMock,
    ) -> None:
        """Test that regulatory articles get context added."""
        mock_categorizer.categorize.return_value = CategoryResult(
            category=NewsCategory.REGULATORY,
            confidence=0.9,
            is_regulatory=True,
            priority_level=PriorityLevel.HIGH,
            matched_patterns=["EU health claims"],
            requires_operator_attention=True,
        )

        article = self._make_article()
        result = transformer.transform([article])

        research, _, _ = result[0]
        assert "[REGULATORY]" in research.content
        assert "attention_required" in research.tags
        assert research.source_metadata["is_regulatory"] is True

    def test_transform_sets_score_from_priority(
        self,
        transformer: NewsTransformer,
        mock_priority_scorer: MagicMock,
    ) -> None:
        """Test that score is set from priority scorer."""
        mock_priority_scorer.calculate_priority.return_value = PriorityScore(
            base_score=6.0,
            final_score=8.5,
            boosters_applied=["regulatory_high_priority"],
            requires_attention=True,
        )

        article = self._make_article()
        result = transformer.transform([article])

        research, _, _ = result[0]
        assert research.score == 8.5

    def test_transform_truncates_long_content(
        self,
        transformer: NewsTransformer,
    ) -> None:
        """Test that long content is truncated."""
        long_summary = "A" * 15000
        article = self._make_article(summary=long_summary)

        result = transformer.transform([article])

        research, _, _ = result[0]
        assert len(research.content) <= 10003  # MAX_SUMMARY_LENGTH + "..."

    def test_transform_empty_list(
        self,
        transformer: NewsTransformer,
    ) -> None:
        """Test transforming empty list."""
        result = transformer.transform([])

        assert result == []
