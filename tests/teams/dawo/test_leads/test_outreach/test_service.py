"""Tests for Outreach Service.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for OutreachService orchestration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
from uuid import uuid4

from teams.dawo.leads.outreach.schemas import (
    LeadType,
    OutreachDraft,
    OutreachTemplate,
    GenerationResult,
    GenerationStatus,
)
from teams.dawo.leads.outreach.classifier import ClassificationResult


class TestOutreachService:
    """Tests for OutreachService class."""

    @pytest.fixture
    def mock_classifier(self):
        """Create a mock lead type classifier."""
        classifier = AsyncMock()
        classifier.classify.return_value = ClassificationResult(
            lead_id=uuid4(),
            lead_type=LeadType.HEALTH_STORE,
            confidence=0.85,
            reasoning="Sells health products",
        )
        return classifier

    @pytest.fixture
    def mock_template_registry(self):
        """Create a mock template registry."""
        registry = MagicMock()
        registry.get_template.return_value = OutreachTemplate(
            template_id="hs-intro-v1",
            lead_type=LeadType.HEALTH_STORE,
            subject_template="Samarbeid med DAWO",
            body_template="Hei {{contact_name}},\n\n{{personalization_opening}}\n\n{{product_recommendation}}\n\n{{value_proposition}}\n\n{{cta}}\n\nMed vennlig hilsen,\nDAWO Team",
            cta_type="sample_offer",
        )
        return registry

    @pytest.fixture
    def mock_generator(self):
        """Create a mock draft generator."""
        generator = AsyncMock()
        generator.generate.return_value = OutreachDraft(
            lead_id=uuid4(),
            template_id="hs-intro-v1",
            template_type=LeadType.HEALTH_STORE,
            subject="Samarbeid med DAWO",
            body="Hei Test, dette er en test email med minst 150 ord...",
            word_count=175,
            personalization_hooks=["økologiske produkter"],
            personalization_score=3,
            suggested_send_time=datetime.now(UTC),
        )
        return generator

    @pytest.fixture
    def mock_validator(self):
        """Create a mock validator."""
        from teams.dawo.leads.outreach.validator import ValidationResult
        validator = AsyncMock()
        validator.validate.return_value = ValidationResult(
            is_valid=True,
            brand_voice_score=0.85,
            generic_language_check=True,
            issues=[],
            suggestions=[],
        )
        return validator

    @pytest.fixture
    def mock_lead(self):
        """Create a mock lead object."""
        lead = MagicMock()
        lead.id = uuid4()
        lead.company = "Test Helse AS"
        lead.first_name = "Erik"
        lead.last_name = "Hansen"
        lead.contact_name = "Erik Hansen"  # Keep for backwards compatibility
        lead.enrichment_data = {
            "business_insights": {
                "focus_areas": ["økologiske produkter"],
                "product_categories": ["supplements", "natural_health"],
            },
            "personalization_hooks": ["fokuserer på økologisk mat"],
            "confidence_score": 8.5,
        }
        lead.confidence_score = 8.5
        return lead

    @pytest.fixture
    def service(self, mock_classifier, mock_template_registry, mock_generator, mock_validator):
        """Create OutreachService with mocked dependencies."""
        from teams.dawo.leads.outreach.service import OutreachService
        return OutreachService(
            classifier=mock_classifier,
            template_registry=mock_template_registry,
            generator=mock_generator,
            validator=mock_validator,
        )

    @pytest.mark.asyncio
    async def test_generate_outreach_returns_generation_result(self, service, mock_lead):
        """generate_outreach should return GenerationResult."""
        result = await service.generate_outreach(mock_lead)

        assert isinstance(result, GenerationResult)

    @pytest.mark.asyncio
    async def test_generate_outreach_classifies_lead(self, service, mock_lead, mock_classifier):
        """Should classify lead type before generating."""
        await service.generate_outreach(mock_lead)

        mock_classifier.classify.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_outreach_selects_template(self, service, mock_lead, mock_template_registry):
        """Should select template based on lead type."""
        await service.generate_outreach(mock_lead)

        mock_template_registry.get_template.assert_called_with(LeadType.HEALTH_STORE)

    @pytest.mark.asyncio
    async def test_generate_outreach_generates_draft(self, service, mock_lead, mock_generator):
        """Should generate draft using generator."""
        await service.generate_outreach(mock_lead)

        mock_generator.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_outreach_validates_draft(self, service, mock_lead, mock_validator):
        """Should validate draft after generation."""
        await service.generate_outreach(mock_lead)

        mock_validator.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_outreach_success_status(self, service, mock_lead):
        """Successful generation should have SUCCESS status."""
        result = await service.generate_outreach(mock_lead)

        assert result.status == GenerationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_generate_outreach_logs_template_selection(self, service, mock_lead, mock_template_registry):
        """Should log template selection."""
        await service.generate_outreach(mock_lead)

        mock_template_registry.log_template_selection.assert_called()

    @pytest.mark.asyncio
    async def test_generate_outreach_fails_on_validation_failure(self, service, mock_lead, mock_validator):
        """Should return failed result if validation fails."""
        from teams.dawo.leads.outreach.validator import ValidationResult
        mock_validator.validate.return_value = ValidationResult(
            is_valid=False,
            brand_voice_score=0.3,
            generic_language_check=False,
            issues=["Too aggressive tone"],
            suggestions=["Soften the language"],
        )

        result = await service.generate_outreach(mock_lead)

        assert result.status == GenerationStatus.VALIDATION_FAILED

    @pytest.mark.asyncio
    async def test_generate_outreach_includes_draft_on_success(self, service, mock_lead):
        """Successful generation should include the draft."""
        result = await service.generate_outreach(mock_lead)

        assert result.draft is not None
        assert isinstance(result.draft, OutreachDraft)

    @pytest.mark.asyncio
    async def test_generate_outreach_handles_classification_error(self, service, mock_lead, mock_classifier):
        """Should handle classification errors gracefully."""
        mock_classifier.classify.side_effect = Exception("LLM error")

        result = await service.generate_outreach(mock_lead)

        assert result.status == GenerationStatus.FAILED
        assert "classification" in result.error.lower()

    @pytest.mark.asyncio
    async def test_generate_outreach_handles_generation_error(self, service, mock_lead, mock_generator):
        """Should handle generation errors gracefully."""
        mock_generator.generate.side_effect = Exception("LLM error")

        result = await service.generate_outreach(mock_lead)

        assert result.status == GenerationStatus.FAILED

    def test_service_accepts_dependencies_via_injection(self, mock_classifier, mock_template_registry, mock_generator, mock_validator):
        """Service should accept all dependencies via injection."""
        from teams.dawo.leads.outreach.service import OutreachService
        service = OutreachService(
            classifier=mock_classifier,
            template_registry=mock_template_registry,
            generator=mock_generator,
            validator=mock_validator,
        )

        assert service._classifier is mock_classifier
        assert service._template_registry is mock_template_registry
        assert service._generator is mock_generator
        assert service._validator is mock_validator

    @pytest.mark.asyncio
    async def test_prepare_for_approval_returns_dict(self, service, mock_lead, mock_generator):
        """prepare_for_approval should return approval data dict."""
        draft = mock_generator.generate.return_value

        approval_data = service.prepare_for_approval(draft, mock_lead)

        assert isinstance(approval_data, dict)

    @pytest.mark.asyncio
    async def test_prepare_for_approval_includes_lead_summary(self, service, mock_lead, mock_generator):
        """Approval data should include lead summary."""
        draft = mock_generator.generate.return_value

        approval_data = service.prepare_for_approval(draft, mock_lead)

        assert "lead_summary" in approval_data
        assert "company" in approval_data["lead_summary"]

    @pytest.mark.asyncio
    async def test_prepare_for_approval_includes_personalization(self, service, mock_lead, mock_generator):
        """Approval data should include personalization used."""
        draft = mock_generator.generate.return_value

        approval_data = service.prepare_for_approval(draft, mock_lead)

        assert "personalization" in approval_data

    @pytest.mark.asyncio
    async def test_prepare_for_approval_includes_send_time(self, service, mock_lead, mock_generator):
        """Approval data should include suggested send time."""
        draft = mock_generator.generate.return_value

        approval_data = service.prepare_for_approval(draft, mock_lead)

        assert "suggested_send_time" in approval_data

    @pytest.mark.asyncio
    async def test_prepare_for_approval_includes_template_info(self, service, mock_lead, mock_generator):
        """Approval data should include template information."""
        draft = mock_generator.generate.return_value

        approval_data = service.prepare_for_approval(draft, mock_lead)

        assert "template_type" in approval_data

    @pytest.mark.asyncio
    async def test_is_qualified_for_outreach_true(self, service, mock_lead):
        """Should return True for qualified leads."""
        mock_lead.confidence_score = 8.5
        mock_lead.status = "QUALIFIED"

        is_qualified = service.is_qualified_for_outreach(mock_lead)

        assert is_qualified is True

    @pytest.mark.asyncio
    async def test_is_qualified_for_outreach_false_low_confidence(self, service, mock_lead):
        """Should return False for low confidence leads."""
        mock_lead.confidence_score = 4.0
        mock_lead.status = "QUALIFIED"

        is_qualified = service.is_qualified_for_outreach(mock_lead)

        assert is_qualified is False

    @pytest.mark.asyncio
    async def test_is_qualified_for_outreach_boundary(self, service, mock_lead):
        """Should return True for exactly threshold confidence."""
        mock_lead.confidence_score = 6.0  # Exactly at threshold
        mock_lead.status = "QUALIFIED"

        is_qualified = service.is_qualified_for_outreach(mock_lead)

        assert is_qualified is True
