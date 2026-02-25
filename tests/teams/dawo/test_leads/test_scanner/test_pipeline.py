"""Tests for B2BLeadPipeline.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.leads.scanner.pipeline import B2BLeadPipeline
from teams.dawo.leads.scanner.agent import B2BLeadScanner
from teams.dawo.leads.scanner.harvester import LeadHarvester
from teams.dawo.leads.scanner.transformer import LeadTransformer
from teams.dawo.leads.scanner.duplicate_checker import LeadDuplicateChecker
from teams.dawo.leads.scanner.schemas import (
    RawLead,
    HarvestedLead,
    HarvestedContact,
    TransformedLead,
    ScanResult,
    PipelineStatus,
)
from teams.dawo.leads.scanner.tools import HunterAPIError


class TestB2BLeadPipeline:
    """Tests for B2BLeadPipeline orchestrator."""

    @pytest.fixture
    def mock_scanner(self) -> AsyncMock:
        """Create mock scanner."""
        scanner = AsyncMock(spec=B2BLeadScanner)
        scanner.scan.return_value = ScanResult(
            leads=[
                RawLead(domain="example.no", company_name="Example", confidence=0.9),
            ],
            domains_searched=5,
            errors=[],
        )
        return scanner

    @pytest.fixture
    def mock_harvester(self) -> AsyncMock:
        """Create mock harvester."""
        harvester = AsyncMock(spec=LeadHarvester)
        harvester.harvest.return_value = [
            HarvestedLead(
                domain="example.no",
                company_name="Example AS",
                contacts=[
                    HarvestedContact(
                        email="contact@example.no",
                        first_name="Test",
                        last_name="User",
                        confidence=0.9,
                    ),
                ],
            ),
        ]
        return harvester

    @pytest.fixture
    def mock_transformer(self) -> MagicMock:
        """Create mock transformer (sync method)."""
        transformer = MagicMock(spec=LeadTransformer)
        transformer.transform.return_value = [
            TransformedLead(
                email="contact@example.no",
                first_name="Test",
                last_name="User",
                company="Example AS",
            ),
        ]
        return transformer

    @pytest.fixture
    def mock_duplicate_checker(self) -> AsyncMock:
        """Create mock duplicate checker."""
        checker = AsyncMock(spec=LeadDuplicateChecker)
        checker.check_duplicates.return_value = [
            TransformedLead(
                email="contact@example.no",
                first_name="Test",
                last_name="User",
                company="Example AS",
            ),
        ]
        return checker

    @pytest.fixture
    def pipeline(
        self,
        mock_scanner: AsyncMock,
        mock_harvester: AsyncMock,
        mock_transformer: MagicMock,
        mock_duplicate_checker: AsyncMock,
        mock_lead_repository: AsyncMock,
    ) -> B2BLeadPipeline:
        """Create pipeline with mocked components."""
        return B2BLeadPipeline(
            scanner=mock_scanner,
            harvester=mock_harvester,
            transformer=mock_transformer,
            duplicate_checker=mock_duplicate_checker,
            repository=mock_lead_repository,
        )

    @pytest.mark.asyncio
    async def test_execute_completes_successfully(
        self,
        pipeline: B2BLeadPipeline,
    ) -> None:
        """Test successful pipeline execution."""
        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.stats.leads_created > 0

    @pytest.mark.asyncio
    async def test_execute_calls_all_stages(
        self,
        pipeline: B2BLeadPipeline,
        mock_scanner: AsyncMock,
        mock_harvester: AsyncMock,
        mock_transformer: MagicMock,
        mock_duplicate_checker: AsyncMock,
        mock_lead_repository: AsyncMock,
    ) -> None:
        """Test that all pipeline stages are called."""
        await pipeline.execute()

        mock_scanner.scan.assert_called_once()
        mock_harvester.harvest.assert_called_once()
        mock_transformer.transform.assert_called_once()
        mock_duplicate_checker.check_duplicates.assert_called_once()
        mock_lead_repository.bulk_create_leads.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tracks_statistics(
        self,
        pipeline: B2BLeadPipeline,
    ) -> None:
        """Test that pipeline tracks statistics."""
        result = await pipeline.execute()

        assert result.stats.domains_searched > 0
        assert result.stats.raw_leads_found > 0
        assert result.stats.leads_harvested > 0
        assert result.stats.leads_transformed > 0

    @pytest.mark.asyncio
    async def test_execute_handles_no_leads_found(
        self,
        pipeline: B2BLeadPipeline,
        mock_scanner: AsyncMock,
    ) -> None:
        """Test pipeline handles case when no leads are found."""
        mock_scanner.scan.return_value = ScanResult(
            leads=[],
            domains_searched=5,
            errors=[],
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.stats.raw_leads_found == 0

    @pytest.mark.asyncio
    async def test_execute_handles_harvest_failure(
        self,
        pipeline: B2BLeadPipeline,
        mock_harvester: AsyncMock,
    ) -> None:
        """Test pipeline handles harvest stage returning no leads."""
        mock_harvester.harvest.return_value = []

        result = await pipeline.execute()

        assert result.status == PipelineStatus.PARTIAL
        assert "Harvest stage" in result.error

    @pytest.mark.asyncio
    async def test_execute_handles_all_duplicates(
        self,
        pipeline: B2BLeadPipeline,
        mock_duplicate_checker: AsyncMock,
    ) -> None:
        """Test pipeline handles case when all leads are duplicates."""
        mock_duplicate_checker.check_duplicates.return_value = []

        result = await pipeline.execute()

        assert result.status == PipelineStatus.COMPLETE
        assert result.stats.duplicates_found > 0
        assert result.stats.leads_created == 0

    @pytest.mark.asyncio
    async def test_execute_handles_api_error(
        self,
        pipeline: B2BLeadPipeline,
        mock_scanner: AsyncMock,
    ) -> None:
        """Test pipeline handles API errors gracefully."""
        mock_scanner.scan.side_effect = HunterAPIError("API Error")

        result = await pipeline.execute()

        assert result.status == PipelineStatus.INCOMPLETE
        assert result.retry_scheduled is True
        assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_execute_handles_critical_error(
        self,
        pipeline: B2BLeadPipeline,
        mock_scanner: AsyncMock,
        mock_notification_service: AsyncMock,
    ) -> None:
        """Test pipeline handles critical errors and notifies."""
        pipeline._notification_service = mock_notification_service
        mock_scanner.scan.side_effect = RuntimeError("Critical failure")

        result = await pipeline.execute()

        assert result.status == PipelineStatus.FAILED
        assert "Pipeline error" in result.error
        mock_notification_service.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_created_ids(
        self,
        pipeline: B2BLeadPipeline,
        mock_lead_repository: AsyncMock,
    ) -> None:
        """Test that pipeline returns created lead IDs."""
        created_ids = [uuid4(), uuid4()]
        mock_lead_repository.bulk_create_leads.return_value = (2, created_ids)

        result = await pipeline.execute()

        assert result.created_lead_ids == created_ids

    @pytest.mark.asyncio
    async def test_execute_calculates_duration(
        self,
        pipeline: B2BLeadPipeline,
    ) -> None:
        """Test that pipeline calculates execution duration."""
        result = await pipeline.execute()

        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_execute_with_scan_errors_returns_partial(
        self,
        pipeline: B2BLeadPipeline,
        mock_scanner: AsyncMock,
    ) -> None:
        """Test that scan errors result in PARTIAL status."""
        mock_scanner.scan.return_value = ScanResult(
            leads=[RawLead(domain="example.no", confidence=0.9)],
            domains_searched=5,
            errors=["Error scanning domain1.no"],
        )

        result = await pipeline.execute()

        assert result.status == PipelineStatus.PARTIAL
        assert result.stats.errors > 0
