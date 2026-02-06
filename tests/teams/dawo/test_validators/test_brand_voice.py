"""Tests for Brand Voice Validator.

Tests cover:
- Warm tone detection (friendly, inviting, personal)
- Educational tone detection (informative, not salesy)
- Nordic simplicity detection (clean, minimal, authentic)
- AI-generic language flagging (cliches, corporate speak)
- Medicinal terminology rejection
- Revision suggestion generation
- Config injection (not direct file loading)
- LLM integration with mocks
- Word boundary edge cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

# Tests will fail until implementation exists
from teams.dawo.validators.brand_voice import (
    BrandVoiceValidator,
    ValidationStatus,
    IssueType,
    BrandIssue,
    BrandValidationResult,
    LLMClient,
    ScoringWeights,
    BrandProfile,
    TonePillar,
    validate_profile,
)


# Test configuration - loaded via injection, not from file
TEST_BRAND_PROFILE = {
    "brand_name": "DAWO",
    "version": "test",
    "tone_pillars": {
        "warm": {
            "description": "Friendly, inviting, personal",
            "positive_markers": ["we", "our", "together", "share", "enjoy", "love"],
            "negative_markers": ["corporation", "enterprise", "consumers", "users"]
        },
        "educational": {
            "description": "Informative first, not salesy",
            "positive_markers": ["learn", "discover", "understand", "explore", "tradition"],
            "negative_markers": ["buy now", "limited time", "act fast", "don't miss"]
        },
        "nordic_simplicity": {
            "description": "Clean, minimal, authentic",
            "positive_markers": ["forest", "nature", "Nordic", "Scandinavian", "pure", "simple"],
            "negative_markers": ["amazing", "incredible", "revolutionary", "game-changer"]
        }
    },
    "forbidden_terms": {
        "medicinal": [
            "treatment", "treats", "cure", "cures", "heal", "heals",
            "remedy", "therapeutic", "clinical", "medicinal",
            "disease", "illness", "condition", "symptoms", "diagnosis"
        ],
        "sales_pressure": [
            "buy now", "limited time", "act fast", "don't miss out",
            "exclusive offer", "hurry", "last chance"
        ],
        "superlatives": [
            "best", "greatest", "most powerful", "ultimate",
            "revolutionary", "game-changer", "breakthrough"
        ]
    },
    "ai_generic_patterns": [
        "In today's fast-paced world",
        "Are you looking for",
        "Look no further",
        "Whether you're a .* or .*",
        "It's no secret that",
        "At the end of the day",
        "Take your .* to the next level",
        "Unlock your potential",
        "Transform your"
    ],
    "style_examples": {
        "good": [
            "We've been foraging in Nordic forests for generations.",
            "Simple ingredients. Honest sourcing. That's what we believe in."
        ],
        "bad": [
            "REVOLUTIONARY mushroom supplements that will TRANSFORM your cognitive performance!",
            "Are you looking for the BEST Lion's Mane on the market?"
        ]
    },
    "scoring_thresholds": {
        "pass": 0.8,
        "needs_revision": 0.5,
        "fail": 0.0
    }
}


@pytest.fixture
def validator():
    """Create BrandVoiceValidator with test configuration."""
    return BrandVoiceValidator(TEST_BRAND_PROFILE)


@pytest.fixture
def validator_with_llm():
    """Create BrandVoiceValidator with mock LLM client."""
    mock_llm = AsyncMock()
    return BrandVoiceValidator(TEST_BRAND_PROFILE, llm_client=mock_llm)


class TestPackageStructure:
    """Tests for package structure and imports - Task 1."""

    def test_brand_voice_validator_importable(self):
        """Test BrandVoiceValidator can be imported."""
        assert BrandVoiceValidator is not None

    def test_validation_status_enum(self):
        """Test ValidationStatus enum values."""
        assert ValidationStatus.PASS.value == "pass"
        assert ValidationStatus.NEEDS_REVISION.value == "needs_revision"
        assert ValidationStatus.FAIL.value == "fail"

    def test_issue_type_enum(self):
        """Test IssueType enum values."""
        assert IssueType.TONE_MISMATCH.value == "tone_mismatch"
        assert IssueType.AI_GENERIC.value == "ai_generic"
        assert IssueType.MEDICINAL_TERM.value == "medicinal_term"
        assert IssueType.STYLE_VIOLATION.value == "style_violation"

    def test_brand_issue_dataclass(self):
        """Test BrandIssue dataclass creation."""
        issue = BrandIssue(
            phrase="test phrase",
            issue_type=IssueType.TONE_MISMATCH,
            severity="medium",
            suggestion="Rephrase to be more warm",
            explanation="Content lacks personal touch"
        )
        assert issue.phrase == "test phrase"
        assert issue.issue_type == IssueType.TONE_MISMATCH
        assert issue.severity == "medium"

    def test_brand_validation_result_dataclass(self):
        """Test BrandValidationResult dataclass creation."""
        result = BrandValidationResult(
            status=ValidationStatus.PASS,
            issues=[],
            brand_score=0.9,
            authenticity_score=0.85,
            tone_analysis={"warm": 0.9, "educational": 0.8, "nordic": 0.7}
        )
        assert result.status == ValidationStatus.PASS
        assert result.brand_score == 0.9
        assert result.authenticity_score == 0.85


class TestToneValidation:
    """Tests for tone validation - Task 3."""

    def test_warm_tone_positive(self, validator):
        """Test content with warm tone passes."""
        content = "We love sharing our Nordic traditions with you."
        result = validator.validate_content_sync(content)

        assert result.tone_analysis["warm"] >= 0.6
        # Warm tone indicators present

    def test_warm_tone_negative(self, validator):
        """Test corporate content has low warm tone score."""
        content = "Corporation provides products to consumers and users."
        result = validator.validate_content_sync(content)

        # Corporate language should result in low warm tone score
        assert result.tone_analysis["warm"] < 0.5, (
            f"Expected warm score < 0.5 for corporate content, got {result.tone_analysis['warm']}"
        )

    def test_educational_tone_positive(self, validator):
        """Test educational content scores well."""
        content = "Discover the tradition of Nordic foraging and learn about mushrooms."
        result = validator.validate_content_sync(content)

        assert result.tone_analysis["educational"] >= 0.6

    def test_educational_tone_negative(self, validator):
        """Test salesy content flags educational issues."""
        content = "Buy now! Limited time offer! Act fast before you miss out!"
        result = validator.validate_content_sync(content)

        # Should flag salesy language
        assert result.tone_analysis["educational"] < 0.5 or result.status != ValidationStatus.PASS

    def test_nordic_simplicity_positive(self, validator):
        """Test Nordic/simple content scores well."""
        content = "Pure ingredients from Nordic forests. Simple and natural."
        result = validator.validate_content_sync(content)

        assert result.tone_analysis["nordic"] >= 0.6

    def test_nordic_simplicity_negative(self, validator):
        """Test hyperbolic content flags superlatives and has low Nordic score."""
        content = "This AMAZING, INCREDIBLE, REVOLUTIONARY product is a GAME-CHANGER!"
        result = validator.validate_content_sync(content)

        # Hyperbolic content MUST flag superlatives as issues
        superlative_issues = [
            i for i in result.issues
            if i.issue_type == IssueType.STYLE_VIOLATION
        ]
        assert len(superlative_issues) >= 1, (
            f"Expected superlative issues for hyperbolic content, got {len(superlative_issues)}"
        )
        # Nordic simplicity score should also be low
        assert result.tone_analysis["nordic"] < 0.5, (
            f"Expected nordic score < 0.5 for hyperbolic content, got {result.tone_analysis['nordic']}"
        )


class TestAIGenericDetection:
    """Tests for AI-generic language detection - Task 4."""

    def test_flags_common_ai_openings(self, validator):
        """Test AI-generic opening phrases are flagged."""
        content = "In today's fast-paced world, wellness is more important than ever."
        result = validator.validate_content_sync(content)

        ai_issues = [i for i in result.issues if i.issue_type == IssueType.AI_GENERIC]
        assert len(ai_issues) >= 1

    def test_flags_looking_for_pattern(self, validator):
        """Test 'Are you looking for' pattern is flagged."""
        content = "Are you looking for the perfect supplement?"
        result = validator.validate_content_sync(content)

        ai_issues = [i for i in result.issues if i.issue_type == IssueType.AI_GENERIC]
        assert len(ai_issues) >= 1

    def test_flags_look_no_further(self, validator):
        """Test 'Look no further' is flagged."""
        content = "Look no further! We have exactly what you need."
        result = validator.validate_content_sync(content)

        ai_issues = [i for i in result.issues if i.issue_type == IssueType.AI_GENERIC]
        assert len(ai_issues) >= 1

    def test_flags_corporate_buzzwords(self, validator):
        """Test corporate buzzwords are flagged."""
        content = "Unlock your potential and transform your wellness journey."
        result = validator.validate_content_sync(content)

        ai_issues = [i for i in result.issues if i.issue_type == IssueType.AI_GENERIC]
        assert len(ai_issues) >= 1

    def test_flags_excessive_superlatives(self, validator):
        """Test superlatives in forbidden list are flagged."""
        content = "The best, most powerful, ultimate breakthrough formula."
        result = validator.validate_content_sync(content)

        # Should flag superlatives
        assert result.status != ValidationStatus.PASS or len(result.issues) >= 1

    def test_accepts_natural_writing(self, validator):
        """Test natural, human writing is accepted."""
        content = "We've been foraging in Nordic forests for generations. Lion's mane has been part of that journey."
        result = validator.validate_content_sync(content)

        ai_issues = [i for i in result.issues if i.issue_type == IssueType.AI_GENERIC]
        assert len(ai_issues) == 0
        assert result.authenticity_score >= 0.7


class TestMedicinalTermFilter:
    """Tests for medicinal terminology filter - Task 5."""

    def test_flags_treatment_language(self, validator):
        """Test 'treatment' and 'treats' are flagged."""
        content = "This supplement treats anxiety and provides treatment for stress."
        result = validator.validate_content_sync(content)

        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        assert len(med_issues) >= 1
        assert result.status == ValidationStatus.FAIL

    def test_flags_cure_language(self, validator):
        """Test 'cure' and 'cures' are flagged."""
        content = "A natural cure that heals and cures brain fog."
        result = validator.validate_content_sync(content)

        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        assert len(med_issues) >= 1
        assert result.status == ValidationStatus.FAIL

    def test_flags_disease_references(self, validator):
        """Test disease/illness references are flagged."""
        content = "May help with disease symptoms and illness conditions."
        result = validator.validate_content_sync(content)

        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        assert len(med_issues) >= 1

    def test_flags_clinical_language(self, validator):
        """Test clinical/therapeutic language is flagged."""
        content = "Our clinically-proven therapeutic medicinal formula."
        result = validator.validate_content_sync(content)

        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        assert len(med_issues) >= 1

    def test_accepts_wellness_language(self, validator):
        """Test wellness/lifestyle language is accepted."""
        content = "Add to your daily wellness routine. Part of a healthy lifestyle."
        result = validator.validate_content_sync(content)

        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        assert len(med_issues) == 0


class TestRevisionSuggestions:
    """Tests for revision suggestion generation - Task 4."""

    def test_provides_specific_alternatives(self, validator):
        """Test suggestions are provided for flagged content."""
        content = "This revolutionary product treats anxiety."
        result = validator.validate_content_sync(content)

        # Should have issues with suggestions
        issues_with_suggestions = [i for i in result.issues if i.suggestion]
        assert len(issues_with_suggestions) >= 1

    def test_suggestions_for_ai_generic(self, validator):
        """Test AI-generic patterns get specific suggestions."""
        content = "In today's fast-paced world, you need our product."
        result = validator.validate_content_sync(content)

        ai_issues = [i for i in result.issues if i.issue_type == IssueType.AI_GENERIC]
        if ai_issues:
            assert ai_issues[0].suggestion  # Should have suggestion

    def test_suggestions_for_medicinal(self, validator):
        """Test medicinal terms get alternative suggestions."""
        content = "Our product treats stress."
        result = validator.validate_content_sync(content)

        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        if med_issues:
            assert med_issues[0].suggestion  # Should suggest compliant alternative


class TestConfigInjection:
    """Tests for configuration injection pattern - AC #2."""

    def test_accepts_profile_via_constructor(self):
        """Test validator accepts brand profile via constructor."""
        validator = BrandVoiceValidator(TEST_BRAND_PROFILE)
        assert validator.profile is not None
        assert validator.profile["brand_name"] == "DAWO"

    def test_custom_profile(self):
        """Test validator uses injected profile, not hardcoded values."""
        custom_profile = {
            "brand_name": "CUSTOM",
            "version": "custom",
            "tone_pillars": {
                "warm": {"positive_markers": [], "negative_markers": []},
                "educational": {"positive_markers": [], "negative_markers": []},
                "nordic_simplicity": {"positive_markers": [], "negative_markers": []}
            },
            "forbidden_terms": {"medicinal": ["custom_forbidden"], "sales_pressure": [], "superlatives": []},
            "ai_generic_patterns": [],
            "style_examples": {"good": [], "bad": []},
            "scoring_thresholds": {"pass": 0.8, "needs_revision": 0.5, "fail": 0.0}
        }

        validator = BrandVoiceValidator(custom_profile)
        assert validator.profile["brand_name"] == "CUSTOM"

    def test_rejects_direct_file_loading(self, validator):
        """Test validator doesn't try to load files directly."""
        # Validator should work without any file system access
        result = validator.validate_content_sync("Test content")
        assert result is not None


class TestLLMIntegration:
    """Tests for LLM integration - Task 8."""

    def test_validator_accepts_llm_client(self):
        """Test validator can be initialized with LLM client."""
        mock_llm = MagicMock()
        validator = BrandVoiceValidator(TEST_BRAND_PROFILE, llm_client=mock_llm)

        assert validator.llm_client is mock_llm

    def test_validator_works_without_llm(self):
        """Test validator works in pattern-only mode without LLM."""
        validator = BrandVoiceValidator(TEST_BRAND_PROFILE, llm_client=None)

        assert validator.llm_client is None
        result = validator.validate_content_sync("Test content")
        assert result is not None

    @pytest.mark.asyncio
    async def test_uses_llm_when_provided(self, validator_with_llm):
        """Test async validation uses LLM when provided."""
        validator_with_llm.llm_client.generate.return_value = '{"status": "pass", "issues": []}'

        result = await validator_with_llm.validate_content("Some brand content")

        # LLM should have been called
        validator_with_llm.llm_client.generate.assert_called()

    def test_falls_back_to_patterns_without_llm(self, validator):
        """Test sync validation uses pattern matching without LLM."""
        content = "In today's fast-paced world, this treats anxiety."
        result = validator.validate_content_sync(content)

        # Should still detect issues via patterns
        assert len(result.issues) >= 1


class TestValidationStatus:
    """Tests for overall validation status calculation."""

    def test_pass_status_clean_content(self, validator):
        """Test PASS status for brand-aligned content."""
        content = "We've been foraging in Nordic forests for generations. Simple ingredients. Honest sourcing."
        result = validator.validate_content_sync(content)

        # Good brand content MUST pass validation
        assert result.status == ValidationStatus.PASS, (
            f"Expected PASS for brand-aligned content, got {result.status}. "
            f"Brand score: {result.brand_score}, Issues: {len(result.issues)}"
        )
        # And should have high brand score
        assert result.brand_score >= 0.6, (
            f"Expected brand score >= 0.6, got {result.brand_score}"
        )

    def test_needs_revision_status(self, validator):
        """Test NEEDS_REVISION for borderline content."""
        content = "Unlock your potential with amazing results."
        result = validator.validate_content_sync(content)

        # AI-generic but no medicinal terms
        assert result.status in [ValidationStatus.NEEDS_REVISION, ValidationStatus.FAIL]

    def test_fail_status_medicinal(self, validator):
        """Test FAIL status for content with medicinal terms."""
        content = "This product treats and cures illness."
        result = validator.validate_content_sync(content)

        assert result.status == ValidationStatus.FAIL

    def test_brand_score_calculation(self, validator):
        """Test brand score is between 0 and 1."""
        content = "Some content about mushrooms."
        result = validator.validate_content_sync(content)

        assert 0.0 <= result.brand_score <= 1.0

    def test_authenticity_score_calculation(self, validator):
        """Test authenticity score is between 0 and 1."""
        content = "Natural content without AI patterns."
        result = validator.validate_content_sync(content)

        assert 0.0 <= result.authenticity_score <= 1.0


class TestWordBoundaryEdgeCases:
    """Tests for word boundary detection."""

    def test_treatment_vs_treats(self, validator):
        """Test 'treatment' matches but doesn't partial-match other words."""
        content = "This is a natural treatment."
        result = validator.validate_content_sync(content)

        # 'treatment' should be flagged (it's in the forbidden list)
        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        assert len(med_issues) >= 1

    def test_case_insensitive_matching(self, validator):
        """Test patterns match regardless of case."""
        content = "REVOLUTIONARY TREATMENT that CURES everything."
        result = validator.validate_content_sync(content)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) >= 1

    def test_pattern_with_punctuation(self, validator):
        """Test patterns work with adjacent punctuation."""
        content = "It treats, cures, and heals!"
        result = validator.validate_content_sync(content)

        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        assert len(med_issues) >= 3


class TestEUComplianceIntegration:
    """Tests for EU Compliance Checker integration - Task 5."""

    @pytest.mark.asyncio
    async def test_accepts_eu_compliance_result(self, validator):
        """Test validator can accept EU compliance result to avoid duplicates."""
        # Create mock EU compliance result
        from unittest.mock import MagicMock
        eu_result = MagicMock()
        eu_result.flagged_phrases = []

        result = await validator.validate_content(
            "Some content",
            eu_compliance_result=eu_result
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_uses_eu_compliance_medicinal_findings(self, validator):
        """Test validator references EU compliance medicinal findings."""
        # If EU compliance already found medicinal terms, brand voice shouldn't duplicate
        from unittest.mock import MagicMock
        eu_result = MagicMock()
        eu_result.flagged_phrases = [MagicMock(phrase="treats anxiety")]

        result = await validator.validate_content(
            "This treats anxiety.",
            eu_compliance_result=eu_result
        )

        # Should still work, potentially referencing EU findings
        assert result is not None

    @pytest.mark.asyncio
    async def test_eu_compliance_findings_used_over_pattern_matching(self, validator):
        """Test that EU compliance findings are used when provided."""
        from unittest.mock import MagicMock
        eu_result = MagicMock()
        flagged = MagicMock()
        flagged.phrase = "clinical treatment"
        eu_result.flagged_phrases = [flagged]

        result = await validator.validate_content(
            "Our clinical treatment approach.",
            eu_compliance_result=eu_result
        )

        # Should have medicinal issues from EU compliance
        med_issues = [i for i in result.issues if i.issue_type == IssueType.MEDICINAL_TERM]
        assert len(med_issues) >= 1
        # Should reference EU compliance in explanation
        assert any("EU Compliance" in i.explanation for i in med_issues)


class TestProfileModule:
    """Tests for profile.py module - BrandProfile and validate_profile."""

    def test_tone_pillar_dataclass(self):
        """Test TonePillar dataclass creation."""
        pillar = TonePillar(
            description="Friendly and warm",
            positive_markers=["we", "our"],
            negative_markers=["corporation"]
        )
        assert pillar.description == "Friendly and warm"
        assert "we" in pillar.positive_markers
        assert "corporation" in pillar.negative_markers

    def test_brand_profile_from_dict(self):
        """Test BrandProfile.from_dict() creates valid profile."""
        profile = BrandProfile.from_dict(TEST_BRAND_PROFILE)

        assert profile.brand_name == "DAWO"
        assert profile.version == "test"
        assert "warm" in profile.tone_pillars
        assert isinstance(profile.tone_pillars["warm"], TonePillar)

    def test_brand_profile_from_dict_missing_key(self):
        """Test BrandProfile.from_dict() raises on missing required keys."""
        invalid_profile = {"version": "test"}  # Missing brand_name, tone_pillars

        with pytest.raises(ValueError) as exc_info:
            BrandProfile.from_dict(invalid_profile)

        assert "Missing required" in str(exc_info.value)

    def test_validate_profile_valid(self):
        """Test validate_profile returns True for valid profile."""
        is_valid, error = validate_profile(TEST_BRAND_PROFILE)

        assert is_valid is True
        assert error is None

    def test_validate_profile_missing_brand_name(self):
        """Test validate_profile catches missing brand_name."""
        invalid = {
            "tone_pillars": {},
            "forbidden_terms": {}
        }
        is_valid, error = validate_profile(invalid)

        assert is_valid is False
        assert "brand_name" in error

    def test_validate_profile_missing_tone_pillars(self):
        """Test validate_profile catches missing tone_pillars."""
        invalid = {
            "brand_name": "Test",
            "forbidden_terms": {}
        }
        is_valid, error = validate_profile(invalid)

        assert is_valid is False
        assert "tone_pillars" in error

    def test_validate_profile_invalid_forbidden_terms(self):
        """Test validate_profile catches invalid forbidden_terms structure."""
        invalid = {
            "brand_name": "Test",
            "tone_pillars": {},
            "forbidden_terms": "not a dict"  # Should be dict
        }
        is_valid, error = validate_profile(invalid)

        assert is_valid is False
        assert "forbidden_terms" in error

    def test_validator_rejects_invalid_profile(self):
        """Test BrandVoiceValidator raises ValueError for invalid profile."""
        invalid_profile = {"version": "bad"}  # Missing required keys

        with pytest.raises(ValueError) as exc_info:
            BrandVoiceValidator(invalid_profile)

        assert "Invalid brand profile" in str(exc_info.value)


class TestScoringWeights:
    """Tests for ScoringWeights constants."""

    def test_scoring_weights_exist(self):
        """Test all scoring weight constants are defined."""
        assert hasattr(ScoringWeights, 'POSITIVE_MARKER_BONUS')
        assert hasattr(ScoringWeights, 'NEGATIVE_MARKER_PENALTY')
        assert hasattr(ScoringWeights, 'HIGH_SEVERITY_PENALTY')
        assert hasattr(ScoringWeights, 'MEDIUM_SEVERITY_PENALTY')
        assert hasattr(ScoringWeights, 'LOW_SEVERITY_PENALTY')
        assert hasattr(ScoringWeights, 'AI_GENERIC_PENALTY')

    def test_scoring_weights_values_reasonable(self):
        """Test scoring weights are within reasonable bounds."""
        assert 0 < ScoringWeights.POSITIVE_MARKER_BONUS <= 0.5
        assert 0 < ScoringWeights.NEGATIVE_MARKER_PENALTY <= 0.5
        assert 0 < ScoringWeights.HIGH_SEVERITY_PENALTY <= 0.5
        assert ScoringWeights.HIGH_SEVERITY_PENALTY > ScoringWeights.MEDIUM_SEVERITY_PENALTY
        assert ScoringWeights.MEDIUM_SEVERITY_PENALTY > ScoringWeights.LOW_SEVERITY_PENALTY
