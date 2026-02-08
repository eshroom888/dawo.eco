"""Integration tests for Asset Usage Tracking.

Tests the full usage lifecycle: create -> use -> performance -> archive
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from teams.dawo.generators.asset_usage import (
    AssetUsageTracker,
    AssetUsageRepository,
    PerformanceMetrics,
    Platform,
    AssetType,
    AssetStatus,
)


class TestFullUsageLifecycle:
    """Tests for complete asset usage lifecycle (Task 10.1)."""

    @pytest.mark.asyncio
    async def test_create_use_performance_archive_lifecycle(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Full lifecycle: register -> use -> performance -> archive."""
        # 1. Register asset (from Story 3.4 or 3.5)
        asset = await tracker.register_asset(
            asset_id="lifecycle-asset",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="DAWO.ECO/Assets/Orshot/lifecycle.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        assert asset.status == AssetStatus.ACTIVE

        # 2. Record usage when post is published (Epic 4)
        publish_time = datetime.now(timezone.utc)
        event = await tracker.record_usage(
            asset_id="lifecycle-asset",
            post_id="instagram-post-123",
            platform=Platform.INSTAGRAM_FEED,
            publish_date=publish_time,
        )

        assert event.platform == Platform.INSTAGRAM_FEED

        # 3. Update performance at 24h interval (Epic 7)
        metrics_24h = PerformanceMetrics(
            engagement_rate=0.04,
            conversions=2,
            reach=2000,
            performance_score=0.0,
            collected_at=publish_time + timedelta(hours=24),
            collection_interval="24h",
        )
        await tracker.update_performance(
            "lifecycle-asset", "instagram-post-123", metrics_24h
        )

        # 4. Update performance at 48h interval
        metrics_48h = PerformanceMetrics(
            engagement_rate=0.05,
            conversions=3,
            reach=2500,
            performance_score=0.0,
            collected_at=publish_time + timedelta(hours=48),
            collection_interval="48h",
        )
        await tracker.update_performance(
            "lifecycle-asset", "instagram-post-123", metrics_48h
        )

        # 5. Check performance is tracked
        record = await tracker.get_usage_stats("lifecycle-asset")
        assert len(record.performance_history) == 2
        assert record.overall_performance is not None
        assert record.overall_performance.total_conversions == 5  # 2 + 3

        # 6. Archive after content is no longer fresh
        archive = await tracker.archive_asset("lifecycle-asset")

        assert archive.total_usages == 1
        assert archive.performance_summary.total_conversions == 5

        # 7. Verify asset is archived but still queryable
        archived_record = await tracker.get_usage_stats("lifecycle-asset")
        assert archived_record.status == AssetStatus.ARCHIVED
        assert len(archived_record.performance_history) == 2  # History preserved


class TestGoogleDriveIntegration:
    """Tests for Google Drive integration (Task 10.2)."""

    @pytest.mark.asyncio
    async def test_archive_calls_drive_with_performance_data(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Archive operation passes performance data to Drive."""
        await tracker.register_asset(
            asset_id="drive-test-asset",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="DAWO.ECO/Assets/Orshot/drive-test.png",
            quality_score=8.5,
            topic="lions_mane",
        )

        # Add performance data
        metrics = PerformanceMetrics(
            engagement_rate=0.05,
            conversions=5,
            reach=2500,
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )
        await tracker.update_performance("drive-test-asset", "post-001", metrics)

        # Archive
        await tracker.archive_asset("drive-test-asset")

        # Verify Drive client called with performance data
        mock_drive_client.move_to_archive.assert_called_once()
        call_args = mock_drive_client.move_to_archive.call_args
        assert call_args.kwargs["file_id"] == "drive-test-asset"
        assert "overall_score" in call_args.kwargs["performance_data"]
        assert "total_conversions" in call_args.kwargs["performance_data"]


class TestSuggestionWithRealisticPool:
    """Tests for suggestion API with realistic asset pool (Task 10.3)."""

    @pytest.mark.asyncio
    async def test_suggestion_with_mixed_performance(
        self,
        tracker: AssetUsageTracker,
    ) -> None:
        """Suggestions correctly rank assets with varying performance."""
        # Create diverse asset pool
        assets = [
            ("high-performer", AssetType.ORSHOT_GRAPHIC, "lions_mane", 7.0),
            ("medium-performer", AssetType.ORSHOT_GRAPHIC, "lions_mane", 7.0),
            ("low-performer", AssetType.ORSHOT_GRAPHIC, "lions_mane", 7.0),
            ("unused-high-quality", AssetType.ORSHOT_GRAPHIC, "lions_mane", 9.5),
            ("nano-banana", AssetType.NANO_BANANA_IMAGE, "wellness", 8.0),
        ]

        for asset_id, asset_type, topic, quality in assets:
            await tracker.register_asset(
                asset_id=asset_id,
                asset_type=asset_type,
                file_path=f"{asset_id}.png",
                quality_score=quality,
                topic=topic,
            )

        # Add performance data for used assets
        performances = [
            ("high-performer", 0.10, 10, 5000),  # Excellent
            ("medium-performer", 0.05, 3, 2000),  # Good
            ("low-performer", 0.01, 0, 500),  # Poor
        ]

        for asset_id, eng, conv, reach in performances:
            await tracker.record_usage(
                asset_id=asset_id,
                post_id=f"post-{asset_id}",
                platform=Platform.INSTAGRAM_FEED,
                publish_date=datetime.now(timezone.utc),
            )

            metrics = PerformanceMetrics(
                engagement_rate=eng,
                conversions=conv,
                reach=reach,
                performance_score=0.0,
                collected_at=datetime.now(timezone.utc),
                collection_interval="24h",
            )
            await tracker.update_performance(asset_id, f"post-{asset_id}", metrics)

        # Get suggestions for lions_mane topic
        suggestions = await tracker.suggest_assets(
            topic="lions_mane", asset_type=AssetType.ORSHOT_GRAPHIC
        )

        # Verify ranking: unused high quality should be near top due to 9.5 score
        # High performer should be at top due to performance
        assert len(suggestions) == 4

        # First should be unused-high-quality (9.5) or high-performer (high perf score)
        top_two_ids = {suggestions[0].asset_id, suggestions[1].asset_id}
        assert "high-performer" in top_two_ids or "unused-high-quality" in top_two_ids

        # Low performer should be last
        assert suggestions[-1].asset_id == "low-performer"


class TestArchiveAndSearchability:
    """Tests for archive and continued searchability (Task 10.4)."""

    @pytest.mark.asyncio
    async def test_archived_assets_remain_queryable(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Archived assets remain searchable for analytics."""
        # Create and archive multiple assets
        for i in range(3):
            await tracker.register_asset(
                asset_id=f"archive-test-{i}",
                asset_type=AssetType.ORSHOT_GRAPHIC,
                file_path=f"archive-{i}.png",
                quality_score=8.0,
                topic="lions_mane",
            )

            await tracker.record_usage(
                asset_id=f"archive-test-{i}",
                post_id=f"post-{i}",
                platform=Platform.INSTAGRAM_FEED,
                publish_date=datetime.now(timezone.utc),
            )

            await tracker.archive_asset(f"archive-test-{i}")

        # All should be queryable individually
        for i in range(3):
            record = await tracker.get_usage_stats(f"archive-test-{i}")
            assert record.status == AssetStatus.ARCHIVED
            assert len(record.usage_events) == 1

    @pytest.mark.asyncio
    async def test_archived_assets_excluded_from_active_suggestions(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Archived assets don't appear in active suggestions."""
        # Create active and archived assets
        await tracker.register_asset(
            asset_id="active-asset",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="active.png",
            quality_score=8.0,
            topic="lions_mane",
        )

        await tracker.register_asset(
            asset_id="to-archive",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="archived.png",
            quality_score=9.0,  # Higher score
            topic="lions_mane",
        )

        await tracker.archive_asset("to-archive")

        # Get suggestions - should only include active
        suggestions = await tracker.suggest_assets()

        assert len(suggestions) == 1
        assert suggestions[0].asset_id == "active-asset"

    @pytest.mark.asyncio
    async def test_performance_history_preserved_after_archive(
        self,
        tracker: AssetUsageTracker,
        mock_drive_client: AsyncMock,
    ) -> None:
        """Full performance history is preserved after archiving."""
        await tracker.register_asset(
            asset_id="history-test",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="history.png",
            quality_score=8.0,
            topic="lions_mane",
        )

        # Add multiple performance entries
        for i in range(5):
            await tracker.record_usage(
                asset_id="history-test",
                post_id=f"post-{i}",
                platform=Platform.INSTAGRAM_FEED,
                publish_date=datetime.now(timezone.utc),
            )

            metrics = PerformanceMetrics(
                engagement_rate=0.03 + i * 0.01,
                conversions=i,
                reach=1000 * (i + 1),
                performance_score=0.0,
                collected_at=datetime.now(timezone.utc),
                collection_interval="24h",
            )
            await tracker.update_performance("history-test", f"post-{i}", metrics)

        # Archive
        archive = await tracker.archive_asset("history-test")

        assert archive.total_usages == 5
        assert archive.performance_summary.total_conversions == 0 + 1 + 2 + 3 + 4  # 10

        # Query again - history should be intact
        record = await tracker.get_usage_stats("history-test")
        assert len(record.performance_history) == 5
        assert len(record.usage_events) == 5
