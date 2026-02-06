# Story 1.3: Brand Voice Validator

Status: done

---

## Story

As an **operator**,
I want content checked against DAWO brand guidelines,
So that all published content maintains consistent voice and authenticity.

---

## Acceptance Criteria

1. **Given** content text is submitted for brand validation
   **When** the Brand Voice Validator evaluates the content
   **Then** it checks tone against DAWO profile: warm, educational, Nordic simplicity
   **And** it flags AI-generic language that lacks human feel
   **And** it verifies no medicinal terminology is used
   **And** it returns validation status: `PASS`, `NEEDS_REVISION`, or `FAIL`
   **And** failed content includes specific revision suggestions

2. **Given** the brand profile exists at `config/dawo_brand_profile.json`
   **When** the validator initializes
   **Then** it loads configuration via dependency injection (not direct file load)
   **And** config includes: tone keywords, forbidden terms, style examples

3. **Given** the validator is registered
   **When** Team Builder requests brand validation capability
   **Then** AgentRegistry returns the Brand Voice Validator instance
   **And** the validator uses the `generate` tier (defaults to Sonnet for judgment quality)

---

## Tasks / Subtasks

- [x] Task 1: Create Brand Voice agent package structure (AC: #3)
  - [x] 1.1 Create `teams/dawo/validators/brand_voice/` directory
  - [x] 1.2 Create `teams/dawo/validators/brand_voice/__init__.py` with exports
  - [x] 1.3 Create `teams/dawo/validators/brand_voice/agent.py` with BrandVoiceValidator class
  - [x] 1.4 Create `teams/dawo/validators/brand_voice/prompts.py` with system prompts
  - [x] 1.5 Create `teams/dawo/validators/brand_voice/profile.py` with profile loading logic

- [x] Task 2: Define validation result types (AC: #1)
  - [x] 2.1 Define `ValidationStatus` enum: PASS, NEEDS_REVISION, FAIL
  - [x] 2.2 Define `BrandIssue` dataclass with: phrase, issue_type, suggestion
  - [x] 2.3 Define `BrandValidationResult` dataclass with: status, issues, score
  - [x] 2.4 Define `IssueType` enum: TONE_MISMATCH, AI_GENERIC, MEDICINAL_TERM, STYLE_VIOLATION

- [x] Task 3: Implement tone validation logic (AC: #1)
  - [x] 3.1 Implement warm tone detection (friendly, inviting language)
  - [x] 3.2 Implement educational tone detection (informative, not salesy)
  - [x] 3.3 Implement Nordic simplicity detection (clean, minimal, authentic)
  - [x] 3.4 Create prompt template that guides LLM to evaluate brand voice

- [x] Task 4: Implement AI-generic language detection (AC: #1)
  - [x] 4.1 Define AI-generic patterns (cliches, perfect structure, corporate speak)
  - [x] 4.2 Implement pattern matching for common AI tells
  - [x] 4.3 Create scoring mechanism for human authenticity (0.0-1.0)
  - [x] 4.4 Generate specific suggestions to humanize flagged content

- [x] Task 5: Implement medicinal terminology filter (AC: #1)
  - [x] 5.1 Load forbidden medical terms from brand profile config
  - [x] 5.2 Implement pattern matching for medicinal language
  - [x] 5.3 Cross-reference with EU Compliance Checker results if available
  - [x] 5.4 Generate compliant alternative suggestions

- [x] Task 6: Create brand profile configuration (AC: #2)
  - [x] 6.1 Create `config/dawo_brand_profile.json` with full specification
  - [x] 6.2 Include tone_keywords: warm, educational, Nordic descriptors
  - [x] 6.3 Include forbidden_terms: medicinal and sales language
  - [x] 6.4 Include style_examples: good vs bad content samples
  - [x] 6.5 Include ai_generic_patterns: common AI writing tells

- [x] Task 7: Register agent in team_spec.py (AC: #3)
  - [x] 7.1 Import BrandVoiceValidator in `teams/dawo/team_spec.py`
  - [x] 7.2 Add RegisteredAgent entry with capabilities=["brand_voice", "content_validation"]
  - [x] 7.3 Set tier="generate" (not hardcoded model name)
  - [x] 7.4 Update validators `__init__.py` to export the agent

- [x] Task 8: Create comprehensive tests
  - [x] 8.1 Test warm tone detection (positive and negative cases)
  - [x] 8.2 Test educational tone detection
  - [x] 8.3 Test Nordic simplicity detection
  - [x] 8.4 Test AI-generic language flagging
  - [x] 8.5 Test medicinal terminology rejection
  - [x] 8.6 Test revision suggestion generation
  - [x] 8.7 Test config injection (not direct file loading)
  - [x] 8.8 Test LLM integration with mocks

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Agent-Package-Structure]

The Brand Voice Validator MUST follow complex agent package structure:

```
teams/dawo/validators/brand_voice/
├── __init__.py           # Exports BrandVoiceValidator and all types
├── agent.py              # Main agent class
├── prompts.py            # System prompts for LLM evaluation
└── profile.py            # Profile loading from config/
```

### Agent Implementation Pattern (MUST FOLLOW)

**Source:** [project-context.md#Agent-Registration], [1-2-eu-compliance-checker-validator.md]

```python
# teams/dawo/validators/brand_voice/agent.py
from typing import List, Optional, Protocol
from dataclasses import dataclass
from enum import Enum

class ValidationStatus(Enum):
    PASS = "pass"
    NEEDS_REVISION = "needs_revision"
    FAIL = "fail"

class IssueType(Enum):
    TONE_MISMATCH = "tone_mismatch"
    AI_GENERIC = "ai_generic"
    MEDICINAL_TERM = "medicinal_term"
    STYLE_VIOLATION = "style_violation"

@dataclass
class BrandIssue:
    phrase: str
    issue_type: IssueType
    severity: str  # "low", "medium", "high"
    suggestion: str
    explanation: str

@dataclass
class BrandValidationResult:
    status: ValidationStatus
    issues: List[BrandIssue]
    brand_score: float  # 0.0-1.0 (1.0 = perfect brand alignment)
    authenticity_score: float  # 0.0-1.0 (1.0 = very human, 0.0 = very AI)
    tone_analysis: dict  # {"warm": 0.8, "educational": 0.7, "nordic": 0.6}

class LLMClient(Protocol):
    """Protocol for LLM client injection (same as EU Compliance)."""
    async def generate(self, prompt: str, system: str = None) -> str:
        ...

class BrandVoiceValidator:
    """DAWO brand voice and authenticity validator.

    Validates content for brand consistency, human authenticity,
    and absence of medicinal terminology.
    Uses 'generate' tier (defaults to Sonnet) for judgment quality.
    """

    def __init__(
        self,
        brand_profile: dict,
        llm_client: Optional[LLMClient] = None
    ):
        """Accept config via dependency injection - NEVER load directly."""
        self.profile = brand_profile
        self.llm_client = llm_client

    async def validate_content(self, content: str) -> BrandValidationResult:
        """Main validation entry point."""
        pass

    def validate_content_sync(self, content: str) -> BrandValidationResult:
        """Synchronous pattern-only validation (no LLM)."""
        pass
```

### Registration Pattern (MUST FOLLOW)

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py - ADD THIS ENTRY
from teams.dawo.validators.brand_voice import BrandVoiceValidator

AGENTS = [
    # ... existing eu_compliance_checker entry ...
    RegisteredAgent(
        name="brand_voice_validator",
        agent_class=BrandVoiceValidator,
        capabilities=["brand_voice", "content_validation"],
        tier="generate"  # NOT "sonnet" - use tier name
    )
]
```

### DAWO Brand Voice Profile (CRITICAL)

**Source:** PRD, Architecture - DAWO brand identity

**Tone Pillars:**
1. **Warm** - Friendly, inviting, personal (not corporate or cold)
2. **Educational** - Informative first, sales second (not pushy)
3. **Nordic Simplicity** - Clean, minimal, authentic (not cluttered or hyperbolic)

**Language Characteristics:**
- First person plural ("we", "our") for community feel
- Short, clear sentences
- Scandinavian aesthetic references (forest, nature, tradition)
- Understated confidence (no superlatives or hype)
- Human imperfection welcome (contractions, casual tone)

**FORBIDDEN - Medicinal Language:**
- "treatment", "treats", "cure", "heal", "remedy"
- "disease", "illness", "condition", "symptoms"
- "clinical", "therapeutic", "medicinal"
- Any claims that overlap with EU Health Claims violations

**FORBIDDEN - AI-Generic Patterns:**
- "In today's fast-paced world..."
- "Are you looking for..."
- "Look no further!"
- "Game-changer", "Revolutionary", "Best-in-class"
- Perfect parallel structure without variation
- Excessive exclamation marks
- Corporate buzzwords ("leverage", "synergy", "optimize")

### Brand Profile Configuration Schema

**Source:** [architecture.md#Config-Files]

```json
// config/dawo_brand_profile.json
{
  "brand_name": "DAWO",
  "version": "2026-02",
  "tone_pillars": {
    "warm": {
      "description": "Friendly, inviting, personal",
      "positive_markers": ["we", "our", "together", "share", "enjoy", "love"],
      "negative_markers": ["corporation", "enterprise", "consumers", "users"]
    },
    "educational": {
      "description": "Informative first, not salesy",
      "positive_markers": ["learn", "discover", "understand", "explore", "tradition"],
      "negative_markers": ["buy now", "limited time", "act fast", "don't miss"]
    },
    "nordic_simplicity": {
      "description": "Clean, minimal, authentic",
      "positive_markers": ["forest", "nature", "Nordic", "Scandinavian", "pure", "simple"],
      "negative_markers": ["amazing", "incredible", "revolutionary", "game-changer"]
    }
  },
  "forbidden_terms": {
    "medicinal": [
      "treatment", "treats", "cure", "cures", "heal", "heals",
      "remedy", "therapeutic", "clinical", "medicinal",
      "disease", "illness", "condition", "symptoms", "diagnosis"
    ],
    "sales_pressure": [
      "buy now", "limited time", "act fast", "don't miss out",
      "exclusive offer", "hurry", "last chance"
    ],
    "superlatives": [
      "best", "greatest", "most powerful", "ultimate",
      "revolutionary", "game-changer", "breakthrough"
    ]
  },
  "ai_generic_patterns": [
    "In today's fast-paced world",
    "Are you looking for",
    "Look no further",
    "Whether you're a .* or .*",
    "It's no secret that",
    "At the end of the day",
    "Take your .* to the next level",
    "Unlock your potential",
    "Transform your"
  ],
  "style_examples": {
    "good": [
      "We've been foraging in Nordic forests for generations. Lion's mane has been part of that journey.",
      "Simple ingredients. Honest sourcing. That's what we believe in.",
      "Some days call for a warm cup and quiet moment. Our mushroom blends are made for those days."
    ],
    "bad": [
      "REVOLUTIONARY mushroom supplements that will TRANSFORM your cognitive performance!",
      "Are you looking for the BEST Lion's Mane on the market? Look no further!",
      "Our clinically-proven formula treats brain fog and cures mental fatigue."
    ]
  },
  "scoring_thresholds": {
    "pass": 0.8,
    "needs_revision": 0.5,
    "fail": 0.0
  }
}
```

### Previous Story Learnings (Story 1.2)

**Source:** [1-2-eu-compliance-checker-validator.md#Completion-Notes-List]

**MUST APPLY these learnings:**

1. **LLM Integration** - Add optional `llm_client` parameter implementing `LLMClient` protocol. Use prompts.py templates for nuanced LLM-based validation.

2. **Dual Methods** - Provide both `async validate_content()` (with LLM) and `validate_content_sync()` (pattern-only) methods.

3. **Complete Exports** - Add ALL types to `__all__` in both `__init__.py` files: `BrandVoiceValidator`, `ValidationStatus`, `IssueType`, `BrandIssue`, `BrandValidationResult`, `LLMClient`.

4. **Tier Naming** - Use `tier="generate"` NOT `tier="sonnet"` in registration.

5. **Test Coverage** - Include edge case tests, mock LLM integration tests, word boundary tests.

6. **Constants Pattern** - If referencing external sources repeatedly (e.g., brand guidelines section names), create a constants class.

### Prompt Design Guidelines

**Source:** [1-2-eu-compliance-checker-validator.md#prompts.py]

```python
# teams/dawo/validators/brand_voice/prompts.py

SYSTEM_PROMPT = """You are the DAWO Brand Voice Validator. Your role is to evaluate content for alignment with DAWO's brand identity.

DAWO Brand Pillars:
1. WARM - Friendly, inviting, personal (not corporate)
2. EDUCATIONAL - Informative first, not salesy
3. NORDIC SIMPLICITY - Clean, minimal, authentic

You MUST:
- Score each tone pillar from 0.0 to 1.0
- Identify specific phrases that violate brand guidelines
- Detect AI-generic language that lacks human authenticity
- Flag any medicinal terminology
- Provide specific, actionable revision suggestions

Return your analysis in JSON format."""

VALIDATION_PROMPT = """Evaluate the following content for DAWO brand voice alignment:

CONTENT:
{content}

BRAND PROFILE:
{profile_summary}

FORBIDDEN TERMS:
{forbidden_terms}

AI GENERIC PATTERNS TO FLAG:
{ai_patterns}

Analyze and return JSON with:
1. tone_scores: {{"warm": float, "educational": float, "nordic": float}}
2. authenticity_score: float (0.0=AI-like, 1.0=very human)
3. issues: [{{"phrase": str, "issue_type": str, "severity": str, "suggestion": str}}]
4. overall_status: "pass" | "needs_revision" | "fail"
"""
```

### Integration with EU Compliance Checker

**Source:** [architecture.md#Cross-Component-Dependencies]

The Brand Voice Validator should NOT duplicate medicinal term detection that EU Compliance Checker already does. Instead:

1. Accept optional `eu_compliance_result` in `validate_content()` to avoid redundant checks
2. If EU compliance flagged medicinal terms, reference those instead of re-detecting
3. Focus Brand Voice on tone, style, and authenticity - let EU Compliance handle regulatory language

```python
async def validate_content(
    self,
    content: str,
    eu_compliance_result: Optional['ContentComplianceCheck'] = None
) -> BrandValidationResult:
    """Main validation with optional EU compliance context."""
    pass
```

### Testing Requirements

**Source:** [architecture.md#Tests]

Create tests in `tests/teams/dawo/test_validators/test_brand_voice.py`:

```python
# Test categories required:
class TestToneValidation:
    def test_warm_tone_positive(self): ...
    def test_warm_tone_negative(self): ...
    def test_educational_tone_positive(self): ...
    def test_educational_tone_negative(self): ...
    def test_nordic_simplicity_positive(self): ...
    def test_nordic_simplicity_negative(self): ...

class TestAIGenericDetection:
    def test_flags_common_ai_openings(self): ...
    def test_flags_corporate_buzzwords(self): ...
    def test_flags_excessive_superlatives(self): ...
    def test_accepts_natural_writing(self): ...

class TestMedicinalTermFilter:
    def test_flags_treatment_language(self): ...
    def test_flags_disease_references(self): ...
    def test_accepts_wellness_language(self): ...

class TestRevisionSuggestions:
    def test_provides_specific_alternatives(self): ...
    def test_suggestions_maintain_meaning(self): ...

class TestConfigInjection:
    def test_accepts_profile_via_constructor(self): ...
    def test_rejects_direct_file_loading(self): ...

class TestLLMIntegration:
    async def test_uses_llm_when_provided(self): ...
    def test_falls_back_to_patterns_without_llm(self): ...
```

### Technology Stack Context

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Use type hints, dataclasses, enums, Protocol |
| Agent Framework | Google ADK | BaseAgent pattern if available |
| LLM | Sonnet (via generate tier) | For accurate judgment |
| Config | JSON | Loaded via dependency injection |
| Testing | pytest | Async tests with `pytest-asyncio` |

### Project Structure Reference

```
teams/dawo/
├── __init__.py
├── team_spec.py                    # Add brand_voice_validator here
├── validators/
│   ├── __init__.py                 # Export brand_voice module
│   ├── eu_compliance/              # Already exists (Story 1.2)
│   │   └── ...
│   └── brand_voice/                # CREATE THIS
│       ├── __init__.py
│       ├── agent.py
│       ├── prompts.py
│       └── profile.py

config/
├── dawo_compliance_rules.json      # Already exists (Story 1.2)
└── dawo_brand_profile.json         # CREATE THIS

tests/teams/dawo/test_validators/
├── __init__.py                     # Already exists
├── test_eu_compliance.py           # Already exists
└── test_brand_voice.py             # CREATE THIS
```

---

## References

- [Source: architecture.md#Agent-Package-Structure] - Complex agent package layout
- [Source: architecture.md#DAWO-Agent-Patterns] - Registration and config patterns
- [Source: project-context.md#Agent-Registration] - RegisteredAgent usage
- [Source: project-context.md#Configuration-Loading] - Dependency injection pattern
- [Source: epics.md#Story-1.3] - Original story requirements
- [Source: 1-2-eu-compliance-checker-validator.md] - Previous story learnings and LLM integration pattern

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

No debug issues encountered during implementation.

### Completion Notes List

1. **Package Structure**: Created complete brand_voice package following complex agent pattern from EU Compliance Checker
2. **RED-GREEN-REFACTOR**: Followed TDD cycle - tests written first (42 tests), then implementation to make them pass
3. **Tone Analysis**: Implemented pillar-based scoring (warm, educational, nordic) with positive/negative marker detection
4. **AI Detection**: Regex-based pattern matching for common AI writing tells with authenticity scoring (0.0-1.0)
5. **Medicinal Filter**: Word-boundary matching for forbidden medical terms with compliant alternative suggestions
6. **Dual Methods**: Both async `validate_content()` (with LLM) and sync `validate_content_sync()` (pattern-only) methods
7. **Config Injection**: Validator accepts brand_profile dict via constructor - never loads files directly
8. **EU Integration**: Optional `eu_compliance_result` parameter to avoid duplicate medicinal term detection
9. **LLM Protocol**: Uses same `LLMClient` Protocol pattern as EU Compliance Checker for consistency
10. **Tests**: 42 tests covering all acceptance criteria - all passing with no regressions (107 total validator tests)

### Change Log

- 2026-02-06: Story 1.3 implementation complete - Brand Voice Validator with full test coverage
- 2026-02-06: Code review fixes applied (9 issues - 3 HIGH, 4 MEDIUM, 2 LOW):
  - ISSUE #1 [HIGH]: Implemented eu_compliance_result cross-referencing (was unused parameter)
  - ISSUE #2 [HIGH]: Integrated profile.py module (was dead code - now exported and validated)
  - ISSUE #3 [HIGH]: Documented LLMClient Protocol sharing between validators
  - ISSUE #4 [MEDIUM]: Added logging for exception handling (was silent swallowing)
  - ISSUE #5 [MEDIUM]: Added 11 new tests for profile.py module (was 0% coverage)
  - ISSUE #6 [MEDIUM]: Strengthened 3 weak test assertions (removed OR logic)
  - ISSUE #7 [MEDIUM]: Extracted magic numbers to ScoringWeights constants class
  - ISSUE #8 [LOW]: Removed duplicate AI tells (were in both code and config)
  - ISSUE #9 [LOW]: Enhanced ScoringWeights docstring with full attribute documentation

### File List

- [x] `teams/dawo/validators/brand_voice/__init__.py` - Package exports (BrandVoiceValidator, ValidationStatus, IssueType, BrandIssue, BrandValidationResult, LLMClient, ScoringWeights, BrandProfile, TonePillar, validate_profile) **[UPDATED: code review - added profile exports]**
- [x] `teams/dawo/validators/brand_voice/agent.py` - Main BrandVoiceValidator class with ScoringWeights constants, logging, EU compliance integration **[UPDATED: code review - 9 fixes]**
- [x] `teams/dawo/validators/brand_voice/prompts.py` - LLM prompt templates (BRAND_SYSTEM_PROMPT, VALIDATION_PROMPT_TEMPLATE)
- [x] `teams/dawo/validators/brand_voice/profile.py` - BrandProfile dataclass and validation utilities **[NOW INTEGRATED]**
- [x] `config/dawo_brand_profile.json` - Brand profile configuration (tone_pillars, forbidden_terms, ai_generic_patterns, style_examples)
- [x] `teams/dawo/team_spec.py` (update) - Added brand_voice_validator registration with tier="generate"
- [x] `teams/dawo/validators/__init__.py` (update) - Added brand_voice exports including profile types, documented LLMClient sharing **[UPDATED: code review]**
- [x] `tests/teams/dawo/test_validators/test_brand_voice.py` - 53 comprehensive tests (all passing) **[UPDATED: code review - added 11 profile tests, strengthened assertions]**
