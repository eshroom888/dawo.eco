# Story 5.4: Gmail API Integration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want approved outreach drafts sent via Gmail API,
So that emails come from my business account with proper tracking.

---

## Acceptance Criteria

1. **Given** an outreach draft is approved
   **When** the Gmail sender executes
   **Then** it sends via configured Gmail API account
   **And** email includes: proper from address, subject line, body, signature
   **And** UTM parameters are added to any links for tracking

2. **Given** Gmail API credentials are configured
   **When** the sender authenticates
   **Then** it uses OAuth2 with refresh token
   **And** credentials are stored securely (not in code)
   **And** authentication failures trigger Discord alert

3. **Given** an email is sent successfully
   **When** send completes
   **Then** lead status changes to `CONTACTED`
   **And** send timestamp is recorded
   **And** email thread ID is captured for follow-up tracking

4. **Given** Gmail API fails
   **When** retry middleware exhausts attempts
   **Then** status changes to `SEND_FAILED`
   **And** operator is notified via Discord
   **And** draft remains approved for manual send or retry

5. **Given** rate limits apply
   **When** many emails are queued
   **Then** sends are spaced to respect Gmail limits (max 20/minute)
   **And** queue processes over time rather than bursting

---

## Tasks / Subtasks

- [x] Task 1: Create Gmail integration module structure (AC: #1, #2)
  - [x]1.1 Create `teams/dawo/leads/gmail/` directory
  - [x]1.2 Create `__init__.py` with complete `__all__` exports
  - [x]1.3 Create `schemas.py` with `GmailSendRequest`, `GmailSendResult`, `EmailMessage`, `SendQueueItem` dataclasses
  - [x]1.4 Create `config.py` with `GmailConfig`, `GmailRateLimitConfig` dataclasses

- [x] Task 2: Implement Gmail Credentials Manager (AC: #2)
  - [x]2.1 Create `credentials_manager.py` with `GmailCredentialsManager` class
  - [x]2.2 Accept `GmailConfig` via dependency injection (token path, credentials path, scopes)
  - [x]2.3 Implement `get_credentials() -> Credentials`:
        - Load token from `credentials/gmail_token.json`
        - Auto-refresh expired tokens using refresh_token
        - Return valid `google.oauth2.credentials.Credentials`
  - [x]2.4 Implement `is_authenticated() -> bool`:
        - Check token exists and is valid or refreshable
  - [x]2.5 Implement `refresh_if_needed() -> Credentials`:
        - Call `creds.refresh(Request())` when expired
        - Save updated token to file
  - [x]2.6 Handle credential errors:
        - Missing token file → raise `GmailAuthError`
        - Invalid/expired refresh token → raise `GmailAuthError`
        - All auth errors trigger Discord alert via injected `DiscordAlertManager`
  - [x]2.7 NEVER load credentials path from hardcoded strings - accept via `GmailConfig`

- [x] Task 3: Implement Gmail API Client (AC: #1, #3)
  - [x]3.1 Create `client.py` with `GmailClient` class
  - [x]3.2 Accept `GmailCredentialsManager` via dependency injection
  - [x]3.3 Implement `_build_service() -> Resource`:
        - Call `build('gmail', 'v1', credentials=creds)`
        - Cache service instance, rebuild on auth refresh
  - [x]3.4 Implement `send_message(message: EmailMessage) -> GmailSendResult`:
        - Construct MIME message from `EmailMessage`
        - Base64url-encode the message
        - Call `service.users().messages().send(userId='me', body={'raw': encoded})`
        - Return `GmailSendResult` with message_id and thread_id
  - [x]3.5 Implement `_construct_mime(message: EmailMessage) -> MIMEMultipart`:
        - Set From, To, Subject headers
        - Set body as plain text (MIMEText)
        - Add GDPR footer (unsubscribe, sender ID, company address)
  - [x]3.6 Wrap all API calls with retry middleware (`RetryMiddleware` from Story 1-5)
  - [x]3.7 Handle API errors: `HttpError` 401 (auth), 403 (quota), 429 (rate limit), 500 (server)

- [x] Task 4: Implement UTM Parameter Injection (AC: #1)
  - [x]4.1 Create `utm.py` with `UTMInjector` class
  - [x]4.2 Implement `inject_utm(body: str, lead_id: UUID, campaign: str) -> str`:
        - Find all URLs in email body using regex
        - Append UTM parameters: `utm_source=email`, `utm_medium=outreach`, `utm_campaign={campaign}`, `utm_content={lead_id}`
        - Preserve existing query parameters
  - [x]4.3 Implement `build_utm_params(lead_id: UUID, campaign: str) -> dict`:
        - Return standardized UTM parameter dict
  - [x]4.4 Handle edge cases: URLs with existing params, URLs in signatures, mailto: links

- [x] Task 5: Implement Email Signature Builder (AC: #1)
  - [x]5.1 Create `signature.py` with `SignatureBuilder` class
  - [x]5.2 Accept `GmailConfig` via injection for sender details
  - [x]5.3 Implement `build_signature() -> str`:
        - Sender name and role
        - Company name (DAWO / ImagoEco AS)
        - Company address (for CAN-SPAM/GDPR compliance)
        - Contact info
  - [x]5.4 Implement `build_gdpr_footer(unsubscribe_url: str) -> str`:
        - "Why you received this" explanation
        - One-click unsubscribe link
        - Company identity and address

- [x] Task 6: Implement GDPR Pre-Send Validation (AC: #1, #2)
  - [x]6.1 Create `gdpr_validator.py` with `GDPRPreSendValidator` class
  - [x]6.2 Accept `LeadRepository` via injection
  - [x]6.3 Implement `validate(lead: Lead) -> tuple[bool, str]`:
        - Check lead not unsubscribed (lead.unsubscribed_at is None)
        - Check lead not erasure-requested
        - Check business email (not personal email domains)
        - Check lead status allows sending (not LOST, not CONVERTED)
        - Check contact_count < MAX_OUTREACH_EMAILS (4)
        - Check minimum spacing since last_contacted_at (3 days)
  - [x]6.4 Define constants: `MAX_OUTREACH_EMAILS = 4`, `MIN_CONTACT_SPACING_DAYS = 3`
  - [x]6.5 Define `PERSONAL_EMAIL_DOMAINS`: gmail.com, yahoo.com, hotmail.com, outlook.com, etc.

- [x] Task 7: Implement Send Rate Limiter (AC: #5)
  - [x]7.1 Create `rate_limiter.py` with `GmailRateLimiter` class
  - [x]7.2 Accept `GmailRateLimitConfig` via injection (max_per_minute, burst_size)
  - [x]7.3 Implement `acquire() -> bool`:
        - Token bucket algorithm
        - Max 20 sends per minute (configurable)
        - Track send timestamps in memory
  - [x]7.4 Implement `wait_for_slot() -> float`:
        - Calculate delay until next available slot
        - Return seconds to wait
  - [x]7.5 Implement `get_stats() -> dict`:
        - Sends in last minute, sends today, remaining quota

- [x] Task 8: Implement Email Send Service (AC: #1, #2, #3, #4)
  - [x]8.1 Create `service.py` with `GmailSendService` class
  - [x]8.2 Accept all components via dependency injection:
        - `GmailClient`, `GDPRPreSendValidator`, `UTMInjector`
        - `SignatureBuilder`, `GmailRateLimiter`, `LeadRepository`
        - `DiscordAlertManager`
  - [x]8.3 Implement `send_outreach(lead: Lead, draft: OutreachDraft) -> GmailSendResult`:
        - GDPR pre-send validation
        - Inject UTM parameters into body
        - Append signature and GDPR footer
        - Rate limit check (wait if needed)
        - Send via GmailClient
        - On success: create OutreachEmail record, update lead status to CONTACTED
        - On failure: update to SEND_FAILED, alert Discord
  - [x]8.4 Implement `_create_email_record(lead: Lead, draft: OutreachDraft, result: GmailSendResult) -> OutreachEmail`:
        - Create OutreachEmail with gmail_message_id, gmail_thread_id, sent_at
        - Set status to SENT
  - [x]8.5 Implement `_update_lead_on_send(lead: Lead) -> None`:
        - Set status to CONTACTED
        - Set last_contacted_at to now
        - Increment contact_count
        - Add LeadActivity with type EMAIL_SENT
  - [x]8.6 Implement `_handle_send_failure(lead: Lead, error: Exception) -> None`:
        - Log error
        - Alert Discord with lead details and error
        - Do NOT change lead status (draft remains approved for retry)

- [x] Task 9: Implement Send Pipeline (AC: #1, #3, #5)
  - [x]9.1 Create `pipeline.py` with `GmailSendPipeline` class
  - [x]9.2 Accept `LeadRepository`, `GmailSendService` via injection
  - [x]9.3 Implement `execute(batch_size: int = 10) -> PipelineResult`:
        - Query approved outreach drafts (lead status = OUTREACH_PENDING, outreach_data.approved = true)
        - Process with rate limiting (respect 20/min)
        - Track results: sent, failed, skipped (GDPR), rate_limited
  - [x]9.4 Implement `send_single(lead_id: UUID) -> GmailSendResult`:
        - For manual send trigger after approval
  - [x]9.5 Handle graceful degradation:
        - Continue on individual send failure
        - Stop pipeline on auth failure (affects all sends)
        - Mark pipeline INCOMPLETE on critical errors

- [x] Task 10: Create Gmail Sender Agent (AC: #1, #5)
  - [x]10.1 Create `agent.py` with `GmailSenderAgent` class
  - [x]10.2 Inherit from BaseAgent pattern
  - [x]10.3 Implement `run() -> AgentResult`:
        - Execute send pipeline
        - Report statistics (sent, failed, rate_limited)
  - [x]10.4 Add scheduling support (every 30 minutes during business hours 8-17 Oslo time)
  - [x]10.5 Use tier="scan" (lightweight orchestration, no LLM needed)

- [x] Task 11: Update LeadRepository (AC: #3, #4)
  - [x]11.1 Add `get_approved_for_sending(limit: int) -> Sequence[Lead]`:
        - Query: status=OUTREACH_PENDING AND outreach_data contains approved draft
        - Order by outreach_data.suggested_send_time ASC
  - [x]11.2 Add `update_send_result(lead_id: UUID, gmail_message_id: str, gmail_thread_id: str) -> Lead`:
        - Set status=CONTACTED, last_contacted_at=now, increment contact_count
  - [x]11.3 Add `create_outreach_email(lead_id: UUID, email_data: dict) -> OutreachEmail`:
        - Create OutreachEmail record with all Gmail tracking fields
  - [x]11.4 Add `get_send_stats() -> dict`:
        - Count by status: OUTREACH_PENDING, CONTACTED, SEND_FAILED

- [x] Task 12: Add Gmail rate limit configuration (AC: #5)
  - [x]12.1 Add gmail section to `config/dawo_rate_limits.json`:
        - max_per_minute: 20
        - max_per_day: 500 (free Gmail limit)
        - burst_size: 5
        - business_hours: {start: 8, end: 17, timezone: "Europe/Oslo"}
  - [x]12.2 Update `core/config.py` with `GmailLimits` dataclass
  - [x]12.3 Load Gmail limits in `get_config()` function

- [x] Task 13: Register in team_spec.py (AC: #1)
  - [x]13.1 Add `GmailSenderAgent` as RegisteredAgent with tier="scan"
  - [x]13.2 Add `GmailClient` as RegisteredService
  - [x]13.3 Add `GmailCredentialsManager` as RegisteredService
  - [x]13.4 Add `GmailSendService` as RegisteredService with capability="email_send"
  - [x]13.5 Add `GmailSendPipeline` as RegisteredService
  - [x]13.6 Add `GDPRPreSendValidator` as RegisteredService
  - [x]13.7 Add `UTMInjector` as RegisteredService
  - [x]13.8 Add `SignatureBuilder` as RegisteredService
  - [x]13.9 Add `GmailRateLimiter` as RegisteredService

- [x] Task 14: Create comprehensive unit tests
  - [x]14.1 Test `GmailCredentialsManager` token loading and refresh (mocked)
  - [x]14.2 Test `GmailCredentialsManager` auth error handling
  - [x]14.3 Test `GmailClient` MIME construction
  - [x]14.4 Test `GmailClient` send with mocked Gmail API service
  - [x]14.5 Test `GmailClient` error handling (401, 403, 429, 500)
  - [x]14.6 Test `UTMInjector` parameter injection
  - [x]14.7 Test `UTMInjector` edge cases (existing params, mailto links)
  - [x]14.8 Test `SignatureBuilder` output format
  - [x]14.9 Test `GDPRPreSendValidator` all validation rules
  - [x]14.10 Test `GDPRPreSendValidator` personal email detection
  - [x]14.11 Test `GmailRateLimiter` token bucket algorithm
  - [x]14.12 Test `GmailRateLimiter` wait calculation
  - [x]14.13 Test `GmailSendService` full send flow (mocked)
  - [x]14.14 Test `GmailSendService` GDPR rejection
  - [x]14.15 Test `GmailSendService` failure handling
  - [x]14.16 Test `GmailSendPipeline` batch processing
  - [x]14.17 Test `GmailSendPipeline` auth failure stops pipeline
  - [x]14.18 Test `GmailSendPipeline` graceful degradation

- [x] Task 15: Create integration tests
  - [x]15.1 Test full send pipeline with mocked Gmail API
  - [x]15.2 Test lead status transitions (OUTREACH_PENDING -> CONTACTED)
  - [x]15.3 Test OutreachEmail record creation with Gmail tracking fields
  - [x]15.4 Test activity logging for sent emails
  - [x]15.5 Test GDPR validation integration with lead data
  - [x]15.6 Test rate limiting behavior across batch sends
  - [x]15.7 Test send failure does not change lead status (remains OUTREACH_PENDING)

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This story adds Gmail sending capability to the B2B Lead Pipeline from Stories 5-1 through 5-3. The Gmail module follows established patterns.

**Send Pipeline:**
```
[Approved Drafts (OUTREACH_PENDING)] → [GDPR Validator] → [UTM Injector]
               |                             |                    |
               v                             v                    v
        [Signature Builder] → [Rate Limiter] → [Gmail Client] → [Gmail API]
                                                     |
                                                     v
                                    [OutreachEmail record + Lead → CONTACTED]
                                                     |
                                            [On failure → Discord Alert]
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure]

```
teams/dawo/leads/
├── __init__.py                    # Add gmail exports
├── repository.py                  # EXTEND with send methods
├── scanner/                       # FROM Story 5-1 (unchanged)
├── enrichment/                    # FROM Story 5-2 (unchanged)
├── outreach/                      # FROM Story 5-3 (unchanged)
└── gmail/                         # CREATE THIS MODULE
    ├── __init__.py                # Export all public types
    ├── schemas.py                 # GmailSendRequest, GmailSendResult, EmailMessage
    ├── config.py                  # GmailConfig, GmailRateLimitConfig
    ├── credentials_manager.py     # GmailCredentialsManager
    ├── client.py                  # GmailClient (wraps google-api-python-client)
    ├── utm.py                     # UTMInjector
    ├── signature.py               # SignatureBuilder
    ├── gdpr_validator.py          # GDPRPreSendValidator
    ├── rate_limiter.py            # GmailRateLimiter
    ├── service.py                 # GmailSendService
    ├── pipeline.py                # GmailSendPipeline
    └── agent.py                   # GmailSenderAgent

tests/teams/dawo/test_leads/
└── test_gmail/                    # CREATE THIS
    ├── __init__.py
    ├── conftest.py                # Fixtures, mocks
    ├── test_schemas.py
    ├── test_config.py
    ├── test_credentials_manager.py
    ├── test_client.py
    ├── test_utm.py
    ├── test_signature.py
    ├── test_gdpr_validator.py
    ├── test_rate_limiter.py
    ├── test_service.py
    ├── test_pipeline.py
    └── test_integration.py
```

### Gmail API Integration Details

**Source:** [docs/research/gmail-api-setup.md]

**Dependencies (already in requirements.txt):**
```
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=1.0.0
```

**Credential files (already set up by eshroom):**
```
credentials/
├── gmail_credentials.json   # OAuth client ID (DO NOT COMMIT)
├── gmail_token.json         # Refresh token (DO NOT COMMIT)
└── .gitignore               # Already ignoring these
```

**Required scope:** `https://www.googleapis.com/auth/gmail.send`

**Core Google API imports:**
```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
```

**Sending flow:**
```python
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Construct MIME message
msg = MIMEMultipart()
msg['to'] = lead.email
msg['from'] = config.sender_email
msg['subject'] = draft.subject
msg.attach(MIMEText(body_with_signature, 'plain'))

# Encode and send
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
result = service.users().messages().send(
    userId='me',
    body={'raw': raw}
).execute()

# Result contains: {'id': 'message_id', 'threadId': 'thread_id', 'labelIds': [...]}
```

### Gmail API Rate Limits

**Source:** [docs/research/gmail-api-setup.md#Rate-Limits]

| Limit | Value | Strategy |
|-------|-------|----------|
| Daily sending (free Gmail) | 500 emails/day | Track daily count |
| Daily sending (Workspace) | 2,000 emails/day | Track daily count |
| Concurrent requests | 10 per user | Token bucket rate limiter |
| Suggested send rate | 20/minute | Space sends with 3s delay |
| Bandwidth limit | 128 MB/request | N/A (text emails) |

**Implementation:** Token bucket algorithm with 20 tokens/minute, burst of 5.

### Gmail API Error Handling

**Source:** [project-context.md#External-API-Calls], retry middleware

```python
# Error codes and handling strategy
GMAIL_ERROR_HANDLING = {
    401: "Auth expired - refresh token, retry once",
    403: "Quota exceeded - stop pipeline, alert Discord",
    429: "Rate limited - back off per Retry-After header",
    500: "Server error - retry with exponential backoff",
    503: "Service unavailable - retry with backoff",
}
```

**Critical:** On 401, attempt token refresh ONCE. If refresh fails, raise `GmailAuthError` and stop the entire pipeline (all sends would fail). On 403 quota exceeded, also stop pipeline and alert operator.

### GDPR Pre-Send Validation (CRITICAL)

**Source:** [docs/research/gdpr-b2b-outreach.md]

**Every email MUST pass these checks before sending:**

```python
class GDPRPreSendValidator:
    """GDPR compliance validator for outreach emails."""

    MAX_OUTREACH_EMAILS = 4        # Max emails per lead
    MIN_CONTACT_SPACING_DAYS = 3   # Min days between contacts

    PERSONAL_EMAIL_DOMAINS = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "live.com", "aol.com", "icloud.com", "me.com",
        "protonmail.com", "mail.com",
    }

    async def validate(self, lead: Lead) -> tuple[bool, str]:
        if lead.unsubscribed_at:
            return False, "Lead has unsubscribed"
        if lead.status == LeadStatus.LOST.value:
            return False, "Lead is marked as lost"
        if lead.status == LeadStatus.CONVERTED.value:
            return False, "Lead is already a customer"
        if lead.contact_count >= self.MAX_OUTREACH_EMAILS:
            return False, f"Max outreach limit reached ({self.MAX_OUTREACH_EMAILS})"
        if lead.last_contacted_at:
            days_since = (datetime.now(UTC) - lead.last_contacted_at).days
            if days_since < self.MIN_CONTACT_SPACING_DAYS:
                return False, f"Too soon since last contact ({days_since} days)"
        # Business email check
        domain = lead.email.split("@")[1].lower()
        if domain in self.PERSONAL_EMAIL_DOMAINS:
            return False, f"Personal email domain: {domain}"
        return True, "OK"
```

**Required email elements (GDPR + Norwegian Marketing Act):**
- Clear sender identification (DAWO / ImagoEco AS)
- Company address
- "Why you received this" explanation
- One-click unsubscribe mechanism
- Subject line must not be misleading

### Email Signature Template

**Source:** [docs/research/gdpr-b2b-outreach.md#Email-Template-Requirements]

```python
SIGNATURE_TEMPLATE = """
---
{sender_name}
{sender_role}
DAWO | ImagoEco AS
{company_address}
{contact_email}

---
Hvorfor mottok du denne e-posten?
Vi kontakter deg fordi vi mener DAWO-produktene kan vaere relevante for din virksomhet.

Ikke interessert? Svar pa denne e-posten med "avmeld" sa fjerner vi deg umiddelbart.
"""
```

### UTM Parameter Injection

**Source:** AC #1

```python
import re
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

class UTMInjector:
    """Inject UTM tracking parameters into email URLs."""

    URL_PATTERN = re.compile(r'https?://[^\s<>"\']+')

    def inject_utm(self, body: str, lead_id: UUID, campaign: str = "b2b_outreach") -> str:
        """Add UTM params to all URLs in email body."""
        def replace_url(match: re.Match) -> str:
            url = match.group(0)
            # Skip mailto: and unsubscribe links
            if url.startswith("mailto:"):
                return url
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            params.update({
                "utm_source": ["email"],
                "utm_medium": ["outreach"],
                "utm_campaign": [campaign],
                "utm_content": [str(lead_id)],
            })
            new_query = urlencode(params, doseq=True)
            return urlunparse(parsed._replace(query=new_query))

        return self.URL_PATTERN.sub(replace_url, body)
```

### Existing OutreachEmail Model (REUSE - DO NOT RECREATE)

**Source:** [core/leads/models.py]

The `OutreachEmail` model already exists with all needed fields:
```python
class OutreachEmail(Base):
    __tablename__ = "outreach_emails"
    id: UUID (PK)
    lead_id: UUID (FK -> leads.id)
    subject: str
    body: str
    template_id: Optional[str]
    status: str (EmailStatus enum)
    gmail_message_id: Optional[str]  # ← Fill on send
    gmail_thread_id: Optional[str]   # ← Fill on send
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]      # ← Fill on send
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]
    replied_at: Optional[datetime]
    bounce_reason: Optional[str]
    created_at: datetime
```

**EmailStatus enum values:** DRAFT, SCHEDULED, SENT, DELIVERED, OPENED, CLICKED, REPLIED, BOUNCED, UNSUBSCRIBED

### Existing Components to REUSE (DO NOT RECREATE)

**Source:** Stories 5-1, 5-2, 5-3, 1-5

```python
# Lead models and repository
from core.leads.models import Lead, LeadStatus, OutreachEmail, EmailStatus, LeadActivity, ActivityType
from teams.dawo.leads.repository import LeadRepository

# Outreach schemas (for draft data)
from teams.dawo.leads.outreach.schemas import OutreachDraft

# Retry middleware
from teams.dawo.middleware.retry import RetryMiddleware, RetryConfig, RetryResult
from teams.dawo.middleware.discord_alerts import DiscordAlertManager

# Config loading pattern
from core.config import get_config
```

### Retry Middleware Integration

**Source:** [teams/dawo/middleware/retry.py], Story 1-5

Wrap Gmail API calls with the existing `RetryMiddleware`:

```python
# In GmailClient
class GmailClient:
    def __init__(
        self,
        credentials_manager: GmailCredentialsManager,
        retry_config: Optional[RetryConfig] = None,
    ):
        self._creds_manager = credentials_manager
        self._retry = RetryMiddleware(retry_config or RetryConfig(
            max_retries=3,
            base_delay=2.0,
            timeout=30.0,
        ))

    async def send_message(self, message: EmailMessage) -> GmailSendResult:
        result = await self._retry.execute(
            self._do_send,
            message=message,
            context="gmail_send",
        )
        if result.is_incomplete:
            raise GmailSendError(f"Send failed after retries: {result.error}")
        return result.data
```

**Note:** The retry middleware's `execute()` returns `RetryResult` with `is_incomplete=True` on exhausted retries (never raises). Check `result.is_incomplete` and handle accordingly.

### Discord Alert Integration

**Source:** [teams/dawo/middleware/discord_alerts.py]

```python
# In GmailSendService
async def _handle_auth_failure(self, error: GmailAuthError) -> None:
    """Alert operator on Gmail auth failure."""
    await self._discord_alerts.send_alert(
        api_name="gmail",
        error=str(error),
        context={
            "action": "gmail_auth_refresh",
            "impact": "All email sends blocked",
            "resolution": "Re-authenticate Gmail API credentials",
        },
    )

async def _handle_send_failure(self, lead: Lead, error: Exception) -> None:
    """Alert operator on individual send failure."""
    await self._discord_alerts.send_alert(
        api_name="gmail",
        error=str(error),
        context={
            "action": "gmail_send",
            "lead_company": lead.company,
            "lead_email": lead.email,
            "resolution": "Retry manually or investigate error",
        },
    )
```

### Configuration Schema

**Source:** [project-context.md#Configuration-Loading], [core/config.py]

```python
# config.py
@dataclass(frozen=True)
class GmailConfig:
    """Gmail API configuration - loaded via injection."""
    token_path: str = "credentials/gmail_token.json"
    credentials_path: str = "credentials/gmail_credentials.json"
    scopes: list[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.send"
    ])
    sender_email: str = ""  # Loaded from env var
    sender_name: str = "DAWO Team"
    sender_role: str = "B2B Sales"
    company_name: str = "ImagoEco AS"
    company_address: str = ""  # Loaded from env var

@dataclass(frozen=True)
class GmailRateLimitConfig:
    """Rate limit configuration for Gmail sends."""
    max_per_minute: int = 20
    max_per_day: int = 500
    burst_size: int = 5
    business_hours_start: int = 8
    business_hours_end: int = 17
    timezone: str = "Europe/Oslo"
```

**Add to `config/dawo_rate_limits.json`:**
```json
{
  "gmail": {
    "max_per_minute": 20,
    "max_per_day": 500,
    "burst_size": 5,
    "business_hours": {
      "start": 8,
      "end": 17,
      "timezone": "Europe/Oslo"
    }
  }
}
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

The Gmail Sender Agent uses `tier="scan"` - this agent does NO LLM work, just orchestrates API calls.

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="gmail_sender_agent",
    agent_class=GmailSenderAgent,
    capabilities=["email_send", "gmail_integration"],
    tier="scan"  # Lightweight orchestration, no LLM needed
)
```

### Lead Status Transitions

**Source:** [core/leads/models.py]

```
OUTREACH_PENDING  →  CONTACTED (on successful send)
OUTREACH_PENDING  →  OUTREACH_PENDING (on send failure - stays for retry)
```

**Critical:** On send failure, do NOT change lead status. The draft remains approved and can be retried. Only change status to CONTACTED on successful send.

### Approval Queue Integration

**Source:** Story 5-3, Epic 4

The send pipeline queries leads where:
1. `status == OUTREACH_PENDING`
2. `outreach_data` contains an approved draft (set by approval queue from Story 5-3)

The approval flow is: Draft Generated → Submitted to Approval Queue → Operator Approves → Status remains OUTREACH_PENDING with `outreach_data.approved = true` → Gmail pipeline picks up and sends.

### Suggested Send Time Respect

**Source:** Story 5-3 `outreach_data.suggested_send_time`

The pipeline should respect the `suggested_send_time` field from Story 5-3:
- Only send if current time >= suggested_send_time
- Order queue by suggested_send_time ASC (earliest first)
- Only send during business hours (8-17 Oslo time)

### Testing Strategy

**Source:** Previous story patterns, 181 tests in Story 5-3

**Mock the Google API service:**
```python
# conftest.py
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_gmail_service():
    """Mock Google Gmail API service."""
    service = MagicMock()
    messages = MagicMock()
    service.users.return_value.messages.return_value = messages

    # Mock successful send
    messages.send.return_value.execute.return_value = {
        "id": "msg_123",
        "threadId": "thread_456",
        "labelIds": ["SENT"],
    }
    return service

@pytest.fixture
def mock_credentials():
    """Mock Gmail credentials."""
    creds = MagicMock(spec=Credentials)
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "refresh_token_123"
    return creds
```

**Test categories:**
- Credential management (load, refresh, error handling)
- MIME message construction (headers, body, signature, footer)
- UTM injection (URLs, edge cases, existing params)
- GDPR validation (all rules, edge cases)
- Rate limiting (token bucket, wait times)
- Send service (success flow, failure flow, GDPR rejection)
- Pipeline (batch processing, auth failure stops, graceful degradation)
- Integration (full flow, status transitions, activity logging)

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [5-3-personalized-outreach-draft-generator.md#Completion-Notes]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="scan"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(UTC)` not `datetime.utcnow()` |
| `activity_metadata` field naming | Use this field name for LeadActivity |
| Add logging to exception handlers | All exceptions logged before continuing |
| Graceful degradation | Pipeline continues on individual send failure |
| Protocol-based DI for tests | Service uses Protocol classes for dependency injection |
| TDD approach | Write tests first for each task |
| 181 tests benchmark from 5-3 | Aim for similar coverage (~100+ tests) |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER load config/credentials directly** - Accept via injection
2. **NEVER hardcode credential paths** - Use GmailConfig
3. **NEVER make API calls without retry wrapper** - Use RetryMiddleware
4. **NEVER use LLM model names** - Use tier system
5. **NEVER swallow exceptions without logging**
6. **NEVER send to personal email addresses** - GDPR violation
7. **NEVER send without GDPR footer** - Legal requirement
8. **NEVER exceed rate limits** - Use rate limiter
9. **NEVER change lead status on send failure** - Draft must remain for retry

### Google API Client Specifics

**Source:** Web research, [Gmail API Python Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)

**Important:** The `googleapiclient` library uses synchronous HTTP. For async compatibility:
```python
import asyncio

async def send_message(self, message: EmailMessage) -> GmailSendResult:
    """Send email via Gmail API (runs sync call in thread pool)."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        self._sync_send,
        message,
    )
    return result

def _sync_send(self, message: EmailMessage) -> GmailSendResult:
    """Synchronous Gmail API send (runs in executor)."""
    service = build('gmail', 'v1', credentials=self._get_creds())
    # ... construct and send
```

**Critical:** The `build()` call and `.execute()` are synchronous. Wrap in `asyncio.run_in_executor()` to avoid blocking the event loop.

### Project Structure Notes

- Follows unified project structure from Stories 5-1, 5-2, 5-3
- All modules under `teams/dawo/leads/gmail/`
- Tests mirror implementation structure in `tests/teams/dawo/test_leads/test_gmail/`
- Extends `core/config.py` with Gmail rate limit config
- Extends `config/dawo_rate_limits.json` with gmail section
- No new database migrations needed (OutreachEmail model already exists)

### References

- [Source: epics.md#Story-5.4] - Original story requirements
- [Source: docs/research/gmail-api-setup.md] - Gmail OAuth2 setup and credentials
- [Source: docs/research/gdpr-b2b-outreach.md] - GDPR compliance for B2B email
- [Source: core/leads/models.py] - Lead, OutreachEmail, EmailStatus models
- [Source: teams/dawo/leads/repository.py] - LeadRepository to extend
- [Source: teams/dawo/middleware/retry.py] - RetryMiddleware for API calls
- [Source: teams/dawo/middleware/discord_alerts.py] - Discord alerting
- [Source: core/config.py] - Configuration loading pattern
- [Source: config/dawo_rate_limits.json] - Rate limit config pattern
- [Source: 5-3-personalized-outreach-draft-generator.md] - Previous story patterns
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology
- [Source: Gmail API Python Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python) - Official docs
- [Source: Gmail API Sending Guide](https://developers.google.com/gmail/api/guides/sending) - Send email reference

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

N/A

### Completion Notes List

- All 15 tasks implemented following TDD red-green-refactor
- 128 total tests: 112 unit tests + 16 integration tests — all passing
- Pipeline fix: auth error detection from service result (service catches GmailAuthError and returns GmailSendResult; pipeline now detects "Auth error" in result.error and stops)
- GDPR compliance: personal email blocking, unsubscribe check, contact spacing (3 days), max outreach limit (4 emails)
- Rate limiter: token bucket algorithm with per-minute and daily limits
- All components follow DI pattern — no hardcoded paths, no direct config loading
- Agent uses tier="scan" — no LLM model names in code
- LeadRepository extended with 4 new Gmail send methods
- Pipeline graceful degradation: continues on individual failure, stops on auth failure

### File List

**New Files Created:**
- `teams/dawo/leads/gmail/__init__.py` — Module exports
- `teams/dawo/leads/gmail/schemas.py` — SendStatus, EmailMessage, GmailSendRequest, GmailSendResult, SendQueueItem
- `teams/dawo/leads/gmail/config.py` — GmailConfig, GmailRateLimitConfig
- `teams/dawo/leads/gmail/credentials_manager.py` — GmailCredentialsManager, GmailAuthError, DiscordAlertProtocol
- `teams/dawo/leads/gmail/client.py` — GmailClient, GmailSendError
- `teams/dawo/leads/gmail/utm.py` — UTMInjector
- `teams/dawo/leads/gmail/signature.py` — SignatureBuilder
- `teams/dawo/leads/gmail/gdpr_validator.py` — GDPRPreSendValidator
- `teams/dawo/leads/gmail/rate_limiter.py` — GmailRateLimiter
- `teams/dawo/leads/gmail/service.py` — GmailSendService
- `teams/dawo/leads/gmail/pipeline.py` — GmailSendPipeline, PipelineResult
- `teams/dawo/leads/gmail/agent.py` — GmailSenderAgent, AgentResult
- `tests/teams/dawo/test_leads/test_gmail/__init__.py`
- `tests/teams/dawo/test_leads/test_gmail/test_schemas.py` — 9 tests
- `tests/teams/dawo/test_leads/test_gmail/test_config.py` — 6 tests
- `tests/teams/dawo/test_leads/test_gmail/test_credentials_manager.py` — 9 tests
- `tests/teams/dawo/test_leads/test_gmail/test_client.py` — 13 tests (incl. HTTP 401/403/429/500)
- `tests/teams/dawo/test_leads/test_gmail/test_utm.py` — 9 tests
- `tests/teams/dawo/test_leads/test_gmail/test_signature.py` — 11 tests
- `tests/teams/dawo/test_leads/test_gmail/test_gdpr_validator.py` — 22 tests
- `tests/teams/dawo/test_leads/test_gmail/test_rate_limiter.py` — 11 tests
- `tests/teams/dawo/test_leads/test_gmail/test_service.py` — 9 tests
- `tests/teams/dawo/test_leads/test_gmail/test_pipeline.py` — 9 tests
- `tests/teams/dawo/test_leads/test_gmail/test_agent.py` — 4 tests
- `tests/integration/test_gmail_integration.py` — 16 integration tests
- `tests/teams/dawo/test_leads/test_gmail/conftest.py` — Shared fixtures

**Modified Files:**
- `teams/dawo/leads/repository.py` — Added get_approved_for_sending, update_send_result, create_outreach_email, get_send_stats
- `config/dawo_rate_limits.json` — Added gmail rate limit section
- `core/config.py` — Added GmailLimits dataclass
- `teams/dawo/team_spec.py` — Registered GmailSenderAgent + 8 services
- `core/publishing/events.py` — Added EMAIL_SENT event type
- `requirements.txt` — Added google-api-python-client, google-auth dependencies
