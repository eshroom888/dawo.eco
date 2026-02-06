"""Compliance adjustment component for research items.

Adjusts final scores based on EU compliance status:
- COMPLIANT: +1 bonus (capped at 10)
- WARNING: No adjustment
- REJECTED: Final score forced to 0

This is applied AFTER the weighted average is calculated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Compliance adjustment constants
COMPLIANT_BONUS: float = 1.0
MAX_FINAL_SCORE: float = 10.0
MIN_FINAL_SCORE: float = 0.0


@dataclass
class ComplianceAdjustment:
    """Result from compliance adjustment calculation.

    Attributes:
        adjustment: The score adjustment to apply (+1 for COMPLIANT, 0 otherwise).
        is_rejected: True if item should have score forced to 0.
        notes: Explanation of the adjustment.
    """

    adjustment: float
    is_rejected: bool
    notes: str


class ComplianceAdjuster:
    """Adjusts scores based on EU compliance status.

    Applied after weighted average calculation:
    - COMPLIANT: +1 bonus (incentivizes compliant content)
    - WARNING: No adjustment (content needs review)
    - REJECTED: Score forced to 0 (prohibited content)

    This ensures that rejected content never surfaces, while
    compliant content gets a small boost.
    """

    def adjust(self, item: dict[str, Any]) -> ComplianceAdjustment:
        """Calculate compliance adjustment for a research item.

        Args:
            item: Dictionary with 'compliance_status' field.

        Returns:
            ComplianceAdjustment with adjustment value and rejection flag.
        """
        compliance_status = item.get("compliance_status", "WARNING")

        if compliance_status == "COMPLIANT":
            logger.debug("Compliance: COMPLIANT, +1 bonus")
            return ComplianceAdjustment(
                adjustment=COMPLIANT_BONUS,
                is_rejected=False,
                notes="COMPLIANT status: +1 bonus",
            )
        elif compliance_status == "REJECTED":
            logger.debug("Compliance: REJECTED, score forced to 0")
            return ComplianceAdjustment(
                adjustment=0.0,
                is_rejected=True,
                notes="REJECTED status: score forced to 0",
            )
        else:  # WARNING or unknown
            logger.debug("Compliance: WARNING, no adjustment")
            return ComplianceAdjustment(
                adjustment=0.0,
                is_rejected=False,
                notes="WARNING status: no adjustment",
            )

    def apply_adjustment(
        self, base_score: float, adjustment: ComplianceAdjustment
    ) -> float:
        """Apply compliance adjustment to a base score.

        Args:
            base_score: The weighted average score before adjustment.
            adjustment: The ComplianceAdjustment to apply.

        Returns:
            Final score (0-10).
        """
        if adjustment.is_rejected:
            return MIN_FINAL_SCORE

        final_score = base_score + adjustment.adjustment
        return min(final_score, MAX_FINAL_SCORE)
