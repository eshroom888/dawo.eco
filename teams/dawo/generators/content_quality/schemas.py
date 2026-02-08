"""Schema definitions for Content Quality Scorer.

Data classes for quality score requests, results, and component scores.
All types use explicit typing for dependency injection compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from teams.dawo.validators.eu_compliance import ContentComplianceCheck
    from teams.dawo.validators.brand_voice import BrandValidationResult


class ContentType(Enum):
    """Content format type for Instagram."""

    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    INSTAGRAM_REEL = "instagram_reel"


# Default scoring weights (must sum to 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "compliance": 0.25,      # EU compliance status
    "brand_voice": 0.20,     # Brand voice match
    "visual_quality": 0.15,  # Image quality score
    "platform": 0.15,        # Platform optimization
    "engagement": 0.15,      # Engagement prediction
    "authenticity": 0.10,    # AI detectability (inverse)
}


def validate_weights(weights: dict[str, float]) -> None:
    """Validate that weights sum to 1.0.

    Args:
        weights: Dictionary of component weights

    Raises:
        ValueError: If weights don't sum to 1.0 (allowing small float error)
    """
    total = sum(weights.values())
    if not (0.99 <= total <= 1.01):
        raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass
class ComponentScore:
    """Individual component scoring result.

    Contains the raw score, weight, and weighted contribution
    for a single scoring component.

    Attributes:
        component: Component name (e.g., "compliance", "brand_voice")
        raw_score: Unweighted score from 0-10
        weight: Component weight from 0.0-1.0
        weighted_score: raw_score * weight (contribution to total)
        details: Component-specific details and metadata
    """

    component: str
    raw_score: float
    weight: float
    weighted_score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthenticityResult:
    """AI detectability analysis result.

    Contains scores and details about how AI-like the content appears.
    Higher authenticity_score means more human-like content.

    Attributes:
        authenticity_score: 0-10 score (higher = more human-like)
        ai_probability: 0.0-1.0 probability of AI generation
        flagged_patterns: List of detected AI markers (e.g., "generic_phrasing")
        vocabulary_diversity: 0.0-1.0 word variation score
        analysis_confidence: 0.0-1.0 confidence in analysis
    """

    authenticity_score: float
    ai_probability: float
    flagged_patterns: list[str] = field(default_factory=list)
    vocabulary_diversity: float = 0.5
    analysis_confidence: float = 0.5


@dataclass
class PlatformOptimizationResult:
    """Platform-specific optimization check result.

    Contains scores for various platform requirements and
    suggestions for improvement.

    Attributes:
        optimization_score: Overall platform optimization score 0-10
        hashtag_score: Hashtag count and relevance score 0-10
        length_score: Caption length appropriateness score 0-10
        format_score: Content type format fit score 0-10
        brand_hashtags_present: Whether required brand hashtags are present
        has_cta: Whether call-to-action is present
        suggestions: List of improvement suggestions
    """

    optimization_score: float
    hashtag_score: float
    length_score: float
    format_score: float
    brand_hashtags_present: bool
    has_cta: bool
    suggestions: list[str] = field(default_factory=list)


@dataclass
class EngagementPrediction:
    """Engagement prediction based on historical data.

    Predicts expected engagement based on content characteristics
    and historical performance data.

    Attributes:
        predicted_score: 0-10 expected engagement score
        confidence: 0.0-1.0 prediction confidence
        similar_content_avg: Average score of similar past content
        data_points: Number of historical items used for prediction
    """

    predicted_score: float
    confidence: float
    similar_content_avg: Optional[float] = None
    data_points: int = 0


@dataclass
class QualityScoreRequest:
    """Input for quality scoring.

    Combines content, assets, and optional pre-computed validation
    results for comprehensive quality scoring.

    Attributes:
        content: Caption text to score
        content_type: Instagram format (feed, story, reel)
        hashtags: List of hashtags in content
        visual_quality_score: Image quality score from generator (0-10)
        source_type: Content source ("trending", "scheduled", "evergreen", "research")
        compliance_check: Pre-computed compliance check if available
        brand_validation: Pre-computed brand validation if available
        created_at: Request creation timestamp
    """

    content: str
    content_type: ContentType
    hashtags: list[str]
    visual_quality_score: float
    source_type: str
    compliance_check: Optional[Any] = None  # ContentComplianceCheck
    brand_validation: Optional[Any] = None  # BrandValidationResult
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class QualityScoreResult:
    """Complete quality scoring result.

    Contains the total quality score, individual component breakdowns,
    and detailed results from each scoring component.

    Attributes:
        total_score: Final quality score 0-10 (1 decimal place)
        component_scores: List of individual component score breakdowns
        authenticity: Detailed AI detectability analysis
        platform_optimization: Platform-specific optimization details
        engagement_prediction: Engagement prediction details
        scoring_time_ms: Time taken to calculate scores in milliseconds
        recommendations: List of improvement recommendations
        created_at: Result creation timestamp
    """

    total_score: float
    component_scores: list[ComponentScore] = field(default_factory=list)
    authenticity: Optional[AuthenticityResult] = None
    platform_optimization: Optional[PlatformOptimizationResult] = None
    engagement_prediction: Optional[EngagementPrediction] = None
    scoring_time_ms: int = 0
    recommendations: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
