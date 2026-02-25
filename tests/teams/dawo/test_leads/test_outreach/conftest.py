"""Test fixtures for Outreach Draft Generator.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides shared fixtures and mocks for outreach testing.
"""

import pytest
from datetime import datetime, UTC
from uuid import UUID, uuid4

from core.leads.models import Lead, LeadStatus
from teams.dawo.leads.enrichment.schemas import (
    PersonalizationHook,
    PersonalizationHookType,
    BusinessInsights,
)


@pytest.fixture
def sample_lead_id() -> UUID:
    """Provide a consistent test lead ID."""
    return uuid4()


@pytest.fixture
def sample_enrichment_data() -> dict:
    """Provide sample enrichment data for testing."""
    return {
        "enriched_at": datetime.now(UTC).isoformat(),
        "confidence_score": 7.5,
        "lead_score": 75.0,
        "personalization_hooks": [
            {"type": "focus", "detail": "Fokuserer på økologiske produkter"},
            {"type": "competitor", "detail": "Fører allerede Lion's Mane fra annen leverandør"},
            {"type": "audience", "detail": "Målretter helsebevisste forbrukere over 40"},
        ],
        "business_insights": {
            "focus_areas": ["økologiske produkter", "naturlig helse", "kosttilskudd"],
            "target_demographics": "Helsebevisste voksne 35-60",
            "product_categories": ["kosttilskudd", "superfoods", "te og urter"],
            "wellness_positioning": "strong",
        },
    }


@pytest.fixture
def sample_qualified_lead(sample_lead_id: UUID, sample_enrichment_data: dict) -> dict:
    """Provide a fully qualified lead for outreach testing."""
    return {
        "id": sample_lead_id,
        "email": "kontakt@helsekost-oslo.no",
        "first_name": "Erik",
        "last_name": "Hansen",
        "company": "Helsekost Oslo AS",
        "job_title": "Daglig leder",
        "website_url": "https://helsekost-oslo.no",
        "country": "Norway",
        "industry": "Health & Wellness Retail",
        "status": LeadStatus.QUALIFIED.value,
        "score": 75.0,
        "enrichment_data": sample_enrichment_data,
    }


@pytest.fixture
def sample_personalization_hooks() -> list[PersonalizationHook]:
    """Provide sample personalization hooks."""
    return [
        PersonalizationHook(
            hook_type=PersonalizationHookType.FOCUS,
            detail="Fokuserer på økologiske produkter",
        ),
        PersonalizationHook(
            hook_type=PersonalizationHookType.COMPETITOR,
            detail="Fører allerede Lion's Mane fra annen leverandør",
        ),
        PersonalizationHook(
            hook_type=PersonalizationHookType.AUDIENCE,
            detail="Målretter helsebevisste forbrukere over 40",
        ),
    ]


@pytest.fixture
def sample_business_insights() -> BusinessInsights:
    """Provide sample business insights."""
    return BusinessInsights(
        focus_areas=["økologiske produkter", "naturlig helse", "kosttilskudd"],
        target_demographics="Helsebevisste voksne 35-60",
        product_categories=["kosttilskudd", "superfoods", "te og urter"],
        wellness_positioning="strong",
    )
