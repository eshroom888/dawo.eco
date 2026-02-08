"""Content Quality Scorer Agent.

Calculates unified quality scores for content items by aggregating
scores from multiple components (compliance, brand voice, visual quality,
platform optimization, engagement prediction, authenticity).

Uses the 'generate' tier for AI detectability analysis.
Configuration is received via dependency injection - NEVER loads config directly.
"""

from datetime import datetime, timezone
from typing import Optional, Protocol
import logging

from .schemas import (
    QualityScoreRequest,
    QualityScoreResult,
    ComponentScore,
    DEFAULT_WEIGHTS,
    validate_weights,
)
from .scorers import (
    ComplianceScorer,
    ComplianceScorerConfig,
    BrandVoiceScorer,
    BrandVoiceScorerConfig,
    VisualQualityScorer,
    VisualQualityScorerConfig,
    PlatformOptimizationScorer,
    PlatformScorerConfig,
    EngagementPredictionScorer,
    EngagementScorerConfig,
    AuthenticityScorer,
    AuthenticityScorerConfig,
    LLMClientProtocol,
)

# Module logger
logger = logging.getLogger(__name__)


class ContentQualityScorerProtocol(Protocol):
    """Protocol for content quality scorer.

    Defines the interface for dependency injection and testing.
    """

    async def score_content(
        self,
        request: QualityScoreRequest
    ) -> QualityScoreResult:
        """Calculate quality score for content.

        Args:
            request: QualityScoreRequest with content and metadata

        Returns:
            QualityScoreResult with total score and component breakdown
        """
        ...


class ContentQualityScorer:
    """Calculates unified quality score for content items.

    Aggregates scores from multiple components (compliance, brand voice,
    visual quality, platform optimization, engagement prediction, authenticity)
    into a single 0-10 quality score with configurable weights.

    Uses the 'generate' tier for AI detectability analysis.
    Configuration is received via dependency injection - NEVER loads config directly.

    Attributes:
        compliance_checker: EU Compliance Checker for compliance scoring
        brand_validator: Brand Voice Validator for brand alignment
        llm_client: LLM client for AI detectability analysis
    """

    def __init__(
        self,
        compliance_checker: object,  # EUComplianceChecker
        brand_validator: object,  # BrandVoiceValidator
        llm_client: LLMClientProtocol,
        weights: Optional[dict[str, float]] = None,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            compliance_checker: EU Compliance Checker for compliance scoring
            brand_validator: Brand Voice Validator for brand alignment
            llm_client: LLM client for AI detectability analysis
            weights: Optional custom scoring weights (default: DEFAULT_WEIGHTS)

        Raises:
            ValueError: If weights don't sum to 1.0
        """
        self._weights = weights or DEFAULT_WEIGHTS.copy()
        validate_weights(self._weights)

        # Initialize component scorers with individual configs
        self._compliance_scorer = ComplianceScorer(
            compliance_checker=compliance_checker,
            config=ComplianceScorerConfig(weight=self._weights.get("compliance", 0.25)),
        )
        self._brand_scorer = BrandVoiceScorer(
            brand_validator=brand_validator,
            config=BrandVoiceScorerConfig(weight=self._weights.get("brand_voice", 0.20)),
        )
        self._visual_scorer = VisualQualityScorer(
            config=VisualQualityScorerConfig(weight=self._weights.get("visual_quality", 0.15)),
        )
        self._platform_scorer = PlatformOptimizationScorer(
            config=PlatformScorerConfig(weight=self._weights.get("platform", 0.15)),
        )
        self._engagement_scorer = EngagementPredictionScorer(
            config=EngagementScorerConfig(weight=self._weights.get("engagement", 0.15)),
        )
        self._authenticity_scorer = AuthenticityScorer(
            llm_client=llm_client,
            config=AuthenticityScorerConfig(weight=self._weights.get("authenticity", 0.10)),
        )

    async def score_content(
        self,
        request: QualityScoreRequest
    ) -> QualityScoreResult:
        """Calculate quality score for content.

        Scores content across all components and returns a weighted
        total score along with individual component breakdowns.

        Args:
            request: QualityScoreRequest with content and metadata

        Returns:
            QualityScoreResult with total score and component breakdown
        """
        start_time = datetime.now(timezone.utc)
        component_scores: list[ComponentScore] = []
        recommendations: list[str] = []

        try:
            # Score compliance
            compliance_score = await self._compliance_scorer.score(
                content=request.content,
                precomputed_check=request.compliance_check,
            )
            component_scores.append(compliance_score)

            # Score brand voice
            brand_score = await self._brand_scorer.score(
                content=request.content,
                precomputed_validation=request.brand_validation,
            )
            component_scores.append(brand_score)

            # Score visual quality (synchronous - uses input score)
            visual_score = self._visual_scorer.score(
                visual_quality_score=request.visual_quality_score,
            )
            component_scores.append(visual_score)

            # Score platform optimization
            platform_result = self._platform_scorer.score(
                content=request.content,
                content_type=request.content_type,
                hashtags=request.hashtags,
            )
            component_scores.append(platform_result)
            recommendations.extend(platform_result.details.get("suggestions", []))

            # Score engagement prediction
            engagement_score = await self._engagement_scorer.score(
                source_type=request.source_type,
                content_type=request.content_type.value if request.content_type else None,
                hashtags=request.hashtags,
            )
            component_scores.append(engagement_score)

            # Score authenticity
            authenticity_score = await self._authenticity_scorer.score(
                content=request.content,
            )
            component_scores.append(authenticity_score)

            # Calculate weighted total
            total_score = sum(cs.weighted_score for cs in component_scores)
            total_score = round(total_score, 1)

            # Clamp to valid range
            total_score = max(0.0, min(10.0, total_score))

            end_time = datetime.now(timezone.utc)
            scoring_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return QualityScoreResult(
                total_score=total_score,
                component_scores=component_scores,
                authenticity=authenticity_score.details.get("result"),
                platform_optimization=platform_result.details.get("result"),
                engagement_prediction=engagement_score.details.get("prediction"),
                scoring_time_ms=scoring_time_ms,
                recommendations=recommendations,
                created_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error("Quality scoring failed: %s", e)
            raise
