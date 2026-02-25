"""Tests for Lead Type Classifier.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for LeadTypeClassifier LLM-based lead classification.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.leads.outreach.classifier import (
    LeadTypeClassifier,
    ClassificationResult,
)
from teams.dawo.leads.outreach.schemas import LeadType


class TestLeadTypeClassifier:
    """Tests for LeadTypeClassifier class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def classifier(self, mock_llm_client):
        """Create a classifier with mocked LLM."""
        return LeadTypeClassifier(llm_client=mock_llm_client)

    @pytest.fixture
    def health_store_enrichment(self):
        """Sample enrichment data for a health store."""
        return {
            "business_insights": {
                "focus_areas": ["økologiske produkter", "naturlig helse", "kosttilskudd"],
                "target_demographics": "Helsebevisste voksne 35-60",
                "product_categories": ["kosttilskudd", "superfoods", "te og urter"],
                "wellness_positioning": "strong",
            },
            "personalization_hooks": [
                {"type": "focus", "detail": "Fokuserer på økologiske produkter"},
            ],
        }

    @pytest.fixture
    def gym_enrichment(self):
        """Sample enrichment data for a gym."""
        return {
            "business_insights": {
                "focus_areas": ["trening", "styrketrening", "personlig trening"],
                "target_demographics": "Aktive voksne 25-50",
                "product_categories": ["treningsutstyr", "proteiner", "kosttilskudd"],
                "wellness_positioning": "moderate",
            },
        }

    @pytest.mark.asyncio
    async def test_classify_health_store(self, classifier, mock_llm_client, health_store_enrichment):
        """Should classify health store lead correctly."""
        # Mock LLM response
        mock_llm_client.generate.return_value = """
        {
            "category": "HEALTH_STORE",
            "confidence": 85,
            "reasoning": "Business focuses on organic health products and supplements"
        }
        """

        result = await classifier.classify(
            lead_id=uuid4(),
            enrichment_data=health_store_enrichment,
        )

        assert result.lead_type == LeadType.HEALTH_STORE
        assert result.confidence >= 0.8
        assert "health" in result.reasoning.lower() or "organic" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_classify_gym_fitness(self, classifier, mock_llm_client, gym_enrichment):
        """Should classify gym/fitness lead correctly."""
        mock_llm_client.generate.return_value = """
        {
            "category": "GYM_FITNESS",
            "confidence": 90,
            "reasoning": "Training center with focus on fitness"
        }
        """

        result = await classifier.classify(
            lead_id=uuid4(),
            enrichment_data=gym_enrichment,
        )

        assert result.lead_type == LeadType.GYM_FITNESS
        assert result.confidence >= 0.85

    @pytest.mark.asyncio
    async def test_fallback_to_generic_on_low_confidence(self, classifier, mock_llm_client):
        """Should fallback to GENERIC when confidence is low."""
        mock_llm_client.generate.return_value = """
        {
            "category": "HEALTH_STORE",
            "confidence": 30,
            "reasoning": "Unclear business focus"
        }
        """

        result = await classifier.classify(
            lead_id=uuid4(),
            enrichment_data={"business_insights": {}},
        )

        # Should fallback to GENERIC due to low confidence
        assert result.lead_type == LeadType.GENERIC

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self, classifier, mock_llm_client):
        """Should fallback to GENERIC on LLM error."""
        mock_llm_client.generate.side_effect = Exception("LLM API error")

        result = await classifier.classify(
            lead_id=uuid4(),
            enrichment_data={"business_insights": {}},
        )

        assert result.lead_type == LeadType.GENERIC
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, classifier, mock_llm_client):
        """Should fallback to GENERIC on invalid LLM response."""
        mock_llm_client.generate.return_value = "Not valid JSON"

        result = await classifier.classify(
            lead_id=uuid4(),
            enrichment_data={"business_insights": {}},
        )

        assert result.lead_type == LeadType.GENERIC

    @pytest.mark.asyncio
    async def test_uses_business_insights(self, classifier, mock_llm_client, health_store_enrichment):
        """Classifier should use business_insights from enrichment data."""
        mock_llm_client.generate.return_value = """
        {"category": "HEALTH_STORE", "confidence": 85, "reasoning": "Test"}
        """

        await classifier.classify(
            lead_id=uuid4(),
            enrichment_data=health_store_enrichment,
        )

        # Verify LLM was called with enrichment data
        call_args = mock_llm_client.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")

        # Prompt should include business insights
        assert "focus_areas" in prompt.lower() or "business" in prompt.lower()

    @pytest.mark.asyncio
    async def test_classification_result_structure(self, classifier, mock_llm_client):
        """ClassificationResult should have all required fields."""
        mock_llm_client.generate.return_value = """
        {
            "category": "ONLINE_RETAILER",
            "confidence": 75,
            "reasoning": "E-commerce business"
        }
        """

        result = await classifier.classify(
            lead_id=uuid4(),
            enrichment_data={"business_insights": {}},
        )

        assert isinstance(result, ClassificationResult)
        assert isinstance(result.lead_type, LeadType)
        assert isinstance(result.confidence, float)
        assert isinstance(result.reasoning, str)
        assert result.lead_id is not None

    @pytest.mark.asyncio
    async def test_handles_empty_enrichment_data(self, classifier, mock_llm_client):
        """Should handle empty enrichment data gracefully."""
        mock_llm_client.generate.return_value = """
        {"category": "GENERIC", "confidence": 50, "reasoning": "Insufficient data"}
        """

        result = await classifier.classify(
            lead_id=uuid4(),
            enrichment_data={},
        )

        assert result.lead_type == LeadType.GENERIC

    @pytest.mark.asyncio
    async def test_confidence_threshold(self, classifier, mock_llm_client):
        """Confidence below threshold should result in GENERIC."""
        # Default threshold is 0.5 (50%)
        mock_llm_client.generate.return_value = """
        {"category": "WELLNESS_CENTER", "confidence": 45, "reasoning": "Maybe wellness"}
        """

        result = await classifier.classify(
            lead_id=uuid4(),
            enrichment_data={"business_insights": {}},
        )

        # 45% confidence is below threshold, should fallback
        assert result.lead_type == LeadType.GENERIC

    def test_classifier_accepts_llm_via_injection(self):
        """Classifier should accept LLM client via dependency injection."""
        mock_llm = MagicMock()
        classifier = LeadTypeClassifier(llm_client=mock_llm)

        assert classifier._llm_client is mock_llm

    @pytest.mark.asyncio
    async def test_all_lead_types_can_be_classified(self, classifier, mock_llm_client):
        """All LeadType values should be valid classification results."""
        for lead_type in LeadType:
            mock_llm_client.generate.return_value = f"""
            {{"category": "{lead_type.name}", "confidence": 80, "reasoning": "Test"}}
            """

            result = await classifier.classify(
                lead_id=uuid4(),
                enrichment_data={"business_insights": {}},
            )

            # Should not raise and should return valid result
            assert isinstance(result, ClassificationResult)
