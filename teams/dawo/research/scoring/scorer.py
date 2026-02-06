"""Composite scoring engine for research items.

Combines all scoring components using weighted average:
- Relevance (default 25%)
- Recency (default 20%)
- Source Quality (default 25%)
- Engagement (default 20%)
- Compliance (default 10%)

Applies compliance adjustment after weighted average:
- COMPLIANT: +1 bonus (capped at 10)
- WARNING: No adjustment
- REJECTED: Score forced to 0
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .config import ScoringConfig
from .schemas import ScoringResult, ComponentScore
from .components.relevance import RelevanceScorer
from .components.recency import RecencyScorer
from .components.source_quality import SourceQualityScorer
from .components.engagement import EngagementScorer
from .components.compliance import ComplianceAdjuster

logger = logging.getLogger(__name__)

# Score limits
MAX_FINAL_SCORE: float = 10.0
MIN_FINAL_SCORE: float = 0.0


class ResearchItemScorer:
    """Composite scorer for research items.

    Calculates content potential scores using weighted component analysis.
    All dependencies are injected via constructor for testability.

    Scoring Formula:
        weighted_score = (relevance * 0.25) + (recency * 0.20) +
                        (source_quality * 0.25) + (engagement * 0.20) +
                        (compliance_base * 0.10)

        if compliance_status == REJECTED:
            final_score = 0
        elif compliance_status == COMPLIANT:
            final_score = min(weighted_score + 1, 10)
        else:  # WARNING
            final_score = weighted_score

    Attributes:
        _config: Scoring configuration with weights.
        _relevance: RelevanceScorer component.
        _recency: RecencyScorer component.
        _source_quality: SourceQualityScorer component.
        _engagement: EngagementScorer component.
        _compliance: ComplianceAdjuster component.
    """

    def __init__(
        self,
        config: ScoringConfig,
        relevance_scorer: RelevanceScorer,
        recency_scorer: RecencyScorer,
        source_quality_scorer: SourceQualityScorer,
        engagement_scorer: EngagementScorer,
        compliance_adjuster: ComplianceAdjuster,
    ) -> None:
        """Accept all dependencies via injection from Team Builder.

        Args:
            config: ScoringConfig with component weights.
            relevance_scorer: RelevanceScorer for keyword matching.
            recency_scorer: RecencyScorer for time decay.
            source_quality_scorer: SourceQualityScorer for source tiers.
            engagement_scorer: EngagementScorer for engagement metrics.
            compliance_adjuster: ComplianceAdjuster for compliance status.
        """
        self._config = config
        self._relevance = relevance_scorer
        self._recency = recency_scorer
        self._source_quality = source_quality_scorer
        self._engagement = engagement_scorer
        self._compliance = compliance_adjuster

    def calculate_score(self, item: dict[str, Any]) -> ScoringResult:
        """Calculate composite score for a research item.

        Args:
            item: Dictionary with research item fields.

        Returns:
            ScoringResult with final score, component breakdown, and reasoning.
        """
        source = item.get("source", "").lower()
        weights = self._config.get_weights_for_source(source)

        # Calculate component scores
        relevance_score = self._relevance.score(item)
        recency_score = self._recency.score(item)
        source_quality_score = self._source_quality.score(item)
        engagement_score = self._engagement.score(item)

        # Apply weights
        relevance_score.weighted_score = relevance_score.raw_score * weights.relevance
        recency_score.weighted_score = recency_score.raw_score * weights.recency
        source_quality_score.weighted_score = source_quality_score.raw_score * weights.source_quality
        engagement_score.weighted_score = engagement_score.raw_score * weights.engagement

        # Calculate compliance base score (default to 5 for neutral contribution)
        compliance_base = 5.0 * weights.compliance

        # Calculate weighted average
        weighted_sum = (
            relevance_score.weighted_score
            + recency_score.weighted_score
            + source_quality_score.weighted_score
            + engagement_score.weighted_score
            + compliance_base
        )

        # Apply compliance adjustment
        compliance_adjustment = self._compliance.adjust(item)
        final_score = self._compliance.apply_adjustment(weighted_sum, compliance_adjustment)

        # Ensure score is in valid range
        final_score = max(MIN_FINAL_SCORE, min(MAX_FINAL_SCORE, round(final_score, 2)))

        # Build component scores dictionary
        component_scores = {
            "relevance": relevance_score,
            "recency": recency_score,
            "source_quality": source_quality_score,
            "engagement": engagement_score,
        }

        # Build reasoning string
        reasoning = self._build_reasoning(
            final_score,
            weighted_sum,
            component_scores,
            compliance_adjustment,
        )

        logger.info(
            f"Scored item {item.get('id', 'unknown')}: {final_score} "
            f"(rel={relevance_score.raw_score}, rec={recency_score.raw_score}, "
            f"sq={source_quality_score.raw_score}, eng={engagement_score.raw_score}, "
            f"comp={compliance_adjustment.adjustment})"
        )

        return ScoringResult(
            final_score=final_score,
            component_scores=component_scores,
            reasoning=reasoning,
            scored_at=datetime.now(timezone.utc),
        )

    def _build_reasoning(
        self,
        final_score: float,
        weighted_sum: float,
        component_scores: dict[str, ComponentScore],
        compliance_adjustment: Any,
    ) -> str:
        """Build human-readable reasoning for the score.

        Args:
            final_score: The final calculated score.
            weighted_sum: The weighted sum before compliance adjustment.
            component_scores: Dictionary of component scores.
            compliance_adjustment: The compliance adjustment applied.

        Returns:
            Reasoning string explaining the score.
        """
        parts = [f"Final score: {final_score}/10"]

        # Add component breakdown
        parts.append("Components:")
        for name, score in component_scores.items():
            parts.append(f"  - {name}: {score.raw_score} ({score.notes})")

        # Add compliance note
        parts.append(f"Compliance: {compliance_adjustment.notes}")

        return "\n".join(parts)
