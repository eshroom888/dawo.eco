"""Tests for ResearchComplianceValidator core functionality.

Tests cover:
- Single item validation
- Compliance status determination
- Integration with EU Compliance Checker
- Source-specific rules
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from teams.dawo.research import TransformedResearch, ResearchSource, ComplianceStatus
from teams.dawo.validators.eu_compliance import (
    ContentComplianceCheck,
    ComplianceResult,
    OverallStatus,
    ComplianceStatus as PhraseStatus,
)
from teams.dawo.validators.research_compliance import (
    ResearchComplianceValidator,
    ComplianceValidationResult,
    CitationInfo,
)


class TestResearchComplianceValidator:
    """Tests for ResearchComplianceValidator class."""

    @pytest.mark.asyncio
    async def test_validate_clean_research_returns_compliant(
        self,
        mock_eu_compliance_checker: AsyncMock,
        sample_reddit_research: TransformedResearch,
    ):
        """Test that clean research without claims returns COMPLIANT."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        result = await validator.validate(sample_reddit_research)

        # Assert
        assert result.compliance_status == ComplianceStatus.COMPLIANT
        assert mock_eu_compliance_checker.check_content.called

    @pytest.mark.asyncio
    async def test_validate_research_with_prohibited_claims_returns_rejected(
        self,
        mock_checker_returns_rejected: AsyncMock,
        research_with_prohibited_claims: TransformedResearch,
    ):
        """Test that research with prohibited claims returns REJECTED."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_checker_returns_rejected
        )

        # Act
        result = await validator.validate(research_with_prohibited_claims)

        # Assert
        assert result.compliance_status == ComplianceStatus.REJECTED
        assert len(result.flagged_phrases) > 0
        assert "prohibited" in result.compliance_notes.lower()

    @pytest.mark.asyncio
    async def test_validate_research_with_borderline_claims_returns_warning(
        self,
        mock_checker_returns_warning: AsyncMock,
        research_with_borderline_claims: TransformedResearch,
    ):
        """Test that research with borderline claims returns WARNING."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_checker_returns_warning
        )

        # Act
        result = await validator.validate(research_with_borderline_claims)

        # Assert
        assert result.compliance_status == ComplianceStatus.WARNING
        assert len(result.flagged_phrases) > 0

    @pytest.mark.asyncio
    async def test_validate_pubmed_defaults_to_compliant_without_prohibited(
        self,
        mock_eu_compliance_checker: AsyncMock,
        sample_pubmed_research: TransformedResearch,
    ):
        """Test that PubMed sources default to COMPLIANT when no prohibited claims."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        result = await validator.validate(sample_pubmed_research)

        # Assert
        assert result.compliance_status == ComplianceStatus.COMPLIANT
        assert result.has_scientific_citation is True
        assert "peer-reviewed" in result.compliance_notes.lower() or "pubmed" in result.source.lower()


class TestComplianceStatusDetermination:
    """Tests for compliance status determination logic."""

    @pytest.mark.asyncio
    async def test_rejected_with_citation_becomes_warning(
        self,
        mock_checker_returns_rejected: AsyncMock,
        research_with_doi_and_claims: TransformedResearch,
    ):
        """Test that REJECTED status with citation downgrades to WARNING."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_checker_returns_rejected
        )

        # Act
        result = await validator.validate(research_with_doi_and_claims)

        # Assert
        # Has DOI in content, so prohibited claim should become WARNING (can cite, not claim)
        assert result.compliance_status == ComplianceStatus.WARNING
        assert result.has_scientific_citation is True
        assert "cite" in result.compliance_notes.lower()

    @pytest.mark.asyncio
    async def test_pubmed_with_prohibited_claims_returns_warning(
        self,
        mock_checker_returns_rejected: AsyncMock,
    ):
        """Test that PubMed with prohibited claims returns WARNING, not REJECTED."""
        # Arrange
        pubmed_item = TransformedResearch(
            source=ResearchSource.PUBMED,
            title="Lion's mane treats cognitive impairment",
            content="This study found that lion's mane treats cognitive impairment in elderly patients.",
            url="https://pubmed.ncbi.nlm.nih.gov/99999999/",
            tags=["lions_mane"],
            source_metadata={"pmid": "99999999", "doi": "10.9999/test"},
            score=8.0,
            created_at=datetime.now(timezone.utc),
        )

        validator = ResearchComplianceValidator(
            compliance_checker=mock_checker_returns_rejected
        )

        # Act
        result = await validator.validate(pubmed_item)

        # Assert
        # PubMed is inherently citable, so REJECTED becomes WARNING
        assert result.compliance_status == ComplianceStatus.WARNING
        assert result.has_scientific_citation is True


class TestComplianceNotes:
    """Tests for compliance notes generation."""

    @pytest.mark.asyncio
    async def test_compliant_notes_indicate_passed(
        self,
        mock_eu_compliance_checker: AsyncMock,
        sample_reddit_research: TransformedResearch,
    ):
        """Test that COMPLIANT status generates appropriate notes."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        result = await validator.validate(sample_reddit_research)

        # Assert
        assert "passed" in result.compliance_notes.lower()

    @pytest.mark.asyncio
    async def test_warning_notes_explain_flagged_content(
        self,
        mock_checker_returns_warning: AsyncMock,
        research_with_borderline_claims: TransformedResearch,
    ):
        """Test that WARNING status explains flagged phrases."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_checker_returns_warning
        )

        # Act
        result = await validator.validate(research_with_borderline_claims)

        # Assert
        assert "flagged" in result.compliance_notes.lower()

    @pytest.mark.asyncio
    async def test_rejected_notes_indicate_prohibited(
        self,
        mock_checker_returns_rejected: AsyncMock,
        research_with_prohibited_claims: TransformedResearch,
    ):
        """Test that REJECTED status indicates prohibited content."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_checker_returns_rejected
        )

        # Act
        result = await validator.validate(research_with_prohibited_claims)

        # Assert
        assert "prohibited" in result.compliance_notes.lower()
        assert "marketing" in result.compliance_notes.lower() or "cannot" in result.compliance_notes.lower()


class TestSourceSpecificRules:
    """Tests for source-specific validation rules."""

    @pytest.mark.asyncio
    async def test_pubmed_source_marked_as_peer_reviewed(
        self,
        mock_eu_compliance_checker: AsyncMock,
        sample_pubmed_research: TransformedResearch,
    ):
        """Test that PubMed sources are identified as peer-reviewed."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        result = await validator.validate(sample_pubmed_research)

        # Assert
        assert "peer-reviewed" in result.compliance_notes.lower() or "scientific" in result.compliance_notes.lower()

    @pytest.mark.asyncio
    async def test_reddit_without_citation_uses_stricter_rules(
        self,
        mock_checker_returns_rejected: AsyncMock,
        research_with_prohibited_claims: TransformedResearch,
    ):
        """Test that Reddit without citation gets REJECTED for prohibited claims."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_checker_returns_rejected
        )

        # Act
        result = await validator.validate(research_with_prohibited_claims)

        # Assert
        # No citation, so prohibited claim stays REJECTED
        assert result.compliance_status == ComplianceStatus.REJECTED
        assert result.has_scientific_citation is False


class TestMalformedInput:
    """Tests for handling malformed or edge-case inputs."""

    @pytest.mark.asyncio
    async def test_empty_content_still_validates(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that items with minimal content still validate."""
        # Arrange
        minimal_item = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="Short post",
            content="x",  # Minimal content
            url="https://reddit.com/r/test/1",
            tags=[],
            source_metadata={},
            score=1.0,
            created_at=datetime.now(timezone.utc),
        )

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        result = await validator.validate(minimal_item)

        # Assert
        assert result is not None
        assert result.compliance_status == ComplianceStatus.COMPLIANT

    @pytest.mark.asyncio
    async def test_missing_source_metadata_handled(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that missing source_metadata doesn't cause errors."""
        # Arrange
        item = TransformedResearch(
            source=ResearchSource.YOUTUBE,
            title="Video about mushrooms",
            content="This video discusses functional mushrooms.",
            url="https://youtube.com/watch?v=test123",
            tags=["mushrooms"],
            source_metadata={},  # Empty metadata
            score=5.0,
            created_at=datetime.now(timezone.utc),
        )

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        result = await validator.validate(item)

        # Assert
        assert result is not None
        assert result.compliance_status == ComplianceStatus.COMPLIANT

    @pytest.mark.asyncio
    async def test_none_source_metadata_handled(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test handling when source_metadata fields are None."""
        # Arrange
        item = TransformedResearch(
            source=ResearchSource.NEWS,
            title="News article",
            content="Article about health supplements.",
            url="https://news.example.com/article",
            tags=[],
            source_metadata={"key_findings": None},  # None values
            score=4.0,
            created_at=datetime.now(timezone.utc),
        )

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        result = await validator.validate(item)

        # Assert
        assert result is not None
