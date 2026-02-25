"""Gmail Email Send Service.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Orchestrates the full send flow: GDPR validation, UTM injection,
signature, rate limiting, send, status tracking, and error handling.
"""

import asyncio
import logging
from datetime import datetime, UTC
from typing import Optional, Protocol, runtime_checkable
from uuid import UUID

from core.leads.models import Lead, LeadStatus, ActivityType, EmailStatus, OutreachEmail
from teams.dawo.leads.gmail.client import GmailClient, GmailSendError
from teams.dawo.leads.gmail.credentials_manager import (
    GmailAuthError,
    DiscordAlertProtocol,
)
from teams.dawo.leads.gmail.gdpr_validator import GDPRPreSendValidator
from teams.dawo.leads.gmail.rate_limiter import GmailRateLimiter
from teams.dawo.leads.gmail.schemas import EmailMessage, GmailSendResult
from teams.dawo.leads.gmail.signature import SignatureBuilder
from teams.dawo.leads.gmail.utm import UTMInjector
from teams.dawo.leads.gmail.config import GmailConfig

logger = logging.getLogger(__name__)


@runtime_checkable
class LeadRepositoryProtocol(Protocol):
    """Protocol for LeadRepository dependency injection."""

    async def get_lead_by_id(self, lead_id: UUID) -> Optional[Lead]: ...
    async def update_send_result(self, lead_id: UUID, gmail_message_id: str, gmail_thread_id: str) -> Optional[Lead]: ...
    async def create_outreach_email(self, lead_id: UUID, email_data: dict) -> OutreachEmail: ...
    async def add_activity(self, lead_id: UUID, activity_type: ActivityType, description: str, metadata: Optional[dict] = None): ...


class GmailSendService:
    """Orchestrates the Gmail email send flow.

    Performs GDPR validation, UTM injection, signature attachment,
    rate limiting, sending, and status tracking for outreach emails.

    All dependencies are injected via constructor.
    """

    def __init__(
        self,
        gmail_client: GmailClient,
        gdpr_validator: GDPRPreSendValidator,
        utm_injector: UTMInjector,
        signature_builder: SignatureBuilder,
        rate_limiter: GmailRateLimiter,
        lead_repository: LeadRepositoryProtocol,
        discord_alerts: DiscordAlertProtocol,
        config: GmailConfig,
    ) -> None:
        """Initialize send service with all dependencies.

        Args:
            gmail_client: Gmail API client
            gdpr_validator: GDPR pre-send validator
            utm_injector: UTM parameter injector
            signature_builder: Email signature builder
            rate_limiter: Rate limiter
            lead_repository: Lead repository for status updates
            discord_alerts: Discord alert manager
            config: Gmail configuration
        """
        self._client = gmail_client
        self._gdpr = gdpr_validator
        self._utm = utm_injector
        self._signature = signature_builder
        self._rate_limiter = rate_limiter
        self._repo = lead_repository
        self._discord = discord_alerts
        self._config = config

    async def send_outreach(
        self,
        lead: Lead,
        subject: str,
        body: str,
        campaign: str = "b2b_outreach",
    ) -> GmailSendResult:
        """Send outreach email to a lead.

        Full pipeline: GDPR check -> UTM inject -> Signature -> Rate limit -> Send -> Track.

        Args:
            lead: Target lead
            subject: Email subject
            body: Email body (from approved draft)
            campaign: Campaign identifier for UTM

        Returns:
            GmailSendResult with success/failure details
        """
        # GDPR pre-send validation
        is_valid, reason = self._gdpr.validate(lead)
        if not is_valid:
            logger.info(f"GDPR rejected send to {lead.email}: {reason}")
            return GmailSendResult(success=False, error=f"GDPR: {reason}")

        # Inject UTM parameters
        body_with_utm = self._utm.inject_utm(body, lead.id, campaign)

        # Append signature and GDPR footer
        full_body = body_with_utm + self._signature.build_full_footer()

        # Rate limit check
        if not self._rate_limiter.acquire():
            wait_time = self._rate_limiter.wait_for_slot()
            logger.info(f"Rate limited, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            if not self._rate_limiter.acquire():
                return GmailSendResult(
                    success=False, error="Rate limit exceeded"
                )

        # Construct email
        message = EmailMessage(
            to=lead.email,
            from_email=self._config.sender_email,
            subject=subject,
            body=full_body,
        )

        # Send
        try:
            result = await self._client.send_message(message)
        except GmailAuthError as e:
            logger.error(f"Gmail auth error sending to {lead.email}: {e}")
            await self._handle_auth_failure(e)
            return GmailSendResult(success=False, error=f"Auth error: {e}")
        except GmailSendError as e:
            logger.error(f"Gmail send error to {lead.email}: {e}")
            await self._handle_send_failure(lead, e)
            return GmailSendResult(success=False, error=str(e))

        # Track success
        await self._update_lead_on_send(lead, result, subject, full_body)
        return result

    async def _update_lead_on_send(
        self,
        lead: Lead,
        result: GmailSendResult,
        subject: str = "",
        body: str = "",
    ) -> None:
        """Update lead status, create OutreachEmail record, and log activity.

        Updates contact_count, last_contacted_at, and status via
        update_send_result. Creates OutreachEmail record for tracking.

        Args:
            lead: Lead that was sent to
            result: Gmail send result
            subject: Email subject for OutreachEmail record
            body: Email body for OutreachEmail record
        """
        try:
            # Update lead: status -> CONTACTED, increment contact_count,
            # set last_contacted_at (handled by update_send_result)
            await self._repo.update_send_result(
                lead.id,
                gmail_message_id=result.message_id or "",
                gmail_thread_id=result.thread_id or "",
            )

            # Create OutreachEmail record for follow-up tracking
            await self._repo.create_outreach_email(
                lead_id=lead.id,
                email_data={
                    "subject": subject,
                    "body": body,
                    "gmail_message_id": result.message_id,
                    "gmail_thread_id": result.thread_id,
                    "sent_at": result.sent_at,
                    "status": EmailStatus.SENT.value,
                },
            )
        except Exception as e:
            logger.error(f"Failed to update lead {lead.id} after send: {e}")

    async def _handle_auth_failure(self, error: GmailAuthError) -> None:
        """Alert operator on Gmail auth failure.

        Args:
            error: Authentication error
        """
        try:
            await self._discord.send_api_error_alert(
                api_name="gmail",
                error=str(error),
                attempts=1,
                queued_for_retry=False,
            )
        except Exception as e:
            logger.warning(f"Failed to send Discord auth alert: {e}")

    async def _handle_send_failure(
        self, lead: Lead, error: Exception
    ) -> None:
        """Alert operator on individual send failure.

        Does NOT change lead status -- draft remains approved for retry.

        Args:
            lead: Lead that failed to send
            error: Send error
        """
        try:
            await self._discord.send_api_error_alert(
                api_name="gmail",
                error=str(error),
                attempts=1,
                queued_for_retry=False,
            )
        except Exception as e:
            logger.warning(f"Failed to send Discord send failure alert: {e}")


__all__ = [
    "GmailSendService",
    "LeadRepositoryProtocol",
]
