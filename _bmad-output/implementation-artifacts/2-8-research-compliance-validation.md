# Story 2.8: Research Compliance Validation

Status: done

---

## Story

As an **operator**,
I want all research validated for EU compliance before pool entry,
So that only safe-to-use research fuels content creation.

---

## Acceptance Criteria

1. **Given** a research item completes harvester processing
   **When** the validator stage runs
   **Then** it calls EU Compliance Checker (from Epic 1)
   **And** it evaluates extracted insights for prohibited claims
   **And** it sets compliance_status on the research item

2. **Given** research contains prohibited language
   **When** compliance check returns REJECTED
   **Then** the item still enters pool (for awareness)
   **And** it's marked with compliance_status=REJECTED
   **And** content teams see warning when viewing

3. **Given** research cites a scientific study
   **When** compliance check runs
   **Then** study citations with DOI links are marked COMPLIANT
   **And** study claims without links are marked WARNING

---

## Tasks / Subtasks

- [x] Task 1: Create shared ResearchComplianceValidator component (AC: #1, #2, #3)
  - [x] 1.1 Create `teams/dawo/validators/research_compliance/` directory structure
  - [x] 1.2 Create `__init__.py` with complete exports and `__all__` list
  - [x] 1.3 Create `validator.py` with `ResearchComplianceValidator` class
  - [x] 1.4 Create `schemas.py` with `ComplianceValidationResult`, `ValidationContext` schemas
  - [x] 1.5 Accept `EUComplianceChecker` via dependency injection (Story 1.2)

- [x] Task 2: Implement core validation logic (AC: #1)
  - [x] 2.1 Create `validate(research_item: TransformedResearch) -> ValidatedResearch` method
  - [x] 2.2 Extract text content to validate (title, summary, content, source_metadata insights)
  - [x] 2.3 Call EU Compliance Checker for each text field
  - [x] 2.4 Aggregate compliance results across all validated fields
  - [x] 2.5 Determine overall compliance_status from aggregated results
  - [x] 2.6 Add logging for validation statistics (passed, warned, rejected)

- [x] Task 3: Implement scientific citation detection (AC: #3)
  - [x] 3.1 Create `detect_scientific_citation(text: str, source_metadata: dict) -> CitationInfo`
  - [x] 3.2 Check for DOI patterns in text and metadata
  - [x] 3.3 Check for PMID patterns in source_metadata
  - [x] 3.4 Check for study URL patterns (pubmed, doi.org, etc.)
  - [x] 3.5 Return CitationInfo with has_doi, has_pmid, has_url flags

- [x] Task 4: Implement compliance status determination (AC: #1, #2, #3)
  - [x] 4.1 If any field is PROHIBITED and no scientific citation → REJECTED
  - [x] 4.2 If any field is PROHIBITED but has valid DOI/PMID → WARNING (can cite, not claim)
  - [x] 4.3 If all fields BORDERLINE with citation → WARNING
  - [x] 4.4 If all fields PERMITTED or neutral → COMPLIANT
  - [x] 4.5 Add compliance_notes explaining the status determination

- [x] Task 5: Implement batch validation (AC: #1)
  - [x] 5.1 Create `validate_batch(items: list[TransformedResearch]) -> list[ValidatedResearch]`
  - [x] 5.2 Process items concurrently with asyncio.gather
  - [x] 5.3 Handle individual item failures without failing the batch
  - [x] 5.4 Track validation statistics: total, compliant, warned, rejected, failed
  - [x] 5.5 Return partial results even if some items fail

- [x] Task 6: Implement source-specific validation rules (AC: #3)
  - [x] 6.1 For source="pubmed": Always has citation, default to COMPLIANT if no prohibited claims
  - [x] 6.2 For source="reddit/youtube/instagram/news": Apply stricter validation
  - [x] 6.3 Add source-based score adjustment recommendations in result
  - [x] 6.4 Scientific sources get compliance boost, social sources get stricter checking

- [x] Task 7: Integrate with scanner validators (AC: #1, #2)
  - [x] 7.1 Update RedditValidator (2.3) to use ResearchComplianceValidator
  - [x] 7.2 Update YouTubeValidator (2.4) to use ResearchComplianceValidator
  - [x] 7.3 Update InstagramValidator (2.5) to use ResearchComplianceValidator
  - [x] 7.4 Update NewsValidator (2.6) to use ResearchComplianceValidator
  - [x] 7.5 Update PubMedValidator (2.7) to use ResearchComplianceValidator
  - [x] 7.6 Ensure all validators inject ResearchComplianceValidator via Team Builder

- [x] Task 8: Register in team_spec.py (AC: #1)
  - [x] 8.1 Add `ResearchComplianceValidator` as RegisteredService
  - [x] 8.2 Add capability tag "research_compliance" for Team Builder resolution
  - [x] 8.3 Ensure dependency on EUComplianceChecker is documented

- [x] Task 9: Create comprehensive unit tests
  - [x] 9.1 Test validation of clean research (no claims) → COMPLIANT
  - [x] 9.2 Test validation of research with prohibited claims → REJECTED
  - [x] 9.3 Test validation of research with DOI and prohibited claims → WARNING
  - [x] 9.4 Test validation of research with borderline claims → WARNING
  - [x] 9.5 Test citation detection (DOI patterns, PMID patterns, URLs)
  - [x] 9.6 Test batch validation with mixed results
  - [x] 9.7 Test source-specific rules (pubmed vs reddit)
  - [x] 9.8 Test graceful handling of malformed input
  - [x] 9.9 Mock EU Compliance Checker responses

- [x] Task 10: Create integration tests
  - [x] 10.1 Test full pipeline: research → compliance validation → pool entry
  - [x] 10.2 Test scanner integration (one scanner as example)
  - [x] 10.3 Test that REJECTED items still enter pool with warning flag
  - [x] 10.4 Test compliance_status visible in Research Pool queries

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Shared-Agent-Strategy], [project-context.md#Agent-Registration]

This story creates a **SHARED COMPONENT** that all research scanners use for compliance validation. It bridges the EU Compliance Checker (Story 1.2) with the Harvester Framework validators.

**Key Insight:** This is NOT a standalone scanner - it's a validation service that existing scanner validators call. The goal is to ensure consistent EU compliance checking across ALL research sources.

### Package Structure (MUST FOLLOW)

**Source:** [project-context.md#Directory-Structure], [architecture.md#DAWO-Team-Structure]

```
teams/dawo/
├── validators/
│   ├── eu_compliance/         # EXISTS from Story 1.2
│   ├── brand_voice/           # EXISTS from Story 1.3
│   └── research_compliance/   # CREATE THIS MODULE
│       ├── __init__.py
│       ├── validator.py       # ResearchComplianceValidator
│       └── schemas.py         # ComplianceValidationResult, CitationInfo, etc.
├── scanners/
│   ├── reddit/                # Story 2.3 - UPDATE validator to use this
│   ├── youtube/               # Story 2.4 - UPDATE validator to use this
│   ├── instagram/             # Story 2.5 - UPDATE validator to use this
│   ├── news/                  # Story 2.6 - UPDATE validator to use this
│   └── pubmed/                # Story 2.7 - UPDATE validator to use this

tests/teams/dawo/
└── test_validators/
    ├── test_eu_compliance/    # EXISTS from Story 1.2
    └── test_research_compliance/   # CREATE THIS
        ├── __init__.py
        ├── conftest.py
        ├── test_validator.py
        ├── test_citation_detection.py
        ├── test_batch_validation.py
        └── test_integration.py
```

### Integration with EU Compliance Checker

**Source:** [1-2-eu-compliance-checker-validator.md], [project-context.md#EU-Compliance]

```python
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ComplianceResult,
    ComplianceStatus,  # COMPLIANT, WARNING, REJECTED
    FlaggedPhrase,
)
```

**EU Compliance Checker provides:**
- `check(text: str) -> ComplianceResult`
- Returns: overall_status, flagged_phrases (list of FlaggedPhrase with phrase, severity, explanation)
- Uses Sonnet tier for accuracy

### Research Compliance Validator Design

**Source:** [epics.md#Story-2.8], [project-context.md#Harvester-Framework]

```python
# validator.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

@dataclass
class CitationInfo:
    """Information about scientific citations in research."""
    has_doi: bool
    has_pmid: bool
    has_url: bool
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None

    @property
    def has_citation(self) -> bool:
        """Returns True if any citation is present."""
        return self.has_doi or self.has_pmid or self.has_url

@dataclass
class ComplianceValidationResult:
    """Result from research compliance validation."""
    compliance_status: ComplianceStatus  # COMPLIANT, WARNING, REJECTED
    citation_info: CitationInfo
    flagged_phrases: list[FlaggedPhrase]
    compliance_notes: str
    source_type: str
    validated_at: datetime

class ResearchComplianceValidator:
    """Validates research items for EU compliance before pool entry.

    Bridges EU Compliance Checker (Story 1.2) with all scanner validators.
    Applies source-specific rules and citation detection.
    """

    # DOI pattern: 10.xxxx/xxxxx
    DOI_PATTERN = re.compile(r'10\.\d{4,}/[^\s]+')
    # PMID pattern: 8+ digit number
    PMID_PATTERN = re.compile(r'(?:PMID|pmid)[:\s]*(\d{7,})|(?:^|\s)(\d{8,})(?:\s|$)')
    # Scientific URL patterns
    SCIENTIFIC_URL_PATTERNS = [
        re.compile(r'pubmed\.ncbi\.nlm\.nih\.gov/\d+'),
        re.compile(r'doi\.org/10\.\d{4,}'),
        re.compile(r'ncbi\.nlm\.nih\.gov/pmc/articles/PMC\d+'),
    ]

    def __init__(
        self,
        compliance_checker: EUComplianceChecker
    ):
        """Accept compliance checker via injection from Team Builder."""
        self._compliance_checker = compliance_checker

    async def validate(
        self,
        research_item: TransformedResearch
    ) -> ValidatedResearch:
        """Validate single research item for EU compliance.

        Args:
            research_item: Transformed research from scanner

        Returns:
            ValidatedResearch with compliance_status set
        """
        # Detect citations first
        citation_info = self._detect_citation(
            text=research_item.content,
            source_metadata=research_item.source_metadata
        )

        # Validate all text content
        texts_to_check = [
            research_item.title,
            research_item.summary or "",
            research_item.content,
        ]

        # Extract any insights from metadata
        if research_item.source_metadata:
            if "key_findings" in research_item.source_metadata:
                texts_to_check.append(research_item.source_metadata["key_findings"])

        # Check each text field
        all_flagged: list[FlaggedPhrase] = []
        worst_status = ComplianceStatus.COMPLIANT

        for text in texts_to_check:
            if not text:
                continue
            result = await self._compliance_checker.check(text)
            all_flagged.extend(result.flagged_phrases)
            if result.overall_status.value > worst_status.value:
                worst_status = result.overall_status

        # Apply citation-based adjustment
        final_status = self._determine_final_status(
            base_status=worst_status,
            citation_info=citation_info,
            source_type=research_item.source
        )

        # Build compliance notes
        notes = self._build_compliance_notes(
            status=final_status,
            citation_info=citation_info,
            flagged_count=len(all_flagged),
            source_type=research_item.source
        )

        return ValidatedResearch(
            **research_item.__dict__,
            compliance_status=final_status,
            compliance_notes=notes,
            flagged_phrases=all_flagged,
            has_scientific_citation=citation_info.has_citation,
        )

    def _detect_citation(
        self,
        text: str,
        source_metadata: Optional[dict]
    ) -> CitationInfo:
        """Detect scientific citations in research."""
        has_doi = False
        has_pmid = False
        has_url = False
        doi = None
        pmid = None
        url = None

        # Check text for DOI
        doi_match = self.DOI_PATTERN.search(text)
        if doi_match:
            has_doi = True
            doi = doi_match.group(0)

        # Check metadata for DOI/PMID
        if source_metadata:
            if "doi" in source_metadata and source_metadata["doi"]:
                has_doi = True
                doi = source_metadata["doi"]
            if "pmid" in source_metadata and source_metadata["pmid"]:
                has_pmid = True
                pmid = source_metadata["pmid"]

        # Check for scientific URLs
        for pattern in self.SCIENTIFIC_URL_PATTERNS:
            url_match = pattern.search(text)
            if url_match:
                has_url = True
                url = url_match.group(0)
                break

        return CitationInfo(
            has_doi=has_doi,
            has_pmid=has_pmid,
            has_url=has_url,
            doi=doi,
            pmid=pmid,
            url=url,
        )

    def _determine_final_status(
        self,
        base_status: ComplianceStatus,
        citation_info: CitationInfo,
        source_type: str
    ) -> ComplianceStatus:
        """Determine final compliance status with citation adjustment.

        Rules:
        - REJECTED + citation → WARNING (can cite, not claim)
        - PubMed source + no REJECTED → COMPLIANT (always has citation)
        - BORDERLINE → WARNING
        - PERMITTED → COMPLIANT
        """
        # PubMed sources are inherently citable
        if source_type == "pubmed":
            if base_status == ComplianceStatus.REJECTED:
                # Even PubMed can have prohibited language in abstracts
                # But we can cite the study, just can't use the claim
                return ComplianceStatus.WARNING
            return ComplianceStatus.COMPLIANT

        # Other sources with citations
        if citation_info.has_citation:
            if base_status == ComplianceStatus.REJECTED:
                # Has citation, downgrade to WARNING
                return ComplianceStatus.WARNING
            return base_status

        # No citation, use base status
        return base_status

    def _build_compliance_notes(
        self,
        status: ComplianceStatus,
        citation_info: CitationInfo,
        flagged_count: int,
        source_type: str
    ) -> str:
        """Build human-readable compliance notes."""
        notes = []

        if status == ComplianceStatus.COMPLIANT:
            notes.append("Content passed EU compliance check.")
        elif status == ComplianceStatus.WARNING:
            notes.append(f"Content has {flagged_count} flagged phrase(s).")
            if citation_info.has_citation:
                notes.append("Scientific citation present - can cite study but cannot make health claims.")
        else:  # REJECTED
            notes.append(f"Content contains {flagged_count} prohibited phrase(s).")
            notes.append("Cannot be used for marketing claims.")

        if source_type == "pubmed":
            notes.append("Source: Peer-reviewed scientific publication.")

        return " ".join(notes)

    async def validate_batch(
        self,
        items: list[TransformedResearch]
    ) -> list[ValidatedResearch]:
        """Validate batch of research items concurrently.

        Args:
            items: List of transformed research items

        Returns:
            List of validated items (partial results if some fail)
        """
        import asyncio

        async def validate_single(item: TransformedResearch) -> Optional[ValidatedResearch]:
            try:
                return await self.validate(item)
            except Exception as e:
                logger.error("Failed to validate item %s: %s", item.source_id, e)
                return None

        results = await asyncio.gather(
            *[validate_single(item) for item in items],
            return_exceptions=False
        )

        # Filter out None results from failures
        validated = [r for r in results if r is not None]

        # Log statistics
        stats = {
            "total": len(items),
            "validated": len(validated),
            "failed": len(items) - len(validated),
            "compliant": sum(1 for r in validated if r.compliance_status == ComplianceStatus.COMPLIANT),
            "warned": sum(1 for r in validated if r.compliance_status == ComplianceStatus.WARNING),
            "rejected": sum(1 for r in validated if r.compliance_status == ComplianceStatus.REJECTED),
        }
        logger.info("Batch validation complete: %s", stats)

        return validated
```

### Scanner Integration Pattern

**Source:** [2-3-reddit-research-scanner.md], [2-7-pubmed-scientific-research-scanner.md]

Each scanner's validator stage should be updated to use `ResearchComplianceValidator`:

```python
# Example: teams/dawo/scanners/reddit/validator.py
class RedditValidator:
    """Validates Reddit research items for pool entry."""

    def __init__(
        self,
        research_compliance: ResearchComplianceValidator
    ):
        """Accept research compliance validator via injection."""
        self._compliance = research_compliance

    async def validate(
        self,
        items: list[TransformedResearch]
    ) -> list[ValidatedResearch]:
        """Validate items using shared compliance validator."""
        return await self._compliance.validate_batch(items)
```

### Compliance Status Values

**Source:** [1-2-eu-compliance-checker-validator.md], [project-context.md#EU-Compliance]

```python
from enum import IntEnum

class ComplianceStatus(IntEnum):
    """Compliance status with ordering for comparison."""
    COMPLIANT = 0   # Green - safe to use
    WARNING = 1     # Yellow - use with caution, add disclaimers
    REJECTED = 2    # Red - cannot use for marketing claims
```

### Research Pool Integration

**Source:** [2-1-research-pool-database-storage.md]

ValidatedResearch items enter the Research Pool with:
- `compliance_status`: COMPLIANT | WARNING | REJECTED
- `compliance_notes`: Human-readable explanation
- `flagged_phrases`: List of specific issues
- `has_scientific_citation`: Boolean for quick filtering

Content teams can:
- Filter by compliance_status to find safe content
- See warnings when viewing REJECTED items
- Use citation info to properly attribute sources

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment], [project-context.md#Code-Review-Checklist]

This validator is **NOT an LLM agent** - it's a service that calls the EU Compliance Checker (which uses tier="generate"). The ResearchComplianceValidator itself does not make LLM calls directly.

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- `claude-haiku`, `claude-sonnet`, `claude-opus`
- Any hardcoded model IDs

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [2-7-pubmed-scientific-research-scanner.md#Previous-Story-Learnings]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | Accept EUComplianceChecker via constructor |
| Use tier terminology ONLY | This validator doesn't use LLM directly - it calls EU Checker |
| datetime deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | All exceptions logged before re-raising |
| Batch processing pattern | Process items concurrently, handle partial failures |
| Integration tests separate | Create test_integration.py with proper fixtures |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], [architecture.md#Anti-Patterns]

1. **NEVER load config directly** - Accept EUComplianceChecker via injection
2. **NEVER duplicate compliance logic** - Use EU Compliance Checker from Story 1.2
3. **NEVER swallow exceptions without logging** - Log all validation failures
4. **NEVER skip items on failure** - Return partial results, track failures

### Exports Template (MUST FOLLOW)

**Source:** [project-context.md#Module-Exports]

```python
# teams/dawo/validators/research_compliance/__init__.py
"""Research Compliance Validator for DAWO research intelligence pipeline."""

from .validator import (
    ResearchComplianceValidator,
    ValidationError,
)
from .schemas import (
    CitationInfo,
    ComplianceValidationResult,
    ValidationContext,
    ValidationStats,
)

__all__ = [
    # Main validator
    "ResearchComplianceValidator",
    # Schemas
    "CitationInfo",
    "ComplianceValidationResult",
    "ValidationContext",
    "ValidationStats",
    # Exceptions
    "ValidationError",
]
```

### Test Fixtures

**Source:** [2-7-pubmed-scientific-research-scanner.md#Test-Fixtures]

```python
# tests/teams/dawo/test_validators/test_research_compliance/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

@pytest.fixture
def mock_eu_compliance_checker():
    """Mock EU Compliance Checker for testing."""
    checker = AsyncMock()
    checker.check.return_value = ComplianceResult(
        overall_status=ComplianceStatus.COMPLIANT,
        flagged_phrases=[],
    )
    return checker

@pytest.fixture
def sample_research_item():
    """Sample TransformedResearch for testing."""
    return TransformedResearch(
        source="pubmed",
        source_id="12345678",
        title="Effects of Lion's Mane on Cognition",
        content="A randomized controlled trial found...",
        summary="Study shows cognitive benefits",
        url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        tags=["lions_mane", "cognition"],
        source_metadata={
            "doi": "10.1234/test.2024",
            "pmid": "12345678",
        },
        created_at=datetime.now(timezone.utc),
    )

@pytest.fixture
def research_with_prohibited_claims():
    """Research item with prohibited health claims."""
    return TransformedResearch(
        source="reddit",
        source_id="abc123",
        title="Lion's mane CURES brain fog!",
        content="I took lion's mane and it cured my brain fog completely.",
        summary="User claims lion's mane cured brain fog",
        url="https://reddit.com/r/Nootropics/abc123",
        tags=["lions_mane"],
        source_metadata={},
        created_at=datetime.now(timezone.utc),
    )

@pytest.fixture
def compliance_validator(mock_eu_compliance_checker):
    """ResearchComplianceValidator with mocked dependencies."""
    return ResearchComplianceValidator(
        compliance_checker=mock_eu_compliance_checker
    )
```

### Project Structure Notes

- **Shared component**: Used by ALL scanner validators, not a standalone scanner
- **Bridges Epic 1 and Epic 2**: Connects EU Compliance Checker (1.2) to Harvester Framework
- **Citation-aware**: Scientific sources get compliance boost
- **Partial failure handling**: Batch validation continues even if items fail
- **Integrates with**: EU Compliance Checker (1.2), all scanners (2.3-2.7), Research Pool (2.1)

### References

- [Source: epics.md#Story-2.8] - Original story requirements
- [Source: architecture.md#Shared-Agent-Strategy] - Shared component pattern
- [Source: project-context.md#EU-Compliance] - Compliance requirements
- [Source: 1-2-eu-compliance-checker-validator.md] - EU Compliance Checker integration
- [Source: 2-1-research-pool-database-storage.md] - Research Pool schema
- [Source: 2-7-pubmed-scientific-research-scanner.md] - Pattern reference (latest scanner)

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (Code Review)

### Debug Log References

- All 43 unit and integration tests pass (pytest)

### Completion Notes List

1. Created ResearchComplianceValidator as shared component bridging EU Compliance Checker (Story 1.2) with all scanner validators
2. Implemented citation detection for DOI, PMID, and scientific URLs (PubMed, doi.org, PMC)
3. Source-specific rules: PubMed sources treated as inherently citable (REJECTED → WARNING)
4. Batch validation with asyncio.gather, partial failure handling, and statistics logging
5. Updated all 5 scanner validators (Reddit, YouTube, Instagram, News, PubMed) to use ResearchComplianceValidator
6. Registered ResearchComplianceValidator as RegisteredService in team_spec.py with "research_compliance" capability
7. Complete test coverage: 43 tests covering validation, citation detection, batch processing, integration

### File List

**New Files (Created):**
- `teams/dawo/validators/research_compliance/__init__.py` - Module exports with `__all__`
- `teams/dawo/validators/research_compliance/validator.py` - ResearchComplianceValidator, ValidatedResearch
- `teams/dawo/validators/research_compliance/schemas.py` - CitationInfo, ValidationStats, ValidationError
- `tests/teams/dawo/test_validators/test_research_compliance/__init__.py`
- `tests/teams/dawo/test_validators/test_research_compliance/conftest.py` - Test fixtures
- `tests/teams/dawo/test_validators/test_research_compliance/test_validator.py` - Core validation tests
- `tests/teams/dawo/test_validators/test_research_compliance/test_citation_detection.py` - Citation detection tests
- `tests/teams/dawo/test_validators/test_research_compliance/test_batch_validation.py` - Batch processing tests
- `tests/teams/dawo/test_validators/test_research_compliance/test_integration.py` - Integration tests

**Modified Files:**
- `teams/dawo/validators/__init__.py` - Added ResearchComplianceValidator exports
- `teams/dawo/scanners/reddit/validator.py` - Uses ResearchComplianceValidator
- `teams/dawo/scanners/youtube/validator.py` - Uses ResearchComplianceValidator
- `teams/dawo/scanners/instagram/validator.py` - Uses ResearchComplianceValidator
- `teams/dawo/scanners/news/validator.py` - Uses ResearchComplianceValidator
- `teams/dawo/scanners/pubmed/validator.py` - Uses ResearchComplianceValidator
- `teams/dawo/team_spec.py` - Added ResearchComplianceValidator registration

