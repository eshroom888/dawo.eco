"""EU Compliance Checker Agent - Validates content against EU Health Claims Regulation.

This agent evaluates content for compliance with EC 1924/2006 and Novel Food regulations.
It classifies phrases as PROHIBITED, BORDERLINE, or PERMITTED and returns an overall
compliance status.

Uses the 'generate' tier (defaults to Sonnet) for accurate judgment.
Configuration is received via dependency injection - NEVER loads config directly.

The checker operates in two modes:
1. Pattern-based (fast): Uses regex patterns for known violations
2. LLM-enhanced (accurate): Uses LLM for nuanced/ambiguous cases when client provided
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol
import logging
import re

from .prompts import COMPLIANCE_SYSTEM_PROMPT, CLASSIFICATION_PROMPT_TEMPLATE
from .rules import ComplianceRules

# Module logger
logger = logging.getLogger(__name__)


class ComplianceScoring:
    """Constants for compliance score calculations.

    These values control how violations affect the overall compliance score.
    Centralizing them here makes the scoring logic transparent and adjustable.

    Score Impact:
        - PROHIBITED_PENALTY: Deduction per prohibited phrase (severe)
        - BORDERLINE_PENALTY: Deduction per borderline phrase (moderate)

    Context Extraction:
        - CONTEXT_WINDOW_CHARS: Characters to include around matched phrases
    """

    PROHIBITED_PENALTY: float = 0.3
    """Score penalty per prohibited phrase. Severe impact reflects regulatory risk."""

    BORDERLINE_PENALTY: float = 0.1
    """Score penalty per borderline phrase. Moderate impact for claims needing review."""

    CONTEXT_WINDOW_CHARS: int = 20
    """Characters before/after match to include for context in flagged phrases."""


# Regulation Reference Constants
class RegulationRef:
    """EU regulation references for compliance checking."""
    HEALTH_CLAIMS = "EC 1924/2006"
    ARTICLE_10 = "EC 1924/2006 Article 10"  # Prohibited health claims
    ARTICLE_13 = "EC 1924/2006 Article 13"  # Function claims (EFSA approval)
    ARTICLE_14 = "EC 1924/2006 Article 14"  # Disease risk reduction
    NOVEL_FOOD = "EC 2015/2283"  # Novel Food Regulation
    NO_CLAIM = "N/A - No claim made"


class ComplianceStatus(Enum):
    """Classification status for individual phrases."""
    PROHIBITED = "prohibited"
    BORDERLINE = "borderline"
    PERMITTED = "permitted"


class OverallStatus(Enum):
    """Overall compliance status for content."""
    COMPLIANT = "compliant"  # No prohibited phrases, minimal borderline
    WARNING = "warning"      # Borderline phrases present but no prohibited
    REJECTED = "rejected"    # Prohibited phrases detected


@dataclass
class ComplianceResult:
    """Result of checking a single phrase."""
    phrase: str
    status: ComplianceStatus
    explanation: str
    regulation_reference: str  # e.g., "EC 1924/2006 Article 10"


@dataclass
class NovelFoodCheck:
    """Result of Novel Food classification validation."""
    product_name: str
    classification: str  # "novel_food", "food", "traditional_food"
    allowed_use: str     # "supplement_only", "food_or_supplement", "food"
    is_valid: bool
    message: str


@dataclass
class ContentComplianceCheck:
    """Complete compliance check result for content."""
    overall_status: OverallStatus
    flagged_phrases: list[ComplianceResult] = field(default_factory=list)
    novel_food_check: Optional[NovelFoodCheck] = None
    compliance_score: float = 1.0  # 0.0-1.0, 1.0 = fully compliant
    llm_enhanced: bool = False  # Whether LLM was used for this check

    @property
    def is_compliant(self) -> bool:
        """Check if content passes compliance."""
        return self.overall_status == OverallStatus.COMPLIANT

    @property
    def prohibited_count(self) -> int:
        """Count of prohibited phrases."""
        return sum(1 for r in self.flagged_phrases if r.status == ComplianceStatus.PROHIBITED)

    @property
    def borderline_count(self) -> int:
        """Count of borderline phrases."""
        return sum(1 for r in self.flagged_phrases if r.status == ComplianceStatus.BORDERLINE)


class LLMClient(Protocol):
    """Protocol for LLM client interface.

    Any LLM client that implements this protocol can be used with the checker.
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


class EUComplianceChecker:
    """EU Health Claims Regulation compliance validator.

    Validates content against EC 1924/2006 and Novel Food regulations.
    Uses 'generate' tier (defaults to Sonnet) for accuracy.

    CRITICAL: Accept config via dependency injection - NEVER load directly.

    The checker supports two modes:
    1. Pattern-only mode (default): Fast regex-based checking
    2. LLM-enhanced mode: Uses LLM for nuanced classification when provided

    Attributes:
        rules: ComplianceRules instance containing patterns and classifications
        llm_client: Optional LLM client for enhanced classification
    """

    def __init__(
        self,
        compliance_rules: dict,
        llm_client: Optional[LLMClient] = None
    ):
        """Initialize with compliance rules configuration.

        Args:
            compliance_rules: Dictionary containing compliance configuration.
                             Injected by Team Builder - NEVER load from file directly.
            llm_client: Optional LLM client for enhanced classification.
                       When provided, enables LLM-based nuanced judgment.
        """
        self.rules = ComplianceRules(compliance_rules)
        self.llm_client = llm_client

    async def check_content(
        self,
        content: str,
        product_name: Optional[str] = None,
        use_llm: bool = True
    ) -> ContentComplianceCheck:
        """Main compliance check entry point.

        Evaluates content for EU Health Claims compliance and optionally
        validates Novel Food classification for specified product.

        When an LLM client is available and use_llm=True, performs enhanced
        checking that can detect nuanced violations beyond pattern matching.

        Args:
            content: Text content to check for compliance
            product_name: Optional product name for Novel Food validation
            use_llm: Whether to use LLM for enhanced checking (default True)

        Returns:
            ContentComplianceCheck with overall status and flagged phrases
        """
        flagged_phrases: list[ComplianceResult] = []
        llm_enhanced = False

        # Phase 1: Pattern-based detection (fast path)
        prohibited_results = self._check_prohibited_phrases(content)
        flagged_phrases.extend(prohibited_results)

        borderline_results = self._check_borderline_phrases(content)
        flagged_phrases.extend(borderline_results)

        # Phase 2: LLM-enhanced detection (when available)
        if self.llm_client and use_llm:
            llm_results = await self._llm_enhanced_check(content, product_name)
            if llm_results:
                # Merge LLM findings, avoiding duplicates
                existing_phrases = {r.phrase.lower() for r in flagged_phrases}
                for result in llm_results:
                    if result.phrase.lower() not in existing_phrases:
                        flagged_phrases.append(result)
                llm_enhanced = True

        # Phase 3: Novel Food classification check
        novel_food_check = None
        if product_name:
            novel_food_check = self._validate_novel_food(content, product_name)
            if novel_food_check and not novel_food_check.is_valid:
                flagged_phrases.append(ComplianceResult(
                    phrase=f"Product: {product_name}",
                    status=ComplianceStatus.PROHIBITED,
                    explanation=novel_food_check.message,
                    regulation_reference=RegulationRef.NOVEL_FOOD
                ))

        # Calculate final status
        overall_status = self._calculate_overall_status(flagged_phrases)
        compliance_score = self._calculate_compliance_score(flagged_phrases)

        return ContentComplianceCheck(
            overall_status=overall_status,
            flagged_phrases=flagged_phrases,
            novel_food_check=novel_food_check,
            compliance_score=compliance_score,
            llm_enhanced=llm_enhanced
        )

    async def _llm_enhanced_check(
        self,
        content: str,
        product_name: Optional[str] = None
    ) -> list[ComplianceResult]:
        """Use LLM for nuanced compliance checking.

        Analyzes content using the LLM with EU Health Claims context.
        Catches subtle violations that pattern matching might miss.

        Args:
            content: Text content to analyze
            product_name: Optional product for context

        Returns:
            List of ComplianceResult from LLM analysis
        """
        if not self.llm_client:
            return []

        try:
            # Build the classification prompt
            prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
                content=content,
                product_name=product_name or "Not specified"
            )

            # Call LLM with compliance system prompt
            response = await self.llm_client.generate(
                prompt=prompt,
                system=COMPLIANCE_SYSTEM_PROMPT
            )

            # Parse LLM response into ComplianceResults
            return self._parse_llm_response(response)

        except Exception as e:
            # Log exception but fail gracefully - pattern matching still works
            logger.warning("LLM enhanced check failed, falling back to patterns: %s", e)
            return []

    def _parse_llm_response(self, response: str) -> list[ComplianceResult]:
        """Parse LLM response into structured ComplianceResults.

        Args:
            response: Raw LLM response text

        Returns:
            List of parsed ComplianceResult objects
        """
        results = []
        lines = response.strip().split('\n')

        current_phrase = None
        current_status = None
        current_explanation = None
        current_reference = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse structured output from LLM
            if line.startswith('PHRASE:'):
                if current_phrase and current_status:
                    results.append(ComplianceResult(
                        phrase=current_phrase,
                        status=current_status,
                        explanation=current_explanation or "LLM-detected violation",
                        regulation_reference=current_reference or RegulationRef.HEALTH_CLAIMS
                    ))
                current_phrase = line[7:].strip()
                current_status = None
                current_explanation = None
                current_reference = None

            elif line.startswith('STATUS:'):
                status_str = line[7:].strip().upper()
                if status_str == 'PROHIBITED':
                    current_status = ComplianceStatus.PROHIBITED
                    current_reference = RegulationRef.ARTICLE_10
                elif status_str == 'BORDERLINE':
                    current_status = ComplianceStatus.BORDERLINE
                    current_reference = RegulationRef.ARTICLE_13
                elif status_str == 'PERMITTED':
                    current_status = ComplianceStatus.PERMITTED
                    current_reference = RegulationRef.NO_CLAIM

            elif line.startswith('EXPLANATION:'):
                current_explanation = line[12:].strip()

            elif line.startswith('REFERENCE:'):
                current_reference = line[10:].strip()

        # Don't forget the last one
        if current_phrase and current_status and current_status != ComplianceStatus.PERMITTED:
            results.append(ComplianceResult(
                phrase=current_phrase,
                status=current_status,
                explanation=current_explanation or "LLM-detected violation",
                regulation_reference=current_reference or RegulationRef.HEALTH_CLAIMS
            ))

        return results

    def _check_prohibited_phrases(self, content: str) -> list[ComplianceResult]:
        """Check content for prohibited health claim patterns.

        Prohibited phrases include: treats, cures, prevents, disease references.

        Args:
            content: Text content to check

        Returns:
            List of ComplianceResult for each prohibited phrase found
        """
        results = []
        content_lower = content.lower()

        for pattern_info in self.rules.prohibited_patterns:
            pattern = pattern_info["pattern"]
            category = pattern_info["category"]

            # Use word boundary matching for accurate detection
            regex_pattern = r'\b' + re.escape(pattern.lower()) + r'\b'
            matches = re.finditer(regex_pattern, content_lower)

            for match in matches:
                # Extract surrounding context
                start = max(0, match.start() - ComplianceScoring.CONTEXT_WINDOW_CHARS)
                end = min(len(content), match.end() + ComplianceScoring.CONTEXT_WINDOW_CHARS)
                context = content[start:end]

                results.append(ComplianceResult(
                    phrase=context.strip(),
                    status=ComplianceStatus.PROHIBITED,
                    explanation=self._get_prohibited_explanation(category),
                    regulation_reference=RegulationRef.ARTICLE_10
                ))

        return results

    def _check_borderline_phrases(self, content: str) -> list[ComplianceResult]:
        """Check content for borderline health claim patterns.

        Borderline phrases include: supports, promotes, contributes to.
        These are function claims that require EFSA approval.

        Args:
            content: Text content to check

        Returns:
            List of ComplianceResult for each borderline phrase found
        """
        results = []
        content_lower = content.lower()

        for pattern_info in self.rules.borderline_patterns:
            pattern = pattern_info["pattern"]
            category = pattern_info["category"]

            regex_pattern = r'\b' + re.escape(pattern.lower()) + r'\b'
            matches = re.finditer(regex_pattern, content_lower)

            for match in matches:
                start = max(0, match.start() - ComplianceScoring.CONTEXT_WINDOW_CHARS)
                end = min(len(content), match.end() + ComplianceScoring.CONTEXT_WINDOW_CHARS)
                context = content[start:end]

                results.append(ComplianceResult(
                    phrase=context.strip(),
                    status=ComplianceStatus.BORDERLINE,
                    explanation=self._get_borderline_explanation(category),
                    regulation_reference=RegulationRef.ARTICLE_13
                ))

        return results

    def _validate_novel_food(
        self,
        content: str,
        product_name: str
    ) -> NovelFoodCheck:
        """Validate content against Novel Food classification for product.

        Ensures product messaging aligns with its regulatory classification.
        E.g., Chaga can only be marketed as a supplement, not food.

        Args:
            content: Text content to validate
            product_name: Product name to check classification

        Returns:
            NovelFoodCheck with validation result
        """
        # Normalize product name for lookup
        normalized_name = product_name.lower().replace(" ", "_").replace("'", "")

        classification = self.rules.get_novel_food_classification(normalized_name)

        if classification is None:
            return NovelFoodCheck(
                product_name=product_name,
                classification="unknown",
                allowed_use="unknown",
                is_valid=True,  # Don't block unknown products
                message=f"Product '{product_name}' not in classification database"
            )

        status = classification["status"]
        allowed_use = classification["use"]

        # Check for food-related messaging with supplement-only products
        is_valid = True
        message = f"Product '{product_name}' correctly marketed"

        if allowed_use == "supplement_only":
            # Check for food-related terms that violate supplement-only status
            food_terms = ["food", "eat", "ingredient", "recipe", "cook", "meal"]
            content_lower = content.lower()

            for term in food_terms:
                if re.search(r'\b' + term + r'\b', content_lower):
                    is_valid = False
                    message = (
                        f"Product '{product_name}' is classified as Novel Food "
                        f"(supplement only) but content uses food-related term '{term}'. "
                        f"Must be marketed as dietary supplement only."
                    )
                    break

        return NovelFoodCheck(
            product_name=product_name,
            classification=status,
            allowed_use=allowed_use,
            is_valid=is_valid,
            message=message
        )

    def _calculate_overall_status(
        self,
        flagged_phrases: list[ComplianceResult]
    ) -> OverallStatus:
        """Calculate overall compliance status from flagged phrases.

        Status logic:
        - REJECTED: Any prohibited phrase present
        - WARNING: Borderline phrases present but no prohibited
        - COMPLIANT: No issues or only permitted phrases

        Args:
            flagged_phrases: List of all flagged phrase results

        Returns:
            OverallStatus enum value
        """
        has_prohibited = any(
            r.status == ComplianceStatus.PROHIBITED
            for r in flagged_phrases
        )
        has_borderline = any(
            r.status == ComplianceStatus.BORDERLINE
            for r in flagged_phrases
        )

        if has_prohibited:
            return OverallStatus.REJECTED
        elif has_borderline:
            return OverallStatus.WARNING
        else:
            return OverallStatus.COMPLIANT

    def _calculate_compliance_score(
        self,
        flagged_phrases: list[ComplianceResult]
    ) -> float:
        """Calculate numeric compliance score.

        Scoring:
        - Start at 1.0 (fully compliant)
        - -PROHIBITED_PENALTY per prohibited phrase
        - -BORDERLINE_PENALTY per borderline phrase
        - Minimum 0.0

        Args:
            flagged_phrases: List of flagged phrase results

        Returns:
            Float score between 0.0 and 1.0
        """
        score = 1.0

        for result in flagged_phrases:
            if result.status == ComplianceStatus.PROHIBITED:
                score -= ComplianceScoring.PROHIBITED_PENALTY
            elif result.status == ComplianceStatus.BORDERLINE:
                score -= ComplianceScoring.BORDERLINE_PENALTY

        return max(0.0, score)

    def _get_prohibited_explanation(self, category: str) -> str:
        """Get explanation text for prohibited phrase category."""
        explanations = {
            "treatment_claim": (
                "Health treatment claims are prohibited under EU Health Claims "
                "Regulation. Only medicines can claim to treat conditions."
            ),
            "cure_claim": (
                "Cure claims are strictly prohibited. No food or supplement "
                "can claim to cure any condition."
            ),
            "prevention_claim": (
                "Disease prevention claims require specific EFSA authorization "
                "under Article 14. No approved claims exist for functional mushrooms."
            ),
            "disease_reference": (
                "Referencing specific diseases implies treatment capability, "
                "which is prohibited for food supplements."
            ),
        }
        return explanations.get(category, "Prohibited health claim detected.")

    def _get_borderline_explanation(self, category: str) -> str:
        """Get explanation text for borderline phrase category."""
        explanations = {
            "function_claim": (
                "Function claims (e.g., 'supports', 'promotes') require EFSA "
                "authorization under Article 13. No approved claims exist for "
                "functional mushrooms. Consider using lifestyle language instead."
            ),
            "general_benefit": (
                "General health benefit claims need authorization. Rephrase using "
                "lifestyle or cultural context language."
            ),
        }
        return explanations.get(category, "Borderline health claim - consider rephrasing.")

    async def classify_phrase(self, phrase: str) -> ComplianceResult:
        """Classify a single phrase for compliance.

        When LLM client is available, uses LLM for nuanced classification.
        Otherwise falls back to pattern matching.

        Args:
            phrase: Single phrase to classify

        Returns:
            ComplianceResult with classification
        """
        # Try LLM-based classification first if available
        if self.llm_client:
            try:
                llm_results = await self._llm_enhanced_check(phrase)
                if llm_results:
                    return llm_results[0]
            except Exception as e:
                # Log but fall back to pattern matching
                logger.warning("LLM phrase classification failed, using patterns: %s", e)

        # Pattern-based classification (fallback)
        return self._classify_phrase_patterns(phrase)

    def _classify_phrase_patterns(self, phrase: str) -> ComplianceResult:
        """Classify a phrase using pattern matching only.

        Args:
            phrase: Single phrase to classify

        Returns:
            ComplianceResult with classification
        """
        # Check prohibited first (higher priority)
        for pattern_info in self.rules.prohibited_patterns:
            pattern = pattern_info["pattern"]
            if re.search(r'\b' + re.escape(pattern.lower()) + r'\b', phrase.lower()):
                return ComplianceResult(
                    phrase=phrase,
                    status=ComplianceStatus.PROHIBITED,
                    explanation=self._get_prohibited_explanation(pattern_info["category"]),
                    regulation_reference=RegulationRef.ARTICLE_10
                )

        # Check borderline
        for pattern_info in self.rules.borderline_patterns:
            pattern = pattern_info["pattern"]
            if re.search(r'\b' + re.escape(pattern.lower()) + r'\b', phrase.lower()):
                return ComplianceResult(
                    phrase=phrase,
                    status=ComplianceStatus.BORDERLINE,
                    explanation=self._get_borderline_explanation(pattern_info["category"]),
                    regulation_reference=RegulationRef.ARTICLE_13
                )

        # Check permitted patterns
        for pattern_info in self.rules.permitted_patterns:
            pattern = pattern_info["pattern"]
            if re.search(r'\b' + re.escape(pattern.lower()) + r'\b', phrase.lower()):
                return ComplianceResult(
                    phrase=phrase,
                    status=ComplianceStatus.PERMITTED,
                    explanation="Content uses permitted lifestyle/cultural language.",
                    regulation_reference=RegulationRef.NO_CLAIM
                )

        # Default to permitted if no patterns match
        return ComplianceResult(
            phrase=phrase,
            status=ComplianceStatus.PERMITTED,
            explanation="No health claims detected in phrase.",
            regulation_reference=RegulationRef.NO_CLAIM
        )

    # Sync version for backwards compatibility
    def classify_phrase_sync(self, phrase: str) -> ComplianceResult:
        """Synchronous phrase classification using patterns only.

        Use this when you need sync classification without LLM.

        Args:
            phrase: Single phrase to classify

        Returns:
            ComplianceResult with classification
        """
        return self._classify_phrase_patterns(phrase)
