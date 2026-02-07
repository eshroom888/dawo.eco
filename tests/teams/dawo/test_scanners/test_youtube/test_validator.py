"""Tests for YouTube Validator.

Tests Task 8: YouTubeValidator implementation that checks EU compliance
for transformed research items before publishing.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from teams.dawo.scanners.youtube.validator import YouTubeValidator
from teams.dawo.scanners.youtube import ValidatedResearch
from teams.dawo.research import TransformedResearch, ResearchSource, ComplianceStatus
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


@pytest.fixture
def sample_transformed_research():
    """Create sample TransformedResearch for testing."""
    return TransformedResearch(
        source=ResearchSource.YOUTUBE,
        title="Lion's Mane Benefits: What Science Actually Says",
        content="Summary: This video explores lion's mane cognitive benefits.",
        url="https://youtube.com/watch?v=abc123xyz",
        tags=["lions_mane", "cognition"],
        source_metadata={
            "channel": "Health Science Channel",
            "views": 15234,
            "video_id": "abc123xyz",
        },
        created_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestYouTubeValidator:
    """Tests for YouTubeValidator class."""

    def test_can_import_youtube_validator(self):
        """Test that YouTubeValidator can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeValidator

        assert YouTubeValidator is not None

    def test_validator_accepts_research_compliance_injection(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ):
        """Test that YouTubeValidator accepts ResearchComplianceValidator via constructor."""
        validator = YouTubeValidator(research_compliance=mock_research_compliance)

        assert validator._compliance is mock_research_compliance


class TestYouTubeValidatorValidate:
    """Tests for YouTubeValidator.validate method."""

    @pytest.mark.asyncio
    async def test_validate_returns_validated_research_list(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_transformed_research: TransformedResearch,
    ):
        """Test validate returns list of ValidatedResearch."""
        validator = YouTubeValidator(research_compliance=mock_research_compliance)

        results = await validator.validate([sample_transformed_research])

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], ValidatedResearch)

    @pytest.mark.asyncio
    async def test_validate_sets_compliant_status(
        self,
        sample_transformed_research: TransformedResearch,
    ):
        """Test validate sets COMPLIANT status when checker passes."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = YouTubeValidator(research_compliance=research_compliance)

        results = await validator.validate([sample_transformed_research])

        assert results[0].compliance_status == ComplianceStatus.COMPLIANT.value

    @pytest.mark.asyncio
    async def test_validate_sets_warning_status(
        self,
        sample_transformed_research: TransformedResearch,
    ):
        """Test validate sets WARNING status for borderline content."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.WARNING,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = YouTubeValidator(research_compliance=research_compliance)

        results = await validator.validate([sample_transformed_research])

        assert results[0].compliance_status == ComplianceStatus.WARNING.value

    @pytest.mark.asyncio
    async def test_validate_sets_rejected_status(
        self,
        sample_transformed_research: TransformedResearch,
    ):
        """Test validate sets REJECTED status for prohibited claims."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = YouTubeValidator(research_compliance=research_compliance)

        results = await validator.validate([sample_transformed_research])

        assert results[0].compliance_status == ComplianceStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_validate_preserves_research_fields(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_transformed_research: TransformedResearch,
    ):
        """Test validate preserves all research fields."""
        validator = YouTubeValidator(research_compliance=mock_research_compliance)

        results = await validator.validate([sample_transformed_research])

        result = results[0]
        assert result.title == sample_transformed_research.title
        assert result.content == sample_transformed_research.content
        assert result.url == sample_transformed_research.url
        assert result.tags == list(sample_transformed_research.tags)

    @pytest.mark.asyncio
    async def test_validate_calls_compliance_checker(
        self,
        mock_eu_compliance_checker: AsyncMock,
        mock_research_compliance: ResearchComplianceValidator,
        sample_transformed_research: TransformedResearch,
    ):
        """Test validate calls compliance checker for each item."""
        validator = YouTubeValidator(research_compliance=mock_research_compliance)

        await validator.validate([sample_transformed_research])

        mock_eu_compliance_checker.check_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_handles_empty_list(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ):
        """Test validate handles empty input list."""
        validator = YouTubeValidator(research_compliance=mock_research_compliance)

        results = await validator.validate([])

        assert results == []

    @pytest.mark.asyncio
    async def test_validate_continues_on_individual_failures(
        self,
        sample_transformed_research: TransformedResearch,
    ):
        """Test validate continues processing after individual item failure."""
        # Create second item
        second_item = TransformedResearch(
            source=ResearchSource.YOUTUBE,
            title="Second Video",
            content="Some content",
            url="https://youtube.com/watch?v=def456",
            created_at=datetime.now(timezone.utc),
        )

        checker = AsyncMock(spec=EUComplianceChecker)
        compliant_result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        # First call fails, second succeeds
        checker.check_content.side_effect = [
            Exception("Check failed"),
            compliant_result,
        ]

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = YouTubeValidator(research_compliance=research_compliance)

        results = await validator.validate([sample_transformed_research, second_item])

        # Should have one result (the second one that succeeded)
        assert len(results) == 1
        assert results[0].title == "Second Video"


class TestValidatorError:
    """Tests for ValidatorError exception."""

    def test_can_import_validator_error(self):
        """Test that ValidatorError can be imported."""
        from teams.dawo.scanners.youtube import ValidatorError

        assert ValidatorError is not None

    def test_validator_error_message(self):
        """Test ValidatorError stores message."""
        from teams.dawo.scanners.youtube.validator import ValidatorError

        error = ValidatorError("Compliance check failed")

        assert error.message == "Compliance check failed"
