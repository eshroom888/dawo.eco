"""Tests for YouTube Validator.

Tests Task 8: YouTubeValidator implementation that checks EU compliance
for transformed research items before publishing.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


class TestYouTubeValidator:
    """Tests for YouTubeValidator class."""

    def test_can_import_youtube_validator(self):
        """Test that YouTubeValidator can be imported from module."""
        from teams.dawo.scanners.youtube import YouTubeValidator

        assert YouTubeValidator is not None

    def test_validator_accepts_compliance_checker_injection(self):
        """Test that YouTubeValidator accepts EUComplianceChecker via constructor."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator

        compliance_checker = MagicMock()

        validator = YouTubeValidator(compliance_checker=compliance_checker)

        assert validator._checker is compliance_checker


class TestYouTubeValidatorValidate:
    """Tests for YouTubeValidator.validate method."""

    @pytest.fixture
    def sample_transformed_research(self):
        """Create sample TransformedResearch for testing."""
        from teams.dawo.research import TransformedResearch, ResearchSource

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

    @pytest.fixture
    def mock_compliant_result(self):
        """Create mock compliant result from checker."""
        from teams.dawo.validators.eu_compliance import OverallStatus

        result = MagicMock()
        result.overall_status = OverallStatus.COMPLIANT
        return result

    @pytest.fixture
    def mock_warning_result(self):
        """Create mock warning result from checker."""
        from teams.dawo.validators.eu_compliance import OverallStatus

        result = MagicMock()
        result.overall_status = OverallStatus.WARNING
        return result

    @pytest.fixture
    def mock_rejected_result(self):
        """Create mock rejected result from checker."""
        from teams.dawo.validators.eu_compliance import OverallStatus

        result = MagicMock()
        result.overall_status = OverallStatus.REJECTED
        return result

    @pytest.mark.asyncio
    async def test_validate_returns_validated_research_list(
        self, sample_transformed_research, mock_compliant_result
    ):
        """Test validate returns list of ValidatedResearch."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator
        from teams.dawo.scanners.youtube import ValidatedResearch

        compliance_checker = AsyncMock()
        compliance_checker.check_content = AsyncMock(return_value=mock_compliant_result)

        validator = YouTubeValidator(compliance_checker=compliance_checker)

        results = await validator.validate([sample_transformed_research])

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], ValidatedResearch)

    @pytest.mark.asyncio
    async def test_validate_sets_compliant_status(
        self, sample_transformed_research, mock_compliant_result
    ):
        """Test validate sets COMPLIANT status when checker passes."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator
        from teams.dawo.research import ComplianceStatus

        compliance_checker = AsyncMock()
        compliance_checker.check_content = AsyncMock(return_value=mock_compliant_result)

        validator = YouTubeValidator(compliance_checker=compliance_checker)

        results = await validator.validate([sample_transformed_research])

        assert results[0].compliance_status == ComplianceStatus.COMPLIANT.value

    @pytest.mark.asyncio
    async def test_validate_sets_warning_status(
        self, sample_transformed_research, mock_warning_result
    ):
        """Test validate sets WARNING status for borderline content."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator
        from teams.dawo.research import ComplianceStatus

        compliance_checker = AsyncMock()
        compliance_checker.check_content = AsyncMock(return_value=mock_warning_result)

        validator = YouTubeValidator(compliance_checker=compliance_checker)

        results = await validator.validate([sample_transformed_research])

        assert results[0].compliance_status == ComplianceStatus.WARNING.value

    @pytest.mark.asyncio
    async def test_validate_sets_rejected_status(
        self, sample_transformed_research, mock_rejected_result
    ):
        """Test validate sets REJECTED status for prohibited claims."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator
        from teams.dawo.research import ComplianceStatus

        compliance_checker = AsyncMock()
        compliance_checker.check_content = AsyncMock(return_value=mock_rejected_result)

        validator = YouTubeValidator(compliance_checker=compliance_checker)

        results = await validator.validate([sample_transformed_research])

        assert results[0].compliance_status == ComplianceStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_validate_preserves_research_fields(
        self, sample_transformed_research, mock_compliant_result
    ):
        """Test validate preserves all research fields."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator

        compliance_checker = AsyncMock()
        compliance_checker.check_content = AsyncMock(return_value=mock_compliant_result)

        validator = YouTubeValidator(compliance_checker=compliance_checker)

        results = await validator.validate([sample_transformed_research])

        result = results[0]
        assert result.title == sample_transformed_research.title
        assert result.content == sample_transformed_research.content
        assert result.url == sample_transformed_research.url
        assert result.tags == sample_transformed_research.tags

    @pytest.mark.asyncio
    async def test_validate_checks_title_and_content(
        self, sample_transformed_research, mock_compliant_result
    ):
        """Test validate checks both title and content for compliance."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator

        compliance_checker = AsyncMock()
        compliance_checker.check_content = AsyncMock(return_value=mock_compliant_result)

        validator = YouTubeValidator(compliance_checker=compliance_checker)

        await validator.validate([sample_transformed_research])

        # Verify check_content was called with title + content
        call_args = compliance_checker.check_content.call_args[0][0]
        assert sample_transformed_research.title in call_args
        assert sample_transformed_research.content in call_args

    @pytest.mark.asyncio
    async def test_validate_handles_empty_list(self):
        """Test validate handles empty input list."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator

        compliance_checker = AsyncMock()
        validator = YouTubeValidator(compliance_checker=compliance_checker)

        results = await validator.validate([])

        assert results == []

    @pytest.mark.asyncio
    async def test_validate_continues_on_individual_failures(
        self, sample_transformed_research, mock_compliant_result
    ):
        """Test validate continues processing after individual item failure."""
        from teams.dawo.scanners.youtube.validator import YouTubeValidator
        from teams.dawo.research import TransformedResearch, ResearchSource

        # Create second item
        second_item = TransformedResearch(
            source=ResearchSource.YOUTUBE,
            title="Second Video",
            content="Some content",
            url="https://youtube.com/watch?v=def456",
            created_at=datetime.now(timezone.utc),
        )

        compliance_checker = AsyncMock()
        # First call fails, second succeeds
        compliance_checker.check_content = AsyncMock(
            side_effect=[Exception("Check failed"), mock_compliant_result]
        )

        validator = YouTubeValidator(compliance_checker=compliance_checker)

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
