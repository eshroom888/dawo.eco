"""Variance and correlation analysis for post-publish quality scoring.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 5: VarianceAnalyzer — flagged variances and outperformer analysis.
Task 6: Correlation analysis — Pearson correlation (pure Python).

Identifies patterns in scoring accuracy and recommends weight adjustments
for the pre-publish quality scorer.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from core.analytics.quality_scoring_repository import QualityScoringRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VarianceReport:
    """Enriched variance report for a flagged post.

    Task 5.4: Frozen dataclass with variance context.
    """

    post_id: str
    pre_score: Decimal
    post_score: Decimal
    variance: Decimal
    flagged_components: list[str]
    calculated_at: datetime


@dataclass(frozen=True)
class ComponentDeviation:
    """Component performance deviation from average.

    Task 5.6: Used in outperformer analysis.
    """

    component: str
    post_value: float
    avg_value: float
    deviation_pct: float


@dataclass(frozen=True)
class OutperformerAnalysis:
    """Analysis of a post that significantly outperformed its prediction.

    Task 5.5: Identifies what made a post successful.
    """

    post_id: str
    post_score: Decimal
    avg_score: Decimal
    strongest_components: list[ComponentDeviation]
    suggested_learnings: list[str]
    similar_post_ids: list[str]


@dataclass(frozen=True)
class CorrelationReport:
    """Correlation analysis between pre-publish and post-publish scores.

    Task 6.4: Generated when 50+ posts have both scores.
    """

    total_posts: int
    correlations: dict[str, float]
    recommended_weights: dict[str, float]
    generated_at: datetime


class VarianceAnalyzer:
    """Analyzes variance between predicted and actual post performance.

    Task 5.1 + Task 6.1: Variance analysis, outperformer identification,
    and correlation analysis with pure Python Pearson coefficient.
    """

    def __init__(self, repository: QualityScoringRepository) -> None:
        """Initialize with quality scoring repository.

        Args:
            repository: Data access for score records.
        """
        self._repository = repository

    async def get_flagged_variances(
        self, limit: int = 50
    ) -> list[VarianceReport]:
        """Get flagged records with enriched context.

        Task 5.2: Returns flagged records as VarianceReport objects.

        Args:
            limit: Maximum records to return.

        Returns:
            List of VarianceReport with component breakdown.
        """
        records = await self._repository.get_flagged_for_review(limit=limit)

        reports = []
        for record in records:
            # Identify which components contributed most to the variance
            flagged_components = self._identify_flagged_components(record)
            reports.append(
                VarianceReport(
                    post_id=record.post_id,
                    pre_score=record.pre_publish_score or Decimal("0"),
                    post_score=record.post_publish_score,
                    variance=record.variance,
                    flagged_components=flagged_components,
                    calculated_at=record.calculated_at,
                )
            )

        return reports

    async def analyze_outperformer(
        self, post_id: str
    ) -> Optional[OutperformerAnalysis]:
        """Analyze why a post outperformed its prediction.

        Task 5.3: Compares component scores against averages,
        identifies drivers and suggests learnings.

        Args:
            post_id: Post to analyze.

        Returns:
            OutperformerAnalysis, or None if post not found.
        """
        record = await self._repository.get_by_post_id(post_id)
        if record is None:
            return None

        avg_score = await self._repository.get_average_post_publish_score() or Decimal("5.0")
        component_averages = await self._repository.get_component_averages()

        # Calculate deviations for each component
        deviations: list[ComponentDeviation] = []
        for component_name, detail in record.component_scores.items():
            post_value = detail.get("weighted_score", 0.0)
            avg_value = component_averages.get(component_name, 0.0)

            if avg_value > 0:
                deviation_pct = ((post_value - avg_value) / avg_value) * 100.0
            else:
                deviation_pct = 0.0

            deviations.append(
                ComponentDeviation(
                    component=component_name,
                    post_value=post_value,
                    avg_value=avg_value,
                    deviation_pct=round(deviation_pct, 1),
                )
            )

        # Sort by deviation (highest positive deviation first)
        deviations.sort(key=lambda d: d.deviation_pct, reverse=True)

        # Generate learnings from top components
        learnings = self._generate_learnings(deviations)

        # Find similar posts with high scores in the same components
        all_records = await self._repository.get_all_scored(limit=100)
        similar_ids = self._find_similar_posts(record, deviations, all_records)

        return OutperformerAnalysis(
            post_id=post_id,
            post_score=record.post_publish_score,
            avg_score=avg_score,
            strongest_components=deviations,
            suggested_learnings=learnings,
            similar_post_ids=similar_ids,
        )

    async def run_correlation_analysis(self) -> Optional[CorrelationReport]:
        """Run correlation analysis between pre-publish and post-publish scores.

        Task 6.2: Only runs when 50+ posts have both scores.
        Uses pure Python Pearson correlation (no numpy/scipy).

        Returns:
            CorrelationReport with correlations and weight recommendations,
            or None if fewer than 50 scored posts.
        """
        count = await self._repository.get_scored_count()
        if count < 50:
            logger.debug("Only %d scored posts, need 50+ for correlation", count)
            return None

        records = await self._repository.get_all_scored(limit=500)
        if len(records) < 50:
            return None

        # Extract post-publish scores as target variable
        post_scores = [float(r.post_publish_score) for r in records]

        # For each component, compute correlation with actual performance
        component_names = set()
        for r in records:
            component_names.update(r.component_scores.keys())

        correlations: dict[str, float] = {}
        for component in component_names:
            values = []
            for r in records:
                detail = r.component_scores.get(component, {})
                values.append(detail.get("weighted_score", 0.0))

            if len(values) == len(post_scores):
                corr = self._pearson_correlation(values, post_scores)
                correlations[component] = round(corr, 3)

        # Generate weight recommendations
        recommended_weights = self._recommend_weights(correlations)

        return CorrelationReport(
            total_posts=len(records),
            correlations=correlations,
            recommended_weights=recommended_weights,
            generated_at=datetime.now(UTC),
        )

    @staticmethod
    def _pearson_correlation(x: list[float], y: list[float]) -> float:
        """Compute Pearson correlation coefficient (pure Python).

        Task 6.3: No numpy/scipy dependency.

        Args:
            x: First variable values.
            y: Second variable values.

        Returns:
            Correlation coefficient between -1.0 and 1.0.
            Returns 0.0 if standard deviation is zero.
        """
        n = len(x)
        if n == 0:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        std_x = (sum((xi - mean_x) ** 2 for xi in x)) ** 0.5
        std_y = (sum((yi - mean_y) ** 2 for yi in y)) ** 0.5

        if std_x * std_y == 0:
            return 0.0

        return cov / (std_x * std_y)

    def _identify_flagged_components(self, record) -> list[str]:
        """Identify which components diverged most from expected."""
        flagged = []
        for name, detail in record.component_scores.items():
            raw_score = detail.get("raw_score", 5.0)
            if raw_score <= 3.0 or raw_score >= 8.0:
                flagged.append(name)
        return flagged

    def _generate_learnings(
        self, deviations: list[ComponentDeviation]
    ) -> list[str]:
        """Generate suggested learnings from component deviations."""
        learnings = []
        for dev in deviations[:3]:
            if dev.deviation_pct > 20:
                learnings.append(
                    f"Strong performance in {dev.component}: "
                    f"{dev.deviation_pct:+.1f}% above average"
                )
            elif dev.deviation_pct < -20:
                learnings.append(
                    f"Underperformance in {dev.component}: "
                    f"{dev.deviation_pct:+.1f}% below average"
                )

        if not learnings:
            learnings.append("Performance close to average across all components")

        return learnings

    @staticmethod
    def _find_similar_posts(
        record, deviations: list[ComponentDeviation], all_records: list
    ) -> list[str]:
        """Find posts with similar high-scoring components."""
        if not deviations:
            return []

        top_component = deviations[0].component

        similar = []
        for r in all_records:
            if r.post_id == record.post_id:
                continue
            detail = r.component_scores.get(top_component, {})
            if detail.get("weighted_score", 0) >= deviations[0].post_value * 0.8:
                similar.append(r.post_id)

        return similar[:5]

    @staticmethod
    def _recommend_weights(
        correlations: dict[str, float]
    ) -> dict[str, float]:
        """Recommend weight adjustments based on correlations.

        High correlation (>0.5) → increase weight.
        Low/negative correlation → decrease weight (floor at 0.05).
        Anti-predictive (negative) components are logged as warnings.
        """
        if not correlations:
            return {}

        # Flag anti-predictive components, floor at 0.05 (not hidden)
        adjusted: dict[str, float] = {}
        for k, v in correlations.items():
            if v < 0:
                logger.warning(
                    "Component '%s' is anti-predictive (r=%.3f): "
                    "negatively correlated with post-publish performance",
                    k, v,
                )
                adjusted[k] = 0.05
            else:
                adjusted[k] = max(0.05, v)

        total = sum(adjusted.values())
        if total == 0:
            return {}

        return {
            k: round(v / total, 3)
            for k, v in adjusted.items()
        }


__all__ = [
    "ComponentDeviation",
    "CorrelationReport",
    "OutperformerAnalysis",
    "VarianceAnalyzer",
    "VarianceReport",
]
