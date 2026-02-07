"""NewsValidator for EU compliance validation.

Implements the validator stage of the Harvester Framework for news.
Validates article content against EU compliance rules using
ResearchComplianceValidator (Story 2.8).

Usage:
    validator = NewsValidator(research_compliance_validator)
    validated = await validator.validate(transformed_items)
"""

import logging

from teams.dawo.research import TransformedResearch
from teams.dawo.validators.research_compliance import ResearchComplianceValidator

from .schemas import ValidatedResearch, CategoryResult, PriorityScore

logger = logging.getLogger(__name__)


class ValidatorError(Exception):
    """Raised when validation fails."""

    pass


class NewsValidator:
    """Validator for news articles.

    Uses the ResearchComplianceValidator (Story 2.8) to validate content
    against EU Health Claims Regulation (EC 1924/2006).

    The ResearchComplianceValidator provides:
        - Citation detection (DOI, PMID, scientific URLs)
        - Source-specific rules
        - Citation-aware status adjustment

    Attributes:
        _compliance: Research Compliance Validator instance
    """

    def __init__(
        self,
        research_compliance: ResearchComplianceValidator,
    ) -> None:
        """Initialize validator.

        Args:
            research_compliance: ResearchComplianceValidator from Story 2.8
        """
        self._compliance = research_compliance

    async def validate(
        self,
        items: list[tuple[TransformedResearch, CategoryResult, PriorityScore]],
    ) -> list[ValidatedResearch]:
        """Validate transformed items against EU compliance.

        Uses ResearchComplianceValidator for validation with
        citation detection and source-specific rules.

        Args:
            items: List of (TransformedResearch, CategoryResult, PriorityScore) tuples

        Returns:
            List of ValidatedResearch with compliance_status set
        """
        # Extract just the research items for batch validation
        research_items = [research for research, _, _ in items]

        if not research_items:
            return []

        # Use batch validation for efficiency
        compliance_results = await self._compliance.validate_batch(research_items)

        # Convert to scanner-specific ValidatedResearch
        validated: list[ValidatedResearch] = []
        errors_count = 0

        for result in compliance_results:
            try:
                scanner_result = ValidatedResearch(
                    source=result.source,
                    title=result.title,
                    content=result.content,
                    url=result.url,
                    tags=result.tags,
                    source_metadata=result.source_metadata,
                    created_at=result.created_at,
                    compliance_status=result.compliance_status.value,
                    score=result.score,
                )
                validated.append(scanner_result)
            except Exception as e:
                errors_count += 1
                logger.warning("Failed to convert article %s: %s", result.url, e)

        logger.info(
            "Validated %d articles, %d failed",
            len(validated),
            errors_count,
        )
        return validated

    async def validate_batch(
        self,
        items: list[TransformedResearch],
    ) -> list[ValidatedResearch]:
        """Validate a batch of research items directly.

        Simpler interface for batch validation without category/priority tuples.

        Args:
            items: List of TransformedResearch items

        Returns:
            List of ValidatedResearch with compliance_status set
        """
        if not items:
            return []

        # Use batch validation for efficiency
        compliance_results = await self._compliance.validate_batch(items)

        # Convert to scanner-specific ValidatedResearch
        validated: list[ValidatedResearch] = []

        for result in compliance_results:
            scanner_result = ValidatedResearch(
                source=result.source,
                title=result.title,
                content=result.content,
                url=result.url,
                tags=result.tags,
                source_metadata=result.source_metadata,
                created_at=result.created_at,
                compliance_status=result.compliance_status.value,
                score=result.score,
            )
            validated.append(scanner_result)

        return validated
