"""Tests for news priority scorer."""

from datetime import datetime, timedelta, timezone

import pytest

from teams.dawo.scanners.news.schemas import (
    HarvestedArticle,
    NewsCategory,
    PriorityLevel,
    CategoryResult,
)
from teams.dawo.scanners.news.priority_scorer import NewsPriorityScorer


class TestNewsPriorityScorer:
    """Tests for NewsPriorityScorer."""

    @pytest.fixture
    def scorer(self) -> NewsPriorityScorer:
        """Create scorer instance."""
        return NewsPriorityScorer()

    def _make_article(
        self,
        hours_ago: float = 12,
        is_tier_1: bool = False,
        title: str = "Test Article",
        summary: str = "Test summary",
    ) -> HarvestedArticle:
        """Helper to create test article."""
        published = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        return HarvestedArticle(
            title=title,
            summary=summary,
            url="https://example.com/article",
            published=published,
            source_name="TestSource",
            is_tier_1=is_tier_1,
        )

    def _make_category_result(
        self,
        category: NewsCategory,
        is_regulatory: bool = False,
        priority_level: PriorityLevel = PriorityLevel.LOW,
        requires_operator_attention: bool = False,
    ) -> CategoryResult:
        """Helper to create category result."""
        return CategoryResult(
            category=category,
            confidence=0.8,
            is_regulatory=is_regulatory,
            priority_level=priority_level,
            matched_patterns=["test_pattern"],
            requires_operator_attention=requires_operator_attention,
        )

    def test_regulatory_high_priority_score(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that regulatory + high priority gets score 8+."""
        article = self._make_article(is_tier_1=True)
        category = self._make_category_result(
            category=NewsCategory.REGULATORY,
            is_regulatory=True,
            priority_level=PriorityLevel.HIGH,
            requires_operator_attention=True,
        )

        result = scorer.calculate_priority(article, category)

        assert result.final_score >= 8.0
        assert result.requires_attention is True
        assert "regulatory_high_priority" in result.boosters_applied
        assert "tier_1_source" in result.boosters_applied

    def test_regulatory_medium_priority_score(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that regulatory + medium priority gets score ~6."""
        article = self._make_article()
        category = self._make_category_result(
            category=NewsCategory.REGULATORY,
            is_regulatory=True,
            priority_level=PriorityLevel.MEDIUM,
        )

        result = scorer.calculate_priority(article, category)

        assert result.base_score == 6.0
        assert result.final_score >= 6.0
        assert result.final_score < 8.0  # No high priority boost

    def test_research_base_score(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that research gets base score ~5."""
        article = self._make_article()
        category = self._make_category_result(
            category=NewsCategory.RESEARCH,
        )

        result = scorer.calculate_priority(article, category)

        assert result.base_score == 5.0

    def test_mushroom_research_boost(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that mushroom research gets boosted."""
        article = self._make_article(
            title="Lion's Mane Study Shows Benefits",
            summary="Research on hericium erinaceus demonstrates cognitive effects.",
        )
        category = self._make_category_result(
            category=NewsCategory.RESEARCH,
        )

        result = scorer.calculate_priority(article, category)

        assert "mushroom_research" in result.boosters_applied
        assert result.final_score > result.base_score

    def test_product_news_base_score(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that product news gets base score ~4."""
        article = self._make_article()
        category = self._make_category_result(
            category=NewsCategory.PRODUCT_NEWS,
        )

        result = scorer.calculate_priority(article, category)

        assert result.base_score == 4.0

    def test_competitor_base_score(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that competitor news gets base score ~4."""
        article = self._make_article()
        category = self._make_category_result(
            category=NewsCategory.COMPETITOR,
        )

        result = scorer.calculate_priority(article, category)

        assert result.base_score == 4.0

    def test_general_base_score(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that general news gets base score ~2."""
        article = self._make_article()
        category = self._make_category_result(
            category=NewsCategory.GENERAL,
        )

        result = scorer.calculate_priority(article, category)

        assert result.base_score == 2.0

    def test_recency_boost_applied(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that recent articles get recency boost."""
        article = self._make_article(hours_ago=2)  # 2 hours ago
        category = self._make_category_result(
            category=NewsCategory.GENERAL,
        )

        result = scorer.calculate_priority(article, category)

        assert "recent_article" in result.boosters_applied
        assert result.final_score > result.base_score

    def test_recency_boost_not_applied_old_article(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that old articles don't get recency boost."""
        article = self._make_article(hours_ago=12)  # 12 hours ago
        category = self._make_category_result(
            category=NewsCategory.GENERAL,
        )

        result = scorer.calculate_priority(article, category)

        assert "recent_article" not in result.boosters_applied

    def test_tier_1_source_boost(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that tier-1 sources get boost."""
        article = self._make_article(is_tier_1=True)
        category = self._make_category_result(
            category=NewsCategory.GENERAL,
        )

        result = scorer.calculate_priority(article, category)

        assert "tier_1_source" in result.boosters_applied
        assert result.final_score > result.base_score

    def test_score_capped_at_10(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that score is capped at 10."""
        # Create conditions for maximum boosting
        article = self._make_article(
            hours_ago=1,  # Recent
            is_tier_1=True,  # Tier-1
            title="Novel Food Health Claims Update",  # Regulatory keywords
        )
        category = self._make_category_result(
            category=NewsCategory.REGULATORY,
            is_regulatory=True,
            priority_level=PriorityLevel.HIGH,
            requires_operator_attention=True,
        )

        result = scorer.calculate_priority(article, category)

        assert result.final_score <= 10.0

    def test_multiple_boosters_combine(
        self, scorer: NewsPriorityScorer
    ) -> None:
        """Test that multiple boosters combine correctly."""
        article = self._make_article(
            hours_ago=2,  # Recent = +0.5
            is_tier_1=True,  # Tier-1 = +0.5
        )
        category = self._make_category_result(
            category=NewsCategory.GENERAL,  # Base = 2.0
        )

        result = scorer.calculate_priority(article, category)

        # Base 2.0 + recency 0.5 + tier_1 0.5 = 3.0
        expected_score = 2.0 + 0.5 + 0.5
        assert result.final_score == pytest.approx(expected_score, rel=0.01)
        assert "recent_article" in result.boosters_applied
        assert "tier_1_source" in result.boosters_applied
