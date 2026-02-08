---
project_name: 'DAWO.ECO'
platform: 'IMAGO.ECO'
date: '2026-02-05'
---

# Project Context for AI Agents

_Critical rules for implementing DAWO.ECO agents on the IMAGO.ECO platform._

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Backend | Python + FastAPI | 3.11+ |
| Database | PostgreSQL | 16 |
| Cache/Queue | Redis + ARQ | 7 |
| ORM | Async SQLAlchemy + Alembic | - |
| Frontend | React + CopilotKit | 18 / 1.50 |
| Styling | Tailwind CSS + shadcn/ui | - |
| Agent Framework | Google ADK | - |
| Auth | Firebase Authentication | - |

---

## Critical Implementation Rules

### Agent Registration (MUST FOLLOW)

- ✅ Register ALL agents via `team_spec.py` using `RegisteredAgent`
- ✅ Use capability tags for shared agent resolution
- ❌ NEVER use `@register_agent` decorators
- ❌ NEVER self-register agents

```python
# CORRECT: team_spec.py
AGENTS = [
    RegisteredAgent(
        name="eu_compliance_checker",
        agent_class=EUComplianceChecker,
        capabilities=["eu_compliance", "content_validation"],
        tier="generate"  # Use tier name, NOT model name like "sonnet"
    )
]
```

### Configuration Loading (MUST FOLLOW)

- ✅ Accept config via constructor injection from Team Builder
- ✅ Team Builder injects brand profile, compliance rules, etc.
- ❌ NEVER load config files directly: `json.load(open("config/..."))`

```python
# CORRECT
class ContentGenerator(BaseAgent):
    def __init__(self, brand_profile: BrandProfile):
        self.brand = brand_profile

# WRONG
class ContentGenerator(BaseAgent):
    def __init__(self):
        with open("config/brand.json") as f:
            self.brand = json.load(f)
```

### LLM Tier Assignment

Default tiers by task type (user can override in settings):

| Task Type | Default Tier | Use For |
|-----------|--------------|---------|
| `scan` | haiku | High-volume research, source discovery |
| `generate` | sonnet | Content writing, compliance checking |
| `strategize` | opus | Campaign planning, complex decisions |

- ❌ NEVER hardcode LLM model names in agent code

### External API Calls (MUST FOLLOW)

- ✅ ALL external calls go through retry middleware
- ✅ Use integrations from `integrations/` folder
- ❌ NEVER make direct API calls without retry wrapper

Retry policy: 3 attempts, exponential backoff (1min, 5min, 15min), then mark incomplete.

### EU Compliance (CRITICAL)

- ✅ ALL content must pass EU Compliance Checker before approval
- ✅ Use patterns from `config/dawo_compliance_rules.json`
- ✅ Zero approved health claims for functional mushrooms (EC 1924/2006)
- ❌ NEVER auto-approve content without compliance check

---

## Code Organization

### Directory Structure

```
teams/dawo/
├── scanners/       # Research agents (scan tier)
├── generators/     # Content creation (generate tier)
├── validators/     # Compliance & quality (generate tier)
├── orchestrators/  # Team coordinators (strategize tier)
└── team_spec.py    # ALL registrations here
```

### Agent Package Structure

Complex agents (>2 files):
```
agent_name/
├── __init__.py
├── agent.py      # Main agent class
├── prompts.py    # System prompts
└── tools.py      # Agent tools
```

Simple agents: single `agent_name.py` file is acceptable.

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Python files | snake_case | `eu_compliance_checker.py` |
| Python classes | PascalCase | `EUComplianceChecker` |
| Database tables | snake_case, plural | `approval_items` |
| API endpoints | snake_case | `/api/agents` |
| JSON fields | snake_case | `team_id`, `created_at` |
| Config files | snake_case | `dawo_brand_profile.json` |

---

## Platform Integration

### Approval Workflow

All content-generating agents must:
1. Call `submit_for_approval()` with content
2. Include source priority: trending(1), scheduled(2), evergreen(3), research(4)
3. Wait for human review before publishing

### Shared Agent Resolution

Request shared agents by capability:
```python
compliance_checker = await registry.get_by_capability("eu_compliance")
brand_validator = await registry.get_by_capability("brand_voice")
```

### Harvester Framework (Research Teams)

Research teams follow: scanner → harvester → transformer → validator → publisher

---

## Anti-Patterns (NEVER DO)

1. ❌ `config = json.load(open(...))` → Use injection
2. ❌ `@register_agent` decorators → Use team_spec.py
3. ❌ `model="claude-3-sonnet"` hardcoded → Use tier system
4. ❌ `requests.get(external_url)` → Use retry middleware
5. ❌ Auto-publish without compliance check → Always validate

---

## Code Review Checklist (REQUIRED)

### Tier Terminology (CRITICAL - caught 3x in Epic 1)

**FORBIDDEN in agent code/docstrings/comments:**
- ❌ `haiku`, `sonnet`, `opus` (model names)
- ❌ `claude-haiku`, `claude-sonnet`, `claude-opus`
- ❌ Any hardcoded model IDs

**REQUIRED tier terminology:**
- ✅ `scan` (maps to Haiku at runtime)
- ✅ `generate` (maps to Sonnet at runtime)
- ✅ `strategize` (maps to Opus at runtime)

**Grep check before commit:**
```bash
# This should return NO matches in teams/dawo/**/*.py
grep -rE "(haiku|sonnet|opus)" teams/dawo/ --include="*.py" | grep -v "test_"
```

### Module Exports (caught 3x in Epic 1)

- ✅ Every `__init__.py` MUST have `__all__` list
- ✅ Export ALL public classes, functions, types, enums
- ✅ Include Protocol types used for dependency injection

### Code Quality

- ✅ No unused imports (dead code)
- ✅ No magic numbers - use named constants
- ✅ Logging in ALL exception handlers (no silent swallowing)
- ✅ Type hints on all public methods
- ✅ Docstrings on all classes and public methods

### Configuration

- ✅ Config loaded via constructor injection
- ✅ No direct file loading in business classes
- ✅ Validation in `__post_init__` or constructor

---

## Epic 3: Content Generation Patterns

### Content Generator Framework

Content generators follow this pipeline:
1. **Research Selection** - Pick high-scoring item from Research Pool
2. **Product Enrichment** - Fetch product data via Shopify integration
3. **Caption Generation** - LLM generates Norwegian caption (tier="generate")
4. **Asset Generation** - Orshot graphic OR Gemini AI image
5. **Validation** - EU Compliance + Brand Voice checks
6. **Scoring** - Quality score calculation
7. **Submission** - Submit to approval queue with assets

### LLM-Chaining Pattern (from Epic 2)

For multi-stage LLM operations, follow the Instagram Scanner pattern:

```python
# Stage 1: Extract themes (tier="generate")
themes = await theme_extractor.extract(content)

# Stage 2: Detect claims using themes (tier="generate")
claims = await claim_detector.detect(content, themes=themes)

# Each stage is independently mockable and testable
```

**Testing LLM chains:**
```python
# Use mock factories for consistent test setup
def create_theme_extractor_mock(themes: list[str]) -> Mock:
    mock = AsyncMock(spec=ThemeExtractor)
    mock.extract.return_value = themes
    return mock
```

### Integration Clients (Epic 3)

All integrations in `integrations/` folder with Protocol + Implementation:

| Integration | Protocol | Client | Purpose |
|-------------|----------|--------|---------|
| Shopify | `ShopifyClientProtocol` | `ShopifyClient` | Product data (1hr cache) |
| Google Drive | `GoogleDriveClientProtocol` | `GoogleDriveClient` | Asset storage |
| Orshot | `OrshotClientProtocol` | `OrshotClient` | Branded graphics |
| Gemini | `GeminiImageClientProtocol` | `GeminiImageClient` | AI images |

**Always inject via Protocol for testability:**
```python
class CaptionGenerator:
    def __init__(
        self,
        shopify: ShopifyClientProtocol,
        brand_profile: BrandProfile,
    ):
        self._shopify = shopify
        self._brand = brand_profile
```

### Norwegian Content Rules

- ✅ Captions: 180-220 words in Norwegian
- ✅ Use `config/dawo_brand_profile.json` → `norwegian` section
- ✅ Check forbidden terms in BOTH English and Norwegian
- ✅ Hashtags: max 15, include brand tags (#DAWO, #DAWOmushrooms)
- ❌ Never machine-translate English captions - generate natively

### Asset Storage Folders

Google Drive structure (auto-created):
```
DAWO.ECO/Assets/
├── Generated/    # Nano Banana AI images
├── Orshot/       # Branded graphics
└── Archive/      # Used assets + performance data
```

Filename pattern: `{date}_{type}_{topic}_{id}.{ext}`

### Quality Scoring Components (Story 3.7)

Content quality score (0-10) comprises:
1. **Brand Voice Alignment** - Matches DAWO tone pillars
2. **EU Compliance** - No prohibited claims
3. **AI Detectability** - Human-like writing
4. **Visual Quality** - Asset resolution/composition
5. **Engagement Prediction** - Based on historical data
6. **Relevance** - Research source quality

Auto-publish threshold: score >= 9 AND compliance = PASS
