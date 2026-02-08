# Story 3.6: Content Compliance & Rewrite Suggestions

Status: done

---

## Story

As an **operator**,
I want generated content checked for EU compliance with rewrite suggestions,
So that I can quickly fix issues without manual rewording.

---

## Acceptance Criteria

1. **Given** a caption is generated
   **When** EU Compliance Checker (Epic 1) evaluates it
   **Then** it returns: overall status, flagged phrases, severity per phrase
   **And** compliance check completes in < 10 seconds

2. **Given** content contains BORDERLINE phrases
   **When** the rewrite suggester runs
   **Then** it proposes compliant alternatives:
   - "supports healthy metabolism" -> keep (borderline acceptable)
   - "treats brain fog" -> "supports mental clarity"
   - "cures fatigue" -> "helps you feel refreshed"
   **And** suggestions maintain brand voice

3. **Given** content is REJECTED
   **When** rewrite suggestions are generated
   **Then** all prohibited phrases have alternatives
   **And** operator can accept suggestions with one click
   **And** re-validation runs automatically after edits

---

## Tasks / Subtasks

- [x] Task 1: Create ComplianceRewriteSuggester class (AC: #2, #3)
  - [x] 1.1 Create `teams/dawo/generators/compliance_rewrite/` package structure
  - [x] 1.2 Implement `ComplianceRewriteSuggesterProtocol` for testability
  - [x] 1.3 Implement `ComplianceRewriteSuggester` class with constructor injection pattern
  - [x] 1.4 Accept `EUComplianceChecker`, `BrandProfile`, `LLMClient` via injection
  - [x] 1.5 Create `RewriteRequest` and `RewriteResult` dataclasses
  - [x] 1.6 Export all types in `__init__.py` with complete `__all__` list

- [x] Task 2: Implement rewrite suggestion generation (AC: #2)
  - [x] 2.1 Create `prompts.py` with rewrite system prompt for Norwegian compliance
  - [x] 2.2 Build context from flagged phrase, severity, and regulation reference
  - [x] 2.3 Generate 2-3 alternative phrasings per flagged phrase
  - [x] 2.4 Apply DAWO brand voice constraints to suggestions (warm, educational, Nordic)
  - [x] 2.5 Preserve surrounding caption context in suggestions
  - [x] 2.6 Handle both Norwegian and English content

- [x] Task 3: Implement phrase-level replacement logic (AC: #2, #3)
  - [x] 3.1 Create `RewriteSuggestion` dataclass with original, suggestions, selected fields
  - [x] 3.2 Implement `generate_suggestions()` for single phrase
  - [x] 3.3 Implement `generate_all_suggestions()` for full content with multiple issues
  - [x] 3.4 Preserve phrase positions for accurate replacement
  - [x] 3.5 Handle overlapping flagged phrases gracefully

- [x] Task 4: Implement "keep as-is" logic for borderline phrases (AC: #2)
  - [x] 4.1 Analyze borderline phrases for acceptable vs. needs-change
  - [x] 4.2 "supports healthy metabolism" type phrases -> suggest keep with explanation
  - [x] 4.3 "promotes disease prevention" type phrases -> require rewrite
  - [x] 4.4 Apply EU regulation context from `RegulationRef` constants
  - [x] 4.5 Provide risk assessment for borderline "keep" decisions

- [x] Task 5: Implement content reconstruction (AC: #3)
  - [x] 5.1 Create `apply_suggestion()` to replace single phrase in content
  - [x] 5.2 Create `apply_all_suggestions()` for batch replacement
  - [x] 5.3 Maintain original content structure, hashtags, and formatting
  - [x] 5.4 Handle word count adjustments (rewritten phrases may differ in length)
  - [x] 5.5 Preserve emojis and special characters correctly

- [x] Task 6: Integrate with EU Compliance Checker (AC: #1)
  - [x] 6.1 Accept `ContentComplianceCheck` result as input
  - [x] 6.2 Process `flagged_phrases` list from compliance check
  - [x] 6.3 Use `ComplianceStatus` enum (PROHIBITED, BORDERLINE, PERMITTED)
  - [x] 6.4 Prioritize PROHIBITED phrases for rewrite generation
  - [x] 6.5 Include compliance `regulation_reference` in suggestion context

- [x] Task 7: Implement re-validation loop (AC: #3)
  - [x] 7.1 After applying suggestions, call `EUComplianceChecker.check_content()`
  - [x] 7.2 If still non-compliant, generate additional suggestions
  - [x] 7.3 Maximum 3 re-validation iterations to prevent infinite loops
  - [x] 7.4 Track validation history in result for audit trail
  - [x] 7.5 Return final compliance status with all changes made

- [x] Task 8: Register ComplianceRewriteSuggester in team_spec.py (AC: #1, #2, #3)
  - [x] 8.1 Add `ComplianceRewriteSuggester` as RegisteredAgent with tier="generate"
  - [x] 8.2 Add capability tags: "compliance_rewrite", "content_rewrite", "eu_compliance"
  - [x] 8.3 Register as service for injection

- [x] Task 9: Create unit tests
  - [x] 9.1 Test suggestion generation for prohibited phrases
  - [x] 9.2 Test suggestion generation for borderline phrases
  - [x] 9.3 Test "keep as-is" logic for acceptable borderline phrases
  - [x] 9.4 Test content reconstruction with applied suggestions
  - [x] 9.5 Test re-validation loop (mock compliance checker)
  - [x] 9.6 Test Norwegian content handling
  - [x] 9.7 Test brand voice compliance in suggestions
  - [x] 9.8 Test < 10 second performance requirement

- [x] Task 10: Create integration tests
  - [x] 10.1 Test end-to-end rewrite flow with real compliance checker
  - [x] 10.2 Test with sample captions containing violations
  - [x] 10.3 Test re-validation confirms suggestions are compliant

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Implementation-Patterns], [project-context.md#Agent-Registration]

This story creates the Compliance Rewrite Suggester that works with the existing EU Compliance Checker from Epic 1. Follow the existing patterns from:
- `teams/dawo/validators/eu_compliance/` - Compliance checker with `ContentComplianceCheck` result type
- `teams/dawo/generators/instagram_caption/` - Generator agent pattern with prompts.py
- `teams/dawo/validators/brand_voice/` - Brand voice validation integration

**Key Pattern:** This is a **generator** agent (creates content) not a validator. It generates compliant alternatives for non-compliant phrases while maintaining brand voice.

### Existing EU Compliance Checker Interface (MUST USE)

**Source:** [teams/dawo/validators/eu_compliance/agent.py]

The EU Compliance Checker provides these types that must be used:

```python
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ComplianceStatus,         # PROHIBITED, BORDERLINE, PERMITTED
    OverallStatus,            # COMPLIANT, WARNING, REJECTED
    ComplianceResult,         # Individual phrase result
    ContentComplianceCheck,   # Full check result
    RegulationRef,            # EC 1924/2006 references
    LLMClient,                # Protocol for LLM calls
)

# ContentComplianceCheck structure:
@dataclass
class ContentComplianceCheck:
    overall_status: OverallStatus
    flagged_phrases: list[ComplianceResult]  # Phrases needing rewrites
    novel_food_check: Optional[NovelFoodCheck]
    compliance_score: float  # 0.0-1.0
    llm_enhanced: bool

# ComplianceResult structure (input for rewrite):
@dataclass
class ComplianceResult:
    phrase: str                    # The flagged phrase with context
    status: ComplianceStatus       # PROHIBITED or BORDERLINE
    explanation: str               # Why it was flagged
    regulation_reference: str      # E.g., "EC 1924/2006 Article 10"
```

### File Structure (MUST FOLLOW)

**Source:** [architecture.md#Agent-Package-Structure]

```
teams/dawo/generators/
├── __init__.py                       # Add ComplianceRewriteSuggester exports
├── compliance_rewrite/               # NEW package
│   ├── __init__.py                   # Package exports with __all__
│   ├── agent.py                      # ComplianceRewriteSuggester class
│   ├── prompts.py                    # Rewrite system prompts (Norwegian + English)
│   ├── schemas.py                    # RewriteRequest, RewriteResult, RewriteSuggestion
│   └── utils.py                      # Content reconstruction utilities
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

```python
# CORRECT: Use tier name for registration
tier=TIER_GENERATE  # Maps to Sonnet for quality rewrite generation

# FORBIDDEN in code/docstrings/comments:
# - "haiku", "sonnet", "opus"
# - "claude-haiku", "claude-sonnet", "claude-opus"
# - Any hardcoded model IDs
```

### Rewrite Suggestion Schema Design

**Source:** Design based on AC requirements

```python
# schemas.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from teams.dawo.validators.eu_compliance import ComplianceStatus, ComplianceResult

@dataclass
class RewriteSuggestion:
    """A single phrase rewrite suggestion."""
    original_phrase: str
    status: ComplianceStatus          # PROHIBITED or BORDERLINE
    regulation_reference: str          # E.g., "EC 1924/2006 Article 10"
    explanation: str                   # Why original was flagged
    suggestions: list[str]             # 2-3 compliant alternatives
    keep_recommendation: Optional[str] # If borderline is acceptable, explain why
    selected: Optional[str] = None     # User's chosen alternative (for apply)
    start_position: int = 0            # For accurate replacement
    end_position: int = 0

@dataclass
class RewriteRequest:
    """Input for rewrite suggestion generation."""
    content: str                       # Full caption/content
    compliance_check: ContentComplianceCheck  # From EU Compliance Checker
    brand_profile: BrandProfile        # For brand voice in suggestions
    language: str = "no"               # "no" for Norwegian, "en" for English

@dataclass
class RewriteResult:
    """Output from rewrite suggestion generation."""
    original_content: str
    suggestions: list[RewriteSuggestion]
    all_prohibited_addressed: bool     # All PROHIBITED have suggestions
    rewritten_content: Optional[str]   # Content with selected suggestions applied
    validation_history: list[ContentComplianceCheck]  # Track re-validations
    final_status: OverallStatus        # After applying suggestions
    generation_time_ms: int
    created_at: datetime
```

### Rewrite System Prompt (prompts.py)

**Source:** Design based on DAWO brand voice and EU compliance requirements

```python
REWRITE_SYSTEM_PROMPT_NO = """Du er en ekspert på EU helsepåstandsforskriften (EC 1924/2006) og DAWO merkevare.

OPPGAVE:
Skriv om forbudte eller grensesprengende fraser til EU-kompatible alternativer som opprettholder DAWO sin stemme.

DAWO MERKEVARE STEMME:
- Varm og inviterende, ikke korporativ
- Utdannende først, salg kommer naturlig
- Nordisk enkelhet - rent, autentisk, ærlig

OMSKRIVING REGLER:
1. For FORBUDTE fraser (behandling, kur, helbrede):
   - Skriv om til livsstilsspråk eller kulturell kontekst
   - Fjern all medisinsk terminologi
   - Fokuser på velvære og tradisjon, ikke behandling

2. For GRENSESPRENGENDE fraser (støtter, fremmer):
   - Vurder om den kan beholdes med forklaring
   - Hvis for sterk, skriv om til mildere språk
   - Unngå spesifikke helsepåstander uten EFSA-godkjenning

3. Behold:
   - Samme lengde og flyt som originalen
   - DAWO merkevare tone
   - Naturlige overganger i setningen

UTGANGSFORMAT (per frase):
ORIGINAL: [flagget frase]
FORSLAG1: [omskrevet alternativ 1]
FORSLAG2: [omskrevet alternativ 2]
FORSLAG3: [omskrevet alternativ 3]
BEGRUNNELSE: [hvorfor originalene var problematisk og forslagene er trygge]
"""

REWRITE_SYSTEM_PROMPT_EN = """You are an expert on EU Health Claims Regulation (EC 1924/2006) and the DAWO brand.

TASK:
Rewrite prohibited or borderline phrases into EU-compliant alternatives that maintain DAWO's voice.

DAWO BRAND VOICE:
- Warm and inviting, never corporate
- Educational first, sales come naturally
- Nordic simplicity - clean, authentic, honest

REWRITE RULES:
1. For PROHIBITED phrases (treats, cures, heals):
   - Rewrite to lifestyle language or cultural context
   - Remove all medical terminology
   - Focus on wellness and tradition, not treatment

2. For BORDERLINE phrases (supports, promotes):
   - Assess if it can be kept with explanation
   - If too strong, rewrite to softer language
   - Avoid specific health claims without EFSA approval

3. Maintain:
   - Same length and flow as original
   - DAWO brand tone
   - Natural sentence transitions

OUTPUT FORMAT (per phrase):
ORIGINAL: [flagged phrase]
SUGGESTION1: [rewritten alternative 1]
SUGGESTION2: [rewritten alternative 2]
SUGGESTION3: [rewritten alternative 3]
RATIONALE: [why originals were problematic and suggestions are safe]
"""
```

### Rewrite Examples (from AC)

**Source:** [epics.md#Story-3.6]

| Original (Problematic) | Rewritten (Compliant) | Status |
|----------------------|---------------------|--------|
| "supports healthy metabolism" | KEEP as-is | BORDERLINE (acceptable) |
| "treats brain fog" | "supports mental clarity" | PROHIBITED -> fixed |
| "cures fatigue" | "helps you feel refreshed" | PROHIBITED -> fixed |
| "prevents cognitive decline" | "traditional brain wellness" | PROHIBITED -> fixed |
| "boosts immune system" | "part of a balanced lifestyle" | BORDERLINE -> fixed |

### Norwegian-Specific Rewrite Examples

**Source:** [config/dawo_brand_profile.json#norwegian]

| Norwegian Original | Rewritten | Type |
|-------------------|-----------|------|
| "behandler hjernetåke" | "støtter mental klarhet" | PROHIBITED |
| "kurerer utmattelse" | "hjelper deg å føle deg uthvilt" | PROHIBITED |
| "lindrer stress" | "del av en balansert livsstil" | BORDERLINE |
| "fremmer immunitet" | "tradisjonell nordisk velvære" | BORDERLINE |

### Content Reconstruction Pattern

**Source:** Design based on requirements

```python
# utils.py
from typing import Optional

def apply_suggestion(
    content: str,
    suggestion: RewriteSuggestion,
    selected_index: int = 0
) -> str:
    """Apply a single suggestion to content.

    Args:
        content: Original content text
        suggestion: The RewriteSuggestion with alternatives
        selected_index: Which suggestion to apply (0, 1, or 2)

    Returns:
        Content with phrase replaced
    """
    if selected_index >= len(suggestion.suggestions):
        raise ValueError(f"Invalid suggestion index: {selected_index}")

    replacement = suggestion.suggestions[selected_index]

    # Use position-based replacement for accuracy
    if suggestion.start_position and suggestion.end_position:
        return (
            content[:suggestion.start_position] +
            replacement +
            content[suggestion.end_position:]
        )

    # Fallback to string replacement
    return content.replace(suggestion.original_phrase, replacement, 1)


def apply_all_suggestions(
    content: str,
    suggestions: list[RewriteSuggestion],
    selections: dict[int, int]  # suggestion_index -> selected_alternative
) -> str:
    """Apply multiple suggestions to content.

    Applies in reverse position order to maintain accurate offsets.

    Args:
        content: Original content
        suggestions: List of RewriteSuggestion objects
        selections: Map of suggestion index to selected alternative index

    Returns:
        Fully rewritten content
    """
    # Sort by position descending to maintain offsets
    sorted_suggestions = sorted(
        enumerate(suggestions),
        key=lambda x: x[1].start_position,
        reverse=True
    )

    result = content
    for idx, suggestion in sorted_suggestions:
        selected = selections.get(idx, 0)  # Default to first suggestion
        result = apply_suggestion(result, suggestion, selected)

    return result
```

### Re-validation Loop Pattern

**Source:** Design based on AC #3 requirements

```python
async def suggest_with_revalidation(
    self,
    content: str,
    max_iterations: int = 3
) -> RewriteResult:
    """Generate suggestions and revalidate until compliant.

    Args:
        content: Content to make compliant
        max_iterations: Max revalidation attempts

    Returns:
        RewriteResult with final compliant content
    """
    validation_history = []
    current_content = content

    for iteration in range(max_iterations):
        # Check compliance
        compliance = await self._compliance_checker.check_content(current_content)
        validation_history.append(compliance)

        if compliance.overall_status == OverallStatus.COMPLIANT:
            # Success - content is compliant
            return RewriteResult(
                original_content=content,
                suggestions=[],
                all_prohibited_addressed=True,
                rewritten_content=current_content,
                validation_history=validation_history,
                final_status=OverallStatus.COMPLIANT,
                ...
            )

        # Generate suggestions for flagged phrases
        suggestions = await self._generate_suggestions(
            current_content,
            compliance.flagged_phrases
        )

        # Apply first suggestion for each (auto-fix mode)
        current_content = apply_all_suggestions(
            current_content,
            suggestions,
            {i: 0 for i in range(len(suggestions))}
        )

    # Max iterations reached - return best effort
    final_check = await self._compliance_checker.check_content(current_content)
    validation_history.append(final_check)

    return RewriteResult(
        original_content=content,
        suggestions=suggestions,
        all_prohibited_addressed=False,
        rewritten_content=current_content,
        validation_history=validation_history,
        final_status=final_check.overall_status,
        ...
    )
```

### ComplianceRewriteSuggester Agent Pattern

**Source:** [teams/dawo/generators/instagram_caption/agent.py]

```python
# agent.py
from typing import Optional, Protocol
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ContentComplianceCheck,
    ComplianceResult,
    ComplianceStatus,
    OverallStatus,
    LLMClient,
)
from teams.dawo.validators.brand_voice import BrandProfile

from .prompts import REWRITE_SYSTEM_PROMPT_NO, REWRITE_SYSTEM_PROMPT_EN
from .schemas import RewriteRequest, RewriteResult, RewriteSuggestion
from .utils import apply_suggestion, apply_all_suggestions

logger = logging.getLogger(__name__)


class ComplianceRewriteSuggesterProtocol(Protocol):
    """Protocol for compliance rewrite suggester."""

    async def suggest_rewrites(
        self,
        request: RewriteRequest
    ) -> RewriteResult:
        """Generate compliant rewrite suggestions."""
        ...

    async def suggest_with_revalidation(
        self,
        content: str,
        brand_profile: BrandProfile,
        language: str = "no",
        max_iterations: int = 3
    ) -> RewriteResult:
        """Generate suggestions and revalidate until compliant."""
        ...


class ComplianceRewriteSuggester:
    """Generates EU-compliant rewrite suggestions for flagged content.

    Uses the 'generate' tier (defaults to Sonnet) for quality rewrites.
    Configuration is received via dependency injection - NEVER loads config directly.

    Attributes:
        compliance_checker: EU Compliance Checker for validation
        brand_profile: DAWO brand guidelines for voice consistency
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

        Args:
            request: RewriteRequest with content and compliance check

        Returns:
            RewriteResult with suggestions for each flagged phrase
        """
        start_time = datetime.now(timezone.utc)
        suggestions = []

        # Process each flagged phrase
        for flagged in request.compliance_check.flagged_phrases:
            if flagged.status == ComplianceStatus.PERMITTED:
                continue  # Skip permitted phrases

            suggestion = await self._generate_suggestion(
                flagged,
                request.content,
                request.language
            )
            suggestions.append(suggestion)

        # Check if all prohibited phrases have suggestions
        all_prohibited_addressed = all(
            len(s.suggestions) > 0 or s.keep_recommendation
            for s in suggestions
            if s.status == ComplianceStatus.PROHIBITED
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
            created_at=datetime.now(timezone.utc),
        )

    async def _generate_suggestion(
        self,
        flagged: ComplianceResult,
        full_content: str,
        language: str
    ) -> RewriteSuggestion:
        """Generate suggestion for a single flagged phrase."""
        # Select language-appropriate prompt
        system_prompt = (
            REWRITE_SYSTEM_PROMPT_NO if language == "no"
            else REWRITE_SYSTEM_PROMPT_EN
        )

        # Build generation prompt
        prompt = f"""Skriv om denne frasen til EU-kompatible alternativer:

FRASE: {flagged.phrase}
STATUS: {flagged.status.value}
FORKLARING: {flagged.explanation}
REGULERING: {flagged.regulation_reference}

KONTEKST: {full_content[:500]}...

Generer 3 alternative formuleringer."""

        try:
            response = await self._llm.generate(
                prompt=prompt,
                system=system_prompt
            )
            return self._parse_suggestion_response(response, flagged)
        except Exception as e:
            logger.error("Failed to generate suggestion: %s", e)
            # Return empty suggestion on error
            return RewriteSuggestion(
                original_phrase=flagged.phrase,
                status=flagged.status,
                regulation_reference=flagged.regulation_reference,
                explanation=flagged.explanation,
                suggestions=[],
                keep_recommendation=None,
            )
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [3-3-instagram-caption-generator.md], [3-5-nano-banana-ai-image-generation.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Export ComplianceRewriteSuggester, Protocol, all schemas |
| Config injection pattern | Accept EUComplianceChecker, BrandProfile, LLMClient via constructor |
| `datetime` deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | Log all LLM and rewrite errors before returning fallback |
| F-string logging anti-pattern | Use `%` formatting: `logger.error("Rewrite failed: %s", e)` |
| Integration tests separate | Create test_integration.py with env var skip markers |
| < 10 second performance | Track generation time, optimize for speed |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER instantiate EUComplianceChecker internally** - Accept via constructor injection
2. **NEVER load brand profile from file** - Accept BrandProfile via injection
3. **NEVER hardcode model names** - Use tier system
4. **NEVER swallow exceptions without logging** - Log all errors
5. **NEVER generate suggestions that violate EU compliance** - Always validate
6. **NEVER exceed 10 second generation time** - Monitor and optimize

### Test Fixtures

**Source:** [tests/teams/dawo/generators/test_instagram_caption/conftest.py] patterns

```python
# tests/teams/dawo/generators/test_compliance_rewrite/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from teams.dawo.validators.eu_compliance import (
    ContentComplianceCheck,
    ComplianceResult,
    ComplianceStatus,
    OverallStatus,
    RegulationRef,
)

@pytest.fixture
def mock_compliance_checker():
    """Mock EUComplianceChecker for rewrite tests."""
    checker = AsyncMock()
    checker.check_content.return_value = ContentComplianceCheck(
        overall_status=OverallStatus.COMPLIANT,
        flagged_phrases=[],
        novel_food_check=None,
        compliance_score=1.0,
        llm_enhanced=False,
    )
    return checker

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for suggestion generation."""
    client = AsyncMock()
    client.generate.return_value = """
ORIGINAL: behandler hjernetåke
FORSLAG1: støtter mental klarhet
FORSLAG2: bidrar til kognitiv velvære
FORSLAG3: fremmer mentalt fokus
BEGRUNNELSE: Original brukte medisinsk terminologi (behandler) som er forbudt.
"""
    return client

@pytest.fixture
def sample_flagged_content():
    """Sample content with compliance violations."""
    return ContentComplianceCheck(
        overall_status=OverallStatus.REJECTED,
        flagged_phrases=[
            ComplianceResult(
                phrase="behandler hjernetåke",
                status=ComplianceStatus.PROHIBITED,
                explanation="Treatment claims prohibited under EC 1924/2006",
                regulation_reference=RegulationRef.ARTICLE_10,
            ),
            ComplianceResult(
                phrase="støtter immunforsvaret",
                status=ComplianceStatus.BORDERLINE,
                explanation="Function claim requires EFSA approval",
                regulation_reference=RegulationRef.ARTICLE_13,
            ),
        ],
        novel_food_check=None,
        compliance_score=0.4,
        llm_enhanced=True,
    )

@pytest.fixture
def sample_rewrite_request(sample_flagged_content, mock_brand_profile):
    """Sample rewrite request for tests."""
    return RewriteRequest(
        content="Løvemanke behandler hjernetåke og støtter immunforsvaret naturlig.",
        compliance_check=sample_flagged_content,
        brand_profile=mock_brand_profile,
        language="no",
    )
```

### Registration in team_spec.py

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py (add to existing registrations)

from teams.dawo.generators.compliance_rewrite import (
    ComplianceRewriteSuggester,
    ComplianceRewriteSuggesterProtocol,
)

AGENTS: List[RegisteredAgent] = [
    # ... existing agents ...
    RegisteredAgent(
        name="compliance_rewrite_suggester",
        agent_class=ComplianceRewriteSuggester,
        capabilities=["compliance_rewrite", "content_rewrite", "eu_compliance"],
        tier=TIER_GENERATE,  # Uses Sonnet for quality rewrites
    ),
]
```

### Integration with Caption Generator (Story 3.3)

**Source:** [3-3-instagram-caption-generator.md]

The rewrite suggester integrates into the content generation pipeline:

```python
# In content generation flow
caption = await caption_generator.generate(request)

# Check compliance
compliance_check = await eu_checker.check_content(caption.caption_text)

if compliance_check.overall_status != OverallStatus.COMPLIANT:
    # Generate rewrite suggestions
    rewrite_result = await rewrite_suggester.suggest_rewrites(
        RewriteRequest(
            content=caption.caption_text,
            compliance_check=compliance_check,
            brand_profile=brand_profile,
            language="no",
        )
    )

    # Attach suggestions to caption result for operator review
    caption.rewrite_suggestions = rewrite_result.suggestions
    caption.compliance_status = compliance_check.overall_status
```

### Project Structure Notes

- **Location**: `teams/dawo/generators/compliance_rewrite/` (new package)
- **Dependencies**: EUComplianceChecker (Epic 1), BrandProfile, LLMClient
- **Used by**: CaptionGenerator (Story 3.3), Content Team orchestrator, Approval UI
- **LLM Tier**: generate (maps to Sonnet for quality)
- **Performance**: < 10 seconds per rewrite generation
- **Languages**: Norwegian (primary), English (supported)

### References

- [Source: epics.md#Story-3.6] - Original story requirements (FR14)
- [Source: architecture.md#Agent-Package-Structure] - Package patterns
- [Source: project-context.md#EU-Compliance] - Compliance requirements
- [Source: project-context.md#LLM-Tier-Assignment] - Tier system
- [Source: teams/dawo/validators/eu_compliance/] - Compliance checker integration
- [Source: teams/dawo/validators/brand_voice/] - Brand voice validation
- [Source: 3-3-instagram-caption-generator.md] - Caption generator patterns
- [Source: 3-5-nano-banana-ai-image-generation.md] - Previous story learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - all tests pass

### Completion Notes List

- Implemented ComplianceRewriteSuggester as a generator agent following existing patterns
- Created comprehensive prompts for Norwegian and English content with DAWO brand voice
- Integrated with EU Compliance Checker via dependency injection (Protocol pattern)
- Implemented re-validation loop with max 3 iterations and full validation history
- Created 44 tests (43 passing, 1 skipped) covering all acceptance criteria
- Added borderline phrase analysis with keep-as-is recommendations for acceptable phrases
- Position-based phrase replacement for accurate content reconstruction
- Registered agent in team_spec.py with tier=TIER_GENERATE and appropriate capability tags
- Code review fixes: position-0 bug, TYPE_CHECKING pattern, logging improvements

### File List

**New Files:**
- teams/dawo/generators/compliance_rewrite/__init__.py
- teams/dawo/generators/compliance_rewrite/agent.py
- teams/dawo/generators/compliance_rewrite/schemas.py
- teams/dawo/generators/compliance_rewrite/prompts.py
- teams/dawo/generators/compliance_rewrite/utils.py
- tests/teams/dawo/generators/test_compliance_rewrite/__init__.py
- tests/teams/dawo/generators/test_compliance_rewrite/conftest.py
- tests/teams/dawo/generators/test_compliance_rewrite/test_unit.py
- tests/teams/dawo/generators/test_compliance_rewrite/test_integration.py

**Modified Files:**
- teams/dawo/generators/__init__.py (added ComplianceRewriteSuggester exports)
- teams/dawo/team_spec.py (registered ComplianceRewriteSuggester agent)

**Files Modified by Code Review Fixes:**
- teams/dawo/generators/compliance_rewrite/utils.py (position-0 bug fix, sorting edge case)
- teams/dawo/generators/compliance_rewrite/schemas.py (TYPE_CHECKING pattern for BrandProfile)
- teams/dawo/generators/compliance_rewrite/agent.py (datetime consistency, logging, docs)

---

## Change Log

- 2026-02-08: Story created by Scrum Master with comprehensive dev context
- 2026-02-08: Story implemented by Dev Agent - all tasks complete, 43 tests passing
- 2026-02-08: Code review completed - 9 issues fixed (3 HIGH, 4 MEDIUM, 2 LOW)
