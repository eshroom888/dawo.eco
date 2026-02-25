"""B2B Lead Pipeline for Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Orchestrates the full lead discovery pipeline:
Scanner -> Harvester -> Transformer -> DuplicateChecker -> Repository
"""

import logging
from datetime import datetime, UTC
from typing import Protocol, Optional
from uuid import UUID

from teams.dawo.leads.scanner.agent import B2BLeadScanner
from teams.dawo.leads.scanner.harvester import LeadHarvester
from teams.dawo.leads.scanner.transformer import LeadTransformer
from teams.dawo.leads.scanner.duplicate_checker import LeadDuplicateChecker
from teams.dawo.leads.scanner.schemas import (
    PipelineResult,
    PipelineStatus,
    ScanStatistics,
    TransformedLead,
)
from teams.dawo.leads.scanner.tools import HunterAPIError


logger = logging.getLogger(__name__)


class LeadRepositoryProtocol(Protocol):
    """Protocol for lead repository dependency."""

    async def bulk_create_leads(
        self,
        leads: list[dict],
    ) -> tuple[int, list[UUID]]:
        """Create multiple leads in database."""
        ...


class NotificationServiceProtocol(Protocol):
    """Protocol for notification service (optional)."""

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
    ) -> bool:
        """Send alert notification."""
        ...


class B2BLeadPipeline:
    """Orchestrates the full lead discovery pipeline.

    Pipeline stages:
    1. Scanner: Discovers potential leads from configured domains
    2. Harvester: Enriches leads with Hunter.io data
    3. Transformer: Maps to Lead model format
    4. DuplicateChecker: Filters existing leads
    5. Repository: Persists new leads to database

    Implements graceful degradation - partial failures don't stop pipeline.

    Accepts all dependencies via injection.
    """

    def __init__(
        self,
        scanner: B2BLeadScanner,
        harvester: LeadHarvester,
        transformer: LeadTransformer,
        duplicate_checker: LeadDuplicateChecker,
        repository: LeadRepositoryProtocol,
        notification_service: Optional[NotificationServiceProtocol] = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            scanner: Lead scanner agent
            harvester: Lead harvester service
            transformer: Lead transformer service
            duplicate_checker: Duplicate detection service
            repository: Lead repository for persistence
            notification_service: Optional notification service for alerts
        """
        self._scanner = scanner
        self._harvester = harvester
        self._transformer = transformer
        self._duplicate_checker = duplicate_checker
        self._repository = repository
        self._notification_service = notification_service

    async def execute(self) -> PipelineResult:
        """Execute the full lead discovery pipeline.

        Returns:
            PipelineResult with status, statistics, and created lead IDs

        Note:
            Implements graceful degradation:
            - API failures mark pipeline INCOMPLETE (retry scheduled)
            - Individual lead failures continue pipeline (PARTIAL status)
            - Critical errors mark pipeline FAILED and notify
        """
        started_at = datetime.now(UTC)
        stats = ScanStatistics()
        created_ids: list[UUID] = []
        error_message: Optional[str] = None
        retry_scheduled = False

        logger.info("Starting B2B lead pipeline execution")

        try:
            # Stage 1: Scan for leads
            logger.info("Stage 1: Scanning for leads")
            scan_result = await self._scanner.scan()
            stats.domains_searched = scan_result.domains_searched
            stats.raw_leads_found = len(scan_result.leads)
            stats.errors = len(scan_result.errors)

            if not scan_result.leads:
                logger.info("No leads found in scan")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    stats=stats,
                    created_lead_ids=[],
                    started_at=started_at,
                )

            # Stage 2: Harvest lead details
            logger.info(f"Stage 2: Harvesting {len(scan_result.leads)} leads")
            harvested = await self._harvester.harvest(scan_result.leads)
            stats.leads_harvested = len(harvested)

            if not harvested:
                logger.info("No leads harvested successfully")
                return PipelineResult(
                    status=PipelineStatus.PARTIAL,
                    stats=stats,
                    created_lead_ids=[],
                    error="Harvest stage produced no valid leads",
                    started_at=started_at,
                )

            # Stage 3: Transform to database format
            logger.info(f"Stage 3: Transforming {len(harvested)} leads")
            transformed = self._transformer.transform(harvested)
            stats.leads_transformed = len(transformed)

            if not transformed:
                logger.info("No leads transformed successfully")
                return PipelineResult(
                    status=PipelineStatus.PARTIAL,
                    stats=stats,
                    created_lead_ids=[],
                    error="Transform stage produced no valid leads",
                    started_at=started_at,
                )

            # Stage 4: Check for duplicates
            logger.info(f"Stage 4: Checking {len(transformed)} leads for duplicates")
            unique_leads = await self._duplicate_checker.check_duplicates(transformed)
            stats.duplicates_found = len(transformed) - len(unique_leads)

            if not unique_leads:
                logger.info("All leads were duplicates")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    stats=stats,
                    created_lead_ids=[],
                    started_at=started_at,
                )

            # Stage 5: Persist to database
            logger.info(f"Stage 5: Creating {len(unique_leads)} leads in database")
            count, created_ids = await self._persist_leads(unique_leads)
            stats.leads_created = count

            # Determine final status
            status = self._determine_status(stats)

            logger.info(
                f"Pipeline complete: {stats.leads_created} leads created "
                f"({stats.duplicates_found} duplicates, {stats.errors} errors)"
            )

            return PipelineResult(
                status=status,
                stats=stats,
                created_lead_ids=created_ids,
                started_at=started_at,
            )

        except HunterAPIError as e:
            # API failure - mark for retry
            logger.error(f"Hunter.io API failure: {e}")
            error_message = f"API error: {e}"
            retry_scheduled = True

            return PipelineResult(
                status=PipelineStatus.INCOMPLETE,
                stats=stats,
                created_lead_ids=created_ids,
                error=error_message,
                retry_scheduled=retry_scheduled,
                started_at=started_at,
            )

        except Exception as e:
            # Critical error
            logger.exception(f"Pipeline failed with unexpected error: {e}")
            error_message = f"Pipeline error: {e}"

            # Send alert if notification service available
            await self._notify_failure(str(e))

            return PipelineResult(
                status=PipelineStatus.FAILED,
                stats=stats,
                created_lead_ids=created_ids,
                error=error_message,
                started_at=started_at,
            )

    async def _persist_leads(
        self,
        leads: list[TransformedLead],
    ) -> tuple[int, list[UUID]]:
        """Persist leads to database.

        Args:
            leads: Transformed leads to create

        Returns:
            Tuple of (count created, list of created IDs)
        """
        try:
            # Convert to dicts for repository
            lead_dicts = [lead.to_dict() for lead in leads]
            return await self._repository.bulk_create_leads(lead_dicts)
        except Exception as e:
            logger.error(f"Failed to persist leads: {e}")
            # Return partial results if any
            return 0, []

    def _determine_status(self, stats: ScanStatistics) -> PipelineStatus:
        """Determine pipeline status based on statistics.

        Args:
            stats: Pipeline statistics

        Returns:
            Appropriate PipelineStatus
        """
        if stats.errors > 0:
            # Some errors but pipeline continued
            return PipelineStatus.PARTIAL

        if stats.leads_created == 0 and stats.raw_leads_found > 0:
            # Found leads but none created (all duplicates/invalid)
            return PipelineStatus.COMPLETE

        return PipelineStatus.COMPLETE

    async def _notify_failure(self, error: str) -> None:
        """Send failure notification if service available.

        Args:
            error: Error message to include
        """
        if self._notification_service:
            try:
                await self._notification_service.send_alert(
                    title="B2B Lead Pipeline Failed",
                    message=f"Pipeline execution failed: {error}",
                    severity="error",
                )
            except Exception as e:
                logger.error(f"Failed to send failure notification: {e}")
