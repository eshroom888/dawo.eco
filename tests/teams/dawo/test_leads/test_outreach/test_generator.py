"""Tests for Outreach Draft Generator.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for OutreachDraftGenerator LLM-powered draft generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
from uuid import uuid4

from teams.dawo.leads.outreach.generator import OutreachDraftGenerator
from teams.dawo.leads.outreach.schemas import LeadType, OutreachDraft, OutreachTemplate
from teams.dawo.leads.outreach.config import OutreachConfig
from teams.dawo.leads.outreach.personalization import PersonalizationEngine
from teams.dawo.leads.outreach.templates import OutreachTemplateRegistry


class TestOutreachDraftGenerator:
    """Tests for OutreachDraftGenerator class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock()
        # Return a properly formatted Norwegian email
        client.generate.return_value = """Hei Erik,

Jeg la merke til at dere fokuserer på økologiske produkter og allerede fører funksjonelle sopp i sortimentet. Det fikk meg til å tenke på et mulig samarbeid.

DAWO tilbyr premium funksjonelle sopp-ekstrakter som passer perfekt for butikker med fokus på naturlige helseprodukter. Våre Lion's Mane Ekstrakt og Chaga Pulver er spesielt populære blant helsebevisste forbrukere.

Premium norsk kvalitet med full sporbarhet fra jord til produkt. Vi sender gjerne et prøveprodukt så dere kan oppleve kvaliteten selv.

Med vennlig hilsen,
DAWO Team"""
        return client

    @pytest.fixture
    def personalization_engine(self):
        """Create a personalization engine."""
        return PersonalizationEngine(config=OutreachConfig())

    @pytest.fixture
    def template_registry(self):
        """Create a template registry."""
        return OutreachTemplateRegistry()

    @pytest.fixture
    def generator(self, mock_llm_client, personalization_engine, template_registry):
        """Create a draft generator with mocked dependencies."""
        return OutreachDraftGenerator(
            llm_client=mock_llm_client,
            personalization_engine=personalization_engine,
            template_registry=template_registry,
            config=OutreachConfig(),
        )

    @pytest.fixture
    def sample_enrichment_data(self):
        """Sample enrichment data for testing."""
        return {
            "personalization_hooks": [
                {"type": "focus", "detail": "Fokuserer på økologiske produkter"},
                {"type": "competitor", "detail": "Fører allerede sopp i sortimentet"},
            ],
            "business_insights": {
                "focus_areas": ["økologiske produkter", "naturlig helse"],
                "product_categories": ["kosttilskudd", "superfoods"],
            },
        }

    @pytest.mark.asyncio
    async def test_generate_returns_outreach_draft(
        self,
        generator,
        sample_enrichment_data,
    ):
        """generate should return an OutreachDraft."""
        lead_id = uuid4()

        draft = await generator.generate(
            lead_id=lead_id,
            contact_name="Erik",
            company="Helsekost Oslo",
            enrichment_data=sample_enrichment_data,
            lead_type=LeadType.HEALTH_STORE,
        )

        assert isinstance(draft, OutreachDraft)
        assert draft.lead_id == lead_id
        assert draft.template_type == LeadType.HEALTH_STORE

    @pytest.mark.asyncio
    async def test_generate_fills_template_placeholders(
        self,
        generator,
        sample_enrichment_data,
    ):
        """Draft should have template placeholders filled."""
        draft = await generator.generate(
            lead_id=uuid4(),
            contact_name="Erik",
            company="Helsekost Oslo",
            enrichment_data=sample_enrichment_data,
            lead_type=LeadType.HEALTH_STORE,
        )

        # Should not contain raw placeholders
        assert "{{" not in draft.body
        assert "}}" not in draft.body

    @pytest.mark.asyncio
    async def test_generate_uses_llm(
        self,
        generator,
        mock_llm_client,
        sample_enrichment_data,
    ):
        """Generator should use LLM to polish the draft."""
        await generator.generate(
            lead_id=uuid4(),
            contact_name="Erik",
            company="Helsekost Oslo",
            enrichment_data=sample_enrichment_data,
            lead_type=LeadType.HEALTH_STORE,
        )

        # LLM should be called
        assert mock_llm_client.generate.called

    @pytest.mark.asyncio
    async def test_draft_has_word_count(
        self,
        generator,
        sample_enrichment_data,
    ):
        """Draft should have word count calculated."""
        draft = await generator.generate(
            lead_id=uuid4(),
            contact_name="Erik",
            company="Helsekost Oslo",
            enrichment_data=sample_enrichment_data,
            lead_type=LeadType.HEALTH_STORE,
        )

        assert draft.word_count > 0

    @pytest.mark.asyncio
    async def test_draft_has_personalization_score(
        self,
        generator,
        sample_enrichment_data,
    ):
        """Draft should have personalization score."""
        draft = await generator.generate(
            lead_id=uuid4(),
            contact_name="Erik",
            company="Helsekost Oslo",
            enrichment_data=sample_enrichment_data,
            lead_type=LeadType.HEALTH_STORE,
        )

        assert draft.personalization_score >= 0

    @pytest.mark.asyncio
    async def test_draft_has_suggested_send_time(
        self,
        generator,
        sample_enrichment_data,
    ):
        """Draft should have suggested send time."""
        draft = await generator.generate(
            lead_id=uuid4(),
            contact_name="Erik",
            company="Helsekost Oslo",
            enrichment_data=sample_enrichment_data,
            lead_type=LeadType.HEALTH_STORE,
        )

        assert isinstance(draft.suggested_send_time, datetime)

    def test_validate_word_count_valid(self, generator):
        """Should return True for valid word count."""
        text = " ".join(["word"] * 200)
        assert generator.validate_word_count(text) is True

    def test_validate_word_count_too_short(self, generator):
        """Should return False for too few words."""
        text = " ".join(["word"] * 100)
        assert generator.validate_word_count(text) is False

    def test_validate_word_count_too_long(self, generator):
        """Should return False for too many words."""
        text = " ".join(["word"] * 300)
        assert generator.validate_word_count(text) is False

    def test_count_personalization_tokens(self, generator):
        """Should count personalization elements in draft."""
        # Draft with personalization references
        draft = "Jeg la merke til at dere fokuserer på økologiske produkter. Lion's Mane Ekstrakt passer perfekt."

        count = generator.count_personalization_tokens(
            draft,
            hooks=["økologiske produkter", "naturlig helse"],
            products=["Lion's Mane Ekstrakt", "Chaga Pulver"],
        )

        assert count >= 2  # At least hook and product mentioned

    def test_generator_accepts_dependencies_via_injection(self):
        """Generator should accept all dependencies via injection."""
        mock_llm = MagicMock()
        mock_personalization = MagicMock()
        mock_templates = MagicMock()
        config = OutreachConfig()

        generator = OutreachDraftGenerator(
            llm_client=mock_llm,
            personalization_engine=mock_personalization,
            template_registry=mock_templates,
            config=config,
        )

        assert generator._llm_client is mock_llm
        assert generator._personalization is mock_personalization
        assert generator._templates is mock_templates

    @pytest.mark.asyncio
    async def test_draft_contains_contact_name(
        self,
        generator,
        sample_enrichment_data,
    ):
        """Draft should contain the contact's name."""
        draft = await generator.generate(
            lead_id=uuid4(),
            contact_name="Erik",
            company="Helsekost Oslo",
            enrichment_data=sample_enrichment_data,
            lead_type=LeadType.HEALTH_STORE,
        )

        assert "Erik" in draft.body
