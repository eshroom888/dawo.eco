"""Gmail integration data schemas.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Defines data structures for the Gmail send pipeline:
- EmailMessage: MIME message representation
- GmailSendRequest: Send request with lead context
- GmailSendResult: Send operation result
- SendQueueItem: Queue item for batch processing
- SendStatus: Queue item status enum
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Optional
from uuid import UUID


class SendStatus(str, Enum):
    """Status of a send queue item.

    Values:
        PENDING: Queued, not yet attempted
        SENDING: Currently being sent
        SENT: Successfully sent
        FAILED: Send failed after retries
        RATE_LIMITED: Waiting for rate limit slot
        GDPR_REJECTED: Blocked by GDPR validation
    """

    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    GDPR_REJECTED = "gdpr_rejected"


@dataclass
class EmailMessage:
    """Email message for MIME construction.

    Represents the content of an email to be sent via Gmail API.

    Attributes:
        to: Recipient email address
        from_email: Sender email address
        subject: Email subject line
        body: Email body (plain text)
        reply_to: Optional reply-to address
        cc: Optional CC address
    """

    to: str
    from_email: str
    subject: str
    body: str
    reply_to: Optional[str] = None
    cc: Optional[str] = None


@dataclass
class GmailSendRequest:
    """Request to send an outreach email via Gmail.

    Bundles the email message with lead context for tracking.

    Attributes:
        lead_id: UUID of the target lead
        message: Email message to send
        campaign: Campaign identifier for UTM tracking
    """

    lead_id: UUID
    message: EmailMessage
    campaign: str = "b2b_outreach"


@dataclass
class GmailSendResult:
    """Result of a Gmail send operation.

    Attributes:
        success: Whether the send succeeded
        message_id: Gmail message ID (on success)
        thread_id: Gmail thread ID (on success)
        error: Error message (on failure)
        sent_at: Timestamp of successful send
    """

    success: bool
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: Optional[datetime] = None


@dataclass
class SendQueueItem:
    """Item in the send queue for batch processing.

    Attributes:
        lead_id: UUID of the target lead
        subject: Email subject
        body: Email body
        to_email: Recipient email
        campaign: Campaign identifier
        status: Current queue status
        created_at: When item was queued
    """

    lead_id: UUID
    subject: str
    body: str
    to_email: str
    campaign: str
    status: SendStatus = SendStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "SendStatus",
    "EmailMessage",
    "GmailSendRequest",
    "GmailSendResult",
    "SendQueueItem",
]
