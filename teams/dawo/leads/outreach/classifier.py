"""Lead Type Classifier for Outreach Template Selection.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides LLM-based classification of B2B leads into types
for template selection:
- LeadTypeClassifier: Main classifier class
- ClassificationResult: Classification output
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Optional, Protocol
from uuid import UUID

from teams.dawo.leads.outreach.schemas import LeadType


logger = logging.getLogger(__name__)


# Confidence threshold for accepting classification (50%)
DEFAULT_CONFIDENCE_THRESHOLD = 0.50


class LLMClientProtocol(Protocol):
    """Protocol for LLM client dependency injection.

    The actual LLM client is injected by Team Builder.
    Uses tier="generate" at runtime.
    """

    async def generate(self, prompt: str) -> str:
        """Generate text from prompt.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Generated text response
        """
        ...


@dataclass
class ClassificationResult:
    """Result of lead type classification.

    Attributes:
        lead_id: UUID of the classified lead
        lead_type: Classified lead type
        confidence: Confidence score (0.0-1.0)
        reasoning: Explanation for classification
        error: Error message if classification failed
        classified_at: Timestamp of classification
    """

    lead_id: UUID
    lead_type: LeadType
    confidence: float
    reasoning: str
    error: Optional[str] = None
    classified_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary for caching on lead record.

        Returns:
            Dict representation for JSONB storage.
        """
        result = {
            "lead_type": self.lead_type.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "classified_at": self.classified_at.isoformat(),
        }

        if self.error:
            result["error"] = self.error

        return result


# Classification prompt template
CLASSIFICATION_PROMPT = """Classify this B2B lead into one of these categories based on their business profile:
- HEALTH_STORE: Helsekost butikk, natural products store, supplement retailer
- GYM_FITNESS: Treningssenter, gym, fitness center, sports facility
- ONLINE_RETAILER: Nettbutikk, e-commerce, online shop
- WELLNESS_CENTER: Spa, wellness, holistic health, massage therapy
- SPECIALTY_GROCER: Specialty food store, gourmet shop, organic market
- GENERIC: Cannot determine specific type or mixed business

Business data:
{enrichment_data}

Return ONLY valid JSON with these fields:
- category: One of the category names above (e.g., "HEALTH_STORE")
- confidence: Confidence level as integer 0-100
- reasoning: Brief explanation for the classification

Example response:
{{"category": "HEALTH_STORE", "confidence": 85, "reasoning": "Business focuses on organic health products and supplements"}}
"""


class LeadTypeClassifier:
    """LLM-based classifier for B2B lead types.

    Classifies leads into types for template selection using
    business insights from enrichment data.

    Uses tier="generate" (Sonnet) for quality classification.
    Accepts LLM client via dependency injection.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        """Initialize the classifier.

        Args:
            llm_client: LLM client for classification (injected)
            confidence_threshold: Minimum confidence for accepting classification
        """
        self._llm_client = llm_client
        self._confidence_threshold = confidence_threshold

    async def classify(
        self,
        lead_id: UUID,
        enrichment_data: dict[str, Any],
    ) -> ClassificationResult:
        """Classify a lead into a type based on enrichment data.

        Args:
            lead_id: UUID of the lead to classify
            enrichment_data: Lead's enrichment_data from database

        Returns:
            ClassificationResult with lead type and confidence
        """
        try:
            # Extract business insights
            business_insights = enrichment_data.get("business_insights", {})

            # Format prompt with enrichment data
            prompt = CLASSIFICATION_PROMPT.format(
                enrichment_data=json.dumps(business_insights, indent=2, ensure_ascii=False)
            )

            # Call LLM for classification
            response = await self._llm_client.generate(prompt)

            # Parse response
            result = self._parse_response(response)

            # Check confidence threshold
            confidence = result.get("confidence", 0) / 100.0  # Convert to 0-1 scale
            category = result.get("category", "GENERIC")
            reasoning = result.get("reasoning", "No reasoning provided")

            # Fallback to GENERIC if confidence too low
            if confidence < self._confidence_threshold:
                logger.info(
                    f"Classification confidence {confidence:.2f} below threshold "
                    f"{self._confidence_threshold:.2f}, falling back to GENERIC"
                )
                return ClassificationResult(
                    lead_id=lead_id,
                    lead_type=LeadType.GENERIC,
                    confidence=confidence,
                    reasoning=f"Low confidence classification: {reasoning}",
                )

            # Map category to LeadType
            lead_type = self._map_category_to_lead_type(category)

            return ClassificationResult(
                lead_id=lead_id,
                lead_type=lead_type,
                confidence=confidence,
                reasoning=reasoning,
            )

        except Exception as e:
            logger.error(f"Classification failed for lead {lead_id}: {e}")
            return ClassificationResult(
                lead_id=lead_id,
                lead_type=LeadType.GENERIC,
                confidence=0.0,
                reasoning="Classification failed",
                error=str(e),
            )

    def _parse_response(self, response: str) -> dict:
        """Parse LLM response as JSON.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If response is not valid JSON
        """
        # Clean response - remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON response: {e}")

    def _map_category_to_lead_type(self, category: str) -> LeadType:
        """Map category string to LeadType enum.

        Args:
            category: Category string from LLM response

        Returns:
            Corresponding LeadType enum value
        """
        category_upper = category.upper().strip()

        category_map = {
            "HEALTH_STORE": LeadType.HEALTH_STORE,
            "GYM_FITNESS": LeadType.GYM_FITNESS,
            "ONLINE_RETAILER": LeadType.ONLINE_RETAILER,
            "WELLNESS_CENTER": LeadType.WELLNESS_CENTER,
            "SPECIALTY_GROCER": LeadType.SPECIALTY_GROCER,
            "GENERIC": LeadType.GENERIC,
        }

        return category_map.get(category_upper, LeadType.GENERIC)
