"""Brand Voice Validator Agent - DAWO brand voice and authenticity validator.

This agent validates content for brand consistency, human authenticity,
and absence of medicinal terminology. Uses 'generate' tier (defaults to Sonnet)
for judgment quality.

Configuration is received via dependency injection - NEVER loads config directly.

The validator operates in two modes:
1. Pattern-based (fast): Uses regex patterns for known violations
2. LLM-enhanced (accurate): Uses LLM for nuanced tone analysis when client provided
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol
import re
import json
import logging

from .prompts import BRAND_SYSTEM_PROMPT, VALIDATION_PROMPT_TEMPLATE
from .profile import validate_profile

# Set up logging for this module
logger = logging.getLogger(__name__)

# Scoring constants - extracted from magic numbers for clarity
class ScoringWeights:
    """Constants for brand score calculations.

    These weights control how various factors affect the overall brand score
    and authenticity score. Adjust these to tune scoring sensitivity.

    Tone Marker Weights:
        POSITIVE_MARKER_BONUS: Score increase per positive marker found (0.15)
        NEGATIVE_MARKER_PENALTY: Score decrease per negative marker found (0.2)
        MAX_MARKER_ADJUSTMENT: Maximum total adjustment from markers (0.5)

    Issue Severity Penalties:
        HIGH_SEVERITY_PENALTY: Deduction for high-severity issues (0.2)
        MEDIUM_SEVERITY_PENALTY: Deduction for medium-severity issues (0.1)
        LOW_SEVERITY_PENALTY: Deduction for low-severity issues (0.05)

    Authenticity Scoring:
        AI_GENERIC_PENALTY: Deduction per AI-generic pattern found (0.15)
        AI_TELL_PENALTY: Deduction per hardcoded AI tell found (0.1)
    """

    # Tone marker weights
    POSITIVE_MARKER_BONUS = 0.15
    NEGATIVE_MARKER_PENALTY = 0.2
    MAX_MARKER_ADJUSTMENT = 0.5

    # Issue severity penalties
    HIGH_SEVERITY_PENALTY = 0.2
    MEDIUM_SEVERITY_PENALTY = 0.1
    LOW_SEVERITY_PENALTY = 0.05

    # Authenticity scoring
    AI_GENERIC_PENALTY = 0.15
    AI_TELL_PENALTY = 0.1


class ValidationStatus(Enum):
    """Overall validation status for content."""
    PASS = "pass"
    NEEDS_REVISION = "needs_revision"
    FAIL = "fail"


class IssueType(Enum):
    """Types of brand voice issues."""
    TONE_MISMATCH = "tone_mismatch"
    AI_GENERIC = "ai_generic"
    MEDICINAL_TERM = "medicinal_term"
    STYLE_VIOLATION = "style_violation"


@dataclass
class BrandIssue:
    """A single brand voice issue found in content."""
    phrase: str
    issue_type: IssueType
    severity: str  # "low", "medium", "high"
    suggestion: str
    explanation: str


@dataclass
class BrandValidationResult:
    """Complete brand validation result for content."""
    status: ValidationStatus
    issues: list[BrandIssue] = field(default_factory=list)
    brand_score: float = 1.0  # 0.0-1.0 (1.0 = perfect brand alignment)
    authenticity_score: float = 1.0  # 0.0-1.0 (1.0 = very human, 0.0 = very AI)
    tone_analysis: dict = field(default_factory=lambda: {"warm": 0.5, "educational": 0.5, "nordic": 0.5})


class LLMClient(Protocol):
    """Protocol for LLM client interface.

    Any LLM client that implements this protocol can be used with the validator.
    Compatible with Google ADK, Anthropic SDK, or custom implementations.
    """
    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt

        Returns:
            The LLM's response text
        """
        ...


class BrandVoiceValidator:
    """DAWO brand voice and authenticity validator.

    Validates content for brand consistency, human authenticity,
    and absence of medicinal terminology.
    Uses 'generate' tier (defaults to Sonnet) for judgment quality.

    CRITICAL: Accept config via dependency injection - NEVER load directly.

    The validator supports two modes:
    1. Pattern-only mode (default): Fast regex-based checking
    2. LLM-enhanced mode: Uses LLM for nuanced tone analysis when provided

    Attributes:
        profile: Brand profile dictionary containing tone rules and patterns
        llm_client: Optional LLM client for enhanced analysis
    """

    def __init__(
        self,
        brand_profile: dict,
        llm_client: Optional[LLMClient] = None
    ):
        """Initialize with brand profile configuration.

        Args:
            brand_profile: Dictionary containing brand voice configuration.
                          Injected by Team Builder - NEVER load from file directly.
            llm_client: Optional LLM client for enhanced tone analysis.
                       When provided, enables LLM-based nuanced judgment.

        Raises:
            ValueError: If brand_profile is missing required keys.
        """
        # Validate profile structure
        is_valid, error_msg = validate_profile(brand_profile)
        if not is_valid:
            raise ValueError(f"Invalid brand profile: {error_msg}")

        self.profile = brand_profile
        self.llm_client = llm_client

        # Extract configuration elements
        self.tone_pillars = brand_profile.get("tone_pillars", {})
        self.forbidden_terms = brand_profile.get("forbidden_terms", {})
        self.ai_generic_patterns = brand_profile.get("ai_generic_patterns", [])
        self.scoring_thresholds = brand_profile.get("scoring_thresholds", {
            "pass": 0.8,
            "needs_revision": 0.5,
            "fail": 0.0
        })

    async def validate_content(
        self,
        content: str,
        eu_compliance_result: Optional[object] = None
    ) -> BrandValidationResult:
        """Main validation entry point with optional LLM enhancement.

        Evaluates content for DAWO brand voice alignment and authenticity.
        When an LLM client is available, performs enhanced tone analysis.

        Args:
            content: Text content to validate for brand alignment
            eu_compliance_result: Optional EU compliance result to avoid duplicating
                                 medicinal term detection. If provided and contains
                                 flagged_phrases, those are used instead of re-scanning.

        Returns:
            BrandValidationResult with overall status and flagged issues
        """
        issues: list[BrandIssue] = []

        # Phase 1: Pattern-based detection (fast path)
        # Cross-reference with EU Compliance results if available to avoid duplicate work
        medicinal_issues = self._check_medicinal_terms_with_eu_context(
            content, eu_compliance_result
        )
        issues.extend(medicinal_issues)

        ai_generic_issues = self._check_ai_generic_patterns(content)
        issues.extend(ai_generic_issues)

        superlative_issues = self._check_superlatives(content)
        issues.extend(superlative_issues)

        sales_issues = self._check_sales_pressure(content)
        issues.extend(sales_issues)

        # Phase 2: Tone analysis
        tone_analysis = self._analyze_tone(content)

        # Phase 3: LLM-enhanced analysis (when available)
        if self.llm_client:
            try:
                llm_issues = await self._llm_enhanced_analysis(content)
                # Merge LLM findings, avoiding duplicates
                existing_phrases = {i.phrase.lower() for i in issues}
                for issue in llm_issues:
                    if issue.phrase.lower() not in existing_phrases:
                        issues.append(issue)
            except Exception as e:
                # Fail gracefully - pattern matching still works
                logger.warning(f"LLM-enhanced analysis failed, using pattern matching only: {e}")

        # Calculate scores
        brand_score = self._calculate_brand_score(issues, tone_analysis)
        authenticity_score = self._calculate_authenticity_score(content, issues)

        # Determine overall status
        status = self._calculate_status(issues, brand_score)

        return BrandValidationResult(
            status=status,
            issues=issues,
            brand_score=brand_score,
            authenticity_score=authenticity_score,
            tone_analysis=tone_analysis
        )

    def validate_content_sync(self, content: str) -> BrandValidationResult:
        """Synchronous pattern-only validation (no LLM).

        Use this when you need sync validation without LLM.

        Args:
            content: Text content to validate

        Returns:
            BrandValidationResult with classification based on patterns
        """
        issues: list[BrandIssue] = []

        # Pattern-based detection
        medicinal_issues = self._check_medicinal_terms(content)
        issues.extend(medicinal_issues)

        ai_generic_issues = self._check_ai_generic_patterns(content)
        issues.extend(ai_generic_issues)

        superlative_issues = self._check_superlatives(content)
        issues.extend(superlative_issues)

        sales_issues = self._check_sales_pressure(content)
        issues.extend(sales_issues)

        # Tone analysis
        tone_analysis = self._analyze_tone(content)

        # Calculate scores
        brand_score = self._calculate_brand_score(issues, tone_analysis)
        authenticity_score = self._calculate_authenticity_score(content, issues)

        # Determine status
        status = self._calculate_status(issues, brand_score)

        return BrandValidationResult(
            status=status,
            issues=issues,
            brand_score=brand_score,
            authenticity_score=authenticity_score,
            tone_analysis=tone_analysis
        )

    def _check_medicinal_terms(self, content: str) -> list[BrandIssue]:
        """Check for forbidden medicinal terminology.

        Args:
            content: Text content to check

        Returns:
            List of BrandIssue for each medicinal term found
        """
        issues = []
        content_lower = content.lower()

        medicinal_terms = self.forbidden_terms.get("medicinal", [])
        for term in medicinal_terms:
            # Use word boundary matching
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            matches = re.finditer(pattern, content_lower)

            for match in matches:
                # Extract surrounding context
                start = max(0, match.start() - 15)
                end = min(len(content), match.end() + 15)
                context = content[start:end].strip()

                issues.append(BrandIssue(
                    phrase=context,
                    issue_type=IssueType.MEDICINAL_TERM,
                    severity="high",
                    suggestion=self._get_medicinal_suggestion(term),
                    explanation=f"Medicinal term '{term}' is forbidden. Use wellness/lifestyle language instead."
                ))

        return issues

    def _check_medicinal_terms_with_eu_context(
        self,
        content: str,
        eu_compliance_result: Optional[object] = None
    ) -> list[BrandIssue]:
        """Check for medicinal terms, cross-referencing EU compliance results.

        If EU compliance has already flagged medicinal terms, reference those
        findings instead of duplicating detection. This avoids redundant work
        and ensures consistency between validators.

        Args:
            content: Text content to check
            eu_compliance_result: Optional EU compliance check result

        Returns:
            List of BrandIssue for medicinal terms found
        """
        # If EU compliance result provided and has flagged phrases, use those
        if eu_compliance_result is not None:
            try:
                # Try to extract flagged phrases from EU compliance result
                flagged_phrases = getattr(eu_compliance_result, 'flagged_phrases', None)
                if flagged_phrases:
                    issues = []
                    for flagged in flagged_phrases:
                        # Extract phrase from EU compliance result
                        phrase = getattr(flagged, 'phrase', str(flagged))
                        issues.append(BrandIssue(
                            phrase=phrase,
                            issue_type=IssueType.MEDICINAL_TERM,
                            severity="high",
                            suggestion="See EU Compliance Checker for detailed guidance",
                            explanation=f"Medicinal term flagged by EU Compliance Checker: '{phrase}'"
                        ))
                    if issues:
                        logger.debug(
                            f"Using {len(issues)} medicinal findings from EU Compliance result"
                        )
                        return issues
            except Exception as e:
                logger.warning(
                    f"Could not extract EU compliance findings, falling back to pattern matching: {e}"
                )

        # Fall back to pattern-based detection
        return self._check_medicinal_terms(content)

    def _check_ai_generic_patterns(self, content: str) -> list[BrandIssue]:
        """Check for AI-generic writing patterns.

        Args:
            content: Text content to check

        Returns:
            List of BrandIssue for each AI-generic pattern found
        """
        issues = []

        for pattern in self.ai_generic_patterns:
            # Patterns may contain regex
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                matches = regex.finditer(content)

                for match in matches:
                    issues.append(BrandIssue(
                        phrase=match.group(),
                        issue_type=IssueType.AI_GENERIC,
                        severity="medium",
                        suggestion=self._get_ai_generic_suggestion(pattern),
                        explanation="This phrase is commonly used by AI and lacks human authenticity. Rephrase in DAWO's warm, personal voice."
                    ))
            except re.error:
                # If pattern is invalid regex, try literal match
                if pattern.lower() in content.lower():
                    issues.append(BrandIssue(
                        phrase=pattern,
                        issue_type=IssueType.AI_GENERIC,
                        severity="medium",
                        suggestion=self._get_ai_generic_suggestion(pattern),
                        explanation="This phrase is commonly used by AI and lacks human authenticity."
                    ))

        return issues

    def _check_superlatives(self, content: str) -> list[BrandIssue]:
        """Check for forbidden superlatives.

        Args:
            content: Text content to check

        Returns:
            List of BrandIssue for each superlative found
        """
        issues = []
        content_lower = content.lower()

        superlatives = self.forbidden_terms.get("superlatives", [])
        for term in superlatives:
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            matches = re.finditer(pattern, content_lower)

            for match in matches:
                start = max(0, match.start() - 10)
                end = min(len(content), match.end() + 10)
                context = content[start:end].strip()

                issues.append(BrandIssue(
                    phrase=context,
                    issue_type=IssueType.STYLE_VIOLATION,
                    severity="medium",
                    suggestion="Use understated confidence. DAWO doesn't need superlatives - let the product speak for itself.",
                    explanation=f"Superlative '{term}' violates Nordic simplicity. DAWO uses understated confidence."
                ))

        return issues

    def _check_sales_pressure(self, content: str) -> list[BrandIssue]:
        """Check for sales pressure language.

        Args:
            content: Text content to check

        Returns:
            List of BrandIssue for each sales pressure term found
        """
        issues = []
        content_lower = content.lower()

        sales_terms = self.forbidden_terms.get("sales_pressure", [])
        for term in sales_terms:
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            if re.search(pattern, content_lower):
                issues.append(BrandIssue(
                    phrase=term,
                    issue_type=IssueType.TONE_MISMATCH,
                    severity="medium",
                    suggestion="Remove urgency language. DAWO is educational first, never salesy.",
                    explanation=f"Sales pressure term '{term}' violates educational tone. Content should inform, not pressure."
                ))

        return issues

    def _analyze_tone(self, content: str) -> dict:
        """Analyze content for DAWO tone pillars.

        Args:
            content: Text content to analyze

        Returns:
            Dictionary with scores for warm, educational, nordic (0.0-1.0 each)
        """
        content_lower = content.lower()
        tone_scores = {"warm": 0.5, "educational": 0.5, "nordic": 0.5}

        # Map pillar names to output keys (nordic_simplicity -> nordic)
        pillar_key_map = {
            "warm": "warm",
            "educational": "educational",
            "nordic_simplicity": "nordic",
            "nordic": "nordic"
        }

        for pillar, config in self.tone_pillars.items():
            output_key = pillar_key_map.get(pillar, pillar)
            if output_key not in tone_scores:
                continue

            positive_markers = config.get("positive_markers", [])
            negative_markers = config.get("negative_markers", [])

            # Count positive markers
            positive_count = sum(
                1 for marker in positive_markers
                if re.search(r'\b' + re.escape(marker.lower()) + r'\b', content_lower)
            )

            # Count negative markers
            negative_count = sum(
                1 for marker in negative_markers
                if re.search(r'\b' + re.escape(marker.lower()) + r'\b', content_lower)
            )

            # Calculate score (start at 0.5, adjust based on markers)
            score = 0.5
            score += min(
                ScoringWeights.MAX_MARKER_ADJUSTMENT,
                positive_count * ScoringWeights.POSITIVE_MARKER_BONUS
            )
            score -= min(
                ScoringWeights.MAX_MARKER_ADJUSTMENT,
                negative_count * ScoringWeights.NEGATIVE_MARKER_PENALTY
            )

            tone_scores[output_key] = max(0.0, min(1.0, score))

        return tone_scores

    def _calculate_brand_score(
        self,
        issues: list[BrandIssue],
        tone_analysis: dict
    ) -> float:
        """Calculate overall brand alignment score.

        Args:
            issues: List of found issues
            tone_analysis: Tone pillar scores

        Returns:
            Float score between 0.0 and 1.0
        """
        # Start with average tone score
        tone_avg = sum(tone_analysis.values()) / len(tone_analysis) if tone_analysis else 0.5

        # Deduct for issues
        score = tone_avg
        for issue in issues:
            if issue.severity == "high":
                score -= ScoringWeights.HIGH_SEVERITY_PENALTY
            elif issue.severity == "medium":
                score -= ScoringWeights.MEDIUM_SEVERITY_PENALTY
            else:
                score -= ScoringWeights.LOW_SEVERITY_PENALTY

        return max(0.0, min(1.0, score))

    def _calculate_authenticity_score(
        self,
        content: str,
        issues: list[BrandIssue]
    ) -> float:
        """Calculate human authenticity score.

        Higher = more human, lower = more AI-like.

        Args:
            content: Original content
            issues: List of found issues

        Returns:
            Float score between 0.0 and 1.0
        """
        score = 1.0

        # Deduct for AI-generic patterns
        ai_issues = [i for i in issues if i.issue_type == IssueType.AI_GENERIC]
        score -= len(ai_issues) * ScoringWeights.AI_GENERIC_PENALTY

        # Additional AI tells for authenticity scoring (not in config patterns)
        # These are regex patterns that indicate AI-generated text but may be
        # too subtle to flag as issues. They only affect authenticity score,
        # not validation status. Keep separate from config to avoid confusion
        # with issue-generating patterns.
        ai_tells = [
            r"whether you're a .* or",  # Common AI conditional opener
            r"it's worth noting",  # Formal AI hedging language
        ]
        for tell in ai_tells:
            if re.search(tell, content.lower()):
                score -= ScoringWeights.AI_TELL_PENALTY

        return max(0.0, min(1.0, score))

    def _calculate_status(
        self,
        issues: list[BrandIssue],
        brand_score: float
    ) -> ValidationStatus:
        """Calculate overall validation status.

        Args:
            issues: List of found issues
            brand_score: Calculated brand alignment score

        Returns:
            ValidationStatus enum value
        """
        # Any medicinal term = FAIL
        medicinal_issues = [i for i in issues if i.issue_type == IssueType.MEDICINAL_TERM]
        if medicinal_issues:
            return ValidationStatus.FAIL

        # No issues and reasonable brand score = PASS
        if len(issues) == 0 and brand_score >= 0.5:
            return ValidationStatus.PASS

        # Check thresholds
        pass_threshold = self.scoring_thresholds.get("pass", 0.8)
        revision_threshold = self.scoring_thresholds.get("needs_revision", 0.5)

        if brand_score >= pass_threshold:
            return ValidationStatus.PASS
        elif brand_score >= revision_threshold or len(issues) <= 2:
            return ValidationStatus.NEEDS_REVISION
        else:
            return ValidationStatus.FAIL

    async def _llm_enhanced_analysis(self, content: str) -> list[BrandIssue]:
        """Use LLM for nuanced brand voice analysis.

        Args:
            content: Text content to analyze

        Returns:
            List of BrandIssue from LLM analysis
        """
        if not self.llm_client:
            return []

        try:
            # Build profile summary for prompt
            profile_summary = f"Brand: {self.profile.get('brand_name', 'DAWO')}\n"
            for pillar, config in self.tone_pillars.items():
                profile_summary += f"- {pillar}: {config.get('description', '')}\n"

            forbidden_summary = json.dumps(self.forbidden_terms.get("medicinal", [])[:5])
            ai_patterns_summary = "\n".join(self.ai_generic_patterns[:5])

            prompt = VALIDATION_PROMPT_TEMPLATE.format(
                content=content,
                profile_summary=profile_summary,
                forbidden_terms=forbidden_summary,
                ai_patterns=ai_patterns_summary
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                system=BRAND_SYSTEM_PROMPT
            )

            return self._parse_llm_response(response)

        except Exception as e:
            logger.warning(f"LLM analysis request failed: {e}")
            return []

    def _parse_llm_response(self, response: str) -> list[BrandIssue]:
        """Parse LLM response into structured BrandIssues.

        Args:
            response: Raw LLM response text

        Returns:
            List of parsed BrandIssue objects
        """
        issues = []

        # Try to parse JSON response
        try:
            data = json.loads(response)
            if isinstance(data, dict) and "issues" in data:
                for item in data["issues"]:
                    issue_type = IssueType.TONE_MISMATCH
                    if item.get("type") == "ai_generic":
                        issue_type = IssueType.AI_GENERIC
                    elif item.get("type") == "medicinal":
                        issue_type = IssueType.MEDICINAL_TERM

                    issues.append(BrandIssue(
                        phrase=item.get("phrase", ""),
                        issue_type=issue_type,
                        severity=item.get("severity", "medium"),
                        suggestion=item.get("suggestion", ""),
                        explanation=item.get("explanation", "")
                    ))
        except json.JSONDecodeError:
            # If not JSON, try line-based parsing
            pass

        return issues

    def _get_medicinal_suggestion(self, term: str) -> str:
        """Get replacement suggestion for medicinal term.

        Args:
            term: The medicinal term found

        Returns:
            Suggested replacement phrase
        """
        suggestions = {
            "treatment": "Use 'wellness routine' or 'daily ritual' instead",
            "treats": "Use 'supports your wellness' or 'part of a healthy lifestyle'",
            "cure": "Remove - no food can cure. Focus on lifestyle benefits",
            "cures": "Remove - no food can cure. Focus on lifestyle benefits",
            "heal": "Use 'nourish' or 'support' instead",
            "heals": "Use 'nourishes' or 'supports' instead",
            "disease": "Avoid medical terms entirely. Focus on positive wellness",
            "illness": "Avoid medical terms entirely. Focus on positive wellness",
            "symptoms": "Describe the experience, not medical symptoms",
            "condition": "Use 'lifestyle' or remove entirely",
            "therapeutic": "Use 'beneficial' or 'soothing' instead",
            "clinical": "Use 'research shows' with DOI citation instead",
            "medicinal": "Use 'functional' or 'traditional' instead"
        }
        return suggestions.get(term.lower(), f"Replace '{term}' with wellness/lifestyle language")

    def _get_ai_generic_suggestion(self, pattern: str) -> str:
        """Get replacement suggestion for AI-generic pattern.

        Args:
            pattern: The AI-generic pattern found

        Returns:
            Suggested replacement approach
        """
        suggestions = {
            "In today's fast-paced world": "Start with your authentic story. 'We've been...' or 'For generations...'",
            "Are you looking for": "Make a statement instead. 'Simple ingredients.' 'Nordic tradition.'",
            "Look no further": "Remove - let quality speak for itself",
            "Unlock your potential": "Be specific about the experience. 'A moment of calm.' 'Morning clarity.'",
            "Transform your": "Use 'Add to' or 'Part of' - subtle, not transformative"
        }

        for key, value in suggestions.items():
            if key.lower() in pattern.lower():
                return value

        return "Rephrase in DAWO's warm, personal, Nordic voice. Be specific and authentic."
