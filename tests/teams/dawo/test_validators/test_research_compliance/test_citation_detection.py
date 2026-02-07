"""Tests for scientific citation detection.

Tests cover:
- DOI pattern detection
- PMID pattern detection
- Scientific URL pattern detection
- Citation info aggregation
"""

import pytest

from teams.dawo.validators.research_compliance import (
    ResearchComplianceValidator,
    CitationInfo,
)


class TestDOIDetection:
    """Tests for DOI pattern detection."""

    def test_detects_doi_in_text(self):
        """Test DOI detection in content text."""
        # Arrange
        text = "This study (DOI: 10.1016/j.jff.2024.001) found significant results."

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, None)

        # Assert
        assert result.has_doi is True
        assert "10.1016/j.jff.2024.001" in result.doi

    def test_detects_doi_in_metadata(self):
        """Test DOI detection from source_metadata."""
        # Arrange
        text = "Study abstract without explicit DOI in text."
        metadata = {"doi": "10.1234/example.2024"}

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, metadata)

        # Assert
        assert result.has_doi is True
        assert result.doi == "10.1234/example.2024"

    def test_detects_doi_in_url_format(self):
        """Test DOI detection in doi.org URL format."""
        # Arrange
        text = "Full paper available at https://doi.org/10.1038/s41591-024-01234"

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, None)

        # Assert
        assert result.has_doi is True or result.has_url is True

    def test_no_doi_returns_false(self):
        """Test that content without DOI returns has_doi=False."""
        # Arrange
        text = "Just a regular post about mushrooms without any citations."

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, None)

        # Assert
        assert result.has_doi is False
        assert result.doi is None


class TestPMIDDetection:
    """Tests for PMID pattern detection."""

    def test_detects_pmid_in_metadata(self):
        """Test PMID detection from source_metadata."""
        # Arrange
        text = "PubMed abstract."
        metadata = {"pmid": "12345678"}

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, metadata)

        # Assert
        assert result.has_pmid is True
        assert result.pmid == "12345678"

    def test_detects_pmid_in_text_with_label(self):
        """Test PMID detection when labeled in text."""
        # Arrange
        text = "See PMID: 98765432 for more details."

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, None)

        # Assert
        assert result.has_pmid is True
        assert "98765432" in result.pmid

    def test_no_pmid_returns_false(self):
        """Test that content without PMID returns has_pmid=False."""
        # Arrange
        text = "Regular content without any PubMed references."
        metadata = {}

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, metadata)

        # Assert
        assert result.has_pmid is False


class TestScientificURLDetection:
    """Tests for scientific URL pattern detection."""

    def test_detects_pubmed_url(self):
        """Test PubMed URL detection."""
        # Arrange
        text = "Study link: https://pubmed.ncbi.nlm.nih.gov/12345678/"

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, None)

        # Assert
        assert result.has_url is True
        assert "pubmed" in result.url.lower()

    def test_detects_pmc_url(self):
        """Test PMC (PubMed Central) URL detection."""
        # Arrange
        text = "Full text at https://ncbi.nlm.nih.gov/pmc/articles/PMC1234567/"

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, None)

        # Assert
        assert result.has_url is True

    def test_detects_doi_org_url(self):
        """Test doi.org URL detection."""
        # Arrange
        text = "Access at https://doi.org/10.1016/test"

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, None)

        # Assert
        assert result.has_url is True or result.has_doi is True

    def test_non_scientific_url_returns_false(self):
        """Test that regular URLs don't count as citations."""
        # Arrange
        text = "Check out https://reddit.com/r/science for more."

        # Act
        result = ResearchComplianceValidator._detect_citation_static(text, None)

        # Assert
        assert result.has_url is False


class TestCitationInfoAggregation:
    """Tests for CitationInfo has_citation property."""

    def test_has_citation_true_with_doi(self):
        """Test has_citation is True when DOI present."""
        # Arrange
        info = CitationInfo(
            has_doi=True,
            has_pmid=False,
            has_url=False,
            doi="10.1234/test",
            pmid=None,
            url=None,
        )

        # Assert
        assert info.has_citation is True

    def test_has_citation_true_with_pmid(self):
        """Test has_citation is True when PMID present."""
        # Arrange
        info = CitationInfo(
            has_doi=False,
            has_pmid=True,
            has_url=False,
            doi=None,
            pmid="12345678",
            url=None,
        )

        # Assert
        assert info.has_citation is True

    def test_has_citation_true_with_url(self):
        """Test has_citation is True when scientific URL present."""
        # Arrange
        info = CitationInfo(
            has_doi=False,
            has_pmid=False,
            has_url=True,
            doi=None,
            pmid=None,
            url="pubmed.ncbi.nlm.nih.gov/123",
        )

        # Assert
        assert info.has_citation is True

    def test_has_citation_false_without_any(self):
        """Test has_citation is False when nothing present."""
        # Arrange
        info = CitationInfo(
            has_doi=False,
            has_pmid=False,
            has_url=False,
            doi=None,
            pmid=None,
            url=None,
        )

        # Assert
        assert info.has_citation is False

    def test_has_citation_true_with_multiple(self):
        """Test has_citation is True when multiple citations present."""
        # Arrange
        info = CitationInfo(
            has_doi=True,
            has_pmid=True,
            has_url=True,
            doi="10.1234/test",
            pmid="12345678",
            url="pubmed.ncbi.nlm.nih.gov/12345678",
        )

        # Assert
        assert info.has_citation is True
