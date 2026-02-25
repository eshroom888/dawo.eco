"""Tests for LeadTransformer.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner
"""

import pytest

from teams.dawo.leads.scanner.transformer import LeadTransformer
from teams.dawo.leads.scanner.config import LeadScannerConfig
from teams.dawo.leads.scanner.schemas import HarvestedLead, HarvestedContact


class TestLeadTransformer:
    """Tests for LeadTransformer service."""

    @pytest.fixture
    def transformer(
        self,
        scanner_config: LeadScannerConfig,
    ) -> LeadTransformer:
        """Create transformer with config."""
        return LeadTransformer(config=scanner_config)

    def test_transform_creates_lead_from_harvested(
        self,
        transformer: LeadTransformer,
        sample_harvested_lead: HarvestedLead,
    ) -> None:
        """Test that transform creates TransformedLead."""
        result = transformer.transform([sample_harvested_lead])

        assert len(result) == 1
        lead = result[0]
        assert lead.email is not None
        assert lead.company is not None
        assert lead.source == "cold_research"
        assert lead.status == "new"

    def test_transform_selects_primary_contact(
        self,
        transformer: LeadTransformer,
        sample_harvested_lead: HarvestedLead,
    ) -> None:
        """Test that transform uses primary (highest confidence) contact."""
        result = transformer.transform([sample_harvested_lead])

        lead = result[0]
        # CEO has highest confidence in sample data
        assert lead.job_title == "CEO"
        assert "john" in lead.email.lower()

    def test_transform_normalizes_email(
        self,
        transformer: LeadTransformer,
    ) -> None:
        """Test that email is lowercased and stripped."""
        harvested = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[
                HarvestedContact(
                    email="  TEST@EXAMPLE.COM  ",
                    first_name="Test",
                    last_name="User",
                    confidence=0.9,
                ),
            ],
        )

        result = transformer.transform([harvested])

        assert result[0].email == "test@example.com"

    def test_transform_normalizes_names(
        self,
        transformer: LeadTransformer,
    ) -> None:
        """Test that names are title-cased."""
        harvested = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[
                HarvestedContact(
                    email="test@example.com",
                    first_name="john",
                    last_name="DOE",
                    confidence=0.9,
                ),
            ],
        )

        result = transformer.transform([harvested])

        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"

    def test_transform_extracts_name_from_email(
        self,
        transformer: LeadTransformer,
    ) -> None:
        """Test that names are extracted from email when missing."""
        harvested = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[
                HarvestedContact(
                    email="john.doe@example.com",
                    first_name=None,
                    last_name=None,
                    confidence=0.9,
                ),
            ],
        )

        result = transformer.transform([harvested])

        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"

    def test_transform_handles_single_name_email(
        self,
        transformer: LeadTransformer,
    ) -> None:
        """Test name extraction from single-word email prefix."""
        harvested = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[
                HarvestedContact(
                    email="info@example.com",
                    first_name=None,
                    last_name=None,
                    confidence=0.9,
                ),
            ],
        )

        result = transformer.transform([harvested])

        assert result[0].first_name == "Info"
        assert result[0].last_name == "Unknown"

    def test_transform_builds_website_url(
        self,
        transformer: LeadTransformer,
        sample_harvested_lead: HarvestedLead,
    ) -> None:
        """Test that website URL is built from domain."""
        result = transformer.transform([sample_harvested_lead])

        assert result[0].website_url == "https://example-health.no"

    def test_transform_includes_enrichment_data(
        self,
        transformer: LeadTransformer,
        sample_harvested_lead: HarvestedLead,
    ) -> None:
        """Test that enrichment_data is populated."""
        result = transformer.transform([sample_harvested_lead])

        enrichment = result[0].enrichment_data
        assert enrichment["source"] == "hunter.io"
        assert "discovered_at" in enrichment
        assert "enriched_at" in enrichment
        assert "confidence" in enrichment
        assert "social_profiles" in enrichment

    def test_transform_filters_invalid_leads(
        self,
        transformer: LeadTransformer,
    ) -> None:
        """Test that leads missing required fields are filtered."""
        # Lead with no email
        harvested = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[
                HarvestedContact(
                    email="",  # Invalid
                    first_name="Test",
                    last_name="User",
                    confidence=0.9,
                ),
            ],
        )

        result = transformer.transform([harvested])

        assert len(result) == 0

    def test_transform_filters_invalid_email_format(
        self,
        transformer: LeadTransformer,
    ) -> None:
        """Test that leads with invalid email format are filtered."""
        harvested = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[
                HarvestedContact(
                    email="not-an-email",  # No @ sign
                    first_name="Test",
                    last_name="User",
                    confidence=0.9,
                ),
            ],
        )

        result = transformer.transform([harvested])

        assert len(result) == 0

    def test_transform_skips_leads_without_contacts(
        self,
        transformer: LeadTransformer,
    ) -> None:
        """Test that leads without contacts are skipped."""
        harvested = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[],
        )

        result = transformer.transform([harvested])

        assert len(result) == 0

    def test_transform_continues_on_error(
        self,
        transformer: LeadTransformer,
        sample_harvested_leads: list[HarvestedLead],
    ) -> None:
        """Test that transform continues processing on individual errors."""
        # Add an invalid lead
        invalid_lead = HarvestedLead(
            domain="invalid.com",
            company_name="Invalid",
            contacts=[
                HarvestedContact(email="", confidence=0.9),  # Invalid email
            ],
        )
        leads_with_invalid = [invalid_lead] + sample_harvested_leads

        result = transformer.transform(leads_with_invalid)

        # Should still transform valid leads
        assert len(result) == len(sample_harvested_leads)

    def test_normalize_company_name(
        self,
        transformer: LeadTransformer,
    ) -> None:
        """Test company name normalization."""
        assert transformer._normalize_company_name("  Example Inc  ") == "Example Inc"
        assert transformer._normalize_company_name("Example  Inc") == "Example Inc"
        assert transformer._normalize_company_name("") == "Unknown Company"
