# IMAGO.ECO Platform Gaps & Issues

**Purpose:** Track platform gaps and issues discovered during DAWO.ECO development.
**For:** IMAGO.ECO Claude Code sessions to read and address.
**Location:** `c:\Users\evend\Desktop\IMAGO.ECO\imago.eco`

---

## How to Use This Document

When working on IMAGO.ECO, reference this document to see what functionality gaps have been identified through real-world usage with the DAWO project. Each item includes:
- **Gap ID** for tracking
- **Priority** (P1 = critical, P2 = important, P3 = nice-to-have)
- **Status** (Resolved / Partial / Not Started)
- **Description** of what's missing or broken
- **Context** from DAWO usage
- **IMAGO Files** - where the implementation exists (for resolved items)

---

## Codebase Analysis Summary (2026-02-05)

Full exploration of `C:\Users\evend\Desktop\IMAGO.ECO\imago.eco` reveals:

| Component | Status | Details |
|-----------|--------|---------|
| **Backend** | FastAPI + async SQLAlchemy | 26+ routers, 100+ endpoints |
| **Frontend** | React 18 + CopilotKit v1.50 | Tailwind, shadcn/ui, recharts |
| **Database** | PostgreSQL 16 + Redis 7 | 16 tables, Alembic migrations |
| **Agent System** | Google ADK + team builder | Perceive-Reason-Act pattern |
| **Teams Deployed** | Platform Test Team only | Echo, Approval, Analytics, Orchestrator agents |

---

## Platform Gaps

### GAP-001: Human-in-the-Loop Approval Workflow UI
**Priority:** P1 - Critical for DAWO MVP
**Status:** RESOLVED

**What Exists:**
- `ui/backend/managers/approval_manager.py` - Full CRUD with batch operations
- `ui/backend/routers/approvals.py` - REST endpoints for approval queue
- `core/models/approval.py` - Approval model with compliance fields:
  - `compliance_status`, `compliance_violations`, `compliance_analyzed_at`
- Frontend approval components in `ui/frontend-react/src/components/approvals/`

**Features Built:**
- List view of pending approvals with filtering
- Approve/reject/edit actions
- Batch approval operations
- Compliance status indicators
- Priority handling

**DAWO Action:** Configure approval queue for content types (Instagram posts, B2B outreach drafts)

---

### GAP-002: Discord Notification Integration
**Priority:** P2 - Important
**Status:** RESOLVED

**What Exists:**
- `integrations/discord/` - Full Discord webhook client with rate limiting
- `ui/backend/services/discord_service.py` - Service layer for notifications
- `ui/backend/routers/discord.py` - REST endpoints at `/api/discord`

**Features Built:**
- Webhook URL configuration per user/project
- Event-to-Discord message formatter (approval needed, errors, completions)
- Rate limiting (respects Discord's 30 msg/min limit)
- Rich embeds with colors and fields

**DAWO Action:** Configure Discord webhook URL in project settings

---

### GAP-003: MCP Tool Integration (Shopify)
**Priority:** P2 - Important
**Status:** RESOLVED

**What Exists:**
- `integrations/mcp_client/client.py` - MCP server client with Shopify tools
- `integrations/mcp_catalog.yaml` - MCP server catalog including Shopify
- Mock Shopify tools added for testing

**Features Built:**
- MCP framework with tool registration
- Shopify product data retrieval tools
- Integration with agent system

**DAWO Action:** Connect to real Shopify MCP server with store credentials

---

### GAP-004: Team Configuration UI
**Priority:** P2 - Important
**Status:** RESOLVED

**What Exists:**
- `ui/backend/schemas/agent_team.py` - TopicConfig, ComplianceRulesConfig, OutputFormatConfig, TeamConfig, TeamConfigUpdate schemas
- `ui/backend/routers/agent_teams.py` - Config endpoints:
  - `GET /api/agent-teams/{id}/config`
  - `PATCH /api/agent-teams/{id}/config`
  - `PUT /api/agent-teams/{id}/config/topics`
  - `PUT /api/agent-teams/{id}/config/compliance`
  - `PUT /api/agent-teams/{id}/config/output-format`
- `ui/frontend-react/src/services/apiService.js` - API methods for config management
- `ui/frontend-react/src/components/teams/TeamConfigPanel.jsx` - Collapsible config UI
- `ui/frontend-react/src/components/teams/AgentTeamDetailPage.jsx` - Integrated TeamConfigPanel

**Features Built:**
- Topic configuration editing (subreddits, keywords, themes)
- Compliance rule assignment to teams
- Output format/template configuration
- Platform-specific settings

**DAWO Action:** Configure DAWO teams with mushroom topics, EU compliance rules, brand voice

---

### GAP-005: Content Scheduling System
**Priority:** P1 - Critical for MVP
**Status:** RESOLVED

**What Exists:**
- `ui/backend/managers/schedule_manager.py` - Full scheduling CRUD
- `ui/backend/routers/schedule.py` - REST endpoints
- `core/models/schedule.py` - ScheduledPost model with fields:
  - `scheduled_time`, `status`, `published_at`, `retry_count`
  - `instagram_media_id` for tracking published posts
- ARQ background jobs for scheduled publishing
- Calendar view in frontend

**Features Built:**
- Store approved content with scheduled publish times
- Background scheduler triggers publishing
- Retry logic for failed posts
- Status tracking (scheduled, publishing, published, failed)

**DAWO Action:** Ready to use - connect to Instagram publisher

---

### GAP-006: Instagram Graph API Integration
**Priority:** P1 - Critical for MVP
**Status:** RESOLVED

**What Exists:**
- `integrations/instagram/auth.py` - OAuth 2.0 flow
- `integrations/instagram/client.py` - Instagram Graph API client
- `ui/backend/routers/instagram.py` - REST endpoints
- `ui/backend/managers/instagram_connection_manager.py` - Connection management
- `core/models/instagram.py` - InstagramConnection model with token management

**Features Built:**
- Facebook Business account OAuth connection
- Instagram Business/Creator account linking
- Media container creation + async publishing
- Rate limit tracking from `X-App-Usage` header
- Token refresh handling

**DAWO Action:** Ready to use - configure Facebook App credentials in `.env`

---

### GAP-007: Performance Tracking Database
**Priority:** P1 - Critical for MVP
**Status:** RESOLVED

**What Exists:**
- `core/models/schedule.py` - PostMetrics model with:
  - `likes`, `comments`, `shares`, `views`
  - `reach`, `impressions`, `saves`
  - `agent_team_id` for attribution
- `ui/backend/routers/metrics.py` - Metrics endpoints
- Dashboard charts in `ui/frontend-react/src/components/metrics/`

**Enhancement opportunities for DAWO:**
- UTM parameter tracking (can add to ScheduledPost)
- Sales attribution (Shopify order linking)
- Post-publish quality scoring

**DAWO Action:** Core metrics ready. Add UTM/sales attribution as enhancement.

---

### GAP-008: Asset Database
**Priority:** P2 - Important
**Status:** RESOLVED

**What Exists:**
- `core/models/asset.py` - Asset model with quality tracking, Orshot integration
- `ui/backend/alembic/versions/20260205_000001_add_assets_table.py` - Migration
- `ui/backend/schemas/asset.py` - Pydantic schemas
- `ui/backend/managers/asset_manager.py` - Business logic
- `ui/backend/routers/assets.py` - REST endpoints at `/api/assets`

**Features Built:**
- Image/video storage with metadata
- Generation prompt tracking
- Quality score tracking
- Orshot template ID linking
- Usage count tracking
- Search/filter capabilities

**DAWO Action:** Ready for storing generated mushroom graphics

---

### GAP-009: Brand Identity Database
**Priority:** P2 - Important
**Status:** RESOLVED

**What Exists:**
- `core/models/brand_profile.py` - Brand profile model with voice guidelines
- `ui/backend/alembic/versions/20260205_000002_add_brand_profiles_table.py` - Migration
- `ui/backend/schemas/brand_profile.py` - Schemas with voice checking
- `ui/backend/managers/brand_profile_manager.py` - Business logic
- `ui/backend/routers/brand_profiles.py` - REST endpoints at `/api/brand-profiles`

**Features Built:**
- Voice guidelines storage (tone, style, examples)
- Visual identity (hex colors, font names, logo assets as JSON)
- Platform-specific variations
- Words to use/avoid lists
- Brand voice compliance checking

**DAWO Action:** Configure DAWO brand profile with mushroom/wellness voice guidelines

---

### GAP-010: Orshot API Integration
**Priority:** P2 - Important
**Status:** RESOLVED

**What Exists:**
- `integrations/orshot/` - Full API client for branded graphics
- `ui/backend/services/orshot_service.py` - Service layer
- `ui/backend/routers/orshot.py` - REST endpoints at `/api/orshot`

**Features Built:**
- Direct Canva template import
- Dynamic image generation (fill text, colors, images)
- Video generation support
- Batch generation via REST API
- Dynamic URL generation
- Template management

**DAWO Action:** Import Canva templates, configure Orshot API key in `.env`

---

## Feature Requests

### FR-001: Mobile App / PWA
**Priority:** P3 - Future
**Status:** Not Started
**Description:** Mobile-friendly access to approval workflows for on-the-go review.

**Context from DAWO:**
Even (DAWO operator) wants to approve content from mobile.

---

## Remaining Work: DAWO Agent Teams

### GAP-011: DAWO-Specific Agent Teams
**Priority:** P1 - Critical for DAWO MVP
**Status:** NOT STARTED

**Description:** Deploy DAWO agent teams using existing team builder infrastructure:

**Required Teams:**
1. **Research Teams** (5 sources)
   - Reddit Research Team (extends existing REDIS pattern)
   - YouTube Research Team
   - PubMed Research Team
   - Instagram Research Team
   - News Research Team

2. **Content Teams**
   - Instagram Content Team (caption + image + hashtags)
   - LinkedIn Content Team (future)

3. **Compliance Team**
   - EU Health Claims Checker (shared agent)
   - Brand Voice Validator (shared agent)

4. **Sales Team**
   - B2B Lead Research Team
   - Outreach Draft Team

5. **CleanMarket Team**
   - Competitor Compliance Monitor

**What Exists:**
- `core/teams/team_builder.py` - Dynamic team composition
- `library/framework_library/teams/harvester_framework.yaml` - Research pattern
- `teams/platform_test/` - Example team implementation
- Agent registry system in `core/registry/`

**DAWO Action:** Create team definitions in `teams/dawo/` following platform_test pattern.

---

## Bugs

*(None identified yet)*

---

## Summary: All Infrastructure Complete

### All P1 & P2 Gaps Resolved
| Gap | Feature | Status | Key Files |
|-----|---------|--------|-----------|
| GAP-001 | Approval Workflow UI | **RESOLVED** | `managers/approval_manager.py` |
| GAP-002 | Discord Webhooks | **RESOLVED** | `integrations/discord/`, `routers/discord.py` |
| GAP-003 | Shopify MCP | **RESOLVED** | `integrations/mcp_catalog.yaml` |
| GAP-004 | Team Config UI | **RESOLVED** | `components/teams/TeamConfigPanel.jsx` |
| GAP-005 | Content Scheduling | **RESOLVED** | `managers/schedule_manager.py` |
| GAP-006 | Instagram Publishing | **RESOLVED** | `integrations/instagram/` |
| GAP-007 | Performance Tracking | **RESOLVED** | `core/models/schedule.py` |
| GAP-008 | Asset Database | **RESOLVED** | `core/models/asset.py`, `routers/assets.py` |
| GAP-009 | Brand Identity DB | **RESOLVED** | `core/models/brand_profile.py`, `routers/brand_profiles.py` |
| GAP-010 | Orshot API | **RESOLVED** | `integrations/orshot/`, `routers/orshot.py` |

### Only Remaining Work
| Gap | Priority | Description |
|-----|----------|-------------|
| **GAP-011** | P1 | DAWO Agent Teams - Create and deploy teams in `teams/dawo/` |

---

## DAWO Configuration Checklist

All infrastructure complete, configuration done:

- [x] Add Facebook App credentials to `.env` (Instagram publishing)
- [x] Configure Discord webhook URL (notifications)
- [x] Add Orshot API key to `.env` (branded graphics)
- [ ] Import Canva templates to Orshot *(TODO - design templates first)*
- [x] Create DAWO brand profile → `config/dawo_brand_profile.json`
- [x] Configure EU Health Claims compliance rules → `config/dawo_compliance_rules.json`
- [ ] Create DAWO agent teams in `teams/dawo/` *(GAP-011 - main remaining work)*
- [x] Connect Shopify MCP server with store credentials

---

## Configuration Files Created

| File | Purpose |
|------|---------|
| `ui/backend/.env` | API credentials (Instagram, Discord, Orshot, Shopify) |
| `config/dawo_brand_profile.json` | Brand voice, colors, fonts, words to use/avoid |
| `config/dawo_compliance_rules.json` | EU Health Claims prohibited/approved patterns |

---

**Last Updated:** 2026-02-05
**Updated By:** DAWO configuration session
