"""Analytics module for Instagram engagement, UTM click-through, Shopify attribution, quality scoring, and feedback loops.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Epic 7, Story 7-2: UTM Click-Through Tracking.
Epic 7, Story 7-3: Shopify Sales Attribution.
Epic 7, Story 7-4: Post-Publish Quality Scoring.
Epic 7, Story 7-5: Performance Feedback Loop.

Provides models, repositories, services, and query APIs for
tracking post performance, click-through attribution, revenue analytics,
post-publish quality scoring with variance analysis, and performance feedback loops.
"""

from core.analytics.attribution_models import (
    AttributionType,
    OrderAttributionRecord,
    ShopifyOrderRecord,
)
from core.analytics.attribution_repository import AttributionRepository
from core.analytics.attribution_service import (
    AttributionResult,
    AttributionService,
    BatchAttributionResult,
)
from core.analytics.click_analytics import (
    ClickAnalyticsService,
    ClickComparison,
    PostClickAnalytics,
)
from core.analytics.comment_sentiment import (
    CommentSentimentResult,
    CommentSentimentScorer,
)
from core.analytics.metrics_collector import (
    BatchCollectionResult,
    CollectionResult,
    InstagramMetricsCollector,
)
from core.analytics.metrics_query import (
    AverageMetrics,
    MetricsDelta,
    MetricsQueryService,
    PerformanceComparison,
    PostMetricsResult,
)
from core.analytics.models import InstagramMediaMetric, SnapshotLabel
from core.analytics.quality_scoring_analyzer import (
    ComponentDeviation,
    CorrelationReport,
    OutperformerAnalysis,
    VarianceAnalyzer,
    VarianceReport,
)
from core.analytics.quality_scoring_models import PostPublishScoreRecord
from core.analytics.quality_scoring_repository import QualityScoringRepository
from core.analytics.quality_scoring_service import (
    ComponentScoreDetail,
    PostPublishScoreResult,
    PostPublishScoringService,
)
from core.analytics.repository import InstagramMetricsRepository
from core.analytics.revenue_analytics import (
    PostAnalyticsSummary,
    PostRevenueResult,
    RevenueAnalyticsService,
    RevenueComparison,
    ROIEstimate,
)
from core.analytics.utm_integration import generate_post_short_link
from core.analytics.utm_models import LinkClick, ShortLink
from core.analytics.utm_repository import UTMRepository
from core.analytics.utm_service import ShortLinkService
from core.analytics.content_performance_analyzer import (
    ContentPerformanceAnalyzer,
    ContentTypeAnalysis,
    ContentTypeRanking,
    HashtagAnalysis,
    HashtagRanking,
    SourcePerformanceAnalysis,
    SourceRanking,
    TimeSlot,
    TimeSlotAnalysis,
)
from core.analytics.feedback_loop_models import (
    FeedbackReport,
    WeightAdjustmentRecord,
)
from core.analytics.feedback_loop_repository import FeedbackLoopRepository
from core.analytics.feedback_loop_service import FeedbackLoopService
from core.analytics.weight_adjuster import (
    WeightAdjuster,
    WeightAdjustmentProposal,
)

__all__ = [
    "AttributionRepository",
    "AttributionResult",
    "AttributionService",
    "AttributionType",
    "AverageMetrics",
    "BatchAttributionResult",
    "BatchCollectionResult",
    "ClickAnalyticsService",
    "ClickComparison",
    "CollectionResult",
    "CommentSentimentResult",
    "CommentSentimentScorer",
    "ComponentDeviation",
    "ComponentScoreDetail",
    "CorrelationReport",
    "InstagramMediaMetric",
    "InstagramMetricsCollector",
    "InstagramMetricsRepository",
    "LinkClick",
    "MetricsDelta",
    "MetricsQueryService",
    "OrderAttributionRecord",
    "OutperformerAnalysis",
    "PerformanceComparison",
    "PostAnalyticsSummary",
    "PostClickAnalytics",
    "PostMetricsResult",
    "PostPublishScoreRecord",
    "PostPublishScoreResult",
    "PostPublishScoringService",
    "PostRevenueResult",
    "QualityScoringRepository",
    "RevenueAnalyticsService",
    "RevenueComparison",
    "ROIEstimate",
    "ShopifyOrderRecord",
    "ShortLink",
    "ShortLinkService",
    "SnapshotLabel",
    "UTMRepository",
    "VarianceAnalyzer",
    "VarianceReport",
    "generate_post_short_link",
    # Story 7-5: Feedback Loop
    "ContentPerformanceAnalyzer",
    "ContentTypeAnalysis",
    "ContentTypeRanking",
    "FeedbackLoopRepository",
    "FeedbackLoopService",
    "FeedbackReport",
    "HashtagAnalysis",
    "HashtagRanking",
    "SourcePerformanceAnalysis",
    "SourceRanking",
    "TimeSlot",
    "TimeSlotAnalysis",
    "WeightAdjuster",
    "WeightAdjustmentProposal",
    "WeightAdjustmentRecord",
]
