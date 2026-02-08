"""Tests for Asset Usage schemas and dataclasses."""

from datetime import datetime, timezone

import pytest

from teams.dawo.generators.asset_usage import (
    UsageEvent,
    PerformanceMetrics,
    AssetUsageRecord,
    AssetPerformanceResult,
    AssetSuggestion,
    ArchiveRecord,
    Platform,
    AssetType,
    AssetStatus,
)


class TestEnums:
    """Tests for enum types."""

    def test_platform_values(self) -> None:
        """Verify Platform enum values."""
        assert Platform.INSTAGRAM_FEED.value == "instagram_feed"
        assert Platform.INSTAGRAM_STORY.value == "instagram_story"
        assert Platform.INSTAGRAM_REEL.value == "instagram_reel"

    def test_asset_type_values(self) -> None:
        """Verify AssetType enum values."""
        assert AssetType.ORSHOT_GRAPHIC.value == "orshot_graphic"
        assert AssetType.NANO_BANANA_IMAGE.value == "nano_banana_image"
        assert AssetType.PRODUCT_PHOTO.value == "product_photo"

    def test_asset_status_values(self) -> None:
        """Verify AssetStatus enum values."""
        assert AssetStatus.ACTIVE.value == "active"
        assert AssetStatus.ARCHIVED.value == "archived"


class TestUsageEvent:
    """Tests for UsageEvent dataclass."""

    def test_create_usage_event(self) -> None:
        """Create UsageEvent with required fields."""
        event = UsageEvent(
            event_id="event-001",
            asset_id="asset-001",
            post_id="post-001",
            platform=Platform.INSTAGRAM_FEED,
            publish_date=datetime(2026, 2, 8, 12, 0, 0, tzinfo=timezone.utc),
        )

        assert event.event_id == "event-001"
        assert event.asset_id == "asset-001"
        assert event.post_id == "post-001"
        assert event.platform == Platform.INSTAGRAM_FEED
        assert event.created_at is not None

    def test_usage_event_default_created_at(self) -> None:
        """Verify created_at defaults to current UTC time."""
        before = datetime.now(timezone.utc)
        event = UsageEvent(
            event_id="event-002",
            asset_id="asset-001",
            post_id="post-002",
            platform=Platform.INSTAGRAM_STORY,
            publish_date=datetime.now(timezone.utc),
        )
        after = datetime.now(timezone.utc)

        assert before <= event.created_at <= after


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics dataclass."""

    def test_create_performance_metrics(self) -> None:
        """Create PerformanceMetrics with all fields."""
        metrics = PerformanceMetrics(
            engagement_rate=0.05,
            conversions=3,
            reach=2340,
            performance_score=5.5,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        assert metrics.engagement_rate == 0.05
        assert metrics.conversions == 3
        assert metrics.reach == 2340
        assert metrics.performance_score == 5.5
        assert metrics.collection_interval == "24h"

    def test_zero_metrics(self) -> None:
        """Create metrics with zero values."""
        metrics = PerformanceMetrics(
            engagement_rate=0.0,
            conversions=0,
            reach=0,
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        assert metrics.engagement_rate == 0.0
        assert metrics.conversions == 0
        assert metrics.reach == 0

    def test_engagement_rate_above_one_raises_error(self) -> None:
        """Engagement rate above 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="engagement_rate must be between"):
            PerformanceMetrics(
                engagement_rate=1.5,  # Invalid: > 1.0
                conversions=0,
                reach=0,
                performance_score=0.0,
                collected_at=datetime.now(timezone.utc),
                collection_interval="24h",
            )

    def test_engagement_rate_negative_raises_error(self) -> None:
        """Negative engagement rate raises ValueError."""
        with pytest.raises(ValueError, match="engagement_rate must be between"):
            PerformanceMetrics(
                engagement_rate=-0.1,  # Invalid: < 0.0
                conversions=0,
                reach=0,
                performance_score=0.0,
                collected_at=datetime.now(timezone.utc),
                collection_interval="24h",
            )

    def test_negative_conversions_raises_error(self) -> None:
        """Negative conversions raises ValueError."""
        with pytest.raises(ValueError, match="conversions must be non-negative"):
            PerformanceMetrics(
                engagement_rate=0.05,
                conversions=-1,  # Invalid: < 0
                reach=0,
                performance_score=0.0,
                collected_at=datetime.now(timezone.utc),
                collection_interval="24h",
            )

    def test_negative_reach_raises_error(self) -> None:
        """Negative reach raises ValueError."""
        with pytest.raises(ValueError, match="reach must be non-negative"):
            PerformanceMetrics(
                engagement_rate=0.05,
                conversions=0,
                reach=-100,  # Invalid: < 0
                performance_score=0.0,
                collected_at=datetime.now(timezone.utc),
                collection_interval="24h",
            )

    def test_boundary_engagement_rate_one(self) -> None:
        """Engagement rate of exactly 1.0 is valid."""
        metrics = PerformanceMetrics(
            engagement_rate=1.0,  # Valid: exactly 1.0
            conversions=0,
            reach=0,
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        assert metrics.engagement_rate == 1.0


class TestAssetUsageRecord:
    """Tests for AssetUsageRecord dataclass."""

    def test_create_asset_record(self) -> None:
        """Create AssetUsageRecord with required fields."""
        record = AssetUsageRecord(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="DAWO.ECO/Assets/Orshot/test.png",
            original_quality_score=8.5,
            topic="lions_mane",
        )

        assert record.asset_id == "asset-001"
        assert record.asset_type == AssetType.ORSHOT_GRAPHIC
        assert record.original_quality_score == 8.5
        assert record.status == AssetStatus.ACTIVE
        assert record.usage_events == []
        assert record.performance_history == []
        assert record.overall_performance is None
        assert record.archived_at is None

    def test_record_with_usage_events(self) -> None:
        """Create record with usage events."""
        event = UsageEvent(
            event_id="event-001",
            asset_id="asset-001",
            post_id="post-001",
            platform=Platform.INSTAGRAM_FEED,
            publish_date=datetime.now(timezone.utc),
        )

        record = AssetUsageRecord(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            original_quality_score=8.5,
            topic="lions_mane",
            usage_events=[event],
        )

        assert len(record.usage_events) == 1
        assert record.usage_events[0].post_id == "post-001"


class TestAssetPerformanceResult:
    """Tests for AssetPerformanceResult dataclass."""

    def test_create_performance_result(self) -> None:
        """Create AssetPerformanceResult with breakdown."""
        result = AssetPerformanceResult(
            asset_id="asset-001",
            overall_score=7.5,
            usage_count=5,
            avg_engagement_rate=0.045,
            total_conversions=15,
            avg_reach=2500,
            score_breakdown={
                "engagement": 4.5,
                "conversions": 3.0,
                "reach": 2.5,
            },
        )

        assert result.overall_score == 7.5
        assert result.usage_count == 5
        assert result.total_conversions == 15
        assert "engagement" in result.score_breakdown


class TestAssetSuggestion:
    """Tests for AssetSuggestion dataclass."""

    def test_create_suggestion(self) -> None:
        """Create AssetSuggestion for content selection."""
        suggestion = AssetSuggestion(
            asset_id="asset-001",
            file_path="DAWO.ECO/Assets/Orshot/test.png",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            topic="lions_mane",
            performance_score=8.5,
            usage_count=3,
            last_used=datetime.now(timezone.utc),
            quality_score=7.0,
            rank=1,
        )

        assert suggestion.rank == 1
        assert suggestion.performance_score == 8.5
        assert suggestion.usage_count == 3

    def test_suggestion_without_last_used(self) -> None:
        """Create suggestion for never-used asset."""
        suggestion = AssetSuggestion(
            asset_id="asset-002",
            file_path="test.png",
            asset_type=AssetType.NANO_BANANA_IMAGE,
            topic="wellness",
            performance_score=7.5,
            usage_count=0,
            last_used=None,
            quality_score=7.5,
            rank=2,
        )

        assert suggestion.last_used is None
        assert suggestion.usage_count == 0


class TestArchiveRecord:
    """Tests for ArchiveRecord dataclass."""

    def test_create_archive_record(self) -> None:
        """Create ArchiveRecord with performance summary."""
        performance = AssetPerformanceResult(
            asset_id="asset-001",
            overall_score=8.0,
            usage_count=10,
            avg_engagement_rate=0.05,
            total_conversions=25,
            avg_reach=3000,
            score_breakdown={},
        )

        archive = ArchiveRecord(
            asset_id="asset-001",
            original_path="DAWO.ECO/Assets/Orshot/original.png",
            archive_path="DAWO.ECO/Assets/Archive/original.png",
            archive_date=datetime.now(timezone.utc),
            performance_summary=performance,
            total_usages=10,
            metadata={"topic": "lions_mane"},
        )

        assert archive.total_usages == 10
        assert archive.performance_summary.overall_score == 8.0
        assert archive.metadata["topic"] == "lions_mane"

    def test_archive_without_performance(self) -> None:
        """Create ArchiveRecord for unused asset."""
        archive = ArchiveRecord(
            asset_id="asset-002",
            original_path="original.png",
            archive_path="archive.png",
            archive_date=datetime.now(timezone.utc),
            performance_summary=None,
            total_usages=0,
            metadata={},
        )

        assert archive.performance_summary is None
        assert archive.total_usages == 0
