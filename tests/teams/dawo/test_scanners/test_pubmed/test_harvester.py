"""Tests for PubMed Harvester stage.

Tests for the harvester stage that enriches raw articles with metadata:
    Scanner -> [Harvester] -> FindingSummarizer -> ClaimValidator -> Transformer -> Validator -> Publisher

Test categories:
    - Single article harvesting
    - Batch harvesting
    - Study type classification
    - Sample size extraction
    - URL generation
    - Error handling
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from teams.dawo.scanners.pubmed.schemas import (
    RawPubMedArticle,
    HarvestedArticle,
    StudyType,
)
from teams.dawo.scanners.pubmed.harvester import (
    PubMedHarvester,
    HarvesterError,
    PUBMED_URL_TEMPLATE,
)


class TestHarvesterInit:
    """Tests for PubMedHarvester initialization."""

    def test_harvester_creates_without_dependencies(self):
        """Harvester should create without any dependencies."""
        harvester = PubMedHarvester()
        assert harvester is not None


class TestHarvestSingle:
    """Tests for single article harvesting."""

    @pytest.fixture
    def harvester(self):
        """Create harvester instance."""
        return PubMedHarvester()

    @pytest.fixture
    def raw_rct_article(self) -> RawPubMedArticle:
        """Create a raw RCT article."""
        return RawPubMedArticle(
            pmid="12345678",
            title="Effects of Lion's Mane on Cognitive Function",
            abstract="Methods: 77 participants were randomized. Results: Significant improvement.",
            authors=["Mori K", "Inatomi S"],
            journal="Phytotherapy Research",
            pub_date=datetime.now(timezone.utc) - timedelta(days=30),
            doi="10.1002/ptr.12345",
            publication_types=["Randomized Controlled Trial"],
        )

    @pytest.fixture
    def raw_meta_analysis_article(self) -> RawPubMedArticle:
        """Create a raw meta-analysis article."""
        return RawPubMedArticle(
            pmid="87654321",
            title="Meta-Analysis of Adaptogenic Mushrooms",
            abstract="We analyzed 25 studies (n=1,847 participants).",
            authors=["Smith J", "Brown A"],
            journal="Journal of Alternative Medicine",
            pub_date=datetime.now(timezone.utc) - timedelta(days=15),
            doi="10.1080/jam.12345",
            publication_types=["Meta-Analysis", "Systematic Review"],
        )

    @pytest.mark.asyncio
    async def test_harvest_single_rct(self, harvester, raw_rct_article):
        """Should harvest a single RCT article with correct metadata."""
        result = await harvester.harvest([raw_rct_article])

        assert len(result) == 1
        article = result[0]

        assert article.pmid == "12345678"
        assert article.title == "Effects of Lion's Mane on Cognitive Function"
        assert article.study_type == StudyType.RCT
        assert article.pubmed_url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
        # Sample size should be extracted (77 participants)
        assert article.sample_size == 77

    @pytest.mark.asyncio
    async def test_harvest_single_meta_analysis(self, harvester, raw_meta_analysis_article):
        """Should harvest a meta-analysis article with correct study type."""
        result = await harvester.harvest([raw_meta_analysis_article])

        assert len(result) == 1
        article = result[0]

        assert article.pmid == "87654321"
        # Meta-Analysis should take precedence in classification
        assert article.study_type == StudyType.META_ANALYSIS
        # Sample size should be extracted (1,847 participants)
        assert article.sample_size == 1847

    @pytest.mark.asyncio
    async def test_harvest_preserves_authors_limited(self, harvester):
        """Should limit authors to 10."""
        many_authors = [f"Author{i}" for i in range(15)]
        raw = RawPubMedArticle(
            pmid="11111111",
            title="Multi-Author Study",
            abstract="A study with many authors.",
            authors=many_authors,
            journal="Test Journal",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=["Review"],
        )

        result = await harvester.harvest([raw])

        assert len(result[0].authors) == 10
        assert result[0].authors[0] == "Author0"
        assert result[0].authors[9] == "Author9"

    @pytest.mark.asyncio
    async def test_harvest_handles_missing_abstract(self, harvester):
        """Should handle articles without abstract."""
        raw = RawPubMedArticle(
            pmid="22222222",
            title="Article Without Abstract",
            abstract="",
            authors=["Test Author"],
            journal="Test Journal",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=["Other"],
        )

        result = await harvester.harvest([raw])

        assert len(result) == 1
        assert result[0].sample_size is None

    @pytest.mark.asyncio
    async def test_harvest_handles_missing_pub_date(self, harvester):
        """Should use current date if pub_date is missing."""
        raw = RawPubMedArticle(
            pmid="33333333",
            title="Article Without Date",
            abstract="Test abstract",
            authors=["Test Author"],
            journal="Test Journal",
            pub_date=None,
            doi=None,
            publication_types=["Other"],
        )

        result = await harvester.harvest([raw])

        assert len(result) == 1
        assert result[0].pub_date is not None
        # Should be recent (within last hour)
        time_diff = datetime.now(timezone.utc) - result[0].pub_date
        assert time_diff.total_seconds() < 3600


class TestStudyTypeClassification:
    """Tests for study type classification."""

    @pytest.fixture
    def harvester(self):
        """Create harvester instance."""
        return PubMedHarvester()

    @pytest.mark.asyncio
    async def test_classify_rct(self, harvester):
        """Should classify as RCT."""
        raw = RawPubMedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=["Randomized Controlled Trial"],
        )

        result = await harvester.harvest([raw])
        assert result[0].study_type == StudyType.RCT

    @pytest.mark.asyncio
    async def test_classify_meta_analysis(self, harvester):
        """Should classify as Meta-Analysis."""
        raw = RawPubMedArticle(
            pmid="2",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=["Meta-Analysis"],
        )

        result = await harvester.harvest([raw])
        assert result[0].study_type == StudyType.META_ANALYSIS

    @pytest.mark.asyncio
    async def test_classify_systematic_review(self, harvester):
        """Should classify as Systematic Review."""
        raw = RawPubMedArticle(
            pmid="3",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=["Systematic Review"],
        )

        result = await harvester.harvest([raw])
        assert result[0].study_type == StudyType.SYSTEMATIC_REVIEW

    @pytest.mark.asyncio
    async def test_classify_review(self, harvester):
        """Should classify as Review."""
        raw = RawPubMedArticle(
            pmid="4",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=["Review"],
        )

        result = await harvester.harvest([raw])
        assert result[0].study_type == StudyType.REVIEW

    @pytest.mark.asyncio
    async def test_classify_other(self, harvester):
        """Should classify as Other when no known types."""
        raw = RawPubMedArticle(
            pmid="5",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=["Journal Article", "Case Report"],
        )

        result = await harvester.harvest([raw])
        assert result[0].study_type == StudyType.OTHER


class TestSampleSizeExtraction:
    """Tests for sample size extraction from abstracts."""

    @pytest.fixture
    def harvester(self):
        """Create harvester instance."""
        return PubMedHarvester()

    @pytest.mark.asyncio
    async def test_extract_n_equals_format(self, harvester):
        """Should extract sample size from n=X format."""
        raw = RawPubMedArticle(
            pmid="1",
            title="Test",
            abstract="We enrolled participants (n=150) in the study.",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=[],
        )

        result = await harvester.harvest([raw])
        assert result[0].sample_size == 150

    @pytest.mark.asyncio
    async def test_extract_participants_format(self, harvester):
        """Should extract sample size from X participants format."""
        raw = RawPubMedArticle(
            pmid="2",
            title="Test",
            abstract="Methods: 200 participants were enrolled.",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=[],
        )

        result = await harvester.harvest([raw])
        assert result[0].sample_size == 200

    @pytest.mark.asyncio
    async def test_extract_subjects_format(self, harvester):
        """Should extract sample size from X subjects format."""
        raw = RawPubMedArticle(
            pmid="3",
            title="Test",
            abstract="The study included 85 subjects.",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=[],
        )

        result = await harvester.harvest([raw])
        assert result[0].sample_size == 85

    @pytest.mark.asyncio
    async def test_extract_with_comma(self, harvester):
        """Should extract sample size with comma formatting."""
        raw = RawPubMedArticle(
            pmid="4",
            title="Test",
            abstract="A total of 1,500 patients were included.",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=[],
        )

        result = await harvester.harvest([raw])
        assert result[0].sample_size == 1500

    @pytest.mark.asyncio
    async def test_no_sample_size_found(self, harvester):
        """Should return None when no sample size found."""
        raw = RawPubMedArticle(
            pmid="5",
            title="Test",
            abstract="This is a theoretical review paper.",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=[],
        )

        result = await harvester.harvest([raw])
        assert result[0].sample_size is None


class TestBatchHarvesting:
    """Tests for batch harvesting functionality."""

    @pytest.fixture
    def harvester(self):
        """Create harvester instance."""
        return PubMedHarvester()

    @pytest.fixture
    def raw_articles(self) -> list[RawPubMedArticle]:
        """Create a batch of raw articles."""
        return [
            RawPubMedArticle(
                pmid=str(i),
                title=f"Article {i}",
                abstract=f"Abstract for article {i} with {i * 10} participants.",
                authors=[f"Author{i}"],
                journal="Test Journal",
                pub_date=datetime.now(timezone.utc) - timedelta(days=i),
                doi=f"10.1234/test.{i}",
                publication_types=["Review"],
            )
            for i in range(5)
        ]

    @pytest.mark.asyncio
    async def test_harvest_multiple_articles(self, harvester, raw_articles):
        """Should harvest multiple articles."""
        result = await harvester.harvest(raw_articles)

        assert len(result) == 5
        # Verify each has expected metadata
        for i, article in enumerate(result):
            assert article.pmid == str(i)
            assert article.title == f"Article {i}"
            assert article.pubmed_url == f"https://pubmed.ncbi.nlm.nih.gov/{i}/"

    @pytest.mark.asyncio
    async def test_harvest_batch_method(self, harvester, raw_articles):
        """Should harvest in batches with batch_size parameter."""
        result = await harvester.harvest_batch(raw_articles, batch_size=2)

        assert len(result) == 5
        # All articles should be processed regardless of batch size

    @pytest.mark.asyncio
    async def test_harvest_empty_list(self, harvester):
        """Should return empty list for empty input."""
        result = await harvester.harvest([])
        assert result == []


class TestErrorHandling:
    """Tests for error handling in harvester."""

    @pytest.fixture
    def harvester(self):
        """Create harvester instance."""
        return PubMedHarvester()

    @pytest.mark.asyncio
    async def test_continues_on_single_failure(self, harvester):
        """Should continue processing if one article fails."""
        good_article = RawPubMedArticle(
            pmid="1",
            title="Good Article",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=[],
        )

        # Create list with good article
        result = await harvester.harvest([good_article])

        # Should process successfully
        assert len(result) == 1


class TestHarvesterError:
    """Tests for HarvesterError exception."""

    def test_error_with_message_only(self):
        """Should create error with message only."""
        error = HarvesterError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.pmid is None

    def test_error_with_pmid(self):
        """Should create error with PMID."""
        error = HarvesterError("Failed to harvest", pmid="12345678")

        assert error.message == "Failed to harvest"
        assert error.pmid == "12345678"


class TestPubMedUrlGeneration:
    """Tests for PubMed URL generation."""

    def test_url_template(self):
        """Should have correct URL template."""
        assert PUBMED_URL_TEMPLATE == "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    @pytest.mark.asyncio
    async def test_generates_correct_url(self):
        """Should generate correct PubMed URL."""
        harvester = PubMedHarvester()
        raw = RawPubMedArticle(
            pmid="38123456",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            publication_types=[],
        )

        result = await harvester.harvest([raw])

        assert result[0].pubmed_url == "https://pubmed.ncbi.nlm.nih.gov/38123456/"
