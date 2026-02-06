---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: 'complete'
completedAt: '2026-02-05'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/imago-refactoring-brief.md'
  - '_bmad-output/planning-artifacts/imago-platform-gaps.md'
  - 'docs/bmad/project-brief.md'
workflowType: 'architecture'
project_name: 'DAWO.ECO'
user_name: 'eshroom'
date: '2026-02-05'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
DAWO.ECO comprises 55 functional requirements across 5 departments:
- **Research Department (FR-101 to FR-106)**: Reddit, YouTube, PubMed, Instagram, News research teams using Harvester Framework pattern
- **Content Department (FR-201 to FR-212)**: Instagram content generation with EU compliance checking, brand voice validation, and Orshot graphics integration
- **Sales Department (FR-301 to FR-306)**: B2B lead research and personalized outreach draft generation
- **CleanMarket Department (FR-401 to FR-404)**: Competitor compliance violation detection and reporting
- **Platform Core (FR-501 to FR-527)**: Approval workflows, scheduling, analytics, configuration management

**Non-Functional Requirements:**
- **Compliance**: EU Health Claims Regulation (EC 1924/2006) enforcement - zero approved health claims for functional mushrooms
- **Cost Optimization**: LLM tiering (Haiku/Sonnet/Opus) based on task complexity
- **Single Operator**: All workflows designed for one-person review capacity
- **Progressive Trust**: Simulated auto-publish before real automation
- **Integration Reliability**: Must handle external API failures gracefully (Instagram, Discord, Orshot, Shopify)

**Scale & Complexity:**

- Primary domain: AI Agent Orchestration with Multi-Team Workflows
- Complexity level: High
- Estimated architectural components: 15+ agent teams, 4 shared stage agents, 5 external integrations

### Technical Constraints & Dependencies

| Constraint | Impact |
|------------|--------|
| IMAGO.ECO Platform | Must use existing FastAPI backend, PostgreSQL/Redis, Google ADK agent framework |
| Platform Test Team Pattern | Agent registration via `team_spec.py`, RegisteredAgent model, AgentRegistry |
| Team Builder | Dynamic composition based on capabilities and performance metrics |
| Approval Manager | All content requiring review routes through existing HITL workflow |
| Harvester Framework | Research teams follow scanner → harvester → transformer → validator → publisher pattern |
| EU Compliance | Every content output must pass compliance checking before approval |

### Cross-Cutting Concerns Identified

1. **EU Compliance Checking** - Shared agent used by Content, Sales, and potentially CleanMarket teams
2. **Brand Voice Validation** - Shared agent ensuring DAWO tone/terminology consistency
3. **Approval Workflow Routing** - All teams feed into single approval queue with priority/urgency
4. **Activity Logging** - Unified logging for supervisor dashboard and analytics
5. **LLM Cost Management** - Consistent tier assignment across all teams
6. **Error Handling** - Graceful degradation when external APIs fail

## Starter Template Evaluation

### Primary Technology Domain

**Brownfield Extension** - DAWO.ECO extends the existing IMAGO.ECO platform rather than starting from a new template.

### Existing Platform Foundation

IMAGO.ECO provides a production-ready foundation with these decisions already made:

**Language & Runtime:**
- Python 3.11+ with full async support
- TypeScript/JavaScript (React frontend)
- Type hints throughout backend codebase

**Backend Architecture:**
- FastAPI with async request handling
- PostgreSQL 16 with async SQLAlchemy ORM
- Redis 7 for caching, pub/sub, and job queue (ARQ)
- Alembic for database migrations

**Frontend Architecture:**
- React 18 with CopilotKit v1.50 integration
- Tailwind CSS with shadcn/ui components
- Real-time WebSocket integration
- Firebase Authentication

**Agent Architecture:**
- Google ADK as agent framework
- Custom Team Builder for dynamic composition
- Perceive-Reason-Act pattern
- Agent Registry for capability-based lookup
- Harvester Framework for research teams

**Code Organization:**
```
imago.eco/
├── ui/backend/           # FastAPI app, routers, managers
├── ui/frontend-react/    # React + CopilotKit
├── core/                 # Registry, models, teams
├── integrations/         # Discord, Instagram, Orshot, Shopify
├── teams/                # Agent team definitions
├── library/              # Framework patterns
└── config/               # DAWO brand profile, compliance rules
```

### Starter Template Decision

**Decision:** No new starter template required.

**Rationale:**
1. IMAGO.ECO platform is 100% complete for DAWO deployment
2. All P1 and P2 infrastructure gaps resolved
3. Platform Test Team demonstrates working agent patterns
4. Team Builder, Harvester Framework, and Agent Registry established
5. External integrations (Instagram, Discord, Orshot, Shopify) configured

**DAWO Implementation Approach:**
Create agent teams in `teams/dawo/` directory following the Platform Test Team pattern (`teams/platform_test/team_spec.py`).

**Note:** First implementation story should be creating the DAWO team directory structure and registering initial agents.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. Agent Team Structure - Capability-based organization
2. Shared Agent Strategy - Registry-based with capability tags
3. LLM Tier Assignment - Task-type mapping with user override

**Important Decisions (Shape Architecture):**
4. Approval Routing - Source-based priority
5. Error Handling - Retry + graceful degradation hybrid
6. Progressive Automation - Manual toggle per content type

### Agent Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Team Structure** | Capability-Based | Reusable across any client: `scanners/`, `generators/`, `validators/`, `orchestrators/` |
| **Shared Agents** | Registry-Based | Leverage existing AgentRegistry; teams request by capability, Team Builder resolves |
| **LLM Tiers** | Task-Type Mapping | Default by task (scan→haiku, generate→sonnet, strategize→opus) with per-agent override in settings |

### Workflow Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Approval Priority** | Source-Based | Predictable ordering: trending(1) → scheduled(2) → evergreen(3) → research(4) |
| **Error Handling** | Retry + Degrade | Auto-retry with exponential backoff; if exhausted, mark incomplete and continue |
| **Auto-Publish Trust** | Manual Toggle | User enables per content type when confident; system shows approval stats to inform decision |

### Implementation Sequence

1. Create capability-based team directory structure
2. Register shared agents (EU Compliance, Brand Voice) in AgentRegistry
3. Implement LLM tier configuration with task-type defaults
4. Configure approval queue with source-based priority
5. Add retry/degradation middleware for external integrations
6. Build auto-publish toggle UI with approval statistics

### Cross-Component Dependencies

- **AgentRegistry** ← All teams depend on for shared agent resolution
- **LLM Tier Config** ← All agents depend on for model selection
- **Approval Manager** ← All content-generating teams feed into
- **Retry Middleware** ← All external integration calls route through

## Implementation Patterns & Consistency Rules

### Inherited Platform Patterns

| Category | Pattern | Example |
|----------|---------|---------|
| Python Naming | snake_case | `eu_compliance_checker.py` |
| Database Tables | snake_case, plural | `approval_items` |
| API Endpoints | snake_case, plural | `/api/agents` |
| JSON Fields | snake_case | `{"team_id": "..."}` |
| Agent Classes | PascalCase | `class EUComplianceChecker` |
| Config Files | snake_case JSON | `dawo_brand_profile.json` |

### DAWO Agent Patterns

| Pattern | Decision | Example |
|---------|----------|---------|
| **Agent Structure** | Package per agent (complex), single file (simple) | `validators/eu_compliance/agent.py` |
| **Registration** | Explicit `team_spec.py` | Platform Test Team pattern |
| **Config Loading** | Dependency Injection | Team Builder injects at composition |

### Agent Package Structure

```
teams/dawo/
├── scanners/
│   └── reddit/
│       ├── __init__.py
│       ├── agent.py
│       ├── prompts.py
│       └── tools.py
├── generators/
│   └── instagram_post/
│       └── ...
├── validators/
│   ├── eu_compliance/
│   │   └── ...
│   └── brand_voice/
│       └── ...
├── orchestrators/
│   └── content_team/
│       └── ...
└── team_spec.py          # All agent registrations
```

### Enforcement Guidelines

**All AI Agents MUST:**
- Follow platform snake_case conventions for Python/JSON
- Use package structure for agents with >2 files
- Register via team_spec.py, never self-register
- Accept config via constructor injection, never load directly
- Use AgentRegistry for shared agent resolution

**Anti-Patterns to Avoid:**
- ❌ `config = json.load(open("config/..."))` - use injection
- ❌ `@register_agent` decorators - use team_spec.py
- ❌ Hardcoded LLM tiers - use task-type mapping
- ❌ Direct external API calls - use retry middleware

## Project Structure & Boundaries

### Complete DAWO Team Structure

```
imago.eco/
├── teams/
│   └── dawo/
│       ├── __init__.py
│       ├── team_spec.py              # All agent registrations
│       │
│       ├── scanners/                  # Research & discovery agents
│       │   ├── __init__.py
│       │   ├── reddit/
│       │   │   ├── __init__.py
│       │   │   ├── agent.py           # RedditScanner
│       │   │   ├── prompts.py
│       │   │   └── tools.py           # Reddit API tools
│       │   ├── youtube/
│       │   ├── pubmed/
│       │   ├── instagram/
│       │   ├── news/
│       │   ├── b2b_leads/
│       │   └── competitor/
│       │
│       ├── generators/                # Content creation agents
│       │   ├── __init__.py
│       │   ├── instagram_post/
│       │   │   ├── __init__.py
│       │   │   ├── agent.py           # InstagramPostGenerator
│       │   │   ├── prompts.py
│       │   │   └── tools.py           # Orshot integration
│       │   ├── instagram_story/
│       │   ├── instagram_reel/
│       │   └── outreach_draft/
│       │
│       ├── validators/                # Compliance & quality agents
│       │   ├── __init__.py
│       │   ├── eu_compliance/
│       │   │   ├── __init__.py
│       │   │   ├── agent.py           # EUComplianceChecker
│       │   │   ├── prompts.py
│       │   │   └── rules.py           # Loads from config/
│       │   └── brand_voice/
│       │       ├── __init__.py
│       │       ├── agent.py           # BrandVoiceValidator
│       │       ├── prompts.py
│       │       └── profile.py         # Loads from config/
│       │
│       └── orchestrators/             # Team coordinators
│           ├── __init__.py
│           ├── research_team/
│           │   ├── __init__.py
│           │   ├── agent.py           # ResearchTeamOrchestrator
│           │   └── workflows.py       # Harvester patterns
│           ├── content_team/
│           ├── sales_team/
│           └── cleanmarket_team/
│
├── config/
│   ├── dawo_brand_profile.json       # Brand voice config (exists)
│   ├── dawo_compliance_rules.json    # EU rules (exists)
│   └── dawo_llm_tiers.json           # LLM tier overrides
│
└── tests/
    └── teams/
        └── dawo/
            ├── test_scanners/
            ├── test_generators/
            ├── test_validators/
            └── test_orchestrators/
```

### Architectural Boundaries

**Agent → Platform Integration:**

| Agent Type | Integrates With | Via |
|------------|-----------------|-----|
| All agents | AgentRegistry | Registration at startup |
| Generators | Approval Manager | `submit_for_approval()` |
| Validators | Shared across teams | Registry capability lookup |
| Orchestrators | Team Builder | Dynamic composition |
| Scanners | External APIs | Retry middleware |

**External Integration Points:**

| Integration | Location | Used By |
|-------------|----------|---------|
| Instagram Graph API | `integrations/instagram/` | Content publishing, research |
| Discord Webhooks | `integrations/discord/` | Notifications |
| Orshot API | `integrations/orshot/` | Graphics generation |
| Shopify MCP | `integrations/shopify/` | Product data |
| Reddit API | `scanners/reddit/tools.py` | Research |
| YouTube API | `scanners/youtube/tools.py` | Research |
| PubMed API | `scanners/pubmed/tools.py` | Research |

### Data Flow

```
[External Sources] → [Scanners] → [Research DB]
                                       ↓
                              [Orchestrators] → [Team Builder]
                                       ↓
                              [Generators] → [Validators]
                                       ↓
                              [Approval Manager] → [Human Review]
                                       ↓
                              [Scheduler] → [Publishers]
                                       ↓
                              [Instagram/Discord]
```

### Cross-Cutting Concerns Location

| Concern | Primary Location | Usage |
|---------|------------------|-------|
| EU Compliance | `validators/eu_compliance/` | Injected by Team Builder |
| Brand Voice | `validators/brand_voice/` | Injected by Team Builder |
| LLM Tier Config | `config/dawo_llm_tiers.json` | Read by Team Builder |
| Retry Logic | `library/middleware/retry.py` | Wraps all external calls |
| Logging | `core/logging/` | Unified activity log |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All 6 core architectural decisions work together seamlessly. Capability-based structure integrates naturally with Registry-based shared agents. Task-type LLM tiers complement source-based approval priority.

**Pattern Consistency:** All patterns follow IMAGO.ECO platform conventions (snake_case, explicit registration). No conflicts between inherited and DAWO-specific patterns.

**Structure Alignment:** Project structure directly supports all decisions - capability folders enable Registry lookups, orchestrators support Team Builder composition.

### Requirements Coverage ✅

**Functional Requirements:** All 55 FRs across 5 departments have architectural support:
- Research (6 FRs) → scanners/ + Harvester Framework
- Content (12 FRs) → generators/ + validators/
- Sales (6 FRs) → scanners/b2b + generators/outreach
- CleanMarket (4 FRs) → scanners/competitor + validators/
- Platform (27 FRs) → Existing IMAGO.ECO infrastructure

**Non-Functional Requirements:**
- EU Compliance: Dedicated validator with config-driven rules
- Cost Optimization: Task-type tier mapping with user override
- Single Operator: Source-based priority queue
- Progressive Trust: Manual auto-publish toggle
- Reliability: Retry + graceful degradation hybrid

### Implementation Readiness ✅

**Decision Completeness:** All critical decisions documented with clear rationale.

**Structure Completeness:** Full directory tree with file-level mappings to requirements.

**Pattern Completeness:** Naming, registration, and configuration patterns fully specified with examples and anti-patterns.

### Architecture Completeness Checklist

- [x] Project context analyzed (55 FRs, 5 departments, brownfield)
- [x] Technical constraints identified (IMAGO.ECO platform patterns)
- [x] Core decisions documented (6 decisions with rationale)
- [x] Implementation patterns defined (3 DAWO-specific patterns)
- [x] Project structure mapped (capability-based + integrations)
- [x] Requirements coverage verified (100% FR coverage)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Leverages proven IMAGO.ECO patterns (Platform Test Team, Harvester)
- Clear capability-based organization reusable for future clients
- Explicit anti-patterns prevent common AI agent conflicts
- EU compliance as first-class concern throughout

**First Implementation Priority:**
Create `teams/dawo/` directory structure and `team_spec.py` with EU Compliance and Brand Voice validators registered.

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2026-02-05
**Document Location:** `_bmad-output/planning-artifacts/architecture.md`

### Final Architecture Deliverables

**Complete Architecture Document**
- 6 core architectural decisions with rationale
- 3 DAWO-specific implementation patterns
- Complete project structure with file mappings
- 100% FR coverage verified (55/55)

**Implementation Ready Foundation**
- Capability-based team structure (scanners, generators, validators, orchestrators)
- Registry-based shared agents with dependency injection
- Task-type LLM tier mapping with user override
- Source-based approval priority queue
- Retry + graceful degradation error handling

### Implementation Handoff

**For AI Agents:**
This architecture document is your complete guide for implementing DAWO.ECO on the IMAGO.ECO platform. Follow all decisions, patterns, and structures exactly as documented.

**Development Sequence:**
1. Create `teams/dawo/` directory structure
2. Implement EU Compliance and Brand Voice validators
3. Register agents via `team_spec.py`
4. Build scanners following Harvester Framework pattern
5. Create generators with Orshot integration
6. Connect orchestrators to Team Builder

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Create Epics & Stories using the architectural decisions documented herein.
