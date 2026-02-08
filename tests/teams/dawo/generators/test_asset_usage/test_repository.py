"""Tests for Asset Usage Repository."""

from datetime import datetime, timezone

import pytest

from teams.dawo.generators.asset_usage import (
    AssetUsageRepository,
    AssetUsageRecord,
    UsageEvent,
    PerformanceMetrics,
    Platform,
    AssetType,
    AssetStatus,
)


class TestAssetUsageRepository:
    """Tests for AssetUsageRepository operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_asset(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
    ) -> None:
        """Create and retrieve an asset record."""
        await repository.create_asset(sample_asset_record)

        result = await repository.get_asset("asset-001")

        assert result is not None
        assert result.asset_id == "asset-001"
        assert result.topic == "lions_mane"

    @pytest.mark.asyncio
    async def test_get_nonexistent_asset(
        self,
        repository: AssetUsageRepository,
    ) -> None:
        """Get returns None for nonexistent asset."""
        result = await repository.get_asset("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_asset(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
    ) -> None:
        """Update an existing asset record."""
        await repository.create_asset(sample_asset_record)

        # Modify and update
        sample_asset_record.status = AssetStatus.ARCHIVED
        await repository.update_asset(sample_asset_record)

        result = await repository.get_asset("asset-001")
        assert result.status == AssetStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_add_usage_event(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
        sample_usage_event: UsageEvent,
    ) -> None:
        """Add usage event to existing asset."""
        await repository.create_asset(sample_asset_record)

        await repository.add_usage_event(sample_usage_event)

        result = await repository.get_asset("asset-001")
        assert len(result.usage_events) == 1
        assert result.usage_events[0].post_id == "post-abc123"

    @pytest.mark.asyncio
    async def test_add_usage_event_nonexistent_asset(
        self,
        repository: AssetUsageRepository,
        sample_usage_event: UsageEvent,
    ) -> None:
        """Adding usage event to nonexistent asset raises ValueError."""
        with pytest.raises(ValueError, match="Asset not found"):
            await repository.add_usage_event(sample_usage_event)

    @pytest.mark.asyncio
    async def test_add_multiple_usage_events(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
    ) -> None:
        """Add multiple usage events to same asset."""
        await repository.create_asset(sample_asset_record)

        events = [
            UsageEvent(
                event_id=f"event-{i}",
                asset_id="asset-001",
                post_id=f"post-{i}",
                platform=Platform.INSTAGRAM_FEED,
                publish_date=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        for event in events:
            await repository.add_usage_event(event)

        result = await repository.get_asset("asset-001")
        assert len(result.usage_events) == 3

    @pytest.mark.asyncio
    async def test_add_performance_metrics(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
        sample_performance_metrics: PerformanceMetrics,
    ) -> None:
        """Add performance metrics to existing asset."""
        await repository.create_asset(sample_asset_record)

        await repository.add_performance_metrics(
            "asset-001", "post-abc123", sample_performance_metrics
        )

        result = await repository.get_asset("asset-001")
        assert len(result.performance_history) == 1
        assert result.performance_history[0].engagement_rate == 0.05

    @pytest.mark.asyncio
    async def test_add_performance_metrics_nonexistent_asset(
        self,
        repository: AssetUsageRepository,
        sample_performance_metrics: PerformanceMetrics,
    ) -> None:
        """Adding performance metrics to nonexistent asset raises ValueError."""
        with pytest.raises(ValueError, match="Asset not found"):
            await repository.add_performance_metrics(
                "nonexistent", "post-001", sample_performance_metrics
            )

    @pytest.mark.asyncio
    async def test_list_assets_no_filter(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
        sample_nano_banana_asset: AssetUsageRecord,
    ) -> None:
        """List all assets without filters."""
        await repository.create_asset(sample_asset_record)
        await repository.create_asset(sample_nano_banana_asset)

        results = await repository.list_assets()

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_assets_filter_by_status(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
        sample_nano_banana_asset: AssetUsageRecord,
    ) -> None:
        """List assets filtered by status."""
        sample_asset_record.status = AssetStatus.ARCHIVED
        await repository.create_asset(sample_asset_record)
        await repository.create_asset(sample_nano_banana_asset)

        active = await repository.list_assets(status=AssetStatus.ACTIVE)
        archived = await repository.list_assets(status=AssetStatus.ARCHIVED)

        assert len(active) == 1
        assert len(archived) == 1
        assert active[0].asset_id == "asset-002"
        assert archived[0].asset_id == "asset-001"

    @pytest.mark.asyncio
    async def test_list_assets_filter_by_topic(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
        sample_nano_banana_asset: AssetUsageRecord,
    ) -> None:
        """List assets filtered by topic."""
        await repository.create_asset(sample_asset_record)  # topic: lions_mane
        await repository.create_asset(sample_nano_banana_asset)  # topic: wellness

        lions_mane = await repository.list_assets(topic="lions_mane")
        wellness = await repository.list_assets(topic="wellness")
        nonexistent = await repository.list_assets(topic="reishi")

        assert len(lions_mane) == 1
        assert len(wellness) == 1
        assert len(nonexistent) == 0

    @pytest.mark.asyncio
    async def test_list_assets_filter_by_type(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
        sample_nano_banana_asset: AssetUsageRecord,
    ) -> None:
        """List assets filtered by asset type."""
        await repository.create_asset(sample_asset_record)  # ORSHOT_GRAPHIC
        await repository.create_asset(sample_nano_banana_asset)  # NANO_BANANA_IMAGE

        orshot = await repository.list_assets(asset_type=AssetType.ORSHOT_GRAPHIC)
        nano = await repository.list_assets(asset_type=AssetType.NANO_BANANA_IMAGE)

        assert len(orshot) == 1
        assert len(nano) == 1
        assert orshot[0].asset_id == "asset-001"
        assert nano[0].asset_id == "asset-002"

    @pytest.mark.asyncio
    async def test_list_assets_combined_filters(
        self,
        repository: AssetUsageRepository,
    ) -> None:
        """List assets with multiple filters combined."""
        # Create multiple assets
        assets = [
            AssetUsageRecord(
                asset_id="a1",
                asset_type=AssetType.ORSHOT_GRAPHIC,
                file_path="a1.png",
                original_quality_score=8.0,
                topic="lions_mane",
                status=AssetStatus.ACTIVE,
            ),
            AssetUsageRecord(
                asset_id="a2",
                asset_type=AssetType.ORSHOT_GRAPHIC,
                file_path="a2.png",
                original_quality_score=7.5,
                topic="lions_mane",
                status=AssetStatus.ARCHIVED,
            ),
            AssetUsageRecord(
                asset_id="a3",
                asset_type=AssetType.NANO_BANANA_IMAGE,
                file_path="a3.png",
                original_quality_score=9.0,
                topic="lions_mane",
                status=AssetStatus.ACTIVE,
            ),
        ]

        for asset in assets:
            await repository.create_asset(asset)

        # Filter: active + lions_mane + orshot
        results = await repository.list_assets(
            status=AssetStatus.ACTIVE,
            topic="lions_mane",
            asset_type=AssetType.ORSHOT_GRAPHIC,
        )

        assert len(results) == 1
        assert results[0].asset_id == "a1"

    @pytest.mark.asyncio
    async def test_get_asset_by_post(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
        sample_usage_event: UsageEvent,
    ) -> None:
        """Get asset by post ID."""
        await repository.create_asset(sample_asset_record)
        await repository.add_usage_event(sample_usage_event)

        result = await repository.get_asset_by_post("post-abc123")

        assert result is not None
        assert result.asset_id == "asset-001"

    @pytest.mark.asyncio
    async def test_get_asset_by_post_not_found(
        self,
        repository: AssetUsageRepository,
    ) -> None:
        """Get asset by post returns None if not found."""
        result = await repository.get_asset_by_post("nonexistent-post")
        assert result is None

    @pytest.mark.asyncio
    async def test_sync_with_drive_all_present(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
    ) -> None:
        """Sync passes when all assets are in Drive."""
        await repository.create_asset(sample_asset_record)

        # All assets present in Drive
        drive_ids = {"asset-001"}
        orphaned = await repository.sync_with_drive(drive_ids)

        assert orphaned == []

    @pytest.mark.asyncio
    async def test_sync_with_drive_orphaned_record(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
    ) -> None:
        """Sync raises ValueError when asset not in Drive."""
        await repository.create_asset(sample_asset_record)

        # Asset not in Drive
        drive_ids: set[str] = set()

        with pytest.raises(ValueError, match="Orphaned usage records detected"):
            await repository.sync_with_drive(drive_ids)

    @pytest.mark.asyncio
    async def test_sync_with_drive_ignores_archived(
        self,
        repository: AssetUsageRepository,
        sample_asset_record: AssetUsageRecord,
    ) -> None:
        """Sync ignores archived assets (they may have different IDs)."""
        sample_asset_record.status = AssetStatus.ARCHIVED
        await repository.create_asset(sample_asset_record)

        # Archived asset not in Drive - should not raise
        drive_ids: set[str] = set()
        orphaned = await repository.sync_with_drive(drive_ids)

        assert orphaned == []
