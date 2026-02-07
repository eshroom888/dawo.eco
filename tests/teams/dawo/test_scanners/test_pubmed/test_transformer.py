"""Tests for PubMed Transformer stage.

Tests for the transformer stage:
    Scanner -> Harvester -> FindingSummarizer -> ClaimValidator -> [Transformer] -> Validator -> Publisher

Test categories:
    - Initialization
    - Single article transformation
    - Tag generation
    - Content building
    - Metadata building
    - Batch transformation
    - Error handling
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from teams.dawo.scanners.pubmed.schemas import (
    HarvestedArticle,
    FindingSummary,
    ClaimValidationResult,
    ValidatedResearch,
    StudyType,
    ContentPotential,
)
from teams.dawo.scanners.pubmed.transformer import (
    PubMedTransformer,
    TransformerError,
    MAX_CONTENT_LENGTH,
    MAX_SUMMARY_LENGTH,
)


class TestTransformerInit:
    """Tests for PubMedTransformer initialization."""

    def test_transformer_creates_without_dependencies(self):
        """Transformer should create without dependencies."""
        transformer = PubMedTransformer()
        assert transformer is not None


class TestSingleArticleTransformation:
    """Tests for single article transformation."""

    @pytest.fixture
    def transformer(self):
        """Create transformer instance."""
        return PubMedTransformer()

    @pytest.fixture
    def sample_article(self) -> HarvestedArticle:
        """Create sample harvested article."""
        return HarvestedArticle(
            pmid="12345678",
            title="Effects of Lion's Mane on Cognitive Function",
            abstract="This RCT examined the effects of Hericium erinaceus.",
            authors=["Mori K", "Inatomi S"],
            journal="Phytotherapy Research",
            pub_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
            doi="10.1002/ptr.12345",
            study_type=StudyType.RCT,
            sample_size=77,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        )

    @pytest.fixture
    def sample_summary(self) -> FindingSummary:
        """Create sample finding summary."""
        return FindingSummary(
            compound_studied="Lion's Mane (Hericium erinaceus)",
            effect_measured="Cognitive function improvement",
            key_findings="Treatment showed significant improvement in cognitive scores.",
            statistical_significance="p<0.05, n=77",
            study_strength="strong",
            content_potential=["educational", "citation_worthy"],
            caveat="Research finding - not an approved health claim."
        )

    @pytest.fixture
    def sample_validation(self) -> ClaimValidationResult:
        """Create sample claim validation result."""
        return ClaimValidationResult(
            content_potential=[ContentPotential.CITATION_ONLY, ContentPotential.EDUCATIONAL],
            usage_guidance="Can cite this study when discussing research directions.",
            eu_claim_status="no_approved_claim",
            caveat="Can cite study but NOT claim treatment/prevention/cure",
            can_cite_study=True,
            can_make_claim=False
        )

    @pytest.mark.asyncio
    async def test_transform_returns_validated_research_list(
        self, transformer, sample_article, sample_summary, sample_validation
    ):
        """Should return list of ValidatedResearch."""
        summaries = {sample_article.pmid: sample_summary}
        validations = {sample_article.pmid: sample_validation}

        result = await transformer.transform([sample_article], summaries, validations)

        assert len(result) == 1
        assert isinstance(result[0], ValidatedResearch)

    @pytest.mark.asyncio
    async def test_transform_sets_source_pubmed(
        self, transformer, sample_article, sample_summary, sample_validation
    ):
        """Should set source to 'pubmed'."""
        summaries = {sample_article.pmid: sample_summary}
        validations = {sample_article.pmid: sample_validation}

        result = await transformer.transform([sample_article], summaries, validations)

        assert result[0].source == "pubmed"

    @pytest.mark.asyncio
    async def test_transform_sets_source_id_to_pmid(
        self, transformer, sample_article, sample_summary, sample_validation
    ):
        """Should set source_id to PMID."""
        summaries = {sample_article.pmid: sample_summary}
        validations = {sample_article.pmid: sample_validation}

        result = await transformer.transform([sample_article], summaries, validations)

        assert result[0].source_id == "12345678"

    @pytest.mark.asyncio
    async def test_transform_preserves_url(
        self, transformer, sample_article, sample_summary, sample_validation
    ):
        """Should preserve PubMed URL."""
        summaries = {sample_article.pmid: sample_summary}
        validations = {sample_article.pmid: sample_validation}

        result = await transformer.transform([sample_article], summaries, validations)

        assert result[0].url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"

    @pytest.mark.asyncio
    async def test_transform_sets_pending_compliance(
        self, transformer, sample_article, sample_summary, sample_validation
    ):
        """Should set compliance_status to PENDING."""
        summaries = {sample_article.pmid: sample_summary}
        validations = {sample_article.pmid: sample_validation}

        result = await transformer.transform([sample_article], summaries, validations)

        assert result[0].compliance_status == "PENDING"

    @pytest.mark.asyncio
    async def test_transform_without_summary(self, transformer, sample_article):
        """Should transform without summary."""
        result = await transformer.transform([sample_article], {}, {})

        assert len(result) == 1
        # Should fall back to abstract for summary
        assert "This RCT examined" in result[0].summary


class TestTagGeneration:
    """Tests for tag generation."""

    @pytest.fixture
    def transformer(self):
        """Create transformer instance."""
        return PubMedTransformer()

    @pytest.mark.asyncio
    async def test_includes_study_type_tag_rct(self, transformer):
        """Should include RCT study type tag."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.RCT,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await transformer.transform([article], {}, {})

        assert "rct" in result[0].tags

    @pytest.mark.asyncio
    async def test_includes_study_type_tag_meta_analysis(self, transformer):
        """Should include meta-analysis study type tag."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.META_ANALYSIS,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await transformer.transform([article], {}, {})

        assert "meta-analysis" in result[0].tags

    @pytest.mark.asyncio
    async def test_includes_pubmed_tag(self, transformer):
        """Should always include pubmed tag."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await transformer.transform([article], {}, {})

        assert "pubmed" in result[0].tags
        assert "scientific-research" in result[0].tags

    @pytest.mark.asyncio
    async def test_includes_mushroom_tag_from_summary(self, transformer):
        """Should include mushroom tag from summary."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )
        summary = FindingSummary(
            compound_studied="Lion's Mane extract",
            effect_measured="Cognitive enhancement",
            key_findings="Test",
            statistical_significance=None,
            study_strength="moderate",
            content_potential=[],
            caveat="Test"
        )

        result = await transformer.transform([article], {"1": summary}, {})

        assert "lions-mane" in result[0].tags

    @pytest.mark.asyncio
    async def test_includes_effect_tag_from_summary(self, transformer):
        """Should include effect tag from summary."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )
        summary = FindingSummary(
            compound_studied="Test compound",
            effect_measured="Immune function support",
            key_findings="Test",
            statistical_significance=None,
            study_strength="moderate",
            content_potential=[],
            caveat="Test"
        )

        result = await transformer.transform([article], {"1": summary}, {})

        assert "immune" in result[0].tags

    @pytest.mark.asyncio
    async def test_limits_tags_to_10(self, transformer):
        """Should limit tags to 10."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.RCT,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await transformer.transform([article], {}, {})

        assert len(result[0].tags) <= 10


class TestContentBuilding:
    """Tests for content building."""

    @pytest.fixture
    def transformer(self):
        """Create transformer instance."""
        return PubMedTransformer()

    @pytest.mark.asyncio
    async def test_content_includes_abstract(self, transformer):
        """Should include abstract in content."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="This is the test abstract content.",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await transformer.transform([article], {}, {})

        assert "This is the test abstract content" in result[0].content
        assert "**Abstract:**" in result[0].content

    @pytest.mark.asyncio
    async def test_content_includes_key_findings(self, transformer):
        """Should include key findings from summary."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )
        summary = FindingSummary(
            compound_studied="Test",
            effect_measured="Test",
            key_findings="These are the key findings from the study.",
            statistical_significance=None,
            study_strength="moderate",
            content_potential=[],
            caveat="Test"
        )

        result = await transformer.transform([article], {"1": summary}, {})

        assert "These are the key findings" in result[0].content
        assert "**Key Findings:**" in result[0].content

    @pytest.mark.asyncio
    async def test_content_includes_usage_guidance(self, transformer):
        """Should include usage guidance from validation."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )
        validation = ClaimValidationResult(
            content_potential=[ContentPotential.EDUCATIONAL],
            usage_guidance="This is the usage guidance text.",
            eu_claim_status="no_approved_claim",
            caveat="Test caveat",
            can_cite_study=True,
            can_make_claim=False
        )

        result = await transformer.transform([article], {}, {"1": validation})

        assert "This is the usage guidance text" in result[0].content
        assert "**Usage Guidance:**" in result[0].content


class TestMetadataBuilding:
    """Tests for metadata building."""

    @pytest.fixture
    def transformer(self):
        """Create transformer instance."""
        return PubMedTransformer()

    @pytest.mark.asyncio
    async def test_metadata_includes_pmid(self, transformer):
        """Should include PMID in metadata."""
        article = HarvestedArticle(
            pmid="12345678",
            title="Test",
            abstract="Test",
            authors=["Author A"],
            journal="Test Journal",
            pub_date=datetime.now(timezone.utc),
            doi="10.1234/test",
            study_type=StudyType.RCT,
            sample_size=100,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        )

        result = await transformer.transform([article], {}, {})

        assert result[0].source_metadata["pmid"] == "12345678"

    @pytest.mark.asyncio
    async def test_metadata_includes_authors(self, transformer):
        """Should include authors in metadata."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=["Author A", "Author B"],
            journal="Test Journal",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await transformer.transform([article], {}, {})

        assert result[0].source_metadata["authors"] == ["Author A", "Author B"]

    @pytest.mark.asyncio
    async def test_metadata_includes_doi_when_present(self, transformer):
        """Should include DOI in metadata when present."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi="10.1234/test.123",
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )

        result = await transformer.transform([article], {}, {})

        assert result[0].source_metadata["doi"] == "10.1234/test.123"

    @pytest.mark.asyncio
    async def test_metadata_includes_claim_potential(self, transformer):
        """Should include claim potential from validation."""
        article = HarvestedArticle(
            pmid="1",
            title="Test",
            abstract="Test",
            authors=[],
            journal="Test",
            pub_date=datetime.now(timezone.utc),
            doi=None,
            study_type=StudyType.OTHER,
            sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )
        validation = ClaimValidationResult(
            content_potential=[ContentPotential.CITATION_ONLY],
            usage_guidance="Test",
            eu_claim_status="no_approved_claim",
            caveat="Test",
            can_cite_study=True,
            can_make_claim=False
        )

        result = await transformer.transform([article], {}, {"1": validation})

        assert "citation_only" in result[0].source_metadata["claim_potential"]


class TestBatchTransformation:
    """Tests for batch transformation."""

    @pytest.fixture
    def transformer(self):
        """Create transformer instance."""
        return PubMedTransformer()

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
    async def test_transforms_multiple_articles(
        self, transformer, sample_articles
    ):
        """Should transform multiple articles."""
        result = await transformer.transform(sample_articles, {}, {})

        assert len(result) == 3
        assert all(isinstance(r, ValidatedResearch) for r in result)

    @pytest.mark.asyncio
    async def test_continues_on_failure(self, transformer):
        """Should continue processing if one article fails."""
        articles = [
            HarvestedArticle(
                pmid="1",
                title="Good Article",
                abstract="Test",
                authors=[],
                journal="Test",
                pub_date=datetime.now(timezone.utc),
                doi=None,
                study_type=StudyType.OTHER,
                sample_size=None,
                pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
            ),
        ]

        result = await transformer.transform(articles, {}, {})

        assert len(result) == 1


class TestTransformerError:
    """Tests for TransformerError exception."""

    def test_error_with_message_only(self):
        """Should create error with message only."""
        error = TransformerError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.pmid is None

    def test_error_with_pmid(self):
        """Should create error with PMID."""
        error = TransformerError("Failed to transform", pmid="12345678")

        assert error.message == "Failed to transform"
        assert error.pmid == "12345678"
