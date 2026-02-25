"""Outreach Pipeline for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides batch processing for outreach generation:
- OutreachPipeline: Batch processing of qualified leads
- PipelineResult: Result of pipeline execution

Accepts all dependencies via constructor injection.
NEVER loads config files directly.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Protocol
from uuid import UUID

from teams.dawo.leads.outreach.schemas import (
    GenerationResult,
    GenerationStatus,
)
from core.leads.models import LeadStatus
from teams.dawo.leads.outreach.config import DEFAULT_BATCH_SIZE


logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of pipeline execution.

    Attributes:
        status: Pipeline status (COMPLETE, INCOMPLETE, FAILED)
        total_processed: Total number of leads processed
        successful: Number of successful generations
        failed: Number of failed generations
        errors: List of error details
        started_at: Pipeline start timestamp
        completed_at: Pipeline completion timestamp
    """

    status: str
    total_processed: int
    successful: int
    failed: int
    errors: list[dict] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSONB storage."""
        return {
            "status": self.status,
            "total_processed": self.total_processed,
            "successful": self.successful,
            "failed": self.failed,
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class LeadRepositoryProtocol(Protocol):
    """Protocol for lead repository."""

    async def get_leads_for_outreach(self, limit: int) -> list[Any]:
        """Get leads qualified for outreach."""
        ...

    async def get_by_id(self, lead_id: UUID) -> Any | None:
        """Get lead by ID."""
        ...

    async def update_outreach(self, lead_id: UUID, outreach_data: dict, status: str) -> Any:
        """Update lead with outreach data."""
        ...


class OutreachServiceProtocol(Protocol):
    """Protocol for outreach service."""

    async def generate_outreach(self, lead: Any) -> GenerationResult:
        """Generate outreach for a lead."""
        ...

    def is_qualified_for_outreach(self, lead: Any) -> bool:
        """Check if lead is qualified for outreach."""
        ...

    def prepare_for_approval(self, draft: Any, lead: Any) -> dict:
        """Prepare draft for approval queue."""
        ...


class OutreachPipeline:
    """Pipeline for batch processing outreach generation.

    Processes qualified leads in batches, generating personalized
    outreach drafts for each lead.

    Accepts all dependencies via constructor injection.
    NEVER loads config files directly.

    Attributes:
        _lead_repository: Repository for lead data access
        _outreach_service: Service for outreach generation
    """

    def __init__(
        self,
        lead_repository: LeadRepositoryProtocol,
        outreach_service: OutreachServiceProtocol,
    ) -> None:
        """Initialize OutreachPipeline with dependencies.

        Args:
            lead_repository: Repository for lead data access
            outreach_service: Service for outreach generation
        """
        self._lead_repository = lead_repository
        self._outreach_service = outreach_service

    async def execute(self, batch_size: int = DEFAULT_BATCH_SIZE) -> PipelineResult:
        """Execute outreach pipeline for a batch of qualified leads.

        Queries for qualified leads and processes them in batches,
        generating personalized outreach drafts.

        Args:
            batch_size: Maximum number of leads to process

        Returns:
            PipelineResult with processing statistics
        """
        started_at = datetime.now(UTC)
        successful = 0
        failed = 0
        errors: list[dict] = []

        logger.info(
            "Starting outreach pipeline",
            extra={"batch_size": batch_size},
        )

        # Query qualified leads
        leads = await self._lead_repository.get_leads_for_outreach(limit=batch_size)
        total = len(leads)

        logger.info(
            "Found leads for outreach",
            extra={"count": total},
        )

        # Process each lead
        for lead in leads:
            try:
                result = await self._outreach_service.generate_outreach(lead)

                if result.status == GenerationStatus.SUCCESS:
                    # Persist outreach data and update status to OUTREACH_PENDING
                    if result.draft:
                        await self._lead_repository.update_outreach(
                            lead_id=lead.id,
                            outreach_data=result.draft.to_dict(),
                            status=LeadStatus.OUTREACH_PENDING,
                        )
                    successful += 1
                    logger.info(
                        "Outreach generated and persisted",
                        extra={"lead_id": str(lead.id)},
                    )
                else:
                    failed += 1
                    errors.append({
                        "lead_id": str(lead.id),
                        "error": result.error or "Unknown error",
                        "status": result.status.value,
                    })
                    logger.warning(
                        "Outreach generation failed",
                        extra={
                            "lead_id": str(lead.id),
                            "error": result.error,
                        },
                    )

            except Exception as e:
                failed += 1
                errors.append({
                    "lead_id": str(lead.id),
                    "error": str(e),
                    "status": "exception",
                })
                logger.exception(
                    "Exception during outreach generation",
                    extra={"lead_id": str(lead.id)},
                )

        # Determine pipeline status
        if failed == 0:
            status = "COMPLETE"
        elif successful == 0:
            status = "FAILED"
        else:
            status = "INCOMPLETE"

        completed_at = datetime.now(UTC)

        logger.info(
            "Outreach pipeline completed",
            extra={
                "status": status,
                "total": total,
                "successful": successful,
                "failed": failed,
            },
        )

        return PipelineResult(
            status=status,
            total_processed=total,
            successful=successful,
            failed=failed,
            errors=errors,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def generate_single(self, lead_id: UUID) -> GenerationResult:
        """Generate outreach for a single lead.

        For manual draft trigger, bypasses batch processing.

        Args:
            lead_id: UUID of the lead to generate outreach for

        Returns:
            GenerationResult for the lead
        """
        logger.info(
            "Generating single outreach",
            extra={"lead_id": str(lead_id)},
        )

        # Get lead from repository
        lead = await self._lead_repository.get_by_id(lead_id)

        if lead is None:
            logger.warning(
                "Lead not found for single outreach",
                extra={"lead_id": str(lead_id)},
            )
            return GenerationResult(
                lead_id=lead_id,
                status=GenerationStatus.FAILED,
                draft=None,
                template_selection=None,
                error=f"Lead not found: {lead_id}",
            )

        # Generate outreach
        result = await self._outreach_service.generate_outreach(lead)

        # Persist outreach data on success
        if result.status == GenerationStatus.SUCCESS and result.draft:
            await self._lead_repository.update_outreach(
                lead_id=lead_id,
                outreach_data=result.draft.to_dict(),
                status=LeadStatus.OUTREACH_PENDING,
            )

        logger.info(
            "Single outreach generation completed",
            extra={
                "lead_id": str(lead_id),
                "status": result.status.value,
            },
        )

        return result
