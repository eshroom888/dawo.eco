"""Authenticity Scorer - AI detectability analysis.

Scores content authenticity using pattern matching and
LLM-based analysis for nuanced AI detection.

Uses the 'generate' tier for LLM analysis.
"""

from dataclasses import dataclass
from typing import Protocol, Optional
import logging

from teams.dawo.generators.content_quality.schemas import (
    ComponentScore,
    AuthenticityResult,
)
from teams.dawo.generators.content_quality.prompts import (
    AI_DETECTABILITY_SYSTEM_PROMPT,
    AI_DETECTABILITY_USER_PROMPT,
    parse_authenticity_response,
)

logger = logging.getLogger(__name__)


class LLMClientProtocol(Protocol):
    """Protocol for LLM client interface."""

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response from the LLM."""
        ...


@dataclass
class AuthenticityScorerConfig:
    """Configuration for authenticity scoring.

    Attributes:
        weight: Weight of authenticity in total score (default 0.10)
        use_llm_analysis: Whether to use LLM for analysis (default False for speed)
        pattern_only_fallback: Use pattern-only if LLM fails (default True)

    Note:
        Set use_llm_analysis=True for more nuanced AI detection at the cost
        of additional LLM API calls. Pattern-only mode is faster and sufficient
        for most use cases.
    """

    weight: float = 0.10
    use_llm_analysis: bool = False  # Default to pattern-only for speed
    pattern_only_fallback: bool = True


# Common AI-generated content markers
AI_PATTERN_MARKERS = {
    "generic_phrasing": [
        "in today's fast-paced world",
        "it's no secret that",
        "let's dive in",
        "first and foremost",
        "at the end of the day",
        "game-changer",
        "unlock your potential",
    ],
    "norwegian_ai_markers": [
        "i dagens moderne verden",
        "det er ingen hemmelighet at",
        "la oss dykke inn i",
        "først og fremst",
        "på slutten av dagen",
    ],
}


class AuthenticityScorer:
    """Scores content authenticity (AI detectability).

    Combines pattern matching for known AI markers with
    LLM-based analysis for nuanced detection.

    Higher scores indicate more human-like content.

    Attributes:
        llm_client: LLM client for authenticity analysis
        config: Scorer configuration
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        config: Optional[AuthenticityScorerConfig] = None,
    ) -> None:
        """Initialize with LLM client.

        Args:
            llm_client: LLM client for AI detectability analysis
            config: Optional scorer configuration
        """
        self._llm = llm_client
        self._config = config or AuthenticityScorerConfig()

    async def score(
        self,
        content: str,
    ) -> ComponentScore:
        """Score content authenticity.

        Uses pattern matching and optionally LLM analysis
        for comprehensive AI detectability scoring.

        Args:
            content: Content text to analyze

        Returns:
            ComponentScore with authenticity details
        """
        # Pattern-based detection first (fast, deterministic)
        pattern_result = self._detect_patterns(content)

        # LLM-based analysis if enabled
        if self._config.use_llm_analysis:
            try:
                llm_result = await self._analyze_with_llm(content)

                # Blend pattern and LLM results
                result = self._blend_results(pattern_result, llm_result)
            except Exception as e:
                logger.warning("LLM authenticity analysis failed: %s", e)
                if self._config.pattern_only_fallback:
                    result = pattern_result
                else:
                    raise
        else:
            result = pattern_result

        return ComponentScore(
            component="authenticity",
            raw_score=result.authenticity_score,
            weight=self._config.weight,
            weighted_score=result.authenticity_score * self._config.weight,
            details={
                "result": result,
                "patterns_found": len(result.flagged_patterns),
            },
        )

    def _detect_patterns(self, content: str) -> AuthenticityResult:
        """Detect AI patterns using pattern matching.

        Args:
            content: Content to analyze

        Returns:
            AuthenticityResult from pattern analysis
        """
        content_lower = content.lower()
        flagged_patterns: list[str] = []

        # Check for AI patterns
        for pattern_type, patterns in AI_PATTERN_MARKERS.items():
            for pattern in patterns:
                if pattern.lower() in content_lower:
                    flagged_patterns.append(f"{pattern_type}: {pattern}")

        # Calculate authenticity score (higher = more human-like)
        # Start at 10, deduct for each AI pattern found
        authenticity_score = max(0.0, 10.0 - len(flagged_patterns) * 2.0)

        # Calculate AI probability
        ai_probability = min(1.0, len(flagged_patterns) * 0.2)

        # Vocabulary diversity check
        words = content_lower.split()
        unique_words = set(words)
        vocabulary_diversity = len(unique_words) / len(words) if words else 0.0

        return AuthenticityResult(
            authenticity_score=authenticity_score,
            ai_probability=ai_probability,
            flagged_patterns=flagged_patterns,
            vocabulary_diversity=vocabulary_diversity,
            analysis_confidence=0.7 if flagged_patterns else 0.5,
        )

    async def _analyze_with_llm(self, content: str) -> AuthenticityResult:
        """Analyze content using LLM for nuanced detection.

        Args:
            content: Content to analyze

        Returns:
            AuthenticityResult from LLM analysis
        """
        prompt = AI_DETECTABILITY_USER_PROMPT.format(content=content)

        response = await self._llm.generate(
            prompt=prompt,
            system=AI_DETECTABILITY_SYSTEM_PROMPT,
        )

        return parse_authenticity_response(response)

    def _blend_results(
        self,
        pattern_result: AuthenticityResult,
        llm_result: AuthenticityResult,
    ) -> AuthenticityResult:
        """Blend pattern and LLM analysis results.

        Pattern detection is weighted 30%, LLM analysis 70%
        for more nuanced final score.

        Args:
            pattern_result: Result from pattern matching
            llm_result: Result from LLM analysis

        Returns:
            Blended AuthenticityResult
        """
        # Combine flagged patterns
        all_patterns = list(set(
            pattern_result.flagged_patterns + llm_result.flagged_patterns
        ))

        # Weighted blend of scores
        blended_score = (
            pattern_result.authenticity_score * 0.3 +
            llm_result.authenticity_score * 0.7
        )

        blended_probability = (
            pattern_result.ai_probability * 0.3 +
            llm_result.ai_probability * 0.7
        )

        # Use higher confidence
        confidence = max(
            pattern_result.analysis_confidence,
            llm_result.analysis_confidence,
        )

        return AuthenticityResult(
            authenticity_score=round(blended_score, 1),
            ai_probability=round(blended_probability, 2),
            flagged_patterns=all_patterns,
            vocabulary_diversity=llm_result.vocabulary_diversity,
            analysis_confidence=confidence,
        )
