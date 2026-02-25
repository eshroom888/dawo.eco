"""Gmail integration configuration.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Configuration dataclasses for Gmail API integration.
All config is injected via constructor — NEVER load files directly.

Attributes:
    GmailConfig: Gmail API credentials and sender details
    GmailRateLimitConfig: Rate limiting configuration
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GmailConfig:
    """Gmail API configuration — loaded via injection.

    Attributes:
        token_path: Path to OAuth2 token JSON file
        credentials_path: Path to OAuth2 client credentials JSON file
        scopes: Gmail API OAuth2 scopes
        sender_email: From address (loaded from env var)
        sender_name: Sender display name
        sender_role: Sender role/title
        company_name: Company legal name
        company_address: Company physical address (GDPR requirement)
    """

    token_path: str = "credentials/gmail_token.json"
    credentials_path: str = "credentials/gmail_credentials.json"
    scopes: list[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.send"
    ])
    sender_email: str = ""
    sender_name: str = "DAWO Team"
    sender_role: str = "B2B Sales"
    company_name: str = "ImagoEco AS"
    company_address: str = ""


@dataclass(frozen=True)
class GmailRateLimitConfig:
    """Rate limit configuration for Gmail sends.

    Attributes:
        max_per_minute: Maximum sends per minute (Gmail limit: 20)
        max_per_day: Maximum sends per day (free Gmail: 500)
        burst_size: Maximum burst before throttling
        business_hours_start: Start of business hours (24h format)
        business_hours_end: End of business hours (24h format)
        timezone: Timezone for business hours
    """

    max_per_minute: int = 20
    max_per_day: int = 500
    burst_size: int = 5
    business_hours_start: int = 8
    business_hours_end: int = 17
    timezone: str = "Europe/Oslo"


__all__ = [
    "GmailConfig",
    "GmailRateLimitConfig",
]
