"""Source quality scoring component for research items.

Scores items based on source tier and study type:
- PubMed: base 8 (peer-reviewed)
- News: base 6 (editorial process)
- YouTube: base 4 (creator content)
- Reddit: base 3 (user-generated)
- Instagram: base 3 (social media)

PubMed study type bonuses:
- RCT: +2 (total 10)
- Meta-analysis: +2 (total 10)
- Systematic review: +1 (total 9)
- Other: +0 (total 8)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..schemas import ComponentScore

logger = logging.getLogger(__name__)

# Source tier base scores
SOURCE_TIER_SCORES: dict[str, float] = {
    "pubmed": 8.0,
    "news": 6.0,
    "youtube": 4.0,
    "reddit": 3.0,
    "instagram": 3.0,
}

# PubMed study type bonuses
PUBMED_STUDY_BONUSES: dict[str, float] = {
    "RCT": 2.0,
    "meta-analysis": 2.0,
    "systematic_review": 1.0,
}

# Default score for unknown sources
DEFAULT_SOURCE_SCORE: float = 5.0

# Max score cap
MAX_SOURCE_QUALITY_SCORE: float = 10.0


@dataclass
class SourceQualityConfig:
    """Configuration for source quality scoring.

    Attributes:
        source_tiers: Base scores for each source type.
        study_bonuses: Bonus scores for PubMed study types.
    """

    source_tiers: dict[str, float] = field(default_factory=lambda: SOURCE_TIER_SCORES.copy())
    study_bonuses: dict[str, float] = field(default_factory=lambda: PUBMED_STUDY_BONUSES.copy())


class SourceQualityScorer:
    """Scores research items based on source quality.

    Higher scores for peer-reviewed sources, with bonuses for
    high-quality study types (RCT, meta-analysis).

    Attributes:
        _config: SourceQualityConfig with tier and bonus settings.
    """

    def __init__(self, config: SourceQualityConfig) -> None:
        """Initialize with configuration.

        Args:
            config: SourceQualityConfig with tier and bonus settings.
        """
        self._config = config

    def score(self, item: dict[str, Any]) -> ComponentScore:
        """Calculate source quality score for a research item.

        Args:
            item: Dictionary with 'source' and 'source_metadata' fields.

        Returns:
            ComponentScore with source quality score (0-10).
        """
        source = item.get("source", "").lower()
        source_metadata = item.get("source_metadata", {})

        # Get base score for source type
        base_score = self._config.source_tiers.get(source, DEFAULT_SOURCE_SCORE)

        # Apply PubMed study type bonus
        bonus = 0.0
        study_type = ""
        if source == "pubmed":
            study_type = source_metadata.get("study_type", "")
            bonus = self._config.study_bonuses.get(study_type, 0.0)

        # Calculate final score (capped at 10)
        raw_score = min(base_score + bonus, MAX_SOURCE_QUALITY_SCORE)

        # Build notes
        if source in self._config.source_tiers:
            notes = f"Source: {source} (tier score {base_score})"
            if bonus > 0:
                notes += f" + {study_type} bonus (+{bonus})"
        else:
            notes = f"Unknown source '{source}', using default score"

        logger.debug(f"Source quality score: {raw_score} for source={source}")

        return ComponentScore(
            component_name="source_quality",
            raw_score=raw_score,
            notes=notes,
        )
