"""Compliance Scorer - EU compliance status scoring.

Scores content based on EU compliance check results.
Maps OverallStatus to numeric scores per AC requirements.
"""

from dataclasses import dataclass
from typing import Protocol, Optional, Any

from teams.dawo.generators.content_quality.schemas import ComponentScore


class ComplianceCheckerProtocol(Protocol):
    """Protocol for EU Compliance Checker."""

    async def check_content(self, content: str) -> Any:
        """Check content for EU compliance."""
        ...


@dataclass
class ComplianceScorerConfig:
    """Configuration for compliance scoring.

    Attributes:
        weight: Weight of compliance in total score (default 0.25)
    """

    weight: float = 0.25


class ComplianceScorer:
    """Scores content based on EU compliance status.

    Maps compliance status to numeric scores:
    - COMPLIANT: 10.0 (full score)
    - WARNING: 8.0 (full - 2 per AC)
    - REJECTED: 0.0 (zero score)

    Attributes:
        compliance_checker: EU Compliance Checker for validation
        config: Scorer configuration
    """

    def __init__(
        self,
        compliance_checker: ComplianceCheckerProtocol,
        config: Optional[ComplianceScorerConfig] = None,
    ) -> None:
        """Initialize with compliance checker.

        Args:
            compliance_checker: EU Compliance Checker instance
            config: Optional scorer configuration
        """
        self._checker = compliance_checker
        self._config = config or ComplianceScorerConfig()

    async def score(
        self,
        content: str,
        precomputed_check: Optional[Any] = None,
    ) -> ComponentScore:
        """Score content for EU compliance.

        Uses pre-computed compliance check if available, otherwise
        runs compliance check.

        Args:
            content: Content text to score
            precomputed_check: Optional pre-computed ContentComplianceCheck

        Returns:
            ComponentScore with compliance scoring details
        """
        from teams.dawo.validators.eu_compliance import OverallStatus

        # Use pre-computed or run check
        if precomputed_check is not None:
            compliance = precomputed_check
        else:
            compliance = await self._checker.check_content(content)

        # Map status to score per AC: COMPLIANT=10, WARNING=8, REJECTED=0
        status_score_map = {
            OverallStatus.COMPLIANT: 10.0,
            OverallStatus.WARNING: 8.0,
            OverallStatus.REJECTED: 0.0,
        }
        raw_score = status_score_map.get(compliance.overall_status, 5.0)

        return ComponentScore(
            component="compliance",
            raw_score=raw_score,
            weight=self._config.weight,
            weighted_score=raw_score * self._config.weight,
            details={
                "status": compliance.overall_status.value,
                "compliance_score": compliance.compliance_score,
            },
        )
