"""Tests for Outreach Templates.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for OutreachTemplateRegistry and template management.
"""

import pytest
from uuid import uuid4
import logging

from teams.dawo.leads.outreach.templates import OutreachTemplateRegistry
from teams.dawo.leads.outreach.schemas import LeadType, OutreachTemplate


class TestOutreachTemplateRegistry:
    """Tests for OutreachTemplateRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a template registry for testing."""
        return OutreachTemplateRegistry()

    def test_registry_has_all_lead_types(self, registry):
        """Registry should have templates for all lead types."""
        for lead_type in LeadType:
            template = registry.get_template(lead_type)
            assert template is not None
            assert isinstance(template, OutreachTemplate)

    def test_get_template_returns_correct_type(self, registry):
        """get_template should return template for specified lead type."""
        template = registry.get_template(LeadType.HEALTH_STORE)

        assert template.lead_type == LeadType.HEALTH_STORE
        assert template.template_id.startswith("hs-")  # Health store prefix

    def test_health_store_template(self, registry):
        """Health store template should be appropriate for health product retailers."""
        template = registry.get_template(LeadType.HEALTH_STORE)

        assert template.lead_type == LeadType.HEALTH_STORE
        assert template.cta_type == "sample_offer"
        # Template should contain placeholders
        assert "{{contact_name}}" in template.body_template
        assert "{{personalization_opening}}" in template.body_template

    def test_gym_fitness_template(self, registry):
        """Gym/fitness template should be for training centers."""
        template = registry.get_template(LeadType.GYM_FITNESS)

        assert template.lead_type == LeadType.GYM_FITNESS
        assert template.cta_type == "meeting_request"

    def test_online_retailer_template(self, registry):
        """Online retailer template should be for e-commerce."""
        template = registry.get_template(LeadType.ONLINE_RETAILER)

        assert template.lead_type == LeadType.ONLINE_RETAILER
        assert template.cta_type == "catalog_request"

    def test_wellness_center_template(self, registry):
        """Wellness center template should be for spas and wellness."""
        template = registry.get_template(LeadType.WELLNESS_CENTER)

        assert template.lead_type == LeadType.WELLNESS_CENTER

    def test_specialty_grocer_template(self, registry):
        """Specialty grocer template should be for specialty food stores."""
        template = registry.get_template(LeadType.SPECIALTY_GROCER)

        assert template.lead_type == LeadType.SPECIALTY_GROCER

    def test_generic_template_as_fallback(self, registry):
        """Generic template should work as fallback."""
        template = registry.get_template(LeadType.GENERIC)

        assert template.lead_type == LeadType.GENERIC
        assert template.template_id.startswith("gen-")

    def test_templates_are_in_norwegian(self, registry):
        """All templates should be in Norwegian."""
        for lead_type in LeadType:
            template = registry.get_template(lead_type)

            # Check for Norwegian greeting
            assert "Hei" in template.body_template

            # Check for Norwegian sign-off
            assert "vennlig hilsen" in template.body_template.lower()

    def test_templates_have_required_placeholders(self, registry):
        """All templates should have required placeholders."""
        required_placeholders = [
            "{{contact_name}}",
            "{{personalization_opening}}",
            "{{product_recommendation}}",
            "{{value_proposition}}",
            "{{cta}}",
        ]

        for lead_type in LeadType:
            template = registry.get_template(lead_type)

            for placeholder in required_placeholders:
                assert placeholder in template.body_template, (
                    f"Template {template.template_id} missing placeholder {placeholder}"
                )

    def test_log_template_selection(self, registry, caplog):
        """log_template_selection should log the selection for tracking."""
        lead_id = uuid4()
        template_id = "hs-intro-v1"

        with caplog.at_level(logging.INFO):
            registry.log_template_selection(template_id, lead_id)

        # Should log the selection
        assert any(
            "template selection" in record.message.lower()
            for record in caplog.records
        )

    def test_get_template_by_id(self, registry):
        """Should be able to get template by ID."""
        # First get a template to know its ID
        template = registry.get_template(LeadType.HEALTH_STORE)
        template_id = template.template_id

        # Then get by ID
        retrieved = registry.get_template_by_id(template_id)

        assert retrieved is not None
        assert retrieved.template_id == template_id
        assert retrieved.lead_type == template.lead_type

    def test_get_template_by_id_returns_none_for_unknown(self, registry):
        """get_template_by_id should return None for unknown ID."""
        retrieved = registry.get_template_by_id("unknown-template-id")

        assert retrieved is None

    def test_list_all_templates(self, registry):
        """list_all should return all registered templates."""
        templates = registry.list_all()

        # Should have at least one template per lead type
        assert len(templates) >= len(LeadType)

        # All should be OutreachTemplate instances
        for template in templates:
            assert isinstance(template, OutreachTemplate)

    def test_templates_avoid_generic_sales_language(self, registry):
        """Templates should not contain forbidden generic sales language."""
        forbidden_patterns = [
            "Til hvem det måtte gjelde",
            "Kjære mottaker",
            "Vi er et selskap som",
            "Kjøp nå!",
            "Begrenset tilbud",
            "Ikke gå glipp av",
            "Eksklusivt tilbud",
        ]

        for lead_type in LeadType:
            template = registry.get_template(lead_type)

            for pattern in forbidden_patterns:
                assert pattern.lower() not in template.body_template.lower(), (
                    f"Template {template.template_id} contains forbidden pattern: {pattern}"
                )

    def test_subject_templates_are_norwegian(self, registry):
        """Subject templates should be in Norwegian."""
        for lead_type in LeadType:
            template = registry.get_template(lead_type)

            # Subject should not be empty
            assert len(template.subject_template) > 0

            # Subject should contain Norwegian or brand terms
            subject_lower = template.subject_template.lower()
            assert any(
                word in subject_lower
                for word in ["dawo", "samarbeid", "mulighet", "sopp", "produkter"]
            )
