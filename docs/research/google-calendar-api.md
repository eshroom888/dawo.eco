# Google Calendar API Integration Research

**Date:** 2026-02-25 (Updated)
**Epic:** 7 - Analytics & System Operations
**Stories:** 7-9 (Google Calendar Sync)

## Summary

Google Calendar API v3 integration follows the exact same patterns as the existing Gmail API integration (Story 5-4). Same libraries, same `asyncio.run_in_executor()` wrapping, same credential management. No new dependencies needed. This document provides comprehensive implementation details for Python developers.

## Package Versions (2026)

### Latest Stable Releases
- `google-api-python-client==2.190.0` (released Feb 2026, weekly updates)
- `google-auth==2.48.0` (released Jan 26, 2026)
- `google-auth-oauthlib==1.2.4` (released Jan 15, 2026)

### Installation
```bash
pip install google-api-python-client google-auth google-auth-oauthlib
```

All packages already present in `requirements.txt` (Story 3.2). Python 3.7-3.14 fully supported.

### Key Improvement in v2.x
Discovery documents are now cached in the library rather than fetched dynamically (substantial reliability improvement). **Highly recommended to stay on v2.x**.

## OAuth2 Flow: Service Account vs User Consent

### Decision: User Consent OAuth2 (Installed Application Flow)

For a **single-operator system** (DAWO.ECO), use **OAuth2 user consent** with `InstalledAppFlow`, NOT service accounts.

| Factor | Service Account | User Consent OAuth2 |
|--------|----------------|---------------------|
| **Best for** | Server-to-server (no user), domain-wide delegation | Single user, installed apps, desktop tools |
| **Calendar access** | Own calendars only (limited utility) | Full access to user's Google Calendar |
| **Setup complexity** | Requires domain admin + delegation setup | Simple OAuth consent screen + credentials |
| **Token management** | Service account key file | Access token + refresh token (auto-renewed) |
| **DAWO.ECO fit** | Poor (no user calendar access) | **Excellent** (single operator, full access) |

### OAuth2 Flow Pattern (Reuse Gmail Pattern from Story 5-4)

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os

SCOPES = ['https://www.googleapis.com/auth/calendar']

creds = None
if os.path.exists('calendar_token.json'):
    creds = Credentials.from_authorized_user_file('calendar_token.json', SCOPES)

# If credentials expired but have refresh token, refresh them
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
# Otherwise, run OAuth flow
else:
    flow = InstalledAppFlow.from_client_secrets_file('gmail_credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

# Save credentials for next run
with open('calendar_token.json', 'w') as token:
    token.write(creds.to_json())
```

### Token Strategy

**Separate token files**:
- Gmail: `credentials/gmail_token.json`
- Calendar: `credentials/calendar_token.json`

**Same OAuth client**: Reuse `credentials/gmail_credentials.json` (same Google Cloud project).

**Why separate tokens?** Prevents breaking Gmail integration if Calendar scope is revoked. Each token can be independently refreshed/revoked.

### Token Storage Best Practices

1. **Automatic refresh**: Check `creds.expired` and `creds.refresh_token` before each session
2. **Secure storage**: Store tokens in `credentials/` directory with `.gitignore` protection
3. **Production**: Use Secret Vault with enterprise-grade encryption (future enhancement)
4. **Incremental authorization**: Request scopes at time of access (already done -- Gmail and Calendar are separate)

### Token Expiration Handling

```python
# Pattern from Google's official quickstart
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
elif not creds or not creds.valid:
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    # Save token
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
```

**Critical**: Always implement token refresh logic. Tokens expire regularly, and refresh tokens remain valid until revoked. Never prompt user for re-auth if refresh token exists.

## OAuth Scopes

### Full Calendar Management (Recommended)
```
https://www.googleapis.com/auth/calendar
```
Provides read/write access to calendars and events. Required for Story 7-9 operations.

### Alternative Scopes (If Narrower Access Needed)
| Scope | Access Level |
|-------|--------------|
| `calendar.readonly` | Read-only access to all calendars |
| `calendar.events` | Read/write events only (not calendar creation) |
| `calendar.calendarlist` | Manage calendar list (not events) |

**Best practice**: Use the most narrowly focused scope possible. For DAWO.ECO (creating calendars + managing events), use full `calendar` scope.

### Scope Verification

To verify current token scopes:
```bash
curl "https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}"
```
Check `scope` field in response.

## Key Calendar API Operations

### 1. Create Calendar (for "DAWO Content Schedule")

```python
calendar = {
    'summary': 'DAWO Content Schedule',
    'timeZone': 'Europe/Oslo',
    'description': 'Automated content publishing schedule for DAWO.ECO'
}

created_calendar = service.calendars().insert(body=calendar).execute()
calendar_id = created_calendar['id']  # Store this in database
```

**Critical**: Store returned `calendar_id` in database. No "get by name" API exists. Must use ID for all subsequent operations.

### 2. Create Event

```python
event = {
    'summary': 'Publish: Omega-3 Health Benefits',
    'description': 'Instagram post #abc123',
    'start': {
        'dateTime': '2026-03-01T10:00:00+01:00',
        'timeZone': 'Europe/Oslo',
    },
    'end': {
        'dateTime': '2026-03-01T10:15:00+01:00',
        'timeZone': 'Europe/Oslo',
    },
    'colorId': '10',  # Basil (Scheduled status)
    'extendedProperties': {
        'private': {
            'dawo_content_id': 'uuid-here',
            'dawo_status': 'scheduled'
        }
    }
}

event = service.events().insert(calendarId=calendar_id, body=event).execute()
event_id = event['id']  # Store as google_calendar_event_id
```

### 3. Update Event (Use PATCH, Not UPDATE)

**Critical**: Use `patch()` for partial updates. `update()` requires sending ALL fields or will clear missing ones.

```python
# Update only status and color
updated_event = {
    'colorId': '9',  # Blueberry (Published)
    'extendedProperties': {
        'private': {
            'dawo_status': 'published'
        }
    }
}

service.events().patch(
    calendarId=calendar_id,
    eventId=event_id,
    body=updated_event
).execute()
```

### 4. Delete Event

```python
service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
```

### 5. Set Event Colors (Status Visualization)

| Status | colorId | Color | Use Case |
|--------|---------|-------|----------|
| Draft | `"1"` | Lavender | Content in draft |
| Approved | `"2"` | Sage | Awaiting schedule |
| Scheduled | `"10"` | Basil | Queued for publish |
| Published | `"9"` | Blueberry | Successfully posted |
| Failed | `"11"` | Tomato | Publish error |

**Note**: colorId is a string, not integer. Must quote in JSON.

### 6. Retrieve Available Colors

```python
colors = service.colors().get().execute()
# Returns:
# {
#   'event': {
#     '1': {'background': '#a4bdfc', 'foreground': '#1d1d1d'},
#     '2': {'background': '#7ae7bf', 'foreground': '#1d1d1d'},
#     ...
#   }
# }
```

### 7. Extended Properties (DAWO Metadata)

Use `extendedProperties.private` to store app-specific metadata:
- **Searchable**: Can query events by extended properties
- **App-private**: Not visible to users in Calendar UI
- **Key-value pairs**: Strings only

```python
'extendedProperties': {
    'private': {
        'dawo_content_id': 'uuid-123',
        'dawo_status': 'scheduled',
        'dawo_post_type': 'instagram_post'
    }
}
```

## Batch API Operations

### Overview
Batch requests combine up to **50 operations** in a single HTTP request using `multipart/mixed` content type. Reduces latency and API call count.

### Python Implementation

```python
from googleapiclient.http import BatchHttpRequest

def callback(request_id, response, exception):
    if exception:
        print(f"Error in request {request_id}: {exception}")
    else:
        print(f"Success: {response['id']}")

batch = service.new_batch_http_request(callback=callback)

# Add multiple operations
for content_item in content_items:
    event = build_event(content_item)
    batch.add(service.events().insert(calendarId=calendar_id, body=event))

# Execute all at once
batch.execute()
```

### Important Notes
- **Unordered execution**: Server may execute calls in any order. Don't rely on execution sequence.
- **Sequential dependencies**: If operation B depends on operation A's result, send them in separate requests.
- **Max 50 ops/batch**: Split larger batches into multiple requests.

### When to Use Batching
- **Bulk event creation**: Syncing 20+ content items at once
- **Periodic sync**: Daily synchronization of published vs scheduled status
- **Initial calendar setup**: Creating multiple events for existing content

**For DAWO.ECO**: Batching likely not critical (typical 1-5 events/day). Useful for initial sync or bulk operations.

## Rate Limits and Quotas

### Current Limits (2026)
- **Daily quota**: 1,000,000 queries/day per project
- **Per-user rate**: 500 queries/100 seconds/user
- **Sliding window**: Quotas calculated per minute using rolling average

### Quota Error Handling

**HTTP 403 or 429** with `rateLimitExceeded` reason. Treat both identically.

### Exponential Backoff Implementation

```python
import time
import random

def call_calendar_api_with_retry(api_call, max_retries=5):
    for attempt in range(max_retries):
        try:
            return api_call()
        except HttpError as e:
            if e.resp.status in [403, 429]:
                if attempt == max_retries - 1:
                    raise
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
            else:
                raise
```

**For DAWO.ECO**: RetryMiddleware already implements exponential backoff. No dedicated rate limiter needed.

### Best Practices for Rate Limits
1. **Use push notifications** instead of polling (see below)
2. **Randomize traffic**: For periodic sync, vary schedule ±25%
3. **Exponential backoff**: Retry with increasing delays on 429/403
4. **Monitor usage**: Track API calls in logs to predict quota needs

### Quota Context for DAWO.ECO
- **Typical usage**: 5-10 API calls/day (event create/update/delete)
- **Quota headroom**: 1M calls/day = 99.999% buffer
- **No concern**: Rate limits extremely generous for content calendar use case

## Push Notifications (Webhooks)

### Overview
Push notifications eliminate polling by triggering HTTPS callbacks when resources change. Requires public HTTPS endpoint and domain verification.

### Setup Steps
1. **Create webhook endpoint**: `POST /api/calendar-webhook` (must be HTTPS)
2. **Watch resource**: `POST /calendar/v3/calendars/{calendarId}/events/watch`
3. **Handle notifications**: Parse notification headers, fetch updated resources
4. **Renew channels**: Channels expire after 1 week (max), must renew

### Watch Request Example

```python
channel = {
    'id': str(uuid.uuid4()),
    'type': 'web_hook',
    'address': 'https://dawo.eco/api/calendar-webhook',
    'token': 'secret-verification-token',
    'expiration': int((datetime.now() + timedelta(days=7)).timestamp()) * 1000
}

watch_response = service.events().watch(calendarId=calendar_id, body=channel).execute()
# Returns: channel ID, resource ID, expiration
```

### Notification Payload
**Critical**: Webhook does NOT include event data. It's a signal that something changed. Must make subsequent API call to fetch updated events.

```json
{
  "kind": "api#channel",
  "id": "channel-id-here",
  "resourceId": "resource-id-here",
  "resourceUri": "https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events",
  "expiration": "1234567890000"
}
```

### Decision for DAWO.ECO: Skip Push Notifications (Phase 1)

**Rationale**:
- **One-directional sync**: DAWO → Calendar only. No user edits in Calendar that need syncing back.
- **Complexity**: Requires public HTTPS, domain verification, channel renewal, webhook security
- **Minimal benefit**: Content calendar changes are application-triggered, not external
- **Future enhancement**: If bidirectional sync needed (user reschedules via Calendar), add in Phase 2

## Breaking Changes and Deprecations (2025-2026)

### Recent API Changes

#### 1. Out of Office Events (2025)
- Organizer now set to `unknownorganizer@calendar.google.com` instead of calendar owner
- Rolled out gradually over 2-3 weeks
- **Impact on DAWO.ECO**: None (not using out-of-office events)

#### 2. Event Type Field (New)
- New `eventType` field distinguishes special events: `default`, `outOfOffice`, `focusTime`, etc.
- **Impact on DAWO.ECO**: None (all DAWO events are `default` type)

#### 3. Conference Data Consistency (2025)
- `conferenceData.conferenceSolution.key.type` must be `hangoutsMeet` for Google Meet
- Third-party providers must use `addOn`
- **Impact on DAWO.ECO**: None (not using video conferencing)

#### 4. JSON-RPC and Global HTTP Batch Endpoints Deprecated
- Batch requests now use multipart/mixed HTTP only
- **Impact**: Already using recommended approach (`new_batch_http_request()`)

### No Breaking Changes for DAWO.ECO Use Case
All Epic 7 Story 7-9 operations use standard, stable Calendar API v3 features. No migration needed.

## Async Wrapping Pattern

### Challenge
Google Calendar API client is **synchronous** (blocking I/O). FastAPI/DAWO.ECO is async-first.

### Solution: `asyncio.run_in_executor()`

**Proven pattern from Story 5-4** (Gmail integration):

```python
import asyncio
from functools import partial

class CalendarClient:
    def __init__(self, credentials_manager):
        self._credentials_manager = credentials_manager

    async def create_event(self, calendar_id: str, event: dict) -> dict:
        """Async wrapper for synchronous Calendar API call."""
        service = self._credentials_manager.get_service()
        # Run synchronous API call in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(service.events().insert(calendarId=calendar_id, body=event).execute)
        )

    async def update_event(self, calendar_id: str, event_id: str, event: dict) -> dict:
        service = self._credentials_manager.get_service()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(service.events().patch(calendarId=calendar_id, eventId=event_id, body=event).execute)
        )
```

### Why This Works
- Thread pool executor runs blocking code in background thread
- FastAPI event loop remains non-blocking
- Identical pattern to Gmail client (proven reliable)

## Error Handling Patterns

### HTTP Error Categories

```python
from googleapiclient.errors import HttpError

try:
    result = service.events().insert(calendarId=calendar_id, body=event).execute()
except HttpError as e:
    if e.resp.status == 401:
        # Unauthorized - token expired or invalid
        # Re-run OAuth flow or refresh token
        pass
    elif e.resp.status == 403:
        # Forbidden - quota exceeded or insufficient permissions
        # Check API quota, verify scopes
        pass
    elif e.resp.status == 404:
        # Not found - calendar or event doesn't exist
        # Verify calendar_id/event_id
        pass
    elif e.resp.status == 429:
        # Rate limit exceeded
        # Exponential backoff retry
        pass
    else:
        # Other errors
        raise
```

### Integration with RetryMiddleware

**RetryMiddleware already handles**:
- Exponential backoff on 429/503
- Network failures (connection errors, timeouts)
- Returns `RetryResult` with `is_incomplete=True` on failure

**Calendar client integration**:
```python
from core.middleware import RetryMiddleware, RetryResult

class CalendarClient:
    def __init__(self, retry_middleware: RetryMiddleware):
        self._retry = retry_middleware

    async def create_event_with_retry(self, calendar_id: str, event: dict) -> RetryResult:
        async def _operation():
            return await self.create_event(calendar_id, event)

        return await self._retry.execute(_operation, operation_name="calendar_create_event")
```

## File Structure (Following Gmail Pattern)

```
teams/dawo/calendar/
    __init__.py                    # Exports: CalendarClient, CalendarSyncService
    config.py                      # CalendarConfig (frozen dataclass)
    credentials_manager.py         # CalendarCredentialsManager (token management)
    client.py                      # CalendarClient (async API wrapper)
    service.py                     # CalendarSyncService (business logic)
    event_builder.py               # Content → Event mapping

credentials/
    gmail_credentials.json         # OAuth client credentials (reused)
    calendar_token.json            # Calendar-specific token (NEW)

scripts/
    authorize_calendar.py          # Initial OAuth flow script (NEW)
```

## Google Cloud Console Setup

### Steps
1. **Enable API**: APIs & Services → Library → Search "Google Calendar API" → Enable
2. **Verify consent screen**: Already configured for Gmail (Story 5-4)
3. **Add scope**: Calendar scope auto-added when first authorized
4. **Run authorization script**: `python scripts/authorize_calendar.py`
5. **Verify token**: Check `credentials/calendar_token.json` created

### No Changes to OAuth Consent Screen
Gmail OAuth client already configured. Adding Calendar scope doesn't require re-submission.

### Debugging OAuth Issues

```bash
# Verify token scopes
curl "https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}"

# Check token expiration
curl "https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}"
```

## Implementation Checklist

### Pre-Implementation Verification (Story 7-9 Start)
- [ ] Enable Google Calendar API in Google Cloud Console
- [ ] Verify `gmail_credentials.json` exists and is valid
- [ ] Run `scripts/authorize_calendar.py` to generate `calendar_token.json`
- [ ] Test `run_in_executor()` pattern with existing Gmail credential manager
- [ ] Confirm `google-api-python-client>=2.0.0` in requirements.txt (already present)

### Development Tasks
- [ ] Create `teams/dawo/calendar/` structure (mirror Gmail)
- [ ] Implement `CalendarCredentialsManager` (reuse Gmail pattern)
- [ ] Implement `CalendarClient` with async wrappers
- [ ] Add `google_calendar_event_id` column to `content` table
- [ ] Implement `CalendarSyncService` business logic
- [ ] Create event builder (content → Calendar event mapping)
- [ ] Add RetryMiddleware integration
- [ ] Register `CalendarSyncService` in `team_spec.py` as `RegisteredService`

### Testing Strategy
- [ ] Unit tests: Mock Calendar API responses
- [ ] Integration tests: Use test calendar (not production "DAWO Content Schedule")
- [ ] Test token refresh flow
- [ ] Test batch operations (if implemented)
- [ ] Test error handling (401, 403, 404, 429)

## Key Differences from Gmail Integration

| Aspect | Gmail (Story 5-4) | Calendar (Story 7-9) |
|--------|------------------|---------------------|
| **Direction** | Outbound only (send emails) | Bidirectional (create/update/read) |
| **Token file** | `gmail_token.json` | `calendar_token.json` |
| **Scope** | `gmail.send` | `calendar` (full) |
| **API resource** | Messages | Calendars + Events |
| **Batch ops** | Not used | Optional (useful for bulk sync) |
| **Metadata** | Email headers | `extendedProperties.private` |
| **ID storage** | Not needed (one-shot send) | Store `calendar_id` + `google_calendar_event_id` |

## Cost and Pricing

**Google Calendar API is FREE** with generous quotas:
- No charges for API usage
- 1M calls/day = suitable for most applications
- Exceeding quota does NOT incur charges (requests just fail)

**DAWO.ECO**: Zero cost impact. Calendar API completely free.

## References and Documentation

### Official Documentation
- [Google Calendar API v3 Reference](https://developers.google.com/workspace/calendar/api/v3/reference)
- [Python Quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python)
- [OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Manage Quotas](https://developers.google.com/workspace/calendar/api/guides/quota)
- [Push Notifications](https://developers.google.com/workspace/calendar/api/guides/push)
- [Batch Requests](https://developers.google.com/workspace/calendar/api/guides/batch)
- [Handle API Errors](https://developers.google.com/workspace/calendar/api/guides/errors)

### Python Library Documentation
- [google-api-python-client PyPI](https://pypi.org/project/google-api-python-client/)
- [google-auth PyPI](https://pypi.org/project/google-auth/)
- [google-auth-oauthlib PyPI](https://pypi.org/project/google-auth-oauthlib/)
- [googleapis/google-api-python-client GitHub](https://github.com/googleapis/google-api-python-client)

### Community Resources
- [OAuth 2.0 for Installed Applications](https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html)
- [OAuth 2.0 for Server to Server](https://googleapis.github.io/google-api-python-client/docs/oauth-server.html)
- [Calendar API Release Notes](https://developers.google.com/workspace/calendar/release-notes)

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Auth pattern** | OAuth2 user consent (not service account) | Single operator, full calendar access |
| **Token management** | Separate `calendar_token.json` | Doesn't break Gmail integration |
| **OAuth client** | Reuse `gmail_credentials.json` | Same Google Cloud project |
| **Async pattern** | `run_in_executor()` | Proven in Gmail client (Story 5-4) |
| **Partial updates** | `patch()` not `update()` | Avoids clearing unset fields |
| **Metadata storage** | `extendedProperties.private` | Searchable, app-private, key-value |
| **Batch operations** | Optional (implement if bulk sync needed) | Typical 1-5 events/day (low benefit) |
| **Webhooks** | Skip Phase 1 | One-directional sync (DAWO → Calendar) |
| **Dependencies** | None new | All already in requirements.txt |
| **Rate limiting** | RetryMiddleware only | 1M calls/day = huge headroom |
| **Calendar ID storage** | Store in database | No "get by name" API |
| **Event ID storage** | Store as `google_calendar_event_id` | Required for update/delete operations |
| **Color scheme** | 5 status colors (Draft, Approved, Scheduled, Published, Failed) | Visual status tracking |

---

## Research Sources

- [google-api-python-client PyPI](https://pypi.org/project/google-api-python-client/)
- [google-auth PyPI](https://pypi.org/project/google-auth/)
- [google-auth-oauthlib PyPI](https://pypi.org/project/google-auth-oauthlib/)
- [Using OAuth 2.0 for Server to Server Applications](https://developers.google.com/identity/protocols/oauth2/service-account)
- [Calendar API Events Reference](https://googleapis.github.io/google-api-python-client/docs/dyn/calendar_v3.events.html)
- [Calendar API Colors Reference](https://developers.google.com/workspace/calendar/api/v3/reference/colors)
- [Manage Quotas Guide](https://developers.google.com/workspace/calendar/api/guides/quota)
- [Handle API Errors Guide](https://developers.google.com/workspace/calendar/api/guides/errors)
- [Choose Google Calendar API Scopes](https://developers.google.com/workspace/calendar/api/auth)
- [Python Quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python)
- [Push Notifications Guide](https://developers.google.com/workspace/calendar/api/guides/push)
- [Send Batch Requests Guide](https://developers.google.com/workspace/calendar/api/guides/batch)
- [Calendar API Release Notes](https://developers.google.com/workspace/calendar/release-notes)
- [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)

---

*Research for Epic 7 Story 7-9*
*Updated: 2026-02-25 with comprehensive implementation details*
