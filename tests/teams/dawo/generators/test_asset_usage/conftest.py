"""Test fixtures for Asset Usage Tracking tests.

Provides reusable fixtures for testing the asset usage tracker
including mock dependencies and sample data.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from integrations.google_drive import DriveAsset

from teams.dawo.generators.asset_usage import (
    AssetUsageTracker,
    AssetUsageRepository,
    AssetUsageRecord,
    UsageEvent,
    PerformanceMetrics,
    AssetSuggestion,
    Platform,
    AssetType,
    AssetStatus,
)


@pytest.fixture
def mock_drive_client() -> AsyncMock:
    """Mock Google Drive client."""
    client = AsyncMock()
    # Configure move_to_archive return value
    client.move_to_archive.return_value = DriveAsset(
        id="archived-file-id",
        name="2026-02-08_orshot_lionsmane_archived.png",
        folder_id="archive-folder-id",
        web_view_link="https://drive.google.com/view/archived",
        download_link="https://drive.google.com/download/archived",
        mime_type="image/png",
        created_at=datetime.now(timezone.utc),
        metadata={"archived": "true"},
    )
    return client


@pytest.fixture
def repository() -> AssetUsageRepository:
    """Fresh repository for each test."""
    return AssetUsageRepository()


@pytest.fixture
def tracker(
    mock_drive_client: AsyncMock,
    repository: AssetUsageRepository,
) -> AssetUsageTracker:
    """AssetUsageTracker with mocked dependencies."""
    return AssetUsageTracker(
        drive_client=mock_drive_client,
        repository=repository,
    )


@pytest.fixture
def sample_asset_record() -> AssetUsageRecord:
    """Sample asset for testing."""
    return AssetUsageRecord(
        asset_id="asset-001",
        asset_type=AssetType.ORSHOT_GRAPHIC,
        file_path="DAWO.ECO/Assets/Orshot/2026-02-08_orshot_lionsmane_001.png",
        original_quality_score=8.5,
        topic="lions_mane",
    )


@pytest.fixture
def sample_nano_banana_asset() -> AssetUsageRecord:
    """Sample Nano Banana AI image asset."""
    return AssetUsageRecord(
        asset_id="asset-002",
        asset_type=AssetType.NANO_BANANA_IMAGE,
        file_path="DAWO.ECO/Assets/Generated/2026-02-08_generated_wellness_002.png",
        original_quality_score=7.5,
        topic="wellness",
    )


@pytest.fixture
def sample_usage_event() -> UsageEvent:
    """Sample usage event."""
    return UsageEvent(
        event_id="asset-001_post-abc123",
        asset_id="asset-001",
        post_id="post-abc123",
        platform=Platform.INSTAGRAM_FEED,
        publish_date=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_performance_metrics() -> PerformanceMetrics:
    """Sample performance metrics with good engagement."""
    return PerformanceMetrics(
        engagement_rate=0.05,
        conversions=3,
        reach=2340,
        performance_score=0.0,  # Will be calculated
        collected_at=datetime.now(timezone.utc),
        collection_interval="24h",
    )


@pytest.fixture
def high_performance_metrics() -> PerformanceMetrics:
    """High-performing metrics for testing."""
    return PerformanceMetrics(
        engagement_rate=0.10,  # 10% engagement is excellent
        conversions=10,
        reach=5000,
        performance_score=0.0,
        collected_at=datetime.now(timezone.utc),
        collection_interval="48h",
    )


@pytest.fixture
def low_performance_metrics() -> PerformanceMetrics:
    """Low-performing metrics for testing."""
    return PerformanceMetrics(
        engagement_rate=0.01,  # 1% engagement
        conversions=0,
        reach=500,
        performance_score=0.0,
        collected_at=datetime.now(timezone.utc),
        collection_interval="24h",
    )


@pytest.fixture
def zero_metrics() -> PerformanceMetrics:
    """Zero performance metrics for edge case testing."""
    return PerformanceMetrics(
        engagement_rate=0.0,
        conversions=0,
        reach=0,
        performance_score=0.0,
        collected_at=datetime.now(timezone.utc),
        collection_interval="24h",
    )
