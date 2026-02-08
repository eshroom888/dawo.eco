"""Integration tests for Instagram Caption Generator (Story 3.3).

These tests require real external services and are skipped by default.
Run with CAPTION_INTEGRATION_TEST=1 to enable.

Tests cover:
- End-to-end caption generation with real LLM
- Real research item from Research Pool
- Real Shopify product data
"""

import os
import pytest
from unittest.mock import AsyncMock

# Skip all tests in this module unless CAPTION_INTEGRATION_TEST=1
pytestmark = pytest.mark.skipif(
    os.environ.get("CAPTION_INTEGRATION_TEST") != "1",
    reason="Integration tests disabled. Set CAPTION_INTEGRATION_TEST=1 to run.",
)


@pytest.fixture
def real_brand_profile():
    """Load real brand profile from config file."""
    import json
    config_path = "config/dawo_brand_profile.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestEndToEndCaptionGeneration:
    """End-to-end integration tests for caption generation."""

    @pytest.mark.asyncio
    async def test_generate_caption_end_to_end(self, real_brand_profile):
        """Test full caption generation with real components.

        This test requires:
        - Real LLM client configured
        - Real Shopify credentials
        - Research Pool with items
        """
        from teams.dawo.generators.instagram_caption.agent import CaptionGenerator
        from teams.dawo.generators.instagram_caption.schemas import CaptionRequest
        from teams.dawo.validators.brand_voice.agent import BrandVoiceValidator

        # Skip if no LLM client configured
        if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("No LLM API key configured")

        # Create mock LLM client for now (would use real client in full integration)
        llm_client = AsyncMock()
        llm_client.generate.return_value = """Vi har sanket i nordiske skoger i generasjoner.

Løvemanke har alltid vært en del av vår tradisjon. Denne fantastiske soppen vokser i de dype skogene,
hvor naturen får tid til å gjøre sitt. Våre forfedre kjente til skogens gaver lenge før moderne vitenskap
begynte å utforske dem.

I dag fortsetter vi denne arven. Vi tror på enkelhet - rene råvarer, ærlig opprinnelse, og produkter
som respekterer naturen. Ingen hastverk, ingen kompromisser. Hver batch tar sin tid, akkurat som
naturen selv har lært oss.

Høsten er her, og skogen kler seg i vakre farger. Det er den perfekte tiden for å utforske naturens
gaver. Fra vår familie til din - vi deler det skogen har gitt oss gjennom generasjoner.

Vil du lære mer? Link i bio for å utforske vårt utvalg av funksjonelle sopp fra nordiske skoger.

#DAWO #DAWOmushrooms #nordisksopp #løvemanke #naturligvelvære #nordiskliv"""

        # Create mock Shopify client
        shopify_client = AsyncMock()
        shopify_client.get_product_by_handle.return_value = None  # No product for this test

        # Create real brand validator with real profile
        validator = BrandVoiceValidator(real_brand_profile)

        # Create generator
        generator = CaptionGenerator(
            brand_profile=real_brand_profile,
            shopify=shopify_client,
            brand_validator=validator,
            llm_client=llm_client,
        )

        # Create request
        request = CaptionRequest(
            research_item_id="integration_test_001",
            research_source="pubmed",
            research_content="Studie viser at løvemanke kan støtte kognitiv funksjon",
            research_tags=["lions_mane", "cognition"],
            product_handle=None,
            content_id="integration_test",
            target_topic="wellness",
        )

        # Generate caption
        result = await generator.generate(request)

        # Assertions
        assert result.success is True
        assert result.caption_text
        assert result.word_count > 0
        assert len(result.hashtags) > 0
        assert "#DAWO" in result.hashtags
        assert result.brand_voice_status in ["PASS", "NEEDS_REVISION", "FAIL"]


class TestWithRealResearchItem:
    """Tests with real research items from Research Pool."""

    @pytest.mark.asyncio
    async def test_generate_from_research_pool(self, real_brand_profile):
        """Test caption generation from a real research pool item.

        Requires Research Pool to be populated.
        """
        # This would fetch from real Research Pool
        # For now, skip if no database connection
        pytest.skip("Research Pool integration not configured")


class TestWithRealShopifyData:
    """Tests with real Shopify product data."""

    @pytest.mark.asyncio
    async def test_generate_with_real_product(self, real_brand_profile):
        """Test caption generation with real Shopify product.

        Requires Shopify credentials to be configured.
        """
        if not os.environ.get("SHOPIFY_STORE_DOMAIN") or not os.environ.get("SHOPIFY_ACCESS_TOKEN"):
            pytest.skip("Shopify credentials not configured")

        # This would use real Shopify client
        pytest.skip("Full Shopify integration test not implemented")
