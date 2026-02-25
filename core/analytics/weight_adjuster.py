"""Quality scoring weight adjuster based on correlation analysis.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 4: WeightAdjuster — proposes weight adjustments for operator review.

Analyzes correlation data from VarianceAnalyzer and proposes weight
changes when significant deviations (>5%) are detected. Weight changes
are PROPOSED only — never auto-applied (operator review required).
"""

import logging
from dataclasses import dataclass, field
from uuid import UUID

from core.analytics.quality_scoring_analyzer import CorrelationReport, VarianceAnalyzer
from core.analytics.feedback_loop_repository import FeedbackLoopRepository
from core.config import QualityScoringConfig

logger = logging.getLogger(__name__)

# Minimum delta to propose a change (5% threshold)
SIGNIFICANCE_THRESHOLD = 0.05


@dataclass(frozen=True)
class WeightAdjustmentProposal:
    """Frozen DTO for a proposed weight adjustment.

    Task 4.2: Contains current vs proposed weights, correlation data,
    and human-readable rationale.
    """

    current_weights: dict[str, float]
    proposed_weights: dict[str, float]
    correlations: dict[str, float]
    change_rationale: list[str]


class WeightAdjuster:
    """Proposes quality scoring weight adjustments based on correlation analysis.

    Task 4.1: Accepts VarianceAnalyzer, FeedbackLoopRepository,
    and QualityScoringConfig via constructor (DI pattern).
    """

    def __init__(
        self,
        variance_analyzer: VarianceAnalyzer,
        feedback_repo: FeedbackLoopRepository,
        config: QualityScoringConfig,
    ) -> None:
        self._variance_analyzer = variance_analyzer
        self._feedback_repo = feedback_repo
        self._config = config

    async def propose_weight_adjustment(self) -> WeightAdjustmentProposal | None:
        """Analyze correlations and propose weight changes if significant.

        Task 4.1: Runs correlation analysis, compares recommended weights
        against current config weights, returns proposal only when at
        least one weight delta exceeds SIGNIFICANCE_THRESHOLD (5%).

        Returns:
            WeightAdjustmentProposal if significant changes detected,
            None otherwise.
        """
        report: CorrelationReport | None = (
            await self._variance_analyzer.run_correlation_analysis()
        )
        if report is None:
            logger.debug("No correlation data available — skipping weight proposal")
            return None

        current = self._config.weights
        recommended = report.recommended_weights

        # Check if any weight delta exceeds the significance threshold
        has_significant_change = False
        for key in current:
            if key in recommended:
                delta = abs(current[key] - recommended[key])
                if delta > SIGNIFICANCE_THRESHOLD:
                    has_significant_change = True
                    break

        if not has_significant_change:
            logger.debug("No significant weight changes detected (all deltas < 5%%)")
            return None

        # Normalize proposed weights to sum to 1.0
        proposed = self._normalize_weights(recommended, current)

        # Build rationale
        rationale = self._build_rationale(current, proposed, report.correlations)

        return WeightAdjustmentProposal(
            current_weights=dict(current),
            proposed_weights=proposed,
            correlations=report.correlations,
            change_rationale=rationale,
        )

    async def apply_adjustment(self, record_id: UUID) -> None:
        """Mark a weight adjustment record as applied by operator.

        Task 4.1: Delegates to FeedbackLoopRepository.mark_adjustment_applied.
        Actual config reload is handled by the operator/system restart.

        Note: Returns None because the repo method mutates in-place and
        the caller already has the record reference. The operator triggers
        application via the record_id; no round-trip return needed.

        Args:
            record_id: UUID of the WeightAdjustmentRecord to mark applied.
        """
        await self._feedback_repo.mark_adjustment_applied(record_id)

    @staticmethod
    def _normalize_weights(
        recommended: dict[str, float],
        current: dict[str, float],
    ) -> dict[str, float]:
        """Normalize recommended weights to sum to 1.0.

        Uses recommended weights for keys present in both current and
        recommended; retains current weight for keys only in current.
        """
        merged: dict[str, float] = {}
        for key in current:
            merged[key] = recommended.get(key, current[key])

        total = sum(merged.values())
        if total == 0:
            return dict(current)

        return {k: round(v / total, 4) for k, v in merged.items()}

    @staticmethod
    def _build_rationale(
        current: dict[str, float],
        proposed: dict[str, float],
        correlations: dict[str, float],
    ) -> list[str]:
        """Build human-readable rationale for each significant change."""
        rationale: list[str] = []
        for key in current:
            if key not in proposed:
                continue
            delta = proposed[key] - current[key]
            if abs(delta) > SIGNIFICANCE_THRESHOLD:
                direction = "increase" if delta > 0 else "decrease"
                corr = correlations.get(key, 0.0)
                rationale.append(
                    f"{key}: {direction} from {current[key]:.2f} to "
                    f"{proposed[key]:.2f} (correlation: {corr:.3f})"
                )
        return rationale


__all__ = [
    "WeightAdjuster",
    "WeightAdjustmentProposal",
    "SIGNIFICANCE_THRESHOLD",
]
