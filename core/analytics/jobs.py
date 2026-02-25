"""ARQ job definitions for Instagram analytics metrics collection.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 5: ARQ scheduling jobs.

Jobs:
    - collect_metrics_job: Cron job that finds pending posts and collects metrics
    - collect_single_metrics_job: Deferred job for a single post + snapshot_label
    - schedule_metrics_collection: Helper to enqueue deferred jobs after publish

Usage:
    from core.analytics.jobs import schedule_metrics_collection, ANALYTICS_JOB_SETTINGS

    # After successful publish, schedule metrics collection
    job_ids = await schedule_metrics_collection(redis_pool, media_id, published_at)

    # ARQ worker picks up cron and deferred jobs
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def _get_session():
    """Get async database session context manager.

    Imported inside function to avoid circular deps.

    Usage:
        async with _get_session() as session:
            ...
    """
    from core.database import get_async_session

    return get_async_session()


async def _build_collector(
    session=None,
) -> tuple:
    """Build InstagramMetricsCollector with dependencies.

    Imports inside function to avoid circular deps at module load.

    Args:
        session: Optional async session (for repository)

    Returns:
        Tuple of (collector, repository)
    """
    from core.analytics.metrics_collector import InstagramMetricsCollector
    from core.analytics.repository import InstagramMetricsRepository
    from core.config import get_config
    from integrations.instagram import InstagramPublishClient

    config = get_config().analytics

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    client = InstagramPublishClient(
        access_token=access_token,
        business_account_id=account_id,
    )

    repository = InstagramMetricsRepository(session)
    collector = InstagramMetricsCollector(
        client=client,
        repository=repository,
        config=config,
    )

    return collector, repository


def _get_delay_hours(snapshot_label: str) -> int:
    """Get required delay in hours for a snapshot_label.

    Args:
        snapshot_label: Label identifying the collection interval

    Returns:
        Delay in hours before collection is valid
    """
    delays = {
        "baseline": 1,
        "24h": 24,
        "48h": 48,
        "7d": 168,
    }
    return delays.get(snapshot_label, 1)


async def collect_metrics_job(ctx: dict, snapshot_label: str) -> str:
    """Cron job that finds pending posts and collects metrics.

    Task 5.2: Finds published posts that need metrics at the given
    snapshot_label, skips already-collected and too-recent posts,
    then collects metrics in batch.

    Args:
        ctx: ARQ context with Redis connection
        snapshot_label: Collection interval label (e.g., "baseline")

    Returns:
        Job result status string
    """
    logger.info("Running collect_metrics_job for snapshot_label=%s", snapshot_label)

    try:
        from core.approval.models import ApprovalItem, ApprovalStatus
        from sqlalchemy import select
    except ImportError as e:
        logger.error("Failed to import required modules: %s", e)
        return f"IMPORT_ERROR: {e}"

    try:
        async with _get_session() as session:
            collector, repository = await _build_collector(session)

            # Query published posts with instagram_post_id
            query = select(ApprovalItem).where(
                ApprovalItem.instagram_post_id.isnot(None),
                ApprovalItem.status == ApprovalStatus.PUBLISHED.value,
            )
            result = await session.execute(query)
            published_items = result.scalars().all()

            if not published_items:
                logger.info("No published posts found")
                return "NO_WORK"

            # Get media_ids and their published_at times
            media_id_map = {
                item.instagram_post_id: item.published_at
                for item in published_items
            }
            media_ids = list(media_id_map.keys())

            # Check which already have metrics at this snapshot_label
            existing = await repository.get_by_media_ids(media_ids)
            already_collected = set()
            for mid, metrics in existing.items():
                for m in metrics:
                    if m.snapshot_label == snapshot_label:
                        already_collected.add(mid)

            # Filter to posts that haven't been collected yet
            pending_ids = [mid for mid in media_ids if mid not in already_collected]

            # Filter to posts old enough for this snapshot_label
            delay_hours = _get_delay_hours(snapshot_label)
            now = datetime.now(UTC)
            eligible_ids = []
            for mid in pending_ids:
                published_at = media_id_map.get(mid)
                if published_at and (now - published_at) >= timedelta(hours=delay_hours):
                    eligible_ids.append(mid)

            if not eligible_ids:
                logger.info(
                    "No eligible posts for %s (checked %d, already collected %d, too recent %d)",
                    snapshot_label,
                    len(media_ids),
                    len(already_collected),
                    len(pending_ids) - len(eligible_ids),
                )
                return "NO_WORK"

            # Collect metrics
            batch_result = await collector.collect_batch(
                media_ids=eligible_ids,
                snapshot_label=snapshot_label,
            )

            await repository.commit()

            # Send Discord alerts for failures
            if batch_result.failed > 0:
                for mid, error in batch_result.errors.items():
                    await _send_analytics_discord_alert(
                        media_id=mid,
                        snapshot_label=snapshot_label,
                        error=error,
                    )

            logger.info(
                "collect_metrics_job complete: %d/%d collected for %s",
                batch_result.succeeded,
                batch_result.total,
                snapshot_label,
            )
            return f"COLLECTED:{batch_result.succeeded}/{batch_result.total}"

    except Exception as e:
        logger.exception("Error in collect_metrics_job: %s", e)
        return f"ERROR: {e}"


async def collect_single_metrics_job(
    ctx: dict,
    media_id: str,
    snapshot_label: str,
) -> str:
    """Deferred job to collect metrics for a single post.

    Task 5.4 (sub): Called by deferred ARQ jobs enqueued
    after publishing. Each post gets 4 deferred jobs
    (baseline, 24h, 48h, 7d).

    Args:
        ctx: ARQ context with Redis connection
        media_id: Instagram media ID
        snapshot_label: Collection interval label

    Returns:
        Job result status string
    """
    logger.info(
        "Collecting metrics for media_id=%s, snapshot_label=%s",
        media_id,
        snapshot_label,
    )

    try:
        async with _get_session() as session:
            collector, repository = await _build_collector(session)

            result = await collector.collect_metrics(
                media_id=media_id,
                snapshot_label=snapshot_label,
            )

            await repository.commit()

            if result.success:
                logger.info(
                    "Successfully collected %s metrics for %s",
                    snapshot_label,
                    media_id,
                )
                return "COLLECTED"
            else:
                logger.warning(
                    "Failed to collect %s metrics for %s: %s",
                    snapshot_label,
                    media_id,
                    result.error_message,
                )
                await _send_analytics_discord_alert(
                    media_id=media_id,
                    snapshot_label=snapshot_label,
                    error=result.error_message or "Unknown error",
                )
                return "FAILED"

    except Exception as e:
        logger.exception(
            "Error collecting metrics for %s (%s): %s",
            media_id,
            snapshot_label,
            e,
        )
        await _send_analytics_discord_alert(
            media_id=media_id,
            snapshot_label=snapshot_label,
            error=str(e),
        )
        return f"ERROR: {e}"


async def schedule_metrics_collection(
    redis_pool,
    media_id: str,
    published_at: datetime,
) -> list[str]:
    """Enqueue deferred metrics collection jobs after publish.

    Task 5.4: Enqueues 4 deferred jobs at T+1h, T+24h, T+48h, T+7d.
    Called from schedule_publish_job after successful Instagram publish.

    Args:
        redis_pool: ARQ Redis pool
        media_id: Instagram media ID
        published_at: When the post was published

    Returns:
        List of enqueued job IDs (may be partial on failure)
    """
    intervals = [
        ("baseline", 1),
        ("24h", 24),
        ("48h", 48),
        ("7d", 168),
    ]

    job_ids: list[str] = []

    for label, delay_hours in intervals:
        defer_until = published_at + timedelta(hours=delay_hours)
        try:
            job = await redis_pool.enqueue_job(
                "collect_single_metrics_job",
                media_id,
                label,
                _defer_until=defer_until,
            )
            job_ids.append(job.job_id)
            logger.info(
                "Enqueued metrics job for %s (%s) at %s",
                media_id,
                label,
                defer_until.isoformat(),
            )
        except Exception as e:
            logger.error(
                "Failed to enqueue metrics job for %s (%s): %s",
                media_id,
                label,
                e,
            )

    logger.info(
        "Scheduled %d/%d metrics collection jobs for %s",
        len(job_ids),
        len(intervals),
        media_id,
    )
    return job_ids


async def _send_analytics_discord_alert(
    media_id: str,
    snapshot_label: str,
    error: str,
) -> None:
    """Send Discord notification for metrics collection failure.

    Task 5.6: Reuses Discord pattern from core/scheduling/jobs.py.

    Args:
        media_id: Instagram media ID that failed
        snapshot_label: Collection interval that failed
        error: Error message
    """
    webhook_url = os.environ.get("DISCORD_ANALYTICS_WEBHOOK_URL", "")
    if not webhook_url:
        logger.debug("Discord analytics webhook URL not configured, skipping alert")
        return

    try:
        from integrations.discord import DiscordWebhookClient

        message = (
            f"**Analytics Collection Failed**\n"
            f"Media ID: `{media_id}`\n"
            f"Snapshot: `{snapshot_label}`\n"
            f"Error: {error}"
        )

        async with DiscordWebhookClient(webhook_url) as discord:
            await discord.send_message(content=message)

        logger.info(
            "Discord alert sent for failed collection: %s (%s)",
            media_id,
            snapshot_label,
        )
    except Exception as e:
        # Don't block on Discord failure
        logger.warning("Failed to send Discord alert: %s", e)


# Task 5.3: Cron schedule configuration
# Each snapshot_label has a cron safety net in case deferred jobs fail.
# Primary collection is via deferred jobs from schedule_metrics_collection.
# Cron frequency: baseline=hourly, 24h/48h=every 6h, 7d=every 12h.
ANALYTICS_JOB_SETTINGS = {
    "cron_jobs": [
        {
            "name": "collect_baseline_metrics",
            "coroutine": collect_metrics_job,
            "minute": {0},  # Top of every hour
            "kwargs": {"snapshot_label": "baseline"},
        },
        {
            "name": "collect_24h_metrics",
            "coroutine": collect_metrics_job,
            "hour": {0, 6, 12, 18},
            "minute": {15},
            "kwargs": {"snapshot_label": "24h"},
        },
        {
            "name": "collect_48h_metrics",
            "coroutine": collect_metrics_job,
            "hour": {0, 6, 12, 18},
            "minute": {30},
            "kwargs": {"snapshot_label": "48h"},
        },
        {
            "name": "collect_7d_metrics",
            "coroutine": collect_metrics_job,
            "hour": {0, 12},
            "minute": {45},
            "kwargs": {"snapshot_label": "7d"},
        },
    ],
    "functions": [
        collect_metrics_job,
        collect_single_metrics_job,
    ],
}


__all__ = [
    "collect_metrics_job",
    "collect_single_metrics_job",
    "schedule_metrics_collection",
    "ANALYTICS_JOB_SETTINGS",
]
