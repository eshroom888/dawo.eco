# Story 4.6: Discord Approval Notifications

Status: done

---

## Story

As an **operator**,
I want Discord notifications when approvals are needed,
So that I know when to check the queue without constantly monitoring.

---

## Acceptance Criteria

1. **Given** new content enters approval queue
   **When** queue reaches threshold (5+ items or configurable)
   **Then** Discord notification is sent: "DAWO Agents: X items ready for review"
   **And** notification includes: count by type, highest priority item

2. **Given** notifications are configured
   **When** they're sent
   **Then** they go to configured webhook URL
   **And** format is: embed with summary, link to dashboard
   **And** rate limited to max 1 per hour (batched)

3. **Given** content has compliance warning
   **When** it enters queue
   **Then** Discord notification mentions: "1 item needs compliance review"

4. **Given** Discord webhook is unavailable
   **When** notification fails
   **Then** retry middleware handles it
   **And** notifications are queued for later delivery
   **And** system continues without blocking

---

## Tasks / Subtasks

- [x] Task 1: Create Approval Notification Service (AC: #1, #2, #3)
  - [x] 1.1 Create `ApprovalNotificationService` class in `core/notifications/approval_notifier.py`
  - [x] 1.2 Implement `ApprovalNotifierProtocol` for dependency injection
  - [x] 1.3 Create `check_and_notify()` method that evaluates queue state
  - [x] 1.4 Add queue threshold configuration (default: 5 items)
  - [x] 1.5 Aggregate counts: total pending, by source_type, by source_priority
  - [x] 1.6 Identify highest priority item for notification highlight
  - [x] 1.7 Count compliance warnings (compliance_status = WARNING)
  - [x] 1.8 Call existing `DiscordWebhookClient.send_approval_notification()`

- [x] Task 2: Implement Rate Limiting (AC: #2)
  - [x] 2.1 Create `NotificationRateLimiter` class in `core/notifications/rate_limiter.py`
  - [x] 2.2 Store last notification timestamp in Redis
  - [x] 2.3 Implement 1-hour cooldown between notifications
  - [x] 2.4 Add configurable cooldown period via config
  - [x] 2.5 Track pending notifications during cooldown for batching
  - [x] 2.6 On cooldown expiry, send batched summary
  - [x] 2.7 Add `is_rate_limited()` check method
  - [x] 2.8 Add `record_notification()` method

- [x] Task 3: Create Notification Trigger Hook (AC: #1, #3)
  - [x] 3.1 Create event hook in `core/notifications/hooks.py`
  - [x] 3.2 Hook into approval queue item creation (after content submission)
  - [x] 3.3 Check threshold and rate limit before triggering notification
  - [x] 3.4 Prioritize compliance warnings in immediate notification
  - [x] 3.5 Log all notification trigger events
  - [x] 3.6 Emit WebSocket event for UI notification indicator

- [x] Task 4: Implement Notification Queue for Failures (AC: #4)
  - [x] 4.1 Create `NotificationQueue` class in `core/notifications/queue.py`
  - [x] 4.2 Store failed notifications in Redis with TTL (24 hours)
  - [x] 4.3 Create background task to retry failed notifications
  - [x] 4.4 Exponential backoff: 1min, 5min, 15min, 1hr
  - [x] 4.5 Max 5 retry attempts per notification
  - [x] 4.6 Log all retry attempts and final status
  - [x] 4.7 Mark notification as abandoned after max retries

- [x] Task 5: Integrate with Retry Middleware (AC: #4)
  - [x] 5.1 Wrap Discord webhook calls with existing retry middleware
  - [x] 5.2 Configure 3 retries with exponential backoff (1s, 2s, 4s)
  - [x] 5.3 On final failure, queue notification for later retry
  - [x] 5.4 Log all retry attempts with error details
  - [x] 5.5 Handle Discord-specific error codes (rate limit, auth)
  - [x] 5.6 Continue system operation on notification failure (non-blocking)

- [x] Task 6: Create Configuration Schema (AC: #1, #2)
  - [x] 6.1 Add notification config to `config/dawo_notifications.json`
  - [x] 6.2 Define fields: webhook_url, threshold, cooldown_minutes, dashboard_url
  - [x] 6.3 Add enable/disable flag per notification type
  - [x] 6.4 Create `NotificationConfig` dataclass for type safety
  - [x] 6.5 Load config via dependency injection pattern
  - [x] 6.6 Validate config on startup

- [x] Task 7: Create ARQ Background Job (AC: #2, #4)
  - [x] 7.1 Create `process_notification_queue` ARQ job
  - [x] 7.2 Schedule job to run every 5 minutes
  - [x] 7.3 Process any pending/failed notifications in queue
  - [x] 7.4 Respect rate limiting during batch processing
  - [x] 7.5 Log job execution with notification counts
  - [x] 7.6 Add health metric for notification queue depth

- [x] Task 8: Add Dashboard Link to Notifications (AC: #2)
  - [x] 8.1 Configure dashboard_url in notification config
  - [x] 8.2 Pass URL to `send_approval_notification()` method
  - [x] 8.3 Discord embed includes clickable link to approval queue
  - [x] 8.4 Link opens directly to filtered pending items view

- [x] Task 9: Create Notification Tests (AC: all)
  - [x] 9.1 Unit test ApprovalNotificationService with mocked Discord client
  - [x] 9.2 Unit test NotificationRateLimiter with mocked Redis
  - [x] 9.3 Unit test NotificationQueue retry logic
  - [x] 9.4 Integration test full notification flow
  - [x] 9.5 Test threshold triggering at boundary (4 vs 5 items)
  - [x] 9.6 Test rate limiting (no spam within cooldown)
  - [x] 9.7 Test compliance warning prioritization
  - [x] 9.8 Test graceful failure handling

- [x] Task 10: Update Sprint Status (AC: all)
  - [x] 10.1 Mark story as done in sprint-status.yaml after validation
  - [x] 10.2 Document any deviations or learnings

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Notification-Patterns], [project-context.md#External-API-Calls]

This story implements FR40 (Discord notifications when approvals are needed). It leverages the existing `DiscordWebhookClient.send_approval_notification()` method added in Epic 4 prep, building the orchestration layer around it.

**Key Pattern:** Event-driven notification with rate limiting. Content submission triggers queue check, which triggers notification if threshold met and not rate-limited.

### Technology Stack (MUST USE)

**Source:** [project-context.md#Technology-Stack]

```
Backend:
- Python 3.11+ with async support
- Redis 7 for rate limiting state and notification queue
- ARQ for background job processing
- Existing DiscordWebhookClient from integrations/discord/

External APIs:
- Discord Webhooks (already integrated)
```

### Existing Discord Client (REUSE)

**Source:** [integrations/discord/client.py]

The Discord client already has the `send_approval_notification()` method implemented:

```python
async def send_approval_notification(
    self,
    pending_count: int,
    high_priority_count: int = 0,
    compliance_warnings: int = 0,
    dashboard_url: Optional[str] = None,
) -> bool:
    """Send approval queue notification (Epic 4, Story 4.6).

    Returns True if sent successfully, False otherwise.
    """
```

This method creates a rich embed with:
- Title: "DAWO Approval Queue"
- Description: "X items ready for review"
- Fields: Pending Items, High Priority, Compliance Warnings
- Color: Purple (EmbedColor.APPROVAL)
- URL: Dashboard link
- Footer: "DAWO Content Pipeline"

### Approval Notification Service Design

**Source:** [project-context.md#Configuration-Loading]

```python
# core/notifications/approval_notifier.py

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Optional
import logging

from integrations.discord.client import DiscordWebhookClient, DiscordClientProtocol

logger = logging.getLogger(__name__)

@dataclass
class QueueStatus:
    """Current state of the approval queue."""
    total_pending: int
    by_source_type: dict[str, int]
    by_priority: dict[int, int]
    compliance_warnings: int
    highest_priority_item: Optional[str]  # Item ID

@dataclass
class NotificationConfig:
    """Configuration for approval notifications."""
    webhook_url: str
    threshold: int = 5  # Notify when queue reaches this count
    cooldown_minutes: int = 60  # Max 1 notification per hour
    dashboard_url: str = "http://localhost:3000/approval"
    enabled: bool = True

class ApprovalNotifierProtocol(Protocol):
    """Protocol for approval notification service."""

    async def check_and_notify(self) -> bool:
        """Check queue state and send notification if warranted."""
        ...

class ApprovalNotificationService:
    """Service for sending approval queue notifications.

    Monitors the approval queue and sends Discord notifications
    when the queue reaches a configurable threshold. Implements
    rate limiting to prevent notification spam.

    Attributes:
        config: Notification configuration
        discord_client: Discord webhook client (injected)
        rate_limiter: Rate limiting service (injected)
        queue_repo: Approval queue repository (injected)
    """

    def __init__(
        self,
        config: NotificationConfig,
        discord_client: DiscordClientProtocol,
        rate_limiter: "NotificationRateLimiter",
        queue_repo: "ApprovalQueueRepository",
    ):
        self._config = config
        self._discord = discord_client
        self._rate_limiter = rate_limiter
        self._queue_repo = queue_repo

    async def check_and_notify(self) -> bool:
        """Check queue state and send notification if warranted.

        Returns:
            True if notification was sent, False otherwise

        Notification is sent when:
        1. Queue size >= threshold
        2. Not currently rate-limited
        3. Notifications are enabled
        """
        if not self._config.enabled:
            logger.debug("Notifications disabled, skipping check")
            return False

        # Get current queue status
        status = await self._get_queue_status()

        # Check threshold
        if status.total_pending < self._config.threshold:
            logger.debug(
                f"Queue size {status.total_pending} below threshold "
                f"{self._config.threshold}, skipping notification"
            )
            return False

        # Check rate limit
        if await self._rate_limiter.is_rate_limited():
            logger.debug("Rate limited, queuing notification for later")
            await self._rate_limiter.queue_pending_notification(status)
            return False

        # Send notification
        success = await self._send_notification(status)

        if success:
            await self._rate_limiter.record_notification()
            logger.info(
                f"Sent approval notification: {status.total_pending} pending, "
                f"{status.compliance_warnings} warnings"
            )
        else:
            logger.warning("Failed to send approval notification")
            # Queue for retry
            await self._queue_failed_notification(status)

        return success

    async def _get_queue_status(self) -> QueueStatus:
        """Get current approval queue status from repository."""
        pending_items = await self._queue_repo.get_pending_items()

        by_source_type: dict[str, int] = {}
        by_priority: dict[int, int] = {}
        compliance_warnings = 0
        highest_priority_item = None
        min_priority = 999

        for item in pending_items:
            # Count by source type
            source = item.source_type
            by_source_type[source] = by_source_type.get(source, 0) + 1

            # Count by priority
            priority = item.source_priority
            by_priority[priority] = by_priority.get(priority, 0) + 1

            # Track highest priority
            if priority < min_priority:
                min_priority = priority
                highest_priority_item = str(item.id)

            # Count compliance warnings
            if item.compliance_status == "WARNING":
                compliance_warnings += 1

        return QueueStatus(
            total_pending=len(pending_items),
            by_source_type=by_source_type,
            by_priority=by_priority,
            compliance_warnings=compliance_warnings,
            highest_priority_item=highest_priority_item,
        )

    async def _send_notification(self, status: QueueStatus) -> bool:
        """Send Discord notification via existing client."""
        high_priority_count = status.by_priority.get(1, 0)  # TRENDING = 1

        return await self._discord.send_approval_notification(
            pending_count=status.total_pending,
            high_priority_count=high_priority_count,
            compliance_warnings=status.compliance_warnings,
            dashboard_url=self._config.dashboard_url,
        )

    async def _queue_failed_notification(self, status: QueueStatus) -> None:
        """Queue failed notification for later retry."""
        # Implementation in NotificationQueue
        pass
```

### Rate Limiter Design

**Source:** [project-context.md#Cache-Queue], Redis patterns

```python
# core/notifications/rate_limiter.py

from datetime import datetime, timedelta
from typing import Optional
import json
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)

class NotificationRateLimiter:
    """Rate limiter for approval notifications.

    Uses Redis to track last notification time and enforce
    cooldown period. Supports queuing pending notifications
    during cooldown for batched delivery.

    Attributes:
        redis: Redis client (injected)
        cooldown_minutes: Minimum time between notifications
        key_prefix: Redis key prefix for rate limit data
    """

    KEY_LAST_NOTIFICATION = "approval:notification:last_sent"
    KEY_PENDING_QUEUE = "approval:notification:pending"

    def __init__(
        self,
        redis_client: redis.Redis,
        cooldown_minutes: int = 60,
    ):
        self._redis = redis_client
        self._cooldown = timedelta(minutes=cooldown_minutes)

    async def is_rate_limited(self) -> bool:
        """Check if currently in cooldown period.

        Returns:
            True if rate limited, False if notification can be sent
        """
        last_sent = await self._redis.get(self.KEY_LAST_NOTIFICATION)

        if not last_sent:
            return False

        last_sent_time = datetime.fromisoformat(last_sent.decode())
        cooldown_expires = last_sent_time + self._cooldown

        return datetime.utcnow() < cooldown_expires

    async def record_notification(self) -> None:
        """Record that a notification was just sent."""
        now = datetime.utcnow().isoformat()

        # Set with TTL slightly longer than cooldown for cleanup
        ttl_seconds = int(self._cooldown.total_seconds()) + 60
        await self._redis.setex(
            self.KEY_LAST_NOTIFICATION,
            ttl_seconds,
            now,
        )

        # Clear pending queue since we just sent
        await self._redis.delete(self.KEY_PENDING_QUEUE)

    async def queue_pending_notification(
        self,
        status: "QueueStatus",
    ) -> None:
        """Queue notification data for later batched delivery.

        During cooldown, we accumulate status updates and send
        a batched summary when cooldown expires.
        """
        data = {
            "total_pending": status.total_pending,
            "compliance_warnings": status.compliance_warnings,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._redis.lpush(
            self.KEY_PENDING_QUEUE,
            json.dumps(data),
        )

        # Expire pending queue after 24 hours
        await self._redis.expire(self.KEY_PENDING_QUEUE, 86400)

    async def get_time_until_available(self) -> Optional[timedelta]:
        """Get remaining cooldown time.

        Returns:
            Remaining cooldown time, or None if not rate limited
        """
        last_sent = await self._redis.get(self.KEY_LAST_NOTIFICATION)

        if not last_sent:
            return None

        last_sent_time = datetime.fromisoformat(last_sent.decode())
        cooldown_expires = last_sent_time + self._cooldown
        remaining = cooldown_expires - datetime.utcnow()

        if remaining.total_seconds() <= 0:
            return None

        return remaining
```

### Notification Hook Integration

**Source:** [core/approval/] - Hook into item creation

```python
# core/notifications/hooks.py

from typing import Optional
import logging

from core.approval.models import ApprovalItem
from core.notifications.approval_notifier import ApprovalNotificationService

logger = logging.getLogger(__name__)

async def on_approval_item_created(
    item: ApprovalItem,
    notifier: ApprovalNotificationService,
) -> None:
    """Hook called when a new item enters the approval queue.

    Triggers notification check asynchronously to avoid blocking
    the content submission flow.

    Args:
        item: The newly created approval item
        notifier: Notification service instance
    """
    try:
        # Check for immediate compliance warning notification
        if item.compliance_status == "WARNING":
            logger.info(
                f"Compliance warning on item {item.id}, "
                "checking for immediate notification"
            )

        # Trigger notification check (rate limiting handled internally)
        await notifier.check_and_notify()

    except Exception as e:
        # Never block content submission on notification failure
        logger.error(
            f"Failed to process notification hook for item {item.id}: {e}"
        )
```

### ARQ Background Job

**Source:** [core/scheduling/jobs.py] pattern from Story 4-4/4-5

```python
# core/notifications/jobs.py

from datetime import datetime
import logging

from arq import Retry

logger = logging.getLogger(__name__)

async def process_notification_queue(ctx: dict) -> str:
    """ARQ job to process pending/failed notifications.

    Scheduled to run every 5 minutes. Processes:
    1. Failed notifications queued for retry
    2. Batched notifications after cooldown expiry

    Args:
        ctx: ARQ context with dependencies

    Returns:
        Status string for job result
    """
    from core.notifications.queue import NotificationQueue
    from core.notifications.rate_limiter import NotificationRateLimiter

    queue = ctx["notification_queue"]
    rate_limiter = ctx["notification_rate_limiter"]

    # Check if cooldown has expired and pending notifications exist
    if not await rate_limiter.is_rate_limited():
        pending_count = await queue.get_pending_count()

        if pending_count > 0:
            logger.info(f"Processing {pending_count} pending notifications")
            processed = await queue.process_pending()
            return f"PROCESSED:{processed}"

    # Process failed notifications with backoff
    failed_count = await queue.get_failed_count()

    if failed_count > 0:
        logger.info(f"Retrying {failed_count} failed notifications")
        retried = await queue.retry_failed()
        return f"RETRIED:{retried}"

    return "NO_WORK"
```

### Configuration File

**Source:** [config/] pattern, [project-context.md#Configuration-Loading]

```json
// config/dawo_notifications.json
{
    "approval_notifications": {
        "enabled": true,
        "webhook_url": "${DISCORD_APPROVAL_WEBHOOK_URL}",
        "threshold": 5,
        "cooldown_minutes": 60,
        "dashboard_url": "https://app.imagoeco.com/dawo/approval"
    },
    "publish_notifications": {
        "enabled": true,
        "webhook_url": "${DISCORD_PUBLISH_WEBHOOK_URL}"
    }
}
```

### File Structure (MUST FOLLOW)

**Source:** IMAGO.ECO conventions

```
core/
└── notifications/
    ├── __init__.py                    # (NEW) Module exports
    ├── approval_notifier.py           # (NEW) ApprovalNotificationService
    ├── rate_limiter.py                # (NEW) NotificationRateLimiter
    ├── queue.py                       # (NEW) NotificationQueue for retries
    ├── hooks.py                       # (NEW) Event hooks for notifications
    └── jobs.py                        # (NEW) ARQ background jobs

config/
└── dawo_notifications.json            # (NEW) Notification configuration

integrations/
└── discord/
    ├── __init__.py                    # (EXISTS) - verify exports
    └── client.py                      # (EXISTS) - already has send_approval_notification()

tests/
└── core/notifications/
    ├── __init__.py                    # (NEW)
    ├── test_approval_notifier.py      # (NEW)
    ├── test_rate_limiter.py           # (NEW)
    └── test_queue.py                  # (NEW)
```

### Previous Story Intelligence (from 4-5)

**Source:** [4-5-instagram-graph-api-auto-publishing.md#Completion-Notes]

Key patterns to reuse from Story 4-5:
- Discord notification pattern via existing client
- Rate limiting cooldown (1 minute per error type - adapt to 1 hour here)
- Non-blocking notification sending
- ARQ job queue integration
- Graceful failure handling

Code patterns established:
1. Use Protocol classes for dependency injection
2. Return bool from Discord client methods (success/failure)
3. Log all notification attempts
4. Queue failures for retry
5. Never block main flow on notification failure

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER call Discord webhook without retry wrapper** - Use retry middleware
2. **NEVER hardcode webhook URLs** - Load from config with env var substitution
3. **NEVER block content submission on notification failure** - Fire and forget pattern
4. **NEVER skip rate limiting** - Respect 1 notification per hour limit
5. **NEVER send notifications for every item** - Batch and threshold
6. **NEVER store webhook URLs in code** - Use secrets/config injection

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

```
This story is integration/notification only - NO LLM usage required.
No tier assignment needed.

FORBIDDEN in code/docstrings/comments:
- "haiku", "sonnet", "opus"
- "claude-haiku", "claude-sonnet", "claude-opus"
```

### Edge Cases to Handle

1. **Queue empty when check runs**: Skip notification silently
2. **Threshold exactly met (5 items)**: Send notification
3. **Multiple items submitted rapidly**: Rate limiting batches them
4. **Discord webhook down for hours**: Queue accumulates, sends on recovery
5. **Cooldown expires during webhook outage**: Queue for retry
6. **All items are compliance warnings**: Highlight in notification
7. **Redis unavailable**: Fall back to memory-based rate limiting
8. **Notification sent but dashboard URL broken**: Log warning, notification still useful
9. **Config webhook_url empty**: Log error, disable notifications gracefully
10. **Duplicate notifications in queue**: Dedupe by timestamp

### Test Scenarios (Task 9)

```python
# tests/core/notifications/test_approval_notifier.py

class TestApprovalNotificationService:
    """Tests for approval notification orchestration."""

    async def test_notification_sent_at_threshold(self):
        """Verify notification triggers at exactly threshold."""
        # Mock 5 pending items (threshold)
        # Assert discord.send_approval_notification called once

    async def test_no_notification_below_threshold(self):
        """Verify no notification when below threshold."""
        # Mock 4 pending items (below threshold)
        # Assert discord.send_approval_notification NOT called

    async def test_rate_limiting_prevents_spam(self):
        """Verify rate limiting prevents multiple notifications."""
        # Send first notification (success)
        # Attempt second within cooldown
        # Assert only first was sent

    async def test_compliance_warnings_counted(self):
        """Verify compliance warnings are correctly aggregated."""
        # Mock items with mixed compliance status
        # Assert warning count passed to discord client

    async def test_failure_queued_for_retry(self):
        """Verify failed notifications are queued."""
        # Mock discord client returning False
        # Assert notification added to retry queue

    async def test_non_blocking_on_failure(self):
        """Verify content submission not blocked by notification failure."""
        # Mock discord client raising exception
        # Assert no exception propagated
```

### Project Structure Notes

- **Location**: New `core/notifications/` directory for notification services
- **Dependencies**: Redis (rate limiting), ARQ (background jobs), existing Discord client
- **Integrates with**: Story 4-1 to 4-4 approval queue, Story 4-7 publish notifications
- **Reuses**: `integrations/discord/client.py` - `send_approval_notification()` method
- **Performance target**: < 100ms notification check, non-blocking

### References

- [Source: epics.md#Story-4.6] - Original story requirements (FR40)
- [Source: epics.md#NFR20] - Retry failed Discord notifications 3x with exponential backoff
- [Source: project-context.md#External-API-Calls] - Retry middleware patterns
- [Source: 4-5-instagram-graph-api-auto-publishing.md] - Discord notification patterns
- [Source: integrations/discord/client.py] - Existing send_approval_notification() method
- [Source: core/approval/models.py] - ApprovalItem, ApprovalStatus, ComplianceStatus

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - Implementation completed without blocking issues.

### Completion Notes List

- Implemented complete Discord notification system for approval queue alerts
- Created ApprovalNotificationService with Protocol-based DI for testability
- Implemented NotificationRateLimiter with Redis-backed 1-hour cooldown
- Created NotificationQueue with exponential backoff retry logic (1min, 5min, 15min, 1hr)
- Added event hook on_approval_item_created for triggering notifications
- Created ARQ background job for queue processing every 5 minutes
- Configuration via dawo_notifications.json with env var substitution for webhook URLs
- Leveraged existing DiscordWebhookClient.send_approval_notification() method

**Code Review Fixes (2026-02-09):**
- H1: Connected NotificationQueue to ApprovalNotificationService for failed notification retry
- H2: Added WebSocket event emission (NotificationEventEmitter) for UI notification indicator
- H3: Added Discord-specific rate limit (429) and auth error (401/403) handling
- M2: Replaced deprecated datetime.utcnow() with datetime.now(UTC) across all files
- M3: Exported ARQ jobs and events from core/notifications/__init__.py
- L2: Added integration test for full notification flow
- All 46 unit tests passing covering all acceptance criteria (6 new tests)

### File List

**New Files:**
- core/notifications/__init__.py
- core/notifications/approval_notifier.py
- core/notifications/rate_limiter.py
- core/notifications/queue.py
- core/notifications/hooks.py
- core/notifications/jobs.py
- core/notifications/events.py (WebSocket events - Task 3.6)
- config/dawo_notifications.json
- tests/core/notifications/__init__.py
- tests/core/notifications/test_approval_notifier.py
- tests/core/notifications/test_rate_limiter.py
- tests/core/notifications/test_queue.py
- tests/core/notifications/test_hooks.py
- tests/core/notifications/test_integration.py (integration tests - Task 9.4)

**Modified Files:**
- integrations/discord/client.py (added DiscordRateLimitError, DiscordAuthError - Task 5.5)
- integrations/discord/__init__.py (exported new error classes)
- _bmad-output/implementation-artifacts/sprint-status.yaml (status: done)
- _bmad-output/implementation-artifacts/4-6-discord-approval-notifications.md (this file)

