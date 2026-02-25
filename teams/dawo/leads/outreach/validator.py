"""Outreach Validator for Brand Voice Compliance.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides validation of outreach drafts:
- OutreachValidator: Main validator class
- ValidationResult: Validation output
- Brand voice compliance checking
- Forbidden pattern detection
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from teams.dawo.leads.outreach.schemas import OutreachDraft


logger = logging.getLogger(__name__)


# Forbidden patterns in outreach emails
# These indicate generic or pushy sales language
FORBIDDEN_PATTERNS = [
    # Generic openers
    r"Til hvem det måtte gjelde",
    r"Kjære mottaker",
    r"Vi er et selskap som",
    r"Dette er en forespørsel",

    # Pushy sales language
    r"Kjøp nå!",
    r"Begrenset tilbud",
    r"Ikke gå glipp av",
    r"Eksklusivt tilbud",
    r"Siste sjanse",
    r"Handle raskt",

    # Mass-mail indicators
    r"Hvis dette ikke er relevant",
    r"videresendt til riktig person",
    r"Avmeld deg her",
    r"Klikk her for å avmelde",
]


# Compiled regex patterns for efficiency
FORBIDDEN_REGEX = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in FORBIDDEN_PATTERNS
]


class BrandValidatorProtocol(Protocol):
    """Protocol for Brand Voice Validator dependency injection."""

    async def validate(self, content: str) -> dict[str, Any]:
        """Validate content against brand voice.

        Args:
            content: Text content to validate

        Returns:
            Dict with: valid (bool), score (float), issues (list)
        """
        ...


@dataclass
class ValidationResult:
    """Result of outreach draft validation.

    Attributes:
        is_valid: Whether draft passes all checks
        brand_voice_score: Score from brand voice validator (0-1)
        generic_language_check: Whether generic language check passed
        issues: List of validation issues found
        suggestions: List of improvement suggestions
    """

    is_valid: bool
    brand_voice_score: float = 0.0
    generic_language_check: bool = True
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage.

        Returns:
            Dict representation.
        """
        return {
            "is_valid": self.is_valid,
            "brand_voice_score": self.brand_voice_score,
            "generic_language_check": self.generic_language_check,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


class OutreachValidator:
    """Validator for outreach draft compliance.

    Validates drafts against:
    - Brand voice guidelines
    - Forbidden patterns (generic/pushy language)
    - Norwegian language requirements

    Accepts BrandVoiceValidator via dependency injection.
    """

    def __init__(self, brand_validator: BrandValidatorProtocol) -> None:
        """Initialize the validator.

        Args:
            brand_validator: Brand voice validator (injected)
        """
        self._brand_validator = brand_validator

    async def validate(self, draft: OutreachDraft) -> ValidationResult:
        """Validate an outreach draft.

        Args:
            draft: OutreachDraft to validate

        Returns:
            ValidationResult with validation status and details
        """
        issues = []
        suggestions = []

        # Check for forbidden patterns
        pattern_issues = self._check_forbidden_patterns(draft.body)
        issues.extend(pattern_issues)

        if pattern_issues:
            suggestions.append("Fjern generiske eller aggressive salgsfraser")

        # Call brand voice validator
        try:
            brand_result = await self._brand_validator.validate(draft.body)
            brand_valid = brand_result.get("valid", False)
            brand_score = brand_result.get("score", 0.0)
            brand_issues = brand_result.get("issues", [])

            if not brand_valid:
                issues.extend(brand_issues)
                suggestions.append("Juster tonen for å matche DAWO merkevare")

        except Exception as e:
            logger.error(f"Brand validator error: {e}")
            brand_valid = True  # Don't fail on validator error
            brand_score = 0.5
            issues.append(f"Brand validation error: {str(e)}")

        # Check word count
        word_count = len(draft.body.split())
        if word_count < 150:
            issues.append(f"Draft is too short ({word_count} words, minimum 150)")
            suggestions.append("Utvid innholdet med mer informasjon om produktene")
        elif word_count > 250:
            issues.append(f"Draft is too long ({word_count} words, maximum 250)")
            suggestions.append("Forkort innholdet mens du beholder nøkkelpunktene")

        # Check personalization
        if draft.personalization_score < 2:
            issues.append("Insufficient personalization (minimum 2 tokens)")
            suggestions.append("Legg til flere personlige referanser til deres virksomhet")

        # Determine overall validity
        generic_language_check = len(pattern_issues) == 0
        is_valid = (
            len(issues) == 0
            and brand_valid
            and generic_language_check
        )

        return ValidationResult(
            is_valid=is_valid,
            brand_voice_score=brand_score,
            generic_language_check=generic_language_check,
            issues=issues,
            suggestions=suggestions,
        )

    def _check_forbidden_patterns(self, text: str) -> list[str]:
        """Check text for forbidden patterns.

        Args:
            text: Text to check

        Returns:
            List of issues found
        """
        issues = []

        for i, pattern in enumerate(FORBIDDEN_REGEX):
            if pattern.search(text):
                issues.append(f"Forbidden pattern detected: {FORBIDDEN_PATTERNS[i]}")

        return issues

    def suggest_improvements(self, result: ValidationResult) -> list[str]:
        """Generate improvement suggestions based on validation result.

        Args:
            result: ValidationResult to analyze

        Returns:
            List of improvement suggestions
        """
        suggestions = list(result.suggestions)

        if not result.generic_language_check:
            suggestions.append("Bruk mer personlig og spesifikk språk")
            suggestions.append("Referer til spesifikke detaljer om deres virksomhet")

        if result.brand_voice_score < 0.7:
            suggestions.append("Gjør tonen varmere og mer profesjonell")
            suggestions.append("Fokuser på utdanning fremfor salg")

        return suggestions
