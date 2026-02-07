"""Tests for Claim Validator LLM stage.

Tests for the EU Health Claims assessment stage:
    Scanner -> Harvester -> FindingSummarizer -> [ClaimValidator] -> Transformer -> Validator -> Publisher

Test categories:
    - Initialization
    - Successful validation
    - Content potential parsing
    - Response parsing
    - Error handling
    - Default results
    - Batch processing
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.pubmed.schemas import (
    FindingSummary,
    ClaimValidationResult,
    ContentPotential,
)
from teams.dawo.scanners.pubmed.claim_validator import (
    ClaimValidator,
    ClaimValidationError,
)


class TestClaimValidatorInit:
    """Tests for ClaimValidator initialization."""

    def test_validator_creates_with_llm_client(self):
        """Should create validator with LLM client."""
        mock_llm = MagicMock()
        validator = ClaimValidator(mock_llm)

        assert validator is not None
        assert validator._llm == mock_llm

    def test_validator_accepts_compliance_checker(self):
        """Should accept optional compliance checker."""
        mock_llm = MagicMock()
        mock_compliance = MagicMock()
        validator = ClaimValidator(mock_llm, mock_compliance)

        assert validator._compliance == mock_compliance


class TestClaimValidation:
    """Tests for claim validation."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client with valid JSON response."""
        client = AsyncMock()
        client.generate = AsyncMock(return_value=json.dumps({
            "content_potential": ["citation_only", "educational"],
            "usage_guidance": "Can cite this study when discussing research directions.",
            "eu_claim_status": "no_approved_claim",
            "caveat": "Can cite study but NOT claim treatment/prevention/cure",
            "can_cite_study": True,
            "can_make_claim": False
        }))
        return client

    @pytest.fixture
    def sample_summary(self) -> FindingSummary:
        """Create sample finding summary."""
        return FindingSummary(
            compound_studied="Hericium erinaceus (Lion's mane)",
            effect_measured="Cognitive function improvement",
            key_findings="Treatment group showed significant improvement.",
            statistical_significance="p<0.05, n=77",
            study_strength="strong",
            content_potential=["educational", "citation_worthy"],
            caveat="Research finding - not an approved health claim."
        )

    @pytest.mark.asyncio
    async def test_validate_returns_claim_validation_result(
        self, mock_llm_client, sample_summary
    ):
        """Should return ClaimValidationResult."""
        validator = ClaimValidator(mock_llm_client)

        result = await validator.validate_claim_potential(sample_summary)

        assert isinstance(result, ClaimValidationResult)
        assert ContentPotential.CITATION_ONLY in result.content_potential
        assert ContentPotential.EDUCATIONAL in result.content_potential
        assert result.can_cite_study is True
        assert result.can_make_claim is False

    @pytest.mark.asyncio
    async def test_validate_calls_llm_with_prompt(
        self, mock_llm_client, sample_summary
    ):
        """Should call LLM with formatted prompt."""
        validator = ClaimValidator(mock_llm_client)

        await validator.validate_claim_potential(sample_summary)

        mock_llm_client.generate.assert_called_once()
        call_kwargs = mock_llm_client.generate.call_args.kwargs
        assert "prompt" in call_kwargs
        assert sample_summary.compound_studied in call_kwargs["prompt"]
        assert sample_summary.effect_measured in call_kwargs["prompt"]


class TestContentPotentialParsing:
    """Tests for content potential enum parsing."""

    @pytest.fixture
    def validator(self):
        """Create validator with mock LLM."""
        return ClaimValidator(AsyncMock())

    def test_parses_citation_only(self, validator):
        """Should parse citation_only to enum."""
        result = validator._parse_content_potential(["citation_only"])
        assert result == [ContentPotential.CITATION_ONLY]

    def test_parses_educational(self, validator):
        """Should parse educational to enum."""
        result = validator._parse_content_potential(["educational"])
        assert result == [ContentPotential.EDUCATIONAL]

    def test_parses_trend_awareness(self, validator):
        """Should parse trend_awareness to enum."""
        result = validator._parse_content_potential(["trend_awareness"])
        assert result == [ContentPotential.TREND_AWARENESS]

    def test_parses_no_claim(self, validator):
        """Should parse no_claim to enum."""
        result = validator._parse_content_potential(["no_claim"])
        assert result == [ContentPotential.NO_CLAIM]

    def test_parses_multiple_values(self, validator):
        """Should parse multiple values."""
        result = validator._parse_content_potential(["citation_only", "educational"])
        assert ContentPotential.CITATION_ONLY in result
        assert ContentPotential.EDUCATIONAL in result

    def test_handles_case_insensitive(self, validator):
        """Should handle case variations."""
        result = validator._parse_content_potential(["CITATION_ONLY", "Educational"])
        assert ContentPotential.CITATION_ONLY in result
        assert ContentPotential.EDUCATIONAL in result

    def test_defaults_to_no_claim_for_empty_list(self, validator):
        """Should default to NO_CLAIM for empty list."""
        result = validator._parse_content_potential([])
        assert result == [ContentPotential.NO_CLAIM]

    def test_ignores_unknown_values(self, validator):
        """Should ignore unknown values."""
        result = validator._parse_content_potential(["educational", "unknown_tag"])
        assert result == [ContentPotential.EDUCATIONAL]


class TestResponseParsing:
    """Tests for LLM response parsing."""

    @pytest.fixture
    def sample_summary(self) -> FindingSummary:
        """Create minimal summary for testing."""
        return FindingSummary(
            compound_studied="Test compound",
            effect_measured="Test effect",
            key_findings="Test findings",
            statistical_significance=None,
            study_strength="moderate",
            content_potential=["educational"],
            caveat="Standard caveat"
        )

    @pytest.mark.asyncio
    async def test_parses_clean_json(self, sample_summary):
        """Should parse clean JSON response."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=json.dumps({
            "content_potential": ["educational"],
            "usage_guidance": "Test guidance",
            "eu_claim_status": "no_approved_claim",
            "caveat": "Test caveat",
            "can_cite_study": True,
            "can_make_claim": False
        }))
        validator = ClaimValidator(mock_llm)

        result = await validator.validate_claim_potential(sample_summary)

        assert result.usage_guidance == "Test guidance"
        assert result.eu_claim_status == "no_approved_claim"

    @pytest.mark.asyncio
    async def test_parses_markdown_wrapped_json(self, sample_summary):
        """Should parse JSON wrapped in markdown code blocks."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value='''```json
{
    "content_potential": ["citation_only"],
    "usage_guidance": "Markdown test guidance",
    "eu_claim_status": "no_approved_claim",
    "caveat": "Test caveat",
    "can_cite_study": true,
    "can_make_claim": false
}
```''')
        validator = ClaimValidator(mock_llm)

        result = await validator.validate_claim_potential(sample_summary)

        assert result.usage_guidance == "Markdown test guidance"
        assert ContentPotential.CITATION_ONLY in result.content_potential

    @pytest.mark.asyncio
    async def test_uses_defaults_for_missing_fields(self, sample_summary):
        """Should use default values for missing fields."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=json.dumps({}))
        validator = ClaimValidator(mock_llm)

        result = await validator.validate_claim_potential(sample_summary)

        # Should use default values
        assert ContentPotential.NO_CLAIM in result.content_potential
        assert result.eu_claim_status == "no_approved_claim"
        assert result.can_cite_study is True  # Conservative default
        assert result.can_make_claim is False  # Conservative default


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def sample_summary(self) -> FindingSummary:
        """Create minimal summary for testing."""
        return FindingSummary(
            compound_studied="Lion's Mane",
            effect_measured="Test effect",
            key_findings="Test findings",
            statistical_significance=None,
            study_strength="moderate",
            content_potential=["educational"],
            caveat="Standard caveat"
        )

    @pytest.mark.asyncio
    async def test_returns_default_on_json_error(self, sample_summary):
        """Should return default result when JSON parsing fails."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Not valid JSON")
        validator = ClaimValidator(mock_llm)

        result = await validator.validate_claim_potential(sample_summary)

        # Should return default result instead of raising
        assert isinstance(result, ClaimValidationResult)
        assert result.can_cite_study is True
        assert result.can_make_claim is False

    @pytest.mark.asyncio
    async def test_raises_claim_validation_error_on_llm_failure(self, sample_summary):
        """Should raise ClaimValidationError when LLM fails."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("API error"))
        validator = ClaimValidator(mock_llm)

        with pytest.raises(ClaimValidationError) as exc_info:
            await validator.validate_claim_potential(sample_summary)

        assert "API error" in str(exc_info.value)
        assert exc_info.value.compound == "Lion's Mane"


class TestDefaultResult:
    """Tests for default result generation."""

    def test_default_result_has_conservative_settings(self):
        """Default result should have conservative settings."""
        validator = ClaimValidator(AsyncMock())

        result = validator._default_result()

        assert ContentPotential.EDUCATIONAL in result.content_potential
        assert result.can_cite_study is True
        assert result.can_make_claim is False
        assert result.eu_claim_status == "no_approved_claim"
        assert "no approved" in result.usage_guidance.lower()


class TestBatchValidation:
    """Tests for batch validation."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock()
        client.generate = AsyncMock(return_value=json.dumps({
            "content_potential": ["educational"],
            "usage_guidance": "Test guidance",
            "eu_claim_status": "no_approved_claim",
            "caveat": "Test caveat",
            "can_cite_study": True,
            "can_make_claim": False
        }))
        return client

    @pytest.fixture
    def sample_summaries(self) -> dict[str, FindingSummary]:
        """Create multiple summaries for batch testing."""
        return {
            str(i): FindingSummary(
                compound_studied=f"Compound {i}",
                effect_measured=f"Effect {i}",
                key_findings=f"Findings {i}",
                statistical_significance=None,
                study_strength="moderate",
                content_potential=["educational"],
                caveat="Standard caveat"
            )
            for i in range(3)
        }

    @pytest.mark.asyncio
    async def test_validate_batch_returns_dict(
        self, mock_llm_client, sample_summaries
    ):
        """Should return dict mapping PMID to ClaimValidationResult."""
        validator = ClaimValidator(mock_llm_client)

        result = await validator.validate_batch(sample_summaries)

        assert isinstance(result, dict)
        assert len(result) == 3
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert all(isinstance(v, ClaimValidationResult) for v in result.values())

    @pytest.mark.asyncio
    async def test_batch_handles_individual_failures(self, sample_summaries):
        """Should continue processing when individual validations fail."""
        mock_llm = AsyncMock()
        # First call fails, rest succeed
        mock_llm.generate = AsyncMock(side_effect=[
            Exception("First fails"),
            json.dumps({"content_potential": ["educational"], "usage_guidance": "Test",
                       "eu_claim_status": "no_approved_claim", "caveat": "Test",
                       "can_cite_study": True, "can_make_claim": False}),
            json.dumps({"content_potential": ["educational"], "usage_guidance": "Test",
                       "eu_claim_status": "no_approved_claim", "caveat": "Test",
                       "can_cite_study": True, "can_make_claim": False}),
        ])
        validator = ClaimValidator(mock_llm)

        result = await validator.validate_batch(sample_summaries)

        # Should still return all 3
        assert len(result) == 3
        # First one should be default result
        assert result["0"].can_make_claim is False


class TestClaimValidationError:
    """Tests for ClaimValidationError exception."""

    def test_error_with_message_only(self):
        """Should create error with message only."""
        error = ClaimValidationError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.compound is None

    def test_error_with_compound(self):
        """Should create error with compound."""
        error = ClaimValidationError("Failed to validate", compound="Lion's Mane")

        assert error.message == "Failed to validate"
        assert error.compound == "Lion's Mane"
