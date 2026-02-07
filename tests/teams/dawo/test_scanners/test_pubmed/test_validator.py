"""Tests for PubMed Validator stage.

Tests for the EU compliance validation stage:
    Scanner -> Harvester -> FindingSummarizer -> ClaimValidator -> Transformer -> [Validator] -> Publisher

Test categories:
    - Initialization
    - Single item validation
    - Compliance status mapping
    - Batch validation
    - Error handling
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from teams.dawo.scanners.pubmed.schemas import ValidatedResearch
from teams.dawo.scanners.pubmed.validator import (
    PubMedValidator,
    ValidatorError,
)
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    OverallStatus,
    ContentComplianceCheck,
)
from teams.dawo.validators.research_compliance import ResearchComplianceValidator


@pytest.fixture
def mock_eu_compliance_checker() -> AsyncMock:
    """Mock EUComplianceChecker for testing."""
    checker = AsyncMock(spec=EUComplianceChecker)
    result = ContentComplianceCheck(
        overall_status=OverallStatus.COMPLIANT,
        flagged_phrases=[],
        compliance_score=1.0,
        llm_enhanced=False,
    )
    checker.check_content.return_value = result
    return checker


@pytest.fixture
def mock_research_compliance(mock_eu_compliance_checker: AsyncMock) -> ResearchComplianceValidator:
    """Create ResearchComplianceValidator with mocked EU Compliance Checker."""
    return ResearchComplianceValidator(compliance_checker=mock_eu_compliance_checker)


class TestValidatorInit:
    """Tests for PubMedValidator initialization."""

    def test_validator_creates_with_research_compliance(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ):
        """Should create validator with ResearchComplianceValidator."""
        validator = PubMedValidator(mock_research_compliance)

        assert validator is not None
        assert validator._compliance == mock_research_compliance


class TestSingleItemValidation:
    """Tests for single item validation."""

    @pytest.fixture
    def sample_item(self) -> ValidatedResearch:
        """Create sample validated research item."""
        return ValidatedResearch(
            source="pubmed",
            source_id="12345678",
            title="Effects of Lion's Mane on Cognitive Function",
            content="Abstract content with key findings",
            summary="Treatment showed significant improvement.",
            url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            tags=["pubmed", "scientific-research"],
            source_metadata={"pmid": "12345678", "summary": "Treatment showed significant improvement."},
            created_at=datetime.now(timezone.utc),
            compliance_status="PENDING",
            score=0.0,
        )

    @pytest.mark.asyncio
    async def test_validate_sets_compliant_status(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_item: ValidatedResearch,
    ):
        """Should set COMPLIANT status when compliance check passes."""
        validator = PubMedValidator(mock_research_compliance)

        result = await validator.validate([sample_item])

        assert len(result) == 1
        assert result[0].compliance_status == "COMPLIANT"

    @pytest.mark.asyncio
    async def test_validate_pubmed_warning_becomes_compliant(
        self,
        sample_item: ValidatedResearch,
    ):
        """PubMed sources upgrade WARNING to COMPLIANT (inherently citable)."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.WARNING,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = PubMedValidator(research_compliance)

        validated = await validator.validate([sample_item])

        # PubMed is inherently citable scientific literature
        # So WARNING gets upgraded to COMPLIANT
        assert validated[0].compliance_status == "COMPLIANT"

    @pytest.mark.asyncio
    async def test_validate_sets_rejected_downgraded_for_pubmed(
        self,
        sample_item: ValidatedResearch,
    ):
        """PubMed items get REJECTED downgraded to WARNING due to citability."""
        checker = AsyncMock(spec=EUComplianceChecker)
        # PubMed source is always citable, so REJECTED becomes WARNING
        result = ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = PubMedValidator(research_compliance)

        validated = await validator.validate([sample_item])

        # PubMed is always citable, so REJECTED is downgraded to WARNING
        assert validated[0].compliance_status == "WARNING"

    @pytest.mark.asyncio
    async def test_validate_preserves_other_fields(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_item: ValidatedResearch,
    ):
        """Should preserve all other fields during validation."""
        validator = PubMedValidator(mock_research_compliance)

        result = await validator.validate([sample_item])

        assert result[0].source == "pubmed"
        assert result[0].source_id == "12345678"
        assert result[0].title == "Effects of Lion's Mane on Cognitive Function"
        assert result[0].url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"


class TestBatchValidation:
    """Tests for batch validation."""

    @pytest.fixture
    def sample_items(self) -> list[ValidatedResearch]:
        """Create multiple items for batch testing."""
        return [
            ValidatedResearch(
                source="pubmed",
                source_id=str(i),
                title=f"Article {i}",
                content=f"Content {i}",
                summary=f"Summary {i}",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{i}/",
                tags=[],
                source_metadata={"pmid": str(i), "summary": f"Summary {i}"},
                created_at=datetime.now(timezone.utc),
                compliance_status="PENDING",
                score=0.0,
            )
            for i in range(3)
        ]

    @pytest.mark.asyncio
    async def test_validate_multiple_items(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_items: list[ValidatedResearch],
    ):
        """Should validate multiple items."""
        validator = PubMedValidator(mock_research_compliance)

        result = await validator.validate(sample_items)

        assert len(result) == 3
        assert all(r.compliance_status == "COMPLIANT" for r in result)

    @pytest.mark.asyncio
    async def test_validate_batch_method(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_items: list[ValidatedResearch],
    ):
        """Should validate in batches with batch_size parameter."""
        validator = PubMedValidator(mock_research_compliance)

        result = await validator.validate_batch(sample_items, batch_size=2)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_continues_on_failure(
        self,
        sample_items: list[ValidatedResearch],
    ):
        """Should continue processing when compliance check fails."""
        checker = AsyncMock(spec=EUComplianceChecker)
        compliant_result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        checker.check_content.side_effect = [
            Exception("Check failed"),
            compliant_result,
            compliant_result,
        ]

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = PubMedValidator(research_compliance)

        result = await validator.validate(sample_items)

        # First one skipped due to error, others succeed
        assert len(result) == 2
        assert all(r.compliance_status == "COMPLIANT" for r in result)


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def sample_item(self) -> ValidatedResearch:
        """Create sample validated research item."""
        return ValidatedResearch(
            source="pubmed",
            source_id="12345678",
            title="Test Article",
            content="Test content",
            summary="Test summary",
            url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            tags=[],
            source_metadata={"pmid": "12345678", "summary": "Test summary"},
            created_at=datetime.now(timezone.utc),
            compliance_status="PENDING",
            score=0.0,
        )

    @pytest.mark.asyncio
    async def test_handles_compliance_check_failure(
        self,
        sample_item: ValidatedResearch,
    ):
        """Should handle compliance check failures gracefully."""
        checker = AsyncMock(spec=EUComplianceChecker)
        checker.check_content.side_effect = Exception("API error")

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = PubMedValidator(research_compliance)

        result = await validator.validate([sample_item])

        # Item should be skipped on error
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_logs_validation_statistics(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_item: ValidatedResearch,
        caplog,
    ):
        """Should log validation statistics."""
        validator = PubMedValidator(mock_research_compliance)

        import logging
        with caplog.at_level(logging.INFO):
            await validator.validate([sample_item])

        # Should have logged statistics
        assert any("compliant" in record.message.lower() for record in caplog.records)


class TestValidatorError:
    """Tests for ValidatorError exception."""

    def test_error_with_message_only(self):
        """Should create error with message only."""
        error = ValidatorError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.pmid is None

    def test_error_with_pmid(self):
        """Should create error with PMID."""
        error = ValidatorError("Failed to validate", pmid="12345678")

        assert error.message == "Failed to validate"
        assert error.pmid == "12345678"
