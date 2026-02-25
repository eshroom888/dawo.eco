"""Shared fixtures for violation detection tests (Story 6-7)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.regulatory.models import (
    ClaimStatus,
    CompetitorContent,
    ExtractedHealthClaim,
    HealthClaim,
)
from teams.dawo.scanners.violation_detection.config import (
    build_violation_detection_config,
)


@pytest.fixture
def sample_config():
    """ViolationDetectionConfig with default values."""
    return build_violation_detection_config({
        "enabled": True,
        "batch_size": 50,
        "min_confidence": 70,
        "auto_violation_categories": ["treatment"],
        "register_check_categories": ["prevention", "enhancement"],
        "suspect_categories": ["general_wellness"],
        "severity_mapping": {
            "treatment": "high",
            "prevention": "high",
            "enhancement": "medium",
            "general_wellness": "low",
        },
        "regulation_mapping": {
            "treatment": "EC 1924/2006 Art. 10",
            "prevention": "EC 1924/2006 Art. 14.1a",
            "enhancement": "EC 1924/2006 Art. 13.1",
            "general_wellness": "EC 1924/2006 Art. 13.1",
        },
        "mushroom_substances": [
            "reishi", "lion's mane", "chaga", "cordyceps",
            "turkey tail", "maitake", "shiitake",
            "hericium erinaceus", "ganoderma lucidum",
            "inonotus obliquus", "trametes versicolor",
            "lentinula edodes", "ophiocordyceps sinensis",
            "grifola frondosa",
        ],
    })


def _make_claim(
    category: str,
    confidence: int,
    claim_text: str,
    context: str,
    competitor_name: str,
    source_url: str,
) -> MagicMock:
    """Create a mock ExtractedHealthClaim."""
    claim = MagicMock(spec=ExtractedHealthClaim)
    claim.id = uuid4()
    claim.claim_text = claim_text
    claim.claim_category = category
    claim.confidence_score = confidence
    claim.language_detected = "en"
    claim.extraction_method = "hybrid"
    claim.eu_article_reference = "prohibited" if category == "treatment" else "13.1"
    claim.surrounding_context = context
    claim.competitor_content_id = uuid4()

    content = MagicMock(spec=CompetitorContent)
    content.competitor_name = competitor_name
    content.source_url = source_url
    claim.competitor_content = content
    return claim


@pytest.fixture
def sample_treatment_claim():
    """ExtractedHealthClaim with treatment category."""
    return _make_claim(
        category="treatment",
        confidence=92,
        claim_text="treats brain fog",
        context="Our lion's mane extract treats brain fog naturally!",
        competitor_name="CompetitorA",
        source_url="https://instagram.com/p/abc123",
    )


@pytest.fixture
def sample_enhancement_claim():
    """ExtractedHealthClaim with enhancement category."""
    return _make_claim(
        category="enhancement",
        confidence=85,
        claim_text="boosts cognitive function",
        context="Lion's mane boosts cognitive function for better focus",
        competitor_name="CompetitorB",
        source_url="https://competitor-b.com/products/lions-mane",
    )


@pytest.fixture
def sample_prevention_claim():
    """ExtractedHealthClaim with prevention category."""
    return _make_claim(
        category="prevention",
        confidence=80,
        claim_text="prevents cognitive decline",
        context="Reishi mushroom prevents cognitive decline in elderly",
        competitor_name="CompetitorD",
        source_url="https://competitor-d.com/reishi",
    )


@pytest.fixture
def sample_wellness_claim():
    """ExtractedHealthClaim with general_wellness category."""
    return _make_claim(
        category="general_wellness",
        confidence=72,
        claim_text="supports overall wellbeing",
        context="Reishi mushroom supports overall wellbeing and balance",
        competitor_name="CompetitorC",
        source_url="https://competitor-c.com/blog/reishi",
    )


@pytest.fixture
def sample_authorized_claims():
    """HealthClaim records from EU Register (none for mushrooms)."""
    vitamin_d = MagicMock(spec=HealthClaim)
    vitamin_d.claim_id = "EU-2012-001"
    vitamin_d.substance = "Vitamin D"
    vitamin_d.status = ClaimStatus.AUTHORISED.value
    vitamin_d.claim_text = (
        "Vitamin D contributes to the normal function of the immune system"
    )
    vitamin_d.food_category = "Vitamin D containing foods"
    vitamin_d.is_relevant = True
    return [vitamin_d]


@pytest.fixture
def mock_session():
    """AsyncSession mock."""
    session = AsyncMock()
    session.add = MagicMock()  # session.add is sync in SQLAlchemy
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_event_emitter():
    """RegulatoryEventEmitter mock."""
    emitter = AsyncMock()
    emitter.emit = AsyncMock()
    return emitter
