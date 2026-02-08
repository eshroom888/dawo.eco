# Story 3.3: Instagram Caption Generator

Status: done

---

## Story

As an **operator**,
I want Instagram captions generated in Norwegian using brand voice,
So that posts are ready for review without manual writing.

---

## Acceptance Criteria

1. **Given** a research item is selected for content
   **When** the caption generator runs
   **Then** it produces a Norwegian caption (180-220 words)
   **And** it follows DAWO brand voice: warm, educational, Nordic simplicity
   **And** it includes a clear CTA (call-to-action)
   **And** it references the research source appropriately

2. **Given** product data is available from Shopify
   **When** the generator builds the caption
   **Then** it weaves in relevant product benefits naturally
   **And** it includes product link with UTM parameters
   **And** it avoids direct sales language (educational first)

3. **Given** the caption is generated
   **When** it's evaluated
   **Then** it's checked against Brand Voice Validator (Epic 1)
   **And** revision suggestions are included if needed
   **And** generation completes in < 60 seconds

---

## Tasks / Subtasks

- [x] Task 1: Create CaptionGenerator agent class (AC: #1)
  - [x] 1.1 Create `teams/dawo/generators/instagram_caption/` package structure
  - [x] 1.2 Implement `CaptionGeneratorProtocol` for testability
  - [x] 1.3 Implement `CaptionGenerator` class with constructor injection pattern
  - [x] 1.4 Accept `BrandProfile`, `ShopifyClientProtocol`, `BrandVoiceValidator` via injection
  - [x] 1.5 Create `CaptionRequest` and `CaptionResult` dataclasses

- [x] Task 2: Implement Norwegian caption generation (AC: #1)
  - [x] 2.1 Create `prompts.py` with system prompt for Norwegian caption writing
  - [x] 2.2 Load Norwegian section from `config/dawo_brand_profile.json` via injection
  - [x] 2.3 Enforce 180-220 word count in prompt and validate post-generation
  - [x] 2.4 Include tone pillars: warm, educational, nordic_simplicity
  - [x] 2.5 Structure: Hook → Story → Connection → CTA (per caption_guidelines)
  - [x] 2.6 Generate max 15 hashtags including brand tags (#DAWO, #DAWOmushrooms, #nordisksopp)

- [x] Task 3: Integrate research source context (AC: #1)
  - [x] 3.1 Accept `ResearchItem` from Research Pool as input
  - [x] 3.2 Extract research source type (reddit, youtube, pubmed, news, instagram)
  - [x] 3.3 Reference source appropriately: studies with citations, social for trends
  - [x] 3.4 Avoid claiming research proves health benefits (EU compliance)

- [x] Task 4: Integrate Shopify product data (AC: #2)
  - [x] 4.1 Use `ShopifyClientProtocol` to fetch product by handle or topic keywords
  - [x] 4.2 Weave product benefits naturally (not sales-y)
  - [x] 4.3 Use `build_utm_url()` for product link with params: source=instagram, medium=post
  - [x] 4.4 Handle missing product gracefully (generate without product link)
  - [x] 4.5 Respect Novel Food classification (food vs supplement messaging)

- [x] Task 5: Implement Brand Voice validation (AC: #3)
  - [x] 5.1 Call `BrandVoiceValidator.validate()` after generation
  - [x] 5.2 Include validation result in `CaptionResult`
  - [x] 5.3 If validation fails, include revision suggestions from validator
  - [x] 5.4 Track validation score for quality scoring (Story 3.7)

- [x] Task 6: Implement AI-generic pattern detection (AC: #3)
  - [x] 6.1 Check generated caption against `ai_generic_patterns` from Norwegian profile
  - [x] 6.2 Flag and suggest rewrites for detected patterns
  - [x] 6.3 Add `authenticity_score` to CaptionResult

- [x] Task 7: Register CaptionGenerator in team_spec.py (AC: #1, #2, #3)
  - [x] 7.1 Add `CaptionGenerator` as RegisteredAgent with tier="generate"
  - [x] 7.2 Add capability tags: "caption_generation", "content_generation", "norwegian"
  - [x] 7.3 Register as service for injection

- [x] Task 8: Create unit tests
  - [x] 8.1 Test caption word count enforcement (180-220)
  - [x] 8.2 Test hashtag generation and brand tag inclusion
  - [x] 8.3 Test product data integration with mock ShopifyClient
  - [x] 8.4 Test UTM parameter generation in links
  - [x] 8.5 Test Brand Voice validation integration
  - [x] 8.6 Test AI-generic pattern detection
  - [x] 8.7 Test < 60 second generation time
  - [x] 8.8 Mock LLM responses using fixtures from Epic 2 patterns

- [x] Task 9: Create integration tests
  - [x] 9.1 Test end-to-end caption generation (skipped unless CAPTION_INTEGRATION_TEST=1)
  - [x] 9.2 Test with real research item from Research Pool
  - [x] 9.3 Test with real Shopify product data

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Implementation-Patterns], [project-context.md#Agent-Registration]

This story creates the first content generator agent in the DAWO team. Follow the existing patterns from:
- `teams/dawo/validators/brand_voice/` - Agent package structure with prompts.py, agent.py
- `teams/dawo/scanners/instagram/` - LLM chaining pattern (ThemeExtractor → HealthClaimDetector)

**Key Pattern:** All content generators follow the Content Generator Framework from project-context.md:
1. Research Selection → 2. Product Enrichment → 3. Caption Generation → 4. Validation → 5. Scoring → 6. Submission

### File Structure (MUST FOLLOW)

**Source:** [architecture.md#Agent-Package-Structure]

```
teams/dawo/generators/
├── __init__.py                       # Export CaptionGenerator, CaptionGeneratorProtocol
├── instagram_caption/
│   ├── __init__.py                   # Package exports
│   ├── agent.py                      # CaptionGenerator class
│   ├── prompts.py                    # System prompts for Norwegian caption generation
│   ├── schemas.py                    # CaptionRequest, CaptionResult dataclasses
│   └── tools.py                      # Caption-specific utilities (hashtag generation, word count)
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment], [team_spec.py]

```python
# CORRECT: Use tier name
tier=TIER_GENERATE  # Maps to Sonnet at runtime for content creation

# FORBIDDEN in code/docstrings/comments:
# - "haiku", "sonnet", "opus"
# - "claude-haiku", "claude-sonnet", "claude-opus"
# - Any hardcoded model IDs
```

### Norwegian Caption Guidelines (CRITICAL)

**Source:** [config/dawo_brand_profile.json#norwegian.caption_guidelines]

```python
# Caption structure (inject into prompts.py)
CAPTION_STRUCTURE = [
    "Hook: Opening line that captures attention naturally",
    "Story: Educational content about mushrooms/wellness",
    "Connection: Relate to Nordic lifestyle/seasons",
    "CTA: Gentle call-to-action (link in bio, check out, etc.)"
]

# Length constraints
MIN_WORDS = 180
MAX_WORDS = 220

# Hashtag rules
MAX_HASHTAGS = 15
BRAND_TAGS = ["#DAWO", "#DAWOmushrooms", "#nordisksopp"]  # MUST include
```

### Brand Voice Tone Pillars (Norwegian)

**Source:** [config/dawo_brand_profile.json#norwegian.tone_pillars]

| Pillar | Description | Positive Markers | Avoid |
|--------|-------------|------------------|-------|
| `warm` | Varm, inviterende, personlig | vi, vår, sammen, dele, fellesskap | konsern, forbrukere, kunder |
| `educational` | Informativ først, salg deretter | lære, oppdage, tradisjon, forskning | kjøp nå, begrenset tid |
| `nordic_simplicity` | Rent, minimalt, autentisk | skog, natur, nordisk, enkel, arv | revolusjonerende, ultimate |

### Forbidden Terms (Norwegian) - REJECT IMMEDIATELY

**Source:** [config/dawo_brand_profile.json#norwegian.forbidden_terms]

- **Medicinal:** behandling, kur, helbrede, medisin, sykdom, symptom, diagnose, resept, pasient, terapi, klinisk
- **Sales pressure:** kjøp nå, begrenset tid, skynd deg, siste sjanse, bestill nå
- **Superlatives:** beste, ultimate, revolusjonerende, mirakel, utrolig, sinnssykt

### AI-Generic Patterns to Avoid (Norwegian)

**Source:** [config/dawo_brand_profile.json#norwegian.ai_generic_patterns]

```python
AI_PATTERNS_NO = [
    "I dagens hektiske verden",
    "Er du på utkikk etter",
    "Se ikke lenger",
    "Til syvende og sist",
    "Ta din .* til neste nivå",
    "Lås opp ditt potensial",
    "Transformer din",
    "Game-changing",
    "For å oppsummere",
]
```

### Good vs Bad Caption Examples

**Source:** [config/dawo_brand_profile.json#norwegian.style_examples]

**GOOD (use these patterns):**
- "Vi har sanket i nordiske skoger i generasjoner. Løvemanke har vært en del av den reisen."
- "Enkle råvarer. Ærlig opprinnelse. Det er det vi tror på."
- "Naturen stresser ikke. Det gjør ikke vi heller. Hver batch tar sin tid."

**BAD (NEVER generate):**
- "REVOLUSJONERENDE sopptilskudd som vil TRANSFORMERE din kognitive ytelse!"
- "Er du på utkikk etter den BESTE løvemanke på markedet? Se ikke lenger!"
- "Vår klinisk beviste formel behandler hjernetåke og kurerer mental utmattelse."

### Shopify Integration Pattern

**Source:** [3-1-shopify-product-data-integration.md#Dev-Notes], [project-context.md#Integration-Clients]

```python
from integrations.shopify import (
    ShopifyClientProtocol,
    ShopifyProduct,
    build_utm_url,
)

class CaptionGenerator:
    def __init__(
        self,
        shopify: ShopifyClientProtocol,  # Inject via Protocol
        brand_profile: BrandProfile,
        brand_validator: BrandVoiceValidator,
    ) -> None:
        self._shopify = shopify
        self._brand = brand_profile
        self._validator = brand_validator

    async def generate(self, request: CaptionRequest) -> CaptionResult:
        # Fetch product if topic matches
        product = await self._shopify.get_product_by_handle(request.product_handle)

        # Build UTM link
        if product:
            product_link = build_utm_url(
                base_url=product.product_url,
                content_type="feed_post",
                post_id=request.content_id,
            )
```

### Novel Food Classification (CRITICAL)

**Source:** [project-context.md#EU-Compliance], [3-1-shopify-product-data-integration.md]

```python
# Product classification affects messaging
if product.novel_food_classification == "supplement":
    # Use supplement messaging (Chaga, kosttilskudd)
    # More restricted language, no food claims
elif product.novel_food_classification == "food":
    # General wellness messaging allowed
    # Can reference culinary/lifestyle uses
```

### Brand Voice Validator Integration

**Source:** [teams/dawo/validators/brand_voice/], [team_spec.py]

```python
from teams.dawo.validators.brand_voice import BrandVoiceValidator

# After caption generation
validation_result = await self._validator.validate(caption_text)

if validation_result.status == "NEEDS_REVISION":
    # Include suggestions in result
    caption_result.revision_suggestions = validation_result.suggestions
    caption_result.brand_score = validation_result.score
```

### CaptionRequest and CaptionResult Schemas

**Source:** Design based on Epic 3 requirements

```python
# schemas.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class CaptionRequest:
    """Input for caption generation."""
    research_item_id: str
    research_source: str  # reddit, youtube, pubmed, news, instagram
    research_content: str  # Extracted insights
    research_tags: list[str]
    product_handle: Optional[str] = None  # Shopify product handle
    content_id: str = ""  # For UTM tracking
    target_topic: str = ""  # Primary topic for hashtag selection

@dataclass
class CaptionResult:
    """Output from caption generation."""
    caption_text: str
    word_count: int
    hashtags: list[str]
    product_link: Optional[str]  # With UTM params
    brand_voice_status: str  # PASS, NEEDS_REVISION, FAIL
    brand_voice_score: float  # 0.0 - 1.0
    revision_suggestions: list[str]
    authenticity_score: float  # AI-generic pattern detection
    generation_time_ms: int
    created_at: datetime
```

### System Prompt Template (prompts.py)

**Source:** Design based on brand profile and Epic 3 requirements

```python
CAPTION_SYSTEM_PROMPT = """Du er en innholdsskaper for DAWO, et nordisk soppmerkevare.

STEMME OG TONE:
- Varm og inviterende, aldri korporativ
- Informativ først, salg kommer naturlig
- Nordisk enkelhet - rent, autentisk, ærlig

STRUKTUR (følg denne rekkefølgen):
1. HOOK: Åpningslinje som fanger oppmerksomhet naturlig
2. STORY: Utdannende innhold om sopp/velvære
3. TILKNYTNING: Relater til nordisk livsstil/årstider
4. CTA: Myk oppfordring til handling (link i bio, sjekk ut, osv.)

REGLER:
- Skriv på norsk, 180-220 ord
- Bruk positive markører: vi, vår, tradisjon, natur, skog
- ALDRI bruk: behandling, kur, helbrede, symptom, diagnose
- ALDRI bruk salgstrykk: kjøp nå, begrenset tid, siste sjanse
- ALDRI bruk superlativer: beste, ultimate, revolusjonerende

HASHTAGS:
- Inkluder alltid: #DAWO #DAWOmushrooms #nordisksopp
- Maks 15 totalt
- Velg fra relevante emner: {topic_hashtags}

FORSKNING REFERANSE:
- Kilde: {research_source}
- Innhold: {research_content}
- Referer til kunnskap, ikke helsepåstander

PRODUKT (hvis tilgjengelig):
- Navn: {product_name}
- Fordeler: {product_benefits}
- Klassifisering: {novel_food_classification}
- Link: {product_link}
"""
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [3-1-shopify-product-data-integration.md], [3-2-google-drive-asset-storage.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Export CaptionGenerator, CaptionGeneratorProtocol, CaptionRequest, CaptionResult |
| Config injection pattern | Accept BrandProfile via constructor, never `json.load(open(...))` |
| `datetime` deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | Log all LLM and API errors before returning fallback |
| F-string logging anti-pattern | Use % formatting for lazy evaluation |
| Integration tests separate | Create test_integration.py with env var skip markers |
| run_in_executor for sync calls | Wrap any synchronous operations in executor |

### LLM Chaining Pattern (from Epic 2)

**Source:** [project-context.md#LLM-Chaining-Pattern]

If multi-stage processing is needed (e.g., draft → refine → validate):

```python
# Stage 1: Generate initial caption
draft = await self._generate_draft(request)

# Stage 2: Refine for brand voice
refined = await self._refine_caption(draft)

# Stage 3: Validate compliance
validated = await self._validator.validate(refined)
```

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], [architecture.md#Anti-Patterns]

1. **NEVER load config directly** - Accept BrandProfile via injection
2. **NEVER hardcode model names** - Use tier system
3. **NEVER swallow exceptions without logging** - Log all errors
4. **NEVER generate English captions** - Always Norwegian
5. **NEVER include medicinal terms** - EU compliance critical
6. **NEVER exceed 15 hashtags** - Platform limit

### Test Fixtures

**Source:** [tests/integrations/test_shopify/conftest.py] patterns

```python
# tests/teams/dawo/generators/test_instagram_caption/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_shopify_client():
    """Mock ShopifyClient for caption tests."""
    client = AsyncMock()
    client.get_product_by_handle.return_value = ShopifyProduct(
        id="gid://shopify/Product/123",
        title="Løvemanke Ekstrakt",
        handle="lovemanke-ekstrakt",
        description="<p>Premium løvemanke fra nordiske skoger</p>",
        price="299.00",
        currency="NOK",
        product_url="https://dawo.no/products/lovemanke-ekstrakt",
        novel_food_classification="supplement",
    )
    return client

@pytest.fixture
def mock_brand_validator():
    """Mock BrandVoiceValidator."""
    validator = AsyncMock()
    validator.validate.return_value = BrandVoiceResult(
        status="PASS",
        score=0.85,
        suggestions=[],
    )
    return validator

@pytest.fixture
def sample_research_item():
    """Sample research item for caption generation."""
    return CaptionRequest(
        research_item_id="ri_123",
        research_source="pubmed",
        research_content="Study shows lion's mane supports cognitive function",
        research_tags=["lions_mane", "cognition", "nootropic"],
        product_handle="lovemanke-ekstrakt",
        content_id="post_456",
        target_topic="wellness",
    )
```

### Registration in team_spec.py

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py (add to existing registrations)

from teams.dawo.generators.instagram_caption import (
    CaptionGenerator,
    CaptionGeneratorProtocol,
)

AGENTS: List[RegisteredAgent] = [
    # ... existing agents ...
    RegisteredAgent(
        name="instagram_caption_generator",
        agent_class=CaptionGenerator,
        capabilities=["caption_generation", "content_generation", "norwegian"],
        tier=TIER_GENERATE,  # Uses Sonnet for quality content creation
    ),
]
```

### Project Structure Notes

- **Location**: `teams/dawo/generators/instagram_caption/` (new package)
- **Dependencies**: ShopifyClient (Story 3.1), BrandVoiceValidator (Story 1.3), BrandProfile
- **Used by**: Content Team orchestrator (future), Approval Manager
- **LLM Tier**: generate (maps to Sonnet)
- **Performance**: < 60 seconds per caption

### References

- [Source: epics.md#Story-3.3] - Original story requirements
- [Source: architecture.md#Agent-Package-Structure] - Package patterns
- [Source: project-context.md#LLM-Tier-Assignment] - Tier system
- [Source: project-context.md#Content-Generator-Framework] - Pipeline pattern
- [Source: config/dawo_brand_profile.json] - Norwegian brand guidelines
- [Source: teams/dawo/validators/brand_voice/] - Validator integration
- [Source: integrations/shopify/] - Product data and UTM utilities
- [Source: 3-1-shopify-product-data-integration.md] - Previous story learnings
- [Source: 3-2-google-drive-asset-storage.md] - Previous story learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed circular import between `integrations.shopify` and `teams.dawo.middleware` by implementing lazy imports in `integrations/__init__.py`, `integrations/shopify/__init__.py`, and `teams/dawo/__init__.py`

### Completion Notes List

- Created CaptionGenerator agent with full Norwegian caption generation pipeline
- Implemented CaptionRequest/CaptionResult dataclasses for type-safe API
- Created prompts.py with comprehensive Norwegian caption system prompt following DAWO brand voice
- Integrated Shopify product data with UTM parameter generation
- Integrated Brand Voice Validator for caption validation
- Implemented AI-generic pattern detection with authenticity scoring
- Created tools.py with word counting, hashtag generation, and research citation utilities
- Registered CaptionGenerator in team_spec.py with tier=TIER_GENERATE
- All 36 unit tests pass, 3 integration tests properly skipped (require CAPTION_INTEGRATION_TEST=1)

### File List

**New Files:**
- teams/dawo/generators/instagram_caption/__init__.py
- teams/dawo/generators/instagram_caption/agent.py
- teams/dawo/generators/instagram_caption/prompts.py
- teams/dawo/generators/instagram_caption/schemas.py
- teams/dawo/generators/instagram_caption/tools.py
- tests/teams/dawo/generators/test_instagram_caption/__init__.py
- tests/teams/dawo/generators/test_instagram_caption/conftest.py
- tests/teams/dawo/generators/test_instagram_caption/test_caption_generator.py
- tests/teams/dawo/generators/test_instagram_caption/test_integration.py

**Modified Files:**
- teams/dawo/generators/__init__.py (added CaptionGenerator exports)
- teams/dawo/team_spec.py (added CaptionGenerator registration, fixed circular imports)
- teams/dawo/__init__.py (lazy imports to fix circular dependency)
- integrations/__init__.py (lazy imports to fix circular dependency)
- config/dawo_brand_profile.json (updated Norwegian caption guidelines)

---

## Change Log

- 2026-02-07: Story 3.3 implementation completed - Instagram Caption Generator with full Norwegian support, brand voice validation, AI pattern detection, and 36 passing tests
- 2026-02-07: Code review fixes - Corrected File List (removed false integrations/shopify/__init__.py claim, added config/dawo_brand_profile.json), exported missing utility functions in __init__.py

