# Story 1.2: EU Compliance Checker Validator

Status: done

---

## Story

As an **operator**,
I want content automatically checked against EU Health Claims Regulation,
So that I never accidentally publish prohibited health claims.

---

## Acceptance Criteria

1. **Given** content text is submitted for compliance checking
   **When** the EU Compliance Checker evaluates the content
   **Then** each phrase is classified as one of: `PROHIBITED`, `BORDERLINE`, `PERMITTED`
   **And** prohibited phrases include: "treats", "cures", "prevents", disease references
   **And** borderline phrases include: "supports", "promotes", "contributes to"
   **And** permitted phrases include: general wellness, lifestyle, study citations with links
   **And** the checker returns overall status: `COMPLIANT`, `WARNING`, or `REJECTED`
   **And** rejected content includes specific flagged phrases with explanations

2. **Given** a product name is included in content
   **When** the checker validates Novel Food classification (FR24)
   **Then** it verifies product is marketed according to its classification (food vs supplement)
   **And** Chaga content is validated as supplement-only messaging

3. **Given** the validator is registered
   **When** Team Builder requests a compliance capability
   **Then** AgentRegistry returns the EU Compliance Checker instance
   **And** the checker uses the `generate` tier (defaults to Sonnet for accuracy)

---

## Tasks / Subtasks

- [x] Task 1: Create EU Compliance agent package structure (AC: #3)
  - [x] 1.1 Create `teams/dawo/validators/eu_compliance/` directory
  - [x] 1.2 Create `teams/dawo/validators/eu_compliance/__init__.py` with exports
  - [x] 1.3 Create `teams/dawo/validators/eu_compliance/agent.py` with EUComplianceChecker class
  - [x] 1.4 Create `teams/dawo/validators/eu_compliance/prompts.py` with system prompts
  - [x] 1.5 Create `teams/dawo/validators/eu_compliance/rules.py` with rule loading logic

- [x] Task 2: Implement phrase classification logic (AC: #1)
  - [x] 2.1 Define `ComplianceResult` dataclass with: phrase, classification, explanation
  - [x] 2.2 Define `ComplianceStatus` enum: PROHIBITED, BORDERLINE, PERMITTED
  - [x] 2.3 Define `OverallStatus` enum: COMPLIANT, WARNING, REJECTED
  - [x] 2.4 Implement `classify_phrase()` method using LLM with rules context
  - [x] 2.5 Implement `check_content()` method returning overall status and flagged phrases

- [x] Task 3: Implement prohibited/borderline/permitted detection (AC: #1)
  - [x] 3.1 Define prohibited patterns: treats, cures, prevents, disease references
  - [x] 3.2 Define borderline patterns: supports, promotes, contributes to
  - [x] 3.3 Define permitted patterns: wellness, lifestyle, study citations with DOI/links
  - [x] 3.4 Create prompt template that guides LLM to apply EU Health Claims rules

- [x] Task 4: Implement Novel Food classification validation (AC: #2)
  - [x] 4.1 Create product classification lookup (food vs supplement)
  - [x] 4.2 Implement Chaga-specific supplement-only validation
  - [x] 4.3 Integrate Novel Food check into main compliance check flow
  - [x] 4.4 Add validation for product-messaging alignment

- [x] Task 5: Register agent in team_spec.py (AC: #3)
  - [x] 5.1 Import EUComplianceChecker in `teams/dawo/team_spec.py`
  - [x] 5.2 Add RegisteredAgent entry with capabilities=["eu_compliance", "content_validation"]
  - [x] 5.3 Set tier="generate" (not hardcoded model name)
  - [x] 5.4 Update validators `__init__.py` to export the agent

- [x] Task 6: Create compliance rules configuration (AC: #1, #2)
  - [x] 6.1 Create `config/dawo_compliance_rules.json` with rule definitions
  - [x] 6.2 Include prohibited_patterns, borderline_patterns, permitted_patterns
  - [x] 6.3 Include novel_food_classifications for DAWO products
  - [x] 6.4 Implement dependency injection for config loading (not direct file read)

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Agent-Package-Structure]

The EU Compliance Checker MUST follow complex agent package structure:

```
teams/dawo/validators/eu_compliance/
├── __init__.py           # Exports EUComplianceChecker
├── agent.py              # Main agent class
├── prompts.py            # System prompts for LLM
└── rules.py              # Rule loading from config/
```

### Agent Implementation Pattern (MUST FOLLOW)

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/validators/eu_compliance/agent.py
from typing import List
from dataclasses import dataclass
from enum import Enum

class ComplianceStatus(Enum):
    PROHIBITED = "prohibited"
    BORDERLINE = "borderline"
    PERMITTED = "permitted"

class OverallStatus(Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    REJECTED = "rejected"

@dataclass
class ComplianceResult:
    phrase: str
    status: ComplianceStatus
    explanation: str
    regulation_reference: str  # e.g., "EC 1924/2006 Article 10"

@dataclass
class ContentComplianceCheck:
    overall_status: OverallStatus
    flagged_phrases: List[ComplianceResult]
    compliance_score: float  # 0.0-1.0

class EUComplianceChecker:
    """EU Health Claims Regulation compliance validator.

    Validates content against EC 1924/2006 and Novel Food regulations.
    Uses 'generate' tier (defaults to Sonnet) for accuracy.
    """

    def __init__(self, compliance_rules: dict):
        """Accept config via dependency injection - NEVER load directly."""
        self.rules = compliance_rules

    async def check_content(self, content: str, product_name: str = None) -> ContentComplianceCheck:
        """Main compliance check entry point."""
        pass
```

### Registration Pattern (MUST FOLLOW)

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py - ADD THIS ENTRY
from teams.dawo.validators.eu_compliance import EUComplianceChecker

AGENTS = [
    RegisteredAgent(
        name="eu_compliance_checker",
        agent_class=EUComplianceChecker,
        capabilities=["eu_compliance", "content_validation"],
        tier="generate"  # NOT "sonnet" - use tier name
    )
]
```

### EU Health Claims Regulation Context (CRITICAL)

**Source:** EC 1924/2006 - Regulation on nutrition and health claims

**Key Rules:**
- **Article 10**: Health claims prohibited unless specifically authorized
- **Article 13**: Functional claims require EFSA approval
- **Article 14**: Disease risk reduction claims require specific authorization

**Functional Mushrooms Status (as of 2026):**
- Lion's Mane: NO approved EU health claims
- Chaga: NO approved EU health claims, classified as Novel Food (supplement only)
- Reishi: NO approved EU health claims
- Cordyceps: NO approved EU health claims
- Shiitake: Food use permitted, NO health claims
- Maitake: Food use permitted, NO health claims

**DAWO Policy:** Zero tolerance for unapproved health claims. All content MUST pass compliance check before approval queue.

### Phrase Classification Examples

| Phrase | Classification | Reason |
|--------|---------------|--------|
| "treats anxiety" | PROHIBITED | Disease treatment claim |
| "cures brain fog" | PROHIBITED | Disease cure claim |
| "prevents cognitive decline" | PROHIBITED | Disease prevention claim |
| "supports mental clarity" | BORDERLINE | Function claim (not EU approved) |
| "promotes focus" | BORDERLINE | Function claim (not EU approved) |
| "contributes to energy" | BORDERLINE | Function claim (not EU approved) |
| "natural wellness ritual" | PERMITTED | Lifestyle, no health claim |
| "Nordic foraging tradition" | PERMITTED | Cultural, no health claim |
| "Study (DOI: 10.xxx) found..." | PERMITTED | Scientific citation with link |

### Configuration Schema

**Source:** [architecture.md#Config-Files]

```json
// config/dawo_compliance_rules.json
{
  "regulation": "EC 1924/2006",
  "version": "2026-02",
  "prohibited_patterns": [
    {"pattern": "treats", "category": "treatment_claim"},
    {"pattern": "cures", "category": "cure_claim"},
    {"pattern": "prevents", "category": "prevention_claim"},
    {"pattern": "heals", "category": "treatment_claim"},
    {"pattern": "fights disease", "category": "treatment_claim"}
  ],
  "borderline_patterns": [
    {"pattern": "supports", "category": "function_claim"},
    {"pattern": "promotes", "category": "function_claim"},
    {"pattern": "contributes to", "category": "function_claim"},
    {"pattern": "helps with", "category": "function_claim"},
    {"pattern": "boosts", "category": "function_claim"}
  ],
  "permitted_patterns": [
    {"pattern": "wellness", "category": "lifestyle"},
    {"pattern": "ritual", "category": "lifestyle"},
    {"pattern": "tradition", "category": "cultural"},
    {"pattern": "DOI:", "category": "scientific_citation"}
  ],
  "novel_food_classifications": {
    "chaga": {"status": "novel_food", "use": "supplement_only"},
    "lions_mane": {"status": "food", "use": "food_or_supplement"},
    "reishi": {"status": "food", "use": "food_or_supplement"},
    "cordyceps": {"status": "novel_food", "use": "supplement_only"},
    "shiitake": {"status": "traditional_food", "use": "food"},
    "maitake": {"status": "traditional_food", "use": "food"}
  }
}
```

### Previous Story Learnings (Story 1.1)

**Source:** [1-1-dawo-team-directory-structure.md#Change-Log]

- Use tier terminology (`generate`) not model names (`sonnet`) in registration
- Include `__all__` exports in all `__init__.py` files
- Use type-safe placeholders (dataclass) when platform integration pending
- Validate Python syntax before marking complete
- Platform Test Team doesn't exist - follow patterns from architecture.md

### Technology Stack Context

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Use type hints, dataclasses, enums |
| Agent Framework | Google ADK | BaseAgent pattern if available |
| LLM | Sonnet (via generate tier) | For accurate judgment |
| Config | JSON | Loaded via dependency injection |

### Testing Requirements

Create tests in `tests/teams/dawo/test_validators/test_eu_compliance.py`:
- Test prohibited phrase detection
- Test borderline phrase detection
- Test permitted phrase detection
- Test overall status calculation (COMPLIANT, WARNING, REJECTED)
- Test Novel Food classification validation
- Test Chaga supplement-only validation
- Test config injection (not direct loading)

---

## References

- [Source: architecture.md#Agent-Package-Structure] - Complex agent package layout
- [Source: architecture.md#DAWO-Agent-Patterns] - Registration and config patterns
- [Source: project-context.md#Agent-Registration] - RegisteredAgent usage
- [Source: project-context.md#EU-Compliance] - Zero tolerance policy
- [Source: epics.md#Story-1.2] - Original story requirements
- [Source: 1-1-dawo-team-directory-structure.md] - Previous story learnings
- EC 1924/2006 - EU Health Claims Regulation
- EC 2015/2283 - Novel Food Regulation

---

## Senior Developer Review (AI)

**Review Date:** 2026-02-06
**Reviewer:** Claude Opus 4.5 (Adversarial Code Review)
**Review Outcome:** Changes Requested → Fixed

### Issues Found and Fixed

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | CRITICAL | prompts.py imported but never used - no LLM integration | ✅ FIXED |
| 2 | CRITICAL | Task 2.4 marked [x] but classify_phrase() didn't use LLM | ✅ FIXED |
| 3 | HIGH | NovelFoodCheck dataclass not exported in __init__.py | ✅ FIXED |
| 4 | HIGH | Async/sync inconsistency in classify_phrase methods | ✅ FIXED |
| 5 | MEDIUM | project-context.md showed tier="sonnet" (wrong example) | ✅ FIXED |
| 6 | MEDIUM | Hardcoded regulation references (Article 10/13) | ✅ FIXED |
| 7 | LOW | Missing word boundary edge case tests | ✅ FIXED |

### Fixes Applied

1. **Added LLM integration** - EUComplianceChecker now accepts optional `llm_client` parameter implementing `LLMClient` protocol. When provided, uses prompts.py templates for nuanced LLM-based classification alongside pattern matching.

2. **Added RegulationRef constants** - All regulation references now use `RegulationRef.ARTICLE_10`, `RegulationRef.ARTICLE_13`, etc. instead of hardcoded strings.

3. **Fixed exports** - Added `NovelFoodCheck`, `RegulationRef`, `LLMClient` to `__all__` in both `__init__.py` files.

4. **Added async classify_phrase** - Now supports both async (with LLM) and sync (`classify_phrase_sync`) versions.

5. **Fixed project-context.md** - Changed example from `tier="sonnet"` to `tier="generate"` with clarifying comment.

6. **Added 25 new tests** - Word boundary edge cases, RegulationRef constants, LLM integration with mocks.

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- All Python files pass syntax validation
- 65/65 pytest tests pass (expanded from 40)
- pytest run: `python -m pytest tests/teams/dawo/test_validators/test_eu_compliance.py -v`

### Completion Notes List

- Created EU Compliance Checker agent package with 4 files following complex agent pattern
- Implemented phrase classification with ComplianceStatus enum (PROHIBITED, BORDERLINE, PERMITTED)
- Implemented overall status calculation (COMPLIANT, WARNING, REJECTED)
- Implemented Novel Food classification validation with Chaga supplement-only enforcement
- Created comprehensive compliance rules config with 30+ prohibited patterns, 27 borderline patterns
- Registered agent in team_spec.py with tier="generate" (not hardcoded model name)
- Created 65 comprehensive tests covering all acceptance criteria
- Used dependency injection pattern for config loading (never direct file load)
- Applied learnings from Story 1.1: tier naming, `__all__` exports, type-safe dataclasses
- **[Code Review]** Added LLM integration with optional client and LLMClient protocol
- **[Code Review]** Added RegulationRef constants class for maintainable regulation references
- **[Code Review]** Exported NovelFoodCheck, RegulationRef, LLMClient in package __init__.py
- **[Code Review]** Added classify_phrase_sync() for synchronous pattern-only classification
- **[Code Review]** Fixed project-context.md tier example from "sonnet" to "generate"
- **[Code Review]** Added 25 new tests: word boundaries, constants, LLM integration

### Change Log

- 2026-02-05: Initial implementation of EU Compliance Checker Validator
- 2026-02-06: Code review fixes - LLM integration, RegulationRef constants, exports, edge case tests
- 2026-02-06: Adversarial LOW review - 5 issues fixed:
  - L1: Added ComplianceScoring constants class (PROHIBITED_PENALTY, BORDERLINE_PENALTY)
  - L2: Added logging to `_llm_enhanced_check()` exception handler (was silent)
  - L3: Added logging to `classify_phrase()` exception handler (was silent)
  - L4: Added `import logging` and module logger setup
  - L5: Added CONTEXT_WINDOW_CHARS constant for context extraction (was magic number 20)
  - Added 3 new tests for ComplianceScoring constants
  - Exported ComplianceScoring from package __init__.py files

### File List

- [x] `teams/dawo/validators/eu_compliance/__init__.py` - Package exports (updated: +NovelFoodCheck, RegulationRef, LLMClient)
- [x] `teams/dawo/validators/eu_compliance/agent.py` - Main EUComplianceChecker class (updated: +LLM integration, +RegulationRef)
- [x] `teams/dawo/validators/eu_compliance/prompts.py` - LLM prompt templates
- [x] `teams/dawo/validators/eu_compliance/rules.py` - ComplianceRules configuration manager
- [x] `config/dawo_compliance_rules.json` - Compliance rules configuration
- [x] `teams/dawo/team_spec.py` (update) - Added agent registration
- [x] `teams/dawo/validators/__init__.py` (update) - Added exports (+NovelFoodCheck, RegulationRef, LLMClient)
- [x] `tests/__init__.py` - Test package init
- [x] `tests/teams/__init__.py` - Test package init
- [x] `tests/teams/dawo/__init__.py` - Test package init
- [x] `tests/teams/dawo/test_validators/__init__.py` - Test package init
- [x] `tests/teams/dawo/test_validators/test_eu_compliance.py` - 65 comprehensive tests (updated: +25 new tests)
- [x] `_bmad-output/project-context.md` (update) - Fixed tier example from "sonnet" to "generate"
