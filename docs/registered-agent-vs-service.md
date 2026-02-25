# RegisteredAgent vs RegisteredService Guide

**Created:** 2026-02-19
**Context:** Epic 6 retro action item — confusion in Story 6-6 (used RegisteredService for LLM component)

---

## Quick Decision Rule

| Question | Answer | Use |
|----------|--------|-----|
| Does this component need an LLM tier? | Yes | `RegisteredAgent` |
| Is it pure Python with no LLM calls? | Yes | `RegisteredService` |

---

## RegisteredAgent

**When to use:** The component orchestrates LLM calls or needs an LLM tier assigned.

```python
RegisteredAgent(
    name="health_claim_extraction_engine",
    agent_class=HealthClaimExtractionEngine,
    capabilities=["competitor_monitoring", "claim_extraction"],
    tier=TIER_GENERATE,  # LLM tier: "scan", "generate", or "strategize"
)
```

**Key properties:**
- Has a `tier` field (`"scan"`, `"generate"`, `"strategize"`)
- Team Builder uses `LLMTierResolver` to map tier → actual model ID
- The component itself (or its sub-components) makes LLM API calls

**Examples:**
| Agent | Tier | Why Agent? |
|-------|------|-----------|
| `EUComplianceChecker` | generate | LLM judgment for compliance checking |
| `CaptionGenerator` | generate | LLM content creation |
| `RedditScanner` | scan | LLM for content categorization |
| `HealthClaimExtractionEngine` | generate | LLM classification pipeline |
| `ViolationDetector` | generate | LLM classification + cross-reference |
| `EvidenceCollector` | scan | No LLM — but orchestrates capture pipeline |

**Edge case — `EvidenceCollector`:**
Registered as `RegisteredAgent` with `tier=TIER_SCAN` even though it doesn't make LLM calls. This is because it orchestrates a multi-step pipeline (screenshot → hash → store) and fits the "agent" pattern of autonomous task execution. If it were just a single-step service, it would be `RegisteredService`.

---

## RegisteredService

**When to use:** The component is a pure Python class with no LLM dependency.

```python
RegisteredService(
    name="health_claims_repository",
    service_class=HealthClaimsRepository,
    capabilities=["regulatory_storage"],
    requires_session=True,  # If True, Team Builder injects AsyncSession
)
```

**Key properties:**
- No `tier` field — no LLM involvement
- Has `requires_session` flag for database services
- Team Builder injects dependencies (sessions, configs, other services)

**Examples:**
| Service | requires_session | Why Service? |
|---------|-----------------|-------------|
| `HealthClaimsRepository` | True | Database CRUD, no LLM |
| `RegisterParser` | False | Stateless data parsing |
| `GmailClient` | False | API client wrapper |
| `ClaimPatternMatcher` | False | Regex-based, no LLM |
| `CompetitorScanPipeline` | True | Orchestrates non-LLM pipeline |

---

## Common Mistakes

### Mistake: Using RegisteredService for LLM component
**Story 6-6** initially registered `HealthClaimExtractionEngine` as `RegisteredService`. This was wrong because the engine orchestrates `ClaimLLMClassifier` which makes LLM calls.

**Rule:** If ANY sub-component in the pipeline uses an LLM, the orchestrating component should be `RegisteredAgent`.

### Mistake: Using RegisteredAgent for pure data service
A repository or parser should never be `RegisteredAgent`. These are data-layer components with no AI behavior.

---

## Decision Flowchart

```
Does this component make LLM calls directly?
├── Yes → RegisteredAgent
└── No
    └── Does it orchestrate other components that make LLM calls?
        ├── Yes → RegisteredAgent
        └── No
            └── Is it a multi-step pipeline orchestrator?
                ├── Yes (and autonomous) → RegisteredAgent (tier=scan)
                └── No → RegisteredService
```

---

## Registration Locations

Both are defined in `teams/dawo/team_spec.py`:
- `AGENTS: List[RegisteredAgent]` — all agents
- `SERVICES: list[RegisteredService]` — all services

---

*Created: 2026-02-19 — Epic 6 Retrospective Action Item #4*
