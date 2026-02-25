"""Regex pre-filter for health claim pattern matching.

Epic 6, Story 6-6, Task 5: ClaimPatternMatcher.

Scans text against compiled regex patterns from config to identify
potential health claims. Handles bilingual (English + Norwegian)
patterns with Norwegian compound word inflections.

Classes:
    ClaimPatternMatcher: Compiles and applies regex patterns.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from teams.dawo.scanners.claim_extraction.config import (
    ClaimPattern,
    HealthClaimExtractionConfig,
)
from teams.dawo.scanners.claim_extraction.schemas import PatternMatch

logger = logging.getLogger(__name__)

# Norwegian-specific characters and keywords for language detection
_NORWEGIAN_CHARS = {"ø", "æ", "å"}
_NORWEGIAN_KEYWORDS = {
    "det", "dette", "denne", "disse", "og", "er", "som", "med",
    "til", "av", "på", "kan", "har", "vil", "skal", "ikke",
    "ditt", "din", "vårt", "vår", "produktet", "naturlig",
}


@dataclass
class _CompiledPattern:
    """Internal: compiled regex with metadata."""
    regex: re.Pattern[str]
    raw_pattern: str
    category: str
    language: str


class ClaimPatternMatcher:
    """Regex pre-filter for health claim detection.

    Compiles all patterns from config at init time and scans text
    for matches. Handles Norwegian compound words with suffix variations.

    Args:
        config: Extraction configuration with pattern lists.
    """

    def __init__(self, config: HealthClaimExtractionConfig) -> None:
        self._config = config
        self._compiled: list[_CompiledPattern] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile all prohibited + borderline patterns into regex objects."""
        all_patterns = list(self._config.prohibited_patterns) + list(
            self._config.borderline_patterns
        )
        for cp in all_patterns:
            self._compiled.append(self._compile_single(cp))

    def _compile_single(self, cp: ClaimPattern) -> _CompiledPattern:
        """Compile one ClaimPattern into a regex.

        For Norwegian patterns, adds suffix variations to handle
        compound word inflections (en/et/er/ene/a/s).
        """
        escaped = re.escape(cp.pattern)

        if cp.language == "no":
            # Norwegian: handle compound word inflections
            # If pattern ends with common verb endings, create stem-based match
            # e.g., "forbedrer" → stem "forbedr" → match forbedr(er|et|ing|es|e)
            pattern_text = cp.pattern
            # Norwegian verbs: if pattern ends with "er", extract stem
            # e.g., "forbedrer" → stem "forbedr" → match forbedr(er|et|ing|es|e)
            if pattern_text.endswith("er") and len(pattern_text) > 4:
                stem_escaped = re.escape(pattern_text[:-2])
                regex_str = (
                    rf"{stem_escaped}(?:er|et|ing|es|e|ene|en|a|s)"
                )
            else:
                regex_str = rf"\b{escaped}(?:en|et|er|ene|a|s)?\b"
        else:
            # English: simple word boundary matching
            regex_str = rf"\b{escaped}\b"

        try:
            compiled = re.compile(regex_str, re.IGNORECASE)
        except re.error:
            logger.warning("Failed to compile pattern: %s", cp.pattern)
            compiled = re.compile(re.escape(cp.pattern), re.IGNORECASE)

        return _CompiledPattern(
            regex=compiled,
            raw_pattern=cp.pattern,
            category=cp.category,
            language=cp.language,
        )

    def find_matches(self, text: str) -> list[PatternMatch]:
        """Scan text against all compiled patterns.

        Args:
            text: Content text to scan.

        Returns:
            List of PatternMatch sorted by position.
        """
        raw_matches: list[PatternMatch] = []

        for cp in self._compiled:
            for m in cp.regex.finditer(text):
                ctx = self._extract_context(
                    text, m.start(), m.end(), self._config.context_window_chars
                )
                raw_matches.append(
                    PatternMatch(
                        matched_text=m.group(),
                        pattern=cp.raw_pattern,
                        category=cp.category,
                        language=cp.language,
                        start_pos=m.start(),
                        end_pos=m.end(),
                        surrounding_context=ctx,
                    )
                )

        # Sort by position
        raw_matches.sort(key=lambda pm: pm.start_pos)

        # Deduplicate overlapping matches: keep longer/higher specificity
        return self._deduplicate_overlapping(raw_matches)

    def _extract_context(
        self, text: str, start: int, end: int, window: int
    ) -> str:
        """Extract surrounding context around a match."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        return text[ctx_start:ctx_end]

    def _deduplicate_overlapping(
        self, matches: list[PatternMatch]
    ) -> list[PatternMatch]:
        """Remove overlapping matches, keeping longer/more specific ones."""
        if not matches:
            return matches

        result: list[PatternMatch] = []
        for m in matches:
            overlap_idx = None
            for i, existing in enumerate(result):
                if self._overlaps(existing, m):
                    overlap_idx = i
                    break

            if overlap_idx is not None:
                existing = result[overlap_idx]
                # Keep the longer match
                if len(m.matched_text) > len(existing.matched_text):
                    result[overlap_idx] = m
            else:
                result.append(m)

        return result

    @staticmethod
    def _overlaps(a: PatternMatch, b: PatternMatch) -> bool:
        """Check if two matches have overlapping text regions."""
        return a.start_pos < b.end_pos and b.start_pos < a.end_pos

    def detect_language(self, text: str) -> str:
        """Detect language with simple heuristic.

        Args:
            text: Text to analyze.

        Returns:
            "no" for Norwegian, "en" for English.
        """
        text_lower = text.lower()

        # Check for Norwegian-specific characters
        for char in _NORWEGIAN_CHARS:
            if char in text_lower:
                return "no"

        # Check for Norwegian keywords
        words = set(re.findall(r"\b\w+\b", text_lower))
        norwegian_word_count = len(words & _NORWEGIAN_KEYWORDS)
        if norwegian_word_count >= 2:
            return "no"

        return "en"


__all__ = [
    "ClaimPatternMatcher",
]
