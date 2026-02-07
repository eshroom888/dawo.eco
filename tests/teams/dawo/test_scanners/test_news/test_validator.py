"""Tests for news validator."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from teams.dawo.scanners.news.schemas import (
    NewsCategory,
    PriorityLevel,
    CategoryResult,
    PriorityScore,
)
from teams.dawo.scanners.news.validator import NewsValidator, ValidatedResearch
from teams.dawo.research import TransformedResearch, ResearchSource
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


class TestNewsValidator:
    """Tests for NewsValidator."""

    def _make_transformed_research(
        self,
        title: str = "Test Article",
    ) -> TransformedResearch:
        """Helper to create transformed research."""
        return TransformedResearch(
            source=ResearchSource.NEWS,
            title=title,
            content="Test content",
            url="https://example.com/article",
            tags=["news", "general"],
            source_metadata={"source_name": "TestSource"},
            created_at=datetime.now(timezone.utc),
            score=5.0,
        )

    def _make_category_result(self) -> CategoryResult:
        """Helper to create category result."""
        return CategoryResult(
            category=NewsCategory.GENERAL,
            confidence=0.7,
            is_regulatory=False,
            priority_level=PriorityLevel.LOW,
            matched_patterns=[],
            requires_operator_attention=False,
        )

    def _make_priority_score(self) -> PriorityScore:
        """Helper to create priority score."""
        return PriorityScore(
            base_score=2.0,
            final_score=3.0,
            boosters_applied=[],
            requires_attention=False,
        )

    @pytest.mark.asyncio
    async def test_validate_single_item(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Test validating a single item."""
        validator = NewsValidator(mock_research_compliance)
        research = self._make_transformed_research()
        category = self._make_category_result()
        priority = self._make_priority_score()

        result = await validator.validate([(research, category, priority)])

        assert len(result) == 1
        assert result[0].compliance_status == "COMPLIANT"

    @pytest.mark.asyncio
    async def test_validate_multiple_items(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Test validating multiple items."""
        validator = NewsValidator(mock_research_compliance)
        items = [
            (
                self._make_transformed_research(title=f"Article {i}"),
                self._make_category_result(),
                self._make_priority_score(),
            )
            for i in range(3)
        ]

        result = await validator.validate(items)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_validate_sets_compliant_status(
        self,
    ) -> None:
        """Test that compliant status is set correctly."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = NewsValidator(research_compliance)

        research = self._make_transformed_research()
        validated = await validator.validate(
            [(research, self._make_category_result(), self._make_priority_score())]
        )

        assert validated[0].compliance_status == "COMPLIANT"

    @pytest.mark.asyncio
    async def test_validate_sets_warning_status(
        self,
    ) -> None:
        """Test that warning status is set correctly."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.WARNING,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = NewsValidator(research_compliance)

        research = self._make_transformed_research()
        validated = await validator.validate(
            [(research, self._make_category_result(), self._make_priority_score())]
        )

        assert validated[0].compliance_status == "WARNING"

    @pytest.mark.asyncio
    async def test_validate_sets_rejected_status(
        self,
    ) -> None:
        """Test that rejected status is set correctly."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = NewsValidator(research_compliance)

        research = self._make_transformed_research()
        validated = await validator.validate(
            [(research, self._make_category_result(), self._make_priority_score())]
        )

        assert validated[0].compliance_status == "REJECTED"

    @pytest.mark.asyncio
    async def test_validate_preserves_metadata(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Test that validation preserves research metadata."""
        validator = NewsValidator(mock_research_compliance)
        research = TransformedResearch(
            source=ResearchSource.NEWS,
            title="Test",
            content="Content",
            url="https://example.com",
            tags=["tag1"],
            source_metadata={"key": "value"},
            created_at=datetime.now(timezone.utc),
            score=7.5,
        )

        result = await validator.validate(
            [(research, self._make_category_result(), self._make_priority_score())]
        )

        assert result[0].score == 7.5
        assert result[0].source_metadata["key"] == "value"
        assert result[0].tags == ["tag1"]

    @pytest.mark.asyncio
    async def test_validate_calls_compliance_checker(
        self,
        mock_eu_compliance_checker: AsyncMock,
        mock_research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Test that compliance checker is called."""
        validator = NewsValidator(mock_research_compliance)
        research = self._make_transformed_research()

        await validator.validate(
            [(research, self._make_category_result(), self._make_priority_score())]
        )

        mock_eu_compliance_checker.check_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_empty_list(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Test validating empty list."""
        validator = NewsValidator(mock_research_compliance)
        result = await validator.validate([])

        assert result == []

    @pytest.mark.asyncio
    async def test_validate_batch_method(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Test validate_batch method for direct research items."""
        validator = NewsValidator(mock_research_compliance)
        items = [
            self._make_transformed_research(title=f"Article {i}")
            for i in range(3)
        ]

        result = await validator.validate_batch(items)

        assert len(result) == 3
        assert all(r.compliance_status == "COMPLIANT" for r in result)
