"""Tests for Asset Usage scoring calculations."""

from datetime import datetime, timezone

import pytest

from teams.dawo.generators.asset_usage import (
    calculate_performance_score,
    calculate_overall_performance,
    PERFORMANCE_WEIGHTS,
    PerformanceMetrics,
    AssetUsageRecord,
    AssetType,
)


class TestPerformanceWeights:
    """Tests for performance weight configuration."""

    def test_weights_sum_to_one(self) -> None:
        """Verify performance weights sum to 1.0."""
        total = sum(PERFORMANCE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001  # Allow small float precision error

    def test_weight_keys(self) -> None:
        """Verify expected weight keys exist."""
        expected_keys = {"engagement_rate", "conversions", "reach"}
        assert set(PERFORMANCE_WEIGHTS.keys()) == expected_keys


class TestCalculatePerformanceScore:
    """Tests for individual performance score calculation."""

    def test_zero_metrics_score(self, zero_metrics: PerformanceMetrics) -> None:
        """Score for zero engagement should be 0."""
        score = calculate_performance_score(zero_metrics)
        assert score == 0.0

    def test_typical_metrics_score(
        self, sample_performance_metrics: PerformanceMetrics
    ) -> None:
        """Score for typical metrics (5% engagement, 3 conversions, 2340 reach).

        Expected calculation:
        - engagement_score = min(10, 0.05 * 100) = 5.0
        - conversion_score = min(10, 3) = 3.0
        - reach_score = min(10, 2340 / 1000) = 2.34

        Weighted: 5.0*0.4 + 3.0*0.3 + 2.34*0.3 = 2.0 + 0.9 + 0.702 = 3.602 ≈ 3.6
        """
        score = calculate_performance_score(sample_performance_metrics)
        # Check it's in reasonable range
        assert 3.0 <= score <= 4.0

    def test_high_performance_score(
        self, high_performance_metrics: PerformanceMetrics
    ) -> None:
        """Score for high performance metrics.

        Expected calculation:
        - engagement_score = min(10, 0.10 * 100) = 10.0
        - conversion_score = min(10, 10) = 10.0
        - reach_score = min(10, 5000 / 1000) = 5.0

        Weighted: 10.0*0.4 + 10.0*0.3 + 5.0*0.3 = 4.0 + 3.0 + 1.5 = 8.5
        """
        score = calculate_performance_score(high_performance_metrics)
        assert score == 8.5

    def test_low_performance_score(
        self, low_performance_metrics: PerformanceMetrics
    ) -> None:
        """Score for low performance metrics.

        Expected calculation:
        - engagement_score = min(10, 0.01 * 100) = 1.0
        - conversion_score = min(10, 0) = 0.0
        - reach_score = min(10, 500 / 1000) = 0.5

        Weighted: 1.0*0.4 + 0.0*0.3 + 0.5*0.3 = 0.4 + 0.0 + 0.15 = 0.55 ≈ 0.6
        """
        score = calculate_performance_score(low_performance_metrics)
        assert 0.5 <= score <= 0.6

    def test_max_engagement_caps_at_ten(self) -> None:
        """Verify engagement score caps at 10 for very high values."""
        metrics = PerformanceMetrics(
            engagement_rate=0.20,  # 20% would be 20 but caps at 10
            conversions=0,
            reach=0,
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        score = calculate_performance_score(metrics)
        # Should be 10.0 * 0.4 = 4.0 (engagement capped)
        assert score == 4.0

    def test_max_conversions_caps_at_ten(self) -> None:
        """Verify conversion score caps at 10 for very high values."""
        metrics = PerformanceMetrics(
            engagement_rate=0.0,
            conversions=50,  # 50 would be 50 but caps at 10
            reach=0,
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        score = calculate_performance_score(metrics)
        # Should be 10.0 * 0.3 = 3.0 (conversions capped)
        assert score == 3.0

    def test_max_reach_caps_at_ten(self) -> None:
        """Verify reach score caps at 10 for very high values."""
        metrics = PerformanceMetrics(
            engagement_rate=0.0,
            conversions=0,
            reach=50000,  # Would be 50 but caps at 10
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        score = calculate_performance_score(metrics)
        # Should be 10.0 * 0.3 = 3.0 (reach capped)
        assert score == 3.0

    def test_maximum_possible_score(self) -> None:
        """Maximum score should be 10.0 when all metrics are excellent."""
        metrics = PerformanceMetrics(
            engagement_rate=0.15,  # 15% caps at 10
            conversions=20,  # 20 caps at 10
            reach=20000,  # 20k caps at 10
            performance_score=0.0,
            collected_at=datetime.now(timezone.utc),
            collection_interval="24h",
        )

        score = calculate_performance_score(metrics)
        assert score == 10.0


class TestCalculateOverallPerformance:
    """Tests for overall asset performance calculation."""

    def test_no_performance_history(self) -> None:
        """Asset with no performance history uses original quality score."""
        record = AssetUsageRecord(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            original_quality_score=8.5,
            topic="lions_mane",
        )

        result = calculate_overall_performance(record)

        assert result.overall_score == 8.5  # Falls back to original
        assert result.usage_count == 0
        assert result.avg_engagement_rate == 0.0
        assert result.total_conversions == 0

    def test_single_performance_entry(
        self, sample_performance_metrics: PerformanceMetrics
    ) -> None:
        """Asset with single performance entry."""
        record = AssetUsageRecord(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            original_quality_score=8.5,
            topic="lions_mane",
            performance_history=[sample_performance_metrics],
        )

        result = calculate_overall_performance(record)

        assert result.usage_count == 0  # No usage events
        assert result.avg_engagement_rate == 0.05
        assert result.total_conversions == 3
        assert result.avg_reach == 2340

    def test_multiple_performance_entries(
        self,
        sample_performance_metrics: PerformanceMetrics,
        high_performance_metrics: PerformanceMetrics,
    ) -> None:
        """Asset with multiple performance entries computes averages."""
        record = AssetUsageRecord(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            original_quality_score=8.5,
            topic="lions_mane",
            performance_history=[
                sample_performance_metrics,  # 0.05 engagement, 3 conv, 2340 reach
                high_performance_metrics,  # 0.10 engagement, 10 conv, 5000 reach
            ],
        )

        result = calculate_overall_performance(record)

        # Average engagement: (0.05 + 0.10) / 2 = 0.075
        assert abs(result.avg_engagement_rate - 0.075) < 0.001

        # Total conversions: 3 + 10 = 13
        assert result.total_conversions == 13

        # Average reach: (2340 + 5000) / 2 = 3670
        assert result.avg_reach == 3670

    def test_score_breakdown_included(
        self, sample_performance_metrics: PerformanceMetrics
    ) -> None:
        """Verify score breakdown is included in result."""
        record = AssetUsageRecord(
            asset_id="asset-001",
            asset_type=AssetType.ORSHOT_GRAPHIC,
            file_path="test.png",
            original_quality_score=8.5,
            topic="lions_mane",
            performance_history=[sample_performance_metrics],
        )

        result = calculate_overall_performance(record)

        assert "engagement" in result.score_breakdown
        assert "conversions" in result.score_breakdown
        assert "reach" in result.score_breakdown
