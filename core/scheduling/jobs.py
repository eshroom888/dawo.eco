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
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Callable, Optional
from uuid import UUID

from arq import cron

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


async def _schedule_post_metrics(
    ctx: dict,
    instagram_post_id: str,
    published_at: Optional[datetime],
) -> None:
    """Schedule metrics collection after successful publish.

    Story 7-1, Task 6: Fire-and-forget metrics scheduling.
    If scheduling fails, it doesn't block the publish flow.
    The cron job in core/analytics/jobs.py serves as a safety net.

    Args:
        ctx: ARQ context with Redis connection
        instagram_post_id: Instagram media ID
        published_at: When the post was published
    """
    try:
        from core.analytics.jobs import schedule_metrics_collection

        redis = ctx.get("redis")
        if not redis:
            logger.warning("No Redis in context, skipping metrics scheduling")
            return

        pub_time = published_at or datetime.now(UTC)
        job_ids = await schedule_metrics_collection(
            redis, instagram_post_id, pub_time
        )
        logger.info(
            "Scheduled %d metrics collection jobs for %s",
            len(job_ids),
            instagram_post_id,
        )
    except Exception as e:
        # Don't block publishing on metrics scheduling failure
        logger.warning("Failed to schedule metrics collection: %s", e)


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
            item.updated_at = datetime.now(UTC)
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
                item.updated_at = datetime.now(UTC)
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

                # Story 7-1, Task 6: Schedule metrics collection after publish
                if publish_result.instagram_post_id:
                    await _schedule_post_metrics(
                        ctx,
                        publish_result.instagram_post_id,
                        publish_result.published_at,
                    )

                # Story 7-9, Task 6.2: Calendar sync on publish success (fire-and-forget)
                try:
                    redis = ctx.get("redis")
                    if redis:
                        await redis.enqueue_job(
                            "sync_calendar_event",
                            item_id,
                            "published",
                            instagram_url=publish_result.permalink or "",
                        )
                except Exception:
                    logger.warning("Calendar sync enqueue failed for item %s", item_id)

                await instagram_client.close()
                return "PUBLISHED"
            else:
                # Story 4-5, Task 4.4-4.6: Update with failure
                item.status = ApprovalStatus.PUBLISH_FAILED.value
                item.publish_error = publish_result.error_message
                item.updated_at = datetime.now(UTC)
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

                # Story 7-9, Task 6.4: Calendar sync on publish failure (fire-and-forget)
                try:
                    redis = ctx.get("redis")
                    if redis:
                        await redis.enqueue_job(
                            "sync_calendar_event",
                            item_id,
                            "failed",
                            error=publish_result.error_message or "Unknown error",
                        )
                except Exception:
                    logger.warning("Calendar sync enqueue failed for item %s", item_id)

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
                    item.updated_at = datetime.now(UTC)
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
    now = datetime.now(UTC)

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


async def _run_shopify_attribution_poll(ctx: dict) -> dict:
    """ARQ cron job for Shopify order attribution polling.

    Story 7-3, Task 6.4: Hourly polling fallback for missed webhooks.
    Imports lazily to avoid circular dependencies.

    Args:
        ctx: ARQ context

    Returns:
        Dict with succeeded, failed, error counts
    """
    try:
        from ui.backend.routers.webhooks import poll_shopify_orders
        from integrations.shopify.client import ShopifyClient
        from core.analytics.attribution_service import AttributionService
        from core.analytics.attribution_repository import AttributionRepository
        from core.analytics.utm_repository import UTMRepository
        from core.database import get_async_session
        from core.config import get_config
        import os

        config = get_config()

        # Build Shopify client
        shopify_client = ShopifyClient(
            store_domain=os.environ.get("SHOPIFY_SHOP_DOMAIN", ""),
            access_token=os.environ.get("SHOPIFY_ACCESS_TOKEN", ""),
        )

        async with get_async_session() as session:
            attr_repo = AttributionRepository(session)
            utm_repo = UTMRepository(session)
            service = AttributionService(attr_repo, utm_repo, config.attribution)

            result = await poll_shopify_orders(
                shopify_client=shopify_client,
                attribution_service=service,
                hours_back=config.attribution.polling_interval_hours + 1,
            )
            await session.commit()

        return result

    except Exception as e:
        logger.warning("Shopify attribution poll failed: %s", e)
        return {"succeeded": 0, "failed": 0, "error": str(e)}


async def _run_post_publish_scoring(ctx: dict) -> dict:
    """ARQ cron job for post-publish quality scoring.

    Story 7-4, Task 7.4: Scheduled scoring of recently published posts.
    Runs daily, scores posts that reached the 7-day maturity window.

    Imports lazily to avoid circular dependencies.

    Args:
        ctx: ARQ context

    Returns:
        Dict with scored, failed, skipped counts
    """
    try:
        from decimal import Decimal
        from core.analytics.quality_scoring_service import PostPublishScoringService
        from core.analytics.quality_scoring_repository import QualityScoringRepository
        from core.analytics.comment_sentiment import CommentSentimentScorer
        from core.database import get_async_session
        from core.config import get_config
        from integrations.instagram import InstagramPublishClient
        import os

        config = get_config()
        qs_config = config.quality_scoring

        # Build dependencies
        access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

        instagram_client = None
        if access_token and account_id:
            instagram_client = InstagramPublishClient(
                access_token=access_token,
                business_account_id=account_id,
            )

        async with get_async_session() as session:
            repository = QualityScoringRepository(session)
            sentiment_scorer = CommentSentimentScorer()

            # Lazy import services from earlier stories
            try:
                from core.analytics.metrics_query import MetricsQueryService
                from core.analytics.click_analytics import ClickAnalyticsService
                from core.analytics.attribution_service import AttributionService
                from core.analytics.attribution_repository import AttributionRepository
                from core.analytics.utm_repository import UTMRepository
                from core.analytics.repository import InstagramMetricsRepository

                metrics_repo = InstagramMetricsRepository(session)
                metrics_query = MetricsQueryService(metrics_repo)
                utm_repo = UTMRepository(session)
                attr_repo = AttributionRepository(session)
                click_analytics = ClickAnalyticsService(utm_repo)
                revenue_analytics = AttributionService(attr_repo, utm_repo, config.attribution)
            except ImportError as e:
                logger.warning("Analytics services not available: %s", e)
                return {"scored": 0, "failed": 0, "error": str(e)}

            service = PostPublishScoringService(
                metrics_query_service=metrics_query,
                click_analytics_service=click_analytics,
                revenue_analytics_service=revenue_analytics,
                comment_sentiment_scorer=sentiment_scorer,
                quality_scoring_repository=repository,
                config=qs_config,
                instagram_client=instagram_client,
            )

            # Find posts ready for scoring (published 7+ days ago)
            from core.approval.models import ApprovalItem, ApprovalStatus
            from sqlalchemy import select
            from datetime import timedelta

            cutoff = datetime.now(UTC) - timedelta(days=qs_config.scoring_delay_days)
            stmt = (
                select(ApprovalItem)
                .where(
                    ApprovalItem.status == ApprovalStatus.PUBLISHED.value,
                    ApprovalItem.published_at <= cutoff,
                    ApprovalItem.instagram_post_id.isnot(None),
                )
                .limit(50)
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

            # Batch check for already-scored posts (prevents N+1)
            item_ids = [str(item.id) for item in items]
            already_scored = await repository.get_by_post_ids(item_ids)

            scored = 0
            failed = 0
            for item in items:
                post_id = str(item.id)
                # Skip if already scored
                if post_id in already_scored:
                    continue

                try:
                    # Pass pre_publish_score from approval item for variance calc
                    pre_score = (
                        Decimal(str(item.quality_score))
                        if getattr(item, "quality_score", None) is not None
                        else None
                    )
                    score_result = await service.score_post(
                        post_id=post_id,
                        media_id=item.instagram_post_id,
                        pre_publish_score=pre_score,
                    )
                    # Persist result
                    from core.analytics.quality_scoring_models import PostPublishScoreRecord

                    record = PostPublishScoreRecord(
                        post_id=score_result.post_id,
                        media_id=score_result.media_id,
                        pre_publish_score=score_result.pre_publish_score,
                        post_publish_score=score_result.post_publish_score,
                        variance=score_result.variance or 0,
                        component_scores=score_result.component_scores,
                        metrics_snapshot=score_result.metrics_snapshot,
                        flagged_for_review=score_result.flagged_for_review,
                        snapshot_label="7d",
                        calculated_at=score_result.calculated_at,
                    )
                    await repository.save_score(record)
                    scored += 1
                except Exception as e:
                    logger.error("Failed to score post %s: %s", item.id, e)
                    failed += 1

            await session.commit()

        if instagram_client:
            await instagram_client.close()

        logger.info("Post-publish scoring complete: scored=%d, failed=%d", scored, failed)
        return {"scored": scored, "failed": failed, "skipped": len(items) - scored - failed}

    except Exception as e:
        logger.warning("Post-publish scoring job failed: %s", e)
        return {"scored": 0, "failed": 0, "error": str(e)}


def _get_feedback_config():
    """Get FeedbackLoopConfig (lazy import to avoid circular deps)."""
    from core.config import get_config
    return get_config().feedback_loop


async def _run_feedback_loop(ctx: dict) -> dict:
    """ARQ cron job for weekly performance feedback analysis.

    Story 7-5, Task 6.3: Weekly cron (Sunday 04:00 UTC).
    Lazy imports to avoid circular dependencies.
    Builds all dependencies inline with proper session lifecycle
    (same pattern as _run_post_publish_scoring).

    Args:
        ctx: ARQ context

    Returns:
        Dict with status, posts_analyzed, recommendations count.
    """
    config = _get_feedback_config()

    if not config.enabled:
        logger.info("Feedback loop disabled, skipping")
        return {"status": "skipped", "posts_analyzed": 0, "recommendations": 0}

    try:
        from core.analytics.feedback_loop_service import FeedbackLoopService
        from core.analytics.feedback_loop_repository import FeedbackLoopRepository
        from core.analytics.content_performance_analyzer import ContentPerformanceAnalyzer
        from core.analytics.weight_adjuster import WeightAdjuster
        from core.analytics.quality_scoring_repository import QualityScoringRepository
        from core.analytics.quality_scoring_analyzer import VarianceAnalyzer
        from core.analytics.repository import InstagramMetricsRepository
        from core.database import get_async_session
        from core.config import get_config

        full_config = get_config()

        async with get_async_session() as session:
            quality_repo = QualityScoringRepository(session)
            metrics_repo = InstagramMetricsRepository(session)
            feedback_repo = FeedbackLoopRepository(session)
            variance_analyzer = VarianceAnalyzer(quality_repo)

            content_analyzer = ContentPerformanceAnalyzer(quality_repo, metrics_repo)
            weight_adjuster = WeightAdjuster(
                variance_analyzer, feedback_repo, full_config.quality_scoring,
            )

            service = FeedbackLoopService(
                content_analyzer, weight_adjuster, feedback_repo,
                quality_repo, config,
            )

            report = await service.run_weekly_analysis()
            await session.commit()

        logger.info(
            "Feedback loop complete: status=%s, posts=%d",
            report.status, report.total_posts_analyzed,
        )
        return {
            "status": report.status,
            "posts_analyzed": report.total_posts_analyzed,
            "recommendations": len(report.recommendations or []),
        }

    except Exception as e:
        logger.warning("Feedback loop job failed: %s", e)
        return {"status": "error", "posts_analyzed": 0, "error": str(e)}


# === Story 7-6: Agent Schedule Dispatcher ===


@asynccontextmanager
async def _schedule_session():
    """Managed session with AgentScheduleRepository.

    Yields repository with proper session lifecycle.
    Always commits on clean exit — all callers mutate state.
    Rolls back on error via session context manager.

    Yields:
        AgentScheduleRepository bound to a managed session.
    """
    from core.database import get_async_session
    from core.scheduling.schedule_repository import AgentScheduleRepository

    async with get_async_session() as session:
        repo = AgentScheduleRepository(session)
        yield repo
        await session.commit()


@asynccontextmanager
async def _execution_log_session():
    """Managed session with ExecutionLogService.

    Story 7-8, Task 5.2: Separate session for execution log writes.
    Execution log failures must NOT block agent execution.

    Yields:
        ExecutionLogService bound to a managed session.
    """
    from core.database import get_async_session
    from core.scheduling.execution_log_repository import ExecutionLogRepository
    from core.scheduling.execution_log_service import ExecutionLogService
    from core.scheduling.schedule_repository import AgentScheduleRepository

    async with get_async_session() as session:
        log_repo = ExecutionLogRepository(session)
        schedule_repo = AgentScheduleRepository(session)
        service = ExecutionLogService(log_repo, schedule_repo)
        yield service
        await session.commit()


async def _run_health_claims_scanner(ctx: dict) -> dict:
    """Run the EU Health Claims Register Monitor.

    Story 7-6, Task 8.1: Scanner runner with lazy imports.
    """
    try:
        from core.database import get_async_session

        async with get_async_session() as session:
            from teams.dawo.scanners.health_claims.monitor import HealthClaimsMonitor
            from core.config import get_config

            config = get_config()
            monitor = HealthClaimsMonitor(session, config)
            result = await monitor.run()
            await session.commit()
            return {"status": "success", "items_processed": result.get("items_processed", 0), "errors": []}
    except Exception as e:
        logger.warning("Health claims scanner failed: %s", e)
        return {"status": "failed", "items_processed": 0, "errors": [str(e)]}


async def _run_novel_food_scanner(ctx: dict) -> dict:
    """Run the Novel Food Catalogue Monitor.

    Story 7-6, Task 8.1: Scanner runner with lazy imports.
    """
    try:
        from core.database import get_async_session

        async with get_async_session() as session:
            from teams.dawo.scanners.novel_food.monitor import NovelFoodMonitor
            from core.config import get_config

            config = get_config()
            monitor = NovelFoodMonitor(session, config)
            result = await monitor.run()
            await session.commit()
            return {"status": "success", "items_processed": result.get("items_processed", 0), "errors": []}
    except Exception as e:
        logger.warning("Novel food scanner failed: %s", e)
        return {"status": "failed", "items_processed": 0, "errors": [str(e)]}


async def _run_mattilsynet_scanner(ctx: dict) -> dict:
    """Run the Mattilsynet Regulatory Monitor.

    Story 7-6, Task 8.1: Scanner runner with lazy imports.
    """
    try:
        from core.database import get_async_session

        async with get_async_session() as session:
            from teams.dawo.scanners.mattilsynet.monitor import MattilsynetMonitor
            from core.config import get_config

            config = get_config()
            monitor = MattilsynetMonitor(session, config)
            result = await monitor.run()
            await session.commit()
            return {"status": "success", "items_processed": result.get("items_processed", 0), "errors": []}
    except Exception as e:
        logger.warning("Mattilsynet scanner failed: %s", e)
        return {"status": "failed", "items_processed": 0, "errors": [str(e)]}


async def _run_competitor_scanner(ctx: dict) -> dict:
    """Run the Competitor Content Scanner.

    Story 7-6, Task 8.1: Scanner runner with lazy imports.
    """
    try:
        from core.database import get_async_session

        async with get_async_session() as session:
            from teams.dawo.scanners.competitor.scanner import CompetitorScanner
            from core.config import get_config

            config = get_config()
            scanner = CompetitorScanner(session, config)
            result = await scanner.run()
            await session.commit()
            return {"status": "success", "items_processed": result.get("items_processed", 0), "errors": []}
    except Exception as e:
        logger.warning("Competitor scanner failed: %s", e)
        return {"status": "failed", "items_processed": 0, "errors": [str(e)]}


async def _run_lead_scanner(ctx: dict) -> dict:
    """Run the B2B Lead Research Scanner.

    Story 7-6, Task 8.1: Scanner runner with lazy imports.
    """
    try:
        from core.database import get_async_session

        async with get_async_session() as session:
            from teams.dawo.leads.scanner import LeadResearchScanner
            from core.config import get_config

            config = get_config()
            scanner = LeadResearchScanner(session, config)
            result = await scanner.run()
            await session.commit()
            return {"status": "success", "items_processed": result.get("items_processed", 0), "errors": []}
    except Exception as e:
        logger.warning("Lead scanner failed: %s", e)
        return {"status": "failed", "items_processed": 0, "errors": [str(e)]}


# Dispatcher registry: maps agent_name → callable runner
AGENT_RUNNERS: dict[str, Callable] = {
    "health_claims_monitor": _run_health_claims_scanner,
    "novel_food_monitor": _run_novel_food_scanner,
    "mattilsynet_monitor": _run_mattilsynet_scanner,
    "competitor_scanner": _run_competitor_scanner,
    "lead_scanner": _run_lead_scanner,
    "shopify_attribution_poll": _run_shopify_attribution_poll,
    "post_publish_scoring": _run_post_publish_scoring,
    "feedback_loop": _run_feedback_loop,
}


async def _check_due_schedules(ctx: dict) -> dict:
    """Dispatcher cron job: check for due schedules and enqueue execution.

    Story 7-6, Task 5.1: Runs every minute via ARQ cron.
    Queries get_due_schedules(now), enqueues each as _run_scheduled_agent.

    Args:
        ctx: ARQ context with Redis connection

    Returns:
        Dict with checked, dispatched, skipped_running counts.
    """
    from core.scheduling.cron_utils import calculate_next_run

    try:
        redis = ctx.get("redis")
        if not redis:
            logger.warning("No Redis in context, schedule dispatcher cannot enqueue jobs")
            return {"checked": 0, "dispatched": 0, "skipped_running": 0, "error": "no_redis"}

        async with _schedule_session() as repo:
            now = datetime.now(UTC)

            due = await repo.get_due_schedules(now)
            dispatched = 0

            for schedule in due:
                # Calculate next run
                next_run = calculate_next_run(
                    schedule.schedule_cron,
                    schedule.timezone or "UTC",
                    after=now,
                )

                # Mark as running and set next_run
                await repo.update_run_status(
                    agent_name=schedule.agent_name,
                    status="running",
                    duration=None,
                    summary=None,
                    next_run=next_run,
                )

                # Enqueue execution job
                await redis.enqueue_job(
                    "_run_scheduled_agent",
                    schedule.agent_name,
                )

                dispatched += 1

        logger.info(
            "Schedule dispatcher: checked=%d, dispatched=%d",
            len(due), dispatched,
        )
        return {
            "checked": len(due),
            "dispatched": dispatched,
            "skipped_running": 0,
        }

    except Exception as e:
        logger.warning("Schedule dispatcher failed: %s", e)
        return {"checked": 0, "dispatched": 0, "skipped_running": 0, "error": str(e)}


async def _check_pending_triggers(ctx: dict, agent_name: str) -> None:
    """Check and re-enqueue pending manual triggers after agent completion.

    Story 7-7, Task 6.1: After agent completes, check if a manual trigger
    was queued while it was running. If so, re-enqueue for immediate execution.

    Uses lazy import to avoid circular dependencies.

    Args:
        ctx: ARQ context with Redis connection
        agent_name: Agent that just completed
    """
    try:
        # Lazy import to avoid circular deps
        from core.scheduling.manual_trigger_service import pending_trigger_store

        pending = pending_trigger_store.pop(agent_name)
        if pending is not None:
            redis = ctx.get("redis")
            if redis:
                await redis.enqueue_job("_run_scheduled_agent", agent_name, "manual")
                logger.info(
                    "Executing pending manual trigger for %s (queued by %s at %s)",
                    agent_name,
                    pending.triggered_by,
                    pending.queued_at.isoformat(),
                )
            else:
                logger.warning(
                    "Pending trigger for %s but no Redis available to re-enqueue",
                    agent_name,
                )
    except Exception as e:
        # Don't block on pending trigger check failure
        logger.warning("Failed to check pending triggers for %s: %s", agent_name, e)


async def _run_scheduled_agent(
    ctx: dict, agent_name: str, trigger_type: str = "scheduled",
) -> dict:
    """Execute a scheduled agent by name from the dispatcher registry.

    Story 7-6, Task 5.2: Resolves agent runner, executes, updates status.
    Story 7-7, Task 6.1: Checks pending triggers after completion.
    Story 7-8, Task 5.2: Creates execution log, captures log output.

    Args:
        ctx: ARQ context
        agent_name: Agent to execute (must be in AGENT_RUNNERS)
        trigger_type: "scheduled" or "manual" (passed by caller)

    Returns:
        Status dict from agent runner.
    """
    import traceback as tb_module
    from core.scheduling.log_capture import LogCaptureHandler

    start_time = datetime.now(UTC)

    # Validate against registry (never use getattr on user input)
    runner = AGENT_RUNNERS.get(agent_name)
    if runner is None:
        logger.error("Agent runner not found in registry: %s", agent_name)
        try:
            async with _schedule_session() as repo:
                await repo.update_run_status(
                    agent_name=agent_name,
                    status="failed",
                    duration=0.0,
                    summary={"error": f"Agent '{agent_name}' not found in runner registry"},
                    next_run=None,
                )
        except Exception:
            pass
        return {"status": "failed", "error": f"Agent '{agent_name}' not found in runner registry"}

    # Story 7-8: Create execution log entry (must NOT block agent)
    execution_log_id = None
    try:
        async with _execution_log_session() as log_service:
            log_dto = await log_service.start_execution(
                agent_name=agent_name,
                trigger_type=trigger_type,
                triggered_by="operator" if trigger_type == "manual" else "scheduler",
            )
            execution_log_id = log_dto.id
    except Exception as e:
        logger.warning("Failed to create execution log for %s: %s", agent_name, e)

    # Story 7-8, Task 6.2: Emit STARTED event (fire-and-forget)
    try:
        from core.scheduling.execution_events import (
            execution_events,
            ExecutionEvent,
            ExecutionEventType,
        )

        await execution_events.emit(ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            agent_name=agent_name,
            execution_id=str(execution_log_id) if execution_log_id else "",
            data={"trigger_type": trigger_type},
        ))
    except Exception:
        pass  # Never block agent execution

    # Story 7-8: Attach log capture handler
    log_handler = LogCaptureHandler.attach(agent_name)

    try:
        result = await runner(ctx)
        duration = (datetime.now(UTC) - start_time).total_seconds()
        status = result.get("status", "success")

        # Update run status with managed session
        async with _schedule_session() as repo:
            await repo.update_run_status(
                agent_name=agent_name,
                status=status,
                duration=duration,
                summary=result,
                next_run=None,
            )

        logger.info(
            "Agent %s completed: status=%s, duration=%.1fs",
            agent_name, status, duration,
        )

        # Story 7-8: Complete execution log (must NOT block)
        if execution_log_id:
            try:
                async with _execution_log_session() as log_service:
                    await log_service.complete_execution(
                        log_id=execution_log_id,
                        status=status,
                        summary=result,
                        error_message=None,
                        error_traceback=None,
                        log_output=log_handler.get_output(),
                    )
            except Exception as e:
                logger.warning("Failed to complete execution log for %s: %s", agent_name, e)

        # Story 7-8, Task 6.2: Emit COMPLETED event (fire-and-forget)
        try:
            from core.scheduling.execution_events import (
                execution_events,
                ExecutionEvent,
                ExecutionEventType,
            )

            await execution_events.emit(ExecutionEvent(
                event_type=ExecutionEventType.COMPLETED,
                agent_name=agent_name,
                execution_id=str(execution_log_id) if execution_log_id else "",
                data={"status": status, "duration": duration},
            ))
        except Exception:
            pass  # Never block agent execution

        # Story 7-7: Check pending manual triggers after completion
        try:
            await _check_pending_triggers(ctx, agent_name)
        except Exception:
            logger.warning("Pending trigger check failed for %s", agent_name)

        return result

    except Exception as e:
        duration = (datetime.now(UTC) - start_time).total_seconds()
        logger.exception("Agent %s failed: %s", agent_name, e)

        try:
            async with _schedule_session() as repo:
                await repo.update_run_status(
                    agent_name=agent_name,
                    status="failed",
                    duration=duration,
                    summary={"error": str(e)},
                    next_run=None,
                )
        except Exception:
            logger.exception("Failed to update status after agent failure")

        # Story 7-8: Complete execution log with failure details (must NOT block)
        if execution_log_id:
            try:
                async with _execution_log_session() as log_service:
                    await log_service.complete_execution(
                        log_id=execution_log_id,
                        status="failed",
                        summary={"error": str(e)},
                        error_message=str(e),
                        error_traceback=tb_module.format_exc(),
                        log_output=log_handler.get_output(),
                    )
            except Exception as log_err:
                logger.warning("Failed to complete execution log for %s: %s", agent_name, log_err)

        # Story 7-8, Task 6.2: Emit FAILED event (fire-and-forget)
        try:
            from core.scheduling.execution_events import (
                execution_events,
                ExecutionEvent,
                ExecutionEventType,
            )

            await execution_events.emit(ExecutionEvent(
                event_type=ExecutionEventType.FAILED,
                agent_name=agent_name,
                execution_id=str(execution_log_id) if execution_log_id else "",
                data={"error": str(e), "duration": duration},
            ))
        except Exception:
            pass  # Never block agent execution

        # Story 7-7: Check pending triggers even after failure
        try:
            await _check_pending_triggers(ctx, agent_name)
        except Exception:
            logger.warning("Pending trigger check failed for %s", agent_name)

        return {"status": "failed", "error": str(e)}

    finally:
        # Story 7-8: Always detach log handler to prevent resource leak
        log_handler.detach()


async def sync_calendar_event(
    ctx: dict,
    item_id: str,
    action: str,
    **kwargs,
) -> str:
    """ARQ job for Google Calendar sync operations.

    Story 7-9, Task 6.1: Calendar sync job with lazy imports.
    Fire-and-forget — never blocks the calling flow.

    Actions: "scheduled", "published", "rescheduled", "failed", "deleted"

    Args:
        ctx: ARQ context
        item_id: Approval item ID
        action: Sync action to perform
        **kwargs: Additional args (e.g., instagram_url for "published")

    Returns:
        Result string: "SYNCED: <event_id>" or "SYNC_FAILED: <error>"
    """
    try:
        from integrations.google_calendar.client import CalendarClient
        from integrations.google_calendar.credentials_manager import CalendarCredentialsManager
        from integrations.google_calendar.sync_service import CalendarSyncService
        from integrations.google_calendar.event_builder import EventBuilder
        from core.config import get_config
        from core.database import get_async_session
        from core.approval.models import ApprovalItem
        from sqlalchemy import select

        config = get_config().calendar

        if not config.sync_enabled:
            return "SYNC_DISABLED"

        creds_manager = CalendarCredentialsManager(config)
        client = CalendarClient(creds_manager, config)
        builder = EventBuilder(config)
        service = CalendarSyncService(client, builder, config)

        async with get_async_session() as session:
            query = select(ApprovalItem).where(ApprovalItem.id == UUID(item_id))
            result = await session.execute(query)
            item = result.scalar_one_or_none()

            if not item:
                logger.warning("Calendar sync: item %s not found", item_id)
                return "ITEM_NOT_FOUND"

            if action == "scheduled":
                sync_result = await service.sync_scheduled(item)
            elif action == "published":
                instagram_url = kwargs.get("instagram_url", "")
                sync_result = await service.sync_published(item, instagram_url)
            elif action == "rescheduled":
                sync_result = await service.sync_rescheduled(item)
            elif action == "failed":
                error_msg = kwargs.get("error", "Unknown error")
                sync_result = await service.sync_failed(item, error_msg)
            elif action == "deleted":
                await service.remove_event(item)
                return "DELETED"
            else:
                return f"UNKNOWN_ACTION: {action}"

            # Store event_id in DB on success
            if sync_result.event_id and sync_result.status in ("created", "updated"):
                item.google_calendar_event_id = sync_result.event_id
                item.updated_at = datetime.now(UTC)
                await session.commit()

            return f"SYNCED: {sync_result.event_id}"

    except Exception as e:
        logger.warning("Calendar sync failed for item %s: %s", item_id, e)
        return f"SYNC_FAILED: {e}"


async def _process_calendar_sync_queue(ctx: dict) -> dict:
    """Cron job to retry failed calendar syncs.

    Story 7-9, Task 6.5: Runs every 15 minutes.
    Finds approval items with scheduled_publish_time but no calendar event_id.
    Enqueues sync_calendar_event for each (max 20 per run).

    Args:
        ctx: ARQ context with Redis connection

    Returns:
        Dict with queued, skipped counts
    """
    try:
        from core.database import get_async_session
        from core.approval.models import ApprovalItem, ApprovalStatus
        from core.config import get_config
        from sqlalchemy import select

        config = get_config().calendar
        if not config.sync_enabled:
            return {"queued": 0, "skipped": 0, "status": "disabled"}

        redis = ctx.get("redis")
        if not redis:
            return {"queued": 0, "skipped": 0, "error": "no_redis"}

        async with get_async_session() as session:
            stmt = (
                select(ApprovalItem)
                .where(
                    ApprovalItem.scheduled_publish_time.isnot(None),
                    ApprovalItem.google_calendar_event_id.is_(None),
                    ApprovalItem.status.in_([
                        ApprovalStatus.APPROVED.value,
                        "scheduled",
                    ]),
                )
                .limit(20)
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

            queued = 0
            for item in items:
                try:
                    await redis.enqueue_job(
                        "sync_calendar_event",
                        str(item.id),
                        "scheduled",
                    )
                    queued += 1
                except Exception as enq_err:
                    logger.warning(
                        "Failed to enqueue calendar sync for %s: %s",
                        item.id, enq_err,
                    )

        logger.info("Calendar sync queue: queued=%d, total_found=%d", queued, len(items))
        return {"queued": queued, "skipped": len(items) - queued}

    except Exception as e:
        logger.warning("Calendar sync queue processing failed: %s", e)
        return {"queued": 0, "skipped": 0, "error": str(e)}


async def _process_recovery_queue(ctx: dict) -> dict:
    """ARQ cron job for processing recovery queue.

    Story 7-10, Task 4.3: Runs every 5 minutes (recovery_check_interval_seconds).
    Processes queued incomplete operations for recovered (healthy) services.

    Lazy imports to avoid circular dependencies.

    Args:
        ctx: ARQ context

    Returns:
        Dict with per-service recovery results.
    """
    try:
        from core.config import get_config
        from core.degradation.recovery import RecoveryProcessor
        from core.degradation.registry import ServiceHealthRegistry
        from teams.dawo.middleware.operation_queue import OperationQueue

        config = get_config().degradation

        redis = ctx.get("redis")
        if not redis:
            logger.warning("No Redis in context for recovery processing")
            return {"status": "error", "error": "no_redis"}

        registry = ServiceHealthRegistry(config, redis)
        queue = OperationQueue(redis)

        async def enqueue_operation(op):
            """Re-enqueue an operation via ARQ."""
            await redis.enqueue_job(
                "_run_scheduled_agent",
                op.context,
            )

        processor = RecoveryProcessor(
            config=config,
            registry=registry,
            queue=queue,
            job_enqueuer=enqueue_operation,
        )

        results = await processor.process_all_services()

        total_processed = sum(r.processed for r in results)
        total_remaining = sum(r.remaining for r in results)

        if total_processed > 0:
            logger.info(
                "Recovery queue: processed=%d, remaining=%d",
                total_processed,
                total_remaining,
            )

        return {
            "status": "success",
            "processed": total_processed,
            "remaining": total_remaining,
            "services": {r.service_name: r.processed for r in results if r.processed > 0},
        }

    except Exception as e:
        logger.warning("Recovery queue processing failed: %s", e)
        return {"status": "error", "error": str(e)}


class WorkerSettings:
    """ARQ worker configuration for scheduling jobs.

    Story 4-4, Task 8.3: Register job in ARQ startup configuration.
    Story 7-3, Task 6.4: Added Shopify attribution polling.
    Story 7-4, Task 7.4: Added post-publish quality scoring.
    Story 7-5, Task 6.4: Added weekly feedback loop analysis.
    Story 7-6, Task 5.3: Added schedule dispatcher + agent runner.
    Story 7-9, Task 6.1: Added calendar sync job + retry cron.
    Story 7-10, Task 4.3: Added recovery queue processor.

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
        _run_shopify_attribution_poll,
        _run_post_publish_scoring,
        _run_feedback_loop,
        _run_scheduled_agent,
        sync_calendar_event,
    ]

    # Cron jobs — existing hardcoded crons kept as fallback during transition
    cron_jobs = [
        cron(_check_due_schedules, minute=None),  # Every minute — schedule dispatcher
        cron(_run_shopify_attribution_poll, hour=None, minute=0),  # Every hour at :00
        cron(_run_post_publish_scoring, hour=3, minute=0),  # Daily at 03:00 UTC
        cron(_run_feedback_loop, weekday=6, hour=4, minute=0),  # Sunday 04:00 UTC
        cron(_process_calendar_sync_queue, minute={0, 15, 30, 45}),  # Every 15 min
        cron(_process_recovery_queue, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),  # Every 5 min
    ]

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
    "sync_calendar_event",
    "WorkerSettings",
    "enqueue_publish_job",
    "update_publish_job",
    "AGENT_RUNNERS",
]
