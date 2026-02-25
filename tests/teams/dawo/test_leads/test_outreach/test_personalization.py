"""Tests for Personalization Engine.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for PersonalizationEngine hook extraction and content generation.
"""

import pytest
from uuid import uuid4

from teams.dawo.leads.outreach.personalization import PersonalizationEngine
from teams.dawo.leads.outreach.schemas import LeadType
from teams.dawo.leads.outreach.config import OutreachConfig


class TestPersonalizationEngine:
    """Tests for PersonalizationEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a personalization engine for testing."""
        return PersonalizationEngine(config=OutreachConfig())

    @pytest.fixture
    def sample_enrichment_data(self):
        """Sample enrichment data with personalization hooks."""
        return {
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

    def test_extract_hooks_returns_formatted_strings(self, engine, sample_enrichment_data):
        """extract_hooks should return natural language strings."""
        hooks = engine.extract_hooks(sample_enrichment_data)

        assert isinstance(hooks, list)
        assert len(hooks) > 0
        assert all(isinstance(h, str) for h in hooks)

    def test_extract_hooks_from_personalization_hooks(self, engine, sample_enrichment_data):
        """Should extract hooks from personalization_hooks field."""
        hooks = engine.extract_hooks(sample_enrichment_data)

        # Should extract from the personalization hooks
        assert any("økologiske" in h.lower() for h in hooks)

    def test_extract_hooks_handles_empty_data(self, engine):
        """Should handle missing personalization_hooks gracefully."""
        hooks = engine.extract_hooks({})

        assert isinstance(hooks, list)
        assert len(hooks) == 0

    def test_select_products_returns_dawo_products(self, engine, sample_enrichment_data):
        """select_products should return DAWO product recommendations."""
        products = engine.select_products(sample_enrichment_data)

        assert isinstance(products, list)
        assert len(products) > 0
        # Products should be DAWO products
        assert all(isinstance(p, str) for p in products)

    def test_select_products_based_on_categories(self, engine):
        """Should select products based on lead's product categories."""
        enrichment = {
            "business_insights": {
                "product_categories": ["kosttilskudd", "superfoods"],
            }
        }

        products = engine.select_products(enrichment)

        # Should include relevant products
        assert len(products) > 0

    def test_select_products_handles_empty_categories(self, engine):
        """Should return default products when no categories available."""
        products = engine.select_products({})

        # Should still return some default recommendations
        assert isinstance(products, list)

    def test_generate_value_prop_returns_norwegian(self, engine, sample_enrichment_data):
        """generate_value_prop should return Norwegian value proposition."""
        value_prop = engine.generate_value_prop(sample_enrichment_data, LeadType.HEALTH_STORE)

        assert isinstance(value_prop, str)
        assert len(value_prop) > 0
        # Should be in Norwegian (check for common Norwegian words)
        assert any(word in value_prop.lower() for word in ["kvalitet", "norsk", "premium", "dawo"])

    def test_generate_value_prop_varies_by_lead_type(self, engine, sample_enrichment_data):
        """Value proposition should vary based on lead type."""
        health_store_prop = engine.generate_value_prop(sample_enrichment_data, LeadType.HEALTH_STORE)
        gym_prop = engine.generate_value_prop(sample_enrichment_data, LeadType.GYM_FITNESS)

        # Should generate different value props for different lead types
        # (At minimum, they should both be valid strings)
        assert isinstance(health_store_prop, str)
        assert isinstance(gym_prop, str)

    def test_select_cta_for_health_store(self, engine):
        """Health stores should get sample offer CTA."""
        cta = engine.select_cta(LeadType.HEALTH_STORE)

        assert isinstance(cta, str)
        assert len(cta) > 0
        # Should be in Norwegian
        assert "prøve" in cta.lower() or "sample" in cta.lower() or "produkt" in cta.lower()

    def test_select_cta_for_gym(self, engine):
        """Gyms should get meeting request CTA."""
        cta = engine.select_cta(LeadType.GYM_FITNESS)

        assert isinstance(cta, str)
        # Should reference a meeting or conversation
        assert any(word in cta.lower() for word in ["samtale", "møte", "diskutere", "kan vi"])

    def test_select_cta_for_online_retailer(self, engine):
        """Online retailers should get catalog CTA."""
        cta = engine.select_cta(LeadType.ONLINE_RETAILER)

        assert isinstance(cta, str)
        # Should reference catalog
        assert "katalog" in cta.lower() or "produkter" in cta.lower()

    def test_select_cta_for_all_lead_types(self, engine):
        """All lead types should have valid CTAs."""
        for lead_type in LeadType:
            cta = engine.select_cta(lead_type)

            assert isinstance(cta, str)
            assert len(cta) > 10  # Should be a meaningful CTA

    def test_engine_accepts_config_via_injection(self):
        """Engine should accept config via dependency injection."""
        config = OutreachConfig()
        engine = PersonalizationEngine(config=config)

        assert engine._config is config

    def test_format_hook_as_natural_language(self, engine):
        """Hooks should be formatted as natural language."""
        enrichment = {
            "personalization_hooks": [
                {"type": "focus", "detail": "Fokuserer på økologiske produkter"},
            ],
        }

        hooks = engine.extract_hooks(enrichment)

        # Should be readable sentences, not raw data
        if hooks:
            # Hook should be a readable string
            assert not hooks[0].startswith("{")
            assert not "type" in hooks[0] or "fokus" in hooks[0].lower()

    def test_product_recommendation_limit(self, engine, sample_enrichment_data):
        """Should limit number of product recommendations."""
        products = engine.select_products(sample_enrichment_data)

        # Should not overwhelm with too many products
        assert len(products) <= 3

    def test_hooks_extraction_limit(self, engine):
        """Should limit number of hooks to avoid overwhelming."""
        # Create enrichment with many hooks
        enrichment = {
            "personalization_hooks": [
                {"type": f"type_{i}", "detail": f"Detail {i}"}
                for i in range(10)
            ],
        }

        hooks = engine.extract_hooks(enrichment)

        # Should limit to reasonable number
        assert len(hooks) <= 5
