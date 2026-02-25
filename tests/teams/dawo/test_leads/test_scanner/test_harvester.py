"""Tests for LeadHarvester.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner
"""

import pytest
from unittest.mock import AsyncMock

from teams.dawo.leads.scanner.harvester import LeadHarvester
from teams.dawo.leads.scanner.config import LeadScannerConfig
from teams.dawo.leads.scanner.schemas import RawLead
from teams.dawo.leads.scanner.tools import HunterAPIError


class TestLeadHarvester:
    """Tests for LeadHarvester service."""

    @pytest.fixture
    def harvester(
        self,
        scanner_config: LeadScannerConfig,
        mock_hunter_client: AsyncMock,
    ) -> LeadHarvester:
        """Create harvester with mocked dependencies."""
        return LeadHarvester(
            config=scanner_config,
            hunter_client=mock_hunter_client,
        )

    @pytest.mark.asyncio
    async def test_harvest_enriches_leads(
        self,
        harvester: LeadHarvester,
        sample_raw_leads: list[RawLead],
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that harvest enriches raw leads."""
        result = await harvester.harvest(sample_raw_leads)

        assert len(result) > 0
        assert mock_hunter_client.domain_search.called

    @pytest.mark.asyncio
    async def test_harvest_extracts_contacts(
        self,
        harvester: LeadHarvester,
        sample_raw_lead: RawLead,
        mock_hunter_domain_response: dict,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that harvest extracts contacts from response."""
        mock_hunter_client.domain_search.return_value = mock_hunter_domain_response

        result = await harvester.harvest([sample_raw_lead])

        assert len(result) == 1
        harvested = result[0]
        assert len(harvested.contacts) > 0
        assert harvested.contacts[0].email is not None

    @pytest.mark.asyncio
    async def test_harvest_filters_low_confidence_contacts(
        self,
        harvester: LeadHarvester,
        sample_raw_lead: RawLead,
        mock_hunter_domain_response: dict,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that contacts below 50% confidence are filtered."""
        mock_hunter_client.domain_search.return_value = mock_hunter_domain_response

        result = await harvester.harvest([sample_raw_lead])

        # The mock response has one contact with 40% confidence
        # It should be filtered out
        harvested = result[0]
        for contact in harvested.contacts:
            assert contact.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_harvest_prioritizes_decision_makers(
        self,
        harvester: LeadHarvester,
        sample_raw_lead: RawLead,
        mock_hunter_domain_response: dict,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that contacts are sorted by position priority."""
        mock_hunter_client.domain_search.return_value = mock_hunter_domain_response

        result = await harvester.harvest([sample_raw_lead])

        harvested = result[0]
        # CEO should be first (highest priority position)
        assert harvested.contacts[0].position == "CEO"

    @pytest.mark.asyncio
    async def test_harvest_handles_api_error_gracefully(
        self,
        harvester: LeadHarvester,
        sample_raw_leads: list[RawLead],
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that harvest continues on API errors."""
        # First call fails, rest succeed
        mock_hunter_client.domain_search.side_effect = [
            HunterAPIError("API Error"),
            {
                "organization": "Good Company",
                "country": "Norway",
                "emails": [
                    {
                        "value": "test@good.com",
                        "confidence": 90,
                        "first_name": "Test",
                        "last_name": "User",
                    }
                ],
            },
            {
                "organization": "Another Company",
                "country": "Sweden",
                "emails": [
                    {
                        "value": "test@another.com",
                        "confidence": 85,
                        "first_name": "Another",
                        "last_name": "User",
                    }
                ],
            },
        ]

        result = await harvester.harvest(sample_raw_leads)

        # Should still get results despite one failure
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_harvest_skips_leads_without_company_name(
        self,
        harvester: LeadHarvester,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that leads without company name are skipped."""
        # Create raw lead without company name to test no-company scenario
        raw_lead_no_company = RawLead(
            domain="no-company.com",
            company_name=None,  # No fallback available
            country="Norway",
        )

        mock_hunter_client.domain_search.return_value = {
            "organization": None,
            "company": None,
            "emails": [{"value": "test@example.com", "confidence": 90}],
        }

        result = await harvester.harvest([raw_lead_no_company])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_harvest_skips_leads_without_contacts(
        self,
        harvester: LeadHarvester,
        sample_raw_lead: RawLead,
        mock_hunter_empty_response: dict,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that leads without contacts are skipped."""
        mock_hunter_client.domain_search.return_value = mock_hunter_empty_response

        result = await harvester.harvest([sample_raw_lead])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_harvest_extracts_company_info(
        self,
        harvester: LeadHarvester,
        sample_raw_lead: RawLead,
        mock_hunter_domain_response: dict,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that harvest extracts full company info."""
        mock_hunter_client.domain_search.return_value = mock_hunter_domain_response

        result = await harvester.harvest([sample_raw_lead])

        harvested = result[0]
        assert harvested.company_name == "Example Health Store"
        assert harvested.country == "Norway"
        assert harvested.city == "Oslo"
        assert harvested.linkedin is not None
        assert harvested.headcount == "11-50"

    def test_get_position_priority(
        self,
        harvester: LeadHarvester,
    ) -> None:
        """Test position priority scoring."""
        # Owner should have highest priority
        assert harvester._get_position_priority("Owner") > 0
        assert harvester._get_position_priority("CEO") > 0
        assert harvester._get_position_priority("Manager") > 0

        # Unknown position should have 0 priority
        assert harvester._get_position_priority("Intern") == 0
        assert harvester._get_position_priority(None) == 0
