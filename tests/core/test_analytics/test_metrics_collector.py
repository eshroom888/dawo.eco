"""Tests for InstagramMetricsCollector service.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 4.8: Write comprehensive tests with mocked client and repository.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.analytics.metrics_collector import (
    InstagramMetricsCollector,
    CollectionResult,
    BatchCollectionResult,
)
from core.analytics.models import InstagramMediaMetric
from core.config import AnalyticsConfig
from integrations.instagram.client import MediaInsightsResult


def _make_insights_result(
    media_id: str = "media_123",
    success: bool = True,
    **kwargs,
) -> MediaInsightsResult:
    """Factory for test MediaInsightsResult."""
    defaults = dict(
        impressions=100, reach=80, likes=50, comments=10,
        saved=5, shares=3, total_interactions=68,
    )
    defaults.update(kwargs)
    return MediaInsightsResult(
        success=success,
        media_id=media_id,
        **defaults,
    )


def _make_collector(
    client: AsyncMock | None = None,
    repository: AsyncMock | None = None,
    config: AnalyticsConfig | None = None,
) -> InstagramMetricsCollector:
    """Factory for test collector."""
    return InstagramMetricsCollector(
        client=client or AsyncMock(),
        repository=repository or AsyncMock(),
        config=config or AnalyticsConfig(),
    )


class TestCollectorInit:
    """Tests for collector initialization."""

    def test_constructor_accepts_dependencies(self) -> None:
        client = AsyncMock()
        repo = AsyncMock()
        config = AnalyticsConfig()
        collector = InstagramMetricsCollector(
            client=client, repository=repo, config=config,
        )
        assert collector._client is client
        assert collector._repository is repo
        assert collector._config is config


class TestCollectMetrics:
    """Tests for collect_metrics method (Task 4.3)."""

    @pytest.mark.asyncio
    async def test_collect_metrics_success(self) -> None:
        """Should call client, store via repo, return success."""
        client = AsyncMock()
        client.get_media_insights = AsyncMock(return_value=_make_insights_result())
        repo = AsyncMock()
        repo.save_snapshot = AsyncMock(return_value=MagicMock())

        collector = _make_collector(client=client, repository=repo)
        result = await collector.collect_metrics("media_123", "baseline")

        assert isinstance(result, CollectionResult)
        assert result.success is True
        assert result.media_id == "media_123"
        assert result.snapshot_label == "baseline"
        client.get_media_insights.assert_awaited_once()
        repo.save_snapshot.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_collect_metrics_api_failure(self) -> None:
        """Should return failed result when API call fails."""
        client = AsyncMock()
        client.get_media_insights = AsyncMock(
            return_value=MediaInsightsResult(
                success=False,
                media_id="media_123",
                error_message="API error",
            )
        )
        repo = AsyncMock()

        collector = _make_collector(client=client, repository=repo)
        result = await collector.collect_metrics("media_123", "baseline")

        assert result.success is False
        assert "API error" in result.error_message
        repo.save_snapshot.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_collect_metrics_maps_fields_correctly(self) -> None:
        """Should map insights to model fields."""
        client = AsyncMock()
        insights = _make_insights_result(
            impressions=500, reach=400, likes=200,
            comments=30, saved=20, shares=10,
            total_interactions=260,
        )
        client.get_media_insights = AsyncMock(return_value=insights)
        repo = AsyncMock()
        repo.save_snapshot = AsyncMock(return_value=MagicMock())

        collector = _make_collector(client=client, repository=repo)
        await collector.collect_metrics("media_123", "24h")

        call_args = repo.save_snapshot.call_args[0][0]
        assert isinstance(call_args, InstagramMediaMetric)
        assert call_args.impressions == 500
        assert call_args.reach == 400
        assert call_args.likes == 200
        assert call_args.total_interactions == 260
        assert call_args.snapshot_label == "24h"


class TestCollectBatch:
    """Tests for collect_batch method (Task 4.4)."""

    @pytest.mark.asyncio
    async def test_collect_batch_all_success(self) -> None:
        """Should process all posts and return batch result."""
        client = AsyncMock()
        client.get_media_insights = AsyncMock(
            side_effect=[
                _make_insights_result(media_id="post1"),
                _make_insights_result(media_id="post2"),
            ]
        )
        repo = AsyncMock()
        repo.save_snapshot = AsyncMock(return_value=MagicMock())

        collector = _make_collector(client=client, repository=repo)
        result = await collector.collect_batch(["post1", "post2"], "baseline")

        assert isinstance(result, BatchCollectionResult)
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_collect_batch_partial_failure(self) -> None:
        """Task 4.7: Should handle partial failures."""
        client = AsyncMock()
        client.get_media_insights = AsyncMock(
            side_effect=[
                _make_insights_result(media_id="post1"),
                MediaInsightsResult(
                    success=False, media_id="post2", error_message="Error",
                ),
                _make_insights_result(media_id="post3"),
            ]
        )
        repo = AsyncMock()
        repo.save_snapshot = AsyncMock(return_value=MagicMock())

        collector = _make_collector(client=client, repository=repo)
        result = await collector.collect_batch(["post1", "post2", "post3"], "24h")

        assert result.total == 3
        assert result.succeeded == 2
        assert result.failed == 1
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_collect_batch_empty_list(self) -> None:
        """Should return empty result for empty input."""
        collector = _make_collector()
        result = await collector.collect_batch([], "baseline")

        assert result.total == 0
        assert result.succeeded == 0


class TestCollectionResult:
    """Tests for CollectionResult dataclass."""

    def test_success_result(self) -> None:
        result = CollectionResult(
            success=True,
            media_id="media_123",
            snapshot_label="baseline",
        )
        assert result.success is True
        assert result.error_message is None

    def test_failed_result(self) -> None:
        result = CollectionResult(
            success=False,
            media_id="media_123",
            snapshot_label="baseline",
            error_message="API timeout",
        )
        assert result.success is False
        assert result.error_message == "API timeout"


class TestBatchCollectionResult:
    """Tests for BatchCollectionResult dataclass."""

    def test_batch_result_counts(self) -> None:
        result = BatchCollectionResult(
            total=5,
            succeeded=3,
            failed=2,
            errors={"post1": "err1", "post2": "err2"},
        )
        assert result.total == 5
        assert result.succeeded == 3
        assert result.failed == 2
        assert len(result.errors) == 2
