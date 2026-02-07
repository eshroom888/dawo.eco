"""Tests for PubMed Research Pipeline.

Tests for the full pipeline orchestration:
    Scanner -> Harvester -> FindingSummarizer -> ClaimValidator -> Transformer -> Validator -> Scorer -> Publisher

Test categories:
    - Initialization
    - Full pipeline execution
    - Individual stage execution
    - Graceful degradation
    - Score boosting
    - Error handling
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.scanners.pubmed.schemas import (
    RawPubMedArticle,
    HarvestedArticle,
    FindingSummary,
    ClaimValidationResult,
    ValidatedResearch,
    ScanResult,
    ScanStatistics,
    PipelineResult,
    PipelineStatus,
    PipelineStatistics,
    StudyType,
    ContentPotential,
)
from teams.dawo.scanners.pubmed.pipeline import (
    PubMedResearchPipeline,
    PipelineError,
    STUDY_TYPE_BOOSTS,
)
from teams.dawo.scanners.pubmed.agent import PubMedScanError


class TestPipelineInit:
    """Tests for PubMedResearchPipeline initialization."""

    def test_pipeline_creates_with_all_components(self):
        """Should create pipeline with all components."""
        scanner = MagicMock()
        harvester = MagicMock()
        summarizer = MagicMock()
        claim_validator = MagicMock()
        transformer = MagicMock()
        validator = MagicMock()
        scorer = MagicMock()
        publisher = MagicMock()

        pipeline = PubMedResearchPipeline(
            scanner, harvester, summarizer, claim_validator,
            transformer, validator, scorer, publisher
        )

        assert pipeline is not None
        assert pipeline._scanner == scanner
        assert pipeline._harvester == harvester
        assert pipeline._summarizer == summarizer
        assert pipeline._claim_validator == claim_validator


class TestPipelineExecution:
    """Tests for full pipeline execution."""

    @pytest.fixture
    def mock_scanner(self):
        """Create mock scanner."""
        scanner = AsyncMock()
        scanner.scan = AsyncMock(return_value=ScanResult(
            articles=[
                RawPubMedArticle(
                    pmid="12345678",
                    title="Test Article",
                    abstract="Test abstract",
                    authors=["Author A"],
                    journal="Test Journal",
                    pub_date=datetime.now(timezone.utc),
                    doi="10.1234/test",
                    publication_types=["Randomized Controlled Trial"],
                )
            ],
            statistics=ScanStatistics(
                queries_executed=1,
                total_pmids_found=1,
                pmids_after_dedup=1,
                queries_failed=0,
            ),
            errors=[],
        ))
        return scanner

    @pytest.fixture
    def mock_harvester(self):
        """Create mock harvester."""
        harvester = AsyncMock()
        harvester.harvest = AsyncMock(return_value=[
            HarvestedArticle(
                pmid="12345678",
                title="Test Article",
                abstract="Test abstract",
                authors=["Author A"],
                journal="Test Journal",
                pub_date=datetime.now(timezone.utc),
                doi="10.1234/test",
                study_type=StudyType.RCT,
                sample_size=100,
                pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            )
        ])
        return harvester

    @pytest.fixture
    def mock_summarizer(self):
        """Create mock summarizer."""
        summarizer = AsyncMock()
        summarizer.summarize_batch = AsyncMock(return_value={
            "12345678": FindingSummary(
                compound_studied="Test compound",
                effect_measured="Test effect",
                key_findings="Test findings",
                statistical_significance="p<0.05",
                study_strength="strong",
                content_potential=["educational"],
                caveat="Test caveat"
            )
        })
        return summarizer

    @pytest.fixture
    def mock_claim_validator(self):
        """Create mock claim validator."""
        validator = AsyncMock()
        validator.validate_batch = AsyncMock(return_value={
            "12345678": ClaimValidationResult(
                content_potential=[ContentPotential.EDUCATIONAL],
                usage_guidance="Test guidance",
                eu_claim_status="no_approved_claim",
                caveat="Test caveat",
                can_cite_study=True,
                can_make_claim=False,
            )
        })
        return validator

    @pytest.fixture
    def mock_transformer(self):
        """Create mock transformer."""
        transformer = AsyncMock()
        transformer.transform = AsyncMock(return_value=[
            ValidatedResearch(
                source="pubmed",
                source_id="12345678",
                title="Test Article",
                content="Test content",
                summary="Test summary",
                url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
                tags=["pubmed"],
                source_metadata={},
                created_at=datetime.now(timezone.utc),
                compliance_status="PENDING",
                score=0.0,
            )
        ])
        return transformer

    @pytest.fixture
    def mock_validator(self):
        """Create mock validator."""
        validator = AsyncMock()
        validator.validate = AsyncMock(return_value=[
            ValidatedResearch(
                source="pubmed",
                source_id="12345678",
                title="Test Article",
                content="Test content",
                summary="Test summary",
                url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
                tags=["pubmed"],
                source_metadata={},
                created_at=datetime.now(timezone.utc),
                compliance_status="COMPLIANT",
                score=0.0,
            )
        ])
        return validator

    @pytest.fixture
    def mock_scorer(self):
        """Create mock scorer."""
        scorer = MagicMock()
        scorer.score = MagicMock(return_value=MagicMock(final_score=5.0))
        return scorer

    @pytest.fixture
    def mock_publisher(self):
        """Create mock publisher."""
        publisher = AsyncMock()
        published_item = MagicMock()
        published_item.id = uuid4()
        publisher.publish_batch = AsyncMock(return_value=[published_item])
        return publisher

    @pytest.mark.asyncio
    async def test_execute_returns_pipeline_result(
        self, mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
        mock_transformer, mock_validator, mock_scorer, mock_publisher
    ):
        """Should return PipelineResult on successful execution."""
        pipeline = PubMedResearchPipeline(
            mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
            mock_transformer, mock_validator, mock_scorer, mock_publisher
        )

        result = await pipeline.execute()

        assert isinstance(result, PipelineResult)
        assert result.status in [PipelineStatus.COMPLETE, PipelineStatus.PARTIAL]

    @pytest.mark.asyncio
    async def test_execute_calls_all_stages_in_order(
        self, mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
        mock_transformer, mock_validator, mock_scorer, mock_publisher
    ):
        """Should call all stages in correct order."""
        pipeline = PubMedResearchPipeline(
            mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
            mock_transformer, mock_validator, mock_scorer, mock_publisher
        )

        await pipeline.execute()

        mock_scanner.scan.assert_called_once()
        mock_harvester.harvest.assert_called_once()
        mock_summarizer.summarize_batch.assert_called_once()
        mock_claim_validator.validate_batch.assert_called_once()
        mock_transformer.transform.assert_called_once()
        mock_validator.validate.assert_called_once()
        mock_publisher.publish_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_complete_status_on_success(
        self, mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
        mock_transformer, mock_validator, mock_scorer, mock_publisher
    ):
        """Should return COMPLETE status on full success."""
        pipeline = PubMedResearchPipeline(
            mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
            mock_transformer, mock_validator, mock_scorer, mock_publisher
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_execute_tracks_published_ids(
        self, mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
        mock_transformer, mock_validator, mock_scorer, mock_publisher
    ):
        """Should track published item IDs."""
        pipeline = PubMedResearchPipeline(
            mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
            mock_transformer, mock_validator, mock_scorer, mock_publisher
        )

        result = await pipeline.execute()

        assert len(result.published_ids) == 1

    @pytest.mark.asyncio
    async def test_execute_populates_statistics(
        self, mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
        mock_transformer, mock_validator, mock_scorer, mock_publisher
    ):
        """Should populate statistics."""
        pipeline = PubMedResearchPipeline(
            mock_scanner, mock_harvester, mock_summarizer, mock_claim_validator,
            mock_transformer, mock_validator, mock_scorer, mock_publisher
        )

        result = await pipeline.execute()

        assert result.statistics.total_found == 1
        assert result.statistics.harvested == 1
        assert result.statistics.summarized == 1
        assert result.statistics.published == 1


class TestGracefulDegradation:
    """Tests for graceful degradation on failures."""

    @pytest.fixture
    def base_mocks(self):
        """Create base mock components."""
        return {
            "scanner": AsyncMock(),
            "harvester": AsyncMock(),
            "summarizer": AsyncMock(),
            "claim_validator": AsyncMock(),
            "transformer": AsyncMock(),
            "validator": AsyncMock(),
            "scorer": MagicMock(),
            "publisher": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_returns_incomplete_on_empty_scan(self, base_mocks):
        """Should return INCOMPLETE when scan finds no articles."""
        base_mocks["scanner"].scan = AsyncMock(return_value=ScanResult(
            articles=[],
            statistics=ScanStatistics(),
            errors=[],
        ))

        pipeline = PubMedResearchPipeline(**base_mocks)

        result = await pipeline.execute()

        assert result.status == PipelineStatus.INCOMPLETE
        assert result.retry_scheduled is True

    @pytest.mark.asyncio
    async def test_returns_incomplete_on_scan_error(self, base_mocks):
        """Should return INCOMPLETE on scan failure."""
        base_mocks["scanner"].scan = AsyncMock(
            side_effect=PubMedScanError("All queries failed")
        )

        pipeline = PubMedResearchPipeline(**base_mocks)

        result = await pipeline.execute()

        assert result.status == PipelineStatus.INCOMPLETE
        assert result.retry_scheduled is True

    @pytest.mark.asyncio
    async def test_returns_incomplete_on_empty_harvest(self, base_mocks):
        """Should return INCOMPLETE when harvest returns no articles."""
        base_mocks["scanner"].scan = AsyncMock(return_value=ScanResult(
            articles=[RawPubMedArticle(
                pmid="1", title="Test", abstract="Test",
                authors=[], journal="", pub_date=None, doi=None, publication_types=[]
            )],
            statistics=ScanStatistics(queries_executed=1, total_pmids_found=1),
            errors=[],
        ))
        base_mocks["harvester"].harvest = AsyncMock(return_value=[])

        pipeline = PubMedResearchPipeline(**base_mocks)

        result = await pipeline.execute()

        assert result.status == PipelineStatus.INCOMPLETE

    @pytest.mark.asyncio
    async def test_returns_failed_on_unexpected_error(self, base_mocks):
        """Should return FAILED on unexpected errors."""
        base_mocks["scanner"].scan = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        pipeline = PubMedResearchPipeline(**base_mocks)

        result = await pipeline.execute()

        assert result.status == PipelineStatus.FAILED
        assert result.retry_scheduled is True


class TestScoreBoosting:
    """Tests for study type score boosting."""

    def test_study_type_boost_values(self):
        """Should have correct boost values for study types."""
        assert STUDY_TYPE_BOOSTS[StudyType.RCT] == 2.0
        assert STUDY_TYPE_BOOSTS[StudyType.META_ANALYSIS] == 2.5
        assert STUDY_TYPE_BOOSTS[StudyType.SYSTEMATIC_REVIEW] == 2.0
        assert STUDY_TYPE_BOOSTS[StudyType.REVIEW] == 1.0
        assert STUDY_TYPE_BOOSTS[StudyType.OTHER] == 0.5

    @pytest.mark.asyncio
    async def test_applies_rct_boost(self):
        """Should apply RCT score boost."""
        # Create mock components
        scanner = AsyncMock()
        scanner.scan = AsyncMock(return_value=ScanResult(
            articles=[RawPubMedArticle(
                pmid="1", title="Test", abstract="Test",
                authors=[], journal="", pub_date=datetime.now(timezone.utc),
                doi=None, publication_types=["Randomized Controlled Trial"]
            )],
            statistics=ScanStatistics(queries_executed=1, total_pmids_found=1),
            errors=[],
        ))

        harvester = AsyncMock()
        harvested_article = HarvestedArticle(
            pmid="1", title="Test", abstract="Test", authors=[], journal="",
            pub_date=datetime.now(timezone.utc), doi=None,
            study_type=StudyType.RCT, sample_size=None,
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        )
        harvester.harvest = AsyncMock(return_value=[harvested_article])

        summarizer = AsyncMock()
        summarizer.summarize_batch = AsyncMock(return_value={
            "1": FindingSummary(
                compound_studied="Test", effect_measured="Test",
                key_findings="Test", statistical_significance=None,
                study_strength="strong", content_potential=[], caveat=""
            )
        })

        claim_validator = AsyncMock()
        claim_validator.validate_batch = AsyncMock(return_value={
            "1": ClaimValidationResult(
                content_potential=[ContentPotential.EDUCATIONAL],
                usage_guidance="Test", eu_claim_status="no_approved_claim",
                caveat="", can_cite_study=True, can_make_claim=False
            )
        })

        transformer = AsyncMock()
        transformer.transform = AsyncMock(return_value=[
            ValidatedResearch(
                source="pubmed", source_id="1", title="Test", content="Test",
                summary="Test", url="url", tags=[], source_metadata={},
                created_at=datetime.now(timezone.utc), compliance_status="PENDING", score=0.0
            )
        ])

        validator = AsyncMock()
        validator.validate = AsyncMock(return_value=[
            ValidatedResearch(
                source="pubmed", source_id="1", title="Test", content="Test",
                summary="Test", url="url", tags=[], source_metadata={},
                created_at=datetime.now(timezone.utc), compliance_status="COMPLIANT", score=0.0
            )
        ])

        scorer = MagicMock()
        scorer.score = MagicMock(return_value=MagicMock(final_score=5.0))

        publisher = AsyncMock()
        published_item = MagicMock()
        published_item.id = uuid4()
        publisher.publish_batch = AsyncMock(return_value=[published_item])

        pipeline = PubMedResearchPipeline(
            scanner, harvester, summarizer, claim_validator,
            transformer, validator, scorer, publisher
        )

        await pipeline.execute()

        # Verify publish_batch was called with boosted score
        call_args = publisher.publish_batch.call_args[0][0]
        # RCT boost is 2.0, base score is 5.0, so final should be 7.0
        assert call_args[0].score == 7.0


class TestPipelineError:
    """Tests for PipelineError exception."""

    def test_error_with_message_only(self):
        """Should create error with message only."""
        error = PipelineError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.stage is None

    def test_error_with_stage(self):
        """Should create error with stage."""
        error = PipelineError("Failed at stage", stage="scan")

        assert error.message == "Failed at stage"
        assert error.stage == "scan"
