"""Instagram metrics collector service.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 4: Metrics collector service.

Orchestrates collection of Instagram engagement metrics by
calling the Instagram client for insights and storing results
via the repository. Handles partial failures gracefully.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional

from core.analytics.models import InstagramMediaMetric
from core.analytics.repository import InstagramMetricsRepository
from core.config import AnalyticsConfig
from integrations.instagram.client import (
    InstagramPublishClientProtocol,
    MediaInsightsResult,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectionResult:
    """Result of a single metrics collection.

    Attributes:
        success: Whether collection succeeded
        media_id: Instagram media ID
        snapshot_label: Collection interval label
        error_message: Error description if failed
    """

    success: bool
    media_id: str
    snapshot_label: str
    error_message: Optional[str] = None


@dataclass(frozen=True)
class BatchCollectionResult:
    """Result of a batch metrics collection.

    Attributes:
        total: Total number of posts in batch
        succeeded: Number of successful collections
        failed: Number of failed collections
        errors: Dict mapping failed media_id to error message
    """

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: dict[str, str] = field(default_factory=dict)


class InstagramMetricsCollector:
    """Service for collecting Instagram engagement metrics.

    Story 7-1, Task 4: Orchestrates metrics collection.

    Constructor injection: client, repository, config.
    Handles partial failures -- successful metrics are stored
    even when some posts fail.

    Attributes:
        _client: Instagram publish client (Protocol-based)
        _repository: Metrics repository for persistence
        _config: Analytics configuration
    """

    def __init__(
        self,
        client: InstagramPublishClientProtocol,
        repository: InstagramMetricsRepository,
        config: AnalyticsConfig,
    ) -> None:
        """Initialize metrics collector.

        Args:
            client: Instagram client for API calls
            repository: Repository for metrics persistence
            config: Analytics configuration
        """
        self._client = client
        self._repository = repository
        self._config = config

    async def collect_metrics(
        self,
        media_id: str,
        snapshot_label: str,
        media_type: Optional[str] = None,
    ) -> CollectionResult:
        """Collect metrics for a single post.

        Task 4.3: Calls client, stores via repo, returns result.

        Args:
            media_id: Instagram media ID
            snapshot_label: Collection interval label (e.g., "baseline")
            media_type: Optional media type for reel-specific metrics

        Returns:
            CollectionResult with success/failure status
        """
        insights = await self._client.get_media_insights(
            media_id=media_id,
            media_type=media_type,
        )

        if not insights.success:
            logger.warning(
                "Failed to collect metrics for %s: %s",
                media_id,
                insights.error_message,
            )
            return CollectionResult(
                success=False,
                media_id=media_id,
                snapshot_label=snapshot_label,
                error_message=insights.error_message,
            )

        # Map insights to model
        metric = InstagramMediaMetric(
            media_id=media_id,
            collected_at=datetime.now(UTC),
            snapshot_label=snapshot_label,
            impressions=insights.impressions,
            reach=insights.reach,
            likes=insights.likes,
            comments=insights.comments,
            saved=insights.saved,
            shares=insights.shares,
            total_interactions=insights.total_interactions,
            plays=insights.plays,
            avg_watch_time_ms=insights.avg_watch_time_ms,
            raw_response=insights.raw_response,
        )

        await self._repository.save_snapshot(metric)

        logger.info(
            "Collected metrics for %s (%s): %d interactions",
            media_id,
            snapshot_label,
            insights.total_interactions,
        )

        return CollectionResult(
            success=True,
            media_id=media_id,
            snapshot_label=snapshot_label,
        )

    async def collect_batch(
        self,
        media_ids: list[str],
        snapshot_label: str,
        media_type: Optional[str] = None,
    ) -> BatchCollectionResult:
        """Collect metrics for multiple posts.

        Task 4.4: Processes all with rate limit awareness.
        Task 4.7: Handles partial failures -- stores successful
        metrics, logs failures, returns mixed results.

        Args:
            media_ids: List of Instagram media IDs
            snapshot_label: Collection interval label
            media_type: Optional media type for reel-specific metrics

        Returns:
            BatchCollectionResult with counts and errors
        """
        if not media_ids:
            return BatchCollectionResult()

        succeeded = 0
        failed = 0
        errors: dict[str, str] = {}

        for media_id in media_ids:
            result = await self.collect_metrics(
                media_id=media_id,
                snapshot_label=snapshot_label,
                media_type=media_type,
            )

            if result.success:
                succeeded += 1
            else:
                failed += 1
                errors[media_id] = result.error_message or "Unknown error"

        logger.info(
            "Batch collection complete: %d/%d succeeded, %d failed",
            succeeded,
            len(media_ids),
            failed,
        )

        return BatchCollectionResult(
            total=len(media_ids),
            succeeded=succeeded,
            failed=failed,
            errors=errors,
        )


__all__ = [
    "InstagramMetricsCollector",
    "CollectionResult",
    "BatchCollectionResult",
]
