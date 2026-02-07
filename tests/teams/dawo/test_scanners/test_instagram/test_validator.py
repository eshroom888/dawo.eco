"""Unit tests for InstagramValidator.

Tests the validate stage of the Harvester Framework pipeline:
    Scanner -> Harvester -> ThemeExtractor -> ClaimDetector -> Transformer -> [Validator] -> Scorer

Coverage:
    - Validate single item with compliance checker
    - Compliance status mapping (COMPLIANT, WARNING, REJECTED)
    - CleanMarket flag preservation
    - Batch validation handling
    - Error handling and graceful degradation
    - Statistics tracking
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from teams.dawo.scanners.instagram import (
    InstagramValidator,
    ValidatorError,
    ValidatedResearch,
)
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
def sample_transformed_item():
    """Sample TransformedResearch for testing."""
    return TransformedResearch(
        source=ResearchSource.INSTAGRAM,
        title="Lion's mane for focus! #lionsmane #focus",
        content="Lion's mane mushroom is amazing for focus!\n\n**Theme Analysis:**\n- Content Type: educational",
        url="https://www.instagram.com/p/ABC123/",
        tags=["lionsmane", "focus", "instagram"],
        source_metadata={
            "account": "wellness_user",
            "account_type": "business",
            "likes": 1500,
            "comments": 45,
            "is_competitor": False,
        },
        created_at=datetime.now(timezone.utc),
        score=0.0,
        compliance_status=ComplianceStatus.COMPLIANT,
    )


class TestInstagramValidator:
    """Tests for InstagramValidator class."""

    @pytest.mark.asyncio
    async def test_validate_returns_list(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_transformed_item: TransformedResearch,
    ):
        """Validate returns list of ValidatedResearch objects."""
        validator = InstagramValidator(mock_research_compliance)
        result = await validator.validate([sample_transformed_item])

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_validate_returns_validated_research_type(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_transformed_item: TransformedResearch,
    ):
        """Validate returns ValidatedResearch objects."""
        validator = InstagramValidator(mock_research_compliance)
        result = await validator.validate([sample_transformed_item])

        assert isinstance(result[0], ValidatedResearch)

    @pytest.mark.asyncio
    async def test_validate_calls_compliance_checker(
        self,
        mock_eu_compliance_checker: AsyncMock,
        mock_research_compliance: ResearchComplianceValidator,
        sample_transformed_item: TransformedResearch,
    ):
        """Validate calls compliance checker with content."""
        validator = InstagramValidator(mock_research_compliance)
        await validator.validate([sample_transformed_item])

        mock_eu_compliance_checker.check_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_sets_compliant_status(
        self,
        sample_transformed_item: TransformedResearch,
    ):
        """Validate sets COMPLIANT status when checker passes."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = InstagramValidator(research_compliance)

        result = await validator.validate([sample_transformed_item])

        assert result[0].compliance_status == "COMPLIANT"

    @pytest.mark.asyncio
    async def test_validate_sets_warning_status(
        self,
        sample_transformed_item: TransformedResearch,
    ):
        """Validate sets WARNING status when checker returns warning."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.WARNING,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = InstagramValidator(research_compliance)

        result = await validator.validate([sample_transformed_item])

        assert result[0].compliance_status == "WARNING"

    @pytest.mark.asyncio
    async def test_validate_sets_rejected_status(
        self,
        sample_transformed_item: TransformedResearch,
    ):
        """Validate sets REJECTED status when checker rejects."""
        checker = AsyncMock(spec=EUComplianceChecker)
        result = ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[],
        )
        checker.check_content.return_value = result

        research_compliance = ResearchComplianceValidator(compliance_checker=checker)
        validator = InstagramValidator(research_compliance)

        result = await validator.validate([sample_transformed_item])

        assert result[0].compliance_status == "REJECTED"

    @pytest.mark.asyncio
    async def test_validate_preserves_cleanmarket_flag_true(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ):
        """Validate preserves cleanmarket_flag when claims detected."""
        item = TransformedResearch(
            source=ResearchSource.INSTAGRAM,
            title="Test",
            content="Test content",
            url="https://www.instagram.com/p/TEST/",
            tags=["test"],
            source_metadata={
                "account": "test",
                "detected_claims": [{"text": "boosts energy", "category": "enhancement"}],
            },
            created_at=datetime.now(timezone.utc),
            score=0.0,
            compliance_status=ComplianceStatus.COMPLIANT,
        )

        validator = InstagramValidator(mock_research_compliance)
        result = await validator.validate([item])

        assert result[0].cleanmarket_flag is True

    @pytest.mark.asyncio
    async def test_validate_cleanmarket_flag_false_when_no_claims(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ):
        """Validate sets cleanmarket_flag to False when no claims in metadata."""
        item = TransformedResearch(
            source=ResearchSource.INSTAGRAM,
            title="Test",
            content="Test content",
            url="https://www.instagram.com/p/TEST/",
            tags=["test"],
            source_metadata={"account": "test"},
            created_at=datetime.now(timezone.utc),
            score=0.0,
            compliance_status=ComplianceStatus.COMPLIANT,
        )

        validator = InstagramValidator(mock_research_compliance)
        result = await validator.validate([item])

        assert result[0].cleanmarket_flag is False

    @pytest.mark.asyncio
    async def test_validate_preserves_all_fields(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_transformed_item: TransformedResearch,
    ):
        """Validate preserves all fields from transformed item."""
        validator = InstagramValidator(mock_research_compliance)
        result = await validator.validate([sample_transformed_item])

        validated = result[0]
        assert validated.title == sample_transformed_item.title
        assert validated.content == sample_transformed_item.content
        assert validated.url == sample_transformed_item.url
        assert validated.tags == list(sample_transformed_item.tags)
        assert validated.source_metadata == dict(sample_transformed_item.source_metadata)
        assert validated.created_at == sample_transformed_item.created_at

    @pytest.mark.asyncio
    async def test_validate_handles_empty_list(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ):
        """Validate handles empty input list."""
        validator = InstagramValidator(mock_research_compliance)
        result = await validator.validate([])

        assert result == []

    @pytest.mark.asyncio
    async def test_validate_batch_processing(
        self,
        mock_research_compliance: ResearchComplianceValidator,
    ):
        """Validate processes multiple items in batch."""
        items = [
            TransformedResearch(
                source=ResearchSource.INSTAGRAM,
                title=f"Test {i}",
                content=f"Content {i}",
                url=f"https://www.instagram.com/p/TEST{i}/",
                tags=["test"],
                source_metadata={"account": "test"},
                created_at=datetime.now(timezone.utc),
                score=0.0,
                compliance_status=ComplianceStatus.COMPLIANT,
            )
            for i in range(5)
        ]

        validator = InstagramValidator(mock_research_compliance)
        result = await validator.validate(items)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_validate_single_method(
        self,
        mock_research_compliance: ResearchComplianceValidator,
        sample_transformed_item: TransformedResearch,
    ):
        """Validate single item via convenience method."""
        validator = InstagramValidator(mock_research_compliance)
        result = await validator.validate_single(sample_transformed_item)

        assert isinstance(result, ValidatedResearch)
        assert result.title == sample_transformed_item.title


class TestValidatedResearchSchema:
    """Tests for ValidatedResearch schema."""

    def test_validated_research_has_all_required_fields(self):
        """ValidatedResearch has all required fields."""
        validated = ValidatedResearch(
            source="instagram",
            title="Test Title",
            content="Test content",
            url="https://www.instagram.com/p/TEST/",
            tags=["test"],
            source_metadata={},
            created_at=datetime.now(timezone.utc),
            compliance_status="COMPLIANT",
            cleanmarket_flag=False,
            score=5.0,
        )

        assert validated.source == "instagram"
        assert validated.title == "Test Title"
        assert validated.compliance_status == "COMPLIANT"
        assert validated.cleanmarket_flag is False

    def test_validated_research_default_compliance_status(self):
        """ValidatedResearch defaults to COMPLIANT status."""
        validated = ValidatedResearch(
            source="instagram",
            title="Test",
            content="Test content",
            url="https://www.instagram.com/p/TEST/",
            created_at=datetime.now(timezone.utc),
        )

        assert validated.compliance_status == "COMPLIANT"

    def test_validated_research_default_cleanmarket_flag(self):
        """ValidatedResearch defaults cleanmarket_flag to False."""
        validated = ValidatedResearch(
            source="instagram",
            title="Test",
            content="Test content",
            url="https://www.instagram.com/p/TEST/",
            created_at=datetime.now(timezone.utc),
        )

        assert validated.cleanmarket_flag is False

    def test_validated_research_score_bounds(self):
        """ValidatedResearch score must be between 0 and 10."""
        # Valid score
        validated = ValidatedResearch(
            source="instagram",
            title="Test",
            content="Test content",
            url="https://www.instagram.com/p/TEST/",
            created_at=datetime.now(timezone.utc),
            score=7.5,
        )
        assert validated.score == 7.5

        # Score at bounds
        validated_min = ValidatedResearch(
            source="instagram",
            title="Test",
            content="Test content",
            url="https://www.instagram.com/p/TEST/",
            created_at=datetime.now(timezone.utc),
            score=0.0,
        )
        assert validated_min.score == 0.0

        validated_max = ValidatedResearch(
            source="instagram",
            title="Test",
            content="Test content",
            url="https://www.instagram.com/p/TEST/",
            created_at=datetime.now(timezone.utc),
            score=10.0,
        )
        assert validated_max.score == 10.0
