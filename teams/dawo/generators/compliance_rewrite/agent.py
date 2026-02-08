"""Compliance Rewrite Suggester Agent.

Generates EU-compliant rewrite suggestions for flagged content.
Uses the 'generate' tier for quality rewrites while maintaining brand voice.

Configuration is received via dependency injection - NEVER loads config directly.
"""

from datetime import datetime, timezone
from typing import Optional, Protocol
import logging
import re

from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ComplianceResult,
    ComplianceStatus,
    ContentComplianceCheck,
    LLMClient,
    OverallStatus,
)
from teams.dawo.validators.brand_voice import BrandProfile

from .prompts import (
    get_system_prompt,
    get_prompt_template,
    get_keep_instruction,
)
from .schemas import (
    RewriteRequest,
    RewriteResult,
    RewriteSuggestion,
)
from .utils import (
    apply_all_suggestions,
    find_phrase_position,
    extract_context,
)

# Module logger
logger = logging.getLogger(__name__)

# Constants
MAX_REVALIDATION_ITERATIONS = 3
CONTEXT_WINDOW_CHARS = 100
GENERATION_TIMEOUT_MS = 10000  # < 10 seconds per AC


class ComplianceRewriteSuggesterProtocol(Protocol):
    """Protocol for compliance rewrite suggester.

    Defines the interface for dependency injection and testing.
    """

    async def suggest_rewrites(
        self,
        request: RewriteRequest
    ) -> RewriteResult:
        """Generate compliant rewrite suggestions for flagged content.

        Args:
            request: RewriteRequest with content and compliance check

        Returns:
            RewriteResult with suggestions for each flagged phrase
        """
        ...

    async def suggest_with_revalidation(
        self,
        content: str,
        brand_profile: BrandProfile,
        language: str = "no",
        max_iterations: int = MAX_REVALIDATION_ITERATIONS
    ) -> RewriteResult:
        """Generate suggestions and revalidate until compliant.

        Automatically applies first suggestion for each phrase and
        re-validates, up to max_iterations.

        Args:
            content: Content to make compliant
            brand_profile: Brand profile for voice guidelines
            language: Content language ("no" or "en")
            max_iterations: Maximum revalidation attempts

        Returns:
            RewriteResult with final compliant content
        """
        ...


class ComplianceRewriteSuggester:
    """Generates EU-compliant rewrite suggestions for flagged content.

    Uses the 'generate' tier (defaults to Sonnet) for quality rewrites.
    Configuration is received via dependency injection - NEVER loads config directly.

    Integrates with EU Compliance Checker from Epic 1 and maintains
    DAWO brand voice in all suggestions.

    Attributes:
        compliance_checker: EU Compliance Checker for re-validation
        brand_profile: DAWO brand profile for voice guidelines
        llm_client: LLM client for generating suggestions
    """

    def __init__(
        self,
        compliance_checker: EUComplianceChecker,
        brand_profile: BrandProfile,
        llm_client: LLMClient,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            compliance_checker: EU Compliance Checker for re-validation
            brand_profile: DAWO brand profile for voice guidelines
            llm_client: LLM client for generating suggestions
        """
        self._checker = compliance_checker
        self._brand = brand_profile
        self._llm = llm_client

    async def suggest_rewrites(
        self,
        request: RewriteRequest
    ) -> RewriteResult:
        """Generate rewrite suggestions for flagged content.

        Processes each flagged phrase from the compliance check and
        generates 2-3 compliant alternatives for each.

        Args:
            request: RewriteRequest with content and compliance check

        Returns:
            RewriteResult with suggestions for each flagged phrase
        """
        start_time = datetime.now(timezone.utc)
        suggestions: list[RewriteSuggestion] = []

        # Process each flagged phrase
        for flagged in request.compliance_check.flagged_phrases:
            if flagged.status == ComplianceStatus.PERMITTED:
                continue  # Skip permitted phrases

            suggestion = await self._generate_suggestion(
                flagged=flagged,
                full_content=request.content,
                language=request.language
            )
            suggestions.append(suggestion)

        # Check if all prohibited phrases have suggestions
        all_prohibited_addressed = all(
            s.has_suggestions
            for s in suggestions
            if s.is_prohibited
        )

        end_time = datetime.now(timezone.utc)
        generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return RewriteResult(
            original_content=request.content,
            suggestions=suggestions,
            all_prohibited_addressed=all_prohibited_addressed,
            rewritten_content=None,  # User selects before applying
            validation_history=[request.compliance_check],
            final_status=request.compliance_check.overall_status,
            generation_time_ms=generation_time_ms,
            created_at=end_time,
        )

    async def suggest_with_revalidation(
        self,
        content: str,
        brand_profile: BrandProfile,
        language: str = "no",
        max_iterations: int = MAX_REVALIDATION_ITERATIONS
    ) -> RewriteResult:
        """Generate suggestions and revalidate until compliant.

        Performs a loop of: check compliance -> generate suggestions ->
        apply suggestions -> re-check, until compliant or max iterations.

        Args:
            content: Content to make compliant
            brand_profile: Brand profile for voice guidelines
            language: Content language ("no" or "en")
            max_iterations: Maximum revalidation attempts

        Returns:
            RewriteResult with final compliant content
        """
        start_time = datetime.now(timezone.utc)
        validation_history: list[ContentComplianceCheck] = []
        current_content = content
        all_suggestions: list[RewriteSuggestion] = []

        for iteration in range(max_iterations):
            # Check compliance
            compliance = await self._checker.check_content(current_content)
            validation_history.append(compliance)

            if compliance.overall_status == OverallStatus.COMPLIANT:
                # Success - content is compliant
                end_time = datetime.now(timezone.utc)
                generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

                return RewriteResult(
                    original_content=content,
                    suggestions=all_suggestions,
                    all_prohibited_addressed=True,
                    rewritten_content=current_content if current_content != content else None,
                    validation_history=validation_history,
                    final_status=OverallStatus.COMPLIANT,
                    generation_time_ms=generation_time_ms,
                    created_at=end_time,
                )

            # Generate suggestions for flagged phrases
            request = RewriteRequest(
                content=current_content,
                compliance_check=compliance,
                brand_profile=brand_profile,
                language=language,
            )
            result = await self.suggest_rewrites(request)
            all_suggestions.extend(result.suggestions)

            # Apply first suggestion for each phrase (auto-fix mode)
            selections = {i: 0 for i in range(len(result.suggestions))}
            current_content = apply_all_suggestions(
                current_content,
                result.suggestions,
                selections
            )

        # Max iterations reached - return best effort
        final_check = await self._checker.check_content(current_content)
        validation_history.append(final_check)

        end_time = datetime.now(timezone.utc)
        generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Check if all prohibited were addressed
        all_prohibited_addressed = all(
            s.has_suggestions
            for s in all_suggestions
            if s.is_prohibited
        )

        return RewriteResult(
            original_content=content,
            suggestions=all_suggestions,
            all_prohibited_addressed=all_prohibited_addressed,
            rewritten_content=current_content if current_content != content else None,
            validation_history=validation_history,
            final_status=final_check.overall_status,
            generation_time_ms=generation_time_ms,
            created_at=end_time,
        )

    async def _generate_suggestion(
        self,
        flagged: ComplianceResult,
        full_content: str,
        language: str
    ) -> RewriteSuggestion:
        """Generate suggestion for a single flagged phrase.

        Args:
            flagged: ComplianceResult with phrase details
            full_content: Full content for context
            language: Content language

        Returns:
            RewriteSuggestion with alternatives
        """
        # Find phrase position in content
        start_pos, end_pos = find_phrase_position(full_content, flagged.phrase)

        # Extract surrounding context
        context = extract_context(
            full_content,
            start_pos if start_pos > 0 else 0,
            end_pos if end_pos > 0 else len(flagged.phrase),
            window=CONTEXT_WINDOW_CHARS
        )

        # Select language-appropriate prompt
        system_prompt = get_system_prompt(language)
        prompt_template = get_prompt_template(language)

        # Get keep instruction for borderline phrases
        is_borderline = flagged.status == ComplianceStatus.BORDERLINE
        keep_instruction = get_keep_instruction(language, is_borderline)

        # Build generation prompt
        prompt = prompt_template.format(
            phrase=flagged.phrase,
            status=flagged.status.value.upper(),
            explanation=flagged.explanation,
            regulation_reference=flagged.regulation_reference,
            context=context,
            keep_instruction=keep_instruction,
        )

        try:
            response = await self._llm.generate(
                prompt=prompt,
                system=system_prompt
            )
            return self._parse_suggestion_response(
                response=response,
                flagged=flagged,
                start_position=start_pos,
                end_position=end_pos
            )

        except Exception as e:
            logger.error("Failed to generate suggestion for phrase '%s': %s", flagged.phrase, e)
            # Return empty suggestion on error
            return RewriteSuggestion(
                original_phrase=flagged.phrase,
                status=flagged.status,
                regulation_reference=flagged.regulation_reference,
                explanation=flagged.explanation,
                suggestions=[],
                keep_recommendation=None,
                start_position=start_pos,
                end_position=end_pos,
            )

    def _parse_suggestion_response(
        self,
        response: str,
        flagged: ComplianceResult,
        start_position: int = 0,
        end_position: int = 0
    ) -> RewriteSuggestion:
        """Parse LLM response into RewriteSuggestion.

        Extracts suggestions from structured output format.

        Args:
            response: Raw LLM response text
            flagged: Original ComplianceResult
            start_position: Start position in content
            end_position: End position in content

        Returns:
            Parsed RewriteSuggestion
        """
        suggestions: list[str] = []
        keep_recommendation: Optional[str] = None

        lines = response.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse suggestions (FORSLAG1/2/3 or SUGGESTION1/2/3)
            if line.upper().startswith('FORSLAG') or line.upper().startswith('SUGGESTION'):
                # Extract the suggestion text after the colon
                if ':' in line:
                    suggestion = line.split(':', 1)[1].strip()
                    if suggestion:
                        suggestions.append(suggestion)

            # Parse keep recommendation (BEHOLDE or KEEP)
            elif line.upper().startswith('BEHOLDE:') or line.upper().startswith('KEEP:'):
                keep_text = line.split(':', 1)[1].strip()
                if keep_text:
                    keep_recommendation = keep_text

        # Log if suggestions were truncated
        if len(suggestions) > 3:
            logger.debug(
                "Truncating %d suggestions to 3 for phrase: %s",
                len(suggestions),
                flagged.phrase
            )

        # Validate response format - log warning if no suggestions parsed
        if not suggestions and not keep_recommendation:
            logger.warning(
                "No suggestions or keep recommendation parsed from LLM response for phrase: %s",
                flagged.phrase
            )

        return RewriteSuggestion(
            original_phrase=flagged.phrase,
            status=flagged.status,
            regulation_reference=flagged.regulation_reference,
            explanation=flagged.explanation,
            suggestions=suggestions[:3],  # Max 3 suggestions
            keep_recommendation=keep_recommendation,
            start_position=start_position,
            end_position=end_position,
        )

    def analyze_borderline_phrase(
        self,
        phrase: str,
        context: str  # Reserved for future LLM-enhanced analysis
    ) -> tuple[bool, str]:
        """Analyze if a borderline phrase is acceptable to keep.

        Uses heuristics based on DAWO brand guidelines and EU compliance.
        Currently synchronous with pattern matching; future versions may
        use async LLM-enhanced analysis with context parameter.

        Args:
            phrase: The borderline phrase
            context: Surrounding context (reserved for future use)

        Returns:
            Tuple of (can_keep, explanation)
        """
        phrase_lower = phrase.lower()

        # Acceptable borderline patterns (from AC #2)
        acceptable_patterns = [
            r'støtter\s+sunn',  # "supports healthy"
            r'supports?\s+healthy',
            r'del\s+av\s+.*livsstil',  # "part of ... lifestyle"
            r'part\s+of\s+.*lifestyle',
            r'tradisjonell',  # "traditional"
            r'traditional',
        ]

        for pattern in acceptable_patterns:
            if re.search(pattern, phrase_lower):
                return True, f"Phrase uses acceptable lifestyle language: '{phrase}'"

        # Needs-change borderline patterns
        needs_change_patterns = [
            r'forebygger',  # "prevents"
            r'prevents?',
            r'styrker\s+immun',  # "strengthens immune"
            r'boost.*immune',
            r'forbedrer\s+helse',  # "improves health"
            r'improves?\s+health',
        ]

        for pattern in needs_change_patterns:
            if re.search(pattern, phrase_lower):
                return False, f"Phrase makes specific health claim that needs rewording: '{phrase}'"

        # Default: unclear, recommend review
        return False, f"Borderline phrase requires review: '{phrase}'"
