"""Tests for AssetUsageTracker agent."""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from teams.dawo.generators.asset_usage import (
    AssetUsageTracker,
    AssetUsageRepository,
    AssetUsageRecord,
    UsageEvent,
    PerformanceMetrics,
    Platform,
    AssetType,
    AssetStatus,
)


class TestAssetRegistration:
    """Tests for asset registration (Task 1, 2)."""

    @pytest.mark.asyncio
    async def test_register_asset(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Register a new asset for tracking."""
        record = await tracker.register_asset(
            asset_id="asset-new",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="DAWO.ECO/Assets/Orshot/test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        assert record.asset_id == "asset-new"
        assert record.original_quality_score == 8.5
        assert record.status == AssetStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_register_nano_banana_asset(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Register a Nano Banana AI-generated asset."""
        record = await tracker.register_asset(
            asset_id="nano-001",
            asset_type=AssetType.NANO_BANANA_IMAGE,
            file_path="DAWO.ECO/Assets/Generated/ai_image.png",
            quality_score=7.0,
            topic="wellness",
        )

        assert record.asset_type == AssetType.NANO_BANANA_IMAGE
        assert record.topic == "wellness"


class TestUsageRecording:
    """Tests for usage recording (AC #1, Task 2)."""

    @pytest.mark.asyncio
    async def test_record_usage_valid_asset(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Record usage for a valid asset."""
        # First register the asset
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        publish_date = datetime.now(timezone.utc)
        event = await tracker.record_usage(
            asset_id="asset-001",
            post_id="post-abc123",
            platform=Platform.INSTAGRAM_FEED,
            publish_date=publish_date,
        )

        assert event.asset_id == "asset-001"
        assert event.post_id == "post-abc123"
        assert event.platform == Platform.INSTAGRAM_FEED
        assert event.publish_date == publish_date

    @pytest.mark.asyncio
    async def test_record_usage_updates_count(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Usage count increments on multiple uses."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        # Record multiple usages
        for i in range(3):
            await tracker.record_usage(
                asset_id="asset-001",
                post_id=f"post-{i}",
                platform=Platform.INSTAGRAM_FEED,
                publish_date=datetime.now(timezone.utc),
            )

        record = await tracker.get_usage_stats("asset-001")
        assert len(record.usage_events) == 3

    @pytest.mark.asyncio
    async def test_record_usage_nonexistent_asset(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Recording usage for nonexistent asset raises error."""
        with pytest.raises(ValueError, match="Asset not found"):
            await tracker.record_usage(
                asset_id="nonexistent",
                post_id="post-001",
                platform=Platform.INSTAGRAM_FEED,
                publish_date=datetime.now(timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_record_usage_different_platforms(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Record usage across different platforms."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        platforms = [
            Platform.INSTAGRAM_FEED,
            Platform.INSTAGRAM_STORY,
            Platform.INSTAGRAM_REEL,
        ]

        for i, platform in enumerate(platforms):
            await tracker.record_usage(
                asset_id="asset-001",
                post_id=f"post-{i}",
                platform=platform,
                publish_date=datetime.now(timezone.utc),
            )

        record = await tracker.get_usage_stats("asset-001")
        recorded_platforms = {e.platform for e in record.usage_events}
        assert recorded_platforms == set(platforms)


class TestPerformanceTracking:
    """Tests for performance metrics tracking (AC #2, Task 3)."""

    @pytest.mark.asyncio
    async def test_update_performance(
        self,
        tracker: AssetUsageTracker,
        sample_performance_metrics: PerformanceMetrics,
    ) -> None:
        """Update performance metrics for asset usage."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        await tracker.update_performance(
            asset_id="asset-001",
            post_id="post-abc123",
            metrics=sample_performance_metrics,
        )

        record = await tracker.get_usage_stats("asset-001")
        assert len(record.performance_history) == 1
        assert record.overall_performance is not None

    @pytest.mark.asyncio
    async def test_performance_score_calculated(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Performance score is calculated on update."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        metrics = PerformanceMetrics(
            engagement_rate=0.10,
            conversions=10,
            reach=5000,
            performance_score=0.0,  # Should be calculated
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        await tracker.update_performance(
            asset_id="asset-001",
            post_id="post-001",
            metrics=metrics,
        )

        # Verify score was calculated
        assert metrics.performance_score > 0

    @pytest.mark.asyncio
    async def test_multiple_performance_updates(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Handle delayed performance updates (24h/48h/7d intervals)."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        intervals = ["24h", "48h", "7d"]
        for interval in intervals:
            metrics = PerformanceMetrics(
                engagement_rate=0.05,
                conversions=3,
                reach=2000,
                performance_score=0.0,
                collected_at=datetime.now(timezone.utc),
                collection_interval=interval,
            )
            await tracker.update_performance(
                asset_id="asset-001",
                post_id="post-001",
                metrics=metrics,
            )

        record = await tracker.get_usage_stats("asset-001")
        assert len(record.performance_history) == 3

    @pytest.mark.asyncio
    async def test_update_performance_nonexistent_asset(
        self,
        tracker: AssetUsageTracker,
        sample_performance_metrics: PerformanceMetrics,
    ) -> None:
        """Updating performance for nonexistent asset raises error."""
        with pytest.raises(ValueError, match="Asset not found"):
            await tracker.update_performance(
                asset_id="nonexistent",
                post_id="post-001",
                metrics=sample_performance_metrics,
            )


class TestPerformanceScoring:
    """Tests for performance score calculation (AC #2, Task 4)."""

    @pytest.mark.asyncio
    async def test_score_weights(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Verify score uses correct weights (40% engagement, 30% conv, 30% reach)."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=5.0,
            topic="lions_mane",
        )

        # Create metrics where we know expected score
        # engagement_score = min(10, 0.10 * 100) = 10.0
        # conversion_score = min(10, 10) = 10.0
        # reach_score = min(10, 5000/1000) = 5.0
        # Expected: 10*0.4 + 10*0.3 + 5*0.3 = 4.0 + 3.0 + 1.5 = 8.5
        metrics = PerformanceMetrics(
            engagement_rate=0.10,
            conversions=10,
            reach=5000,
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        await tracker.update_performance(
            asset_id="asset-001",
            post_id="post-001",
            metrics=metrics,
        )

        record = await tracker.get_usage_stats("asset-001")
        assert record.overall_performance.overall_score == 8.5

    @pytest.mark.asyncio
    async def test_running_average_performance(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Average performance calculated across all usages."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=5.0,
            topic="lions_mane",
        )

        # Add two different performance updates
        metrics1 = PerformanceMetrics(
            engagement_rate=0.04,  # 4.0 score
            conversions=2,  # 2.0 score
            reach=2000,  # 2.0 score
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        metrics2 = PerformanceMetrics(
            engagement_rate=0.06,  # 6.0 score
            conversions=4,  # 4.0 score
            reach=4000,  # 4.0 score
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        await tracker.update_performance("asset-001", "post-001", metrics1)
        await tracker.update_performance("asset-001", "post-002", metrics2)

        record = await tracker.get_usage_stats("asset-001")

        # Average engagement: (0.04 + 0.06) / 2 = 0.05
        assert abs(record.overall_performance.avg_engagement_rate - 0.05) < 0.001


class TestAssetSuggestions:
    """Tests for asset query and suggestion (AC #3, Task 5)."""

    @pytest.mark.asyncio
    async def test_suggest_assets_sorted_by_performance(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Assets are suggested sorted by performance score."""
        # Create multiple assets with different quality scores
        for i, score in enumerate([7.0, 9.0, 8.0]):
            await tracker.register_asset(
                asset_id=f"asset-{i}",
                asset_type=AssetType.ORSHOT_GRAPHIC,
                file_path=f"test-{i}.png",
                quality_score=score,
                topic="lions_mane",
            )

        suggestions = await tracker.suggest_assets()

        # Should be sorted by quality score (no performance data yet)
        assert suggestions[0].asset_id == "asset-1"  # score 9.0
        assert suggestions[1].asset_id == "asset-2"  # score 8.0
        assert suggestions[2].asset_id == "asset-0"  # score 7.0

    @pytest.mark.asyncio
    async def test_suggest_assets_filter_by_topic(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Filter suggestions by content topic."""
        await tracker.register_asset(
            asset_id="asset-1",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test1.png",
            quality_score=8.0,
            topic="lions_mane",
        )
        await tracker.register_asset(
            asset_id="asset-2",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test2.png",
            quality_score=9.0,
            topic="wellness",
        )

        suggestions = await tracker.suggest_assets(topic="lions_mane")

        assert len(suggestions) == 1
        assert suggestions[0].topic == "lions_mane"

    @pytest.mark.asyncio
    async def test_suggest_assets_filter_by_type(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Filter suggestions by asset type."""
        await tracker.register_asset(
            asset_id="asset-1",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test1.png",
            quality_score=8.0,
            topic="lions_mane",
        )
        await tracker.register_asset(
            asset_id="asset-2",
            asset_type=AssetType.NANO_BANANA_IMAGE,
            file_path="test2.png",
            quality_score=9.0,
            topic="lions_mane",
        )

        suggestions = await tracker.suggest_assets(
            asset_type=AssetType.ORSHOT_GRAPHIC
        )

        assert len(suggestions) == 1
        assert suggestions[0].asset_type == AssetType.ORSHOT_GRAPHIC

    @pytest.mark.asyncio
    async def test_suggest_assets_includes_usage_stats(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Suggestions include usage count and last used date."""
        await tracker.register_asset(
            asset_id="asset-1",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.0,
            topic="lions_mane",
        )

        # Add some usages
        for i in range(3):
            await tracker.record_usage(
                asset_id="asset-1",
                post_id=f"post-{i}",
                platform=Platform.INSTAGRAM_FEED,
                publish_date=datetime.now(timezone.utc),
            )

        suggestions = await tracker.suggest_assets()

        assert suggestions[0].usage_count == 3
        assert suggestions[0].last_used is not None

    @pytest.mark.asyncio
    async def test_suggest_assets_respects_limit(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Suggestions respect the limit parameter."""
        for i in range(10):
            await tracker.register_asset(
                asset_id=f"asset-{i}",
                asset_type=AssetType.ORSHOT_GRAPHIC,
                file_path=f"test-{i}.png",
                quality_score=8.0 + i * 0.1,
                topic="lions_mane",
            )

        suggestions = await tracker.suggest_assets(limit=5)

        assert len(suggestions) == 5

    @pytest.mark.asyncio
    async def test_suggest_assets_assigns_ranks(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Suggestions have correct rank assignments."""
        for i in range(3):
            await tracker.register_asset(
                asset_id=f"asset-{i}",
                asset_type=AssetType.ORSHOT_GRAPHIC,
                file_path=f"test-{i}.png",
                quality_score=8.0 + i,
                topic="lions_mane",
            )

        suggestions = await tracker.suggest_assets()

        assert suggestions[0].rank == 1
        assert suggestions[1].rank == 2
        assert suggestions[2].rank == 3

    @pytest.mark.asyncio
    async def test_suggest_assets_excludes_archived(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Suggestions exclude archived assets."""
        await tracker.register_asset(
            asset_id="asset-active",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="active.png",
            quality_score=8.0,
            topic="lions_mane",
        )
        await tracker.register_asset(
            asset_id="asset-to-archive",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="to-archive.png",
            quality_score=9.0,
            topic="lions_mane",
        )

        # Archive one asset
        await tracker.archive_asset("asset-to-archive")

        suggestions = await tracker.suggest_assets()

        assert len(suggestions) == 1
        assert suggestions[0].asset_id == "asset-active"


class TestArchiveManagement:
    """Tests for archive management (AC #4, Task 6)."""

    @pytest.mark.asyncio
    async def test_archive_asset(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Archive asset moves to Archive folder."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="DAWO.ECO/Assets/Orshot/original.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        archive_record = await tracker.archive_asset("asset-001")

        assert archive_record.asset_id == "asset-001"
        assert "Archive" in archive_record.archive_path
        assert archive_record.total_usages == 0

        # Verify Drive client was called
        mock_drive_client.move_to_archive.assert_called_once()

    @pytest.mark.asyncio
    async def test_archive_preserves_performance(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Archive preserves performance history."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="original.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        # Add usage and performance
        await tracker.record_usage(
            asset_id="asset-001",
            post_id="post-001",
            platform=Platform.INSTAGRAM_FEED,
            publish_date=datetime.now(timezone.utc),
        )

        metrics = PerformanceMetrics(
            engagement_rate=0.05,
            conversions=5,
            reach=2500,
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )
        await tracker.update_performance("asset-001", "post-001", metrics)

        archive_record = await tracker.archive_asset("asset-001")

        assert archive_record.total_usages == 1
        assert archive_record.performance_summary is not None
        assert archive_record.performance_summary.total_conversions == 5

    @pytest.mark.asyncio
    async def test_archive_updates_status(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Archive updates asset status to ARCHIVED."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="original.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        await tracker.archive_asset("asset-001")

        record = await tracker.get_usage_stats("asset-001")
        assert record.status == AssetStatus.ARCHIVED
        assert record.archived_at is not None

    @pytest.mark.asyncio
    async def test_archive_nonexistent_asset(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Archiving nonexistent asset raises error."""
        with pytest.raises(ValueError, match="Asset not found"):
            await tracker.archive_asset("nonexistent")

    @pytest.mark.asyncio
    async def test_archive_with_metadata(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Archive includes metadata in record."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="original.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        archive_record = await tracker.archive_asset("asset-001")

        assert archive_record.metadata["asset_type"] == "orshot_graphic"
        assert archive_record.metadata["topic"] == "lions_mane"
        assert archive_record.metadata["original_quality_score"] == 8.5


class TestConcurrentOperations:
    """Tests for concurrent usage recording (Task 2.5)."""

    @pytest.mark.asyncio
    async def test_concurrent_usage_recording(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Handle concurrent usage recording for same asset."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        # Simulate concurrent usage recording
        import asyncio

        async def record(post_id: str):
            return await tracker.record_usage(
                asset_id="asset-001",
                post_id=post_id,
                platform=Platform.INSTAGRAM_FEED,
                publish_date=datetime.now(timezone.utc),
            )

        # Record 5 usages concurrently
        events = await asyncio.gather(
            record("post-1"),
            record("post-2"),
            record("post-3"),
            record("post-4"),
            record("post-5"),
        )

        assert len(events) == 5

        # Verify all usages recorded
        record = await tracker.get_usage_stats("asset-001")
        assert len(record.usage_events) == 5


class TestGetUsageStats:
    """Tests for usage statistics retrieval."""

    @pytest.mark.asyncio
    async def test_get_usage_stats(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Get complete usage statistics for asset."""
        await tracker.register_asset(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        record = await tracker.get_usage_stats("asset-001")

        assert record.asset_id == "asset-001"
        assert record.original_quality_score == 8.5

    @pytest.mark.asyncio
    async def test_get_usage_stats_nonexistent(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Get stats for nonexistent asset raises error."""
        with pytest.raises(ValueError, match="Asset not found"):
            await tracker.get_usage_stats("nonexistent")


class TestListAssetsByPerformance:
    """Tests for dashboard performance listing (Task 5.5)."""

    @pytest.mark.asyncio
    async def test_list_assets_by_performance(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """List all assets sorted by performance for dashboard."""
        for i in range(5):
            await tracker.register_asset(
                asset_id=f"asset-{i}",
                asset_type=AssetType.ORSHOT_GRAPHIC,
                file_path=f"test-{i}.png",
                quality_score=5.0 + i,
                topic="lions_mane",
            )

        assets = await tracker.list_assets_by_performance(limit=3)

        assert len(assets) == 3
        # Should be sorted by score descending
        assert assets[0].quality_score > assets[1].quality_score


class TestUnusedDaysThreshold:
    """Tests for unused_days_threshold filtering (Task 5.3)."""

    @pytest.mark.asyncio
    async def test_suggest_assets_with_unused_threshold(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Filter suggestions by unused days threshold."""
        # Create two assets
        await tracker.register_asset(
            asset_id="recently-used",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="recent.png",
            quality_score=9.0,
            topic="lions_mane",
        )
        await tracker.register_asset(
            asset_id="never-used",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="never.png",
            quality_score=8.0,
            topic="lions_mane",
        )

        # Record usage for one asset (today)
        await tracker.record_usage(
            asset_id="recently-used",
            post_id="post-today",
            platform=Platform.INSTAGRAM_FEED,
            publish_date=datetime.now(timezone.utc),
        )

        # With threshold of 7 days, recently-used should be excluded
        suggestions = await tracker.suggest_assets(unused_days_threshold=7)

        # Only never-used should appear (recently-used was used today < 7 days ago)
        assert len(suggestions) == 1
        assert suggestions[0].asset_id == "never-used"

    @pytest.mark.asyncio
    async def test_suggest_assets_unused_threshold_includes_old_usage(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Assets used longer ago than threshold are included."""
        await tracker.register_asset(
            asset_id="old-usage",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="old.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        # Record usage 40 days ago
        old_date = datetime.now(timezone.utc) - timedelta(days=40)
        await tracker.record_usage(
            asset_id="old-usage",
            post_id="post-old",
            platform=Platform.INSTAGRAM_FEED,
            publish_date=old_date,
        )

        # With threshold of 30 days, old-usage should be included
        suggestions = await tracker.suggest_assets(unused_days_threshold=30)

        assert len(suggestions) == 1
        assert suggestions[0].asset_id == "old-usage"

    @pytest.mark.asyncio
    async def test_suggest_assets_no_threshold_returns_all(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Without threshold, all assets are returned."""
        await tracker.register_asset(
            asset_id="asset-1",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test1.png",
            quality_score=8.0,
            topic="lions_mane",
        )
        await tracker.register_asset(
            asset_id="asset-2",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test2.png",
            quality_score=9.0,
            topic="lions_mane",
        )

        # Use one asset
        await tracker.record_usage(
            asset_id="asset-1",
            post_id="post-1",
            platform=Platform.INSTAGRAM_FEED,
            publish_date=datetime.now(timezone.utc),
        )

        # Without threshold, both should appear
        suggestions = await tracker.suggest_assets()

        assert len(suggestions) == 2
