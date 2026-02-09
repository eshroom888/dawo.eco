"""ARQ job definitions for notification processing.

Story 4-6: Discord Approval Notifications (Task 7)
Story 4-7: Discord Publish Notifications (Task 5)

Jobs:
    - process_notification_queue: Retries failed notifications
    - check_pending_notifications: Sends batched notifications after cooldown
    - send_daily_publish_summary: Daily publishing summary at configured hour (Story 4-7)
    - process_batch_notifications: Check and send expired batch notifications (Story 4-7)

Usage:
    from core.notifications.jobs import process_notification_queue, send_daily_publish_summary

    # Scheduled by ARQ worker
"""

import logging
from datetime import datetime, date, UTC
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class ApprovalRepoProtocol(Protocol):
    """Protocol for approval repository methods needed by jobs."""

    async def get_daily_publishing_stats(self, for_date: date) -> "DailyStats":
        """Get publishing stats for a specific date."""
        ...

    async def get_top_performing_post(self, for_date: date) -> Optional[dict]:
        """Get top performing post for a specific date."""
        ...


async def process_notification_queue(ctx: dict) -> str:
    """ARQ job to process pending/failed notifications.

    Story 4-6, Task 7.1: Scheduled every 5 minutes.

    Processes:
    1. Failed notifications queued for retry
    2. Batched notifications after cooldown expiry

    Args:
        ctx: ARQ context with dependencies

    Returns:
        Status string for job result
    """
    try:
        from core.notifications.queue import NotificationQueue
        from core.notifications.rate_limiter import NotificationRateLimiter

        queue: Optional[NotificationQueue] = ctx.get("notification_queue")
        rate_limiter: Optional[NotificationRateLimiter] = ctx.get("notification_rate_limiter")

        if not queue or not rate_limiter:
            logger.warning("Notification dependencies not available in context")
            return "DEPENDENCIES_MISSING"

        processed = 0

        # Check if cooldown has expired and pending notifications exist
        if not await rate_limiter.is_rate_limited():
            pending_count = await queue.get_pending_count()

            if pending_count > 0:
                logger.info(f"Processing {pending_count} pending notifications")
                processed = await queue.process_pending()
                if processed > 0:
                    await rate_limiter.record_notification()
                    return f"PROCESSED:{processed}"

        # Process failed notifications with backoff
        failed_count = await queue.get_failed_count()

        if failed_count > 0:
            logger.info(f"Retrying {failed_count} failed notifications")
            retried = await queue.retry_failed()
            return f"RETRIED:{retried}"

        return "NO_WORK"

    except Exception as e:
        logger.error(f"Notification queue job failed: {e}")
        return f"ERROR:{str(e)}"


async def get_notification_queue_depth(ctx: dict) -> dict:
    """Get notification queue health metrics.

    Story 4-6, Task 7.6: Health metric for queue depth.

    Args:
        ctx: ARQ context with dependencies

    Returns:
        Dict with queue depth metrics
    """
    try:
        from core.notifications.queue import NotificationQueue
        from core.notifications.rate_limiter import NotificationRateLimiter

        queue: Optional[NotificationQueue] = ctx.get("notification_queue")
        rate_limiter: Optional[NotificationRateLimiter] = ctx.get("notification_rate_limiter")

        if not queue or not rate_limiter:
            return {"status": "unavailable"}

        pending = await queue.get_pending_count()
        failed = await queue.get_failed_count()
        is_rate_limited = await rate_limiter.is_rate_limited()
        cooldown_remaining = await rate_limiter.get_time_until_available()

        return {
            "status": "healthy",
            "pending_count": pending,
            "failed_count": failed,
            "is_rate_limited": is_rate_limited,
            "cooldown_remaining_seconds": cooldown_remaining.total_seconds() if cooldown_remaining else 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get queue metrics: {e}")
        return {"status": "error", "error": str(e)}


async def send_daily_publish_summary(ctx: dict) -> str:
    """ARQ job to send daily publishing summary notification.

    Story 4-7, Task 5.1: Scheduled to run at configured hour (default 10 PM).
    Summarizes the day's publishing activity.

    Args:
        ctx: ARQ context with dependencies

    Returns:
        Status string for job result
    """
    try:
        discord_client = ctx.get("discord_client")
        approval_repo = ctx.get("approval_repo")

        if not discord_client:
            logger.warning("Discord client not available in context")
            return "DISCORD_MISSING"

        if not approval_repo:
            logger.warning("Approval repo not available in context")
            return "REPO_MISSING"

        today = date.today()

        # Get daily stats
        stats = await approval_repo.get_daily_publishing_stats(today)

        # Skip if no activity
        if stats.published == 0 and stats.failed == 0:
            logger.info("No publishing activity today, skipping summary")
            return "NO_ACTIVITY"

        # Get top performing post if available
        top_post = None
        if stats.published > 0:
            top_post = await approval_repo.get_top_performing_post(today)

        # Send summary notification
        success = await discord_client.send_daily_summary_notification(
            published_count=stats.published,
            pending_count=stats.pending,
            failed_count=stats.failed,
            top_post=top_post,
        )

        if success:
            logger.info(
                f"Sent daily summary: {stats.published} published, "
                f"{stats.pending} pending, {stats.failed} failed"
            )
            return f"SENT:{stats.published}/{stats.pending}/{stats.failed}"
        else:
            logger.warning("Failed to send daily summary notification")
            return "SEND_FAILED"

    except Exception as e:
        logger.error(f"Daily summary job failed: {e}")
        return f"ERROR:{str(e)}"


async def process_batch_notifications(ctx: dict) -> str:
    """ARQ job to process expired batch notifications.

    Story 4-7, Task 5: Runs every 5 minutes to check if any batch
    windows have expired and need to be sent.

    Args:
        ctx: ARQ context with dependencies

    Returns:
        Status string for job result
    """
    try:
        from core.notifications.publish_batcher import PublishBatcher
        from core.notifications.publish_notifier import PublishNotificationService

        batcher: Optional[PublishBatcher] = ctx.get("publish_batcher")
        notifier: Optional[PublishNotificationService] = ctx.get("publish_notifier")

        if not batcher:
            logger.debug("Publish batcher not available in context")
            return "BATCHER_MISSING"

        batch_count = await batcher.get_batch_count()

        if batch_count == 0:
            return "NO_BATCHES"

        # Get and clear the batch - send if any posts are waiting
        posts = await batcher.get_and_clear_batch()

        if posts and notifier:
            # Send the batched notification
            await notifier._send_batched_notification()
            logger.info(f"Sent batch notification with {len(posts)} posts")
            return f"SENT_BATCH:{len(posts)}"

        return "BATCH_NOT_READY"

    except Exception as e:
        logger.error(f"Batch notification job failed: {e}")
        return f"ERROR:{str(e)}"


# Worker settings for ARQ (referenced by worker configuration)
NOTIFICATION_JOB_SETTINGS = {
    "cron_jobs": [
        {
            "name": "process_notification_queue",
            "coroutine": process_notification_queue,
            "minute": {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},  # Every 5 min
        },
        {
            "name": "process_batch_notifications",
            "coroutine": process_batch_notifications,
            "minute": {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},  # Every 5 min
        },
        {
            "name": "send_daily_publish_summary",
            "coroutine": send_daily_publish_summary,
            "hour": {22},  # 10 PM (configurable in deployment)
            "minute": {0},
        },
    ],
    "functions": [
        process_notification_queue,
        get_notification_queue_depth,
        send_daily_publish_summary,
        process_batch_notifications,
    ],
}


__all__ = [
    "process_notification_queue",
    "get_notification_queue_depth",
    "send_daily_publish_summary",
    "process_batch_notifications",
    "NOTIFICATION_JOB_SETTINGS",
]
