"""PubMed Validator - EU compliance validation for research items.

Implements the validator stage of the Harvester Framework:
    Scanner -> Harvester -> FindingSummarizer -> ClaimValidator -> Transformer -> [Validator] -> Publisher

The PubMedValidator:
    1. Takes ValidatedResearch list from transformer
    2. Uses ResearchComplianceValidator (Story 2.8) for compliance checking
    3. Sets compliance_status based on check result
    4. Preserves claim_potential tags for content team
    5. Returns validated items ready for publishing

Note: PubMed sources are treated as inherently citable scientific publications,
so prohibited claims are downgraded to WARNING (can cite study, not make claim).

Registration: team_spec.py as RegisteredService

Usage:
    # Created by Team Builder with injected dependencies
    validator = PubMedValidator(research_compliance_validator)

    # Execute validation
    validated = await validator.validate(transformed)
"""

import logging

from teams.dawo.research import TransformedResearch, ComplianceStatus
from teams.dawo.validators.research_compliance import ResearchComplianceValidator

from .schemas import ValidatedResearch


# Module logger
logger = logging.getLogger(__name__)


class ValidatorError(Exception):
    """Exception raised for validator errors.

    Attributes:
        message: Error description
        pmid: PMID of the article that failed
    """

    def __init__(
        self,
        message: str,
        pmid: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.pmid = pmid


class PubMedValidator:
    """PubMed Validator - EU compliance validation.

    Uses the ResearchComplianceValidator (Story 2.8) to validate content
    against EU Health Claims Regulation (EC 1924/2006).

    The ResearchComplianceValidator provides:
        - Citation detection (DOI, PMID, scientific URLs)
        - Source-specific rules (PubMed = always citable)
        - Citation-aware status adjustment

    PubMed-specific behavior:
        - PubMed sources are inherently citable scientific publications
        - REJECTED status is automatically downgraded to WARNING
        - Content can cite the study but cannot make direct health claims

    All dependencies are injected via constructor.

    Attributes:
        _compliance: Research Compliance Validator from Story 2.8
    """

    def __init__(self, research_compliance: ResearchComplianceValidator):
        """Initialize validator with injected dependencies.

        Args:
            research_compliance: ResearchComplianceValidator (Story 2.8)
        """
        self._compliance = research_compliance

    async def validate(
        self,
        items: list[ValidatedResearch],
    ) -> list[ValidatedResearch]:
        """Validate research items for EU compliance.

        Uses ResearchComplianceValidator for validation. PubMed sources
        receive special treatment as citable scientific publications.

        Args:
            items: List of ValidatedResearch from transformer

        Returns:
            List of ValidatedResearch with compliance_status set
        """
        if not items:
            return []

        logger.info("Validating %d research items", len(items))

        # Convert ValidatedResearch to TransformedResearch for validation
        transformed_items = self._convert_to_transformed(items)

        # Use batch validation for efficiency
        compliance_results = await self._compliance.validate_batch(transformed_items)

        # Convert back to scanner-specific ValidatedResearch
        validated: list[ValidatedResearch] = []
        compliant_count = 0
        warning_count = 0
        rejected_count = 0

        for result in compliance_results:
            scanner_result = ValidatedResearch(
                source=result.source,
                source_id=result.source_metadata.get("pmid", ""),
                title=result.title,
                content=result.content,
                summary=result.source_metadata.get("summary", result.content[:500]),
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
                compliant_count += 1
            elif result.compliance_status == ComplianceStatus.WARNING:
                warning_count += 1
            else:
                rejected_count += 1

        logger.info(
            "Validation complete: %d compliant, %d warnings, %d rejected",
            compliant_count,
            warning_count,
            rejected_count,
        )

        return validated

    def _convert_to_transformed(
        self,
        items: list[ValidatedResearch],
    ) -> list[TransformedResearch]:
        """Convert ValidatedResearch to TransformedResearch for validation.

        Args:
            items: List of ValidatedResearch

        Returns:
            List of TransformedResearch
        """
        from teams.dawo.research import ResearchSource

        transformed = []
        for item in items:
            transformed.append(
                TransformedResearch(
                    source=ResearchSource.PUBMED,
                    title=item.title,
                    content=item.content,
                    url=item.url,
                    tags=item.tags,
                    source_metadata=item.source_metadata,
                    score=item.score,
                    created_at=item.created_at,
                )
            )
        return transformed

    async def validate_batch(
        self,
        items: list[ValidatedResearch],
        batch_size: int = 10,
    ) -> list[ValidatedResearch]:
        """Validate items in batches (for rate limiting).

        Args:
            items: List of ValidatedResearch
            batch_size: Number of items per batch

        Returns:
            List of validated items
        """
        all_validated: list[ValidatedResearch] = []

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            logger.debug("Validating batch %d-%d", i, i + len(batch))

            validated = await self.validate(batch)
            all_validated.extend(validated)

        return all_validated
