# Story 1.5: External API Retry Middleware

Status: complete

---

## Story

As an **operator**,
I want external API calls to retry automatically on failure,
So that temporary outages don't cause lost work or missed schedules.

---

## Acceptance Criteria

1. **Given** an external API call fails (Instagram, Discord, Orshot, Shopify)
   **When** the retry middleware handles the failure
   **Then** it retries with exponential backoff: 1s, 2s, 4s (3 attempts max)
   **And** it respects API rate limits during retry
   **And** it logs each retry attempt with error details

2. **Given** all retry attempts are exhausted
   **When** the middleware reports failure
   **Then** it marks the operation as `INCOMPLETE` (not failed)
   **And** it queues the operation for later retry
   **And** it allows the rest of the pipeline to continue (graceful degradation)
   **And** it sends Discord alert for API errors (if Discord is available)

3. **Given** an API returns rate limit response (429)
   **When** the middleware handles it
   **Then** it waits for the specified retry-after duration
   **And** it does not count this as a retry attempt

---

## Tasks / Subtasks

- [x] Task 1: Create retry middleware module structure (AC: #1)
  - [x] 1.1 Create `teams/dawo/middleware/` directory
  - [x] 1.2 Create `teams/dawo/middleware/__init__.py` with exports
  - [x] 1.3 Create `teams/dawo/middleware/retry.py` with RetryMiddleware class
  - [x] 1.4 Define `RetryConfig` dataclass: max_retries, base_delay, max_delay, backoff_multiplier
  - [x] 1.5 Define `RetryResult` dataclass: success, response, attempts, last_error, is_incomplete

- [x] Task 2: Implement exponential backoff logic (AC: #1)
  - [x] 2.1 Implement `_calculate_delay(attempt: int) -> float` with backoff formula
  - [x] 2.2 Delays: attempt 1 = 1s, attempt 2 = 2s, attempt 3 = 4s (exponential)
  - [x] 2.3 Add jitter to prevent thundering herd (±10% randomization)
  - [x] 2.4 Cap delay at max_delay from config

- [x] Task 3: Implement retry execution wrapper (AC: #1, #2)
  - [x] 3.1 Create async `execute_with_retry(operation: Callable, context: str) -> RetryResult`
  - [x] 3.2 Catch HTTP errors (5xx, connection errors, timeouts)
  - [x] 3.3 Log each retry attempt with: operation context, attempt number, error type, delay
  - [x] 3.4 After max retries, set `is_incomplete=True` (NOT failed)
  - [x] 3.5 Return result allowing caller to continue (graceful degradation)

- [x] Task 4: Implement rate limit handling (AC: #3)
  - [x] 4.1 Detect HTTP 429 responses
  - [x] 4.2 Parse `Retry-After` header (seconds or HTTP-date format)
  - [x] 4.3 Wait for specified duration before retry
  - [x] 4.4 Do NOT count 429 waits against max_retries
  - [x] 4.5 Cap rate-limit wait at reasonable max (5 minutes)

- [x] Task 5: Implement operation queuing for later retry (AC: #2)
  - [x] 5.1 Define `IncompleteOperation` dataclass: operation_id, context, payload, created_at, retry_count
  - [x] 5.2 Create `OperationQueue` class for persisting incomplete operations
  - [x] 5.3 Queue uses Redis (ARQ pattern) for persistence across restarts
  - [x] 5.4 Implement `queue_for_retry(operation: IncompleteOperation)`
  - [x] 5.5 Implement `get_pending_operations() -> List[IncompleteOperation]`

- [x] Task 6: Implement Discord error alerting (AC: #2)
  - [x] 6.1 Create `send_api_error_alert(context: str, error: str, attempts: int)`
  - [x] 6.2 Use existing Discord integration from `integrations/discord/`
  - [x] 6.3 Wrap Discord call in retry (but don't fail if Discord itself fails)
  - [x] 6.4 Rate-limit Discord alerts (max 1 per API per 5 minutes)
  - [x] 6.5 Include actionable info: API name, error type, queued for retry status

- [x] Task 7: Create retry configuration (AC: #1)
  - [x] 7.1 Create `config/dawo_retry_config.json` with default settings
  - [x] 7.2 Define per-API overrides (Instagram, Discord, Orshot, Shopify)
  - [x] 7.3 Include timeout settings per API
  - [x] 7.4 Support config injection pattern (like LLMTierResolver)

- [x] Task 8: Create HTTP client wrapper (AC: #1, #3)
  - [x] 8.1 Create `RetryableHttpClient` class wrapping httpx/aiohttp
  - [x] 8.2 All external HTTP calls MUST go through this client
  - [x] 8.3 Automatically applies retry middleware to all requests
  - [x] 8.4 Include request timeout handling

- [x] Task 9: Create comprehensive tests
  - [x] 9.1 Test exponential backoff delays (1s, 2s, 4s)
  - [x] 9.2 Test max retries respected (stops at 3)
  - [x] 9.3 Test 429 rate limit handling (waits, doesn't count as retry)
  - [x] 9.4 Test incomplete status returned (not exception)
  - [x] 9.5 Test operation queuing works
  - [x] 9.6 Test Discord alert sent on exhausted retries
  - [x] 9.7 Test Discord alert rate-limiting
  - [x] 9.8 Test graceful degradation (caller continues)
  - [x] 9.9 Test config injection pattern
  - [x] 9.10 Test per-API config overrides

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Workflow-Architecture], [project-context.md#External-API-Calls]

**Decision from Architecture:**
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Error Handling** | Retry + Degrade | Auto-retry with exponential backoff; if exhausted, mark incomplete and continue |

**Critical Rules from project-context.md:**
- ✅ ALL external calls go through retry middleware
- ✅ Use integrations from `integrations/` folder
- ❌ NEVER make direct API calls without retry wrapper
- Retry policy: 3 attempts, exponential backoff (1s, 2s, 4s), then mark incomplete

### Exponential Backoff Implementation

**Source:** [epics.md#Story-1.5]

```python
def _calculate_delay(self, attempt: int) -> float:
    """Calculate delay with exponential backoff.

    attempt 1: 1s (base_delay)
    attempt 2: 2s (base_delay * 2^1)
    attempt 3: 4s (base_delay * 2^2)

    Add jitter (±10%) to prevent thundering herd.
    """
    base_delay = self._config.base_delay  # 1.0
    multiplier = self._config.backoff_multiplier  # 2.0

    delay = base_delay * (multiplier ** (attempt - 1))
    delay = min(delay, self._config.max_delay)

    # Add jitter
    jitter = delay * 0.1 * (random.random() * 2 - 1)
    return delay + jitter
```

### Rate Limit Handling (AC #3)

**Source:** [epics.md#Story-1.5]

HTTP 429 responses are special:
- Do NOT count against max_retries
- Wait for `Retry-After` header duration
- Cap wait at 5 minutes (prevent infinite waits)

```python
async def _handle_rate_limit(self, response: Response) -> float:
    """Extract wait duration from 429 response.

    Retry-After header formats:
    - Seconds: "120" (wait 120 seconds)
    - HTTP-date: "Wed, 21 Oct 2015 07:28:00 GMT"

    Returns wait duration in seconds, capped at MAX_RATE_LIMIT_WAIT.
    """
    MAX_RATE_LIMIT_WAIT = 300  # 5 minutes

    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return 60  # Default 1 minute if no header

    try:
        # Try parsing as seconds
        wait_seconds = float(retry_after)
    except ValueError:
        # Parse as HTTP-date
        wait_seconds = parse_http_date_to_seconds(retry_after)

    return min(wait_seconds, MAX_RATE_LIMIT_WAIT)
```

### Graceful Degradation Pattern (AC #2)

**Source:** [architecture.md#Error-Handling], [project-context.md#External-API-Calls]

**CRITICAL:** Operations are marked `INCOMPLETE`, not `FAILED`:
- Caller continues with other operations
- Incomplete operation is queued for later retry
- Pipeline doesn't stop for one API failure

```python
@dataclass
class RetryResult:
    """Result of retry-wrapped operation."""
    success: bool
    response: Optional[Any] = None
    attempts: int = 0
    last_error: Optional[str] = None
    is_incomplete: bool = False
    operation_id: Optional[str] = None  # For queued operations

# Usage pattern - caller handles incomplete gracefully
result = await retry_client.execute_with_retry(
    operation=lambda: instagram_api.post(content),
    context="instagram_publish"
)

if result.success:
    handle_success(result.response)
elif result.is_incomplete:
    # Continue with other work - operation queued for retry
    logger.warning(f"Instagram publish queued for retry: {result.operation_id}")
    continue_with_other_content()
```

### Operation Queue (Redis + ARQ)

**Source:** [architecture.md#Backend-Architecture]

Use existing Redis/ARQ infrastructure for operation queue:

```python
# teams/dawo/middleware/operation_queue.py
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json

@dataclass
class IncompleteOperation:
    """Operation queued for later retry."""
    operation_id: str
    context: str  # e.g., "instagram_publish", "discord_notification"
    payload: dict  # Serialized operation parameters
    created_at: datetime
    retry_count: int = 0
    last_attempt: Optional[datetime] = None
    last_error: Optional[str] = None

class OperationQueue:
    """Queue for incomplete operations using Redis."""

    QUEUE_KEY = "dawo:incomplete_operations"

    def __init__(self, redis_client):
        """Accept Redis client via injection - NEVER connect directly."""
        self._redis = redis_client

    async def queue_for_retry(self, operation: IncompleteOperation) -> str:
        """Add operation to retry queue."""
        await self._redis.hset(
            self.QUEUE_KEY,
            operation.operation_id,
            json.dumps(asdict(operation), default=str)
        )
        return operation.operation_id

    async def get_pending_operations(self) -> list[IncompleteOperation]:
        """Get all pending operations for retry processing."""
        raw_ops = await self._redis.hgetall(self.QUEUE_KEY)
        return [
            IncompleteOperation(**json.loads(data))
            for data in raw_ops.values()
        ]
```

### Discord Alert Pattern (AC #2)

**Source:** [epics.md#Story-1.5]

```python
class DiscordAlertManager:
    """Rate-limited Discord alerting for API errors."""

    ALERT_COOLDOWN = 300  # 5 minutes per API

    def __init__(self, discord_client, redis_client):
        self._discord = discord_client
        self._redis = redis_client

    async def send_api_error_alert(
        self,
        api_name: str,
        error: str,
        attempts: int,
        queued_for_retry: bool
    ) -> bool:
        """Send Discord alert if not rate-limited.

        Returns True if alert was sent, False if rate-limited.
        """
        # Check rate limit
        cache_key = f"dawo:alert_cooldown:{api_name}"
        if await self._redis.exists(cache_key):
            return False

        # Send alert
        message = self._format_alert(api_name, error, attempts, queued_for_retry)
        try:
            await self._discord.send_webhook(message)
            # Set cooldown
            await self._redis.setex(cache_key, self.ALERT_COOLDOWN, "1")
            return True
        except Exception:
            # Discord itself failed - log but don't propagate
            logger.warning("Discord alert failed - continuing without alert")
            return False

    def _format_alert(self, api_name: str, error: str, attempts: int, queued: bool) -> str:
        status = "✅ Queued for retry" if queued else "❌ Manual intervention needed"
        return f"""
❌ **API Error: {api_name}**
• Error: {error}
• Attempts: {attempts}
• Status: {status}
"""
```

### Configuration Schema

**Source:** [architecture.md#Config-Files]

```json
// config/dawo_retry_config.json
{
  "version": "2026-02",
  "description": "Retry middleware configuration for DAWO external API calls",

  "default": {
    "max_retries": 3,
    "base_delay": 1.0,
    "max_delay": 60.0,
    "backoff_multiplier": 2.0,
    "timeout": 30.0,
    "max_rate_limit_wait": 300
  },

  "api_overrides": {
    "instagram": {
      "timeout": 45.0,
      "max_rate_limit_wait": 600
    },
    "discord": {
      "max_retries": 2,
      "timeout": 10.0
    },
    "orshot": {
      "timeout": 60.0
    },
    "shopify": {
      "timeout": 30.0
    }
  },

  "discord_alerts": {
    "enabled": true,
    "webhook_url": "${DISCORD_WEBHOOK_URL}",
    "cooldown_seconds": 300
  }
}
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#Project-Structure]

```
teams/dawo/
├── middleware/                       # CREATE THIS
│   ├── __init__.py                   # Export RetryMiddleware, RetryableHttpClient, etc.
│   ├── retry.py                      # RetryMiddleware class, RetryConfig, RetryResult
│   ├── http_client.py                # RetryableHttpClient wrapper
│   ├── operation_queue.py            # IncompleteOperation, OperationQueue
│   └── discord_alerts.py             # DiscordAlertManager

config/
├── dawo_compliance_rules.json        # Exists (Story 1.2)
├── dawo_brand_profile.json           # Exists (Story 1.3)
├── dawo_llm_tiers.json               # Exists (Story 1.4)
└── dawo_retry_config.json            # CREATE THIS

tests/teams/dawo/
├── test_validators/                  # Exists
├── test_config/                      # Exists (Story 1.4)
└── test_middleware/                  # CREATE THIS
    ├── __init__.py
    ├── test_retry.py
    ├── test_http_client.py
    ├── test_operation_queue.py
    └── test_discord_alerts.py
```

### Previous Story Learnings (Story 1.4)

**Source:** [1-4-llm-tier-configuration.md#Completion-Notes-List]

**MUST APPLY these learnings:**

1. **Config Injection** - All configuration MUST be injected via constructor. RetryMiddleware accepts RetryConfig dataclass, not file path.

2. **Complete Exports** - Add ALL types to `__all__` in `__init__.py`:
   - `RetryMiddleware`
   - `RetryConfig`
   - `RetryResult`
   - `RetryableHttpClient`
   - `IncompleteOperation`
   - `OperationQueue`
   - `DiscordAlertManager`
   - `load_retry_config` (for Team Builder only)

3. **Dataclass Pattern** - Use dataclasses for all configuration and result structures.

4. **Validation on Init** - Validate configuration when middleware is constructed.

5. **Error Messages** - Provide helpful, actionable error messages.

### Integration Points

**Source:** [architecture.md#External-Integration-Points]

| Integration | Usage | Special Handling |
|-------------|-------|------------------|
| Instagram Graph API | Content publishing, research | Higher timeout (45s), longer rate limit wait |
| Discord Webhooks | Notifications, alerts | Lower retries (2), short timeout (10s) |
| Orshot API | Graphics generation | High timeout (60s) for rendering |
| Shopify MCP | Product data | Standard timeout (30s) |

### Retryable vs Non-Retryable Errors

**IMPORTANT:** Only retry on transient errors:

**Retryable (DO retry):**
- HTTP 5xx (server errors)
- HTTP 429 (rate limit - special handling)
- Connection errors
- Timeout errors
- DNS resolution failures

**Non-Retryable (DON'T retry):**
- HTTP 4xx (except 429) - client errors, bad request
- HTTP 401/403 - authentication/authorization
- Validation errors
- Malformed response (likely bad request)

```python
RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.NetworkError,
    asyncio.TimeoutError,
)

def _is_retryable(self, error: Exception) -> bool:
    """Determine if error warrants retry."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(error, RETRYABLE_EXCEPTIONS)
```

### Technology Stack Context

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | async/await, type hints |
| httpx | Latest | Async HTTP client |
| Redis | 7 | Operation queue persistence |
| ARQ | Latest | Job queue integration |
| Testing | pytest, pytest-asyncio | Async test support |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [architecture.md#Anti-Patterns], [project-context.md#Anti-Patterns]

1. ❌ Direct API calls without retry wrapper → Use RetryableHttpClient
2. ❌ Raising exceptions on retry exhaustion → Return RetryResult with is_incomplete=True
3. ❌ Hardcoded retry counts/delays → Use config injection
4. ❌ Infinite retry loops → Respect max_retries
5. ❌ Counting 429 as retry attempt → Special rate-limit handling
6. ❌ Blocking other operations on failure → Graceful degradation

### Project Context Reference

**Source:** [project-context.md]

The External API Retry Middleware implements the "External API Calls" pattern defined in project-context.md:

> - ✅ ALL external calls go through retry middleware
> - ✅ Use integrations from `integrations/` folder
> - ❌ NEVER make direct API calls without retry wrapper
>
> Retry policy: 3 attempts, exponential backoff (1min, 5min, 15min), then mark incomplete.

**Note:** PRD specifies longer intervals (1min, 5min, 15min) but epics specify shorter (1s, 2s, 4s). Architecture clarifies: use shorter delays (1s, 2s, 4s) for responsiveness. The "mark incomplete and queue" pattern handles extended outages.

---

## References

- [Source: architecture.md#Workflow-Architecture] - Retry + graceful degradation decision
- [Source: architecture.md#External-Integration-Points] - Integration locations
- [Source: architecture.md#Anti-Patterns] - Direct API call anti-pattern
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: epics.md#Story-1.5] - Original story requirements with backoff times
- [Source: 1-4-llm-tier-configuration.md] - Previous story patterns (config injection, testing)

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

1. **TDD Red-Green-Refactor** - Followed strict TDD cycle throughout. All 104 tests written first (RED), then implementation (GREEN), then verified.

2. **Exponential Backoff Formula** - Implemented as `base_delay * (multiplier ** (attempt - 1))` with ±10% jitter to prevent thundering herd.

3. **Rate Limit Handling** - HTTP 429 handled specially: waits for Retry-After header duration, does NOT count against max_retries.

4. **Graceful Degradation** - Operations return `RetryResult` with `is_incomplete=True` instead of raising exceptions. Caller can continue processing.

5. **Config Injection Pattern** - All classes accept config via constructor injection. No direct file loading in business classes.

6. **httpx Mock Compatibility** - `raise_for_status()` requires request instance on response. Fixed by manually checking status codes in RetryableHttpClient.

7. **Per-API Configuration** - Config loader merges default config with API-specific overrides (Instagram, Discord, Orshot, Shopify).

8. **Discord Alert Rate Limiting** - Uses Redis keys with 5-minute cooldown per API to prevent alert spam.

### File List

**Created Files:**
- `teams/dawo/middleware/__init__.py` - Module exports (updated with new exports)
- `teams/dawo/middleware/retry.py` - RetryConfig, RetryResult, RetryMiddleware (+ validation)
- `teams/dawo/middleware/http_client.py` - RetryableHttpClient wrapper (+ PUT/DELETE/PATCH)
- `teams/dawo/middleware/operation_queue.py` - IncompleteOperation, OperationQueue (+ update_operation fix)
- `teams/dawo/middleware/discord_alerts.py` - DiscordAlertManager (+ cooldown injection)
- `teams/dawo/middleware/integration.py` - RetryPipeline (NEW - full pipeline integration)
- `config/dawo_retry_config.json` - Retry configuration with per-API overrides
- `integrations/__init__.py` - Integrations module (NEW)
- `integrations/discord/__init__.py` - Discord integration exports (NEW)
- `integrations/discord/client.py` - DiscordWebhookClient (NEW)
- `tests/teams/dawo/test_middleware/__init__.py` - Test module
- `tests/teams/dawo/test_middleware/test_retry.py` - 47 tests for core retry logic
- `tests/teams/dawo/test_middleware/test_http_client.py` - 10 tests for HTTP client
- `tests/teams/dawo/test_middleware/test_operation_queue.py` - 19 tests for operation queue
- `tests/teams/dawo/test_middleware/test_discord_alerts.py` - 14 tests for Discord alerts
- `tests/teams/dawo/test_middleware/test_config_loader.py` - 14 tests for config loading
- `tests/teams/dawo/test_middleware/test_code_review_fixes.py` - 32 tests for code review fixes (NEW)

**Test Results:** 136 tests passing (104 original + 32 code review fixes)

---

## Code Review Record

### Review Date
2026-02-06

### Reviewer
Dev Agent (Amelia) - Code Review Workflow

### Issues Found and Fixed

| Severity | Issue | Fix Applied |
|----------|-------|-------------|
| HIGH | H1: Missing Discord integration | Created `integrations/discord/` with DiscordWebhookClient |
| HIGH | H2: Missing PUT/DELETE/PATCH methods | Added to RetryableHttpClient |
| HIGH | H3: No RetryConfig validation | Added `__post_init__` validation |
| MEDIUM | M1: HTTP-date not parsed in Retry-After | Added RFC 7231 date parsing |
| MEDIUM | M2: discord_alerts config unused | Added cooldown_seconds injection |
| MEDIUM | M3: update_operation just called queue | Implemented proper field updates |
| MEDIUM | M4: No component integration | Created RetryPipeline class |
| LOW | L1: Generic Any types | Added Protocol types for Redis/Discord |
| LOW | L2: No __aexit__ error handling | Added try/except in context manager |

### Review Outcome
**PASS** - All 9 issues fixed, 136 tests passing

