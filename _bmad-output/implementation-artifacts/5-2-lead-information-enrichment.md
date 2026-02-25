# Story 5.2: Lead Information Enrichment

Status: done

---

## Story

As an **operator**,
I want discovered leads enriched with detailed business information,
So that outreach can be personalized and relevant.

---

## Acceptance Criteria

1. **Given** a lead has status `NEW` (discovered via scanner)
   **When** the enrichment agent processes it
   **Then** it gathers from public sources:
   - Business description and focus areas
   - Product categories carried
   - Social media presence and activity
   - Any existing mushroom/supplement offerings
   - Decision maker names if publicly available

2. **Given** enrichment completes successfully
   **When** data is saved
   **Then** lead status changes to `QUALIFIED`
   **And** enrichment confidence score is assigned (1-10)
   **And** personalization hooks are identified (e.g., "carries competitor X", "focus on organic")

3. **Given** enrichment finds insufficient data
   **When** confidence score < 5
   **Then** lead is flagged for manual research
   **And** status changes to `RESEARCHING` (needs review)
   **And** operator sees what data is missing

4. **Given** lead is a competitor retailer
   **When** they already carry DAWO products
   **Then** lead is marked `CONVERTED` (existing customer) and excluded from outreach

---

## Tasks / Subtasks

- [x] Task 1: Create Lead Enrichment module structure (AC: #1)
  - [x] 1.1 Create `teams/dawo/leads/enrichment/` directory
  - [x] 1.2 Create `__init__.py` with complete `__all__` exports
  - [x] 1.3 Create `schemas.py` with `EnrichmentResult`, `PersonalizationHook`, `WebsiteAnalysis` dataclasses
  - [x] 1.4 Create `config.py` with `EnrichmentConfig` dataclass

- [x] Task 2: Implement Website Analyzer (AC: #1)
  - [x] 2.1 Create `website_analyzer.py` with `WebsiteAnalyzer` class
  - [x] 2.2 Accept `httpx.AsyncClient` via dependency injection
  - [x] 2.3 Implement `fetch_page(url: str) -> Optional[str]` - Get HTML content
  - [x] 2.4 Implement `extract_text(html: str) -> str` - Strip HTML, extract text
  - [x] 2.5 Implement `analyze(domain: str) -> WebsiteAnalysis`:
        - Fetch homepage and about page
        - Extract business description
        - Identify product categories
        - Detect mushroom/supplement keywords
  - [x] 2.6 Respect robots.txt (use `robotexclusionrulesparser`)
  - [x] 2.7 Set 5-second timeout, handle failures gracefully
  - [x] 2.8 Rate limit: max 1 request per second per domain

- [x] Task 3: Implement LLM-based Business Analyzer (AC: #1, #2)
  - [x] 3.1 Create `business_analyzer.py` with `BusinessAnalyzer` class
  - [x] 3.2 Accept `LLMClient` via dependency injection (tier="generate")
  - [x] 3.3 Implement `analyze_business(content: str, company: str) -> BusinessInsights`:
        - Business focus areas
        - Target customer demographics
        - Product specializations
        - Wellness/health positioning
  - [x] 3.4 Implement `identify_hooks(insights: BusinessInsights, lead: Lead) -> list[PersonalizationHook]`:
        - "Focuses on organic products"
        - "Carries competitor brands"
        - "Strong wellness positioning"
        - "Nordic/Scandinavian focus"
  - [x] 3.5 Implement `detect_existing_customer(content: str) -> bool`:
        - Check for DAWO mentions
        - Check for DAWO product names
  - [x] 3.6 Return structured insights with confidence scores

- [x] Task 4: Implement Hunter.io Extended Enrichment (AC: #1)
  - [x] 4.1 Create `hunter_enricher.py` with `HunterEnricher` class
  - [x] 4.2 Reuse `HunterClient` from Story 5-1 via dependency injection
  - [x] 4.3 Implement `enrich_company(domain: str) -> CompanyEnrichment`:
        - Call domain_search for company details
        - Get organization, headcount, industry
        - Collect all email patterns
  - [x] 4.4 Implement `find_decision_makers(domain: str) -> list[HarvestedContact]`:
        - Filter for owner, CEO, buyer, purchasing roles
        - Prioritize verified emails
  - [x] 4.5 Implement `verify_contacts(contacts: list[HarvestedContact]) -> list[HarvestedContact]`:
        - Call email_verifier for each contact
        - Filter to only deliverable emails
  - [x] 4.6 Track API usage for budget monitoring

- [x] Task 5: Implement Social Media Analyzer (AC: #1)
  - [x] 5.1 Create `social_analyzer.py` with `SocialAnalyzer` class
  - [x] 5.2 Implement `analyze_instagram(handle: str) -> Optional[SocialProfile]`:
        - Get bio, follower count (public data only)
        - Detect wellness/health themes
        - Note: No scraping, use public profile info
  - [x] 5.3 Implement `analyze_linkedin(url: str) -> Optional[SocialProfile]`:
        - Extract company description (from Hunter.io data)
        - Employee count indicators
  - [x] 5.4 Implement `analyze_facebook(url: str) -> Optional[SocialProfile]`:
        - Business page info if public
  - [x] 5.5 Return presence score (0-10) based on activity level

- [x] Task 6: Implement Enrichment Scoring (AC: #2, #3)
  - [x] 6.1 Create `scorer.py` with `EnrichmentScorer` class
  - [x] 6.2 Implement `calculate_confidence(result: EnrichmentResult) -> float`:
        - +2 for verified email
        - +2 for business description
        - +1 for social media presence
        - +1 for decision maker contact
        - +1 for industry match
        - +1 for product categories
        - +1 for personalization hooks
        - +1 for website accessible
  - [x] 6.3 Implement `calculate_lead_score(result: EnrichmentResult) -> float`:
        - Industry relevance (0-30)
        - Company size fit (0-20)
        - Geographic fit (0-20)
        - Engagement potential (0-15)
        - Data completeness (0-15)
  - [x] 6.4 Return score breakdown for transparency
  - [x] 6.5 Define constants: `MIN_CONFIDENCE_THRESHOLD = 5`

- [x] Task 7: Implement Lead Enrichment Service (AC: #1, #2, #3, #4)
  - [x] 7.1 Create `service.py` with `LeadEnrichmentService` class
  - [x] 7.2 Accept all analyzers via dependency injection
  - [x] 7.3 Implement `enrich_lead(lead: Lead) -> EnrichmentResult`:
        - Orchestrate all analyzers
        - Aggregate results
        - Calculate scores
  - [x] 7.4 Implement `determine_status(result: EnrichmentResult) -> LeadStatus`:
        - Confidence >= 5 → QUALIFIED
        - Confidence < 5 → RESEARCHING
        - Is existing customer → CONVERTED
  - [x] 7.5 Implement `format_enrichment_data(result: EnrichmentResult) -> dict`:
        - Structure for Lead.enrichment_data JSONB field
  - [x] 7.6 Implement `get_missing_fields(result: EnrichmentResult) -> list[str]`:
        - For RESEARCHING status, show what's missing

- [x] Task 8: Implement Enrichment Pipeline (AC: #1, #2, #3)
  - [x] 8.1 Create `pipeline.py` with `EnrichmentPipeline` class
  - [x] 8.2 Accept `LeadRepository` and `LeadEnrichmentService` via injection
  - [x] 8.3 Implement `execute(batch_size: int = 10) -> PipelineResult`:
        - Query leads with status=NEW, ordered by created_at
        - Process in batches
        - Update each lead after enrichment
        - Track statistics
  - [x] 8.4 Implement `enrich_single(lead_id: UUID) -> EnrichmentResult`:
        - For manual enrichment trigger
  - [x] 8.5 Handle graceful degradation:
        - Continue on individual lead failure
        - Mark pipeline INCOMPLETE on critical errors
  - [x] 8.6 Add activity log entry for each enriched lead

- [x] Task 9: Create Enrichment Agent (AC: #1)
  - [x] 9.1 Create `agent.py` with `LeadEnrichmentAgent` class
  - [x] 9.2 Inherit from BaseAgent pattern
  - [x] 9.3 Implement `run() -> AgentResult`:
        - Execute enrichment pipeline
        - Report statistics
  - [x] 9.4 Add scheduling support (daily 8 AM, after scanner completes)
  - [x] 9.5 Use tier="generate" for LLM analysis operations

- [x] Task 10: Update LeadRepository (AC: #2, #3, #4)
  - [x] 10.1 Add `get_leads_for_enrichment(limit: int) -> Sequence[Lead]`:
        - Query status=NEW, ordered by created_at ASC
  - [x] 10.2 Add `update_enrichment(lead_id: UUID, enrichment_data: dict, status: LeadStatus, score: float, enriched_at: datetime) -> Lead`
  - [x] 10.3 Add `mark_existing_customer(lead_id: UUID) -> Lead`:
        - Set status=CONVERTED, add tag "existing_customer"
  - [x] 10.4 Add `get_enrichment_stats() -> dict`:
        - Count by status: NEW, RESEARCHING, QUALIFIED, CONVERTED

- [x] Task 11: Register in team_spec.py (AC: #1)
  - [x] 11.1 Add `LeadEnrichmentAgent` as RegisteredAgent with tier="generate"
  - [x] 11.2 Add `LeadEnrichmentService` as RegisteredService
  - [x] 11.3 Add `WebsiteAnalyzer` as RegisteredService
  - [x] 11.4 Add `BusinessAnalyzer` as RegisteredService
  - [x] 11.5 Add `HunterEnricher` as RegisteredService
  - [x] 11.6 Add `SocialAnalyzer` as RegisteredService
  - [x] 11.7 Add `EnrichmentScorer` as RegisteredService
  - [x] 11.8 Add `EnrichmentPipeline` as RegisteredService with capability="lead_enrichment"

- [x] Task 12: Create comprehensive unit tests
  - [x] 12.1 Test WebsiteAnalyzer with mocked HTTP responses
  - [x] 12.2 Test BusinessAnalyzer with mocked LLM responses
  - [x] 12.3 Test HunterEnricher with mocked Hunter.io API
  - [x] 12.4 Test SocialAnalyzer with mocked data
  - [x] 12.5 Test EnrichmentScorer calculations
  - [x] 12.6 Test LeadEnrichmentService orchestration
  - [x] 12.7 Test EnrichmentPipeline batch processing
  - [x] 12.8 Test status determination logic (QUALIFIED/RESEARCHING/CONVERTED)
  - [x] 12.9 Test graceful degradation on failures

- [x] Task 13: Create integration tests
  - [x] 13.1 Test full enrichment pipeline with mocked external services
  - [x] 13.2 Test lead status transitions
  - [x] 13.3 Test enrichment_data JSONB storage
  - [x] 13.4 Test activity logging for enriched leads
  - [x] 13.5 Test existing customer detection

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This story extends the B2B Lead Pipeline from Story 5-1. The enrichment module follows the same patterns.

**Enrichment Pipeline:**
```
[NEW Leads] → [Hunter Enricher] → [Website Analyzer] → [Business Analyzer (LLM)]
                     ↓                    ↓                      ↓
              [Social Analyzer] → [Enrichment Scorer] → [Repository Update]
                                          ↓
                              [QUALIFIED or RESEARCHING]
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure]

```
teams/dawo/leads/
├── __init__.py                    # Add enrichment exports
├── repository.py                  # EXTEND with enrichment methods
├── scanner/                       # FROM Story 5-1 (unchanged)
│   └── ...
└── enrichment/                    # CREATE THIS MODULE
    ├── __init__.py                # Export all public types
    ├── schemas.py                 # EnrichmentResult, PersonalizationHook, etc.
    ├── config.py                  # EnrichmentConfig
    ├── website_analyzer.py        # WebsiteAnalyzer
    ├── business_analyzer.py       # BusinessAnalyzer (LLM-based)
    ├── hunter_enricher.py         # HunterEnricher
    ├── social_analyzer.py         # SocialAnalyzer
    ├── scorer.py                  # EnrichmentScorer
    ├── service.py                 # LeadEnrichmentService
    ├── pipeline.py                # EnrichmentPipeline
    └── agent.py                   # LeadEnrichmentAgent

tests/teams/dawo/test_leads/
└── test_enrichment/               # CREATE THIS
    ├── __init__.py
    ├── conftest.py                # Fixtures, mocks
    ├── test_website_analyzer.py
    ├── test_business_analyzer.py
    ├── test_hunter_enricher.py
    ├── test_social_analyzer.py
    ├── test_scorer.py
    ├── test_service.py
    ├── test_pipeline.py
    └── test_integration.py
```

### Status Mapping

**Source:** [core/leads/models.py]

| Epic Term | LeadStatus Enum | Description |
|-----------|-----------------|-------------|
| DISCOVERED | `NEW` | Just created by scanner |
| ENRICHED | `QUALIFIED` | Enrichment complete, ready for outreach |
| NEEDS_REVIEW | `RESEARCHING` | Insufficient data, needs manual work |
| EXISTING_CUSTOMER | `CONVERTED` | Already carries DAWO products |

### Enrichment Data Schema

**Source:** [core/leads/models.py#enrichment_data]

Store enrichment results in the JSONB field:
```python
enrichment_data = {
    "enriched_at": "2026-02-09T10:00:00Z",
    "confidence_score": 7.5,
    "score_breakdown": {
        "verified_email": 2,
        "business_description": 2,
        "social_presence": 1,
        "decision_maker": 1,
        "industry_match": 1,
        "personalization_hooks": 0.5,
    },
    "business_insights": {
        "focus_areas": ["organic products", "health foods", "local producers"],
        "target_demographics": "health-conscious consumers, 25-55",
        "product_categories": ["supplements", "organic groceries", "wellness"],
        "wellness_positioning": "strong",
    },
    "personalization_hooks": [
        {"type": "competitor", "detail": "Carries HealthWorks mushroom products"},
        {"type": "focus", "detail": "Strong organic and local producer focus"},
        {"type": "audience", "detail": "Nordic wellness community"},
    ],
    "social_presence": {
        "instagram": {"handle": "@example_store", "followers": 2500, "active": true},
        "linkedin": {"url": "linkedin.com/company/example", "employees": "11-50"},
        "facebook": null,
    },
    "website_analysis": {
        "accessible": true,
        "description": "Premium health food store in Oslo...",
        "mushroom_keywords_found": ["lion's mane", "functional mushrooms"],
        "supplement_section": true,
    },
    "missing_fields": [],  # Only populated if status=RESEARCHING
}
```

### Personalization Hook Types

**Source:** PRD FR18, FR19

```python
class PersonalizationHookType(str, Enum):
    """Types of personalization hooks for outreach."""

    COMPETITOR = "competitor"      # Carries competitor products
    FOCUS = "focus"               # Business focus alignment
    AUDIENCE = "audience"         # Target audience match
    LOCATION = "location"         # Geographic relevance
    PRODUCT = "product"           # Product category fit
    VALUES = "values"             # Shared values (organic, sustainable)
    GROWTH = "growth"             # Expansion/growth indicators
```

### LLM Analysis Prompts

**Source:** Brand Voice, tier="generate"

```python
# business_analyzer.py
BUSINESS_ANALYSIS_PROMPT = """
Analyze this business website content to extract key insights for B2B outreach.

Company: {company_name}
Content:
{website_content}

Extract:
1. Business focus areas (what they specialize in)
2. Target customer demographics
3. Product categories they carry
4. Wellness/health positioning strength (weak/moderate/strong)
5. Any mushroom, adaptogen, or supplement offerings mentioned

Return as structured JSON.
"""

PERSONALIZATION_PROMPT = """
Given these business insights, identify personalization hooks for a DAWO mushroom supplement outreach.

Insights:
{insights}

Lead data:
{lead_data}

Identify 2-4 personalization hooks that would make outreach relevant.
Each hook should be specific and actionable.

Return as JSON list with type and detail fields.
"""
```

### Integration with Story 5-1 Components

**Source:** [5-1-b2b-lead-research-scanner.md#File-List]

Reuse these components from Story 5-1:
```python
# Import from scanner module
from teams.dawo.leads.scanner.tools import HunterClient
from teams.dawo.leads.scanner.config import HunterClientConfig
from teams.dawo.leads.scanner.schemas import HarvestedContact

# Import from leads module
from teams.dawo.leads.repository import LeadRepository
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

The Lead Enrichment Agent uses `tier="generate"` (maps to Sonnet at runtime) for business analysis.

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="lead_enrichment_agent",
    agent_class=LeadEnrichmentAgent,
    capabilities=["lead_enrichment", "business_analysis"],
    tier="generate"  # Maps to Sonnet at runtime - NEVER use model names
)
```

### Graceful Degradation Pattern

**Source:** [project-context.md#External-API-Calls]

```python
# service.py
class LeadEnrichmentService:
    async def enrich_lead(self, lead: Lead) -> EnrichmentResult:
        """Enrich a single lead with all available data."""
        result = EnrichmentResult(lead_id=lead.id)

        # Hunter.io enrichment
        try:
            company_data = await self._hunter.enrich_company(lead.website_url)
            result.company_enrichment = company_data
        except HunterAPIError as e:
            logger.warning(f"Hunter.io enrichment failed for {lead.id}: {e}")
            result.errors.append(f"Hunter.io: {e}")

        # Website analysis (continue even if Hunter failed)
        try:
            website_data = await self._website_analyzer.analyze(lead.website_url)
            result.website_analysis = website_data
        except WebsiteAnalysisError as e:
            logger.warning(f"Website analysis failed for {lead.id}: {e}")
            result.errors.append(f"Website: {e}")

        # LLM business analysis (requires website content)
        if result.website_analysis and result.website_analysis.content:
            try:
                insights = await self._business_analyzer.analyze_business(
                    result.website_analysis.content,
                    lead.company
                )
                result.business_insights = insights
            except LLMError as e:
                logger.warning(f"LLM analysis failed for {lead.id}: {e}")
                result.errors.append(f"LLM: {e}")

        # Calculate scores based on what we got
        result.confidence_score = self._scorer.calculate_confidence(result)
        result.lead_score = self._scorer.calculate_lead_score(result)

        return result
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [5-1-b2b-lead-research-scanner.md#Completion-Notes]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="generate"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(UTC)` not `datetime.utcnow()` |
| `activity_metadata` field naming | Use this field name for LeadActivity |
| Add logging to exception handlers | All exceptions logged before continuing |
| Fuzzy matching for company names | Reuse from duplicate_checker for existing customer detection |
| TDD approach | Write tests first for each task |

### DAWO Product Detection

**Source:** Brand assets, [config/dawo_brand_profile.json]

Detect existing customers by checking for DAWO products:
```python
DAWO_PRODUCT_KEYWORDS = [
    "dawo",
    "dawo mushrooms",
    "dawo.eco",
    "lion's mane dawo",
    "chaga dawo",
    "reishi dawo",
    "cordyceps dawo",
]

def detect_existing_customer(content: str) -> bool:
    """Check if business already carries DAWO products."""
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in DAWO_PRODUCT_KEYWORDS)
```

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER load config directly** - Accept via injection
2. **NEVER make direct HTTP calls without timeout** - Always set 5-30s timeout
3. **NEVER use LLM model names** - Use tier system
4. **NEVER swallow exceptions without logging**
5. **NEVER scrape websites aggressively** - Respect robots.txt, rate limit

### Rate Limiting Strategy

**Source:** [docs/research/lead-enrichment-services.md]

| Service | Rate Limit | Strategy |
|---------|------------|----------|
| Hunter.io | 10 req/s (Starter) | Use existing rate limiter from 5-1 |
| Website scraping | 1 req/s per domain | asyncio.Semaphore + delay |
| LLM calls | No hard limit | Batch to minimize calls |

### References

- [Source: epics.md#Story-5.2] - Original story requirements
- [Source: 5-1-b2b-lead-research-scanner.md] - Scanner implementation patterns
- [Source: docs/research/lead-enrichment-services.md] - Hunter.io recommendation
- [Source: core/leads/models.py] - Lead model with enrichment_data field
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

1. All enrichment components use dependency injection pattern consistent with Story 5-1
2. LLM tier terminology strictly followed: `tier="generate"` (never model names)
3. Used `datetime.now(UTC)` instead of deprecated `datetime.utcnow()`
4. Used `activity_metadata` field name for LeadActivity
5. Graceful degradation pattern applied - pipeline continues on individual analyzer failures
6. 133 tests total: 123 unit tests + 10 integration tests
7. Registered 1 agent and 7 services in team_spec.py (21 agents, 49 services total)
8. LeadRepository extended with enrichment methods (get_leads_for_enrichment, update_enrichment, mark_existing_customer, get_enrichment_stats)

### File List

**Enrichment Module:**
- teams/dawo/leads/enrichment/__init__.py - Module exports
- teams/dawo/leads/enrichment/schemas.py - Data schemas (EnrichmentResult, WebsiteAnalysis, etc.)
- teams/dawo/leads/enrichment/config.py - EnrichmentConfig, scoring weights
- teams/dawo/leads/enrichment/website_analyzer.py - WebsiteAnalyzer class
- teams/dawo/leads/enrichment/business_analyzer.py - BusinessAnalyzer class (LLM-based)
- teams/dawo/leads/enrichment/hunter_enricher.py - HunterEnricher class
- teams/dawo/leads/enrichment/social_analyzer.py - SocialAnalyzer class
- teams/dawo/leads/enrichment/scorer.py - EnrichmentScorer class
- teams/dawo/leads/enrichment/service.py - LeadEnrichmentService class
- teams/dawo/leads/enrichment/pipeline.py - EnrichmentPipeline, PipelineResult, PipelineStatus
- teams/dawo/leads/enrichment/agent.py - LeadEnrichmentAgent, AgentResult

**Updated Files:**
- teams/dawo/leads/repository.py - Added enrichment methods
- teams/dawo/team_spec.py - Registered agent and services

**Test Files:**
- tests/teams/dawo/test_leads/test_enrichment/__init__.py
- tests/teams/dawo/test_leads/test_enrichment/conftest.py
- tests/teams/dawo/test_leads/test_enrichment/test_schemas.py
- tests/teams/dawo/test_leads/test_enrichment/test_config.py
- tests/teams/dawo/test_leads/test_enrichment/test_website_analyzer.py
- tests/teams/dawo/test_leads/test_enrichment/test_business_analyzer.py
- tests/teams/dawo/test_leads/test_enrichment/test_hunter_enricher.py
- tests/teams/dawo/test_leads/test_enrichment/test_social_analyzer.py
- tests/teams/dawo/test_leads/test_enrichment/test_scorer.py
- tests/teams/dawo/test_leads/test_enrichment/test_service.py
- tests/teams/dawo/test_leads/test_enrichment/test_pipeline.py
- tests/teams/dawo/test_leads/test_enrichment/test_agent.py
- tests/teams/dawo/test_leads/test_enrichment/test_integration.py

