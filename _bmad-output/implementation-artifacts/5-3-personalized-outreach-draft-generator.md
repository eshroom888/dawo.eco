# Story 5.3: Personalized Outreach Draft Generator

Status: done

---

## Story

As an **operator**,
I want personalized outreach emails drafted using lead insights,
So that B2B contacts feel tailored, not mass-mailed.

---

## Acceptance Criteria

1. **Given** a lead has status `QUALIFIED` with confidence >= 6
   **When** the outreach generator runs
   **Then** it creates a personalized email draft including:
   - Reference to their business focus (from enrichment)
   - Relevant DAWO products for their customer base
   - Specific value proposition based on their market
   - Clear CTA (meeting request, sample offer, catalog)

2. **Given** the draft is generated
   **When** it's evaluated
   **Then** it passes Brand Voice Validator (warm, professional, Norwegian)
   **And** it avoids generic sales language
   **And** it includes personalization tokens that were filled
   **And** draft length is 150-250 words

3. **Given** a draft is ready
   **When** it enters approval queue
   **Then** it shows: lead summary, personalization used, suggested send time
   **And** operator can edit before approving
   **And** status changes to `OUTREACH_PENDING`

4. **Given** multiple outreach templates exist
   **When** generator selects one
   **Then** it chooses based on lead type (health store vs. gym vs. online retailer)
   **And** template selection is logged for performance tracking

---

## Tasks / Subtasks

- [x] Task 1: Create Outreach Generator module structure (AC: #1)
  - [x] 1.1 Create `teams/dawo/leads/outreach/` directory
  - [x] 1.2 Create `__init__.py` with complete `__all__` exports
  - [x] 1.3 Create `schemas.py` with `OutreachDraft`, `OutreachTemplate`, `TemplateSelection`, `GenerationResult` dataclasses
  - [x] 1.4 Create `config.py` with `OutreachConfig`, `TemplateConfig` dataclasses

- [x] Task 2: Create Outreach Templates (AC: #4)
  - [x] 2.1 Create `templates.py` with `OutreachTemplateRegistry` class
  - [x] 2.2 Define template type enum: `HEALTH_STORE`, `GYM_FITNESS`, `ONLINE_RETAILER`, `WELLNESS_CENTER`, `SPECIALTY_GROCER`
  - [x] 2.3 Create base template structure with placeholders: `{{company_name}}`, `{{personalization_hook}}`, `{{product_recommendation}}`, `{{cta}}`
  - [x] 2.4 Implement `get_template(lead_type: LeadType) -> OutreachTemplate`
  - [x] 2.5 Implement `log_template_selection(template_id: str, lead_id: UUID)` for performance tracking
  - [x] 2.6 All templates in Norwegian with warm, professional tone

- [x] Task 3: Implement Lead Type Classifier (AC: #4)
  - [x] 3.1 Create `classifier.py` with `LeadTypeClassifier` class
  - [x] 3.2 Accept `LLMClient` via dependency injection (tier="generate")
  - [x] 3.3 Implement `classify(lead: Lead) -> LeadType`:
        - Use enrichment_data business_insights
        - Analyze product categories
        - Determine best template match
  - [x] 3.4 Implement confidence-based fallback to generic template
  - [x] 3.5 Cache classification results on lead record

- [x] Task 4: Implement Personalization Engine (AC: #1, #2)
  - [x] 4.1 Create `personalization.py` with `PersonalizationEngine` class
  - [x] 4.2 Implement `extract_hooks(lead: Lead) -> list[str]`:
        - Extract from lead.enrichment_data.personalization_hooks
        - Format as natural language references
  - [x] 4.3 Implement `select_products(lead: Lead) -> list[str]`:
        - Match DAWO products to lead's customer base
        - Use business_insights.product_categories
        - Prioritize complementary products
  - [x] 4.4 Implement `generate_value_prop(lead: Lead) -> str`:
        - Create specific value proposition for their market
        - Reference their focus areas
  - [x] 4.5 Implement `select_cta(lead_type: LeadType) -> str`:
        - Meeting request for large retailers
        - Sample offer for health stores
        - Catalog request for online retailers

- [x] Task 5: Implement Draft Generator (AC: #1, #2)
  - [x] 5.1 Create `generator.py` with `OutreachDraftGenerator` class
  - [x] 5.2 Accept `LLMClient`, `PersonalizationEngine`, `OutreachTemplateRegistry` via injection
  - [x] 5.3 Implement `generate(lead: Lead, template: OutreachTemplate) -> OutreachDraft`:
        - Fill template placeholders with personalization
        - Use LLM to polish and expand (tier="generate")
        - Ensure Norwegian language output
  - [x] 5.4 Implement `validate_length(draft: str) -> bool`:
        - Enforce 150-250 word limit
        - Truncate or expand as needed
  - [x] 5.5 Implement `count_personalization_tokens(draft: str) -> int`:
        - Track how many personalization elements were used
        - Minimum 2 required for "personalized" status

- [x] Task 6: Implement Brand Voice Validation (AC: #2)
  - [x] 6.1 Create `validator.py` with `OutreachValidator` class
  - [x] 6.2 Accept `BrandVoiceValidator` from shared validators via injection
  - [x] 6.3 Implement `validate(draft: OutreachDraft) -> ValidationResult`:
        - Call Brand Voice Validator
        - Check for generic sales language patterns
        - Verify Norwegian language
  - [x] 6.4 Define FORBIDDEN_PATTERNS list:
        - Generic openers ("Vi er et selskap som...")
        - Pushy sales language ("Kjop na!", "Tilbud!")
        - Mass-mail indicators ("Til hvem det matte gjelde")
  - [x] 6.5 Implement `suggest_improvements(result: ValidationResult) -> list[str]`

- [x] Task 7: Implement Outreach Service (AC: #1, #2, #3, #4)
  - [x] 7.1 Create `service.py` with `OutreachService` class
  - [x] 7.2 Accept all components via dependency injection
  - [x] 7.3 Implement `generate_outreach(lead: Lead) -> GenerationResult`:
        - Classify lead type
        - Select appropriate template
        - Generate personalized draft
        - Validate against brand voice
        - Return complete result
  - [x] 7.4 Implement `prepare_for_approval(draft: OutreachDraft, lead: Lead) -> ApprovalItem`:
        - Create approval queue item
        - Include lead summary
        - Include personalization used
        - Calculate suggested send time
  - [x] 7.5 Implement `update_lead_status(lead_id: UUID)`:
        - Set status to OUTREACH_PENDING
        - Store draft in outreach_data JSONB field

- [x] Task 8: Implement Outreach Pipeline (AC: #1, #3)
  - [x] 8.1 Create `pipeline.py` with `OutreachPipeline` class
  - [x] 8.2 Accept `LeadRepository`, `OutreachService` via injection
  - [x] 8.3 Implement `execute(batch_size: int = 10) -> PipelineResult`:
        - Query leads with status=QUALIFIED AND confidence >= 6
        - Process in batches
        - Update each lead after draft generation
        - Track statistics
  - [x] 8.4 Implement `generate_single(lead_id: UUID) -> GenerationResult`:
        - For manual draft trigger
  - [x] 8.5 Handle graceful degradation:
        - Continue on individual lead failure
        - Mark pipeline INCOMPLETE on critical errors
  - [x] 8.6 Add activity log entry for each generated draft

- [x] Task 9: Create Outreach Agent (AC: #1)
  - [x] 9.1 Create `agent.py` with `OutreachDraftAgent` class
  - [x] 9.2 Inherit from BaseAgent pattern
  - [x] 9.3 Implement `run() -> AgentResult`:
        - Execute outreach pipeline
        - Report statistics
  - [x] 9.4 Add scheduling support (daily 9 AM, after enrichment completes)
  - [x] 9.5 Use tier="generate" for LLM operations

- [x] Task 10: Update Lead Model and Repository (AC: #3)
  - [x] 10.1 Add `outreach_data` JSONB field to Lead model (if not exists)
  - [x] 10.2 Add `get_leads_for_outreach(limit: int) -> Sequence[Lead]`:
        - Query status=QUALIFIED, confidence >= 6, no existing draft
  - [x] 10.3 Add `update_outreach(lead_id: UUID, outreach_data: dict, status: LeadStatus) -> Lead`
  - [x] 10.4 Add `get_outreach_stats() -> dict`:
        - Count by status: QUALIFIED, OUTREACH_PENDING

- [x] Task 11: Create Approval Queue Integration (AC: #3)
  - [x] 11.1 Create `approval_integration.py` with `OutreachApprovalIntegration` class
  - [x] 11.2 Implement `submit_to_queue(draft: OutreachDraft, lead: Lead) -> ApprovalItem`:
        - Create approval item with source_type="b2b_outreach"
        - Include all display fields for approval UI
  - [x] 11.3 Implement `get_display_data(draft: OutreachDraft, lead: Lead) -> dict`:
        - Lead summary (company, location, contact)
        - Personalization hooks used
        - Template type selected
        - Suggested send time (business hours)

- [x] Task 12: Register in team_spec.py (AC: #1)
  - [x] 12.1 Add `OutreachDraftAgent` as RegisteredAgent with tier="generate"
  - [x] 12.2 Add `OutreachService` as RegisteredService
  - [x] 12.3 Add `OutreachDraftGenerator` as RegisteredService
  - [x] 12.4 Add `PersonalizationEngine` as RegisteredService
  - [x] 12.5 Add `LeadTypeClassifier` as RegisteredService
  - [x] 12.6 Add `OutreachValidator` as RegisteredService
  - [x] 12.7 Add `OutreachPipeline` as RegisteredService with capability="lead_outreach"

- [x] Task 13: Create comprehensive unit tests
  - [x] 13.1 Test OutreachTemplateRegistry template selection
  - [x] 13.2 Test LeadTypeClassifier with mocked LLM responses
  - [x] 13.3 Test PersonalizationEngine hook extraction
  - [x] 13.4 Test PersonalizationEngine product selection
  - [x] 13.5 Test OutreachDraftGenerator with mocked LLM
  - [x] 13.6 Test OutreachValidator forbidden patterns
  - [x] 13.7 Test OutreachService orchestration
  - [x] 13.8 Test OutreachPipeline batch processing
  - [x] 13.9 Test word count validation (150-250)
  - [x] 13.10 Test personalization token counting

- [x] Task 14: Create integration tests
  - [x] 14.1 Test full outreach pipeline with mocked external services
  - [x] 14.2 Test lead status transitions (QUALIFIED -> OUTREACH_PENDING)
  - [x] 14.3 Test outreach_data JSONB storage
  - [x] 14.4 Test activity logging for generated drafts
  - [x] 14.5 Test approval queue submission
  - [x] 14.6 Test template performance logging

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This story extends the B2B Lead Pipeline from Stories 5-1 and 5-2. The outreach module follows the same patterns.

**Outreach Pipeline:**
```
[QUALIFIED Leads] --> [Lead Classifier] --> [Template Selection]
       |                    |                      |
       v                    v                      v
[Personalization Engine] --> [Draft Generator (LLM)] --> [Brand Validator]
                                     |
                                     v
                          [Approval Queue Submission]
                                     |
                                     v
                          [OUTREACH_PENDING status]
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure]

```
teams/dawo/leads/
├── __init__.py                    # Add outreach exports
├── repository.py                  # EXTEND with outreach methods
├── scanner/                       # FROM Story 5-1 (unchanged)
├── enrichment/                    # FROM Story 5-2 (unchanged)
└── outreach/                      # CREATE THIS MODULE
    ├── __init__.py                # Export all public types
    ├── schemas.py                 # OutreachDraft, OutreachTemplate, etc.
    ├── config.py                  # OutreachConfig
    ├── templates.py               # OutreachTemplateRegistry
    ├── classifier.py              # LeadTypeClassifier
    ├── personalization.py         # PersonalizationEngine
    ├── generator.py               # OutreachDraftGenerator
    ├── validator.py               # OutreachValidator
    ├── service.py                 # OutreachService
    ├── pipeline.py                # OutreachPipeline
    ├── approval_integration.py    # OutreachApprovalIntegration
    └── agent.py                   # OutreachDraftAgent

tests/teams/dawo/test_leads/
└── test_outreach/                 # CREATE THIS
    ├── __init__.py
    ├── conftest.py                # Fixtures, mocks
    ├── test_templates.py
    ├── test_classifier.py
    ├── test_personalization.py
    ├── test_generator.py
    ├── test_validator.py
    ├── test_service.py
    ├── test_pipeline.py
    ├── test_approval_integration.py
    └── test_integration.py
```

### Lead Type Enum

**Source:** PRD FR19

```python
class LeadType(str, Enum):
    """Types of B2B leads for template selection."""

    HEALTH_STORE = "health_store"           # Helsekost butikk
    GYM_FITNESS = "gym_fitness"             # Treningssenter
    ONLINE_RETAILER = "online_retailer"     # Nettbutikk
    WELLNESS_CENTER = "wellness_center"     # Velvaeresenter
    SPECIALTY_GROCER = "specialty_grocer"   # Spesialbutikk
    GENERIC = "generic"                     # Fallback
```

### Outreach Data Schema

**Source:** [core/leads/models.py]

Store outreach results in the JSONB field:
```python
outreach_data = {
    "generated_at": "2026-02-09T09:00:00Z",
    "template_type": "health_store",
    "template_id": "hs-intro-v2",
    "draft": {
        "subject": "Samarbeid med DAWO - Funksjonelle sopp for din butikk",
        "body": "Hei [kontaktperson]...",
        "word_count": 185,
    },
    "personalization": {
        "hooks_used": [
            "Fokuserer pa okologiske produkter",
            "Forer allerede Lion's Mane fra annen leverandor"
        ],
        "products_recommended": ["Lion's Mane Extract", "Chaga Powder"],
        "value_prop": "Premium norsk kvalitet med full sporbarhet",
        "cta_type": "sample_offer",
    },
    "validation": {
        "brand_voice_pass": true,
        "generic_language_check": "pass",
        "word_count_valid": true,
        "personalization_score": 4,  # Number of tokens used
    },
    "suggested_send_time": "2026-02-10T10:00:00+01:00",  # Business hours
}
```

### Norwegian Outreach Templates

**Source:** [config/dawo_brand_profile.json], PRD FR19

**Template Structure:**
```python
HEALTH_STORE_TEMPLATE = """
Hei {{contact_name}},

{{personalization_opening}}

DAWO tilbyr premium funksjonelle sopp-ekstrakter som passer perfekt for {{business_focus}}.

{{product_recommendation}}

{{value_proposition}}

{{cta}}

Med vennlig hilsen,
DAWO Team
"""

# Example personalization_opening:
# "Jeg la merke til at dere fokuserer pa okologiske produkter og allerede
# forer funksjonelle sopp i sortimentet."

# Example CTA options:
CTA_MEETING = "Kan vi ta en kort samtale for a diskutere hvordan DAWO kan styrke sortimentet deres?"
CTA_SAMPLE = "Vi sender gjerne et proveprodukt sa dere kan oppleve kvaliteten selv."
CTA_CATALOG = "Jeg legger ved var produktkatalog - hvilke produkter ville vaere mest relevante for dere?"
```

### Brand Voice Validation Patterns

**Source:** [project-context.md#Norwegian-Content-Rules], Brand Voice Validator

**FORBIDDEN patterns in outreach:**
```python
FORBIDDEN_PATTERNS = [
    # Generic openers
    r"^Til hvem det matte gjelde",
    r"^Kjaere mottaker",
    r"^Vi er et selskap som",

    # Pushy sales language
    r"Kjop na!",
    r"Begrenset tilbud",
    r"Ikke ga glipp av",
    r"Eksklusivt tilbud",

    # Mass-mail indicators
    r"Hvis dette ikke er relevant",
    r"videresendt til riktig person",
    r"Avmeld deg her",
]

# REQUIRED brand voice elements
REQUIRED_ELEMENTS = [
    "warm tone",           # Not cold/corporate
    "educational angle",   # Share knowledge, not just sell
    "nordic simplicity",   # Clear, direct, not flowery
    "personal touch",      # Reference specific business details
]
```

### LLM Prompts

**Source:** tier="generate"

```python
# classifier.py
CLASSIFICATION_PROMPT = """
Classify this B2B lead into one of these categories based on their business profile:
- HEALTH_STORE: Helsekost butikk, natural products store
- GYM_FITNESS: Treningssenter, gym, fitness center
- ONLINE_RETAILER: Nettbutikk, e-commerce
- WELLNESS_CENTER: Spa, wellness, holistic health
- SPECIALTY_GROCER: Specialty food store, gourmet
- GENERIC: Cannot determine specific type

Business data:
{enrichment_data}

Return JSON with: category, confidence (0-100), reasoning
"""

# generator.py
DRAFT_GENERATION_PROMPT = """
Generate a personalized B2B outreach email in Norwegian for DAWO mushroom supplements.

Template:
{template}

Lead information:
- Company: {company}
- Business focus: {focus_areas}
- Personalization hooks: {hooks}
- Recommended products: {products}
- Value proposition: {value_prop}
- CTA type: {cta_type}

Requirements:
1. Write in warm, professional Norwegian
2. Length: 150-250 words
3. Reference their specific business naturally
4. Avoid generic sales language
5. Educational tone, not pushy
6. End with clear but soft CTA

Return the complete email body.
"""
```

### Integration with Previous Stories

**Source:** [5-1-b2b-lead-research-scanner.md], [5-2-lead-information-enrichment.md]

Reuse these components:
```python
# From leads module
from teams.dawo.leads.repository import LeadRepository
from teams.dawo.leads.models import Lead, LeadStatus

# From enrichment module
from teams.dawo.leads.enrichment.schemas import (
    EnrichmentResult,
    PersonalizationHook,
    BusinessInsights,
)

# From shared validators
from teams.dawo.validators.brand_voice import BrandVoiceValidator
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

The Outreach Draft Agent uses `tier="generate"` (maps to Sonnet at runtime) for all LLM operations.

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="outreach_draft_agent",
    agent_class=OutreachDraftAgent,
    capabilities=["lead_outreach", "email_generation"],
    tier="generate"  # Maps to Sonnet at runtime - NEVER use model names
)
```

### Suggested Send Time Logic

**Source:** PRD FR19

```python
def calculate_suggested_send_time(lead: Lead) -> datetime:
    """Calculate optimal send time for B2B outreach."""
    now = datetime.now(UTC)

    # Business hours: Tuesday-Thursday, 9-11 AM Norwegian time
    # Avoid Monday (busy) and Friday (winding down)

    oslo_tz = ZoneInfo("Europe/Oslo")
    local_now = now.astimezone(oslo_tz)

    # Find next Tuesday, Wednesday, or Thursday
    days_until_good_day = {
        0: 1,  # Mon -> Tue
        1: 0,  # Tue -> Tue (same day if before 11 AM)
        2: 0,  # Wed -> Wed
        3: 0,  # Thu -> Thu
        4: 4,  # Fri -> Tue
        5: 3,  # Sat -> Tue
        6: 2,  # Sun -> Tue
    }

    target_date = local_now + timedelta(days=days_until_good_day[local_now.weekday()])

    # Set time to 10:00 AM Oslo time
    target_time = target_date.replace(hour=10, minute=0, second=0, microsecond=0)

    # If today is a good day but past 11 AM, move to next good day
    if target_time <= local_now:
        target_time += timedelta(days=1)
        while target_time.weekday() not in (1, 2, 3):  # Tue, Wed, Thu
            target_time += timedelta(days=1)

    return target_time
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [5-2-lead-information-enrichment.md#Completion-Notes]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="generate"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(UTC)` not `datetime.utcnow()` |
| `activity_metadata` field naming | Use this field name for LeadActivity |
| Add logging to exception handlers | All exceptions logged before continuing |
| Graceful degradation | Pipeline continues on individual lead failure |
| TDD approach | Write tests first for each task |
| 133 tests benchmark | Aim for similar coverage (~100+ tests) |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER load config directly** - Accept via injection
2. **NEVER use LLM model names** - Use tier system
3. **NEVER swallow exceptions without logging**
4. **NEVER generate English content** - All output in Norwegian
5. **NEVER use generic templates** - Always personalize with at least 2 hooks

### Word Count Enforcement

**Source:** AC #2

```python
def validate_word_count(draft: str) -> tuple[bool, int]:
    """Validate draft is 150-250 words."""
    words = len(draft.split())
    is_valid = 150 <= words <= 250
    return is_valid, words

async def adjust_length(draft: str, llm: LLMClient) -> str:
    """Use LLM to adjust draft length if needed."""
    word_count = len(draft.split())

    if word_count < 150:
        prompt = f"Expand this Norwegian email to 150-200 words while keeping the same tone:\n{draft}"
    elif word_count > 250:
        prompt = f"Shorten this Norwegian email to 200-250 words while keeping key points:\n{draft}"
    else:
        return draft

    return await llm.generate(prompt)
```

### Approval Queue Integration

**Source:** [Epic 4 patterns], [ui/backend/routers/approval.py]

```python
# approval_integration.py
class OutreachApprovalIntegration:
    """Integrate outreach drafts with approval queue."""

    async def submit_to_queue(
        self,
        draft: OutreachDraft,
        lead: Lead,
    ) -> ApprovalItem:
        """Submit outreach draft to approval queue."""
        return ApprovalItem(
            id=uuid4(),
            source_type="b2b_outreach",
            content_type="email",
            title=f"Outreach: {lead.company}",
            preview=draft.subject,
            full_content=draft.body,
            metadata={
                "lead_id": str(lead.id),
                "company": lead.company,
                "contact": lead.contact_name,
                "template_type": draft.template_type.value,
                "personalization_hooks": draft.personalization_hooks,
                "suggested_send_time": draft.suggested_send_time.isoformat(),
            },
            quality_score=draft.personalization_score,  # Based on personalization depth
            compliance_status="COMPLIANT",  # B2B emails don't need EU health claims check
            created_at=datetime.now(UTC),
        )
```

### Project Structure Notes

- Follows unified project structure from Stories 5-1 and 5-2
- All modules under `teams/dawo/leads/outreach/`
- Tests mirror implementation structure in `tests/teams/dawo/test_leads/test_outreach/`
- No detected conflicts with existing patterns

### References

- [Source: epics.md#Story-5.3] - Original story requirements
- [Source: 5-1-b2b-lead-research-scanner.md] - Scanner implementation patterns
- [Source: 5-2-lead-information-enrichment.md] - Enrichment patterns and learnings
- [Source: core/leads/models.py] - Lead model with outreach_data field
- [Source: project-context.md#Norwegian-Content-Rules] - Norwegian content requirements
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology
- [Source: config/dawo_brand_profile.json] - Brand voice guidelines

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

| Learning | Detail |
|----------|--------|
| Protocol-based DI for integration tests | Service uses Protocol classes for dependency injection; mock classes must match Protocol signatures |
| 181 total tests achieved | 158 unit tests + 23 integration tests covering all acceptance criteria |
| TDD workflow maintained | All components developed test-first with mocked dependencies |
| Norwegian content throughout | All templates, CTAs, and generated content in Norwegian as required |
| Graceful degradation | Pipeline continues processing on individual lead failures |
| Logging for observability | Template selection and generation activity logged for performance tracking |

### File List

**Implementation Files (12 files):**
- `teams/dawo/leads/outreach/__init__.py`
- `teams/dawo/leads/outreach/schemas.py`
- `teams/dawo/leads/outreach/config.py`
- `teams/dawo/leads/outreach/templates.py`
- `teams/dawo/leads/outreach/classifier.py`
- `teams/dawo/leads/outreach/personalization.py`
- `teams/dawo/leads/outreach/generator.py`
- `teams/dawo/leads/outreach/validator.py`
- `teams/dawo/leads/outreach/service.py`
- `teams/dawo/leads/outreach/pipeline.py`
- `teams/dawo/leads/outreach/agent.py`
- `teams/dawo/leads/outreach/approval_integration.py`

**Test Files (14 files):**
- `tests/teams/dawo/test_leads/test_outreach/__init__.py`
- `tests/teams/dawo/test_leads/test_outreach/conftest.py`
- `tests/teams/dawo/test_leads/test_outreach/test_schemas.py`
- `tests/teams/dawo/test_leads/test_outreach/test_config.py`
- `tests/teams/dawo/test_leads/test_outreach/test_templates.py`
- `tests/teams/dawo/test_leads/test_outreach/test_classifier.py`
- `tests/teams/dawo/test_leads/test_outreach/test_personalization.py`
- `tests/teams/dawo/test_leads/test_outreach/test_generator.py`
- `tests/teams/dawo/test_leads/test_outreach/test_validator.py`
- `tests/teams/dawo/test_leads/test_outreach/test_service.py`
- `tests/teams/dawo/test_leads/test_outreach/test_pipeline.py`
- `tests/teams/dawo/test_leads/test_outreach/test_agent.py`
- `tests/teams/dawo/test_leads/test_outreach/test_approval_integration.py`
- `tests/teams/dawo/test_leads/test_outreach/test_integration.py`

**Modified Files:**
- `teams/dawo/team_spec.py` - Registered agent and services
- `teams/dawo/leads/repository.py` - Added outreach query methods

**New Files (from Epic 5 foundation):**
- `core/leads/models.py` - Lead model with OUTREACH_PENDING status and outreach_data fields
- `migrations/versions/2026_02_09_002_add_outreach_data_to_leads.py` - Database migration
