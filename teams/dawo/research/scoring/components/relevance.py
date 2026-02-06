"""Relevance scoring component for research items.

Calculates relevance score based on keyword matching:
- Primary keywords (mushroom products): +2 each, max +6
- Secondary keywords (wellness themes): +1 each, max +4
- Total max score: 10

Keywords are matched case-insensitively in both title and content.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..schemas import ComponentScore

logger = logging.getLogger(__name__)

# Scoring constants
PRIMARY_KEYWORD_BONUS: float = 2.0
SECONDARY_KEYWORD_BONUS: float = 1.0
MAX_PRIMARY_BONUS: float = 6.0
MAX_SECONDARY_BONUS: float = 4.0
MAX_SCORE: float = 10.0

# Default DAWO product keywords (mushroom types with variants)
DEFAULT_PRIMARY_KEYWORDS: list[str] = [
    # Lion's Mane variants
    "lion's mane",
    "lions mane",
    "hericium erinaceus",
    # Chaga
    "chaga",
    "inonotus obliquus",
    # Reishi
    "reishi",
    "ganoderma lucidum",
    # Cordyceps
    "cordyceps",
    "cordyceps sinensis",
    "cordyceps militaris",
    # Shiitake
    "shiitake",
    "lentinula edodes",
    # Maitake
    "maitake",
    "grifola frondosa",
]

# Default wellness theme keywords
DEFAULT_SECONDARY_KEYWORDS: list[str] = [
    # Cognition
    "cognition",
    "cognitive",
    "brain",
    "memory",
    "focus",
    "mental clarity",
    # Immunity
    "immunity",
    "immune",
    "immune system",
    # Energy
    "energy",
    "stamina",
    "vitality",
    "fatigue",
    # Stress
    "stress",
    "adaptogen",
    "adaptogenic",
    "cortisol",
    # Sleep
    "sleep",
    "insomnia",
    "rest",
]


@dataclass
class RelevanceConfig:
    """Configuration for relevance scoring.

    Attributes:
        primary_keywords: List of primary keywords (mushroom products).
        secondary_keywords: List of secondary keywords (wellness themes).
    """

    primary_keywords: list[str] = field(default_factory=lambda: DEFAULT_PRIMARY_KEYWORDS.copy())
    secondary_keywords: list[str] = field(default_factory=lambda: DEFAULT_SECONDARY_KEYWORDS.copy())


class RelevanceScorer:
    """Scores research items based on relevance to DAWO products.

    Calculates relevance by matching keywords in title and content:
    - Primary keywords (mushroom products): +2 each, max +6
    - Secondary keywords (wellness themes): +1 each, max +4

    Attributes:
        _config: RelevanceConfig with keyword lists.
    """

    def __init__(self, config: RelevanceConfig) -> None:
        """Initialize with configuration.

        Args:
            config: RelevanceConfig with keyword lists.
        """
        self._config = config
        # Pre-lowercase keywords for efficient matching
        self._primary_keywords_lower = [kw.lower() for kw in config.primary_keywords]
        self._secondary_keywords_lower = [kw.lower() for kw in config.secondary_keywords]

    def score(self, item: dict[str, Any]) -> ComponentScore:
        """Calculate relevance score for a research item.

        Args:
            item: Dictionary with 'title' and 'content' fields.

        Returns:
            ComponentScore with relevance score (0-10).
        """
        title = item.get("title", "")
        content = item.get("content", "")
        text = f"{title} {content}".lower()

        # Count unique primary keyword matches
        primary_matches = self._count_unique_matches(text, self._primary_keywords_lower)
        primary_bonus = min(primary_matches * PRIMARY_KEYWORD_BONUS, MAX_PRIMARY_BONUS)

        # Count unique secondary keyword matches
        secondary_matches = self._count_unique_matches(text, self._secondary_keywords_lower)
        secondary_bonus = min(secondary_matches * SECONDARY_KEYWORD_BONUS, MAX_SECONDARY_BONUS)

        # Calculate total score (capped at 10)
        raw_score = min(primary_bonus + secondary_bonus, MAX_SCORE)

        # Build notes with matched keywords
        matched_primary = self._find_matched_keywords(text, self._primary_keywords_lower)
        matched_secondary = self._find_matched_keywords(text, self._secondary_keywords_lower)

        notes_parts = []
        if matched_primary:
            notes_parts.append(f"Primary: {', '.join(matched_primary[:3])}")
        if matched_secondary:
            notes_parts.append(f"Secondary: {', '.join(matched_secondary[:3])}")

        notes = "; ".join(notes_parts) if notes_parts else "No relevant keywords found"

        logger.debug(
            f"Relevance score: {raw_score} (primary: {primary_matches}, secondary: {secondary_matches})"
        )

        return ComponentScore(
            component_name="relevance",
            raw_score=raw_score,
            notes=notes,
        )

    def _count_unique_matches(self, text: str, keywords: list[str]) -> int:
        """Count unique keyword matches in text.

        Groups similar keywords (e.g., "lion's mane" and "lions mane") to avoid
        double-counting the same concept.

        Args:
            text: Lowercase text to search.
            keywords: List of lowercase keywords.

        Returns:
            Number of unique keyword matches.
        """
        # Group keywords by base concept to avoid double-counting
        matched_concepts: set[str] = set()

        for keyword in keywords:
            if keyword in text:
                # Use first word as concept identifier (simplified grouping)
                concept = keyword.split()[0]
                matched_concepts.add(concept)

        return len(matched_concepts)

    def _find_matched_keywords(self, text: str, keywords: list[str]) -> list[str]:
        """Find which keywords matched in text.

        Args:
            text: Lowercase text to search.
            keywords: List of lowercase keywords.

        Returns:
            List of matched keywords (deduplicated by concept).
        """
        matched: list[str] = []
        seen_concepts: set[str] = set()

        for keyword in keywords:
            if keyword in text:
                concept = keyword.split()[0]
                if concept not in seen_concepts:
                    matched.append(keyword)
                    seen_concepts.add(concept)

        return matched
