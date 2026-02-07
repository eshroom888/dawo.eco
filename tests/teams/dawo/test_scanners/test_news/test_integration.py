"""Integration tests for news scanner module.

These tests verify the integration between pipeline components
without mocking internal stages.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from teams.dawo.scanners.news import (
    NewsScanner,
    NewsFeedClient,
    NewsHarvester,
    NewsCategorizer,
    NewsPriorityScorer,
    NewsTransformer,
    NewsValidator,
    NewsResearchPipeline,
    NewsScannerConfig,
    NewsFeedClientConfig,
    FeedSource,
    PipelineStatus,
    NewsCategory,
)


class TestNewsModuleIntegration:
    """Integration tests for news scanner module."""

    @pytest.fixture
    def scanner_config(self) -> NewsScannerConfig:
        """Create scanner configuration."""
        return NewsScannerConfig(
            feeds=[
                FeedSource("TestFeed", "https://test.com/rss", is_tier_1=True),
            ],
            keywords=["mushrooms", "supplements"],
            competitor_brands=["CompetitorBrand"],
            hours_back=24,
        )

    @pytest.fixture
    def mock_feed_client(self) -> AsyncMock:
        """Create mock feed client."""
        now = datetime.now(timezone.utc)
        client = AsyncMock(spec=NewsFeedClient)
        client.fetch_feed.return_value = [
            {
                "title": "EU Health Claims Update for Supplements",
                "summary": "The European Commission announces new health claims compliance requirements.",
                "url": "https://test.com/eu-update",
                "published": now - timedelta(hours=2),
                "source_name": "TestFeed",
                "is_tier_1": True,
            },
            {
                "title": "Clinical Study on Lion's Mane Cognitive Benefits",
                "summary": "Peer-reviewed research demonstrates significant cognitive improvements.",
                "url": "https://test.com/study",
                "published": now - timedelta(hours=6),
                "source_name": "TestFeed",
                "is_tier_1": True,
            },
            {
                "title": "New Mushroom Supplement Brand Launches",
                "summary": "Wellness startup announces launch of functional mushroom products.",
                "url": "https://test.com/launch",
                "published": now - timedelta(hours=12),
                "source_name": "TestFeed",
                "is_tier_1": True,
            },
        ]
        return client

    @pytest.fixture
    def mock_compliance_checker(self) -> MagicMock:
        """Create mock compliance checker."""
        checker = MagicMock()
        checker.check_compliance.return_value = MagicMock(
            is_compliant=True,
            compliance_status="COMPLIANT",
        )
        return checker

    @pytest.fixture
    def mock_publisher(self) -> AsyncMock:
        """Create mock publisher."""
        publisher = AsyncMock()
        publisher.publish_batch.return_value = [
            MagicMock(id=uuid4()) for _ in range(3)
        ]
        return publisher

    @pytest.fixture
    def mock_scorer(self) -> MagicMock:
        """Create mock scorer."""
        scorer = MagicMock()
        scorer.calculate_score.return_value = MagicMock(final_score=5.0)
        return scorer

    def test_categorizer_classifies_regulatory(self) -> None:
        """Test that categorizer correctly classifies regulatory news."""
        from teams.dawo.scanners.news.schemas import HarvestedArticle

        categorizer = NewsCategorizer()

        article = HarvestedArticle(
            title="EU Health Claims Regulation Update",
            summary="New compliance requirements for health claims under EC 1924/2006.",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=True,
        )

        result = categorizer.categorize(article)

        assert result.category == NewsCategory.REGULATORY
        assert result.is_regulatory is True

    def test_categorizer_classifies_research(self) -> None:
        """Test that categorizer correctly classifies research news."""
        from teams.dawo.scanners.news.schemas import HarvestedArticle

        categorizer = NewsCategorizer()

        article = HarvestedArticle(
            title="Clinical Study Shows Benefits",
            summary="A new peer-reviewed study demonstrates significant health benefits.",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=False,
        )

        result = categorizer.categorize(article)

        assert result.category == NewsCategory.RESEARCH

    def test_priority_scorer_boosts_regulatory_high(self) -> None:
        """Test that priority scorer boosts regulatory high priority."""
        from teams.dawo.scanners.news.schemas import (
            HarvestedArticle,
            CategoryResult,
            PriorityLevel,
        )

        scorer = NewsPriorityScorer()

        article = HarvestedArticle(
            title="Novel Food Health Claims Update",
            summary="EFSA approves new health claim for mushroom extract.",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=True,
        )

        category = CategoryResult(
            category=NewsCategory.REGULATORY,
            confidence=0.9,
            is_regulatory=True,
            priority_level=PriorityLevel.HIGH,
            requires_operator_attention=True,
        )

        result = scorer.calculate_priority(article, category)

        assert result.final_score >= 8.0
        assert "regulatory_high_priority" in result.boosters_applied

    def test_harvester_cleans_content(self) -> None:
        """Test that harvester cleans HTML from content."""
        from teams.dawo.scanners.news.schemas import RawNewsArticle

        harvester = NewsHarvester()

        raw = RawNewsArticle(
            title="Test Article",
            summary="<p><strong>Bold</strong> text with <a href='#'>link</a></p>",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=False,
        )

        result = harvester.harvest([raw])

        assert len(result) == 1
        assert "<p>" not in result[0].summary
        assert "<strong>" not in result[0].summary
        assert "Bold" in result[0].summary

    def test_transformer_produces_valid_research(self) -> None:
        """Test that transformer produces valid research items."""
        from teams.dawo.scanners.news.schemas import HarvestedArticle

        categorizer = NewsCategorizer()
        scorer = NewsPriorityScorer()
        transformer = NewsTransformer(categorizer, scorer)

        article = HarvestedArticle(
            title="Test Article",
            summary="Test summary content",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=True,
        )

        result = transformer.transform([article])

        assert len(result) == 1
        research, category, priority = result[0]
        assert research.source == "news"
        assert research.title == "Test Article"
        assert "news" in research.tags

    def test_full_harvester_to_transformer_flow(self) -> None:
        """Test flow from harvester through transformer."""
        from teams.dawo.scanners.news.schemas import RawNewsArticle

        # Create components
        harvester = NewsHarvester()
        categorizer = NewsCategorizer(competitor_brands=["CompetitorBrand"])
        scorer = NewsPriorityScorer()
        transformer = NewsTransformer(categorizer, scorer)

        # Create raw articles
        raw_articles = [
            RawNewsArticle(
                title="EU Regulation Update",
                summary="New health claims compliance requirements.",
                url="https://example.com/eu",
                published=datetime.now(timezone.utc),
                source_name="Source",
                is_tier_1=True,
            ),
            RawNewsArticle(
                title="Clinical Trial Results",
                summary="A new study finds benefits from lion's mane mushroom.",
                url="https://example.com/study",
                published=datetime.now(timezone.utc),
                source_name="Source",
                is_tier_1=False,
            ),
        ]

        # Execute flow
        harvested = harvester.harvest(raw_articles)
        transformed = transformer.transform(harvested)

        assert len(transformed) == 2

        # Verify first article is regulatory
        research1, category1, priority1 = transformed[0]
        assert category1.category == NewsCategory.REGULATORY
        assert priority1.final_score >= 6.0

        # Verify second article is research
        research2, category2, priority2 = transformed[1]
        assert category2.category == NewsCategory.RESEARCH
