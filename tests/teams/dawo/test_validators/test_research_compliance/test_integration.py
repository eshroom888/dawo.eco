"""Integration tests for Research Compliance Validator.

Tests cover:
- Full validation pipeline with EU Compliance Checker
- Scanner integration patterns
- Research Pool entry with compliance status
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.research import (
    TransformedResearch,
    ResearchSource,
    ComplianceStatus,
)
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ContentComplianceCheck,
    ComplianceResult,
    OverallStatus,
    ComplianceStatus as PhraseStatus,
)
from teams.dawo.validators.research_compliance import (
    ResearchComplianceValidator,
    ValidatedResearch,
)


class TestFullValidationPipeline:
    """Tests for complete validation pipeline."""

    @pytest.mark.asyncio
    async def test_research_to_compliance_validation_to_pool_entry(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test full pipeline: research → compliance validation → pool entry."""
        # Arrange
        research_item = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="User experience with Lion's Mane",
            content="I've been taking lion's mane for a month. Noticed improved focus.",
            url="https://reddit.com/r/Nootropics/comments/test123",
            tags=["lions_mane", "focus"],
            source_metadata={"subreddit": "Nootropics", "upvotes": 100},
            score=6.5,
            created_at=datetime.now(timezone.utc),
        )

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        result = await validator.validate(research_item)

        # Assert
        assert result is not None
        assert result.compliance_status == ComplianceStatus.COMPLIANT
        assert result.source == "reddit"
        assert result.title == research_item.title
        assert result.content == research_item.content
        assert result.url == research_item.url
        assert result.tags == list(research_item.tags)
        assert result.score == research_item.score

    @pytest.mark.asyncio
    async def test_rejected_items_still_enter_pool_with_warning_flag(
        self,
        mock_checker_returns_rejected: AsyncMock,
    ):
        """Test that REJECTED items still enter pool with compliance warning."""
        # Arrange
        research_item = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="Lion's mane cures brain fog!",
            content="This cures brain fog completely! Best treatment ever.",
            url="https://reddit.com/r/test/abc",
            tags=["lions_mane"],
            source_metadata={},
            score=5.0,
            created_at=datetime.now(timezone.utc),
        )

        validator = ResearchComplianceValidator(
            compliance_checker=mock_checker_returns_rejected
        )

        # Act
        result = await validator.validate(research_item)

        # Assert
        # Item should be validated (enters pool) but marked REJECTED
        assert result is not None
        assert result.compliance_status == ComplianceStatus.REJECTED
        assert "prohibited" in result.compliance_notes.lower()
        assert len(result.flagged_phrases) > 0


class TestScannerIntegration:
    """Tests for scanner validator integration patterns."""

    @pytest.mark.asyncio
    async def test_scanner_validator_uses_research_compliance(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that scanner validators can use ResearchComplianceValidator."""
        # Arrange
        from teams.dawo.scanners.reddit.validator import RedditValidator

        research_compliance = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # This is how Team Builder would inject the dependency
        reddit_validator = RedditValidator(research_compliance=research_compliance)

        items = [
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title="Test post",
                content="Test content about mushrooms",
                url="https://reddit.com/r/test/1",
                tags=["test"],
                source_metadata={},
                score=5.0,
                created_at=datetime.now(timezone.utc),
            )
        ]

        # Act
        results = await reddit_validator.validate(items)

        # Assert
        assert len(results) == 1
        assert results[0].compliance_status == ComplianceStatus.COMPLIANT.value


class TestComplianceStatusVisibility:
    """Tests for compliance status visibility in Research Pool."""

    @pytest.mark.asyncio
    async def test_compliance_status_set_on_validated_research(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that compliance_status is properly set on validated output."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        item = TransformedResearch(
            source=ResearchSource.YOUTUBE,
            title="Video about mushrooms",
            content="This video discusses functional mushrooms.",
            url="https://youtube.com/watch?v=test",
            tags=["mushrooms"],
            source_metadata={},
            score=7.0,
            created_at=datetime.now(timezone.utc),
        )

        # Act
        result = await validator.validate(item)

        # Assert
        assert hasattr(result, "compliance_status")
        assert result.compliance_status in [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.WARNING,
            ComplianceStatus.REJECTED,
        ]

    @pytest.mark.asyncio
    async def test_has_scientific_citation_flag_visible(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that has_scientific_citation flag is set correctly."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Item with DOI
        item_with_citation = TransformedResearch(
            source=ResearchSource.NEWS,
            title="Study finds benefits",
            content="According to study 10.1016/j.example.2024, researchers found...",
            url="https://news.example.com/study",
            tags=["research"],
            source_metadata={},
            score=8.0,
            created_at=datetime.now(timezone.utc),
        )

        # Item without citation
        item_without_citation = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="My opinion",
            content="I think mushrooms are great.",
            url="https://reddit.com/r/test/2",
            tags=[],
            source_metadata={},
            score=3.0,
            created_at=datetime.now(timezone.utc),
        )

        # Act
        result_with = await validator.validate(item_with_citation)
        result_without = await validator.validate(item_without_citation)

        # Assert
        assert result_with.has_scientific_citation is True
        assert result_without.has_scientific_citation is False


class TestTeamBuilderIntegration:
    """Tests for Team Builder dependency injection patterns."""

    def test_research_compliance_validator_accepts_eu_checker(self):
        """Test that ResearchComplianceValidator accepts EU Compliance Checker."""
        # Arrange
        mock_checker = MagicMock(spec=EUComplianceChecker)

        # Act
        validator = ResearchComplianceValidator(compliance_checker=mock_checker)

        # Assert
        assert validator._compliance_checker is mock_checker

    @pytest.mark.asyncio
    async def test_validator_chain_eu_checker_to_research_compliance(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test the validator chain: EU Checker → Research Compliance → Scanner Validator."""
        # This simulates how Team Builder would compose the validators

        # Step 1: Create ResearchComplianceValidator with EU Checker
        research_compliance = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Step 2: Create scanner validator with ResearchComplianceValidator
        from teams.dawo.scanners.youtube.validator import YouTubeValidator
        youtube_validator = YouTubeValidator(research_compliance=research_compliance)

        # Step 3: Validate items through the chain
        items = [
            TransformedResearch(
                source=ResearchSource.YOUTUBE,
                title="Test video",
                content="Test content",
                url="https://youtube.com/watch?v=test",
                tags=[],
                source_metadata={},
                score=5.0,
                created_at=datetime.now(timezone.utc),
            )
        ]

        results = await youtube_validator.validate(items)

        # Assert
        assert len(results) == 1
        # EU Compliance Checker should have been called
        assert mock_eu_compliance_checker.check_content.called
