"""Tests for EU Compliance Checker validator.

Tests cover:
- Prohibited phrase detection (treats, cures, prevents, disease references)
- Borderline phrase detection (supports, promotes, contributes to)
- Permitted phrase detection (wellness, lifestyle, study citations)
- Overall status calculation (COMPLIANT, WARNING, REJECTED)
- Novel Food classification validation
- Chaga supplement-only validation
- Config injection (not direct loading)
- Word boundary edge cases (treatment vs treats, supporter vs supports)
- Regulation reference constants
- LLM integration capability
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ComplianceStatus,
    OverallStatus,
    ComplianceResult,
    ContentComplianceCheck,
    NovelFoodCheck,
    RegulationRef,
    ComplianceScoring,
)
from teams.dawo.validators.eu_compliance.rules import ComplianceRules


# Test configuration - loaded via injection, not from file
TEST_CONFIG = {
    "regulation": "EC 1924/2006",
    "version": "test",
    "prohibited_patterns": [
        {"pattern": "treats", "category": "treatment_claim"},
        {"pattern": "cures", "category": "cure_claim"},
        {"pattern": "prevents", "category": "prevention_claim"},
        {"pattern": "heals", "category": "treatment_claim"},
        {"pattern": "cancer", "category": "disease_reference"},
        {"pattern": "disease", "category": "disease_reference"},
    ],
    "borderline_patterns": [
        {"pattern": "supports", "category": "function_claim"},
        {"pattern": "promotes", "category": "function_claim"},
        {"pattern": "contributes to", "category": "function_claim"},
        {"pattern": "boosts", "category": "function_claim"},
        {"pattern": "enhances", "category": "function_claim"},
    ],
    "permitted_patterns": [
        {"pattern": "wellness", "category": "lifestyle"},
        {"pattern": "ritual", "category": "lifestyle"},
        {"pattern": "tradition", "category": "cultural"},
        {"pattern": "DOI:", "category": "scientific_citation"},
    ],
    "novel_food_classifications": {
        "chaga": {"status": "novel_food", "use": "supplement_only"},
        "lions_mane": {"status": "food", "use": "food_or_supplement"},
        "reishi": {"status": "food", "use": "food_or_supplement"},
        "cordyceps": {"status": "novel_food", "use": "supplement_only"},
        "shiitake": {"status": "traditional_food", "use": "food"},
    },
}


@pytest.fixture
def checker():
    """Create EUComplianceChecker with test configuration."""
    return EUComplianceChecker(TEST_CONFIG)


@pytest.fixture
def rules():
    """Create ComplianceRules with test configuration."""
    return ComplianceRules(TEST_CONFIG)


class TestComplianceRules:
    """Tests for ComplianceRules class."""

    def test_rules_initialization(self, rules):
        """Test rules are properly loaded from config."""
        assert rules.regulation == "EC 1924/2006"
        assert len(rules.prohibited_patterns) == 6
        assert len(rules.borderline_patterns) == 5
        assert len(rules.permitted_patterns) == 4

    def test_missing_config_raises_error(self):
        """Test that missing required config keys raises ValueError."""
        incomplete_config = {"regulation": "EC 1924/2006"}
        with pytest.raises(ValueError, match="Missing required configuration key"):
            ComplianceRules(incomplete_config)

    def test_novel_food_lookup(self, rules):
        """Test Novel Food classification lookup."""
        chaga = rules.get_novel_food_classification("chaga")
        assert chaga is not None
        assert chaga["status"] == "novel_food"
        assert chaga["use"] == "supplement_only"

    def test_novel_food_lookup_unknown(self, rules):
        """Test Novel Food lookup returns None for unknown products."""
        unknown = rules.get_novel_food_classification("unknown_mushroom")
        assert unknown is None

    def test_is_prohibited_pattern(self, rules):
        """Test quick prohibited pattern check."""
        assert rules.is_prohibited_pattern("This treats anxiety")
        assert rules.is_prohibited_pattern("CURES everything")
        assert not rules.is_prohibited_pattern("This is wellness")

    def test_is_borderline_pattern(self, rules):
        """Test quick borderline pattern check."""
        assert rules.is_borderline_pattern("Supports mental clarity")
        assert rules.is_borderline_pattern("BOOSTS energy")
        assert not rules.is_borderline_pattern("Nordic tradition")


class TestProhibitedPhraseDetection:
    """Tests for prohibited phrase detection."""

    @pytest.mark.asyncio
    async def test_treats_prohibited(self, checker):
        """Test 'treats' is detected as prohibited."""
        content = "Lion's Mane treats anxiety and depression."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED
        assert result.prohibited_count >= 1
        prohibited_phrases = [
            r for r in result.flagged_phrases
            if r.status == ComplianceStatus.PROHIBITED
        ]
        assert len(prohibited_phrases) >= 1

    @pytest.mark.asyncio
    async def test_cures_prohibited(self, checker):
        """Test 'cures' is detected as prohibited."""
        content = "This mushroom cures brain fog."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED
        assert result.prohibited_count >= 1

    @pytest.mark.asyncio
    async def test_prevents_prohibited(self, checker):
        """Test 'prevents' is detected as prohibited."""
        content = "Regular use prevents cognitive decline."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED
        assert result.prohibited_count >= 1

    @pytest.mark.asyncio
    async def test_disease_reference_prohibited(self, checker):
        """Test disease references are detected as prohibited."""
        content = "May help with cancer treatment."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED
        assert result.prohibited_count >= 1

    @pytest.mark.asyncio
    async def test_multiple_prohibited(self, checker):
        """Test multiple prohibited phrases are all detected."""
        content = "Treats anxiety and prevents disease."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED
        assert result.prohibited_count >= 2


class TestBorderlinePhraseDetection:
    """Tests for borderline phrase detection."""

    @pytest.mark.asyncio
    async def test_supports_borderline(self, checker):
        """Test 'supports' is detected as borderline."""
        content = "Lion's Mane supports mental clarity."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.WARNING
        assert result.borderline_count >= 1
        assert result.prohibited_count == 0

    @pytest.mark.asyncio
    async def test_promotes_borderline(self, checker):
        """Test 'promotes' is detected as borderline."""
        content = "This extract promotes focus and concentration."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.WARNING
        assert result.borderline_count >= 1

    @pytest.mark.asyncio
    async def test_boosts_borderline(self, checker):
        """Test 'boosts' is detected as borderline."""
        content = "Cordyceps boosts energy levels naturally."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.WARNING
        assert result.borderline_count >= 1

    @pytest.mark.asyncio
    async def test_contributes_to_borderline(self, checker):
        """Test 'contributes to' is detected as borderline."""
        content = "Reishi contributes to better sleep quality."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.WARNING
        assert result.borderline_count >= 1


class TestPermittedPhraseDetection:
    """Tests for permitted phrase detection."""

    @pytest.mark.asyncio
    async def test_wellness_permitted(self, checker):
        """Test wellness language is permitted."""
        content = "Add mushrooms to your daily wellness routine."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.COMPLIANT
        assert result.prohibited_count == 0
        assert result.borderline_count == 0

    @pytest.mark.asyncio
    async def test_ritual_permitted(self, checker):
        """Test ritual language is permitted."""
        content = "Make it part of your morning ritual."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.COMPLIANT

    @pytest.mark.asyncio
    async def test_tradition_permitted(self, checker):
        """Test cultural/tradition language is permitted."""
        content = "A Nordic foraging tradition for centuries."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.COMPLIANT

    @pytest.mark.asyncio
    async def test_study_citation_permitted(self, checker):
        """Test scientific citations with DOI are permitted."""
        content = "A study (DOI: 10.1234/example) found interesting results."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.COMPLIANT


class TestOverallStatusCalculation:
    """Tests for overall compliance status calculation."""

    @pytest.mark.asyncio
    async def test_compliant_status(self, checker):
        """Test COMPLIANT status for clean content."""
        content = "Embrace the Nordic wellness tradition."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.COMPLIANT
        assert result.is_compliant is True

    @pytest.mark.asyncio
    async def test_warning_status(self, checker):
        """Test WARNING status for borderline content."""
        content = "This supports your wellness journey."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.WARNING
        assert result.is_compliant is False

    @pytest.mark.asyncio
    async def test_rejected_status(self, checker):
        """Test REJECTED status for prohibited content."""
        content = "This treats and cures health issues."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED
        assert result.is_compliant is False

    @pytest.mark.asyncio
    async def test_prohibited_overrides_borderline(self, checker):
        """Test that prohibited phrases result in REJECTED even with borderline."""
        content = "Supports wellness and treats anxiety."
        result = await checker.check_content(content)

        # Prohibited should take priority
        assert result.overall_status == OverallStatus.REJECTED


class TestNovelFoodValidation:
    """Tests for Novel Food classification validation."""

    @pytest.mark.asyncio
    async def test_chaga_supplement_only_valid(self, checker):
        """Test Chaga with supplement messaging is valid."""
        content = "Try our Chaga supplement for your daily routine."
        result = await checker.check_content(content, product_name="chaga")

        assert result.novel_food_check is not None
        assert result.novel_food_check.is_valid is True
        assert result.novel_food_check.allowed_use == "supplement_only"

    @pytest.mark.asyncio
    async def test_chaga_food_messaging_invalid(self, checker):
        """Test Chaga with food messaging is invalid."""
        content = "Add Chaga as an ingredient in your recipes."
        result = await checker.check_content(content, product_name="chaga")

        assert result.novel_food_check is not None
        assert result.novel_food_check.is_valid is False
        assert "supplement only" in result.novel_food_check.message.lower()

    @pytest.mark.asyncio
    async def test_lions_mane_food_or_supplement(self, checker):
        """Test Lion's Mane can be marketed as food or supplement."""
        content = "Add Lion's Mane to your favorite recipe."
        result = await checker.check_content(content, product_name="lions_mane")

        assert result.novel_food_check is not None
        assert result.novel_food_check.is_valid is True
        assert result.novel_food_check.allowed_use == "food_or_supplement"

    @pytest.mark.asyncio
    async def test_unknown_product_not_blocked(self, checker):
        """Test unknown products are not blocked by Novel Food check."""
        content = "Try our new mystery mushroom blend."
        result = await checker.check_content(content, product_name="unknown_mushroom")

        assert result.novel_food_check is not None
        assert result.novel_food_check.is_valid is True  # Don't block unknown

    @pytest.mark.asyncio
    async def test_cordyceps_supplement_only(self, checker):
        """Test Cordyceps is supplement-only like Chaga."""
        content = "Eat Cordyceps as a meal ingredient."
        result = await checker.check_content(content, product_name="cordyceps")

        assert result.novel_food_check is not None
        assert result.novel_food_check.is_valid is False


class TestComplianceScore:
    """Tests for compliance score calculation."""

    @pytest.mark.asyncio
    async def test_perfect_score(self, checker):
        """Test perfect score for compliant content."""
        content = "A simple wellness ritual."
        result = await checker.check_content(content)

        assert result.compliance_score == 1.0

    @pytest.mark.asyncio
    async def test_borderline_reduces_score(self, checker):
        """Test borderline phrases reduce score."""
        content = "Supports your daily wellness."
        result = await checker.check_content(content)

        assert result.compliance_score < 1.0
        assert result.compliance_score >= 0.8  # -0.1 per borderline

    @pytest.mark.asyncio
    async def test_prohibited_reduces_score_more(self, checker):
        """Test prohibited phrases reduce score significantly."""
        content = "This treats your condition."
        result = await checker.check_content(content)

        assert result.compliance_score < 0.8  # -0.3 per prohibited

    @pytest.mark.asyncio
    async def test_minimum_score_zero(self, checker):
        """Test score doesn't go below zero."""
        content = "Treats, cures, prevents, and heals all disease conditions."
        result = await checker.check_content(content)

        assert result.compliance_score >= 0.0


class TestClassifyPhrase:
    """Tests for single phrase classification."""

    def test_classify_prohibited_phrase(self, checker):
        """Test single phrase classification for prohibited."""
        result = checker.classify_phrase_sync("This treats anxiety")

        assert result.status == ComplianceStatus.PROHIBITED
        assert result.regulation_reference == RegulationRef.ARTICLE_10

    def test_classify_borderline_phrase(self, checker):
        """Test single phrase classification for borderline."""
        result = checker.classify_phrase_sync("Supports mental clarity")

        assert result.status == ComplianceStatus.BORDERLINE
        assert result.regulation_reference == RegulationRef.ARTICLE_13

    def test_classify_permitted_phrase(self, checker):
        """Test single phrase classification for permitted."""
        result = checker.classify_phrase_sync("Part of your wellness routine")

        assert result.status == ComplianceStatus.PERMITTED

    def test_classify_neutral_phrase(self, checker):
        """Test neutral phrase defaults to permitted."""
        result = checker.classify_phrase_sync("Hello world")

        assert result.status == ComplianceStatus.PERMITTED

    @pytest.mark.asyncio
    async def test_classify_phrase_async(self, checker):
        """Test async phrase classification."""
        result = await checker.classify_phrase("This treats anxiety")

        assert result.status == ComplianceStatus.PROHIBITED


class TestConfigInjection:
    """Tests for configuration injection pattern."""

    def test_config_via_constructor(self):
        """Test checker accepts config via constructor."""
        checker = EUComplianceChecker(TEST_CONFIG)
        assert checker.rules is not None
        assert checker.rules.regulation == "EC 1924/2006"

    def test_custom_config(self):
        """Test checker uses injected config, not hardcoded values."""
        custom_config = {
            "regulation": "CUSTOM-REG",
            "version": "custom",
            "prohibited_patterns": [
                {"pattern": "custom_prohibited", "category": "test"}
            ],
            "borderline_patterns": [],
            "permitted_patterns": [],
            "novel_food_classifications": {},
        }

        checker = EUComplianceChecker(custom_config)
        assert checker.rules.regulation == "CUSTOM-REG"
        assert len(checker.rules.prohibited_patterns) == 1


class TestResultDataclasses:
    """Tests for result dataclass properties."""

    def test_compliance_result_creation(self):
        """Test ComplianceResult dataclass."""
        result = ComplianceResult(
            phrase="test phrase",
            status=ComplianceStatus.PROHIBITED,
            explanation="Test explanation",
            regulation_reference="EC 1924/2006"
        )

        assert result.phrase == "test phrase"
        assert result.status == ComplianceStatus.PROHIBITED

    def test_content_compliance_check_properties(self):
        """Test ContentComplianceCheck dataclass properties."""
        check = ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[
                ComplianceResult(
                    phrase="treats",
                    status=ComplianceStatus.PROHIBITED,
                    explanation="",
                    regulation_reference=""
                ),
                ComplianceResult(
                    phrase="supports",
                    status=ComplianceStatus.BORDERLINE,
                    explanation="",
                    regulation_reference=""
                ),
            ],
            compliance_score=0.5
        )

        assert check.is_compliant is False
        assert check.prohibited_count == 1
        assert check.borderline_count == 1

    def test_novel_food_check_dataclass(self):
        """Test NovelFoodCheck dataclass."""
        check = NovelFoodCheck(
            product_name="chaga",
            classification="novel_food",
            allowed_use="supplement_only",
            is_valid=True,
            message="Product correctly marketed"
        )

        assert check.product_name == "chaga"
        assert check.classification == "novel_food"
        assert check.is_valid is True


class TestWordBoundaryEdgeCases:
    """Tests for word boundary detection - prevents false positives."""

    @pytest.mark.asyncio
    async def test_treatment_not_matched_by_treats(self, checker):
        """Test 'treatment' doesn't match 'treats' pattern."""
        # 'treatment' should NOT be flagged by 'treats' pattern
        # The word 'treatment' contains 'treat' but word boundary prevents false match
        content = "This is a natural treatment option."
        result = await checker.check_content(content)

        # Should not match 'treats' - only exact word boundary
        assert result.overall_status == OverallStatus.COMPLIANT
        assert result.prohibited_count == 0

    @pytest.mark.asyncio
    async def test_supporter_not_matched_by_supports(self, checker):
        """Test 'supporter' doesn't match 'supports' pattern."""
        content = "I'm a big supporter of this brand."
        result = await checker.check_content(content)

        # 'supporter' should NOT trigger 'supports' pattern
        assert result.overall_status == OverallStatus.COMPLIANT
        assert result.borderline_count == 0

    @pytest.mark.asyncio
    async def test_curator_not_matched_by_cures(self, checker):
        """Test 'curator' doesn't match 'cures' pattern."""
        content = "The museum curator approved this exhibit."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.COMPLIANT
        assert result.prohibited_count == 0

    @pytest.mark.asyncio
    async def test_healer_not_matched_by_heals(self, checker):
        """Test 'healer' doesn't match 'heals' pattern."""
        content = "The traditional healer shared stories."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.COMPLIANT

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, checker):
        """Test patterns match regardless of case."""
        content = "TREATS anxiety and SUPPORTS focus."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED
        assert result.prohibited_count >= 1
        assert result.borderline_count >= 1

    @pytest.mark.asyncio
    async def test_phrase_at_start_of_content(self, checker):
        """Test pattern at the very start of content."""
        content = "Treats anxiety effectively."
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED

    @pytest.mark.asyncio
    async def test_phrase_at_end_of_content(self, checker):
        """Test pattern at the very end of content."""
        content = "This product treats"
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED

    @pytest.mark.asyncio
    async def test_phrase_with_punctuation(self, checker):
        """Test patterns work with adjacent punctuation."""
        content = "It treats, cures, and heals!"
        result = await checker.check_content(content)

        assert result.overall_status == OverallStatus.REJECTED
        assert result.prohibited_count >= 3


class TestRegulationRefConstants:
    """Tests for RegulationRef constant values."""

    def test_regulation_ref_health_claims(self):
        """Test health claims regulation reference."""
        assert RegulationRef.HEALTH_CLAIMS == "EC 1924/2006"

    def test_regulation_ref_article_10(self):
        """Test Article 10 reference for prohibited claims."""
        assert RegulationRef.ARTICLE_10 == "EC 1924/2006 Article 10"

    def test_regulation_ref_article_13(self):
        """Test Article 13 reference for function claims."""
        assert RegulationRef.ARTICLE_13 == "EC 1924/2006 Article 13"

    def test_regulation_ref_article_14(self):
        """Test Article 14 reference for disease risk claims."""
        assert RegulationRef.ARTICLE_14 == "EC 1924/2006 Article 14"

    def test_regulation_ref_novel_food(self):
        """Test Novel Food regulation reference."""
        assert RegulationRef.NOVEL_FOOD == "EC 2015/2283"

    def test_regulation_ref_no_claim(self):
        """Test no claim reference."""
        assert RegulationRef.NO_CLAIM == "N/A - No claim made"

    def test_prohibited_uses_article_10(self, checker):
        """Test prohibited phrases use Article 10 reference."""
        result = checker.classify_phrase_sync("This treats anxiety")
        assert result.regulation_reference == RegulationRef.ARTICLE_10

    def test_borderline_uses_article_13(self, checker):
        """Test borderline phrases use Article 13 reference."""
        result = checker.classify_phrase_sync("Supports mental clarity")
        assert result.regulation_reference == RegulationRef.ARTICLE_13


class TestLLMIntegration:
    """Tests for LLM client integration."""

    def test_checker_accepts_llm_client(self):
        """Test checker can be initialized with LLM client."""
        mock_llm = MagicMock()
        checker = EUComplianceChecker(TEST_CONFIG, llm_client=mock_llm)

        assert checker.llm_client is mock_llm

    def test_checker_works_without_llm_client(self):
        """Test checker works in pattern-only mode without LLM."""
        checker = EUComplianceChecker(TEST_CONFIG, llm_client=None)

        assert checker.llm_client is None
        # Should still classify using patterns
        result = checker.classify_phrase_sync("This treats anxiety")
        assert result.status == ComplianceStatus.PROHIBITED

    @pytest.mark.asyncio
    async def test_llm_enhanced_flag_without_client(self, checker):
        """Test llm_enhanced is False when no client provided."""
        result = await checker.check_content("Some wellness content")

        assert result.llm_enhanced is False

    @pytest.mark.asyncio
    async def test_llm_enhanced_flag_with_mock_client(self):
        """Test llm_enhanced is True when LLM returns findings."""
        mock_llm = AsyncMock()
        # Return a structured response that will parse to findings
        mock_llm.generate.return_value = """PHRASE: test phrase
STATUS: BORDERLINE
EXPLANATION: Test finding from LLM"""

        checker = EUComplianceChecker(TEST_CONFIG, llm_client=mock_llm)
        result = await checker.check_content("Some content")

        # llm_enhanced is True when LLM returns parseable findings
        assert result.llm_enhanced is True
        assert result.borderline_count >= 1

    @pytest.mark.asyncio
    async def test_llm_client_called_with_prompts(self):
        """Test LLM client is called with correct prompts."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = ""

        checker = EUComplianceChecker(TEST_CONFIG, llm_client=mock_llm)
        await checker.check_content("Test content", product_name="chaga")

        # Verify generate was called
        mock_llm.generate.assert_called_once()

        # Check the call arguments
        call_args = mock_llm.generate.call_args
        assert "Test content" in call_args.kwargs.get("prompt", "")
        assert call_args.kwargs.get("system") is not None

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_patterns(self):
        """Test that LLM failures gracefully fall back to pattern matching."""
        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("LLM unavailable")

        checker = EUComplianceChecker(TEST_CONFIG, llm_client=mock_llm)
        result = await checker.check_content("This treats anxiety")

        # Should still detect via patterns despite LLM failure
        assert result.overall_status == OverallStatus.REJECTED
        assert result.prohibited_count >= 1

    @pytest.mark.asyncio
    async def test_use_llm_flag_disables_llm(self):
        """Test use_llm=False skips LLM even when client available."""
        mock_llm = AsyncMock()

        checker = EUComplianceChecker(TEST_CONFIG, llm_client=mock_llm)
        result = await checker.check_content("Some content", use_llm=False)

        # LLM should not be called
        mock_llm.generate.assert_not_called()
        assert result.llm_enhanced is False


class TestComplianceScoring:
    """Tests for ComplianceScoring constants."""

    def test_scoring_constants_exist(self):
        """Test all scoring constants are defined."""
        assert hasattr(ComplianceScoring, 'PROHIBITED_PENALTY')
        assert hasattr(ComplianceScoring, 'BORDERLINE_PENALTY')
        assert hasattr(ComplianceScoring, 'CONTEXT_WINDOW_CHARS')

    def test_scoring_values_reasonable(self):
        """Test scoring values are within reasonable bounds."""
        # Penalties should be positive and not exceed 1.0
        assert 0 < ComplianceScoring.PROHIBITED_PENALTY <= 1.0
        assert 0 < ComplianceScoring.BORDERLINE_PENALTY <= 1.0
        # Prohibited should be more severe than borderline
        assert ComplianceScoring.PROHIBITED_PENALTY > ComplianceScoring.BORDERLINE_PENALTY
        # Context window should be reasonable (5-100 chars)
        assert 5 <= ComplianceScoring.CONTEXT_WINDOW_CHARS <= 100

    def test_scoring_constants_used_in_calculation(self, checker):
        """Test that scoring constants are actually used in score calculation."""
        # Single prohibited phrase should reduce by PROHIBITED_PENALTY
        result = checker.classify_phrase_sync("This treats anxiety")
        assert result.status == ComplianceStatus.PROHIBITED

        # Verify the penalty value matches expected
        assert ComplianceScoring.PROHIBITED_PENALTY == 0.3
        assert ComplianceScoring.BORDERLINE_PENALTY == 0.1
