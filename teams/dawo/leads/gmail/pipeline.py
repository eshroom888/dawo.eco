"""Gmail Send Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Batch processing pipeline for approved outreach emails.
Queries approved drafts and sends with rate limiting.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional, Protocol, Sequence, runtime_checkable
from uuid import UUID

from core.leads.models import Lead
from teams.dawo.leads.gmail.credentials_manager import GmailAuthError
from teams.dawo.leads.gmail.schemas import GmailSendResult
from teams.dawo.leads.gmail.service import GmailSendService

logger = logging.getLogger(__name__)


@runtime_checkable
class PipelineLeadRepositoryProtocol(Protocol):
    """Protocol for pipeline's lead repository needs."""

    async def get_approved_for_sending(self, limit: int) -> Sequence[Lead]: ...
    async def get_lead_by_id(self, lead_id: UUID) -> Optional[Lead]: ...


@dataclass
class PipelineResult:
    """Result of a pipeline execution.

    Attributes:
        sent: Number of emails successfully sent
        failed: Number of failed sends
        skipped_gdpr: Number of leads skipped by GDPR validation
        rate_limited: Number of sends delayed by rate limiter
        total_processed: Total leads processed
        started_at: Pipeline start time
        completed_at: Pipeline completion time
        is_complete: True if pipeline finished normally
        error: Pipeline-level error (if any)
    """

    sent: int = 0
    failed: int = 0
    skipped_gdpr: int = 0
    rate_limited: int = 0
    total_processed: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    is_complete: bool = True
    error: Optional[str] = None


class GmailSendPipeline:
    """Batch send pipeline for approved outreach emails.

    Queries leads with approved outreach drafts and sends emails
    via GmailSendService with rate limiting and error handling.

    Graceful degradation:
    - Individual send failures don't stop the pipeline
    - Auth failures stop the pipeline (all sends would fail)
    """

    def __init__(
        self,
        lead_repository: PipelineLeadRepositoryProtocol,
        send_service: GmailSendService,
    ) -> None:
        """Initialize pipeline.

        Args:
            lead_repository: Repository for querying approved leads
            send_service: Email send service
        """
        self._repo = lead_repository
        self._service = send_service

    async def execute(self, batch_size: int = 10) -> PipelineResult:
        """Execute the send pipeline.

        Queries approved outreach drafts and sends with rate limiting.

        Args:
            batch_size: Maximum leads to process in this batch

        Returns:
            PipelineResult with send statistics
        """
        result = PipelineResult()

        try:
            leads = await self._repo.get_approved_for_sending(limit=batch_size)
        except Exception as e:
            logger.error(f"Failed to query approved leads: {e}")
            result.is_complete = False
            result.error = f"Query failed: {e}"
            result.completed_at = datetime.now(UTC)
            return result

        for lead in leads:
            result.total_processed += 1

            try:
                # Extract draft from outreach_data
                outreach_data = lead.outreach_data or {}
                draft_data = outreach_data.get("draft", {})
                subject = draft_data.get("subject", "")
                body = draft_data.get("body", "")

                if not subject or not body:
                    logger.warning(f"Lead {lead.id} has empty draft, skipping")
                    result.failed += 1
                    continue

                send_result = await self._service.send_outreach(
                    lead=lead,
                    subject=subject,
                    body=body,
                )

                if send_result.success:
                    result.sent += 1
                elif send_result.error and "GDPR" in send_result.error:
                    result.skipped_gdpr += 1
                elif send_result.error and "Rate limit" in send_result.error:
                    result.rate_limited += 1
                elif send_result.error and "Auth error" in send_result.error:
                    # Auth failure stops the entire pipeline
                    logger.error(f"Auth failure stops pipeline: {send_result.error}")
                    result.is_complete = False
                    result.error = f"Auth failure: {send_result.error}"
                    result.failed += 1
                    break
                else:
                    result.failed += 1

            except GmailAuthError as e:
                # Auth failure stops the entire pipeline
                logger.error(f"Auth failure stops pipeline: {e}")
                result.is_complete = False
                result.error = f"Auth failure: {e}"
                result.failed += 1
                break

            except Exception as e:
                # Individual send failure — continue with next lead
                logger.error(f"Send failed for lead {lead.id}: {e}")
                result.failed += 1
                continue

        result.completed_at = datetime.now(UTC)
        logger.info(
            f"Pipeline complete: {result.sent} sent, {result.failed} failed, "
            f"{result.skipped_gdpr} GDPR skipped"
        )
        return result

    async def send_single(self, lead_id: UUID) -> GmailSendResult:
        """Send a single outreach email by lead ID.

        For manual send trigger after approval.

        Args:
            lead_id: Lead UUID to send to

        Returns:
            GmailSendResult

        Raises:
            ValueError: If lead not found or no approved draft
        """
        lead = await self._repo.get_lead_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead not found: {lead_id}")

        outreach_data = lead.outreach_data or {}
        draft_data = outreach_data.get("draft", {})
        subject = draft_data.get("subject", "")
        body = draft_data.get("body", "")

        if not subject or not body:
            raise ValueError(f"Lead {lead_id} has no approved draft")

        return await self._service.send_outreach(
            lead=lead,
            subject=subject,
            body=body,
        )


__all__ = [
    "GmailSendPipeline",
    "PipelineResult",
    "PipelineLeadRepositoryProtocol",
]
