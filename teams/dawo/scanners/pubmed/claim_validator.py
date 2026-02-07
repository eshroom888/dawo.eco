"""Claim Validator - LLM-powered EU Health Claims assessment.

Implements the claim validation stage of the Harvester Framework:
    Scanner -> Harvester -> FindingSummarizer -> [ClaimValidator] -> Transformer -> Validator -> Publisher

The ClaimValidator:
    1. Takes FindingSummary from summarizer
    2. Uses LLM (tier="generate") to assess content potential
    3. Cross-references with EU Health Claims context
    4. Tags content potential: citation_only, educational, trend_awareness, no_claim
    5. Returns ClaimValidationResult with usage guidance

Registration: team_spec.py with tier="generate" (maps to Sonnet at runtime)

Usage:
    # Created by Team Builder with injected dependencies
    validator = ClaimValidator(llm_client, compliance_checker)

    # Execute claim validation
    result = await validator.validate_claim_potential(summary)
"""

import json
import logging
from typing import Any, Optional

from .schemas import FindingSummary, ClaimValidationResult, ContentPotential
from .prompts import CLAIM_VALIDATION_PROMPT


# Module logger
logger = logging.getLogger(__name__)


class ClaimValidationError(Exception):
    """Exception raised for claim validation errors.

    Attributes:
        message: Error description
        compound: Compound that failed validation
    """

    def __init__(
        self,
        message: str,
        compound: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.compound = compound


class ClaimValidator:
    """LLM-powered EU Health Claims validator.

    Uses tier="generate" (Sonnet) for accurate claim assessment.
    Cross-references research findings with EU compliance rules.

    CRITICAL CONTEXT: There are currently ZERO approved EU health claims
    for functional mushrooms. All content using these findings CANNOT
    make health claims.

    Features:
        - Content potential categorization
        - EU claim status determination
        - Usage guidance generation
        - Standard caveat inclusion

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _llm: LLM client configured for tier="generate"
        _compliance: EU compliance checker (optional, for future integration)
    """

    def __init__(
        self,
        llm_client: Any,
        compliance_checker: Optional[Any] = None,
    ):
        """Initialize claim validator with injected dependencies.

        Args:
            llm_client: LLM client configured for tier="generate"
            compliance_checker: Optional EU compliance checker (Story 1.2)
        """
        self._llm = llm_client
        self._compliance = compliance_checker

    async def validate_claim_potential(
        self,
        summary: FindingSummary,
    ) -> ClaimValidationResult:
        """Validate research finding against EU Health Claims context.

        Args:
            summary: FindingSummary from summarizer

        Returns:
            ClaimValidationResult with usage guidance

        Raises:
            ClaimValidationError: If validation fails
        """
        # Format prompt
        prompt = CLAIM_VALIDATION_PROMPT.format(
            compound=summary.compound_studied,
            effect=summary.effect_measured,
            summary=summary.key_findings,
            strength=summary.study_strength,
        )

        try:
            # Call LLM
            response = await self._llm.generate(
                prompt=prompt,
                max_tokens=600,
            )

            # Parse response
            return self._parse_response(response)

        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse LLM response as JSON for %s: %s",
                summary.compound_studied,
                e,
            )
            return self._default_result()
        except Exception as e:
            logger.error(
                "Claim validation failed for %s: %s",
                summary.compound_studied,
                e,
            )
            raise ClaimValidationError(
                f"Failed to validate: {e}",
                compound=summary.compound_studied,
            ) from e

    async def validate_batch(
        self,
        summaries: dict[str, FindingSummary],
    ) -> dict[str, ClaimValidationResult]:
        """Validate multiple summaries.

        Args:
            summaries: Dict mapping PMID to FindingSummary

        Returns:
            Dict mapping PMID to ClaimValidationResult
        """
        results: dict[str, ClaimValidationResult] = {}

        for pmid, summary in summaries.items():
            try:
                result = await self.validate_claim_potential(summary)
                results[pmid] = result
            except ClaimValidationError as e:
                logger.warning("Claim validation failed for %s: %s", pmid, e)
                results[pmid] = self._default_result()

        return results

    def _parse_response(self, response: str) -> ClaimValidationResult:
        """Parse LLM response into ClaimValidationResult.

        Args:
            response: Raw LLM response text

        Returns:
            ClaimValidationResult parsed from response
        """
        # Handle potential markdown code blocks
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        data = json.loads(text)

        # Map string to ContentPotential enum
        potential_tags = self._parse_content_potential(
            data.get("content_potential", ["no_claim"])
        )

        return ClaimValidationResult(
            content_potential=potential_tags,
            usage_guidance=data.get(
                "usage_guidance",
                "Cannot make health claims. Can cite study for educational purposes only.",
            ),
            eu_claim_status=data.get("eu_claim_status", "no_approved_claim"),
            caveat=data.get(
                "caveat",
                "Can cite study but NOT claim treatment/prevention/cure",
            ),
            can_cite_study=data.get("can_cite_study", True),
            can_make_claim=data.get("can_make_claim", False),
        )

    def _parse_content_potential(
        self,
        potential_list: list[str],
    ) -> list[ContentPotential]:
        """Parse content potential strings to enum values.

        Args:
            potential_list: List of content potential strings

        Returns:
            List of ContentPotential enum values
        """
        mapping = {
            "citation_only": ContentPotential.CITATION_ONLY,
            "educational": ContentPotential.EDUCATIONAL,
            "trend_awareness": ContentPotential.TREND_AWARENESS,
            "no_claim": ContentPotential.NO_CLAIM,
        }

        result = []
        for p in potential_list:
            if p.lower() in mapping:
                result.append(mapping[p.lower()])

        # Default to NO_CLAIM if empty
        return result if result else [ContentPotential.NO_CLAIM]

    def _default_result(self) -> ClaimValidationResult:
        """Create default ClaimValidationResult for failed validations.

        Returns:
            Default ClaimValidationResult with conservative settings
        """
        return ClaimValidationResult(
            content_potential=[ContentPotential.EDUCATIONAL],
            usage_guidance=(
                "Cannot make health claims. Can cite study for educational purposes only. "
                "Functional mushrooms have no approved EU health claims."
            ),
            eu_claim_status="no_approved_claim",
            caveat="Can cite study but NOT claim treatment/prevention/cure",
            can_cite_study=True,
            can_make_claim=False,
        )
