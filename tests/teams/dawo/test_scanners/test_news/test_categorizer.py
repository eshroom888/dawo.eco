"""Tests for news categorizer."""

from datetime import datetime, timezone

import pytest

from teams.dawo.scanners.news.schemas import (
    HarvestedArticle,
    NewsCategory,
    PriorityLevel,
)
from teams.dawo.scanners.news.categorizer import NewsCategorizer


class TestNewsCategorizer:
    """Tests for NewsCategorizer."""

    @pytest.fixture
    def categorizer(self) -> NewsCategorizer:
        """Create categorizer instance."""
        return NewsCategorizer(competitor_brands=["CompetitorBrand", "RivalCo"])

    @pytest.fixture
    def categorizer_no_competitors(self) -> NewsCategorizer:
        """Create categorizer without competitor brands."""
        return NewsCategorizer()

    def _make_article(self, title: str, summary: str) -> HarvestedArticle:
        """Helper to create test article."""
        return HarvestedArticle(
            title=title,
            summary=summary,
            url="https://example.com/article",
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=False,
        )

    def test_categorize_regulatory_eu_health_claims(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test categorization of EU health claims regulatory news."""
        article = self._make_article(
            title="EU Health Claims Regulation Update for Supplements",
            summary="The European Commission announces new health claims compliance requirements.",
        )
        result = categorizer.categorize(article)

        assert result.category == NewsCategory.REGULATORY
        assert result.is_regulatory is True
        assert result.priority_level == PriorityLevel.HIGH
        assert result.requires_operator_attention is True
        assert result.confidence >= 0.7

    def test_categorize_regulatory_novel_food(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test categorization of novel food regulatory news."""
        article = self._make_article(
            title="Novel Food Application Approved for New Ingredient",
            summary="EFSA approves novel food status for mushroom extract.",
        )
        result = categorizer.categorize(article)

        assert result.category == NewsCategory.REGULATORY
        assert result.is_regulatory is True
        assert "novel food" in " ".join(result.matched_patterns).lower() or result.confidence > 0.5

    def test_categorize_regulatory_mattilsynet(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test categorization of Mattilsynet regulatory news."""
        article = self._make_article(
            title="Mattilsynet Issues Warning on Supplements",
            summary="Norwegian Food Safety Authority releases compliance guidance.",
        )
        result = categorizer.categorize(article)

        assert result.category == NewsCategory.REGULATORY
        assert result.is_regulatory is True

    def test_categorize_research_clinical_trial(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test categorization of clinical trial research news."""
        article = self._make_article(
            title="Clinical Trial Shows Positive Results for Mushroom Extract",
            summary="A new study finds significant cognitive benefits from lion's mane supplementation.",
        )
        result = categorizer.categorize(article)

        assert result.category == NewsCategory.RESEARCH
        assert result.is_regulatory is False
        assert result.priority_level == PriorityLevel.LOW

    def test_categorize_research_peer_reviewed(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test categorization of peer-reviewed research news."""
        article = self._make_article(
            title="Peer-Reviewed Study on Adaptogen Benefits",
            summary="Researchers found significant immune support effects in controlled study.",
        )
        result = categorizer.categorize(article)

        assert result.category == NewsCategory.RESEARCH

    def test_categorize_product_news_launch(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test categorization of product launch news."""
        article = self._make_article(
            title="Wellness Brand Launches New Supplement Line",
            summary="Company announces expansion into functional mushroom market.",
        )
        result = categorizer.categorize(article)

        assert result.category == NewsCategory.PRODUCT_NEWS
        assert result.is_regulatory is False

    def test_categorize_competitor_mention(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test categorization of competitor brand mention."""
        article = self._make_article(
            title="CompetitorBrand Expands to European Markets",
            summary="The supplement company targets health-conscious consumers.",
        )
        result = categorizer.categorize(article)

        assert result.category == NewsCategory.COMPETITOR
        assert result.confidence >= 0.9

    def test_categorize_general_news(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test categorization of general industry news."""
        article = self._make_article(
            title="Global Supplement Market Trends",
            summary="Industry analysts report continued growth in wellness sector.",
        )
        result = categorizer.categorize(article)

        assert result.category == NewsCategory.GENERAL
        assert result.is_regulatory is False
        assert result.priority_level == PriorityLevel.LOW
        assert result.requires_operator_attention is False

    def test_regulatory_takes_precedence(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test that regulatory classification takes precedence."""
        article = self._make_article(
            title="Clinical Study Prompts EU Regulation Review",
            summary="Research findings lead to new EU health claims compliance requirements.",
        )
        result = categorizer.categorize(article)

        # Regulatory should take precedence over research
        assert result.category == NewsCategory.REGULATORY
        assert result.is_regulatory is True

    def test_high_priority_keywords_trigger_attention(
        self, categorizer: NewsCategorizer
    ) -> None:
        """Test that high priority keywords require operator attention."""
        article = self._make_article(
            title="FDA Issues Compliance Violation Warning",
            summary="Regulatory enforcement action targets health claims violations.",
        )
        result = categorizer.categorize(article)

        assert result.is_regulatory is True
        assert result.priority_level == PriorityLevel.HIGH
        assert result.requires_operator_attention is True

    def test_no_competitor_brands_skips_competitor_check(
        self, categorizer_no_competitors: NewsCategorizer
    ) -> None:
        """Test that without competitor brands, competitor check is skipped."""
        article = self._make_article(
            title="CompetitorBrand Announces New Product",
            summary="Company expands product line.",
        )
        result = categorizer_no_competitors.categorize(article)

        # Without competitor brands configured, should not match COMPETITOR
        assert result.category != NewsCategory.COMPETITOR
