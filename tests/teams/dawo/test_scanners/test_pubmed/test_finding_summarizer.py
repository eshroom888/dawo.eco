"""Tests for Finding Summarizer LLM stage.

Tests for the LLM summarization stage:
    Scanner -> Harvester -> [FindingSummarizer] -> ClaimValidator -> Transformer -> Validator -> Publisher

Test categories:
    - Initialization
    - Successful summarization
    - Response parsing
    - Error handling
    - Default summaries
    - Batch processing
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.pubmed.schemas import (
    HarvestedArticle,
    FindingSummary,
    StudyType,
)
from teams.dawo.scanners.pubmed.finding_summarizer import (
    FindingSummarizer,
    SummarizationError,
)


class TestFindingSummarizerInit:
    """Tests for FindingSummarizer initialization."""

    def test_summarizer_creates_with_llm_client(self):
        """Should create summarizer with LLM client."""
        mock_llm = MagicMock()
        summarizer = FindingSummarizer(mock_llm)

        assert summarizer is not None
        assert summarizer._llm == mock_llm


class TestSummarization:
    """Tests for successful summarization."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client with valid JSON response."""
        client = AsyncMock()
        client.generate = AsyncMock(return_value=json.dumps({
            "compound_studied": "Hericium erinaceus (Lion's mane)",
            "effect_measured": "Cognitive function improvement",
            "key_findings": "Treatment group showed significant improvement in cognitive scores.",
            "statistical_significance": "p<0.05, n=77",
            "study_strength": "strong",
            "content_potential": ["educational", "citation_worthy"],
            "caveat": "Research finding - not an approved health claim."
        }))
        return client

    @pytest.fixture
    def sample_article(self) -> HarvestedArticle:
        """Create sample harvested article."""
        return HarvestedArticle(
            pmid="12345678",
            title="Effects of Lion's Mane on Cognitive Function",
            abstract="This RCT examined the effects of Hericium erinaceus on cognition. "
                     "77 participants were randomized. Results showed significant improvement.",
            authors=["Mori K", "Inatomi S"],
            journal="Phytotherapy Research",
            pub_date=datetime.now(timezone.utc),
            doi="10.1002/ptr.12345",
            study_type=StudyType.RCT,
            sample_size=77,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        )

    @pytest.mark.asyncio
    async def test_summarize_returns_finding_summary(
        self, mock_llm_client, sample_article
    ):
        """Should return FindingSummary with extracted information."""
        summarizer = FindingSummarizer(mock_llm_client)

        result = await summarizer.summarize(sample_article)

        assert isinstance(result, FindingSummary)
        assert result.compound_studied == "Hericium erinaceus (Lion's mane)"
        assert result.effect_measured == "Cognitive function improvement"
        assert "significant improvement" in result.key_findings
        assert result.study_strength == "strong"
        assert "educational" in result.content_potential

    @pytest.mark.asyncio
    async def test_summarize_calls_llm_with_prompt(
        self, mock_llm_client, sample_article
    ):
        """Should call LLM with formatted prompt."""
        summarizer = FindingSummarizer(mock_llm_client)

        await summarizer.summarize(sample_article)

        mock_llm_client.generate.assert_called_once()
        call_kwargs = mock_llm_client.generate.call_args.kwargs
        assert "prompt" in call_kwargs
        assert sample_article.title in call_kwargs["prompt"]
        assert "rct" in call_kwargs["prompt"]  # study_type.value

    @pytest.mark.asyncio
    async def test_summarize_truncates_long_abstract(self, mock_llm_client):
        """Should truncate very long abstracts."""
        long_abstract = "A" * 5000
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract=long_abstract,
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )
        summarizer = FindingSummarizer(mock_llm_client)

        await summarizer.summarize(article)

        call_kwargs = mock_llm_client.generate.call_args.kwargs
        # Abstract should be truncated to 4000 chars
        assert len(call_kwargs["prompt"]) < len(long_abstract) + 1000


class TestResponseParsing:
    """Tests for LLM response parsing."""

    @pytest.fixture
    def summarizer(self):
        """Create summarizer with mock LLM."""
        return FindingSummarizer(AsyncMock())

    @pytest.fixture
    def sample_article(self) -> HarvestedArticle:
        """Create minimal article for testing."""
        return HarvestedArticle(
            pmid="1",
            title="Test Article",
            abstract="Test abstract content",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

    @pytest.mark.asyncio
    async def test_parses_clean_json(self, sample_article):
        """Should parse clean JSON response."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=json.dumps({
            "compound_studied": "Test compound",
            "effect_measured": "Test effect",
            "key_findings": "Test findings",
            "statistical_significance": None,
            "study_strength": "moderate",
            "content_potential": ["educational"],
            "caveat": "Standard caveat"
        }))
        summarizer = FindingSummarizer(mock_llm)

        result = await summarizer.summarize(sample_article)

        assert result.compound_studied == "Test compound"
        assert result.study_strength == "moderate"

    @pytest.mark.asyncio
    async def test_parses_markdown_wrapped_json(self, sample_article):
        """Should parse JSON wrapped in markdown code blocks."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value='''```json
{
    "compound_studied": "Markdown test",
    "effect_measured": "Test effect",
    "key_findings": "Test findings",
    "statistical_significance": null,
    "study_strength": "weak",
    "content_potential": ["educational"],
    "caveat": "Standard caveat"
}
```''')
        summarizer = FindingSummarizer(mock_llm)

        result = await summarizer.summarize(sample_article)

        assert result.compound_studied == "Markdown test"

    @pytest.mark.asyncio
    async def test_uses_defaults_for_missing_fields(self, sample_article):
        """Should use default values for missing fields."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=json.dumps({
            # Minimal response
        }))
        summarizer = FindingSummarizer(mock_llm)

        result = await summarizer.summarize(sample_article)

        # Should use default values
        assert result.compound_studied == "Unknown compound"
        assert result.effect_measured == "Unknown effect"
        assert result.study_strength == "weak"


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def sample_article(self) -> HarvestedArticle:
        """Create minimal article for testing."""
        return HarvestedArticle(
            pmid="12345678",
            title="Test Article",
            abstract="Test abstract content",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        )

    @pytest.mark.asyncio
    async def test_returns_default_on_json_error(self, sample_article):
        """Should return default summary when JSON parsing fails."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Not valid JSON")
        summarizer = FindingSummarizer(mock_llm)

        result = await summarizer.summarize(sample_article)

        # Should return default summary instead of raising
        assert isinstance(result, FindingSummary)
        assert "Functional mushroom compound" in result.compound_studied

    @pytest.mark.asyncio
    async def test_raises_summarization_error_on_llm_failure(self, sample_article):
        """Should raise SummarizationError when LLM fails."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("API error"))
        summarizer = FindingSummarizer(mock_llm)

        with pytest.raises(SummarizationError) as exc_info:
            await summarizer.summarize(sample_article)

        assert "API error" in str(exc_info.value)
        assert exc_info.value.pmid == "12345678"


class TestDefaultSummary:
    """Tests for default summary generation."""

    @pytest.fixture
    def summarizer(self):
        """Create summarizer with mock LLM."""
        return FindingSummarizer(AsyncMock())

    @pytest.mark.asyncio
    async def test_default_summary_for_empty_abstract(self, summarizer):
        """Should return default summary for articles without abstract."""
        article = HarvestedArticle(
            pmid="1",
            title="Lion's Mane Study",
            abstract="",  # Empty abstract
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await summarizer.summarize(article)

        assert isinstance(result, FindingSummary)
        # Should not have called LLM
        summarizer._llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_default_summary_extracts_mushroom_from_title(self, summarizer):
        """Should extract mushroom name from title if possible."""
        article = HarvestedArticle(
            pmid="1",
            title="Effects of Chaga on Immune Function",
            abstract="",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await summarizer.summarize(article)

        assert "Chaga" in result.compound_studied

    @pytest.mark.asyncio
    async def test_default_summary_includes_caveat(self, summarizer):
        """Should include standard caveat in default summary."""
        article = HarvestedArticle(
            pmid="1",
            title="Test Article",
            abstract="",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await summarizer.summarize(article)

        assert "not an approved health claim" in result.caveat


class TestBatchSummarization:
    """Tests for batch summarization."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock()
        client.generate = AsyncMock(return_value=json.dumps({
            "compound_studied": "Test",
            "effect_measured": "Test",
            "key_findings": "Test findings",
            "statistical_significance": None,
            "study_strength": "moderate",
            "content_potential": ["educational"],
            "caveat": "Standard caveat"
        }))
        return client

    @pytest.fixture
    def sample_articles(self) -> list[HarvestedArticle]:
        """Create multiple articles for batch testing."""
        return [
            HarvestedArticle(
                pmid=str(i),
                title=f"Article {i}",
                abstract=f"Abstract {i}",
                authors=[],
                journal="Test",
                pub_date=datetime.now(timezone.utc),
                doi=None,
                study_type=StudyType.OTHER,
                sample_size=None,
                pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{i}/",
            )
            for i in range(3)
        ]

    @pytest.mark.asyncio
    async def test_summarize_batch_returns_dict(
        self, mock_llm_client, sample_articles
    ):
        """Should return dict mapping PMID to FindingSummary."""
        summarizer = FindingSummarizer(mock_llm_client)

        result = await summarizer.summarize_batch(sample_articles)

        assert isinstance(result, dict)
        assert len(result) == 3
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert all(isinstance(v, FindingSummary) for v in result.values())

    @pytest.mark.asyncio
    async def test_batch_handles_individual_failures(self, sample_articles):
        """Should continue processing when individual articles fail."""
        mock_llm = AsyncMock()
        # First call fails, rest succeed
        mock_llm.generate = AsyncMock(side_effect=[
            Exception("First fails"),
            json.dumps({"compound_studied": "Test", "effect_measured": "Test",
                       "key_findings": "Test", "study_strength": "weak",
                       "content_potential": [], "caveat": "Test"}),
            json.dumps({"compound_studied": "Test", "effect_measured": "Test",
                       "key_findings": "Test", "study_strength": "weak",
                       "content_potential": [], "caveat": "Test"}),
        ])
        summarizer = FindingSummarizer(mock_llm)

        result = await summarizer.summarize_batch(sample_articles)

        # Should still return all 3
        assert len(result) == 3
        # First one should be default summary
        assert result["0"].compound_studied == "Functional mushroom compound"


class TestSummarizationError:
    """Tests for SummarizationError exception."""

    def test_error_with_message_only(self):
        """Should create error with message only."""
        error = SummarizationError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.pmid is None

    def test_error_with_pmid(self):
        """Should create error with PMID."""
        error = SummarizationError("Failed to summarize", pmid="12345678")

        assert error.message == "Failed to summarize"
        assert error.pmid == "12345678"
