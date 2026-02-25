# Story 5.1: B2B Lead Research Scanner

Status: done

---

## Story

As an **operator**,
I want potential B2B retail partners automatically discovered,
So that I have a steady pipeline of qualified leads without manual research.

---

## Acceptance Criteria

1. **Given** the B2B scanner is scheduled (weekly Monday 7 AM)
   **When** it executes
   **Then** it searches configured sources for: health food stores, wellness retailers, specialty grocers
   **And** it filters by: location (Norway/Nordic), size indicators, online presence
   **And** it collects: business name, location, website, contact info if public

2. **Given** a potential lead is discovered
   **When** the harvester processes it
   **Then** it extracts: company name, address, website URL, social profiles
   **And** it validates the business is relevant (health/wellness focus)
   **And** it checks for existing relationship in lead database (no duplicates)

3. **Given** a lead passes initial filtering
   **When** it enters the pipeline
   **Then** status is set to `NEW`
   **And** lead record is created with discovery timestamp
   **And** it's queued for enrichment (Story 5.2)

---

## Tasks / Subtasks

- [x] Task 1: Create B2B lead scanner agent structure (AC: #1, #2)
  - [x] 1.1 Create `teams/dawo/leads/` directory structure
  - [x] 1.2 Create `teams/dawo/leads/scanner/` module directory
  - [x] 1.3 Create `__init__.py` with complete exports
  - [x] 1.4 Create `agent.py` with `B2BLeadScanner` class
  - [x] 1.5 Create `tools.py` with search tools (Hunter.io API)
  - [x] 1.6 Create `config.py` with `LeadScannerConfig` dataclass
  - [x] 1.7 Create `schemas.py` with `RawLead`, `HarvestedLead`, `ScanResult` schemas

- [x] Task 2: Implement Hunter.io API client (AC: #1, #3)
  - [x] 2.1 Create `HunterClient` class in `tools.py`
  - [x] 2.2 Accept config via dependency injection (api_key)
  - [x] 2.3 Implement `domain_search(domain: str) -> dict` - Find emails at domain
  - [x] 2.4 Implement `email_finder(domain: str, first_name: str, last_name: str) -> dict`
  - [x] 2.5 Implement `email_verifier(email: str) -> dict` - Verify email deliverability
  - [x] 2.6 Implement `account_info() -> dict` - Get account usage info
  - [x] 2.7 Add rate limiting (respect Hunter.io limits based on plan)
  - [x] 2.8 Wrap all API calls with retry middleware (Story 1.5)

- [x] Task 3: Implement scanner stage (AC: #1)
  - [x] 3.1 Create `scan()` method that queries configured search criteria
  - [x] 3.2 Search by industry keywords: "health food store", "wellness retailer", "organic shop"
  - [x] 3.3 Filter by location: Norway first, then Nordics (SE, DK, FI)
  - [x] 3.4 Apply relevance scoring based on industry match
  - [x] 3.5 Return list of `RawLead` objects
  - [x] 3.6 Log scan statistics: companies found, filtered, duplicates

- [x] Task 4: Implement harvester stage (AC: #2)
  - [x] 4.1 Create `LeadHarvester` class
  - [x] 4.2 Accept `HunterClient` via dependency injection
  - [x] 4.3 Implement `harvest(raw_leads: list[RawLead]) -> list[HarvestedLead]`
  - [x] 4.4 For each lead, gather: company name, domain, location, social profiles
  - [x] 4.5 Extract decision-maker contacts if publicly available
  - [x] 4.6 Handle missing data gracefully (partial leads still valuable)
  - [x] 4.7 Rate limit API calls per Hunter.io guidelines

- [x] Task 5: Implement transformer stage (AC: #2)
  - [x] 5.1 Create `LeadTransformer` class
  - [x] 5.2 Implement `transform(harvested_leads: list[HarvestedLead]) -> list[TransformedLead]`
  - [x] 5.3 Map to Lead model schema:
        - `email`: primary contact email
        - `first_name`, `last_name`: contact name
        - `company`: business name
        - `website_url`: company domain
        - `country`: location
        - `industry`: business category
        - `source`: COLD_RESEARCH
        - `status`: NEW
  - [x] 5.4 Validate required fields present (email, company required)
  - [x] 5.5 Normalize data: trim whitespace, standardize country names

- [x] Task 6: Implement duplicate detection (AC: #2)
  - [x] 6.1 Create `LeadDuplicateChecker` class
  - [x] 6.2 Accept `LeadRepository` via dependency injection
  - [x] 6.3 Implement `check_duplicates(leads: list[TransformedLead]) -> list[TransformedLead]`
  - [x] 6.4 Check by email (exact match)
  - [x] 6.5 Check by company name + country (fuzzy match threshold 90%)
  - [x] 6.6 Return only non-duplicate leads
  - [x] 6.7 Log duplicate statistics

- [x] Task 7: Implement lead repository (AC: #3)
  - [x] 7.1 Create `LeadRepository` class in `teams/dawo/leads/repository.py`
  - [x] 7.2 Accept `AsyncSession` via dependency injection
  - [x] 7.3 Implement `create_lead(lead_data: dict) -> Lead`
  - [x] 7.4 Implement `get_lead_by_email(email: str) -> Optional[Lead]`
  - [x] 7.5 Implement `get_leads_by_company(company: str, country: str) -> Sequence[Lead]`
  - [x] 7.6 Implement `bulk_create_leads(leads: list[dict]) -> tuple[int, list[UUID]]`
  - [x] 7.7 Implement `update_lead_status(lead_id: UUID, status: LeadStatus) -> Lead`

- [x] Task 8: Create orchestrated pipeline (AC: #1, #2, #3)
  - [x] 8.1 Create `B2BLeadPipeline` class
  - [x] 8.2 Accept all stage components via dependency injection
  - [x] 8.3 Implement `execute() -> PipelineResult`
  - [x] 8.4 Chain stages: scan → harvest → transform → dedupe → persist
  - [x] 8.5 Track and return statistics: scanned, harvested, transformed, deduped, created
  - [x] 8.6 Handle partial failures: continue pipeline even if some leads fail

- [x] Task 9: Implement graceful degradation (AC: #3)
  - [x] 9.1 Wrap pipeline execution in try/catch
  - [x] 9.2 On API failure (after retries), mark scan as INCOMPLETE
  - [x] 9.3 Log failure details for debugging
  - [x] 9.4 Queue for next scheduled run (via INCOMPLETE status)
  - [x] 9.5 Ensure existing lead data remains intact
  - [x] 9.6 Notify on scan failure via logging (Discord hook ready)

- [x] Task 10: Register in team_spec.py (AC: #1)
  - [x] 10.1 Add `B2BLeadScanner` as RegisteredAgent with tier="scan"
  - [x] 10.2 Add `LeadHarvester` as RegisteredService
  - [x] 10.3 Add `LeadTransformer` as RegisteredService
  - [x] 10.4 Add `LeadDuplicateChecker` as RegisteredService
  - [x] 10.5 Add `B2BLeadPipeline` as RegisteredService with capability="b2b_lead_research"
  - [x] 10.6 Add `LeadRepository` as RegisteredRepository
  - [x] 10.7 Ensure all components are injectable via Team Builder

- [x] Task 11: Create configuration file (AC: #1)
  - [x] 11.1 Create `config/dawo_lead_scanner.json`
  - [x] 11.2 Define search criteria: industries, keywords, locations
  - [x] 11.3 Define filters: min company size, required fields
  - [x] 11.4 Define schedule: cron expression for weekly Monday 7 AM
  - [x] 11.5 Add Hunter.io API key placeholder (loaded from env vars)

- [x] Task 12: Create comprehensive unit tests
  - [x] 12.1 Test HunterClient API calls (mocked)
  - [x] 12.2 Test scanner filtering logic
  - [x] 12.3 Test harvester data extraction
  - [x] 12.4 Test transformer field mapping
  - [x] 12.5 Test duplicate checker logic
  - [x] 12.6 Test repository CRUD operations (mocked)
  - [x] 12.7 Test pipeline orchestration
  - [x] 12.8 Test graceful degradation on API failure
  - [x] 12.9 Mock Hunter.io API responses for all tests

- [x] Task 13: Create integration tests
  - [x] 13.1 Test full pipeline with mocked Hunter.io API
  - [x] 13.2 Test duplicate detection with existing leads (mocked)
  - [x] 13.3 Test pipeline handles API errors gracefully
  - [x] 13.4 Test statistics tracking through pipeline

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This scanner follows a simplified Harvester Framework pattern adapted for lead discovery:

**Lead Discovery Pipeline:**
```
[Scanner] → [Harvester] → [Transformer] → [DuplicateChecker] → [Repository] → [Lead DB]
     ↑           ↑             ↑                ↑                    ↑
   scan()    harvest()    transform()    check_duplicates()    bulk_create()
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure]

```
teams/dawo/
├── leads/                            # CREATE THIS MODULE
│   ├── __init__.py                   # Export all public types
│   ├── scanner/
│   │   ├── __init__.py               # Scanner exports
│   │   ├── agent.py                  # B2BLeadScanner main class
│   │   ├── tools.py                  # HunterClient, API tools
│   │   ├── config.py                 # LeadScannerConfig
│   │   ├── schemas.py                # RawLead, HarvestedLead, etc.
│   │   ├── harvester.py              # LeadHarvester
│   │   ├── transformer.py            # LeadTransformer
│   │   ├── duplicate_checker.py      # LeadDuplicateChecker
│   │   └── pipeline.py               # B2BLeadPipeline
│   └── repository.py                 # LeadRepository

core/leads/                           # EXISTS from prep
├── __init__.py                       # Model exports
└── models.py                         # Lead, LeadActivity, OutreachEmail

config/
└── dawo_lead_scanner.json            # CREATE: Scanner configuration

tests/teams/dawo/
└── test_leads/
    └── test_scanner/                 # CREATE THIS
        ├── __init__.py
        ├── conftest.py               # Fixtures, mocks
        ├── test_client.py            # HunterClient tests
        ├── test_scanner.py           # Scanner stage tests
        ├── test_harvester.py         # Harvester stage tests
        ├── test_transformer.py       # Transformer stage tests
        ├── test_duplicate_checker.py # Duplicate detection tests
        ├── test_repository.py        # Repository CRUD tests
        ├── test_pipeline.py          # Full pipeline tests
        └── test_integration.py       # Integration with Lead DB
```

### Hunter.io API Integration

**Source:** [docs/research/lead-enrichment-services.md]

**API Details:**
- **Base URL:** `https://api.hunter.io/v2/`
- **Auth:** API key in query params or header
- **Rate Limit:** Based on plan (Starter: 500 requests/month)
- **Recommended Plan:** Starter ($49/mo)

**Key Endpoints:**
```python
# tools.py
class HunterClient:
    """Hunter.io API client for lead discovery.

    Accepts credentials via dependency injection - NEVER loads from file.
    """

    BASE_URL = "https://api.hunter.io/v2/"

    def __init__(self, config: HunterClientConfig):
        """Accept config via injection from Team Builder."""
        self._config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def domain_search(self, domain: str) -> dict:
        """Find all emails associated with a domain.

        Returns:
            {
                "domain": "example.com",
                "company": "Example Inc",
                "emails": [...],
                "organization": "Example Inc",
                "country": "Norway"
            }
        """
        url = f"{self.BASE_URL}domain-search"
        params = {
            "domain": domain,
            "api_key": self._config.api_key
        }
        # ... API call with retry middleware

    async def email_finder(
        self,
        domain: str,
        first_name: str,
        last_name: str
    ) -> dict:
        """Find specific person's email at a domain."""
        url = f"{self.BASE_URL}email-finder"
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": self._config.api_key
        }
        # ... API call
```

### Lead Data Structure

**Source:** [core/leads/models.py], [docs/research/lead-scoring-approach.md]

**Raw Lead (from scan):**
```python
@dataclass
class RawLead:
    """Raw lead data from search results."""
    domain: str
    company_name: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    source_url: Optional[str] = None
    confidence: float = 0.0
```

**Harvested Lead (enriched from Hunter.io):**
```python
@dataclass
class HarvestedLead:
    """Lead with Hunter.io enrichment data."""
    domain: str
    company_name: str
    emails: list[dict]  # [{email, first_name, last_name, position, confidence}]
    organization: Optional[str] = None
    country: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    phone: Optional[str] = None
    headcount: Optional[str] = None  # Employee count
    industry: Optional[str] = None
```

**Transformed Lead (mapped to Lead model):**
```python
@dataclass
class TransformedLead:
    """Lead ready for database insertion."""
    email: str
    first_name: str
    last_name: str
    company: str
    job_title: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    source: str = "cold_research"
    status: str = "new"
    score: float = 0.0  # Initial score, enrichment adds more
```

### Configuration Schema

**Source:** [project-context.md#Configuration-Loading]

```python
# config.py
from dataclasses import dataclass, field

@dataclass
class HunterClientConfig:
    """Hunter.io API credentials - loaded from environment variables."""
    api_key: str

@dataclass
class LeadScannerConfig:
    """Scanner configuration - loaded from config file via injection."""

    # Target industries for B2B retail partners
    industries: list[str] = field(default_factory=lambda: [
        "health food store",
        "wellness retailer",
        "organic shop",
        "specialty grocery",
        "supplement store",
        "natural products retailer"
    ])

    # Location priorities (in order)
    countries: list[str] = field(default_factory=lambda: [
        "Norway",
        "Sweden",
        "Denmark",
        "Finland"
    ])

    # Minimum confidence for lead inclusion
    min_confidence: float = 0.7

    # Maximum leads per scan cycle
    max_leads_per_scan: int = 50

    # Required fields for valid lead
    required_fields: list[str] = field(default_factory=lambda: [
        "email",
        "company"
    ])
```

**config/dawo_lead_scanner.json:**
```json
{
  "industries": [
    "health food store",
    "wellness retailer",
    "organic shop",
    "specialty grocery",
    "supplement store",
    "natural products retailer"
  ],
  "countries": ["Norway", "Sweden", "Denmark", "Finland"],
  "min_confidence": 0.7,
  "max_leads_per_scan": 50,
  "required_fields": ["email", "company"],
  "schedule": {
    "cron": "0 7 * * 1",
    "timezone": "Europe/Oslo"
  }
}
```

### Integration with Existing Components

**Story 1.5 - Retry Middleware:**
```python
from teams.dawo.middleware.retry import (
    RetryMiddleware,
    with_retry,
    RetryConfig
)
```

**Core Lead Models:**
```python
from core.leads import (
    Lead,
    LeadStatus,
    LeadSource,
    LeadActivity,
    ActivityType
)
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

The B2B Lead Scanner uses `tier="scan"` (maps to Haiku at runtime).

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="b2b_lead_scanner",
    agent_class=B2BLeadScanner,
    capabilities=["b2b_lead_research", "lead_discovery"],
    tier="scan"  # Maps to Haiku at runtime - NEVER use model names
)
```

### Duplicate Detection Strategy

**Source:** [docs/research/crm-integration-patterns.md]

**Email Match (Exact):**
```python
async def _check_email_duplicate(self, email: str) -> bool:
    """Check if email already exists in database."""
    existing = await self._repository.get_lead_by_email(email)
    return existing is not None
```

**Company Match (Fuzzy):**
```python
async def _check_company_duplicate(
    self,
    company: str,
    country: str
) -> bool:
    """Check if company already exists using fuzzy matching."""
    # Normalize company name
    normalized = self._normalize_company(company)
    existing = await self._repository.get_leads_by_company_fuzzy(
        normalized,
        country,
        threshold=0.9
    )
    return len(existing) > 0

def _normalize_company(self, name: str) -> str:
    """Normalize company name for matching."""
    # Remove common suffixes: AS, AB, ApS, Oy, Ltd, etc.
    # Lowercase, strip whitespace
    suffixes = ["as", "ab", "aps", "oy", "ltd", "inc", "gmbh"]
    lower = name.lower().strip()
    for suffix in suffixes:
        if lower.endswith(f" {suffix}"):
            lower = lower[:-len(suffix)-1]
    return lower
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** Epic 2-4 retrospectives

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="scan"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| SQLAlchemy reserved word fix | Use `source_metadata` not `metadata` |
| Add logging to exception handlers | All exceptions logged before re-raising |
| Extract magic numbers to constants | `MIN_CONFIDENCE = 0.7`, `MAX_LEADS = 50`, etc. |
| TDD approach | Write tests first for each task |
| Unit tests with mocking | Mock Hunter.io API for all tests |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER load config directly** - Accept via injection
2. **NEVER make direct API calls without retry wrapper**
3. **NEVER use LLM model names**
4. **NEVER swallow exceptions without logging**
5. **NEVER store API keys in code** - Use environment variables

### Graceful Degradation Pattern

**Source:** [prd.md#Technical-Constraints]

```python
# pipeline.py
class B2BLeadPipeline:
    async def execute(self) -> PipelineResult:
        """Execute full pipeline with graceful degradation."""
        try:
            raw_leads = await self._scanner.scan()
            harvested = await self._harvester.harvest(raw_leads)
            transformed = await self._transformer.transform(harvested)
            deduped = await self._duplicate_checker.check_duplicates(transformed)
            created = await self._repository.bulk_create_leads(deduped)

            return PipelineResult(
                status=PipelineStatus.COMPLETE,
                stats=self._calculate_stats(raw_leads, harvested, transformed, deduped, created)
            )

        except HunterAPIError as e:
            logger.error(f"Hunter.io API failure: {e}")
            return PipelineResult(
                status=PipelineStatus.INCOMPLETE,
                error=str(e),
                retry_scheduled=True
            )

        except Exception as e:
            logger.error(f"Unexpected pipeline error: {e}")
            await self._notify_failure(e)
            raise PipelineError(f"Pipeline failed: {e}") from e
```

### GDPR Compliance (CRITICAL)

**Source:** [docs/research/gdpr-b2b-outreach.md]

All lead data processing must comply with GDPR:

1. **Legitimate Interest Basis**: B2B cold research is permitted under legitimate interest
2. **Business Emails Only**: Only collect work email addresses, never personal
3. **Data Minimization**: Only collect necessary fields
4. **Record Source**: Always record where lead data came from
5. **Suppression List Ready**: Design supports future unsubscribe tracking

```python
# In Lead creation
lead = Lead(
    email=transformed.email,
    source=LeadSource.COLD_RESEARCH,
    # ... other fields
)
# Record in activity log
activity = LeadActivity(
    lead_id=lead.id,
    activity_type=ActivityType.CREATED,
    description="Lead discovered via B2B research scanner",
    metadata={"discovery_source": "hunter.io", "scan_id": scan_id}
)
```

### References

- [Source: epics.md#Story-5.1] - Original story requirements
- [Source: architecture.md#DAWO-Team-Structure] - Package structure
- [Source: docs/research/lead-enrichment-services.md] - Hunter.io recommendation
- [Source: docs/research/lead-scoring-approach.md] - Scoring model
- [Source: docs/research/gdpr-b2b-outreach.md] - GDPR compliance
- [Source: core/leads/models.py] - Lead data models
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology

---

## Dev Agent Record

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

1. **Harvester Framework Pattern**: Successfully followed the established Harvester Framework pattern from Epic 2 scanners (Scanner → Harvester → Transformer → DuplicateChecker → Repository).

2. **Hunter.io API Client**: Implemented full async HTTP client with rate limiting, retry middleware support, and proper error handling (HunterAPIError, HunterRateLimitError).

3. **Dependency Injection**: All components accept dependencies via constructor injection - no direct config loading.

4. **SQLAlchemy Reserved Word Fix**: Applied learning from previous stories - LeadActivity model uses `activity_metadata` field name with explicit column mapping to avoid SQLAlchemy's reserved `metadata` keyword.

5. **Fuzzy Duplicate Detection**: Used `difflib.SequenceMatcher` for 90% similarity threshold on company name matching, with normalization removing legal suffixes (AS, AB, Ltd, etc.).

6. **Graceful Degradation**: Pipeline returns INCOMPLETE status on API errors, PARTIAL on some stage failures, allowing retry scheduling.

7. **Test Coverage**: 112 tests covering all pipeline stages with comprehensive mocking of Hunter.io API responses (including repository and integration tests).

8. **GDPR Compliance**: Source tracking via LeadSource.COLD_RESEARCH and activity logging for audit trail.

### File List

**New Files Created:**

- `teams/dawo/leads/__init__.py` - Module exports for B2B Leads package
- `teams/dawo/leads/repository.py` - LeadRepository with async SQLAlchemy operations
- `teams/dawo/leads/scanner/__init__.py` - Scanner module exports
- `teams/dawo/leads/scanner/schemas.py` - Data schemas (RawLead, HarvestedContact, HarvestedLead, TransformedLead, ScanResult, PipelineResult, PipelineStatus, ScanStatistics)
- `teams/dawo/leads/scanner/config.py` - HunterClientConfig and LeadScannerConfig dataclasses
- `teams/dawo/leads/scanner/tools.py` - HunterClient with async HTTP and rate limiting
- `teams/dawo/leads/scanner/agent.py` - B2BLeadScanner agent class
- `teams/dawo/leads/scanner/harvester.py` - LeadHarvester for Hunter.io enrichment
- `teams/dawo/leads/scanner/transformer.py` - LeadTransformer for data normalization
- `teams/dawo/leads/scanner/duplicate_checker.py` - LeadDuplicateChecker with fuzzy matching
- `teams/dawo/leads/scanner/pipeline.py` - B2BLeadPipeline orchestrator
- `config/dawo_lead_scanner.json` - Scanner configuration with seed domains
- `core/leads/__init__.py` - Lead model exports
- `core/leads/models.py` - Lead, LeadActivity, OutreachEmail SQLAlchemy models
- `migrations/versions/2026_02_09_001_create_leads_tables.py` - Alembic migration for leads tables

**Test Files Created:**

- `tests/teams/dawo/test_leads/__init__.py`
- `tests/teams/dawo/test_leads/test_scanner/__init__.py`
- `tests/teams/dawo/test_leads/test_scanner/conftest.py` - Fixtures and mocks
- `tests/teams/dawo/test_leads/test_scanner/test_schemas.py` - Schema tests
- `tests/teams/dawo/test_leads/test_scanner/test_client.py` - HunterClient tests
- `tests/teams/dawo/test_leads/test_scanner/test_scanner.py` - Scanner stage tests
- `tests/teams/dawo/test_leads/test_scanner/test_harvester.py` - Harvester tests
- `tests/teams/dawo/test_leads/test_scanner/test_transformer.py` - Transformer tests
- `tests/teams/dawo/test_leads/test_scanner/test_duplicate_checker.py` - Duplicate checker tests
- `tests/teams/dawo/test_leads/test_scanner/test_repository.py` - Repository CRUD tests (mocked)
- `tests/teams/dawo/test_leads/test_scanner/test_pipeline.py` - Pipeline orchestration tests
- `tests/teams/dawo/test_leads/test_scanner/test_integration.py` - Full pipeline integration tests

**Modified Files:**

- `teams/dawo/team_spec.py` - Registered B2BLeadScanner agent and 6 services

**Code Review Fixes Applied:**

- Fixed `activity_metadata` field naming in repository.py (was incorrectly using `metadata`)
- Updated model header to correctly attribute Story 5-1
- Deleted spurious `nul` file artifact
