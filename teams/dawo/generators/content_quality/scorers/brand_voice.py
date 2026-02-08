"""Brand Voice Scorer - Brand voice alignment scoring.

Scores content based on brand voice validation results.
Maps ValidationStatus to numeric scores.
"""

from dataclasses import dataclass
from typing import Protocol, Optional, Any

from teams.dawo.generators.content_quality.schemas import ComponentScore


class BrandValidatorProtocol(Protocol):
    """Protocol for Brand Voice Validator."""

    async def validate_content(self, content: str) -> Any:
        """Validate content for brand voice alignment."""
        ...


@dataclass
class BrandVoiceScorerConfig:
    """Configuration for brand voice scoring.

    Attributes:
        weight: Weight of brand voice in total score (default 0.20)
    """

    weight: float = 0.20


class BrandVoiceScorer:
    """Scores content based on brand voice alignment.

    Maps validation status to numeric scores:
    - PASS: 10.0 (full alignment)
    - NEEDS_REVISION: 6.0 (partial alignment)
    - FAIL: 2.0 (poor alignment)

    Attributes:
        brand_validator: Brand Voice Validator for validation
        config: Scorer configuration
    """

    def __init__(
        self,
        brand_validator: BrandValidatorProtocol,
        config: Optional[BrandVoiceScorerConfig] = None,
    ) -> None:
        """Initialize with brand validator.

        Args:
            brand_validator: Brand Voice Validator instance
            config: Optional scorer configuration
        """
        self._validator = brand_validator
        self._config = config or BrandVoiceScorerConfig()

    async def score(
        self,
        content: str,
        precomputed_validation: Optional[Any] = None,
    ) -> ComponentScore:
        """Score content for brand voice alignment.

        Uses pre-computed brand validation if available, otherwise
        runs brand validation.

        Args:
            content: Content text to score
            precomputed_validation: Optional pre-computed BrandValidationResult

        Returns:
            ComponentScore with brand voice scoring details
        """
        from teams.dawo.validators.brand_voice import ValidationStatus

        # Use pre-computed or run validation
        if precomputed_validation is not None:
            validation = precomputed_validation
        else:
            validation = await self._validator.validate_content(content)

        # Map status to score: PASS=10, NEEDS_REVISION=6, FAIL=2
        status_score_map = {
            ValidationStatus.PASS: 10.0,
            ValidationStatus.NEEDS_REVISION: 6.0,
            ValidationStatus.FAIL: 2.0,
        }
        raw_score = status_score_map.get(validation.status, 5.0)

        return ComponentScore(
            component="brand_voice",
            raw_score=raw_score,
            weight=self._config.weight,
            weighted_score=raw_score * self._config.weight,
            details={
                "status": validation.status.value,
                "brand_score": validation.brand_score,
                "authenticity_score": validation.authenticity_score,
            },
        )
