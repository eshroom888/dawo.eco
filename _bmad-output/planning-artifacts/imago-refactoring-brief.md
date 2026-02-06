# IMAGO.ECO Refactoring Brief

**Purpose:** Context document for BMAD brownfield session to refactor IMAGO.ECO
**Use with:** `/bmad:bmm:workflows:document-project` or direct brownfield analysis
**Reference:** Use alongside `imago-platform-gaps.md` in the same folder
**Last Updated:** 2026-02-05 (all P2 infrastructure complete)

---

## Executive Summary

IMAGO.ECO platform infrastructure is **100% complete for DAWO deployment**. All P1 and P2 gaps have been resolved. The only remaining work is **building and deploying DAWO-specific agent teams**.

### Infrastructure Status: ALL COMPLETE

| Gap | Feature | Status |
|-----|---------|--------|
| GAP-001 | Approval Workflow UI | **RESOLVED** |
| GAP-002 | Discord Webhooks | **RESOLVED** |
| GAP-003 | Shopify MCP | **RESOLVED** |
| GAP-004 | Team Config UI | **RESOLVED** |
| GAP-005 | Content Scheduling | **RESOLVED** |
| GAP-006 | Instagram Publishing | **RESOLVED** |
| GAP-007 | Performance Tracking | **RESOLVED** |
| GAP-008 | Asset Database | **RESOLVED** |
| GAP-009 | Brand Identity DB | **RESOLVED** |
| GAP-010 | Orshot API | **RESOLVED** |

**Only remaining: GAP-011 - DAWO Agent Teams**

---

## What is IMAGO.ECO?

IMAGO.ECO is a platform for deploying and managing AI agent teams.

### Architecture (Confirmed)
```
┌─────────────────────────────────────────┐
│     React Frontend (CopilotKit v1.50)   │
│  • Tailwind CSS, shadcn/ui components   │
│  • Real-time WebSocket integration      │
│  • Firebase Authentication              │
└─────────────────────┬───────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │  REST API + WebSocket     │
        │      FastAPI (async)      │
        └─────────────┬─────────────┘
                      │
┌─────────────────────┴───────────────────┐
│     PostgreSQL 16 + Redis 7             │
│  • Async SQLAlchemy ORM                 │
│  • Cache, pub/sub, job queue (ARQ)      │
│  • Alembic migrations                   │
└─────────────────────────────────────────┘
```

### Key Stats (Updated)
- **26+ API routers** with 100+ endpoints
- **16 database tables** (including new assets, brand_profiles)
- **Agent system**: Google ADK + custom team builder with Perceive-Reason-Act pattern
- **Platform Test Team deployed** - Echo, Approval, Analytics, Orchestrator agents

### Location
`C:\Users\evend\Desktop\IMAGO.ECO\imago.eco`

---

## What is DAWO.ECO?

DAWO.ECO is the first customer/deployment of IMAGO.ECO:

- **Business:** One-person organic mushroom supplement company (EU-based)
- **Goal:** AI agents for content creation, B2B sales, compliance monitoring
- **Constraint:** EU Health Claims Regulation (EC 1924/2006) - zero approved claims for functional mushrooms
- **Operator:** Single supervisor (Even/eshroom) managing all agent teams
- **PRD Location:** `c:\Users\evend\Desktop\DAWO.ECO\_bmad-output\planning-artifacts\prd.md`

---

## Only Remaining Work: GAP-011 DAWO Agent Teams

### Required Teams Structure

```
teams/dawo/
├── research/
│   ├── reddit_team/         # Extends REDIS pattern
│   ├── youtube_team/
│   ├── pubmed_team/
│   ├── instagram_team/
│   └── news_team/
├── content/
│   └── instagram_team/      # Caption + image + hashtags
├── compliance/
│   ├── eu_health_claims/    # Shared checker agent
│   └── brand_validator/     # Shared brand voice agent
├── sales/
│   ├── lead_research/       # B2B lead finder
│   └── outreach_draft/      # Personalized email drafts
└── cleanmarket/
    └── competitor_monitor/  # Compliance violation detection
```

### Existing Patterns to Follow

1. **Platform Test Team** (`teams/platform_test/`)
   - `team_spec.py` - Team registration
   - Individual agent files with capabilities
   - Orchestrator pattern for multi-agent workflows

2. **Team Builder** (`core/teams/team_builder.py`)
   - Dynamic team composition based on capabilities
   - Performance-based agent selection
   - LLM tier requirements (Haiku/Sonnet/Opus)

3. **Harvester Framework** (`library/framework_library/teams/harvester_framework.yaml`)
   - Research team pattern: scanner → harvester → transformer → validator → publisher

4. **Agent Registry** (`core/registry/agent_registry.py`)
   - In-memory agent catalog
   - Capability-based lookup
   - Status and deployment tracking

---

## New Infrastructure Available

### GAP-008: Asset Database
- `core/models/asset.py` - Asset model
- `ui/backend/routers/assets.py` - REST endpoints at `/api/assets`
- Use for storing generated mushroom graphics

### GAP-009: Brand Identity Database
- `core/models/brand_profile.py` - Brand profile model
- `ui/backend/routers/brand_profiles.py` - REST endpoints at `/api/brand-profiles`
- Use for DAWO voice guidelines and visual identity

### GAP-002: Discord Webhooks
- `integrations/discord/` - Full webhook client
- `ui/backend/routers/discord.py` - REST endpoints at `/api/discord`
- Use for approval notifications

### GAP-010: Orshot API
- `integrations/orshot/` - Full API client
- `ui/backend/routers/orshot.py` - REST endpoints at `/api/orshot`
- Use for branded graphics generation

### GAP-004: Team Config UI
- `ui/frontend-react/src/components/teams/TeamConfigPanel.jsx`
- Topic, compliance, and output format configuration
- Use for configuring DAWO team settings

---

## Technical Context

### LLM Strategy (from DAWO PRD)
| Model | Use Case |
|-------|----------|
| **Claude Haiku** | High-volume scanning (research teams) |
| **Claude Sonnet** | Content writing, compliance checking |
| **Claude Opus 4.5** | Strategic decisions, brand architecture |

### External Integrations (All Ready)
| Integration | Status | Notes |
|-------------|--------|-------|
| Instagram Graph API | **Ready** | Configure FB App credentials |
| Discord Webhooks | **Ready** | Configure webhook URL |
| Orshot API | **Ready** | Configure API key |
| Shopify MCP | **Ready** | Connect MCP server |
| Asset Storage | **Ready** | `/api/assets` endpoints |
| Brand Profiles | **Ready** | `/api/brand-profiles` endpoints |

### Key DAWO Constraints
- **EU Health Claims:** Zero approved claims for functional mushrooms - content must educate without claiming benefits
- **Progressive Auto-Publish:** Start with "WOULD_AUTO_PUBLISH" simulation before real automation
- **Single Operator:** All workflows optimized for one-person review

---

## Implementation Plan

### Phase 1: Configuration (No Code)
1. Add Facebook App credentials to `.env`
2. Configure Discord webhook URL
3. Add Orshot API key to `.env`
4. Import Canva templates to Orshot
5. Create DAWO brand profile via `/api/brand-profiles`
6. Configure EU Health Claims compliance rules

### Phase 2: DAWO Agent Teams (Code)
1. Create `teams/dawo/` directory structure
2. Implement Reddit Research Team (extends REDIS)
3. Implement Instagram Content Team
4. Implement EU Compliance Checker (shared agent)
5. Wire teams to existing approval workflow

### Phase 3: Additional Teams
1. YouTube, PubMed, News Research Teams
2. B2B Lead Research & Outreach Teams
3. CleanMarket Competitor Monitor

---

## Key Files Reference

### Infrastructure (All Built)
| File | Purpose |
|------|---------|
| `ui/backend/main.py` | FastAPI app with 26+ routers |
| `core/teams/team_builder.py` | Dynamic team composition |
| `core/registry/agent_registry.py` | Agent catalog |
| `ui/backend/managers/approval_manager.py` | Approval queue |
| `integrations/instagram/client.py` | Instagram publishing |
| `integrations/discord/` | Discord notifications |
| `integrations/orshot/` | Branded graphics |
| `core/models/asset.py` | Asset storage |
| `core/models/brand_profile.py` | Brand identity |
| `ui/frontend-react/src/components/teams/TeamConfigPanel.jsx` | Team config UI |

### Need to Create
| File | Purpose |
|------|---------|
| `teams/dawo/` | All DAWO team definitions |

### DAWO Reference Docs
| File | Purpose |
|------|---------|
| `_bmad-output/planning-artifacts/prd.md` | Complete DAWO requirements (55 FRs) |
| `_bmad-output/planning-artifacts/imago-platform-gaps.md` | Gap tracking |
| `docs/bmad/project-brief.md` | Original DAWO project brief |

---

## DAWO Configuration Checklist

Configuration complete (2026-02-05):

- [x] Add Facebook App credentials to `.env` (Instagram publishing)
- [x] Configure Discord webhook URL (notifications)
- [x] Add Orshot API key to `.env` (branded graphics)
- [ ] Import Canva templates to Orshot *(TODO - design templates first)*
- [x] Create DAWO brand profile → `config/dawo_brand_profile.json`
- [x] Configure EU Health Claims compliance rules → `config/dawo_compliance_rules.json`
- [x] Connect Shopify MCP server with store credentials

**Ready to build agent teams.**

---

## Out of Scope

- Mobile app / PWA (P3 future feature)
- Multi-language content support
- Klaviyo email integration
- Google UCP integration
- Support Department agents
- LinkedIn/TikTok publishing (future platforms)

---

**Last Updated:** 2026-02-05
**Source:** P2 infrastructure completion session
