"""Tests for news scanner schemas."""

from datetime import datetime, timezone

import pytest

from teams.dawo.scanners.news.schemas import (
    RawNewsArticle,
    HarvestedArticle,
    NewsCategory,
    PriorityLevel,
    CategoryResult,
    PriorityScore,
    ValidatedResearch,
    ScanStatistics,
    ScanResult,
    PipelineStatistics,
    PipelineResult,
    PipelineStatus,
)


class TestNewsCategory:
    """Tests for NewsCategory enum."""

    def test_category_values(self) -> None:
        """Test category enum values."""
        assert NewsCategory.REGULATORY.value == "regulatory"
        assert NewsCategory.PRODUCT_NEWS.value == "product_news"
        assert NewsCategory.RESEARCH.value == "research"
        assert NewsCategory.COMPETITOR.value == "competitor"
        assert NewsCategory.GENERAL.value == "general"


class TestPriorityLevel:
    """Tests for PriorityLevel enum."""

    def test_priority_values(self) -> None:
        """Test priority enum values."""
        assert PriorityLevel.HIGH.value == "high"
        assert PriorityLevel.MEDIUM.value == "medium"
        assert PriorityLevel.LOW.value == "low"


class TestRawNewsArticle:
    """Tests for RawNewsArticle schema."""

    def test_create_raw_article(self) -> None:
        """Test creating a raw article."""
        now = datetime.now(timezone.utc)
        article = RawNewsArticle(
            title="Test Article",
            summary="Test summary",
            url="https://example.com/article",
            published=now,
            source_name="TestSource",
            is_tier_1=True,
        )
        assert article.title == "Test Article"
        assert article.summary == "Test summary"
        assert article.url == "https://example.com/article"
        assert article.published == now
        assert article.source_name == "TestSource"
        assert article.is_tier_1 is True

    def test_raw_article_defaults(self) -> None:
        """Test raw article default values."""
        article = RawNewsArticle(
            title="Test",
            url="https://example.com",
            source_name="Source",
        )
        assert article.summary == ""
        assert article.published is None
        assert article.is_tier_1 is False


class TestHarvestedArticle:
    """Tests for HarvestedArticle schema."""

    def test_create_harvested_article(self) -> None:
        """Test creating a harvested article."""
        now = datetime.now(timezone.utc)
        article = HarvestedArticle(
            title="Test Article",
            summary="Cleaned summary",
            url="https://example.com/article",
            published=now,
            source_name="TestSource",
            is_tier_1=False,
        )
        assert article.title == "Test Article"
        assert article.summary == "Cleaned summary"


class TestCategoryResult:
    """Tests for CategoryResult dataclass."""

    def test_create_category_result(self) -> None:
        """Test creating a category result."""
        result = CategoryResult(
            category=NewsCategory.REGULATORY,
            confidence=0.9,
            is_regulatory=True,
            priority_level=PriorityLevel.HIGH,
            matched_patterns=["pattern1"],
            requires_operator_attention=True,
        )
        assert result.category == NewsCategory.REGULATORY
        assert result.confidence == 0.9
        assert result.is_regulatory is True
        assert result.priority_level == PriorityLevel.HIGH
        assert result.requires_operator_attention is True

    def test_category_result_defaults(self) -> None:
        """Test category result default values."""
        result = CategoryResult(category=NewsCategory.GENERAL)
        assert result.confidence == 0.5
        assert result.is_regulatory is False
        assert result.priority_level == PriorityLevel.LOW
        assert result.matched_patterns == []
        assert result.requires_operator_attention is False

    def test_category_result_invalid_confidence(self) -> None:
        """Test validation of confidence score."""
        with pytest.raises(ValueError, match="confidence must be 0-1"):
            CategoryResult(category=NewsCategory.GENERAL, confidence=1.5)


class TestPriorityScore:
    """Tests for PriorityScore dataclass."""

    def test_create_priority_score(self) -> None:
        """Test creating a priority score."""
        score = PriorityScore(
            base_score=6.0,
            final_score=8.5,
            boosters_applied=["tier_1_source", "regulatory_high_priority"],
            requires_attention=True,
        )
        assert score.base_score == 6.0
        assert score.final_score == 8.5
        assert len(score.boosters_applied) == 2
        assert score.requires_attention is True

    def test_priority_score_invalid(self) -> None:
        """Test validation of final score."""
        with pytest.raises(ValueError, match="final_score must be 0-10"):
            PriorityScore(base_score=5.0, final_score=11.0)


class TestValidatedResearch:
    """Tests for ValidatedResearch schema."""

    def test_create_validated_research(self) -> None:
        """Test creating validated research."""
        now = datetime.now(timezone.utc)
        research = ValidatedResearch(
            source="news",
            title="Test Article",
            content="Article content",
            url="https://example.com/article",
            tags=["news", "regulatory"],
            source_metadata={"category": "regulatory"},
            created_at=now,
            compliance_status="COMPLIANT",
            score=7.5,
        )
        assert research.source == "news"
        assert research.title == "Test Article"
        assert research.compliance_status == "COMPLIANT"
        assert research.score == 7.5


class TestPipelineStatus:
    """Tests for PipelineStatus enum."""

    def test_status_values(self) -> None:
        """Test pipeline status values."""
        assert PipelineStatus.COMPLETE.value == "COMPLETE"
        assert PipelineStatus.INCOMPLETE.value == "INCOMPLETE"
        assert PipelineStatus.PARTIAL.value == "PARTIAL"
        assert PipelineStatus.FAILED.value == "FAILED"


class TestPipelineStatistics:
    """Tests for PipelineStatistics dataclass."""

    def test_statistics_defaults(self) -> None:
        """Test statistics default values."""
        stats = PipelineStatistics()
        assert stats.total_found == 0
        assert stats.harvested == 0
        assert stats.categorized == 0
        assert stats.regulatory_flagged == 0
        assert stats.transformed == 0
        assert stats.validated == 0
        assert stats.scored == 0
        assert stats.published == 0
        assert stats.failed == 0
        assert stats.feeds_processed == 0
        assert stats.feeds_failed == 0


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_create_pipeline_result(self) -> None:
        """Test creating a pipeline result."""
        result = PipelineResult(
            status=PipelineStatus.COMPLETE,
            statistics=PipelineStatistics(total_found=10, published=8),
        )
        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.total_found == 10
        assert result.statistics.published == 8
        assert result.error is None
        assert result.retry_scheduled is False
