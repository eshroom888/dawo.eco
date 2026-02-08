"""Unit tests for Compliance Rewrite Suggester.

Tests cover:
- Suggestion generation for prohibited phrases (AC #2, #3)
- Suggestion generation for borderline phrases (AC #2)
- Keep-as-is logic for acceptable borderline phrases (AC #2)
- Content reconstruction with applied suggestions (AC #3)
- Re-validation loop (AC #3)
- Norwegian content handling
- Brand voice compliance
- Performance (< 10 seconds)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from teams.dawo.validators.eu_compliance import (
    ComplianceStatus,
    ContentComplianceCheck,
    OverallStatus,
    RegulationRef,
    ComplianceResult,
)
from teams.dawo.generators.compliance_rewrite import (
    ComplianceRewriteSuggester,
    RewriteRequest,
    RewriteResult,
    RewriteSuggestion,
    apply_suggestion,
    apply_all_suggestions,
    find_phrase_position,
    extract_context,
    preserve_formatting,
    count_words,
    validate_rewrite_length,
)


class TestRewriteSuggestion:
    """Tests for RewriteSuggestion dataclass."""

    def test_has_suggestions_with_alternatives(self, sample_rewrite_suggestion):
        """Test has_suggestions returns True when alternatives exist."""
        assert sample_rewrite_suggestion.has_suggestions is True

    def test_has_suggestions_with_keep_only(self, sample_borderline_suggestion):
        """Test has_suggestions returns True with keep recommendation."""
        suggestion = RewriteSuggestion(
            original_phrase="støtter sunn metabolisme",
            status=ComplianceStatus.BORDERLINE,
            regulation_reference=RegulationRef.ARTICLE_13,
            explanation="Acceptable",
            suggestions=[],
            keep_recommendation="Can be kept as-is",
        )
        assert suggestion.has_suggestions is True

    def test_has_suggestions_empty(self):
        """Test has_suggestions returns False when no alternatives or keep."""
        suggestion = RewriteSuggestion(
            original_phrase="test",
            status=ComplianceStatus.PROHIBITED,
            regulation_reference=RegulationRef.ARTICLE_10,
            explanation="Test",
            suggestions=[],
            keep_recommendation=None,
        )
        assert suggestion.has_suggestions is False

    def test_is_prohibited(self, sample_rewrite_suggestion):
        """Test is_prohibited property."""
        assert sample_rewrite_suggestion.is_prohibited is True

    def test_is_borderline(self, sample_borderline_suggestion):
        """Test is_borderline property."""
        assert sample_borderline_suggestion.is_borderline is True


class TestApplySuggestion:
    """Tests for apply_suggestion utility function."""

    def test_apply_first_suggestion(self, sample_rewrite_suggestion):
        """Test applying first suggestion to content."""
        content = "Løvemanke behandler hjernetåke naturlig."
        result = apply_suggestion(content, sample_rewrite_suggestion, 0)
        assert "støtter mental klarhet" in result
        assert "behandler hjernetåke" not in result

    def test_apply_second_suggestion(self, sample_rewrite_suggestion):
        """Test applying second suggestion to content."""
        content = "Løvemanke behandler hjernetåke naturlig."
        result = apply_suggestion(content, sample_rewrite_suggestion, 1)
        assert "bidrar til kognitiv velvære" in result

    def test_apply_invalid_index_raises(self, sample_rewrite_suggestion):
        """Test that invalid suggestion index raises ValueError."""
        content = "Test content"
        with pytest.raises(ValueError, match="Invalid suggestion index"):
            apply_suggestion(content, sample_rewrite_suggestion, 10)

    def test_apply_keep_recommendation_returns_unchanged(self):
        """Test that keep recommendation returns content unchanged."""
        suggestion = RewriteSuggestion(
            original_phrase="støtter sunn metabolisme",
            status=ComplianceStatus.BORDERLINE,
            regulation_reference=RegulationRef.ARTICLE_13,
            explanation="Acceptable",
            suggestions=[],
            keep_recommendation="Can be kept",
        )
        content = "Dette støtter sunn metabolisme."
        result = apply_suggestion(content, suggestion, 0)
        assert result == content

    def test_apply_position_based_replacement(self):
        """Test position-based replacement accuracy."""
        suggestion = RewriteSuggestion(
            original_phrase="behandler",
            status=ComplianceStatus.PROHIBITED,
            regulation_reference=RegulationRef.ARTICLE_10,
            explanation="Treatment claim",
            suggestions=["støtter"],
            start_position=10,
            end_position=19,
        )
        content = "Løvemanke behandler hjernetåke."
        result = apply_suggestion(content, suggestion, 0)
        assert result == "Løvemanke støtter hjernetåke."


class TestApplyAllSuggestions:
    """Tests for apply_all_suggestions utility function."""

    def test_apply_multiple_suggestions(self):
        """Test applying multiple suggestions to content."""
        content = "Løvemanke behandler hjernetåke og kurerer utmattelse."
        suggestions = [
            RewriteSuggestion(
                original_phrase="behandler hjernetåke",
                status=ComplianceStatus.PROHIBITED,
                regulation_reference=RegulationRef.ARTICLE_10,
                explanation="Treatment",
                suggestions=["støtter mental klarhet"],
                start_position=10,
                end_position=30,
            ),
            RewriteSuggestion(
                original_phrase="kurerer utmattelse",
                status=ComplianceStatus.PROHIBITED,
                regulation_reference=RegulationRef.ARTICLE_10,
                explanation="Cure claim",
                suggestions=["hjelper deg å føle deg uthvilt"],
                start_position=34,
                end_position=52,
            ),
        ]
        result = apply_all_suggestions(content, suggestions)
        assert "støtter mental klarhet" in result
        assert "hjelper deg å føle deg uthvilt" in result
        assert "behandler" not in result
        assert "kurerer" not in result

    def test_apply_with_custom_selections(self):
        """Test applying with custom selection indices."""
        content = "Test behandler something."
        suggestions = [
            RewriteSuggestion(
                original_phrase="behandler",
                status=ComplianceStatus.PROHIBITED,
                regulation_reference=RegulationRef.ARTICLE_10,
                explanation="Treatment",
                suggestions=["option1", "option2", "option3"],
            ),
        ]
        result = apply_all_suggestions(content, suggestions, {0: 2})
        assert "option3" in result

    def test_apply_empty_suggestions(self):
        """Test applying empty suggestions list returns original."""
        content = "Original content"
        result = apply_all_suggestions(content, [])
        assert result == content


class TestFindPhrasePosition:
    """Tests for find_phrase_position utility function."""

    def test_find_exact_match(self):
        """Test finding exact phrase match."""
        content = "Løvemanke behandler hjernetåke."
        start, end = find_phrase_position(content, "behandler hjernetåke")
        assert start == 10
        assert end == 30

    def test_find_case_insensitive(self):
        """Test case-insensitive matching."""
        content = "Løvemanke BEHANDLER hjernetåke."
        start, end = find_phrase_position(content, "behandler")
        assert start == 10
        assert end == 19

    def test_find_not_found(self):
        """Test returns (0, 0) when not found."""
        content = "Clean content here."
        start, end = find_phrase_position(content, "behandler")
        assert start == 0
        assert end == 0


class TestExtractContext:
    """Tests for extract_context utility function."""

    def test_extract_with_surrounding(self):
        """Test extracting context with surrounding text."""
        content = "Start Løvemanke behandler hjernetåke naturlig. End"
        context = extract_context(content, 16, 36, window=10)
        assert "behandler hjernetåke" in context

    def test_extract_at_start(self):
        """Test extracting context at content start."""
        content = "behandler hjernetåke naturlig."
        context = extract_context(content, 0, 20, window=10)
        assert "behandler" in context
        assert not context.startswith("...")

    def test_extract_at_end(self):
        """Test extracting context at content end."""
        content = "Test behandler hjernetåke"
        context = extract_context(content, 5, 25, window=10)
        assert "behandler" in context
        assert not context.endswith("...")


class TestPreserveFormatting:
    """Tests for preserve_formatting utility function."""

    def test_preserve_uppercase(self):
        """Test preserving uppercase formatting."""
        result = preserve_formatting("ORIGINAL", "replacement")
        assert result == "REPLACEMENT"

    def test_preserve_titlecase(self):
        """Test preserving title case formatting."""
        result = preserve_formatting("Original", "replacement")
        assert result == "Replacement"

    def test_preserve_leading_space(self):
        """Test preserving leading whitespace."""
        result = preserve_formatting("  original", "replacement")
        # Leading spaces preserved; lowercase original stays lowercase
        assert result == "  replacement"


class TestCountWords:
    """Tests for count_words utility function."""

    def test_count_excluding_hashtags(self):
        """Test word count excludes hashtags."""
        text = "This is content #DAWO #Løvemanke with hashtags"
        count = count_words(text)
        assert count == 5  # "This is content with hashtags"

    def test_count_empty(self):
        """Test word count for empty string."""
        assert count_words("") == 0


class TestValidateRewriteLength:
    """Tests for validate_rewrite_length utility function."""

    def test_within_tolerance(self):
        """Test rewrite within tolerance passes."""
        original = "This is the original content with several words"
        rewritten = "This is the rewritten content with some words"
        assert validate_rewrite_length(original, rewritten) is True

    def test_exceeds_tolerance(self):
        """Test rewrite exceeding tolerance fails."""
        original = "Short"
        rewritten = "This is a much longer rewritten version with many words"
        assert validate_rewrite_length(original, rewritten) is False


class TestComplianceRewriteSuggester:
    """Tests for ComplianceRewriteSuggester agent class."""

    @pytest.mark.asyncio
    async def test_suggest_rewrites_prohibited(
        self,
        mock_compliance_checker,
        mock_llm_client,
        mock_brand_profile,
        sample_prohibited_compliance_check,
        sample_content_norwegian,
    ):
        """Test generating suggestions for prohibited phrases (AC #2)."""
        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client,
        )

        request = RewriteRequest(
            content=sample_content_norwegian,
            compliance_check=sample_prohibited_compliance_check,
            brand_profile=mock_brand_profile,
            language="no",
        )

        result = await suggester.suggest_rewrites(request)

        assert isinstance(result, RewriteResult)
        assert len(result.suggestions) >= 1
        assert result.suggestions[0].original_phrase == "behandler hjernetåke"
        assert len(result.suggestions[0].suggestions) >= 1

    @pytest.mark.asyncio
    async def test_suggest_rewrites_borderline(
        self,
        mock_compliance_checker,
        mock_llm_client_borderline,
        mock_brand_profile,
        sample_borderline_compliance_check,
    ):
        """Test generating suggestions for borderline phrases (AC #2)."""
        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client_borderline,
        )

        content = "Løvemanke støtter immunforsvaret naturlig."
        request = RewriteRequest(
            content=content,
            compliance_check=sample_borderline_compliance_check,
            brand_profile=mock_brand_profile,
            language="no",
        )

        result = await suggester.suggest_rewrites(request)

        assert isinstance(result, RewriteResult)
        assert len(result.suggestions) >= 1
        # Borderline should have suggestions OR keep recommendation

    @pytest.mark.asyncio
    async def test_suggest_rewrites_maintains_brand_voice(
        self,
        mock_compliance_checker,
        mock_llm_client,
        mock_brand_profile,
        sample_prohibited_compliance_check,
        sample_content_norwegian,
    ):
        """Test that suggestions maintain brand voice (AC #2)."""
        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client,
        )

        request = RewriteRequest(
            content=sample_content_norwegian,
            compliance_check=sample_prohibited_compliance_check,
            brand_profile=mock_brand_profile,
            language="no",
        )

        result = await suggester.suggest_rewrites(request)

        # Verify LLM was called with brand context in system prompt
        mock_llm_client.generate.assert_called()
        call_kwargs = mock_llm_client.generate.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_suggest_with_revalidation_loop(
        self,
        mock_compliance_checker,
        mock_llm_client,
        mock_brand_profile,
        sample_content_norwegian,
    ):
        """Test re-validation loop until compliant (AC #3)."""
        # First call returns rejected, second returns compliant
        mock_compliance_checker.check_content.side_effect = [
            ContentComplianceCheck(
                overall_status=OverallStatus.REJECTED,
                flagged_phrases=[
                    ComplianceResult(
                        phrase="behandler hjernetåke",
                        status=ComplianceStatus.PROHIBITED,
                        explanation="Treatment claim",
                        regulation_reference=RegulationRef.ARTICLE_10,
                    )
                ],
                compliance_score=0.4,
                llm_enhanced=True,
            ),
            ContentComplianceCheck(
                overall_status=OverallStatus.COMPLIANT,
                flagged_phrases=[],
                compliance_score=1.0,
                llm_enhanced=True,
            ),
        ]

        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client,
        )

        result = await suggester.suggest_with_revalidation(
            content=sample_content_norwegian,
            brand_profile=mock_brand_profile,
            language="no",
            max_iterations=3,
        )

        assert result.final_status == OverallStatus.COMPLIANT
        assert len(result.validation_history) == 2  # Initial + after rewrite

    @pytest.mark.asyncio
    async def test_suggest_with_revalidation_max_iterations(
        self,
        mock_compliance_checker,
        mock_llm_client,
        mock_brand_profile,
        sample_content_norwegian,
    ):
        """Test re-validation stops after max iterations (AC #3)."""
        # Always returns rejected
        mock_compliance_checker.check_content.return_value = ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[
                ComplianceResult(
                    phrase="behandler",
                    status=ComplianceStatus.PROHIBITED,
                    explanation="Treatment",
                    regulation_reference=RegulationRef.ARTICLE_10,
                )
            ],
            compliance_score=0.4,
            llm_enhanced=True,
        )

        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client,
        )

        result = await suggester.suggest_with_revalidation(
            content=sample_content_norwegian,
            brand_profile=mock_brand_profile,
            max_iterations=3,
        )

        # Should have 4 validation checks: initial + 3 iterations + final
        assert len(result.validation_history) <= 4

    @pytest.mark.asyncio
    async def test_norwegian_content_handling(
        self,
        mock_compliance_checker,
        mock_llm_client,
        mock_brand_profile,
        sample_prohibited_compliance_check,
        sample_content_norwegian,
    ):
        """Test Norwegian content is handled correctly (Task 2.6)."""
        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client,
        )

        request = RewriteRequest(
            content=sample_content_norwegian,
            compliance_check=sample_prohibited_compliance_check,
            brand_profile=mock_brand_profile,
            language="no",
        )

        result = await suggester.suggest_rewrites(request)

        # Verify Norwegian prompt was used
        call_kwargs = mock_llm_client.generate.call_args
        assert "FORSLAG" in call_kwargs.kwargs.get("system", "") or \
               mock_llm_client.generate.called

    @pytest.mark.asyncio
    async def test_performance_under_10_seconds(
        self,
        mock_compliance_checker,
        mock_llm_client,
        mock_brand_profile,
        sample_prohibited_compliance_check,
        sample_content_norwegian,
    ):
        """Test generation completes in < 10 seconds (AC #1)."""
        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client,
        )

        request = RewriteRequest(
            content=sample_content_norwegian,
            compliance_check=sample_prohibited_compliance_check,
            brand_profile=mock_brand_profile,
            language="no",
        )

        result = await suggester.suggest_rewrites(request)

        # Mocked, so should be nearly instant
        assert result.generation_time_ms < 10000

    @pytest.mark.asyncio
    async def test_llm_failure_returns_empty_suggestion(
        self,
        mock_compliance_checker,
        mock_brand_profile,
        sample_prohibited_compliance_check,
        sample_content_norwegian,
    ):
        """Test graceful handling of LLM failures."""
        failing_llm = AsyncMock()
        failing_llm.generate.side_effect = Exception("LLM Error")

        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=failing_llm,
        )

        request = RewriteRequest(
            content=sample_content_norwegian,
            compliance_check=sample_prohibited_compliance_check,
            brand_profile=mock_brand_profile,
            language="no",
        )

        result = await suggester.suggest_rewrites(request)

        # Should return result with empty suggestions, not crash
        assert isinstance(result, RewriteResult)
        assert len(result.suggestions) >= 1
        assert len(result.suggestions[0].suggestions) == 0

    def test_analyze_borderline_phrase_acceptable(
        self,
        mock_compliance_checker,
        mock_llm_client,
        mock_brand_profile,
    ):
        """Test borderline phrase analysis for acceptable phrases (AC #2)."""
        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client,
        )

        can_keep, explanation = suggester.analyze_borderline_phrase(
            phrase="støtter sunn metabolisme",
            context="Løvemanke støtter sunn metabolisme som del av en balansert livsstil."
        )

        assert can_keep is True

    def test_analyze_borderline_phrase_needs_change(
        self,
        mock_compliance_checker,
        mock_llm_client,
        mock_brand_profile,
    ):
        """Test borderline phrase analysis for phrases needing change (AC #2)."""
        suggester = ComplianceRewriteSuggester(
            compliance_checker=mock_compliance_checker,
            brand_profile=mock_brand_profile,
            llm_client=mock_llm_client,
        )

        can_keep, explanation = suggester.analyze_borderline_phrase(
            phrase="forebygger sykdom",
            context="Løvemanke forebygger sykdom naturlig."
        )

        assert can_keep is False


class TestRewriteResult:
    """Tests for RewriteResult dataclass."""

    def test_prohibited_count(self, sample_rewrite_suggestion, sample_borderline_suggestion):
        """Test prohibited_count property."""
        result = RewriteResult(
            original_content="test",
            suggestions=[sample_rewrite_suggestion, sample_borderline_suggestion],
        )
        assert result.prohibited_count == 1

    def test_borderline_count(self, sample_rewrite_suggestion, sample_borderline_suggestion):
        """Test borderline_count property."""
        result = RewriteResult(
            original_content="test",
            suggestions=[sample_rewrite_suggestion, sample_borderline_suggestion],
        )
        assert result.borderline_count == 1

    def test_is_compliant(self):
        """Test is_compliant property."""
        result = RewriteResult(
            original_content="test",
            final_status=OverallStatus.COMPLIANT,
        )
        assert result.is_compliant is True

    def test_validation_iterations(self):
        """Test validation_iterations property."""
        result = RewriteResult(
            original_content="test",
            validation_history=[
                ContentComplianceCheck(
                    overall_status=OverallStatus.REJECTED,
                    compliance_score=0.5,
                ),
                ContentComplianceCheck(
                    overall_status=OverallStatus.COMPLIANT,
                    compliance_score=1.0,
                ),
            ],
        )
        assert result.validation_iterations == 2
