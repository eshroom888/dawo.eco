"""Tests for Reddit Validator.

Tests:
    - Validator initialization
    - Compliance checking via ResearchComplianceValidator
    - Status mapping
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.reddit.validator import RedditValidator
from teams.dawo.scanners.reddit.schemas import ValidatedResearch
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

    # Default to COMPLIANT
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
def transformed_item() -> TransformedResearch:
    """Sample TransformedResearch for testing."""
    return TransformedResearch(
        source=ResearchSource.REDDIT,
        title="Test research item",
        content="This is test content about mushroom supplements",
        url="https://reddit.com/r/Test/comments/test123/",
        tags=["lions_mane", "cognitive"],
        source_metadata={"subreddit": "Test", "author": "user"},
        created_at=datetime.now(timezone.utc),
    )


class TestRedditValidatorInit:
    """Tests for RedditValidator initialization."""

    def test_validator_creation(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Validator should be created with injected ResearchComplianceValidator."""
        validator = RedditValidator(mock_research_compliance)
        assert validator._compliance == mock_research_compliance


class TestRedditValidatorValidate:
    """Tests for validate() method."""

    @pytest.mark.asyncio
    async def test_validate_returns_list(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        transformed_item: TransformedResearch,
    ) -> None:
        """Validate should return list of ValidatedResearch."""
        validator = RedditValidator(mock_research_compliance)
        result = await validator.validate([transformed_item])

        assert len(result) == 1
        assert isinstance(result[0], ValidatedResearch)

    @pytest.mark.asyncio
    async def test_validate_empty_list(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Validate with empty list should return empty list."""
        validator = RedditValidator(mock_research_compliance)
        result = await validator.validate([])

        assert result == []

    @pytest.mark.asyncio
    async def test_validate_calls_checker(
        self,
        mock_eu_compliance_checker: AsyncMock,
        mock_research_compliance: ResearchComplianceValidator,
        transformed_item: TransformedResearch,
    ) -> None:
        """Validator should call compliance checker for each item."""
        validator = RedditValidator(mock_research_compliance)
        await validator.validate([transformed_item])

        mock_eu_compliance_checker.check_content.assert_called_once()


class TestRedditValidatorStatus:
    """Tests for compliance status mapping."""

    @pytest.mark.asyncio
    async def test_compliant_status(
        self,
        transformed_item: TransformedResearch,
    ) -> None:
        """COMPLIANT checker result should set COMPLIANT status."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = RedditValidator(research_compliance)
        validated = await validator.validate([transformed_item])

        assert validated[0].compliance_status == ComplianceStatus.COMPLIANT.value

    @pytest.mark.asyncio
    async def test_warning_status(
        self,
        transformed_item: TransformedResearch,
    ) -> None:
        """WARNING checker result should set WARNING status."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.WARNING,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = RedditValidator(research_compliance)
        validated = await validator.validate([transformed_item])

        assert validated[0].compliance_status == ComplianceStatus.WARNING.value

    @pytest.mark.asyncio
    async def test_rejected_status(
        self,
        transformed_item: TransformedResearch,
    ) -> None:
        """REJECTED checker result should set REJECTED status."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = RedditValidator(research_compliance)
        validated = await validator.validate([transformed_item])

        assert validated[0].compliance_status == ComplianceStatus.REJECTED.value


class TestRedditValidatorErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_checker_error_skips_item(
        self,
        transformed_item: TransformedResearch,
    ) -> None:
        """Checker error should skip item and continue."""
        checker = AsyncMock(spec=EUComplianceChecker)
        checker.check_content.side_effect = Exception("Checker error")

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = RedditValidator(research_compliance)
        result = await validator.validate([transformed_item])

        # Item should be skipped on error
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_partial_failure_continues(
        self,
        transformed_item: TransformedResearch,
    ) -> None:
        """Failure on one item should not stop others."""
        checker = AsyncMock(spec=EUComplianceChecker)

        # First call fails, second succeeds
        compliant_result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        checker.check_content.side_effect = [
            Exception("Error"),
            compliant_result,
        ]

        items = [transformed_item, transformed_item]
        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = RedditValidator(research_compliance)
        result = await validator.validate(items)

        # Should have one successful validation
        assert len(result) == 1
        assert result[0].compliance_status == ComplianceStatus.COMPLIANT.value


class TestRedditValidatorFieldPreservation:
    """Tests that all fields are preserved through validation."""

    @pytest.mark.asyncio
    async def test_preserves_all_fields(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        transformed_item: TransformedResearch,
    ) -> None:
        """All fields from TransformedResearch should be in ValidatedResearch."""
        validator = RedditValidator(mock_research_compliance)
        result = await validator.validate([transformed_item])

        validated = result[0]
        assert validated.source == transformed_item.source.value
        assert validated.title == transformed_item.title
        assert validated.content == transformed_item.content
        assert validated.url == transformed_item.url
        assert validated.tags == list(transformed_item.tags)
        assert validated.source_metadata == dict(transformed_item.source_metadata)
        assert validated.created_at == transformed_item.created_at
