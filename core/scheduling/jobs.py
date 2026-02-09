"""ARQ job definitions for content scheduling.

Story 4-4, Task 8: ARQ job queue integration for scheduled publishing.
Story 4-5: Extended with actual Instagram publishing via InstagramPublisher.

Jobs:
    - schedule_publish_job: Triggers publishing at scheduled time
    - cancel_publish_job: Cancels a scheduled publish job
    - update_publish_job: Updates job when rescheduled

Usage:
    from core.scheduling.jobs import schedule_publish_job, WorkerSettings

    # Schedule a job
    job = await arq_pool.enqueue_job(
        "schedule_publish_job",
        item_id=item_id,
        publish_time=publish_time,
        _defer_until=publish_time,
    )
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Job timeout for publishing (30s API + 30s buffer)
PUBLISH_JOB_TIMEOUT = 60

# Story 4-5, Task 5.6: Discord rate limiting - track last alert per error type
_discord_alert_timestamps: dict[str, datetime] = {}
DISCORD_RATE_LIMIT_SECONDS = 60  # 1 minute between same error type


async def _emit_publish_event(
    item_id: str,
    event_type: str,
    data: dict,
) -> None:
    """Emit a publishing event to subscribed clients.

    Story 4-5, Task 3.6: WebSocket event emission.

    Args:
        item_id: Approval item ID
        event_type: Event type (publish_success, publish_failed, etc.)
        data: Event payload data
    """
    try:
        from core.publishing.events import publish_events, PublishEvent, PublishEventType

        event_type_enum = PublishEventType(event_type)
        event = PublishEvent(
            event_type=event_type_enum,
            item_id=item_id,
            data=data,
        )
        await publish_events.emit(event)
        logger.debug("Emitted %s event for item %s", event_type, item_id)
    except Exception as e:
        # Don't block on event emission failure
        logger.warning("Failed to emit publish event: %s", e)


async def schedule_publish_job(
    ctx: dict,
    item_id: str,
    publish_time: datetime,
) -> str:
    """Job to trigger publishing at scheduled time.

    Story 4-4, Task 8.1: schedule_publish_job function for ARQ.
    Story 4-5: Extended with actual Instagram publishing.

    Called by ARQ worker at scheduled_publish_time.
    Transitions item: SCHEDULED -> PUBLISHING -> PUBLISHED/PUBLISH_FAILED

    Flow:
    1. Load ApprovalItem
    2. Set status to PUBLISHING
    3. Call InstagramPublisher
    4. On success: Set PUBLISHED, store instagram_post_id
    5. On failure: Set PUBLISH_FAILED, send Discord alert

    Args:
        ctx: ARQ context with Redis connection
        item_id: Approval item to publish
        publish_time: Scheduled time (for logging)

    Returns:
        Job result status: "PUBLISHED", "PUBLISH_FAILED", "ITEM_NOT_FOUND", etc.
    """
    logger.info(
        "Publishing job triggered for item %s (scheduled: %s)",
        item_id,
        publish_time.isoformat(),
    )

    try:
        # Import here to avoid circular deps
        from core.approval.models import ApprovalItem, ApprovalStatus
        from core.database import get_async_session
        from core.publishing import InstagramPublisher
        from integrations.instagram import InstagramPublishClient
        from integrations.discord import DiscordWebhookClient
        from teams.dawo.middleware.retry import RetryMiddleware, RetryConfig
        from sqlalchemy import select
        import os
    except ImportError as e:
        logger.error("Failed to import required modules: %s", e)
        return "IMPORT_ERROR"

    try:
        async with get_async_session() as session:
            # Fetch the item
            query = select(ApprovalItem).where(ApprovalItem.id == UUID(item_id))
            result = await session.execute(query)
            item = result.scalar_one_or_none()

            if not item:
                logger.error("Item not found: %s", item_id)
                return "ITEM_NOT_FOUND"

            # Validate status
            if item.status != ApprovalStatus.SCHEDULED.value:
                logger.warning(
                    "Item %s not in SCHEDULED status: %s",
                    item_id,
                    item.status,
                )
                return "INVALID_STATUS"

            # Story 4-5, Task 3.2: Set PUBLISHING intermediate status
            item.status = ApprovalStatus.PUBLISHING.value
            item.publish_attempts = (item.publish_attempts or 0) + 1
            item.updated_at = datetime.utcnow()
            await session.commit()

            logger.info("Item %s status set to PUBLISHING", item_id)

            # Initialize Instagram client and publisher
            access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
            account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

            if not access_token or not account_id:
                error_msg = "Instagram credentials not configured"
                logger.error(error_msg)
                item.status = ApprovalStatus.PUBLISH_FAILED.value
                item.publish_error = error_msg
                await session.commit()
                return "CONFIG_ERROR"

            instagram_client = InstagramPublishClient(
                access_token=access_token,
                business_account_id=account_id,
            )

            retry_config = RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=4.0,
                backoff_multiplier=2.0,
            )
            retry_middleware = RetryMiddleware(retry_config)
            publisher = InstagramPublisher(instagram_client, retry_middleware)

            # Execute publish
            publish_result = await publisher.publish(
                image_url=item.thumbnail_url,
                caption=item.full_caption,
                hashtags=item.hashtags if item.hashtags else None,
            )

            if publish_result.success:
                # Story 4-5, Task 3.3-3.5: Update with success
                item.status = ApprovalStatus.PUBLISHED.value
                item.instagram_post_id = publish_result.instagram_post_id
                item.instagram_permalink = publish_result.permalink
                item.published_at = publish_result.published_at
                item.publish_error = None
                item.updated_at = datetime.utcnow()
                await session.commit()

                logger.info(
                    "Successfully published item %s: %s",
                    item_id,
                    publish_result.permalink,
                )

                # Story 4-5, Task 3.6: Emit WebSocket event on publish success
                await _emit_publish_event(
                    item_id=item_id,
                    event_type="publish_success",
                    data={
                        "instagram_post_id": publish_result.instagram_post_id,
                        "permalink": publish_result.permalink,
                        "published_at": (
                            publish_result.published_at.isoformat()
                            if publish_result.published_at
                            else None
                        ),
                    },
                )

                await instagram_client.close()
                return "PUBLISHED"
            else:
                # Story 4-5, Task 4.4-4.6: Update with failure
                item.status = ApprovalStatus.PUBLISH_FAILED.value
                item.publish_error = publish_result.error_message
                item.updated_at = datetime.utcnow()
                await session.commit()

                logger.error(
                    "Failed to publish item %s: %s",
                    item_id,
                    publish_result.error_message,
                )

                # Story 4-5, Task 3.6: Emit WebSocket event on publish failure
                await _emit_publish_event(
                    item_id=item_id,
                    event_type="publish_failed",
                    data={
                        "error": publish_result.error_message,
                        "retry_allowed": publish_result.retry_allowed,
                    },
                )

                # Story 4-5, Task 5: Send Discord alert (with rate limiting)
                await _send_discord_failure_alert(
                    item_title=item.full_caption[:100],
                    error=publish_result.error_message or "Unknown error",
                    item_id=item_id,
                )

                await instagram_client.close()
                return "PUBLISH_FAILED"

    except Exception as e:
        logger.exception("Error in schedule_publish_job for item %s: %s", item_id, e)

        # Try to update item status to PUBLISH_FAILED
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
            from core.database import get_async_session
            from sqlalchemy import select

            async with get_async_session() as session:
                query = select(ApprovalItem).where(ApprovalItem.id == UUID(item_id))
                result = await session.execute(query)
                item = result.scalar_one_or_none()
                if item:
                    item.status = ApprovalStatus.PUBLISH_FAILED.value
                    item.publish_error = str(e)
                    item.updated_at = datetime.utcnow()
                    await session.commit()
        except Exception:
            logger.exception("Failed to update item status after error")

        return f"ERROR: {str(e)}"


async def _send_discord_failure_alert(
    item_title: str,
    error: str,
    item_id: str,
) -> None:
    """Send Discord notification for publish failure.

    Story 4-5, Task 5: Discord failure notifications.
    Story 4-5, Task 5.6: Rate limit alerts (max 1 per minute for same error type).

    Args:
        item_title: Title/excerpt of the failed post
        error: Error message
        item_id: Item ID for dashboard link
    """
    import os

    # Story 4-5, Task 5.6: Rate limiting - extract error type for deduplication
    error_type = _extract_error_type(error)
    now = datetime.utcnow()

    # Check rate limit
    last_alert = _discord_alert_timestamps.get(error_type)
    if last_alert and (now - last_alert).total_seconds() < DISCORD_RATE_LIMIT_SECONDS:
        logger.debug(
            "Discord alert rate-limited for error type '%s' (last sent %ds ago)",
            error_type,
            (now - last_alert).total_seconds(),
        )
        return

    try:
        from integrations.discord import DiscordWebhookClient

        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
        if not webhook_url:
            logger.warning("Discord webhook URL not configured, skipping alert")
            return

        async with DiscordWebhookClient(webhook_url) as discord:
            await discord.send_publish_notification(
                post_title=item_title,
                success=False,
                error_message=error,
            )

        # Update rate limit timestamp
        _discord_alert_timestamps[error_type] = now
        logger.info("Discord failure alert sent for item %s", item_id)

    except Exception as e:
        # Don't block on Discord failure
        logger.warning("Failed to send Discord alert: %s", e)


def _extract_error_type(error: str) -> str:
    """Extract error type for rate limiting deduplication.

    Story 4-5, Task 5.6: Categorize errors for rate limiting.

    Args:
        error: Error message string

    Returns:
        Normalized error type key
    """
    error_lower = error.lower()

    # Map common errors to types
    if "rate limit" in error_lower:
        return "rate_limit"
    if "access token" in error_lower or "auth" in error_lower:
        return "auth_error"
    if "timeout" in error_lower:
        return "timeout"
    if "network" in error_lower or "connection" in error_lower:
        return "network_error"
    if "invalid media" in error_lower or "image" in error_lower:
        return "media_error"
    if "policy" in error_lower or "violation" in error_lower:
        return "policy_violation"

    # Default: use first 50 chars as key
    return f"other:{error[:50]}"


async def cancel_publish_job(
    ctx: dict,
    item_id: str,
    job_id: str,
) -> str:
    """Cancel a scheduled publish job.

    Story 4-4, Task 8.5: Cancel job when item is unscheduled.

    Args:
        ctx: ARQ context with Redis connection
        item_id: Item being unscheduled
        job_id: ARQ job ID to cancel

    Returns:
        Job result status
    """
    logger.info("Cancelling publish job %s for item %s", job_id, item_id)

    try:
        from arq.jobs import Job

        redis = ctx.get("redis")
        if not redis:
            logger.error("Redis connection not available in context")
            return "NO_REDIS"

        job = Job(job_id, redis)
        await job.abort()

        logger.info("Successfully cancelled job %s", job_id)
        return "CANCELLED"

    except Exception as e:
        logger.exception("Error cancelling job %s: %s", job_id, e)
        return f"ERROR: {str(e)}"


async def get_scheduled_jobs_status(
    ctx: dict,
    item_ids: list[str],
) -> dict[str, dict]:
    """Get status of scheduled jobs for items.

    Story 4-4, Task 8.6: get_scheduled_jobs utility.

    Args:
        ctx: ARQ context with Redis connection
        item_ids: List of item IDs to check

    Returns:
        Dict mapping item_id to job status info
    """
    logger.debug("Checking job status for %d items", len(item_ids))

    try:
        from core.approval.models import ApprovalItem
        from core.database import get_async_session
        from sqlalchemy import select
    except ImportError as e:
        logger.error("Failed to import required modules: %s", e)
        return {}

    result = {}

    try:
        async with get_async_session() as session:
            # Fetch items with their job IDs
            query = (
                select(ApprovalItem)
                .where(ApprovalItem.id.in_([UUID(id) for id in item_ids]))
            )
            items_result = await session.execute(query)
            items = items_result.scalars().all()

            for item in items:
                item_id = str(item.id)
                result[item_id] = {
                    "status": item.status,
                    "scheduled_time": (
                        item.scheduled_publish_time.isoformat()
                        if item.scheduled_publish_time
                        else None
                    ),
                    "arq_job_id": getattr(item, "arq_job_id", None),
                }

    except Exception as e:
        logger.exception("Error getting job status: %s", e)

    return result


class WorkerSettings:
    """ARQ worker configuration for scheduling jobs.

    Story 4-4, Task 8.3: Register job in ARQ startup configuration.

    Usage:
        arq worker core.scheduling.jobs.WorkerSettings
    """

    # Redis settings - will be overridden by environment
    redis_settings = None  # Set from config

    # Registered functions
    functions = [
        schedule_publish_job,
        cancel_publish_job,
        get_scheduled_jobs_status,
    ]

    # No cron jobs - all scheduled dynamically
    cron_jobs = []

    # Job settings
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # 1 hour

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Called when worker starts."""
        logger.info("ARQ worker started for scheduling jobs")

    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        """Called when worker shuts down."""
        logger.info("ARQ worker shutting down")


async def enqueue_publish_job(
    redis_pool,
    item_id: str,
    publish_time: datetime,
) -> Optional[str]:
    """Helper to enqueue a publish job.

    Story 4-4, Task 8.2: Create job to transition APPROVED -> SCHEDULED.

    Args:
        redis_pool: ARQ Redis pool
        item_id: Item to publish
        publish_time: When to publish

    Returns:
        Job ID if successful, None otherwise
    """
    try:
        job = await redis_pool.enqueue_job(
            "schedule_publish_job",
            item_id,
            publish_time,
            _defer_until=publish_time,
        )
        logger.info(
            "Enqueued publish job %s for item %s at %s",
            job.job_id,
            item_id,
            publish_time.isoformat(),
        )
        return job.job_id
    except Exception as e:
        logger.exception("Failed to enqueue publish job: %s", e)
        return None


async def update_publish_job(
    redis_pool,
    item_id: str,
    old_job_id: str,
    new_publish_time: datetime,
) -> Optional[str]:
    """Update a publish job when rescheduled.

    Story 4-4, Task 8.4: Update job when publish time is rescheduled.

    Args:
        redis_pool: ARQ Redis pool
        item_id: Item being rescheduled
        old_job_id: Previous job ID to cancel
        new_publish_time: New publish time

    Returns:
        New job ID if successful, None otherwise
    """
    try:
        from arq.jobs import Job

        # Cancel old job
        if old_job_id:
            old_job = Job(old_job_id, redis_pool)
            await old_job.abort()
            logger.info("Cancelled old job %s", old_job_id)

        # Enqueue new job
        new_job_id = await enqueue_publish_job(redis_pool, item_id, new_publish_time)
        return new_job_id

    except Exception as e:
        logger.exception("Failed to update publish job: %s", e)
        return None


__all__ = [
    "schedule_publish_job",
    "cancel_publish_job",
    "get_scheduled_jobs_status",
    "WorkerSettings",
    "enqueue_publish_job",
    "update_publish_job",
]
