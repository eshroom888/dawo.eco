"""Norwegian keyword matcher for Mattilsynet content.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 7: Match text against Norwegian keyword tiers with character normalization.
"""

import logging

from teams.dawo.scanners.mattilsynet.config import MattilsynetMonitorConfig
from teams.dawo.scanners.mattilsynet.schemas import KeywordMatchResult

logger = logging.getLogger(__name__)


class NorwegianKeywordMatcher:
    """Matches text against Norwegian keyword tiers.

    Handles Norwegian special characters (ae/oe/aa) by matching
    against both original Unicode and ASCII-normalized forms.

    Severity mapping:
        - Tier 1 + enforcement -> CRITICAL
        - Tier 1 only -> HIGH
        - Tier 2 + enforcement -> HIGH
        - Tier 2 only -> MEDIUM
    """

    def __init__(self, config: MattilsynetMonitorConfig) -> None:
        """Initialize with keyword configuration.

        Args:
            config: Monitor config containing keyword lists
        """
        self._tier_1 = config.keywords_tier_1
        self._tier_2 = config.keywords_tier_2
        self._enforcement = config.enforcement_keywords

    def match(self, text: str) -> KeywordMatchResult:
        """Match text against all keyword tiers.

        Matches against BOTH original Norwegian characters and
        ASCII-normalized variants (case-insensitive).

        Args:
            text: Text to match keywords against

        Returns:
            KeywordMatchResult with match details
        """
        text_lower = text.lower()
        text_normalized = self.normalize_norwegian(text)

        matched_keywords: list[str] = []
        tier_1_match = False
        tier_2_match = False
        is_enforcement = False

        # Check tier 1 keywords
        for keyword in self._tier_1:
            if self._keyword_in_text(keyword, text_lower, text_normalized):
                matched_keywords.append(keyword)
                tier_1_match = True

        # Check tier 2 keywords
        for keyword in self._tier_2:
            if self._keyword_in_text(keyword, text_lower, text_normalized):
                matched_keywords.append(keyword)
                tier_2_match = True

        # Check enforcement keywords
        for keyword in self._enforcement:
            if self._keyword_in_text(keyword, text_lower, text_normalized):
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)
                is_enforcement = True

        if not matched_keywords:
            return KeywordMatchResult()

        relevance_tier = 1 if tier_1_match else 2
        is_relevant = tier_1_match or tier_2_match

        return KeywordMatchResult(
            is_relevant=is_relevant,
            relevance_tier=relevance_tier,
            matched_keywords=tuple(matched_keywords),
            is_enforcement=is_enforcement,
        )

    def _keyword_in_text(
        self, keyword: str, text_lower: str, text_normalized: str
    ) -> bool:
        """Check if keyword matches in either original or normalized text."""
        keyword_lower = keyword.lower()
        keyword_normalized = self.normalize_norwegian(keyword)
        return keyword_lower in text_lower or keyword_normalized in text_normalized

    @staticmethod
    def normalize_norwegian(text: str) -> str:
        """Normalize Norwegian special characters for ASCII-safe matching.

        Replaces ae (U+00E6), oe (U+00F8), aa (U+00E5) with
        their ASCII equivalents.

        Args:
            text: Text with potential Norwegian characters

        Returns:
            Lowercased text with Norwegian characters replaced
        """
        replacements = {
            "\u00e6": "ae",
            "\u00c6": "AE",
            "\u00f8": "oe",
            "\u00d8": "OE",
            "\u00e5": "aa",
            "\u00c5": "AA",
        }
        normalized = text
        for char, replacement in replacements.items():
            normalized = normalized.replace(char, replacement)
        return normalized.lower()


__all__ = [
    "NorwegianKeywordMatcher",
]
