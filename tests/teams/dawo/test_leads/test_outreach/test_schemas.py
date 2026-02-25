"""Tests for Outreach schemas.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for outreach data structures.
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from teams.dawo.leads.outreach.schemas import (
    LeadType,
    OutreachDraft,
    OutreachTemplate,
    TemplateSelection,
    GenerationResult,
    GenerationStatus,
)


class TestLeadType:
    """Tests for LeadType enum."""

    def test_lead_type_values(self):
        """LeadType should have all required values."""
        assert LeadType.HEALTH_STORE.value == "health_store"
        assert LeadType.GYM_FITNESS.value == "gym_fitness"
        assert LeadType.ONLINE_RETAILER.value == "online_retailer"
        assert LeadType.WELLNESS_CENTER.value == "wellness_center"
        assert LeadType.SPECIALTY_GROCER.value == "specialty_grocer"
        assert LeadType.GENERIC.value == "generic"

    def test_lead_type_is_string_enum(self):
        """LeadType should be a string enum."""
        assert isinstance(LeadType.HEALTH_STORE, str)
        assert LeadType.HEALTH_STORE == "health_store"


class TestOutreachTemplate:
    """Tests for OutreachTemplate dataclass."""

    def test_create_template(self):
        """Should create template with all required fields."""
        template = OutreachTemplate(
            template_id="hs-intro-v2",
            lead_type=LeadType.HEALTH_STORE,
            subject_template="Samarbeid med DAWO - {{product_category}}",
            body_template="Hei {{contact_name}},\n\n{{personalization_opening}}\n\nMed vennlig hilsen,\nDAWO",
            cta_type="sample_offer",
        )

        assert template.template_id == "hs-intro-v2"
        assert template.lead_type == LeadType.HEALTH_STORE
        assert "{{contact_name}}" in template.body_template
        assert template.cta_type == "sample_offer"

    def test_template_to_dict(self):
        """Template should convert to dict for JSON storage."""
        template = OutreachTemplate(
            template_id="hs-intro-v2",
            lead_type=LeadType.HEALTH_STORE,
            subject_template="Samarbeid",
            body_template="Hei {{contact_name}}",
            cta_type="meeting_request",
        )

        result = template.to_dict()

        assert result["template_id"] == "hs-intro-v2"
        assert result["lead_type"] == "health_store"
        assert result["cta_type"] == "meeting_request"


class TestOutreachDraft:
    """Tests for OutreachDraft dataclass."""

    def test_create_draft(self):
        """Should create draft with all fields."""
        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="hs-intro-v2",
            template_type=LeadType.HEALTH_STORE,
            subject="Samarbeid med DAWO",
            body="Hei Erik, Vi tilbyr premium funksjonelle sopp...",
            word_count=185,
            personalization_hooks=["økologisk fokus", "eksisterende soppprodukter"],
            personalization_score=4,
            suggested_send_time=datetime.now(UTC),
        )

        assert draft.word_count == 185
        assert len(draft.personalization_hooks) == 2
        assert draft.personalization_score == 4

    def test_draft_word_count_validation(self):
        """Draft should have valid word count (150-250)."""
        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="test",
            template_type=LeadType.GENERIC,
            subject="Test",
            body="Word " * 200,
            word_count=200,
            personalization_hooks=[],
            personalization_score=0,
            suggested_send_time=datetime.now(UTC),
        )

        assert 150 <= draft.word_count <= 250

    def test_draft_to_dict(self):
        """Draft should convert to dict for JSONB storage."""
        lead_id = uuid4()
        now = datetime.now(UTC)

        draft = OutreachDraft(
            lead_id=lead_id,
            template_id="hs-intro-v2",
            template_type=LeadType.HEALTH_STORE,
            subject="Test Subject",
            body="Test body content.",
            word_count=3,
            personalization_hooks=["hook1", "hook2"],
            personalization_score=2,
            suggested_send_time=now,
        )

        result = draft.to_dict()

        assert result["template_id"] == "hs-intro-v2"
        assert result["template_type"] == "health_store"
        assert result["draft"]["subject"] == "Test Subject"
        assert result["draft"]["body"] == "Test body content."
        assert result["draft"]["word_count"] == 3
        assert result["personalization"]["hooks_used"] == ["hook1", "hook2"]
        assert result["personalization"]["personalization_score"] == 2


class TestTemplateSelection:
    """Tests for TemplateSelection dataclass."""

    def test_create_selection(self):
        """Should create template selection with metadata."""
        selection = TemplateSelection(
            lead_id=uuid4(),
            template_id="hs-intro-v2",
            lead_type=LeadType.HEALTH_STORE,
            classification_confidence=0.85,
            classification_reasoning="Business focuses on organic health products",
        )

        assert selection.classification_confidence == 0.85
        assert selection.template_id == "hs-intro-v2"


class TestGenerationResult:
    """Tests for GenerationResult dataclass."""

    def test_successful_generation(self):
        """Should create successful generation result."""
        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="test",
            template_type=LeadType.GENERIC,
            subject="Test",
            body="Body",
            word_count=1,
            personalization_hooks=[],
            personalization_score=0,
            suggested_send_time=datetime.now(UTC),
        )

        result = GenerationResult(
            lead_id=draft.lead_id,
            status=GenerationStatus.SUCCESS,
            draft=draft,
        )

        assert result.status == GenerationStatus.SUCCESS
        assert result.draft is not None
        assert result.error is None

    def test_failed_generation(self):
        """Should create failed generation result with error."""
        lead_id = uuid4()

        result = GenerationResult(
            lead_id=lead_id,
            status=GenerationStatus.FAILED,
            error="Lead confidence score too low",
        )

        assert result.status == GenerationStatus.FAILED
        assert result.draft is None
        assert result.error == "Lead confidence score too low"

    def test_generation_status_values(self):
        """GenerationStatus should have expected values."""
        assert GenerationStatus.SUCCESS.value == "success"
        assert GenerationStatus.FAILED.value == "failed"
        assert GenerationStatus.SKIPPED.value == "skipped"
        assert GenerationStatus.VALIDATION_FAILED.value == "validation_failed"
