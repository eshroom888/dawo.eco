"""Test fixtures for Compliance Rewrite Suggester tests.

Provides mock objects and sample data for unit and integration tests.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.validators.eu_compliance import (
    ContentComplianceCheck,
    ComplianceResult,
    ComplianceStatus,
    OverallStatus,
    RegulationRef,
)
from teams.dawo.validators.brand_voice import BrandProfile, TonePillar
from teams.dawo.generators.compliance_rewrite import (
    RewriteRequest,
    RewriteResult,
    RewriteSuggestion,
)


@pytest.fixture
def mock_compliance_checker():
    """Mock EUComplianceChecker for rewrite tests."""
    checker = AsyncMock()
    # Default to returning compliant after rewrite
    checker.check_content.return_value = ContentComplianceCheck(
        overall_status=OverallStatus.COMPLIANT,
        flagged_phrases=[],
        novel_food_check=None,
        compliance_score=1.0,
        llm_enhanced=False,
    )
    return checker


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for suggestion generation."""
    client = AsyncMock()
    # Default Norwegian response
    client.generate.return_value = """ORIGINAL: behandler hjernetåke
FORSLAG1: støtter mental klarhet
FORSLAG2: bidrar til kognitiv velvære
FORSLAG3: fremmer mentalt fokus
BEGRUNNELSE: Original brukte medisinsk terminologi (behandler) som er forbudt.
"""
    return client


@pytest.fixture
def mock_llm_client_borderline():
    """Mock LLM client for borderline phrase with keep recommendation."""
    client = AsyncMock()
    client.generate.return_value = """ORIGINAL: støtter sunn metabolisme
FORSLAG1: bidrar til naturlig energi
FORSLAG2: del av en balansert livsstil
FORSLAG3: fremmer velvære
BEHOLDE: Frasen "støtter sunn metabolisme" bruker akseptabelt livsstilsspråk og kan beholdes.
"""
    return client


@pytest.fixture
def mock_brand_profile():
    """Mock DAWO brand profile."""
    return BrandProfile(
        brand_name="DAWO",
        version="2026-02",
        tone_pillars={
            "warm": TonePillar(
                description="Warm and inviting",
                positive_markers=["varm", "inviterende", "naturlig"],
                negative_markers=["kald", "korporativ"]
            ),
            "educational": TonePillar(
                description="Educational first",
                positive_markers=["lær", "forstå", "oppdage"],
                negative_markers=["kjøp", "handle"]
            ),
            "nordic_simplicity": TonePillar(
                description="Nordic simplicity",
                positive_markers=["enkel", "ren", "autentisk"],
                negative_markers=["komplisert", "kunstig"]
            ),
        },
        forbidden_terms={
            "medicinal": ["behandler", "kurerer", "helbreder"],
            "sales_pressure": ["kjøp nå", "begrenset tilbud"]
        },
        ai_generic_patterns=["I dag skal vi", "La oss"],
        style_examples={"good": [], "bad": []},
        scoring_thresholds={"pass": 0.8, "needs_revision": 0.5, "fail": 0.0}
    )


@pytest.fixture
def sample_prohibited_compliance_check():
    """Sample compliance check with prohibited phrases."""
    return ContentComplianceCheck(
        overall_status=OverallStatus.REJECTED,
        flagged_phrases=[
            ComplianceResult(
                phrase="behandler hjernetåke",
                status=ComplianceStatus.PROHIBITED,
                explanation="Treatment claims prohibited under EC 1924/2006",
                regulation_reference=RegulationRef.ARTICLE_10,
            ),
        ],
        novel_food_check=None,
        compliance_score=0.4,
        llm_enhanced=True,
    )


@pytest.fixture
def sample_borderline_compliance_check():
    """Sample compliance check with borderline phrases."""
    return ContentComplianceCheck(
        overall_status=OverallStatus.WARNING,
        flagged_phrases=[
            ComplianceResult(
                phrase="støtter immunforsvaret",
                status=ComplianceStatus.BORDERLINE,
                explanation="Function claim requires EFSA approval",
                regulation_reference=RegulationRef.ARTICLE_13,
            ),
        ],
        novel_food_check=None,
        compliance_score=0.7,
        llm_enhanced=True,
    )


@pytest.fixture
def sample_mixed_compliance_check():
    """Sample compliance check with both prohibited and borderline phrases."""
    return ContentComplianceCheck(
        overall_status=OverallStatus.REJECTED,
        flagged_phrases=[
            ComplianceResult(
                phrase="behandler hjernetåke",
                status=ComplianceStatus.PROHIBITED,
                explanation="Treatment claims prohibited under EC 1924/2006",
                regulation_reference=RegulationRef.ARTICLE_10,
            ),
            ComplianceResult(
                phrase="støtter immunforsvaret",
                status=ComplianceStatus.BORDERLINE,
                explanation="Function claim requires EFSA approval",
                regulation_reference=RegulationRef.ARTICLE_13,
            ),
        ],
        novel_food_check=None,
        compliance_score=0.3,
        llm_enhanced=True,
    )


@pytest.fixture
def sample_content_norwegian():
    """Sample Norwegian content with compliance violations."""
    return "Løvemanke behandler hjernetåke og støtter immunforsvaret naturlig. #DAWO #Løvemanke"


@pytest.fixture
def sample_content_english():
    """Sample English content with compliance violations."""
    return "Lion's Mane treats brain fog and boosts immune system naturally. #DAWO #LionsMane"


@pytest.fixture
def sample_rewrite_request(
    sample_content_norwegian,
    sample_prohibited_compliance_check,
    mock_brand_profile
):
    """Sample rewrite request for tests."""
    return RewriteRequest(
        content=sample_content_norwegian,
        compliance_check=sample_prohibited_compliance_check,
        brand_profile=mock_brand_profile,
        language="no",
    )


@pytest.fixture
def sample_rewrite_suggestion():
    """Sample rewrite suggestion for tests."""
    return RewriteSuggestion(
        original_phrase="behandler hjernetåke",
        status=ComplianceStatus.PROHIBITED,
        regulation_reference=RegulationRef.ARTICLE_10,
        explanation="Treatment claims prohibited",
        suggestions=[
            "støtter mental klarhet",
            "bidrar til kognitiv velvære",
            "fremmer mentalt fokus"
        ],
        keep_recommendation=None,
        start_position=10,
        end_position=30,
    )


@pytest.fixture
def sample_borderline_suggestion():
    """Sample borderline suggestion with keep recommendation."""
    return RewriteSuggestion(
        original_phrase="støtter sunn metabolisme",
        status=ComplianceStatus.BORDERLINE,
        regulation_reference=RegulationRef.ARTICLE_13,
        explanation="Function claim needs review",
        suggestions=[
            "bidrar til naturlig energi",
            "del av en balansert livsstil"
        ],
        keep_recommendation="Acceptable lifestyle language",
        start_position=0,
        end_position=24,
    )
