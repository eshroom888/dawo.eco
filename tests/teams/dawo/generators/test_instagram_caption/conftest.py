"""Test fixtures for Instagram Caption Generator tests.

Provides mock objects and sample data for testing caption generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

# Use direct imports to avoid circular import issues
from integrations.shopify.client import ShopifyProduct
from teams.dawo.validators.brand_voice.agent import (
    BrandValidationResult,
    ValidationStatus,
    BrandIssue,
    IssueType,
)
from teams.dawo.generators.instagram_caption.schemas import (
    CaptionRequest,
    CaptionResult,
)


@pytest.fixture
def sample_brand_profile() -> dict:
    """Complete brand profile with Norwegian section."""
    return {
        "brand_name": "DAWO",
        "version": "2026-02",
        "tone_pillars": {
            "warm": {
                "description": "Friendly, inviting",
                "positive_markers": ["we", "our", "together"],
                "negative_markers": ["corporation", "consumers"],
            },
        },
        "forbidden_terms": {
            "medicinal": ["treatment", "cure", "heal"],
            "sales_pressure": ["buy now", "limited time"],
            "superlatives": ["best", "ultimate"],
        },
        "ai_generic_patterns": [
            "In today's fast-paced world",
            "Look no further",
        ],
        "scoring_thresholds": {"pass": 0.8, "needs_revision": 0.5, "fail": 0.0},
        "norwegian": {
            "tone_pillars": {
                "warm": {
                    "description": "Varm, inviterende",
                    "positive_markers": ["vi", "vår", "sammen"],
                    "negative_markers": ["konsern", "forbrukere"],
                },
                "educational": {
                    "description": "Informativ først",
                    "positive_markers": ["lære", "oppdage", "tradisjon"],
                    "negative_markers": ["kjøp nå", "skynd deg"],
                },
                "nordic_simplicity": {
                    "description": "Rent, minimalt",
                    "positive_markers": ["skog", "natur", "nordisk"],
                    "negative_markers": ["revolusjonerende", "ultimate"],
                },
            },
            "forbidden_terms": {
                "medicinal": ["behandling", "kur", "helbrede"],
                "sales_pressure": ["kjøp nå", "begrenset tid"],
                "superlatives": ["beste", "ultimate", "revolusjonerende"],
            },
            "ai_generic_patterns": [
                "I dagens hektiske verden",
                "Er du på utkikk etter",
                "Se ikke lenger",
            ],
            "caption_guidelines": {
                "length": {"min_words": 180, "max_words": 220},
                "hashtags": {
                    "max_count": 15,
                    "brand_tags": ["#DAWO", "#DAWOmushrooms", "#nordisksopp"],
                },
            },
        },
    }


@pytest.fixture
def mock_shopify_client() -> AsyncMock:
    """Mock ShopifyClient for caption tests."""
    client = AsyncMock()
    client.get_product_by_handle.return_value = ShopifyProduct(
        id="gid://shopify/Product/123",
        title="Løvemanke Ekstrakt",
        description="<p>Premium løvemanke fra nordiske skoger</p>",
        handle="lovemanke-ekstrakt",
        price="299.00",
        currency="NOK",
        variants=[],
        images=["https://dawo.no/images/lovemanke.jpg"],
        inventory_quantity=100,
        product_type="Supplement",
        tags=["lions_mane", "supplement"],
        novel_food_classification="supplement",
        sku="DAWO-LM-001",
        benefits=["Støtter kognitiv funksjon", "Naturlig energi"],
        product_url="https://dawo.no/products/lovemanke-ekstrakt",
        collection_handles=["alle-produkter"],
        is_placeholder=False,
    )
    return client


@pytest.fixture
def mock_shopify_client_no_product() -> AsyncMock:
    """Mock ShopifyClient that returns no product."""
    client = AsyncMock()
    client.get_product_by_handle.return_value = None
    return client


@pytest.fixture
def mock_brand_validator() -> MagicMock:
    """Mock BrandVoiceValidator that returns PASS."""
    validator = MagicMock()
    validator.validate_content_sync.return_value = BrandValidationResult(
        status=ValidationStatus.PASS,
        issues=[],
        brand_score=0.85,
        authenticity_score=0.9,
        tone_analysis={"warm": 0.8, "educational": 0.7, "nordic": 0.85},
    )
    return validator


@pytest.fixture
def mock_brand_validator_needs_revision() -> MagicMock:
    """Mock BrandVoiceValidator that returns NEEDS_REVISION."""
    validator = MagicMock()
    validator.validate_content_sync.return_value = BrandValidationResult(
        status=ValidationStatus.NEEDS_REVISION,
        issues=[
            BrandIssue(
                phrase="utrolig",
                issue_type=IssueType.STYLE_VIOLATION,
                severity="medium",
                suggestion="Bruk mer nøktern ordbruk",
                explanation="Superlativ bør unngås",
            )
        ],
        brand_score=0.65,
        authenticity_score=0.8,
        tone_analysis={"warm": 0.6, "educational": 0.7, "nordic": 0.5},
    )
    return validator


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Mock LLM client for caption generation."""
    client = AsyncMock()
    # Return a valid Norwegian caption (180+ words)
    client.generate.return_value = """Vi har sanket i nordiske skoger i generasjoner, og løvemanke har alltid vært en del av den reisen.

Denne fantastiske soppen har en lang tradisjon i nordisk kultur. Våre forfedre kjente til skogens gaver, og vi fortsetter denne arven med ydmykhet og respekt for naturen.

I dag deler vi denne kunnskapen med deg. Løvemanke er ikke bare en ingrediens – den er en forbindelse til generasjoner med nordisk visdom. Når høsten kommer og skogen kler seg i gull og rust, minnes vi at naturen alltid har hatt noe å tilby oss.

Vi tror på enkelhet. Rene råvarer fra skogen, ærlig opprinnelse, og produkter som respekterer tradisjon. Ingen hastverk, ingen kompromisser. Hver batch tar sin tid, akkurat som naturen selv.

Vil du lære mer om hvordan løvemanke kan bli en del av din daglige rutine? Link i bio for å utforske vårt utvalg. Fra vår familie til din – vi deler det skogen har gitt oss.

#DAWO #DAWOmushrooms #nordisksopp #løvemanke #naturligvelvære #nordiskliv"""
    return client


@pytest.fixture
def mock_llm_client_short_response() -> AsyncMock:
    """Mock LLM client that returns too short caption."""
    client = AsyncMock()
    client.generate.return_value = "Kort tekst som ikke er lang nok. #DAWO"
    return client


@pytest.fixture
def mock_llm_client_with_ai_patterns() -> AsyncMock:
    """Mock LLM client that returns caption with AI patterns."""
    client = AsyncMock()
    client.generate.return_value = """I dagens hektiske verden er det viktig å ta vare på seg selv.

Er du på utkikk etter en naturlig måte å støtte din velvære? Se ikke lenger! Våre løvemanke-produkter er akkurat det du trenger.

Vi har sanket i nordiske skoger i generasjoner, og denne kunnskapen deler vi med deg. Naturen har så mye å tilby oss når vi tar oss tid til å lytte. Skogen gir oss rene råvarer og ærlig opprinnelse.

Hver dag er en mulighet til å utforske naturens gaver. Fra vår familie til din, deler vi det skogen har gitt oss gjennom generasjoner av nordisk tradisjon og kunnskap.

Ta din velvære til neste nivå med våre produkter. Link i bio for mer informasjon om vårt utvalg av funksjonelle sopp fra nordiske skoger.

#DAWO #DAWOmushrooms #nordisksopp #løvemanke #naturligvelvære"""
    return client


@pytest.fixture
def sample_caption_request() -> CaptionRequest:
    """Sample caption request for testing."""
    return CaptionRequest(
        research_item_id="ri_123",
        research_source="pubmed",
        research_content="Studie viser at løvemanke kan støtte kognitiv funksjon",
        research_tags=["lions_mane", "cognition", "wellness"],
        product_handle="lovemanke-ekstrakt",
        content_id="post_456",
        target_topic="wellness",
    )


@pytest.fixture
def sample_caption_request_no_product() -> CaptionRequest:
    """Sample caption request without product handle."""
    return CaptionRequest(
        research_item_id="ri_789",
        research_source="instagram",
        research_content="Trend: Flere nordmenn interesserer seg for funksjonelle sopp",
        research_tags=["trend", "mushrooms", "wellness"],
        product_handle=None,
        content_id="post_789",
        target_topic="lifestyle",
    )
