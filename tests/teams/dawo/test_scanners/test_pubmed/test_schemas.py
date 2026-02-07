"""Tests for PubMed scanner schemas.

Tests schema validation, data structures, and enums used throughout
the PubMed scanner pipeline.
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID


class TestPipelineStatus:
    """Tests for PipelineStatus enum."""

    def test_complete_status(self):
        """Test COMPLETE status exists."""
        from teams.dawo.scanners.pubmed.schemas import PipelineStatus

        assert PipelineStatus.COMPLETE.value == "COMPLETE"

    def test_incomplete_status(self):
        """Test INCOMPLETE status exists."""
        from teams.dawo.scanners.pubmed.schemas import PipelineStatus

        assert PipelineStatus.INCOMPLETE.value == "INCOMPLETE"

    def test_partial_status(self):
        """Test PARTIAL status exists."""
        from teams.dawo.scanners.pubmed.schemas import PipelineStatus

        assert PipelineStatus.PARTIAL.value == "PARTIAL"

    def test_failed_status(self):
        """Test FAILED status exists."""
        from teams.dawo.scanners.pubmed.schemas import PipelineStatus

        assert PipelineStatus.FAILED.value == "FAILED"


class TestContentPotential:
    """Tests for ContentPotential enum."""

    def test_citation_only(self):
        """Test CITATION_ONLY value."""
        from teams.dawo.scanners.pubmed.schemas import ContentPotential

        assert ContentPotential.CITATION_ONLY.value == "citation_only"

    def test_educational(self):
        """Test EDUCATIONAL value."""
        from teams.dawo.scanners.pubmed.schemas import ContentPotential

        assert ContentPotential.EDUCATIONAL.value == "educational"

    def test_trend_awareness(self):
        """Test TREND_AWARENESS value."""
        from teams.dawo.scanners.pubmed.schemas import ContentPotential

        assert ContentPotential.TREND_AWARENESS.value == "trend_awareness"

    def test_no_claim(self):
        """Test NO_CLAIM value."""
        from teams.dawo.scanners.pubmed.schemas import ContentPotential

        assert ContentPotential.NO_CLAIM.value == "no_claim"


class TestStudyType:
    """Tests for StudyType enum."""

    def test_rct(self):
        """Test RCT study type."""
        from teams.dawo.scanners.pubmed.schemas import StudyType

        assert StudyType.RCT.value == "rct"

    def test_meta_analysis(self):
        """Test META_ANALYSIS study type."""
        from teams.dawo.scanners.pubmed.schemas import StudyType

        assert StudyType.META_ANALYSIS.value == "meta_analysis"

    def test_systematic_review(self):
        """Test SYSTEMATIC_REVIEW study type."""
        from teams.dawo.scanners.pubmed.schemas import StudyType

        assert StudyType.SYSTEMATIC_REVIEW.value == "systematic_review"

    def test_review(self):
        """Test REVIEW study type."""
        from teams.dawo.scanners.pubmed.schemas import StudyType

        assert StudyType.REVIEW.value == "review"

    def test_other(self):
        """Test OTHER study type."""
        from teams.dawo.scanners.pubmed.schemas import StudyType

        assert StudyType.OTHER.value == "other"


class TestRawPubMedArticle:
    """Tests for RawPubMedArticle schema."""

    def test_create_raw_article(self):
        """Test creating a raw PubMed article."""
        from teams.dawo.scanners.pubmed.schemas import RawPubMedArticle

        article = RawPubMedArticle(
            pmid="12345678",
            title="Test Article",
        )
        assert article.pmid == "12345678"
        assert article.title == "Test Article"

    def test_raw_article_defaults(self):
        """Test RawPubMedArticle default values."""
        from teams.dawo.scanners.pubmed.schemas import RawPubMedArticle

        article = RawPubMedArticle(
            pmid="12345678",
            title="Test Article",
        )
        assert article.abstract == ""
        assert article.authors == []
        assert article.journal == ""
        assert article.pub_date is None
        assert article.doi is None
        assert article.publication_types == []

    def test_raw_article_full_data(self):
        """Test RawPubMedArticle with full data."""
        from teams.dawo.scanners.pubmed.schemas import RawPubMedArticle

        pub_date = datetime.now(timezone.utc)
        article = RawPubMedArticle(
            pmid="12345678",
            title="Effects of Lion's Mane on Cognition",
            abstract="Background: This study...",
            authors=["Smith J", "Doe A"],
            journal="Phytotherapy Research",
            pub_date=pub_date,
            doi="10.1002/ptr.12345",
            publication_types=["Randomized Controlled Trial"],
        )
        assert article.pmid == "12345678"
        assert article.title == "Effects of Lion's Mane on Cognition"
        assert article.abstract == "Background: This study..."
        assert article.authors == ["Smith J", "Doe A"]
        assert article.journal == "Phytotherapy Research"
        assert article.pub_date == pub_date
        assert article.doi == "10.1002/ptr.12345"
        assert article.publication_types == ["Randomized Controlled Trial"]

    def test_raw_article_is_frozen(self):
        """Test RawPubMedArticle is immutable."""
        from teams.dawo.scanners.pubmed.schemas import RawPubMedArticle

        article = RawPubMedArticle(pmid="12345678", title="Test")
        with pytest.raises(Exception):  # Pydantic ValidationError or AttributeError
            article.pmid = "99999999"


class TestHarvestedArticle:
    """Tests for HarvestedArticle schema."""

    def test_create_harvested_article(self):
        """Test creating a harvested article."""
        from teams.dawo.scanners.pubmed.schemas import HarvestedArticle, StudyType

        article = HarvestedArticle(
            pmid="12345678",
            title="Test Article",
            abstract="Abstract text",
            authors=["Smith J"],
            journal="Test Journal",
            pub_date=datetime.now(timezone.utc),
            doi="10.1000/test",
            study_type=StudyType.RCT,
            sample_size=77,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        )
        assert article.pmid == "12345678"
        assert article.study_type == StudyType.RCT
        assert article.sample_size == 77

    def test_harvested_article_optional_fields(self):
        """Test HarvestedArticle with optional fields."""
        from teams.dawo.scanners.pubmed.schemas import HarvestedArticle, StudyType

        article = HarvestedArticle(
            pmid="12345678",
            title="Test Article",
            abstract="Abstract text",
            authors=[],
            journal="Test Journal",
            pub_date=datetime.now(timezone.utc),
            study_type=StudyType.OTHER,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        )
        assert article.doi is None
        assert article.sample_size is None


class TestFindingSummary:
    """Tests for FindingSummary dataclass."""

    def test_create_finding_summary(self):
        """Test creating a finding summary."""
        from teams.dawo.scanners.pubmed.schemas import FindingSummary

        summary = FindingSummary(
            compound_studied="Lion's mane extract (Hericium erinaceus)",
            effect_measured="cognitive function improvement",
            key_findings="A 12-week RCT found significant cognitive improvements.",
            statistical_significance="p<0.05, n=77",
            study_strength="strong",
            content_potential=["educational", "citation_worthy"],
            caveat="Research finding - not an approved health claim.",
        )
        assert summary.compound_studied == "Lion's mane extract (Hericium erinaceus)"
        assert summary.effect_measured == "cognitive function improvement"
        assert summary.study_strength == "strong"

    def test_finding_summary_optional_significance(self):
        """Test FindingSummary with optional statistical_significance."""
        from teams.dawo.scanners.pubmed.schemas import FindingSummary

        summary = FindingSummary(
            compound_studied="Chaga extract",
            effect_measured="antioxidant activity",
            key_findings="Review found antioxidant properties.",
            statistical_significance=None,
            study_strength="weak",
            content_potential=["educational"],
            caveat="Research finding - not an approved health claim.",
        )
        assert summary.statistical_significance is None


class TestClaimValidationResult:
    """Tests for ClaimValidationResult dataclass."""

    def test_create_claim_validation_result(self):
        """Test creating a claim validation result."""
        from teams.dawo.scanners.pubmed.schemas import ClaimValidationResult, ContentPotential

        result = ClaimValidationResult(
            content_potential=[ContentPotential.CITATION_ONLY, ContentPotential.EDUCATIONAL],
            usage_guidance="Can cite study in educational content about research directions.",
            eu_claim_status="no_approved_claim",
            caveat="Can cite study but NOT claim treatment/prevention/cure",
            can_cite_study=True,
            can_make_claim=False,
        )
        assert ContentPotential.CITATION_ONLY in result.content_potential
        assert result.can_cite_study is True
        assert result.can_make_claim is False


class TestValidatedResearch:
    """Tests for ValidatedResearch schema."""

    def test_create_validated_research(self):
        """Test creating validated research."""
        from teams.dawo.scanners.pubmed.schemas import ValidatedResearch

        research = ValidatedResearch(
            source="pubmed",
            source_id="12345678",
            title="Test Article",
            content="Abstract and summary content",
            summary="Plain-language summary of findings",
            url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            tags=["lion's mane", "cognitive", "rct"],
            source_metadata={
                "authors": ["Smith J"],
                "journal": "Test Journal",
                "doi": "10.1000/test",
                "study_type": "rct",
                "sample_size": 77,
            },
            created_at=datetime.now(timezone.utc),
            compliance_status="COMPLIANT",
            score=7.5,
        )
        assert research.source == "pubmed"
        assert research.source_id == "12345678"
        assert research.compliance_status == "COMPLIANT"

    def test_validated_research_defaults(self):
        """Test ValidatedResearch default values."""
        from teams.dawo.scanners.pubmed.schemas import ValidatedResearch

        research = ValidatedResearch(
            source="pubmed",
            source_id="12345678",
            title="Test Article",
            content="Content",
            summary="Summary",
            url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            created_at=datetime.now(timezone.utc),
        )
        assert research.tags == []
        assert research.source_metadata == {}
        assert research.compliance_status == "COMPLIANT"
        assert research.score == 0.0


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_create_scan_result(self):
        """Test creating a scan result."""
        from teams.dawo.scanners.pubmed.schemas import ScanResult, ScanStatistics

        result = ScanResult(
            articles=[],
            statistics=ScanStatistics(
                queries_executed=5,
                total_pmids_found=25,
                pmids_after_dedup=20,
            ),
            errors=[],
        )
        assert result.statistics.queries_executed == 5
        assert result.statistics.total_pmids_found == 25


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_create_pipeline_result_complete(self):
        """Test creating a complete pipeline result."""
        from teams.dawo.scanners.pubmed.schemas import (
            PipelineResult,
            PipelineStatus,
            PipelineStatistics,
        )

        result = PipelineResult(
            status=PipelineStatus.COMPLETE,
            statistics=PipelineStatistics(
                total_found=10,
                harvested=10,
                summarized=10,
                claim_validated=10,
                transformed=10,
                validated=9,
                scored=9,
                published=9,
            ),
        )
        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.published == 9

    def test_create_pipeline_result_incomplete(self):
        """Test creating an incomplete pipeline result."""
        from teams.dawo.scanners.pubmed.schemas import PipelineResult, PipelineStatus

        result = PipelineResult(
            status=PipelineStatus.INCOMPLETE,
            error="Entrez API unavailable after retries",
            retry_scheduled=True,
        )
        assert result.status == PipelineStatus.INCOMPLETE
        assert result.retry_scheduled is True
        assert "Entrez" in result.error
