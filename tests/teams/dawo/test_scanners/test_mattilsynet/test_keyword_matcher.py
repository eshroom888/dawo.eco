"""Tests for Norwegian keyword matcher.

Epic 6, Story 6-3: Tasks 13.10-13.15.
"""

import pytest

from teams.dawo.scanners.mattilsynet.config import (
    FeedConfig,
    MattilsynetMonitorConfig,
)
from teams.dawo.scanners.mattilsynet.keyword_matcher import NorwegianKeywordMatcher


@pytest.fixture
def matcher(keyword_config: MattilsynetMonitorConfig) -> NorwegianKeywordMatcher:
    return NorwegianKeywordMatcher(keyword_config)


class TestMatchTier1:
    """Test Tier 1 keyword matching."""

    def test_matches_tier_1_keyword(self, matcher: NorwegianKeywordMatcher) -> None:
        result = matcher.match("Nye regler for kosttilskudd fra Mattilsynet")
        assert result.is_relevant is True
        assert result.relevance_tier == 1
        assert "kosttilskudd" in result.matched_keywords

    def test_tier_1_severity_high(self, matcher: NorwegianKeywordMatcher) -> None:
        result = matcher.match("Nye regler for kosttilskudd")
        assert result.is_relevant is True
        assert result.relevance_tier == 1


class TestMatchTier2:
    """Test Tier 2 keyword matching."""

    def test_matches_tier_2_keyword(self, matcher: NorwegianKeywordMatcher) -> None:
        result = matcher.match("Soppekstrakt og funksjonssopp i Norge")
        assert result.is_relevant is True
        assert result.relevance_tier == 2
        assert "funksjonssopp" in result.matched_keywords

    def test_tier_2_only_sets_tier_2(self, matcher: NorwegianKeywordMatcher) -> None:
        result = matcher.match("Nye produkter med adaptogener")
        assert result.relevance_tier == 2


class TestMatchEnforcement:
    """Test enforcement keyword matching."""

    def test_matches_enforcement_keyword(self, matcher: NorwegianKeywordMatcher) -> None:
        result = matcher.match("Tilbakekalling av kosttilskudd")
        assert result.is_enforcement is True
        assert "tilbakekalling" in result.matched_keywords

    def test_enforcement_with_tier_1(self, matcher: NorwegianKeywordMatcher) -> None:
        # tilbakekalling is both tier_1 and enforcement keyword
        result = matcher.match("Tilbakekalling av kosttilskudd")
        assert result.is_enforcement is True
        assert result.relevance_tier == 1


class TestNorwegianNormalization:
    """Test Norwegian character normalization."""

    def test_normalizes_ae(self, matcher: NorwegianKeywordMatcher) -> None:
        # Text uses ASCII 'ae' but keyword uses Unicode ae
        result = NorwegianKeywordMatcher.normalize_norwegian("naeringsstoffer")
        assert "ae" in result

    def test_normalizes_oe(self, matcher: NorwegianKeywordMatcher) -> None:
        result = NorwegianKeywordMatcher.normalize_norwegian("kosttilsk\u00f8dd")
        assert "oe" in result

    def test_normalizes_aa(self, matcher: NorwegianKeywordMatcher) -> None:
        result = NorwegianKeywordMatcher.normalize_norwegian("helsep\u00e5stander")
        assert "aastander" in result

    def test_matches_unicode_text_with_unicode_keyword(self, matcher: NorwegianKeywordMatcher) -> None:
        # Both text and keyword use Unicode aa (U+00E5)
        result = matcher.match("Nye regler for helsep\u00e5stander i EU")
        assert result.is_relevant is True
        assert "helsep\u00e5stander" in result.matched_keywords

    def test_matches_ascii_text_with_unicode_keyword(self, matcher: NorwegianKeywordMatcher) -> None:
        # Text uses ASCII 'aa', keyword uses Unicode aa
        result = matcher.match("Nye regler for helsepaastander i EU")
        assert result.is_relevant is True

    def test_handles_all_norwegian_chars(self, matcher: NorwegianKeywordMatcher) -> None:
        text = "\u00c6\u00d8\u00c5 \u00e6\u00f8\u00e5"
        normalized = NorwegianKeywordMatcher.normalize_norwegian(text)
        assert "ae" in normalized
        assert "oe" in normalized
        assert "aa" in normalized
        assert "\u00e6" not in normalized
        assert "\u00f8" not in normalized
        assert "\u00e5" not in normalized


class TestNoMatch:
    """Test non-relevant text."""

    def test_returns_not_relevant_for_unrelated_text(self, matcher: NorwegianKeywordMatcher) -> None:
        result = matcher.match("Weather forecast for Oslo tomorrow")
        assert result.is_relevant is False
        assert result.relevance_tier == 0
        assert result.matched_keywords == ()
        assert result.is_enforcement is False

    def test_returns_not_relevant_for_empty_text(self, matcher: NorwegianKeywordMatcher) -> None:
        result = matcher.match("")
        assert result.is_relevant is False
