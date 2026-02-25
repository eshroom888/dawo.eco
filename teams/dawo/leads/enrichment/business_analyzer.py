"""LLM-based Business Analyzer for Lead Enrichment.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 3: Implement LLM-based Business Analyzer

Analyzes website content using LLM to extract:
- Business focus areas
- Target demographics
- Product categories
- Wellness positioning
- Personalization hooks for outreach
"""

import logging
from typing import Any, Optional, Protocol

from teams.dawo.leads.enrichment.config import EnrichmentConfig
from teams.dawo.leads.enrichment.schemas import (
    BusinessInsights,
    PersonalizationHook,
    PersonalizationHookType,
)


logger = logging.getLogger(__name__)


# Prompts for LLM analysis (tier="generate" maps to Sonnet at runtime)
BUSINESS_ANALYSIS_PROMPT = """Analyze this business website content to extract key insights for B2B outreach.

Company: {company_name}
Content:
{website_content}

Extract:
1. Business focus areas (what they specialize in)
2. Target customer demographics
3. Product categories they carry
4. Wellness/health positioning strength (weak/moderate/strong)
5. Any mushroom, adaptogen, or supplement offerings mentioned

Return as JSON with these exact fields:
{{
    "focus_areas": ["area1", "area2", ...],
    "target_demographics": "description or null",
    "product_categories": ["category1", "category2", ...],
    "wellness_positioning": "weak" | "moderate" | "strong" | null
}}"""

PERSONALIZATION_PROMPT = """Given these business insights, identify personalization hooks for a DAWO mushroom supplement outreach.

Business Insights:
{insights}

Lead Data:
{lead_data}

Identify 2-4 personalization hooks that would make outreach relevant.
Each hook should be specific and actionable.

Return as JSON list with type and detail fields:
[
    {{"type": "competitor|focus|audience|location|product|values|growth", "detail": "specific detail"}},
    ...
]

Hook types:
- competitor: They carry competitor products
- focus: Business focus aligns with DAWO values
- audience: Target audience match
- location: Geographic relevance (Nordic/Scandinavian)
- product: Product category fit
- values: Shared values (organic, sustainable, natural)
- growth: Business expansion indicators"""


class LLMClientProtocol(Protocol):
    """Protocol for LLM client dependency injection.

    Agents use tier="generate" which maps to Sonnet at runtime.
    NEVER use model names like "sonnet" in code.
    """

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate structured JSON response from LLM.

        Args:
            prompt: User prompt with content to analyze
            system_prompt: Optional system context

        Returns:
            Parsed JSON response from LLM
        """
        ...


class BusinessAnalyzer:
    """LLM-based business analyzer for lead enrichment.

    Analyzes website content to extract business insights
    and identify personalization hooks for outreach.

    Accepts LLM client via dependency injection.
    Uses tier="generate" for all LLM operations.

    Attributes:
        _llm: LLM client for analysis
        _config: Enrichment configuration
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        config: EnrichmentConfig,
    ) -> None:
        """Initialize the business analyzer.

        Args:
            llm_client: LLM client (tier="generate")
            config: Enrichment configuration
        """
        self._llm = llm_client
        self._config = config

    async def analyze_business(
        self,
        content: str,
        company: str,
    ) -> BusinessInsights:
        """Analyze website content to extract business insights.

        Uses LLM to understand:
        - Business focus areas
        - Target demographics
        - Product categories
        - Wellness positioning

        Args:
            content: Extracted website text content
            company: Company name

        Returns:
            BusinessInsights with extracted data
        """
        if not content or not company:
            return BusinessInsights()

        prompt = BUSINESS_ANALYSIS_PROMPT.format(
            company_name=company,
            website_content=content[:5000],  # Limit context size
        )

        try:
            response = await self._llm.generate_json(prompt)

            return BusinessInsights(
                focus_areas=response.get("focus_areas", []),
                target_demographics=response.get("target_demographics"),
                product_categories=response.get("product_categories", []),
                wellness_positioning=response.get("wellness_positioning"),
            )

        except Exception as e:
            logger.warning(f"LLM business analysis failed: {e}")
            return BusinessInsights()

    async def identify_hooks(
        self,
        insights: BusinessInsights,
        lead_data: dict[str, Any],
    ) -> list[PersonalizationHook]:
        """Identify personalization hooks for outreach.

        Analyzes business insights to find relevant hooks:
        - Competitor product presence
        - Organic/wellness focus alignment
        - Nordic/Scandinavian audience
        - Product category fit

        Args:
            insights: Business insights from analysis
            lead_data: Lead data dictionary

        Returns:
            List of personalization hooks
        """
        if not insights.focus_areas and not insights.product_categories:
            return []

        prompt = PERSONALIZATION_PROMPT.format(
            insights=insights.to_dict(),
            lead_data=lead_data,
        )

        try:
            response = await self._llm.generate_json(prompt)

            hooks = []
            for hook_data in response if isinstance(response, list) else []:
                hook_type_str = hook_data.get("type", "focus")
                detail = hook_data.get("detail", "")

                # Map string to enum
                try:
                    hook_type = PersonalizationHookType(hook_type_str.lower())
                except ValueError:
                    hook_type = PersonalizationHookType.FOCUS

                hooks.append(PersonalizationHook(
                    hook_type=hook_type,
                    detail=detail,
                ))

            return hooks

        except Exception as e:
            logger.warning(f"LLM hook identification failed: {e}")
            return []

    def detect_existing_customer(self, content: Optional[str]) -> bool:
        """Check if business already carries DAWO products.

        Searches for DAWO brand mentions in website content.
        Uses keywords from configuration.

        Args:
            content: Website text content

        Returns:
            True if DAWO products detected
        """
        if not content:
            return False

        content_lower = content.lower()

        for keyword in self._config.dawo_product_keywords:
            if keyword.lower() in content_lower:
                logger.debug(f"DAWO keyword detected: {keyword}")
                return True

        return False
