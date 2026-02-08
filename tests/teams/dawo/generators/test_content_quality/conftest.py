"""Test fixtures for Content Quality Scorer tests.

Provides mock validators, LLM clients, and sample content requests
for testing quality scoring components.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone


@pytest.fixture
def mock_compliance_checker():
    """Mock EUComplianceChecker returning COMPLIANT."""
    from teams.dawo.validators.eu_compliance import (
        ContentComplianceCheck,
        OverallStatus,
    )
    checker = AsyncMock()
    checker.check_content.return_value = ContentComplianceCheck(
        overall_status=OverallStatus.COMPLIANT,
        flagged_phrases=[],
        novel_food_check=None,
        compliance_score=1.0,
        llm_enhanced=False,
    )
    return checker


@pytest.fixture
def mock_compliance_checker_warning():
    """Mock EUComplianceChecker returning WARNING."""
    from teams.dawo.validators.eu_compliance import (
        ContentComplianceCheck,
        OverallStatus,
    )
    checker = AsyncMock()
    checker.check_content.return_value = ContentComplianceCheck(
        overall_status=OverallStatus.WARNING,
        flagged_phrases=[],
        novel_food_check=None,
        compliance_score=0.8,
        llm_enhanced=False,
    )
    return checker


@pytest.fixture
def mock_compliance_checker_rejected():
    """Mock EUComplianceChecker returning REJECTED."""
    from teams.dawo.validators.eu_compliance import (
        ContentComplianceCheck,
        OverallStatus,
    )
    checker = AsyncMock()
    checker.check_content.return_value = ContentComplianceCheck(
        overall_status=OverallStatus.REJECTED,
        flagged_phrases=[],
        novel_food_check=None,
        compliance_score=0.0,
        llm_enhanced=False,
    )
    return checker


@pytest.fixture
def mock_brand_validator():
    """Mock BrandVoiceValidator returning PASS."""
    from teams.dawo.validators.brand_voice import (
        BrandValidationResult,
        ValidationStatus,
    )
    validator = AsyncMock()
    validator.validate_content.return_value = BrandValidationResult(
        status=ValidationStatus.PASS,
        issues=[],
        brand_score=0.9,
        authenticity_score=0.85,
        tone_analysis={"warm": 0.8, "educational": 0.7, "nordic": 0.75},
    )
    return validator


@pytest.fixture
def mock_brand_validator_needs_revision():
    """Mock BrandVoiceValidator returning NEEDS_REVISION."""
    from teams.dawo.validators.brand_voice import (
        BrandValidationResult,
        ValidationStatus,
    )
    validator = AsyncMock()
    validator.validate_content.return_value = BrandValidationResult(
        status=ValidationStatus.NEEDS_REVISION,
        issues=[],
        brand_score=0.6,
        authenticity_score=0.55,
        tone_analysis={"warm": 0.5, "educational": 0.6, "nordic": 0.55},
    )
    return validator


@pytest.fixture
def mock_brand_validator_fail():
    """Mock BrandVoiceValidator returning FAIL."""
    from teams.dawo.validators.brand_voice import (
        BrandValidationResult,
        ValidationStatus,
    )
    validator = AsyncMock()
    validator.validate_content.return_value = BrandValidationResult(
        status=ValidationStatus.FAIL,
        issues=[],
        brand_score=0.2,
        authenticity_score=0.3,
        tone_analysis={"warm": 0.2, "educational": 0.3, "nordic": 0.25},
    )
    return validator


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for authenticity analysis."""
    client = AsyncMock()
    client.generate.return_value = """
AUTHENTICITY_SCORE: 8.5
AI_PROBABILITY: 0.15
PATTERNS_DETECTED: none
VOCABULARY_DIVERSITY: 0.78
CONFIDENCE: 0.85
"""
    return client


@pytest.fixture
def mock_llm_client_ai_detected():
    """Mock LLM client detecting AI patterns."""
    client = AsyncMock()
    client.generate.return_value = """
AUTHENTICITY_SCORE: 3.0
AI_PROBABILITY: 0.75
PATTERNS_DETECTED: generic_phrasing, perfect_structure
VOCABULARY_DIVERSITY: 0.35
CONFIDENCE: 0.90
"""
    return client


@pytest.fixture
def sample_quality_request():
    """Sample content for quality scoring."""
    from teams.dawo.generators.content_quality import (
        QualityScoreRequest,
        ContentType,
    )
    return QualityScoreRequest(
        content="Løvemanke har vært brukt i tradisjonell asiatisk kultur i århundrer. Opplev denne fantastiske soppen som en del av din daglige rutine. #DAWO #DAWOmushrooms #lionsmane #wellness #norge",
        content_type=ContentType.INSTAGRAM_FEED,
        hashtags=["DAWO", "DAWOmushrooms", "lionsmane", "wellness", "norge"],
        visual_quality_score=8.5,
        source_type="research",
        compliance_check=None,
        brand_validation=None,
    )


@pytest.fixture
def low_quality_request():
    """Sample AI-like content for testing low scores."""
    from teams.dawo.generators.content_quality import (
        QualityScoreRequest,
        ContentType,
    )
    return QualityScoreRequest(
        content="In today's fast-paced world, it's no secret that supplements are game-changers. Let's dive in and unlock your potential!",
        content_type=ContentType.INSTAGRAM_FEED,
        hashtags=["supplements"],
        visual_quality_score=4.0,
        source_type="evergreen",
        compliance_check=None,
        brand_validation=None,
    )


@pytest.fixture
def minimal_hashtags_request():
    """Content with too few hashtags."""
    from teams.dawo.generators.content_quality import (
        QualityScoreRequest,
        ContentType,
    )
    return QualityScoreRequest(
        content="Great mushroom product! " * 20,  # ~100 words
        content_type=ContentType.INSTAGRAM_FEED,
        hashtags=["mushrooms"],  # Only 1 hashtag, no brand tags
        visual_quality_score=7.0,
        source_type="evergreen",
        compliance_check=None,
        brand_validation=None,
    )


@pytest.fixture
def optimal_content_request():
    """Content optimized for all scoring components."""
    from teams.dawo.generators.content_quality import (
        QualityScoreRequest,
        ContentType,
    )
    # ~200 words with proper structure
    content = (
        "Løvemanke har en rik historie i tradisjonell asiatisk kultur. "
        "Denne fantastiske soppen har vært verdsatt i århundrer for sin unike karakter. "
        "DAWO bringer deg de beste funksjonelle soppene fra Norge. "
        "Opplev kvalitet og autentisitet i hver dose. "
        "Vår løvemanke er nøye utvalgt og prosessert for optimal kvalitet. "
        "Ta den som en del av din daglige rutine for en balansert livsstil. "
        "DAWO mushrooms - din partner for velvære og balanse. "
    ) * 3  # Roughly 200 words

    return QualityScoreRequest(
        content=content + "\n\nProver det selv! Link i bio.",
        content_type=ContentType.INSTAGRAM_FEED,
        hashtags=[
            "DAWO", "DAWOmushrooms", "lionsmane", "løvemanke",
            "funksjonellesopper", "wellness", "helse", "norge",
            "naturlig", "kvalitet", "livsstil"
        ],  # 11 hashtags - optimal
        visual_quality_score=9.5,
        source_type="research",
        compliance_check=None,
        brand_validation=None,
    )
