"""Tests for ClaimPatternMatcher regex pre-filter.

Story 6-6, Task 5: Regex pattern matching for health claims.
"""

import pytest

from teams.dawo.scanners.claim_extraction.config import (
    HealthClaimExtractionConfig,
    ClaimPattern,
)
from teams.dawo.scanners.claim_extraction.pattern_matcher import ClaimPatternMatcher
from teams.dawo.scanners.claim_extraction.schemas import PatternMatch


@pytest.fixture
def config() -> HealthClaimExtractionConfig:
    """Config with English + Norwegian patterns."""
    return HealthClaimExtractionConfig(
        prohibited_patterns=(
            ClaimPattern(pattern="cures cancer", category="treatment", language="en"),
            ClaimPattern(pattern="treats depression", category="treatment", language="en"),
            ClaimPattern(pattern="behandler kreft", category="treatment", language="no"),
        ),
        borderline_patterns=(
            ClaimPattern(pattern="boosts immunity", category="enhancement", language="en"),
            ClaimPattern(pattern="styrker immunforsvaret", category="enhancement", language="no"),
            ClaimPattern(pattern="forbedrer", category="enhancement", language="no"),
        ),
        permitted_patterns=(
            ClaimPattern(pattern="wellbeing", category="general_wellness", language="en"),
        ),
        context_window_chars=20,
    )


@pytest.fixture
def matcher(config: HealthClaimExtractionConfig) -> ClaimPatternMatcher:
    return ClaimPatternMatcher(config)


class TestClaimPatternMatcher:
    """Tests for ClaimPatternMatcher."""

    def test_matches_english_prohibited(self, matcher: ClaimPatternMatcher) -> None:
        matches = matcher.find_matches("This product cures cancer naturally!")
        assert len(matches) == 1
        assert matches[0].matched_text == "cures cancer"
        assert matches[0].category == "treatment"

    def test_matches_norwegian_prohibited(self, matcher: ClaimPatternMatcher) -> None:
        matches = matcher.find_matches("Produktet behandler kreft effektivt.")
        assert len(matches) == 1
        assert matches[0].matched_text == "behandler kreft"
        assert matches[0].category == "treatment"

    def test_matches_english_borderline(self, matcher: ClaimPatternMatcher) -> None:
        matches = matcher.find_matches("Our extract boosts immunity and energy.")
        assert len(matches) == 1
        assert matches[0].matched_text == "boosts immunity"
        assert matches[0].category == "enhancement"

    def test_matches_norwegian_compound_with_suffix(self, matcher: ClaimPatternMatcher) -> None:
        matches = matcher.find_matches("Dette styrker immunforsvaret ditt.")
        assert len(matches) == 1
        assert matches[0].matched_text == "styrker immunforsvaret"
        assert matches[0].category == "enhancement"

    def test_no_match_for_neutral_content(self, matcher: ClaimPatternMatcher) -> None:
        matches = matcher.find_matches("Delicious mushroom recipes for dinner.")
        assert len(matches) == 0

    def test_case_insensitive_matching(self, matcher: ClaimPatternMatcher) -> None:
        matches = matcher.find_matches("This product CURES CANCER.")
        assert len(matches) == 1
        assert matches[0].category == "treatment"

    def test_norwegian_suffix_variations(self, matcher: ClaimPatternMatcher) -> None:
        # "forbedrer" should match, and "forbedret" (suffix) should also match
        matches_base = matcher.find_matches("Det forbedrer kognisjon.")
        assert len(matches_base) >= 1
        matches_suffix = matcher.find_matches("Forbedret søvnkvalitet.")
        assert len(matches_suffix) >= 1

    def test_multiple_matches_sorted_by_position(self, matcher: ClaimPatternMatcher) -> None:
        text = "This boosts immunity and also cures cancer."
        matches = matcher.find_matches(text)
        assert len(matches) == 2
        assert matches[0].start_pos < matches[1].start_pos

    def test_overlapping_matches_keeps_longer(self, matcher: ClaimPatternMatcher) -> None:
        # "styrker immunforsvaret" is longer than just "styrker"
        # Both could match the same region. Ensure no duplicate overlap.
        config = HealthClaimExtractionConfig(
            prohibited_patterns=(
                ClaimPattern(pattern="styrker", category="enhancement", language="no"),
            ),
            borderline_patterns=(
                ClaimPattern(pattern="styrker immunforsvaret", category="enhancement", language="no"),
            ),
            context_window_chars=20,
        )
        m = ClaimPatternMatcher(config)
        matches = m.find_matches("Det styrker immunforsvaret.")
        # Should keep only the longer match
        assert len(matches) == 1
        assert "immunforsvaret" in matches[0].matched_text

    def test_surrounding_context_extraction(self, matcher: ClaimPatternMatcher) -> None:
        text = "AAAAA cures cancer BBBBB"
        matches = matcher.find_matches(text)
        assert len(matches) == 1
        ctx = matches[0].surrounding_context
        # Context should include text around the match
        assert "AAAAA" in ctx or "BBBBB" in ctx

    def test_detect_language_norwegian(self, matcher: ClaimPatternMatcher) -> None:
        lang = matcher.detect_language("Dette produktet styrker immunforsvaret ditt.")
        assert lang == "no"

    def test_detect_language_english(self, matcher: ClaimPatternMatcher) -> None:
        lang = matcher.detect_language("This product boosts your immune system.")
        assert lang == "en"
