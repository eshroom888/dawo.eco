"""Tests for Outreach Validator.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for OutreachValidator brand voice validation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
from uuid import uuid4

from teams.dawo.leads.outreach.validator import (
    OutreachValidator,
    ValidationResult,
    FORBIDDEN_PATTERNS,
)
from teams.dawo.leads.outreach.schemas import LeadType, OutreachDraft


class TestOutreachValidator:
    """Tests for OutreachValidator class."""

    @pytest.fixture
    def mock_brand_validator(self):
        """Create a mock brand voice validator."""
        validator = AsyncMock()
        validator.validate.return_value = {
            "valid": True,
            "score": 0.85,
            "issues": [],
        }
        return validator

    @pytest.fixture
    def validator(self, mock_brand_validator):
        """Create a validator with mocked brand validator."""
        return OutreachValidator(brand_validator=mock_brand_validator)

    @pytest.fixture
    def valid_draft(self):
        """Create a valid outreach draft."""
        return OutreachDraft(
            lead_id=uuid4(),
            template_id="hs-intro-v1",
            template_type=LeadType.HEALTH_STORE,
            subject="Samarbeid med DAWO",
            body="""Hei Erik,

Jeg la merke til at dere fokuserer på økologiske produkter og naturlige helseløsninger i butikken deres. Det fikk meg til å tenke på et mulig samarbeid mellom deres butikk og DAWO.

DAWO er en norsk leverandør av premium funksjonelle sopp-ekstrakter. Vi spesialiserer oss på produkter som Lion's Mane Ekstrakt, Chaga Pulver, Reishi Tinktur og Cordyceps Kapsler. Alle våre produkter er utviklet med fokus på kvalitet, renhet og dokumentert effekt basert på tradisjonell bruk.

For helsebutikker som deres, med fokus på naturlige og økologiske produkter, tror vi vårt sortiment kan være et verdifullt tillegg. Funksjonelle sopp har blitt stadig mer populære blant helsebevisste forbrukere, og vi ser økende etterspørsel i det norske markedet.

Vi tilbyr premium norsk kvalitet med full sporbarhet fra jord til ferdig produkt. Bærekraftig produksjon og transparens er kjerneverdier for oss. Våre produkter kommer med komplett dokumentasjon som gjør det enkelt for deres ansatte å gi god veiledning til kundene.

Vi sender gjerne et prøveprodukt så dere kan oppleve kvaliteten selv før dere tar en beslutning. Kan vi ta en kort samtale for å diskutere hvordan DAWO kan styrke sortimentet deres?

Med vennlig hilsen,
DAWO Team""",
            word_count=195,
            personalization_hooks=["økologiske produkter", "naturlige helseløsninger"],
            personalization_score=3,
            suggested_send_time=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_validate_returns_result(self, validator, valid_draft):
        """validate should return ValidationResult."""
        result = await validator.validate(valid_draft)

        assert isinstance(result, ValidationResult)

    @pytest.mark.asyncio
    async def test_validate_passes_for_good_draft(self, validator, valid_draft):
        """Should pass validation for a good draft."""
        result = await validator.validate(valid_draft)

        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_fails_for_generic_opener(self, validator):
        """Should fail for generic sales openers."""
        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="test",
            template_type=LeadType.GENERIC,
            subject="Test",
            body="Til hvem det måtte gjelde, vi er et selskap som selger produkter.",
            word_count=10,
            personalization_hooks=[],
            personalization_score=0,
            suggested_send_time=datetime.now(UTC),
        )

        result = await validator.validate(draft)

        assert result.is_valid is False
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_validate_fails_for_pushy_language(self, validator):
        """Should fail for pushy sales language."""
        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="test",
            template_type=LeadType.GENERIC,
            subject="Test",
            body="Hei, Kjøp nå! Begrenset tilbud! Ikke gå glipp av denne sjansen!",
            word_count=10,
            personalization_hooks=[],
            personalization_score=0,
            suggested_send_time=datetime.now(UTC),
        )

        result = await validator.validate(draft)

        assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_validate_calls_brand_validator(self, validator, mock_brand_validator, valid_draft):
        """Should call brand voice validator."""
        await validator.validate(valid_draft)

        assert mock_brand_validator.validate.called

    @pytest.mark.asyncio
    async def test_validate_fails_on_brand_validator_failure(self, validator, mock_brand_validator, valid_draft):
        """Should fail if brand validator fails."""
        mock_brand_validator.validate.return_value = {
            "valid": False,
            "score": 0.3,
            "issues": ["Tone is too aggressive"],
        }

        result = await validator.validate(valid_draft)

        assert result.is_valid is False

    def test_forbidden_patterns_list_exists(self):
        """FORBIDDEN_PATTERNS should be defined."""
        assert isinstance(FORBIDDEN_PATTERNS, list)
        assert len(FORBIDDEN_PATTERNS) > 0

    def test_forbidden_patterns_include_generic_openers(self):
        """FORBIDDEN_PATTERNS should include generic openers."""
        patterns_str = " ".join(FORBIDDEN_PATTERNS).lower()

        assert "hvem det måtte gjelde" in patterns_str or "mottaker" in patterns_str

    def test_forbidden_patterns_include_pushy_language(self):
        """FORBIDDEN_PATTERNS should include pushy sales language."""
        patterns_str = " ".join(FORBIDDEN_PATTERNS).lower()

        assert "kjøp" in patterns_str or "tilbud" in patterns_str

    @pytest.mark.asyncio
    async def test_suggest_improvements_on_failure(self, validator):
        """Should suggest improvements when validation fails."""
        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="test",
            template_type=LeadType.GENERIC,
            subject="Test",
            body="Kjære mottaker, vi er et selskap som vil selge dere noe.",
            word_count=10,
            personalization_hooks=[],
            personalization_score=0,
            suggested_send_time=datetime.now(UTC),
        )

        result = await validator.validate(draft)

        assert len(result.suggestions) > 0

    def test_validator_accepts_brand_validator_via_injection(self):
        """Validator should accept brand validator via injection."""
        mock_validator = MagicMock()
        validator = OutreachValidator(brand_validator=mock_validator)

        assert validator._brand_validator is mock_validator

    @pytest.mark.asyncio
    async def test_validation_result_structure(self, validator, valid_draft):
        """ValidationResult should have all required fields."""
        result = await validator.validate(valid_draft)

        assert hasattr(result, "is_valid")
        assert hasattr(result, "brand_voice_score")
        assert hasattr(result, "issues")
        assert hasattr(result, "suggestions")

    @pytest.mark.asyncio
    async def test_draft_in_norwegian(self, validator, valid_draft):
        """Should validate that draft is in Norwegian."""
        # Valid Norwegian draft should pass
        result = await validator.validate(valid_draft)

        assert result.is_valid is True
