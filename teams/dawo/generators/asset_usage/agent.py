"""Asset Usage Tracker agent.

Tracks asset usage and performance across published content.
Records when assets are used in posts, collects performance metrics,
calculates performance scores, and provides asset suggestions based
on historical performance data.

Uses 'generate' tier (defaults to configured model) for consistency.
Configuration is received via dependency injection - NEVER loads config directly.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Protocol

from integrations.google_drive import GoogleDriveClientProtocol

from .constants import ASSET_FOLDERS
from .repository import AssetUsageRepositoryProtocol
from .schemas import (
    ArchiveRecord,
    AssetStatus,
    AssetSuggestion,
    AssetType,
    AssetUsageRecord,
    PerformanceMetrics,
    Platform,
    UsageEvent,
)
from .scoring import calculate_overall_performance, calculate_performance_score


logger = logging.getLogger(__name__)


class AssetUsageTrackerProtocol(Protocol):
    """Protocol for asset usage tracker.

    Defines the public interface for tracking asset usage and performance.
    """

    async def record_usage(
        self,
        asset_id: str,
        post_id: str,
        platform: Platform,
        publish_date: datetime,
    ) -> UsageEvent:
        """Record asset usage in a published post.

        Args:
            asset_id: Unique asset identifier
            post_id: Published post identifier
            platform: Publishing platform
            publish_date: When the post was published

        Returns:
            UsageEvent record
        """
        ...

    async def update_performance(
        self,
        asset_id: str,
        post_id: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Update performance metrics for an asset usage.

        Args:
            asset_id: Asset identifier
            post_id: Post identifier for the usage
            metrics: Performance metrics collected
        """
        ...

    async def get_usage_stats(
        self,
        asset_id: str,
    ) -> AssetUsageRecord:
        """Get usage statistics for an asset.

        Args:
            asset_id: Asset identifier

        Returns:
            AssetUsageRecord with full usage history
        """
        ...

    async def suggest_assets(
        self,
        topic: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        unused_days_threshold: Optional[int] = None,
        limit: int = 10,
    ) -> list[AssetSuggestion]:
        """Get suggested assets sorted by performance.

        Args:
            topic: Filter by content topic (optional)
            asset_type: Filter by asset type (optional)
            unused_days_threshold: Only include assets unused for this many days (optional)
            limit: Maximum suggestions to return

        Returns:
            List of AssetSuggestion sorted by performance score (descending)
        """
        ...

    async def archive_asset(
        self,
        asset_id: str,
    ) -> ArchiveRecord:
        """Archive asset while preserving performance history.

        Args:
            asset_id: Asset identifier

        Returns:
            ArchiveRecord with preserved history
        """
        ...


class AssetUsageTracker:
    """Tracks asset usage and performance across published content.

    Records when assets are used in posts, collects performance metrics,
    calculates performance scores, and provides asset suggestions based
    on historical performance data.

    Uses 'generate' tier (defaults to configured model) for consistency.
    Configuration is received via dependency injection - NEVER loads config directly.
    """

    def __init__(
        self,
        drive_client: GoogleDriveClientProtocol,
        repository: AssetUsageRepositoryProtocol,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            drive_client: Google Drive client for asset operations
            repository: Storage layer for usage records
        """
        self._drive = drive_client
        self._repository = repository

    async def register_asset(
        self,
        asset_id: str,
        asset_type: AssetType,
        file_path: str,
        quality_score: float,
        topic: str,
    ) -> AssetUsageRecord:
        """Register a new asset for tracking.

        Called when content is generated (Story 3.4 or 3.5).

        Args:
            asset_id: Unique asset identifier
            asset_type: Type of asset (Orshot/Nano Banana)
            file_path: Google Drive path to asset
            quality_score: Original quality score from generator
            topic: Content topic for filtering

        Returns:
            Created AssetUsageRecord
        """
        record = AssetUsageRecord(
            asset_id=asset_id,
            asset_type=asset_type,
            file_path=file_path,
            original_quality_score=quality_score,
            topic=topic,
        )

        await self._repository.create_asset(record)
        logger.info(
            "Registered asset %s (type=%s, topic=%s, score=%.1f)",
            asset_id,
            asset_type.value,
            topic,
            quality_score,
        )

        return record

    async def record_usage(
        self,
        asset_id: str,
        post_id: str,
        platform: Platform,
        publish_date: datetime,
    ) -> UsageEvent:
        """Record asset usage in a published post.

        Called when post is published (Epic 4).

        Args:
            asset_id: Unique asset identifier
            post_id: Published post identifier
            platform: Publishing platform (instagram_feed, etc.)
            publish_date: When the post was published

        Returns:
            UsageEvent record

        Raises:
            ValueError: If asset not found
        """
        try:
            # Generate unique event ID
            event_id = f"{asset_id}_{post_id}_{uuid.uuid4().hex[:8]}"

            event = UsageEvent(
                event_id=event_id,
                asset_id=asset_id,
                post_id=post_id,
                platform=platform,
                publish_date=publish_date,
            )

            await self._repository.add_usage_event(event)
            logger.info(
                "Recorded usage for asset %s in post %s on %s",
                asset_id,
                post_id,
                platform.value,
            )

            return event

        except Exception as e:
            logger.error("Failed to record usage for asset %s: %s", asset_id, e)
            raise

    async def update_performance(
        self,
        asset_id: str,
        post_id: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Update performance metrics for an asset usage.

        Called when Epic 7 collects post performance data at 24h/48h/7d intervals.

        Args:
            asset_id: Asset identifier
            post_id: Post identifier for the usage
            metrics: Performance metrics collected

        Raises:
            ValueError: If asset not found
        """
        try:
            # Calculate performance score from metrics
            metrics.performance_score = calculate_performance_score(metrics)

            await self._repository.add_performance_metrics(asset_id, post_id, metrics)

            # Recalculate overall asset performance
            record = await self._repository.get_asset(asset_id)
            if record:
                record.overall_performance = calculate_overall_performance(record)
                await self._repository.update_asset(record)

            logger.info(
                "Updated performance for asset %s (post %s): score=%.1f",
                asset_id,
                post_id,
                metrics.performance_score,
            )

        except Exception as e:
            logger.error("Failed to update performance for asset %s: %s", asset_id, e)
            raise

    async def get_usage_stats(
        self,
        asset_id: str,
    ) -> AssetUsageRecord:
        """Get usage statistics for an asset.

        Args:
            asset_id: Asset identifier

        Returns:
            AssetUsageRecord with full usage history

        Raises:
            ValueError: If asset not found
        """
        record = await self._repository.get_asset(asset_id)
        if not record:
            raise ValueError(f"Asset not found: {asset_id}")
        return record

    async def suggest_assets(
        self,
        topic: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        unused_days_threshold: Optional[int] = None,
        limit: int = 10,
    ) -> list[AssetSuggestion]:
        """Get suggested assets sorted by performance.

        High-performing assets are suggested first. Assets not used within
        the threshold period are prioritized to encourage variety.

        Args:
            topic: Filter by content topic (optional)
            asset_type: Filter by asset type (optional)
            unused_days_threshold: Only include assets unused for this many days (optional)
            limit: Maximum suggestions to return

        Returns:
            List of AssetSuggestion sorted by performance score (descending)
        """
        try:
            assets = await self._repository.list_assets(
                status=AssetStatus.ACTIVE,
                topic=topic,
                asset_type=asset_type,
            )

            # Build suggestions with ranking
            suggestions: list[AssetSuggestion] = []
            now = datetime.now(timezone.utc)

            for asset in assets:
                perf = asset.overall_performance
                score = perf.overall_score if perf else asset.original_quality_score
                usage_count = len(asset.usage_events)
                last_used = (
                    max(e.publish_date for e in asset.usage_events)
                    if asset.usage_events
                    else None
                )

                # Apply unused_days_threshold filter
                if unused_days_threshold is not None:
                    if last_used is not None:
                        days_since_use = (now - last_used).days
                        if days_since_use < unused_days_threshold:
                            continue  # Skip recently used assets

                suggestions.append(
                    AssetSuggestion(
                        asset_id=asset.asset_id,
                        file_path=asset.file_path,
                        asset_type=asset.asset_type,
                        topic=asset.topic,
                        performance_score=score,
                        usage_count=usage_count,
                        last_used=last_used,
                        quality_score=asset.original_quality_score,
                        rank=0,  # Set after sorting
                    )
                )

            # Sort by performance score descending
            suggestions.sort(key=lambda s: s.performance_score, reverse=True)

            # Assign ranks and limit
            for i, suggestion in enumerate(suggestions[:limit]):
                suggestion.rank = i + 1

            return suggestions[:limit]

        except Exception as e:
            logger.error("Failed to get asset suggestions: %s", e)
            raise

    async def list_assets_by_performance(
        self,
        limit: int = 50,
    ) -> list[AssetSuggestion]:
        """List all active assets sorted by performance for dashboard view.

        Args:
            limit: Maximum assets to return

        Returns:
            List of AssetSuggestion sorted by performance
        """
        return await self.suggest_assets(limit=limit)

    async def archive_asset(
        self,
        asset_id: str,
    ) -> ArchiveRecord:
        """Archive asset while preserving performance history.

        Moves asset to Archive folder in Google Drive, maintains full
        usage and performance history for analytics.

        Args:
            asset_id: Asset identifier

        Returns:
            ArchiveRecord with preserved history

        Raises:
            ValueError: If asset not found
            RuntimeError: If Drive operation fails
        """
        try:
            record = await self._repository.get_asset(asset_id)
            if not record:
                raise ValueError(f"Asset not found: {asset_id}")

            # Build performance data for Drive metadata
            perf_data: dict[str, str] = {}
            if record.overall_performance:
                perf_data = {
                    "overall_score": str(record.overall_performance.overall_score),
                    "usage_count": str(record.overall_performance.usage_count),
                    "avg_engagement_rate": str(
                        record.overall_performance.avg_engagement_rate
                    ),
                    "total_conversions": str(
                        record.overall_performance.total_conversions
                    ),
                }

            # Capture original path BEFORE modification
            original_file_path = record.file_path

            # Move file in Google Drive using existing move_to_archive method
            # Note: GoogleDriveClientProtocol uses move_to_archive, not move_file
            archived_asset = await self._drive.move_to_archive(
                file_id=asset_id,  # Assuming asset_id is the Drive file ID
                performance_data=perf_data,
            )

            # Update record status
            archive_date = datetime.now(timezone.utc)
            archive_path = ASSET_FOLDERS["archive"] + archived_asset.name

            record.status = AssetStatus.ARCHIVED
            record.archived_at = archive_date
            record.file_path = archive_path

            archive_record = ArchiveRecord(
                asset_id=asset_id,
                original_path=original_file_path,
                archive_path=archive_path,
                archive_date=archive_date,
                performance_summary=record.overall_performance,
                total_usages=len(record.usage_events),
                metadata={
                    "asset_type": record.asset_type.value,
                    "topic": record.topic,
                    "original_quality_score": record.original_quality_score,
                },
            )

            await self._repository.update_asset(record)

            logger.info(
                "Archived asset %s with %d usages, score=%.1f",
                asset_id,
                len(record.usage_events),
                (
                    record.overall_performance.overall_score
                    if record.overall_performance
                    else 0
                ),
            )

            return archive_record

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to archive asset %s: %s", asset_id, e)
            raise
