"""Enrichment Pipeline for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 8: Implement Enrichment Pipeline

Orchestrates batch processing of leads for enrichment:
- Queries NEW leads from repository
- Processes in configurable batches
- Updates lead status and enrichment data
- Logs activities for audit trail
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Optional, Protocol
from uuid import UUID

from teams.dawo.leads.enrichment.config import EnrichmentConfig, DEFAULT_BATCH_SIZE
from teams.dawo.leads.enrichment.schemas import EnrichmentResult
from core.leads.models import LeadStatus, ActivityType


logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """Pipeline execution status.

    Values:
        COMPLETE: All leads processed successfully
        INCOMPLETE: Some leads failed, but pipeline continued
        FAILED: Critical error, pipeline stopped
        EMPTY: No leads to process
    """

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    EMPTY = "empty"


@dataclass
class PipelineResult:
    """Result of pipeline execution.

    Attributes:
        total_processed: Total leads attempted
        successful: Successfully enriched leads
        failed: Leads that failed enrichment
        qualified: Leads marked QUALIFIED
        researching: Leads marked RESEARCHING
        converted: Leads marked CONVERTED (existing customers)
        status: Overall pipeline status
        errors: List of error messages
        started_at: Pipeline start time
        completed_at: Pipeline completion time
    """

    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    qualified: int = 0
    researching: int = 0
    converted: int = 0
    status: PipelineStatus = PipelineStatus.COMPLETE
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "total_processed": self.total_processed,
            "successful": self.successful,
            "failed": self.failed,
            "qualified": self.qualified,
            "researching": self.researching,
            "converted": self.converted,
            "status": self.status.value,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class LeadNotFoundError(Exception):
    """Raised when a lead is not found in the repository."""

    def __init__(self, lead_id: UUID) -> None:
        self.lead_id = lead_id
        super().__init__(f"Lead not found: {lead_id}")


class LeadRepositoryProtocol(Protocol):
    """Protocol for lead repository dependency."""

    async def get_leads_for_enrichment(self, limit: int) -> list[Any]:
        """Get leads ready for enrichment (status=NEW)."""
        ...

    async def get_by_id(self, lead_id: UUID) -> Optional[Any]:
        """Get a lead by ID."""
        ...

    async def update_enrichment(
        self,
        lead_id: UUID,
        enrichment_data: dict[str, Any],
        status: LeadStatus,
        score: float,
        enriched_at: datetime,
    ) -> Any:
        """Update lead with enrichment data."""
        ...

    async def add_activity(
        self,
        lead_id: UUID,
        activity_type: ActivityType,
        description: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Add activity log entry for a lead."""
        ...


class EnrichmentServiceProtocol(Protocol):
    """Protocol for enrichment service dependency."""

    async def enrich_lead(self, lead: Any) -> EnrichmentResult:
        """Enrich a single lead."""
        ...

    def determine_status(
        self,
        result: EnrichmentResult,
        is_existing_customer: bool = False,
    ) -> LeadStatus:
        """Determine lead status based on enrichment result."""
        ...

    def format_enrichment_data(self, result: EnrichmentResult) -> dict[str, Any]:
        """Format enrichment result for storage."""
        ...


class EnrichmentPipeline:
    """Pipeline for batch lead enrichment.

    Orchestrates the enrichment process for multiple leads:
    - Queries leads with NEW status
    - Processes in configurable batches
    - Updates lead records with enrichment data
    - Logs activities for audit trail
    - Handles failures gracefully

    Attributes:
        _config: Pipeline configuration
        _repository: Lead repository for data access
        _enrichment_service: Service for enriching leads
    """

    def __init__(
        self,
        config: EnrichmentConfig,
        repository: LeadRepositoryProtocol,
        enrichment_service: EnrichmentServiceProtocol,
    ) -> None:
        """Initialize the enrichment pipeline.

        Args:
            config: Pipeline configuration
            repository: Lead repository for data access
            enrichment_service: Service for enriching leads
        """
        self._config = config
        self._repository = repository
        self._enrichment_service = enrichment_service

    async def execute(
        self,
        batch_size: Optional[int] = None,
    ) -> PipelineResult:
        """Execute the enrichment pipeline.

        Queries leads with status=NEW and processes them in batches.
        Continues processing even if individual leads fail.

        Args:
            batch_size: Maximum leads to process (default from config)

        Returns:
            PipelineResult with statistics
        """
        batch_size = batch_size or self._config.batch_size or DEFAULT_BATCH_SIZE

        result = PipelineResult(
            started_at=datetime.now(UTC),
        )

        try:
            # Query leads for enrichment
            leads = await self._repository.get_leads_for_enrichment(limit=batch_size)

            if not leads:
                result.status = PipelineStatus.EMPTY
                result.completed_at = datetime.now(UTC)
                logger.info("No leads to process")
                return result

            # Process each lead
            for lead in leads:
                result.total_processed += 1

                try:
                    await self._process_lead(lead, result)
                    result.successful += 1
                except Exception as e:
                    result.failed += 1
                    error_msg = f"Lead {lead.id} enrichment failed: {e}"
                    result.errors.append(error_msg)
                    logger.warning(error_msg)

            # Determine final status
            if result.failed > 0:
                result.status = PipelineStatus.INCOMPLETE
            else:
                result.status = PipelineStatus.COMPLETE

        except Exception as e:
            result.status = PipelineStatus.FAILED
            error_msg = f"Pipeline failed: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)

        result.completed_at = datetime.now(UTC)

        logger.info(
            f"Pipeline complete: {result.successful}/{result.total_processed} successful, "
            f"{result.qualified} qualified, {result.researching} researching, "
            f"{result.converted} converted"
        )

        return result

    async def enrich_single(self, lead_id: UUID) -> EnrichmentResult:
        """Enrich a single lead by ID.

        For manual enrichment trigger or re-enrichment.

        Args:
            lead_id: UUID of lead to enrich

        Returns:
            EnrichmentResult with gathered data

        Raises:
            LeadNotFoundError: If lead does not exist
        """
        # Fetch lead
        lead = await self._repository.get_by_id(lead_id)
        if not lead:
            raise LeadNotFoundError(lead_id)

        # Enrich
        enrichment_result = await self._enrichment_service.enrich_lead(lead)

        # Determine status
        is_existing = getattr(enrichment_result, "is_existing_customer", False)
        new_status = self._enrichment_service.determine_status(
            enrichment_result,
            is_existing_customer=is_existing,
        )

        # Format data for storage
        enrichment_data = self._enrichment_service.format_enrichment_data(
            enrichment_result
        )

        # Update lead
        await self._repository.update_enrichment(
            lead_id=lead_id,
            enrichment_data=enrichment_data,
            status=new_status,
            score=enrichment_result.lead_score or 0.0,
            enriched_at=datetime.now(UTC),
        )

        # Log activity
        await self._repository.add_activity(
            lead_id=lead_id,
            activity_type=ActivityType.ENRICHED,
            description=f"Lead enriched with confidence score {enrichment_result.confidence_score:.1f}",
            metadata={
                "confidence_score": enrichment_result.confidence_score,
                "lead_score": enrichment_result.lead_score,
                "new_status": new_status.value,
            },
        )

        return enrichment_result

    async def _process_lead(
        self,
        lead: Any,
        result: PipelineResult,
    ) -> None:
        """Process a single lead through enrichment.

        Args:
            lead: Lead to process
            result: Pipeline result to update statistics
        """
        # Enrich lead
        enrichment_result = await self._enrichment_service.enrich_lead(lead)

        # Determine status
        is_existing = getattr(enrichment_result, "is_existing_customer", False)
        new_status = self._enrichment_service.determine_status(
            enrichment_result,
            is_existing_customer=is_existing,
        )

        # Update statistics
        if new_status == LeadStatus.QUALIFIED:
            result.qualified += 1
        elif new_status == LeadStatus.RESEARCHING:
            result.researching += 1
        elif new_status == LeadStatus.CONVERTED:
            result.converted += 1

        # Format data for storage
        enrichment_data = self._enrichment_service.format_enrichment_data(
            enrichment_result
        )

        # Update lead record
        await self._repository.update_enrichment(
            lead_id=lead.id,
            enrichment_data=enrichment_data,
            status=new_status,
            score=enrichment_result.lead_score or 0.0,
            enriched_at=datetime.now(UTC),
        )

        # Log activity
        await self._repository.add_activity(
            lead_id=lead.id,
            activity_type=ActivityType.ENRICHED,
            description=f"Lead enriched with confidence score {enrichment_result.confidence_score:.1f}",
            metadata={
                "confidence_score": enrichment_result.confidence_score,
                "lead_score": enrichment_result.lead_score,
                "new_status": new_status.value,
            },
        )

        logger.debug(
            f"Lead {lead.id} enriched: status={new_status.value}, "
            f"confidence={enrichment_result.confidence_score:.1f}"
        )
