"""Repository for asset usage persistence.

MVP implementation uses in-memory storage. The Protocol pattern
enables future database persistence without changing consumers.
"""

import logging
from typing import Optional, Protocol

from .schemas import (
    AssetStatus,
    AssetType,
    AssetUsageRecord,
    PerformanceMetrics,
    UsageEvent,
)


logger = logging.getLogger(__name__)


class AssetUsageRepositoryProtocol(Protocol):
    """Protocol for asset usage persistence.

    Defines the interface for storage operations. Implementations
    can be in-memory (MVP) or database-backed (future).
    """

    async def create_asset(self, record: AssetUsageRecord) -> None:
        """Create a new asset record.

        Args:
            record: Asset record to create
        """
        ...

    async def get_asset(self, asset_id: str) -> Optional[AssetUsageRecord]:
        """Get asset by ID.

        Args:
            asset_id: Unique asset identifier

        Returns:
            AssetUsageRecord if found, None otherwise
        """
        ...

    async def update_asset(self, record: AssetUsageRecord) -> None:
        """Update asset record.

        Args:
            record: Asset record with updated fields
        """
        ...

    async def add_usage_event(self, event: UsageEvent) -> None:
        """Add usage event to asset.

        Args:
            event: Usage event to add

        Raises:
            ValueError: If asset not found
        """
        ...

    async def add_performance_metrics(
        self,
        asset_id: str,
        post_id: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Add performance metrics for usage.

        Args:
            asset_id: Asset identifier
            post_id: Post identifier for the usage
            metrics: Performance metrics collected

        Raises:
            ValueError: If asset not found
        """
        ...

    async def list_assets(
        self,
        status: Optional[AssetStatus] = None,
        topic: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
    ) -> list[AssetUsageRecord]:
        """List assets with optional filters.

        Args:
            status: Filter by asset status
            topic: Filter by content topic
            asset_type: Filter by asset type

        Returns:
            List of matching asset records
        """
        ...

    async def sync_with_drive(
        self,
        drive_file_ids: set[str],
    ) -> list[str]:
        """Reconcile repository with Google Drive state.

        Identifies orphaned records where assets were deleted from Drive.

        Args:
            drive_file_ids: Set of file IDs currently in Google Drive

        Returns:
            List of orphaned asset IDs (in repository but not in Drive)

        Raises:
            ValueError: If orphaned records are found
        """
        ...


class AssetUsageRepository:
    """In-memory repository for asset usage records.

    MVP implementation stores data in memory. Future enhancement will
    persist to database via the same Protocol interface.

    Thread-safe for concurrent access via async lock (if needed).
    """

    def __init__(self) -> None:
        """Initialize empty repository."""
        self._assets: dict[str, AssetUsageRecord] = {}
        self._usage_by_post: dict[str, str] = {}  # post_id -> asset_id for lookup

    async def create_asset(self, record: AssetUsageRecord) -> None:
        """Create a new asset record.

        Args:
            record: Asset record to create
        """
        self._assets[record.asset_id] = record
        logger.info("Created asset record: %s", record.asset_id)

    async def get_asset(self, asset_id: str) -> Optional[AssetUsageRecord]:
        """Get asset by ID.

        Args:
            asset_id: Unique asset identifier

        Returns:
            AssetUsageRecord if found, None otherwise
        """
        return self._assets.get(asset_id)

    async def update_asset(self, record: AssetUsageRecord) -> None:
        """Update asset record.

        Args:
            record: Asset record with updated fields
        """
        self._assets[record.asset_id] = record
        logger.debug("Updated asset record: %s", record.asset_id)

    async def add_usage_event(self, event: UsageEvent) -> None:
        """Add usage event to asset.

        Args:
            event: Usage event to add

        Raises:
            ValueError: If asset not found
        """
        record = await self.get_asset(event.asset_id)
        if not record:
            raise ValueError(f"Asset not found: {event.asset_id}")

        record.usage_events.append(event)
        self._usage_by_post[event.post_id] = event.asset_id
        logger.debug(
            "Added usage event for asset %s, post %s",
            event.asset_id,
            event.post_id,
        )

    async def add_performance_metrics(
        self,
        asset_id: str,
        post_id: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Add performance metrics for usage.

        Args:
            asset_id: Asset identifier
            post_id: Post identifier for the usage
            metrics: Performance metrics collected

        Raises:
            ValueError: If asset not found
        """
        record = await self.get_asset(asset_id)
        if not record:
            raise ValueError(f"Asset not found: {asset_id}")

        record.performance_history.append(metrics)
        logger.debug(
            "Added performance metrics for asset %s, post %s",
            asset_id,
            post_id,
        )

    async def list_assets(
        self,
        status: Optional[AssetStatus] = None,
        topic: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
    ) -> list[AssetUsageRecord]:
        """List assets with optional filters.

        Args:
            status: Filter by asset status
            topic: Filter by content topic
            asset_type: Filter by asset type

        Returns:
            List of matching asset records
        """
        results = list(self._assets.values())

        if status is not None:
            results = [r for r in results if r.status == status]
        if topic is not None:
            results = [r for r in results if r.topic == topic]
        if asset_type is not None:
            results = [r for r in results if r.asset_type == asset_type]

        return results

    async def get_asset_by_post(self, post_id: str) -> Optional[AssetUsageRecord]:
        """Get asset used in a specific post.

        Args:
            post_id: Post identifier

        Returns:
            AssetUsageRecord if found, None otherwise
        """
        asset_id = self._usage_by_post.get(post_id)
        if not asset_id:
            return None
        return await self.get_asset(asset_id)

    async def sync_with_drive(
        self,
        drive_file_ids: set[str],
    ) -> list[str]:
        """Reconcile repository with Google Drive state.

        Identifies orphaned records where assets were deleted from Drive.
        Only checks ACTIVE assets (archived assets may have been moved).

        Args:
            drive_file_ids: Set of file IDs currently in Google Drive

        Returns:
            List of orphaned asset IDs (in repository but not in Drive)

        Raises:
            ValueError: If orphaned records are found (caller should handle)
        """
        orphaned_ids: list[str] = []

        for asset_id, record in self._assets.items():
            # Only check active assets - archived may have different IDs
            if record.status == AssetStatus.ACTIVE:
                if asset_id not in drive_file_ids:
                    orphaned_ids.append(asset_id)
                    logger.warning(
                        "Orphaned asset detected: %s (not found in Drive)",
                        asset_id,
                    )

        if orphaned_ids:
            logger.error(
                "Found %d orphaned asset records: %s",
                len(orphaned_ids),
                orphaned_ids,
            )
            raise ValueError(
                f"Orphaned usage records detected: {orphaned_ids}. "
                "Assets deleted from Drive but usage records exist."
            )

        logger.info(
            "Drive sync complete: %d assets verified",
            len([a for a in self._assets.values() if a.status == AssetStatus.ACTIVE]),
        )
        return orphaned_ids
