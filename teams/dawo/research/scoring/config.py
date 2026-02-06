"""Scoring configuration schema for research item scoring engine.

Defines the weight configuration for composite scoring, including:
- Default weights for each scoring component
- Per-source weight overrides
- Validation to ensure weights are valid

Configuration follows the injection pattern - instances are created
by the Team Builder and injected into the scorer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Default weight constants (must sum to 1.0)
# As specified in story requirements:
# relevance(25%), recency(20%), source_quality(25%), engagement(20%), compliance(10%)
DEFAULT_RELEVANCE_WEIGHT: float = 0.25
DEFAULT_RECENCY_WEIGHT: float = 0.20
DEFAULT_SOURCE_QUALITY_WEIGHT: float = 0.25
DEFAULT_ENGAGEMENT_WEIGHT: float = 0.20
DEFAULT_COMPLIANCE_WEIGHT: float = 0.10


def _validate_weight(value: float, name: str) -> None:
    """Validate a single weight value.

    Args:
        value: The weight value to validate.
        name: The name of the weight (for error messages).

    Raises:
        ValueError: If weight is negative or exceeds 1.0.
    """
    if value < 0:
        raise ValueError(f"Weight '{name}' must be non-negative, got {value}")
    if value > 1.0:
        raise ValueError(f"Weight '{name}' cannot exceed 1.0, got {value}")


@dataclass(frozen=True)
class ScoringWeights:
    """Weight values for each scoring component.

    All weights should sum to 1.0 for proper normalization.
    Each weight represents the relative importance of that component
    in the final composite score.

    Attributes:
        relevance: Weight for relevance scoring (default 25%)
        recency: Weight for recency scoring (default 20%)
        source_quality: Weight for source quality scoring (default 25%)
        engagement: Weight for engagement scoring (default 20%)
        compliance: Weight for compliance base scoring (default 10%)
    """

    relevance: float = DEFAULT_RELEVANCE_WEIGHT
    recency: float = DEFAULT_RECENCY_WEIGHT
    source_quality: float = DEFAULT_SOURCE_QUALITY_WEIGHT
    engagement: float = DEFAULT_ENGAGEMENT_WEIGHT
    compliance: float = DEFAULT_COMPLIANCE_WEIGHT

    def __post_init__(self) -> None:
        """Validate weight values after initialization."""
        _validate_weight(self.relevance, "relevance")
        _validate_weight(self.recency, "recency")
        _validate_weight(self.source_quality, "source_quality")
        _validate_weight(self.engagement, "engagement")
        _validate_weight(self.compliance, "compliance")

        total = (
            self.relevance
            + self.recency
            + self.source_quality
            + self.engagement
            + self.compliance
        )
        if abs(total - 1.0) > 0.001:
            logger.warning(
                f"Scoring weights sum to {total:.3f}, not 1.0. "
                "This may affect score normalization."
            )


@dataclass
class ScoringConfig:
    """Configuration for the research item scoring engine.

    Provides default weights and allows per-source overrides.
    Created by Team Builder and injected into ResearchItemScorer.

    Attributes:
        weights: Default weights for all scoring components.
        source_overrides: Per-source weight overrides (e.g., higher engagement
            weight for Reddit, higher source_quality for PubMed).

    Example:
        config = ScoringConfig(
            source_overrides={
                "reddit": ScoringWeights(engagement=0.35, ...),
                "pubmed": ScoringWeights(source_quality=0.35, ...),
            }
        )
    """

    weights: ScoringWeights = field(default_factory=ScoringWeights)
    source_overrides: dict[str, ScoringWeights] = field(default_factory=dict)

    def get_weights_for_source(self, source: str) -> ScoringWeights:
        """Get the appropriate weights for a given source.

        Args:
            source: The research source (e.g., "reddit", "pubmed").

        Returns:
            ScoringWeights for the source (override if available, else default).
        """
        source_lower = source.lower()
        if source_lower in self.source_overrides:
            return self.source_overrides[source_lower]
        return self.weights

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoringConfig:
        """Create ScoringConfig from a dictionary.

        Args:
            data: Dictionary with 'weights' and optional 'source_overrides'.

        Returns:
            ScoringConfig instance.

        Example:
            config = ScoringConfig.from_dict({
                "weights": {"relevance": 0.25, ...},
                "source_overrides": {"reddit": {"engagement": 0.35, ...}}
            })
        """
        weights_data = data.get("weights", {})
        weights = ScoringWeights(**weights_data) if weights_data else ScoringWeights()

        source_overrides: dict[str, ScoringWeights] = {}
        overrides_data = data.get("source_overrides", {})
        for source, override_weights in overrides_data.items():
            source_overrides[source.lower()] = ScoringWeights(**override_weights)

        return cls(weights=weights, source_overrides=source_overrides)
