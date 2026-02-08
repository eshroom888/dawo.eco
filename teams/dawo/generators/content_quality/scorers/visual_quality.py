"""Visual Quality Scorer - Visual quality scoring.

Scores content based on provided image quality score.
Clamps input to valid 0-10 range.
"""

from dataclasses import dataclass
from typing import Optional

from teams.dawo.generators.content_quality.schemas import ComponentScore


@dataclass
class VisualQualityScorerConfig:
    """Configuration for visual quality scoring.

    Attributes:
        weight: Weight of visual quality in total score (default 0.15)
    """

    weight: float = 0.15


class VisualQualityScorer:
    """Scores visual quality from input score.

    Uses the visual_quality_score provided in the request
    (from image generator output). Clamps to valid 0-10 range.

    Attributes:
        config: Scorer configuration
    """

    def __init__(
        self,
        config: Optional[VisualQualityScorerConfig] = None,
    ) -> None:
        """Initialize with optional configuration.

        Args:
            config: Optional scorer configuration
        """
        self._config = config or VisualQualityScorerConfig()

    def score(
        self,
        visual_quality_score: float,
    ) -> ComponentScore:
        """Score visual quality from input.

        Args:
            visual_quality_score: Quality score from image generator (0-10)

        Returns:
            ComponentScore with visual quality details
        """
        # Clamp to valid range
        raw_score = max(0.0, min(10.0, visual_quality_score))

        return ComponentScore(
            component="visual_quality",
            raw_score=raw_score,
            weight=self._config.weight,
            weighted_score=raw_score * self._config.weight,
            details={
                "input_score": visual_quality_score,
            },
        )
