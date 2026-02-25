"""Gmail integration module for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Provides Gmail API sending capability for approved outreach drafts:
- OAuth2 credential management
- MIME message construction and sending
- UTM parameter injection for tracking
- GDPR pre-send validation
- Rate limiting (20/min, 500/day)
- Email signature and GDPR footer
- Send pipeline for batch processing
- Agent for scheduled execution

Exports:
    Schemas:
        - EmailMessage, GmailSendRequest, GmailSendResult
        - SendQueueItem, SendStatus

    Config:
        - GmailConfig, GmailRateLimitConfig

    Credentials:
        - GmailCredentialsManager, GmailAuthError, DiscordAlertProtocol

    Client:
        - GmailClient, GmailSendError

    Utilities:
        - UTMInjector, SignatureBuilder, GDPRPreSendValidator
        - GmailRateLimiter

    Service:
        - GmailSendService

    Pipeline:
        - GmailSendPipeline, PipelineResult

    Agent:
        - GmailSenderAgent, AgentResult
"""

from teams.dawo.leads.gmail.schemas import (
    SendStatus,
    EmailMessage,
    GmailSendRequest,
    GmailSendResult,
    SendQueueItem,
)

from teams.dawo.leads.gmail.config import (
    GmailConfig,
    GmailRateLimitConfig,
)

from teams.dawo.leads.gmail.credentials_manager import (
    GmailCredentialsManager,
    GmailAuthError,
    DiscordAlertProtocol,
)

from teams.dawo.leads.gmail.client import (
    GmailClient,
    GmailSendError,
)

from teams.dawo.leads.gmail.utm import UTMInjector
from teams.dawo.leads.gmail.signature import SignatureBuilder
from teams.dawo.leads.gmail.gdpr_validator import (
    GDPRPreSendValidator,
    MAX_OUTREACH_EMAILS,
    MIN_CONTACT_SPACING_DAYS,
    PERSONAL_EMAIL_DOMAINS,
)
from teams.dawo.leads.gmail.rate_limiter import GmailRateLimiter

from teams.dawo.leads.gmail.service import GmailSendService

from teams.dawo.leads.gmail.pipeline import (
    GmailSendPipeline,
    PipelineResult,
)

from teams.dawo.leads.gmail.agent import (
    GmailSenderAgent,
    AgentResult,
)


__all__ = [
    # Schemas
    "SendStatus",
    "EmailMessage",
    "GmailSendRequest",
    "GmailSendResult",
    "SendQueueItem",
    # Config
    "GmailConfig",
    "GmailRateLimitConfig",
    # Credentials
    "GmailCredentialsManager",
    "GmailAuthError",
    "DiscordAlertProtocol",
    # Client
    "GmailClient",
    "GmailSendError",
    # Utilities
    "UTMInjector",
    "SignatureBuilder",
    "GDPRPreSendValidator",
    "MAX_OUTREACH_EMAILS",
    "MIN_CONTACT_SPACING_DAYS",
    "PERSONAL_EMAIL_DOMAINS",
    "GmailRateLimiter",
    # Service
    "GmailSendService",
    # Pipeline
    "GmailSendPipeline",
    "PipelineResult",
    # Agent
    "GmailSenderAgent",
    "AgentResult",
]
