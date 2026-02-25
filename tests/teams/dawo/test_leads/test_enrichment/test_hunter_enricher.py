"""Tests for HunterEnricher.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 4: Implement Hunter.io Extended Enrichment
"""

import pytest
from unittest.mock import AsyncMock, Mock


class TestHunterEnricherInit:
    """Tests for HunterEnricher initialization."""

    def test_accepts_hunter_client_via_injection(self) -> None:
        """Test HunterEnricher accepts HunterClient via DI."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher

        hunter_client = AsyncMock()

        enricher = HunterEnricher(hunter_client=hunter_client)

        assert enricher._client is hunter_client


class TestEnrichCompany:
    """Tests for enrich_company method."""

    @pytest.mark.asyncio
    async def test_enrich_company_returns_company_data(self) -> None:
        """Test enriching company with domain search."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher

        hunter_response = {
            "domain": "healthstore.no",
            "organization": "Health Store AS",
            "company": "Health Store AS",
            "country": "Norway",
            "headcount": "11-50",
            "industry": "Retail - Health & Wellness",
            "emails": [
                {"value": "john@healthstore.no", "confidence": 95},
            ],
        }

        hunter_client = AsyncMock()
        hunter_client.domain_search.return_value = hunter_response

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.enrich_company("healthstore.no")

        assert result.domain == "healthstore.no"
        assert result.organization == "Health Store AS"
        assert result.headcount == "11-50"
        assert result.industry == "Retail - Health & Wellness"

    @pytest.mark.asyncio
    async def test_enrich_company_extracts_email_patterns(self) -> None:
        """Test extraction of email patterns."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher

        hunter_response = {
            "domain": "example.com",
            "organization": "Example Inc",
            "emails": [
                {"value": "john.smith@example.com", "confidence": 95},
                {"value": "jane.doe@example.com", "confidence": 90},
            ],
        }

        hunter_client = AsyncMock()
        hunter_client.domain_search.return_value = hunter_response

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.enrich_company("example.com")

        assert "john.smith@example.com" in result.email_patterns
        assert "jane.doe@example.com" in result.email_patterns

    @pytest.mark.asyncio
    async def test_enrich_company_handles_api_error(self) -> None:
        """Test graceful handling of Hunter.io API errors."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher
        from teams.dawo.leads.scanner.tools import HunterAPIError

        hunter_client = AsyncMock()
        hunter_client.domain_search.side_effect = HunterAPIError("API error")

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.enrich_company("error.com")

        assert result.domain == "error.com"
        assert result.organization is None

    @pytest.mark.asyncio
    async def test_enrich_company_handles_empty_response(self) -> None:
        """Test handling of empty API response."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher

        hunter_client = AsyncMock()
        hunter_client.domain_search.return_value = {}

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.enrich_company("unknown.com")

        assert result.domain == "unknown.com"
        assert result.organization is None


class TestFindDecisionMakers:
    """Tests for find_decision_makers method."""

    @pytest.mark.asyncio
    async def test_find_decision_makers_filters_by_position(self) -> None:
        """Test filtering contacts by decision-maker positions."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher

        hunter_response = {
            "domain": "store.no",
            "emails": [
                {
                    "value": "ceo@store.no",
                    "first_name": "John",
                    "last_name": "CEO",
                    "position": "CEO",
                    "confidence": 95,
                },
                {
                    "value": "intern@store.no",
                    "first_name": "Jane",
                    "last_name": "Intern",
                    "position": "Marketing Intern",
                    "confidence": 80,
                },
                {
                    "value": "buyer@store.no",
                    "first_name": "Bob",
                    "last_name": "Buyer",
                    "position": "Purchasing Manager",
                    "confidence": 90,
                },
            ],
        }

        hunter_client = AsyncMock()
        hunter_client.domain_search.return_value = hunter_response

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.find_decision_makers("store.no")

        # Should include CEO and Purchasing Manager, not Intern
        emails = [c.email for c in result]
        assert "ceo@store.no" in emails
        assert "buyer@store.no" in emails
        assert "intern@store.no" not in emails

    @pytest.mark.asyncio
    async def test_find_decision_makers_prioritizes_verified(self) -> None:
        """Test prioritization of verified emails."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher

        hunter_response = {
            "domain": "store.no",
            "emails": [
                {
                    "value": "owner1@store.no",
                    "position": "Owner",
                    "confidence": 50,
                },
                {
                    "value": "owner2@store.no",
                    "position": "Owner",
                    "confidence": 95,
                },
            ],
        }

        hunter_client = AsyncMock()
        hunter_client.domain_search.return_value = hunter_response

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.find_decision_makers("store.no")

        # Higher confidence should come first
        assert result[0].email == "owner2@store.no"

    @pytest.mark.asyncio
    async def test_find_decision_makers_returns_empty_on_error(self) -> None:
        """Test graceful handling of API errors."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher
        from teams.dawo.leads.scanner.tools import HunterAPIError

        hunter_client = AsyncMock()
        hunter_client.domain_search.side_effect = HunterAPIError("Error")

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.find_decision_makers("error.com")

        assert result == []


class TestVerifyContacts:
    """Tests for verify_contacts method."""

    @pytest.mark.asyncio
    async def test_verify_contacts_filters_deliverable(self) -> None:
        """Test filtering to only deliverable emails."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher
        from teams.dawo.leads.scanner.schemas import HarvestedContact

        contacts = [
            HarvestedContact(email="valid@test.com", first_name="Valid"),
            HarvestedContact(email="invalid@test.com", first_name="Invalid"),
        ]

        def mock_verify(email):
            if email == "valid@test.com":
                return {"status": "valid", "result": "deliverable", "score": 95}
            return {"status": "invalid", "result": "undeliverable", "score": 10}

        hunter_client = AsyncMock()
        hunter_client.email_verifier.side_effect = mock_verify

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.verify_contacts(contacts)

        assert len(result) == 1
        assert result[0].email == "valid@test.com"

    @pytest.mark.asyncio
    async def test_verify_contacts_handles_api_error(self) -> None:
        """Test graceful handling of verification errors."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher
        from teams.dawo.leads.scanner.schemas import HarvestedContact
        from teams.dawo.leads.scanner.tools import HunterAPIError

        contacts = [
            HarvestedContact(email="test@test.com", first_name="Test"),
        ]

        hunter_client = AsyncMock()
        hunter_client.email_verifier.side_effect = HunterAPIError("Error")

        enricher = HunterEnricher(hunter_client=hunter_client)
        result = await enricher.verify_contacts(contacts)

        # Should return empty on error, not crash
        assert result == []


class TestAPIUsageTracking:
    """Tests for API usage tracking."""

    @pytest.mark.asyncio
    async def test_tracks_api_calls(self) -> None:
        """Test that API calls are tracked."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher

        hunter_response = {"domain": "test.com", "emails": []}

        hunter_client = AsyncMock()
        hunter_client.domain_search.return_value = hunter_response

        enricher = HunterEnricher(hunter_client=hunter_client)

        # Make some calls
        await enricher.enrich_company("test.com")
        await enricher.find_decision_makers("test2.com")

        # Check usage stats
        stats = enricher.get_usage_stats()
        assert stats["domain_searches"] == 2

    @pytest.mark.asyncio
    async def test_tracks_verification_calls(self) -> None:
        """Test that verification calls are tracked."""
        from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher
        from teams.dawo.leads.scanner.schemas import HarvestedContact

        contacts = [
            HarvestedContact(email="a@test.com"),
            HarvestedContact(email="b@test.com"),
        ]

        hunter_client = AsyncMock()
        hunter_client.email_verifier.return_value = {
            "status": "valid",
            "result": "deliverable",
        }

        enricher = HunterEnricher(hunter_client=hunter_client)
        await enricher.verify_contacts(contacts)

        stats = enricher.get_usage_stats()
        assert stats["verifications"] == 2
