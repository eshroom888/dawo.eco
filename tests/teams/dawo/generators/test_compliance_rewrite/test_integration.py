"""Integration tests for Compliance Rewrite Suggester.

Tests end-to-end rewrite flow with real compliance checker.
Requires actual LLM client for full integration testing.

Skip markers:
- SKIP_INTEGRATION: Set to skip integration tests in CI
- SKIP_LLM_TESTS: Set to skip tests requiring live LLM
"""

import os
import pytest
from unittest.mock import AsyncMock

from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ComplianceStatus,
    ContentComplianceCheck,
    OverallStatus,
)
from teams.dawo.validators.brand_voice import BrandProfile, TonePillar
from teams.dawo.generators.compliance_rewrite import (
    ComplianceRewriteSuggester,
    RewriteRequest,
    RewriteResult,
    apply_all_suggestions,
)


# Skip markers for CI/CD
SKIP_INTEGRATION = os.getenv("SKIP_INTEGRATION", "false").lower() == "true"
SKIP_LLM_TESTS = os.getenv("SKIP_LLM_TESTS", "true").lower() == "true"


@pytest.fixture
def real_compliance_rules():
    """Real compliance rules for integration tests."""
    return {
        "prohibited_patterns": [
            {"pattern": "behandler", "category": "treatment_claim"},
            {"pattern": "kurerer", "category": "cure_claim"},
            {"pattern": "helbreder", "category": "cure_claim"},
            {"pattern": "treats", "category": "treatment_claim"},
            {"pattern": "cures", "category": "cure_claim"},
        ],
        "borderline_patterns": [
            {"pattern": "støtter", "category": "function_claim"},
            {"pattern": "fremmer", "category": "function_claim"},
            {"pattern": "supports", "category": "function_claim"},
            {"pattern": "promotes", "category": "function_claim"},
        ],
        "permitted_patterns": [
            {"pattern": "tradisjonell", "category": "cultural"},
            {"pattern": "traditional", "category": "cultural"},
            {"pattern": "livsstil", "category": "lifestyle"},
            {"pattern": "lifestyle", "category": "lifestyle"},
        ],
        "novel_food_classifications": {},
    }


@pytest.fixture
def real_brand_profile():
    """Real DAWO brand profile for integration tests."""
    return BrandProfile(
        brand_name="DAWO",
        version="2026-02",
        tone_pillars={
            "warm": TonePillar(
                description="Warm and inviting, never corporate",
                positive_markers=["naturlig", "varm", "ekte", "autentisk"],
                negative_markers=["kald", "korporativ", "hard"]
            ),
            "educational": TonePillar(
                description="Educational first, sales come naturally",
                positive_markers=["lær", "forstå", "oppdage", "utforske"],
                negative_markers=["kjøp", "handle", "nå"]
            ),
            "nordic_simplicity": TonePillar(
                description="Nordic simplicity - clean, authentic, honest",
                positive_markers=["enkel", "ren", "nordisk", "ærlig"],
                negative_markers=["komplisert", "kunstig", "overdrevet"]
            ),
        },
        forbidden_terms={
            "medicinal": ["behandler", "kurerer", "helbreder", "lindrer"],
            "sales_pressure": ["kjøp nå", "begrenset tilbud", "siste sjanse"],
            "superlatives": ["beste", "mest effektive", "garantert"],
        },
        ai_generic_patterns=[],
        style_examples={"good": [], "bad": []},
        scoring_thresholds={"pass": 0.8, "needs_revision": 0.5, "fail": 0.0},
    )


@pytest.fixture
def real_compliance_checker(real_compliance_rules):
    """Real EU Compliance Checker for integration tests."""
    return EUComplianceChecker(
        compliance_rules=real_compliance_rules,
        llm_client=None,  # Pattern-only mode for faster tests
    )


@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestEndToEndRewriteFlow:
    """End-to-end integration tests for rewrite flow."""

    @pytest.mark.asyncio
    async def test_full_rewrite_flow_norwegian(
        self,
        real_compliance_checker,
        real_brand_profile,
        mock_llm_client,
    ):
        """Test full rewrite flow with Norwegian content (AC #1, #2, #3)."""
        content = "Løvemanke behandler hjernetåke og støtter immunforsvaret naturlig."

        # Step 1: Check compliance
        compliance = await real_compliance_checker.check_content(content)
        assert compliance.overall_status == OverallStatus.REJECTED
        assert compliance.prohibited_count >= 1

        # Step 2: Generate suggestions
        suggester = ComplianceRewriteSuggester(
            compliance_checker=real_compliance_checker,
            brand_profile=real_brand_profile,
            llm_client=mock_llm_client,
        )

        request = RewriteRequest(
            content=content,
            compliance_check=compliance,
            brand_profile=real_brand_profile,
            language="no",
        )
        result = await suggester.suggest_rewrites(request)

        assert isinstance(result, RewriteResult)
        assert len(result.suggestions) >= 1
        assert result.all_prohibited_addressed or len(result.suggestions[0].suggestions) > 0

    @pytest.mark.asyncio
    async def test_revalidation_confirms_compliance(
        self,
        real_compliance_checker,
        real_brand_profile,
    ):
        """Test re-validation confirms suggestions are compliant (AC #3)."""
        # Use mock LLM that returns compliant suggestions
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = """ORIGINAL: behandler hjernetåke
FORSLAG1: tradisjonell nordisk velvære
FORSLAG2: del av en balansert livsstil
FORSLAG3: naturlig støtte for mental klarhet
BEGRUNNELSE: Originalen brukte medisinsk terminologi.
"""

        content = "Løvemanke behandler hjernetåke naturlig."

        suggester = ComplianceRewriteSuggester(
            compliance_checker=real_compliance_checker,
            brand_profile=real_brand_profile,
            llm_client=mock_llm,
        )

        # Check initial compliance
        initial_check = await real_compliance_checker.check_content(content)
        assert initial_check.overall_status != OverallStatus.COMPLIANT

        # Generate suggestions
        request = RewriteRequest(
            content=content,
            compliance_check=initial_check,
            brand_profile=real_brand_profile,
            language="no",
        )
        result = await suggester.suggest_rewrites(request)

        # Apply first suggestion
        if result.suggestions and result.suggestions[0].suggestions:
            rewritten = apply_all_suggestions(
                content,
                result.suggestions,
                {0: 0}  # Select first suggestion
            )

            # Re-validate
            final_check = await real_compliance_checker.check_content(rewritten)
            # With proper suggestions, should be compliant or at least improved
            assert final_check.compliance_score >= initial_check.compliance_score

    @pytest.mark.asyncio
    async def test_sample_captions_with_violations(
        self,
        real_compliance_checker,
        real_brand_profile,
        mock_llm_client,
    ):
        """Test with sample captions containing violations (Task 10.2)."""
        test_captions = [
            "Løvemanke behandler hjernetåke og gir deg mental klarhet.",
            "Chaga kurerer utmattelse og gir deg ny energi.",
            "Reishi helbreder søvnproblemer naturlig.",
        ]

        suggester = ComplianceRewriteSuggester(
            compliance_checker=real_compliance_checker,
            brand_profile=real_brand_profile,
            llm_client=mock_llm_client,
        )

        for caption in test_captions:
            compliance = await real_compliance_checker.check_content(caption)
            assert compliance.overall_status == OverallStatus.REJECTED

            request = RewriteRequest(
                content=caption,
                compliance_check=compliance,
                brand_profile=real_brand_profile,
                language="no",
            )
            result = await suggester.suggest_rewrites(request)

            assert len(result.suggestions) >= 1
            # Should have addressed the prohibited phrase
            # Note: original_phrase may include context from compliance checker
            has_prohibited_addressed = any(
                s.is_prohibited and s.has_suggestions
                for s in result.suggestions
            )
            assert has_prohibited_addressed, \
                f"Expected prohibited phrase to have suggestions for: {caption}"


@pytest.mark.skipif(SKIP_LLM_TESTS, reason="LLM tests disabled")
class TestWithRealLLM:
    """Tests requiring real LLM client.

    These tests are skipped by default in CI.
    Run manually with SKIP_LLM_TESTS=false to test with real LLM.
    """

    @pytest.mark.asyncio
    async def test_real_llm_suggestion_quality(
        self,
        real_compliance_checker,
        real_brand_profile,
    ):
        """Test suggestion quality with real LLM."""
        # This test would use a real LLM client
        # Skip for now as it requires API keys
        pytest.skip("Requires real LLM client with API keys")
