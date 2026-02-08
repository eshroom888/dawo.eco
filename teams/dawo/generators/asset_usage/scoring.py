"""Performance score calculation for assets.

Implements weighted scoring based on engagement, conversions, and reach.
"""

from .schemas import (
    AssetPerformanceResult,
    AssetUsageRecord,
    PerformanceMetrics,
)


# Performance score weights (must sum to 1.0)
PERFORMANCE_WEIGHTS: dict[str, float] = {
    "engagement_rate": 0.40,    # Engagement is primary indicator
    "conversions": 0.30,        # Revenue impact
    "reach": 0.30,              # Visibility impact
}


def calculate_performance_score(metrics: PerformanceMetrics) -> float:
    """Calculate performance score from metrics.

    Normalizes each metric to 0-10 scale and applies weights.

    Args:
        metrics: PerformanceMetrics with engagement, conversions, reach

    Returns:
        Float score 0-10
    """
    # Normalize engagement rate: 0.0-0.10 is typical, 0.05+ is good
    # Multiply by 100 to scale 0.05 -> 5.0
    engagement_score = min(10.0, metrics.engagement_rate * 100)

    # Conversions: 0-10+ per post is good, direct mapping
    conversion_score = min(10.0, float(metrics.conversions))

    # Reach: 0-10000 typical for Instagram, normalize to 0-10
    reach_score = min(10.0, metrics.reach / 1000)

    # Weighted sum
    total = (
        engagement_score * PERFORMANCE_WEIGHTS["engagement_rate"]
        + conversion_score * PERFORMANCE_WEIGHTS["conversions"]
        + reach_score * PERFORMANCE_WEIGHTS["reach"]
    )

    return round(total, 1)


def calculate_overall_performance(record: AssetUsageRecord) -> AssetPerformanceResult:
    """Calculate overall performance from all usage history.

    Computes averages across all performance metrics collected.

    Args:
        record: AssetUsageRecord with performance_history

    Returns:
        AssetPerformanceResult with aggregated scores
    """
    if not record.performance_history:
        # No performance data yet - use original quality score
        return AssetPerformanceResult(
            asset_id=record.asset_id,
            overall_score=record.original_quality_score,
            usage_count=len(record.usage_events),
            avg_engagement_rate=0.0,
            total_conversions=0,
            avg_reach=0,
            score_breakdown={
                "engagement": 0.0,
                "conversions": 0.0,
                "reach": 0.0,
            },
        )

    # Aggregate metrics
    total_engagement = sum(m.engagement_rate for m in record.performance_history)
    total_conversions = sum(m.conversions for m in record.performance_history)
    total_reach = sum(m.reach for m in record.performance_history)

    count = len(record.performance_history)
    avg_engagement = total_engagement / count
    avg_reach = total_reach // count

    # Calculate individual component scores
    engagement_score = min(10.0, avg_engagement * 100)
    conversion_score = min(10.0, float(total_conversions) / count)
    reach_score = min(10.0, avg_reach / 1000)

    # Weighted overall score
    overall_score = (
        engagement_score * PERFORMANCE_WEIGHTS["engagement_rate"]
        + conversion_score * PERFORMANCE_WEIGHTS["conversions"]
        + reach_score * PERFORMANCE_WEIGHTS["reach"]
    )

    return AssetPerformanceResult(
        asset_id=record.asset_id,
        overall_score=round(overall_score, 1),
        usage_count=len(record.usage_events),
        avg_engagement_rate=round(avg_engagement, 4),
        total_conversions=total_conversions,
        avg_reach=avg_reach,
        score_breakdown={
            "engagement": round(engagement_score, 1),
            "conversions": round(conversion_score, 1),
            "reach": round(reach_score, 1),
        },
    )
