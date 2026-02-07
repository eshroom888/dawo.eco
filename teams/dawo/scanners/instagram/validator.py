"""Instagram Validator - EU compliance validation.

Implements the validate stage of the Harvester Framework:
    Scanner -> Harvester -> ThemeExtractor -> ClaimDetector -> Transformer -> [Validator] -> Scorer -> Publisher -> Research Pool

The InstagramValidator:
    1. Takes transformed research items
    2. Uses ResearchComplianceValidator (Story 2.8) for compliance checking
    3. Sets compliance_status based on result
    4. Preserves cleanmarket_flag for Epic 6

Registration: team_spec.py as RegisteredService

Usage:
    # Created by Team Builder with injected dependencies
    validator = InstagramValidator(research_compliance_validator)

    # Execute validate stage
    validated = await validator.validate(transformed_items)
"""

import logging

from teams.dawo.research import ComplianceStatus, TransformedResearch
from teams.dawo.validators.research_compliance import ResearchComplianceValidator

from .schemas import ValidatedResearch


# Module logger
logger = logging.getLogger(__name__)


class ValidatorError(Exception):
    """Exception raised for validator-level errors.

    Attributes:
        message: Error description
        partial_results: Any items validated before error
    """

    def __init__(
        self,
        message: str,
        partial_results: list | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.partial_results = partial_results or []


class InstagramValidator:
    """Instagram Validator - EU compliance validation.

    Uses the ResearchComplianceValidator (Story 2.8) to validate content
    against EU Health Claims Regulation (EC 1924/2006).

    The ResearchComplianceValidator provides:
        - Citation detection (DOI, PMID, scientific URLs)
        - Source-specific rules (stricter for social sources like Instagram)
        - Citation-aware status adjustment

    Features:
        - EU Health Claims Regulation compliance checking
        - Compliance status assignment (COMPLIANT, WARNING, REJECTED)
        - CleanMarket flag preservation for Epic 6
        - Validation statistics logging

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _compliance: Research Compliance Validator instance
    """

    def __init__(self, research_compliance: ResearchComplianceValidator):
        """Initialize validator with injected dependencies.

        Args:
            research_compliance: ResearchComplianceValidator from Story 2.8
        """
        self._compliance = research_compliance

    async def validate(
        self,
        items: list[TransformedResearch],
    ) -> list[ValidatedResearch]:
        """Validate transformed research items for EU compliance.

        Uses ResearchComplianceValidator for batch validation with
        citation detection and source-specific rules.

        Args:
            items: List of transformed research items

        Returns:
            List of ValidatedResearch with compliance_status set
        """
        logger.info("Starting validation for %d items", len(items))

        # Use batch validation for efficiency
        compliance_results = await self._compliance.validate_batch(items)

        # Convert to scanner-specific ValidatedResearch
        validated: list[ValidatedResearch] = []
        stats = {"compliant": 0, "warning": 0, "rejected": 0, "cleanmarket_flagged": 0}

        # Build a map of original items by title for metadata lookup
        original_items = {item.title: item for item in items}

        for result in compliance_results:
            # Get original item for cleanmarket flag detection
            original = original_items.get(result.title)
            detected_claims = []
            if original and original.source_metadata:
                detected_claims = original.source_metadata.get("detected_claims", [])

            cleanmarket_flag = len(detected_claims) > 0

            scanner_result = ValidatedResearch(
                source=result.source,
                title=result.title,
                content=result.content,
                url=result.url,
                tags=result.tags,
                source_metadata=result.source_metadata,
                created_at=result.created_at,
                compliance_status=result.compliance_status.value,
                cleanmarket_flag=cleanmarket_flag,
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

            if cleanmarket_flag:
                stats["cleanmarket_flagged"] += 1

        logger.info(
            "Validation complete: %d compliant, %d warnings, %d rejected, %d flagged for CleanMarket",
            stats["compliant"],
            stats["warning"],
            stats["rejected"],
            stats["cleanmarket_flagged"],
        )

        return validated

    async def validate_single(
        self,
        item: TransformedResearch,
    ) -> ValidatedResearch:
        """Validate a single item - convenience method.

        Args:
            item: Transformed research item

        Returns:
            ValidatedResearch with compliance_status set
        """
        results = await self.validate([item])
        if results:
            return results[0]
        raise ValidatorError("Failed to validate item")
