"""Reddit Validator - checks EU compliance for research items.

Implements the validate stage of the Harvester Framework pipeline:
    Scanner → Harvester → Transformer → [Validator] → Publisher → Research Pool

The validator checks transformed research items against EU Health Claims
Regulation (EC 1924/2006) using the ResearchComplianceValidator (Story 2.8).

Usage:
    validator = RedditValidator(research_compliance_validator)
    validated = await validator.validate(transformed_items)
"""

import logging

from teams.dawo.research import TransformedResearch, ComplianceStatus
from teams.dawo.validators.research_compliance import ResearchComplianceValidator

from .schemas import ValidatedResearch


# Module logger
logger = logging.getLogger(__name__)


class ValidatorError(Exception):
    """Exception raised for validator-level errors.

    Attributes:
        message: Error description
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class RedditValidator:
    """Reddit Validator - EU compliance checking for research items.

    Uses the ResearchComplianceValidator (Story 2.8) to validate content
    against EU Health Claims Regulation (EC 1924/2006).

    The ResearchComplianceValidator provides:
        - Citation detection (DOI, PMID, scientific URLs)
        - Source-specific rules (stricter for social sources)
        - Citation-aware status adjustment

    Sets compliance_status based on check result:
        - COMPLIANT: Content passes compliance checks
        - WARNING: Borderline content, needs review
        - REJECTED: Content contains prohibited claims

    Configuration is injected via constructor - NEVER loads files directly.

    Attributes:
        _compliance: Research Compliance Validator instance
    """

    def __init__(self, research_compliance: ResearchComplianceValidator):
        """Initialize validator with injected research compliance validator.

        Args:
            research_compliance: ResearchComplianceValidator from Story 2.8
        """
        self._compliance = research_compliance

    async def validate(
        self,
        items: list[TransformedResearch],
    ) -> list[ValidatedResearch]:
        """Validate transformed items against EU compliance rules.

        Uses ResearchComplianceValidator for batch validation with
        citation detection and source-specific rules.

        Args:
            items: Transformed research items from transformer stage

        Returns:
            List of ValidatedResearch objects with compliance status set
        """
        logger.info("Validating %d items for EU compliance", len(items))

        # Use batch validation for efficiency
        compliance_results = await self._compliance.validate_batch(items)

        # Convert to scanner-specific ValidatedResearch
        validated: list[ValidatedResearch] = []
        stats = {"compliant": 0, "warning": 0, "rejected": 0}

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

            # Track statistics
            if result.compliance_status == ComplianceStatus.COMPLIANT:
                stats["compliant"] += 1
            elif result.compliance_status == ComplianceStatus.WARNING:
                stats["warning"] += 1
            else:
                stats["rejected"] += 1

        logger.info(
            "Validation complete: %d compliant, %d warnings, %d rejected",
            stats["compliant"],
            stats["warning"],
            stats["rejected"],
        )

        return validated
