"""Reddit Validator - checks EU compliance for research items.

Implements the validate stage of the Harvester Framework pipeline:
    Scanner → Harvester → Transformer → [Validator] → Publisher → Research Pool

The validator checks transformed research items against EU Health Claims
Regulation (EC 1924/2006) using the EUComplianceChecker.

Usage:
    validator = RedditValidator(compliance_checker)
    validated = await validator.validate(transformed_items)
"""

import logging
from typing import Optional

from teams.dawo.research import TransformedResearch, ComplianceStatus
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    OverallStatus,
)

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

    Uses the EUComplianceChecker to validate content against
    EU Health Claims Regulation (EC 1924/2006).

    Sets compliance_status based on check result:
        - COMPLIANT: Content passes compliance checks
        - WARNING: Borderline content, needs review
        - REJECTED: Content contains prohibited claims

    Configuration is injected via constructor - NEVER loads files directly.

    Attributes:
        _checker: EU Compliance Checker instance
    """

    def __init__(self, compliance_checker: EUComplianceChecker):
        """Initialize validator with injected compliance checker.

        Args:
            compliance_checker: EUComplianceChecker instance from Story 1.2
        """
        self._checker = compliance_checker

    async def validate(
        self,
        items: list[TransformedResearch],
    ) -> list[ValidatedResearch]:
        """Validate transformed items against EU compliance rules.

        Checks title and content of each item and sets compliance_status.

        Args:
            items: Transformed research items from transformer stage

        Returns:
            List of ValidatedResearch objects with compliance status set
        """
        logger.info("Validating %d items for EU compliance", len(items))

        validated: list[ValidatedResearch] = []
        stats = {"compliant": 0, "warning": 0, "rejected": 0}

        for item in items:
            try:
                result = await self._validate_single(item)
                validated.append(result)

                # Track statistics
                status = result.compliance_status
                if status == ComplianceStatus.COMPLIANT.value:
                    stats["compliant"] += 1
                elif status == ComplianceStatus.WARNING.value:
                    stats["warning"] += 1
                else:
                    stats["rejected"] += 1

            except Exception as e:
                logger.error(
                    "Failed to validate item '%s': %s",
                    item.title[:50],
                    e,
                )
                # Skip item on validation failure
                continue

        logger.info(
            "Validation complete: %d compliant, %d warnings, %d rejected",
            stats["compliant"],
            stats["warning"],
            stats["rejected"],
        )

        return validated

    async def _validate_single(
        self,
        item: TransformedResearch,
    ) -> ValidatedResearch:
        """Validate a single item.

        Args:
            item: Transformed research item

        Returns:
            ValidatedResearch with compliance status set
        """
        # Combine title and content for compliance check
        text_to_check = f"{item.title}\n\n{item.content}"

        # Check compliance
        check_result = await self._checker.check_content(text_to_check)

        # Map checker result to ComplianceStatus
        compliance_status = self._map_compliance_status(check_result.overall_status)

        logger.debug(
            "Validated '%s': %s",
            item.title[:30],
            compliance_status,
        )

        return ValidatedResearch(
            source=item.source.value if hasattr(item.source, "value") else str(item.source),
            title=item.title,
            content=item.content,
            url=item.url,
            tags=item.tags,
            source_metadata=item.source_metadata,
            created_at=item.created_at,
            compliance_status=compliance_status,
            score=item.score,
        )

    def _map_compliance_status(self, overall_status: OverallStatus) -> str:
        """Map EUComplianceChecker result to ComplianceStatus.

        Args:
            overall_status: Result from EUComplianceChecker

        Returns:
            ComplianceStatus value string
        """
        status_map = {
            OverallStatus.COMPLIANT: ComplianceStatus.COMPLIANT.value,
            OverallStatus.WARNING: ComplianceStatus.WARNING.value,
            OverallStatus.REJECTED: ComplianceStatus.REJECTED.value,
        }
        return status_map.get(overall_status, ComplianceStatus.WARNING.value)
