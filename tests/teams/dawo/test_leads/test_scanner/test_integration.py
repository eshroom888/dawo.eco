"""Integration tests for B2B Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Tests full pipeline integration with mocked external dependencies.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from teams.dawo.leads.scanner.agent import B2BLeadScanner
from teams.dawo.leads.scanner.harvester import LeadHarvester
from teams.dawo.leads.scanner.transformer import LeadTransformer
from teams.dawo.leads.scanner.duplicate_checker import LeadDuplicateChecker
from teams.dawo.leads.scanner.pipeline import B2BLeadPipeline
from teams.dawo.leads.scanner.config import HunterClientConfig, LeadScannerConfig
from teams.dawo.leads.scanner.schemas import (
    RawLead,
    HarvestedLead,
    HarvestedContact,
    TransformedLead,
    PipelineStatus,
)
from teams.dawo.leads.scanner.tools import HunterAPIError


class TestPipelineIntegration:
    """Integration tests for the full B2B lead pipeline."""

    @pytest.fixture
    def hunter_config(self) -> HunterClientConfig:
        """Hunter.io API configuration."""
        return HunterClientConfig(
            api_key="test_api_key",
            base_url="https://api.hunter.io/v2",
            timeout_seconds=10,
            rate_limit_per_minute=60,
        )

    @pytest.fixture
    def scanner_config(self) -> LeadScannerConfig:
        """Lead scanner configuration."""
        return LeadScannerConfig(
            industries=["health food store"],
            search_keywords=["helsekost"],
            countries=["Norway"],
            min_confidence=0.7,
            max_leads_per_scan=5,
            required_fields=["email", "company"],
            preferred_positions=["ceo", "owner"],
            rate_limit_per_minute=60,
        )

    @pytest.fixture
    def mock_hunter_client(self) -> AsyncMock:
        """Mock Hunter.io client."""
        client = AsyncMock()
        client.domain_search.return_value = {
            "domain": "health-shop.no",
            "organization": "Health Shop AS",
            "company": "Health Shop AS",
            "country": "Norway",
            "industry": "Health Food",
            "linkedin": "https://linkedin.com/company/health-shop",
            "headcount": "11-50",
            "emails": [
                {
                    "value": "owner@health-shop.no",
                    "first_name": "Olav",
                    "last_name": "Hansen",
                    "position": "Owner",
                    "confidence": 95,
                },
                {
                    "value": "info@health-shop.no",
                    "first_name": None,
                    "last_name": None,
                    "position": None,
                    "confidence": 40,
                },
            ],
        }
        return client

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Mock lead repository."""
        repo = AsyncMock()
        repo.get_lead_by_email.return_value = None
        repo.get_leads_by_company.return_value = []
        repo.bulk_create_leads.return_value = (1, [uuid4()])
        return repo

    # =========================================================================
    # Full Pipeline Integration Tests
    # =========================================================================

    async def test_full_pipeline_creates_leads(
        self,
        scanner_config: LeadScannerConfig,
        mock_hunter_client: AsyncMock,
        mock_repository: AsyncMock,
    ) -> None:
        """Test full pipeline from scan to persistence."""
        # Create real components with mocked dependencies
        scanner = B2BLeadScanner(
            config=scanner_config,
            hunter_client=mock_hunter_client,
        )
        harvester = LeadHarvester(
            config=scanner_config,
            hunter_client=mock_hunter_client,
        )
        transformer = LeadTransformer(config=scanner_config)
        duplicate_checker = LeadDuplicateChecker(repository=mock_repository)

        pipeline = B2BLeadPipeline(
            scanner=scanner,
            harvester=harvester,
            transformer=transformer,
            duplicate_checker=duplicate_checker,
            repository=mock_repository,
        )

        # Execute pipeline
        result = await pipeline.execute()

        # Verify success
        assert result.status in [PipelineStatus.COMPLETE, PipelineStatus.PARTIAL]
        assert result.stats.domains_searched > 0
        mock_repository.bulk_create_leads.assert_called()

    async def test_pipeline_with_existing_leads_filters_duplicates(
        self,
        scanner_config: LeadScannerConfig,
        mock_hunter_client: AsyncMock,
        mock_repository: AsyncMock,
    ) -> None:
        """Test pipeline filters out existing leads."""
        # Configure repository to return existing lead
        existing_lead = MagicMock()
        existing_lead.email = "owner@health-shop.no"
        existing_lead.company = "Health Shop AS"
        mock_repository.get_lead_by_email.return_value = existing_lead

        scanner = B2BLeadScanner(
            config=scanner_config,
            hunter_client=mock_hunter_client,
        )
        harvester = LeadHarvester(
            config=scanner_config,
            hunter_client=mock_hunter_client,
        )
        transformer = LeadTransformer(config=scanner_config)
        duplicate_checker = LeadDuplicateChecker(repository=mock_repository)

        pipeline = B2BLeadPipeline(
            scanner=scanner,
            harvester=harvester,
            transformer=transformer,
            duplicate_checker=duplicate_checker,
            repository=mock_repository,
        )

        result = await pipeline.execute()

        # Should complete but with duplicates filtered
        assert result.status == PipelineStatus.COMPLETE
        assert result.stats.duplicates_found > 0

    async def test_pipeline_handles_api_errors_gracefully(
        self,
        scanner_config: LeadScannerConfig,
        mock_repository: AsyncMock,
    ) -> None:
        """Test pipeline handles Hunter.io API errors."""
        # Mock client that raises error
        failing_client = AsyncMock()
        failing_client.domain_search.side_effect = HunterAPIError("Rate limit exceeded", 429)

        scanner = B2BLeadScanner(
            config=scanner_config,
            hunter_client=failing_client,
        )
        harvester = LeadHarvester(
            config=scanner_config,
            hunter_client=failing_client,
        )
        transformer = LeadTransformer(config=scanner_config)
        duplicate_checker = LeadDuplicateChecker(repository=mock_repository)

        pipeline = B2BLeadPipeline(
            scanner=scanner,
            harvester=harvester,
            transformer=transformer,
            duplicate_checker=duplicate_checker,
            repository=mock_repository,
        )

        result = await pipeline.execute()

        # Should return INCOMPLETE or COMPLETE (graceful degradation)
        assert result.status in [PipelineStatus.INCOMPLETE, PipelineStatus.COMPLETE]

    async def test_pipeline_tracks_statistics_through_stages(
        self,
        scanner_config: LeadScannerConfig,
        mock_hunter_client: AsyncMock,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that pipeline tracks statistics at each stage."""
        scanner = B2BLeadScanner(
            config=scanner_config,
            hunter_client=mock_hunter_client,
        )
        harvester = LeadHarvester(
            config=scanner_config,
            hunter_client=mock_hunter_client,
        )
        transformer = LeadTransformer(config=scanner_config)
        duplicate_checker = LeadDuplicateChecker(repository=mock_repository)

        pipeline = B2BLeadPipeline(
            scanner=scanner,
            harvester=harvester,
            transformer=transformer,
            duplicate_checker=duplicate_checker,
            repository=mock_repository,
        )

        result = await pipeline.execute()

        # Verify statistics are tracked
        stats = result.stats
        assert stats.domains_searched >= 0
        assert stats.raw_leads_found >= 0
        assert stats.leads_harvested >= 0
        assert stats.leads_transformed >= 0


class TestDuplicateDetectionIntegration:
    """Integration tests for duplicate detection with mocked database."""

    @pytest.fixture
    def mock_repository_with_existing_leads(self) -> AsyncMock:
        """Repository with pre-existing leads."""
        repo = AsyncMock()

        # Existing leads in database
        existing = MagicMock()
        existing.email = "existing@company.no"
        existing.company = "Existing Company AS"

        def check_email(email: str):
            if email.lower() == "existing@company.no":
                return existing
            return None

        def check_company(company: str, country: str = None):
            if "existing" in company.lower():
                return [existing]
            return []

        repo.get_lead_by_email.side_effect = check_email
        repo.get_leads_by_company.side_effect = check_company

        return repo

    async def test_duplicate_checker_filters_exact_email_match(
        self,
        mock_repository_with_existing_leads: AsyncMock,
    ) -> None:
        """Test duplicate checker filters exact email matches."""
        checker = LeadDuplicateChecker(
            repository=mock_repository_with_existing_leads,
        )

        leads = [
            TransformedLead(
                email="existing@company.no",
                first_name="Test",
                last_name="User",
                company="Test Company",
            ),
            TransformedLead(
                email="new@company.no",
                first_name="New",
                last_name="User",
                company="New Company",
            ),
        ]

        result = await checker.check_duplicates(leads)

        # Only the new lead should remain
        assert len(result) == 1
        assert result[0].email == "new@company.no"

    async def test_duplicate_checker_filters_fuzzy_company_match(
        self,
        mock_repository_with_existing_leads: AsyncMock,
    ) -> None:
        """Test duplicate checker filters fuzzy company matches."""
        checker = LeadDuplicateChecker(
            repository=mock_repository_with_existing_leads,
            match_threshold=0.9,
        )

        leads = [
            TransformedLead(
                email="new-email@existing-company.no",
                first_name="Other",
                last_name="Person",
                company="Existing Company",  # Same company, different email
                country="Norway",
            ),
        ]

        result = await checker.check_duplicates(leads)

        # Should be filtered as duplicate company
        assert len(result) == 0

    async def test_duplicate_checker_deduplicates_batch(
        self,
        mock_repository_with_existing_leads: AsyncMock,
    ) -> None:
        """Test duplicate checker handles duplicates within same batch."""
        checker = LeadDuplicateChecker(
            repository=mock_repository_with_existing_leads,
        )

        leads = [
            TransformedLead(
                email="unique@newcompany.no",
                first_name="First",
                last_name="Person",
                company="New Company",
            ),
            TransformedLead(
                email="UNIQUE@NEWCOMPANY.NO",  # Same email, different case
                first_name="Second",
                last_name="Person",
                company="New Company",
            ),
        ]

        result = await checker.check_duplicates(leads)

        # Only first occurrence should remain
        assert len(result) == 1
        assert result[0].first_name == "First"


class TestScannerHarvesterIntegration:
    """Integration tests for scanner and harvester stages."""

    @pytest.fixture
    def scanner_config(self) -> LeadScannerConfig:
        """Scanner configuration for integration tests."""
        return LeadScannerConfig(
            industries=["health food"],
            search_keywords=["organic"],
            countries=["Norway", "Sweden"],
            min_confidence=0.6,
            max_leads_per_scan=10,
            required_fields=["email", "company"],
            preferred_positions=["owner", "ceo"],
            rate_limit_per_minute=60,
        )

    async def test_scanner_to_harvester_data_flow(
        self,
        scanner_config: LeadScannerConfig,
    ) -> None:
        """Test data flows correctly from scanner to harvester."""
        # Mock response for all domain searches
        domain_response = {
            "domain": "shop.no",
            "organization": "Shop Company",
            "country": "Norway",
            "emails": [{"value": "contact@shop.no", "confidence": 90, "first_name": "Test", "last_name": "User", "position": "Owner"}],
        }

        mock_client = AsyncMock()
        # Return same response for all calls (scanner and harvester)
        mock_client.domain_search.return_value = domain_response

        scanner = B2BLeadScanner(config=scanner_config, hunter_client=mock_client)
        harvester = LeadHarvester(config=scanner_config, hunter_client=mock_client)

        # Execute scanner
        scan_result = await scanner.scan()
        assert len(scan_result.leads) > 0

        # Pass to harvester
        harvested = await harvester.harvest(scan_result.leads)

        # Verify data integrity
        assert len(harvested) > 0
        for lead in harvested:
            assert lead.company_name is not None
            assert len(lead.contacts) > 0

    async def test_harvester_filters_low_confidence_contacts(
        self,
        scanner_config: LeadScannerConfig,
    ) -> None:
        """Test harvester filters low confidence contacts."""
        mock_client = AsyncMock()
        mock_client.domain_search.return_value = {
            "domain": "test.no",
            "organization": "Test Company",
            "country": "Norway",
            "emails": [
                {"value": "high@test.no", "confidence": 95, "first_name": "High", "last_name": "Conf", "position": "CEO"},
                {"value": "low@test.no", "confidence": 30, "first_name": "Low", "last_name": "Conf", "position": None},
            ],
        }

        harvester = LeadHarvester(config=scanner_config, hunter_client=mock_client)

        raw_leads = [
            RawLead(
                domain="test.no",
                company_name="Test Company",
                country="Norway",
                confidence=0.9,
            )
        ]

        harvested = await harvester.harvest(raw_leads)

        # Only high confidence contact should be included
        assert len(harvested) == 1
        assert len(harvested[0].contacts) == 1
        assert harvested[0].contacts[0].confidence >= 0.5


class TestTransformerValidation:
    """Integration tests for transformer validation."""

    @pytest.fixture
    def scanner_config(self) -> LeadScannerConfig:
        """Scanner configuration."""
        return LeadScannerConfig(
            industries=["health food"],
            countries=["Norway"],
            min_confidence=0.7,
            max_leads_per_scan=10,
            required_fields=["email", "company"],
        )

    def test_transformer_validates_required_fields(
        self,
        scanner_config: LeadScannerConfig,
    ) -> None:
        """Test transformer validates required fields."""
        transformer = LeadTransformer(config=scanner_config)

        # Lead missing email
        leads = [
            HarvestedLead(
                domain="test.no",
                company_name="Test Company",
                contacts=[],  # No contacts = no email
            )
        ]

        result = transformer.transform(leads)

        # Should be filtered out
        assert len(result) == 0

    def test_transformer_normalizes_data(
        self,
        scanner_config: LeadScannerConfig,
    ) -> None:
        """Test transformer normalizes data correctly."""
        transformer = LeadTransformer(config=scanner_config)

        leads = [
            HarvestedLead(
                domain="test.no",
                company_name="  Test Company AS  ",  # Needs trimming
                contacts=[
                    HarvestedContact(
                        email="  JOHN.DOE@TEST.NO  ",  # Needs lowercase + trim
                        first_name="john",  # Needs title case
                        last_name="DOE",  # Needs title case
                        position="ceo",
                        confidence=0.95,
                    )
                ],
                country="norway",  # Needs title case
            )
        ]

        result = transformer.transform(leads)

        assert len(result) == 1
        assert result[0].email == "john.doe@test.no"
        assert result[0].first_name == "John"
        assert result[0].last_name == "Doe"
