"""Violation Classifier (Story 6-7, Task 5).

Classifies extracted health claims against EU regulations.
Three classification paths: auto-violation, register-check, and suspect.
"""

import logging
from typing import Sequence

from core.regulatory.models import ExtractedHealthClaim, HealthClaim
from teams.dawo.scanners.violation_detection.config import ViolationDetectionConfig
from teams.dawo.scanners.violation_detection.schemas import ViolationResult

logger = logging.getLogger(__name__)


class ViolationClassifier:
    """Classifies extracted claims against EU Health Claims regulations.

    Three classification paths:
    - Auto-violation: Treatment claims are ALWAYS prohibited (no register check).
    - Register-check: Prevention/enhancement claims cross-reference EU register.
    - Suspect: General wellness claims flagged for operator review.

    Args:
        config: ViolationDetectionConfig with category rules.
    """

    def __init__(self, config: ViolationDetectionConfig) -> None:
        self._config = config

    def classify(
        self,
        claim: ExtractedHealthClaim,
        authorized_claims: Sequence[HealthClaim],
        competitor_name: str,
        source_url: str,
    ) -> ViolationResult:
        """Classify a single extracted claim against EU regulations.

        Args:
            claim: The extracted health claim to evaluate.
            authorized_claims: EU register authorized claims for cross-reference.
            competitor_name: Name of the competitor.
            source_url: URL of the competitor content.

        Returns:
            ViolationResult with classification details.
        """
        category = claim.claim_category

        # Path 1: Auto-violation (treatment claims)
        if category in self._config.auto_violation_categories:
            return self._auto_violation(claim, competitor_name, source_url)

        # Path 2: Register-check (prevention/enhancement claims)
        if category in self._config.register_check_categories:
            return self._register_check(
                claim, authorized_claims, competitor_name, source_url
            )

        # Path 3: Suspect (general_wellness claims)
        if category in self._config.suspect_categories:
            return self._suspect(claim, competitor_name, source_url)

        # Fallback: unknown category → suspect
        logger.warning(
            "Unknown claim category '%s' for claim %s, classifying as suspect",
            category,
            claim.id,
        )
        return self._suspect(claim, competitor_name, source_url)

    def _auto_violation(
        self,
        claim: ExtractedHealthClaim,
        competitor_name: str,
        source_url: str,
    ) -> ViolationResult:
        """Auto-violation path for prohibited categories (e.g. treatment)."""
        category = claim.claim_category
        severity = self._config.severity_mapping[category]
        regulation = self._config.regulation_mapping[category]

        reasoning = (
            f"{category.replace('_', ' ').title()} claim '{claim.claim_text}' "
            f"is prohibited under {regulation}. Functional mushroom products "
            f"have ZERO authorized health claims."
        )

        return ViolationResult(
            extracted_claim_id=claim.id,
            claim_text=claim.claim_text,
            claim_category=category,
            confidence_score=claim.confidence_score,
            violation_status="violation",
            severity=severity,
            regulation_article=regulation,
            violation_type=f"unauthorized_{category}_claim",
            detection_reasoning=reasoning,
            authorized_claims_checked=0,
            nearest_authorized_claim=None,
            competitor_name=competitor_name,
            source_url=source_url,
            evidence_status="pending_collection",
        )

    def _register_check(
        self,
        claim: ExtractedHealthClaim,
        authorized_claims: Sequence[HealthClaim],
        competitor_name: str,
        source_url: str,
    ) -> ViolationResult:
        """Register-check path for prevention/enhancement claims."""
        category = claim.claim_category
        severity = self._config.severity_mapping[category]
        regulation = self._config.regulation_mapping[category]

        substance_keywords = self._extract_substance_keywords(claim)
        nearest = self._find_nearest_authorized_claim(
            substance_keywords, authorized_claims
        )

        reasoning = (
            f"No authorized EU health claim found for substance "
            f"'{', '.join(substance_keywords) if substance_keywords else 'unknown'}' "
            f"under {regulation}. Checked {len(authorized_claims)} authorized claims."
        )

        return ViolationResult(
            extracted_claim_id=claim.id,
            claim_text=claim.claim_text,
            claim_category=category,
            confidence_score=claim.confidence_score,
            violation_status="violation",
            severity=severity,
            regulation_article=regulation,
            violation_type=f"unauthorized_{category}_claim",
            detection_reasoning=reasoning,
            authorized_claims_checked=len(authorized_claims),
            nearest_authorized_claim=nearest,
            competitor_name=competitor_name,
            source_url=source_url,
            evidence_status="pending_collection",
        )

    def _suspect(
        self,
        claim: ExtractedHealthClaim,
        competitor_name: str,
        source_url: str,
    ) -> ViolationResult:
        """Suspect path for borderline wellness claims."""
        category = claim.claim_category
        severity = self._config.severity_mapping.get(category, "low")
        regulation = self._config.regulation_mapping.get(
            category, "EC 1924/2006 Art. 13.1"
        )

        reasoning = (
            f"Borderline wellness claim. May be permitted with qualifying "
            f"language but requires operator review under {regulation}."
        )

        return ViolationResult(
            extracted_claim_id=claim.id,
            claim_text=claim.claim_text,
            claim_category=category,
            confidence_score=claim.confidence_score,
            violation_status="suspect",
            severity=severity,
            regulation_article=regulation,
            violation_type=f"borderline_{category}_claim",
            detection_reasoning=reasoning,
            authorized_claims_checked=0,
            nearest_authorized_claim=None,
            competitor_name=competitor_name,
            source_url=source_url,
            evidence_status="pending_collection",
        )

    def _find_nearest_authorized_claim(
        self,
        substance_keywords: list[str],
        authorized_claims: Sequence[HealthClaim],
    ) -> str | None:
        """Find closest matching authorized claim by substance keyword.

        Args:
            substance_keywords: Extracted substance keywords from claim.
            authorized_claims: EU register authorized claims.

        Returns:
            Formatted claim text if match found, None otherwise.
        """
        for keyword in substance_keywords:
            keyword_lower = keyword.lower()
            for ac in authorized_claims:
                if keyword_lower in ac.substance.lower():
                    return f"{ac.substance}: {ac.claim_text[:200]}"
        return None

    def _extract_substance_keywords(
        self, claim: ExtractedHealthClaim
    ) -> list[str]:
        """Extract substance keywords from claim text and context.

        Cross-references with configured mushroom_substances list.

        Args:
            claim: The extracted health claim.

        Returns:
            List of matched substance keywords.
        """
        text = (
            f"{claim.claim_text} {claim.surrounding_context or ''}"
        ).lower()

        matched = []
        for substance in self._config.mushroom_substances:
            if substance.lower() in text:
                matched.append(substance)

        return matched


__all__ = [
    "ViolationClassifier",
]
