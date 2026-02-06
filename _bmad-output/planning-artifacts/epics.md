---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
status: 'complete'
completedAt: '2026-02-05'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
workflowType: 'epics-and-stories'
project_name: 'DAWO.ECO'
totalEpics: 7
totalStories: 51
frCoverage: '55/55 (100%)'
---

# DAWO.ECO - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for DAWO.ECO, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Research & Intelligence (FR1-FR8)**
- FR1: System can monitor Reddit for mushroom-related discussions and trending topics
- FR2: System can search YouTube for mushroom supplement content and extract key insights
- FR3: System can monitor Instagram hashtags and competitor accounts for trend detection
- FR4: System can aggregate industry news from configured sources
- FR5: System can query PubMed for scientific research on mushroom compounds
- FR6: System can validate research findings against EU Health Claims compliance
- FR7: System can store research items in a searchable Research Pool with metadata
- FR8: System can score research items for content potential and relevance

**Content Generation (FR9-FR16)**
- FR9: System can generate Instagram post captions in Norwegian using brand voice guidelines
- FR10: System can generate branded graphics via Orshot API (with Canva template import)
- FR11: System can generate AI images via Nano Banana (Gemini) for visual content
- FR12: System can combine research insights with product data to create content drafts
- FR13: System can apply EU Health Claims compliance checking to all generated content
- FR14: System can suggest compliant rewrites when content fails compliance
- FR15: System can score content quality including AI detectability risk
- FR16: System can tag content with "WOULD_AUTO_PUBLISH" status when score >=9 and compliance passes

**B2B Sales & Outreach (FR17-FR21)**
- FR17: System can research potential B2B retail partners using configured criteria
- FR18: System can extract business information from public sources for lead enrichment
- FR19: System can generate personalized B2B outreach drafts referencing lead-specific insights
- FR20: System can queue approved outreach emails for sending via Gmail API
- FR21: System can track B2B lead status through pipeline stages

**Compliance & Regulatory (FR22-FR28)**
- FR22: System can evaluate content against EU Health Claims Regulation (EC 1924/2006)
- FR23: System can classify language as prohibited, borderline, or permitted
- FR24: System can validate content against Novel Food product classifications
- FR25: System can monitor EU Health Claims Register for new approved claims
- FR26: System can monitor Novel Food Catalogue for status changes
- FR27: System can monitor Mattilsynet.no for Norwegian regulatory updates
- FR28: System can alert operator when new claims become available for DAWO products

**CleanMarket - Competitor Intelligence (FR29-FR34)**
- FR29: System can scan competitor Instagram accounts and websites for health claims
- FR30: System can extract and classify competitor health claims
- FR31: System can detect potential EU Health Claims violations in competitor content
- FR32: System can collect evidence (screenshots, timestamps, URLs) of violations
- FR33: System can store evidence in searchable database with metadata
- FR34: Operator can generate compliance violation reports on demand

**Approval & Publishing (FR35-FR41)**
- FR35: Operator can view pending content in approval queue with quality scores
- FR36: Operator can approve, reject, or edit content items
- FR37: Operator can batch approve multiple content items
- FR38: Operator can schedule approved content for future publication
- FR39: System can publish approved content to Instagram via Graph API at scheduled time
- FR40: System can send Discord notifications when approvals are needed
- FR41: System can send Discord notifications when scheduled posts are published

**Performance Tracking (FR42-FR46)**
- FR42: System can collect engagement metrics (likes, comments, shares, saves, reach) from Instagram
- FR43: System can track click-through rates via UTM parameters
- FR44: System can attribute Shopify sales to specific posts via UTM correlation
- FR45: System can calculate post-publish quality scores based on engagement
- FR46: System can feed performance data back to content scoring algorithms

**Asset & Brand Management (FR47-FR50)**
- FR47: System can store generated assets in Google Drive with organized folder structure
- FR48: System can retrieve product data from Shopify via MCP
- FR49: System can apply brand voice guidelines to all generated content
- FR50: System can track asset usage history and performance correlation

**System Administration (FR51-FR55)**
- FR51: Operator can configure agent execution schedules
- FR52: Operator can manually trigger specific teams or agents
- FR53: Operator can view agent execution logs and status
- FR54: System can sync content calendar to Google Calendar
- FR55: System can gracefully degrade when external APIs are unavailable

### NonFunctional Requirements

**Performance**
- NFR1: Approval queue load time < 3 seconds
- NFR2: Content generation < 60 seconds per post
- NFR3: Research scan < 5 minutes per source
- NFR4: Instagram publish latency < 30 seconds from trigger
- NFR5: Compliance check < 10 seconds per item

**Security**
- NFR6: API key storage encrypted at rest, never logged in plaintext
- NFR7: TLS 1.3 for all external API calls
- NFR8: Single operator with full access (MVP); RBAC ready for Growth
- NFR9: Secure token-based auth, 24-hour expiry
- NFR10: All approval actions logged with timestamp and user
- NFR11: GDPR compliance - B2B contact data erasable on request

**Reliability**
- NFR12: Scheduled publish success rate > 99%
- NFR13: Agent execution success rate > 95%
- NFR14: System availability 99% uptime
- NFR15: Daily data backups
- NFR16: Graceful degradation when APIs unavailable

**Integration**
- NFR17: API timeout max 30 seconds, then fail gracefully with retry queue
- NFR18: Respect all API rate limits, implement backoff
- NFR19: Document all API versions, alert on deprecation notices
- NFR20: Retry failed Discord notifications 3x with exponential backoff
- NFR21: Health checks for all critical APIs (Instagram, Gmail, Orshot)

**Compliance**
- NFR22: EU Health Claims accuracy 100% - no prohibited claims published
- NFR23: Full compliance audit trail with reasoning
- NFR24: AI-generated content disclosure per EU AI Act Article 50 (human approval = exemption)
- NFR25: Data retention - Research: 2 years, Performance: indefinite, B2B: until relationship ends
- NFR26: CleanMarket evidence immutable once collected

**Operational**
- NFR27: Discord alerts for failed publishes, compliance warnings, API errors
- NFR28: 30 days operational logs, 1 year audit logs
- NFR29: Recovery time objective (RTO) < 4 hours
- NFR30: Recovery point objective (RPO) < 24 hours
- NFR31: Monthly API spend tracking, alerts at 80% budget

### Additional Requirements

**From Architecture Document:**

- Brownfield extension of IMAGO.ECO platform - no new starter template required
- First story must create `teams/dawo/` directory structure and register initial agents
- Capability-based team organization: `scanners/`, `generators/`, `validators/`, `orchestrators/`
- Registry-based shared agents via AgentRegistry (EU Compliance, Brand Voice)
- LLM tier mapping: Haiku for scanning, Sonnet for generation, Opus for strategy
- Source-based approval priority: trending(1) -> scheduled(2) -> evergreen(3) -> research(4)
- Retry + graceful degradation hybrid for all external API calls
- Manual auto-publish toggle per content type with approval stats display
- Platform Test Team pattern - all agents register via `team_spec.py`
- Harvester Framework for research teams: scanner -> harvester -> transformer -> validator -> publisher
- Dependency injection for configuration - never load config directly
- Package structure for complex agents (>2 files), single file for simple agents
- All Python/JSON follows snake_case convention
- Anti-patterns to avoid: self-registration, hardcoded LLM tiers, direct external API calls

**Technical Infrastructure (from Architecture):**

- Python 3.11+ with async support
- FastAPI backend with async SQLAlchemy ORM
- PostgreSQL 16 + Redis 7 (ARQ job queue)
- React 18 frontend with CopilotKit v1.50
- Google ADK agent framework
- Team Builder for dynamic composition
- Agent Registry for capability-based lookup

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | Reddit monitoring for mushroom discussions |
| FR2 | Epic 2 | YouTube content search and insight extraction |
| FR3 | Epic 2 | Instagram hashtag and competitor monitoring |
| FR4 | Epic 2 | Industry news aggregation |
| FR5 | Epic 2 | PubMed scientific research queries |
| FR6 | Epic 2 | Research validation against EU compliance |
| FR7 | Epic 2 | Research Pool storage with metadata |
| FR8 | Epic 2 | Content potential scoring |
| FR9 | Epic 3 | Instagram caption generation in Norwegian |
| FR10 | Epic 3 | Orshot branded graphics generation |
| FR11 | Epic 3 | Nano Banana AI image generation |
| FR12 | Epic 3 | Research + product data fusion |
| FR13 | Epic 3 | EU Health Claims compliance checking |
| FR14 | Epic 3 | Compliant rewrite suggestions |
| FR15 | Epic 3 | Quality scoring with AI detectability |
| FR16 | Epic 3 | WOULD_AUTO_PUBLISH tagging |
| FR17 | Epic 5 | B2B retail partner research |
| FR18 | Epic 5 | Business info extraction/enrichment |
| FR19 | Epic 5 | Personalized outreach draft generation |
| FR20 | Epic 5 | Gmail API integration for sending |
| FR21 | Epic 5 | Lead pipeline status tracking |
| FR22 | Epic 1 | EU Health Claims Regulation evaluation |
| FR23 | Epic 1 | Language classification (prohibited/borderline/permitted) |
| FR24 | Epic 1 | Novel Food product classification validation |
| FR25 | Epic 6 | EU Health Claims Register monitoring |
| FR26 | Epic 6 | Novel Food Catalogue monitoring |
| FR27 | Epic 6 | Mattilsynet.no regulatory monitoring |
| FR28 | Epic 6 | New claims activation alerts |
| FR29 | Epic 6 | Competitor Instagram/website scanning |
| FR30 | Epic 6 | Competitor health claim extraction |
| FR31 | Epic 6 | EU violation detection |
| FR32 | Epic 6 | Evidence collection (screenshots, timestamps) |
| FR33 | Epic 6 | Searchable evidence database |
| FR34 | Epic 6 | On-demand violation reports |
| FR35 | Epic 4 | Approval queue with quality scores |
| FR36 | Epic 4 | Approve/reject/edit actions |
| FR37 | Epic 4 | Batch approval capability |
| FR38 | Epic 4 | Content scheduling interface |
| FR39 | Epic 4 | Instagram Graph API auto-publishing |
| FR40 | Epic 4 | Discord notifications for approvals needed |
| FR41 | Epic 4 | Discord notifications for published posts |
| FR42 | Epic 7 | Instagram engagement metrics collection |
| FR43 | Epic 7 | UTM click-through tracking |
| FR44 | Epic 7 | Shopify sales attribution |
| FR45 | Epic 7 | Post-publish quality scores |
| FR46 | Epic 7 | Performance feedback loop |
| FR47 | Epic 3 | Google Drive asset storage |
| FR48 | Epic 3 | Shopify MCP product data retrieval |
| FR49 | Epic 1 | Brand voice guidelines application |
| FR50 | Epic 3 | Asset usage history tracking |
| FR51 | Epic 7 | Agent schedule configuration |
| FR52 | Epic 7 | Manual team/agent triggers |
| FR53 | Epic 7 | Execution logs and status |
| FR54 | Epic 7 | Google Calendar sync |
| FR55 | Epic 7 | Graceful API degradation |

**Coverage Summary:** 55/55 FRs mapped (100%)

## Epic List

| Epic | Title | FRs | User Value |
|------|-------|-----|------------|
| 1 | Agent Foundation & Shared Validators | FR22-24, FR49 | Core agent infrastructure with compliance and brand protection |
| 2 | Research Intelligence Pipeline | FR1-8 | Content opportunities from 5 sources flow into Research Pool |
| 3 | Content Creation & Assets | FR9-16, FR47-48, FR50 | Instagram content with graphics queued for review |
| 4 | Approval & Auto-Publishing | FR35-41 | Review, approve, and auto-publish to Instagram |
| 5 | B2B Sales Pipeline | FR17-21 | Find partners and draft personalized outreach |
| 6 | CleanMarket & Regulatory Intelligence | FR25-34 | Monitor competitors and regulatory changes |
| 7 | Analytics & System Operations | FR42-46, FR51-55 | Track performance and manage agent execution |

---

## Epic 1: Agent Foundation & Shared Validators

**Goal:** Core agent infrastructure is operational with compliance and brand protection built-in

**User Value:** The system is ready to run AI agents with EU compliance checking and brand voice validation as foundational capabilities that all other teams can leverage.

**FRs covered:** FR22, FR23, FR24, FR49

### Story 1.1: DAWO Team Directory Structure

As a **developer**,
I want the DAWO agent team directory structure created with proper organization,
So that all future agents have a consistent location and registration pattern.

**Acceptance Criteria:**

**Given** the IMAGO.ECO platform codebase exists
**When** I create the DAWO team structure
**Then** the following directories exist:
- `teams/dawo/scanners/`
- `teams/dawo/generators/`
- `teams/dawo/validators/`
- `teams/dawo/orchestrators/`
**And** `teams/dawo/__init__.py` exports the team module
**And** `teams/dawo/team_spec.py` exists with empty agent registration list
**And** the structure follows Platform Test Team pattern from `teams/platform_test/`

---

### Story 1.2: EU Compliance Checker Validator

As an **operator**,
I want content automatically checked against EU Health Claims Regulation,
So that I never accidentally publish prohibited health claims.

**Acceptance Criteria:**

**Given** content text is submitted for compliance checking
**When** the EU Compliance Checker evaluates the content
**Then** each phrase is classified as one of: `PROHIBITED`, `BORDERLINE`, `PERMITTED`
**And** prohibited phrases include: "treats", "cures", "prevents", disease references
**And** borderline phrases include: "supports", "promotes", "contributes to"
**And** permitted phrases include: general wellness, lifestyle, study citations with links
**And** the checker returns overall status: `COMPLIANT`, `WARNING`, or `REJECTED`
**And** rejected content includes specific flagged phrases with explanations

**Given** a product name is included in content
**When** the checker validates Novel Food classification (FR24)
**Then** it verifies product is marketed according to its classification (food vs supplement)
**And** Chaga content is validated as supplement-only messaging

**Given** the validator is registered
**When** Team Builder requests a compliance capability
**Then** AgentRegistry returns the EU Compliance Checker instance
**And** the checker uses Sonnet model tier for accuracy

---

### Story 1.3: Brand Voice Validator

As an **operator**,
I want content checked against DAWO brand guidelines,
So that all published content maintains consistent voice and authenticity.

**Acceptance Criteria:**

**Given** content text is submitted for brand validation
**When** the Brand Voice Validator evaluates the content
**Then** it checks tone against DAWO profile: warm, educational, Nordic simplicity
**And** it flags AI-generic language that lacks human feel
**And** it verifies no medicinal terminology is used
**And** it returns validation status: `PASS`, `NEEDS_REVISION`, or `FAIL`
**And** failed content includes specific revision suggestions

**Given** the brand profile exists at `config/dawo_brand_profile.json`
**When** the validator initializes
**Then** it loads configuration via dependency injection (not direct file load)
**And** config includes: tone keywords, forbidden terms, style examples

**Given** the validator is registered
**When** Team Builder requests brand validation capability
**Then** AgentRegistry returns the Brand Voice Validator instance
**And** the validator uses Sonnet model tier for judgment quality

---

### Story 1.4: LLM Tier Configuration

As a **developer**,
I want LLM model selection configured by task type,
So that costs are optimized while maintaining quality where needed.

**Acceptance Criteria:**

**Given** the LLM tier configuration exists at `config/dawo_llm_tiers.json`
**When** an agent is instantiated
**Then** it receives its model tier based on task type mapping:
- `scan` tasks → Claude Haiku 4 (low cost, high volume)
- `generate` tasks → Claude Sonnet 4 (quality, creativity)
- `strategize` tasks → Claude Opus 4.5 (complex planning)
**And** individual agents can have per-agent overrides in config

**Given** Team Builder composes a team
**When** it injects configuration into agents
**Then** each agent receives appropriate model tier
**And** agents never hardcode model selection

**Given** config specifies an override for a specific agent
**When** that agent is instantiated
**Then** it uses the override model instead of task-type default

---

### Story 1.5: External API Retry Middleware

As an **operator**,
I want external API calls to retry automatically on failure,
So that temporary outages don't cause lost work or missed schedules.

**Acceptance Criteria:**

**Given** an external API call fails (Instagram, Discord, Orshot, Shopify)
**When** the retry middleware handles the failure
**Then** it retries with exponential backoff: 1s, 2s, 4s (3 attempts max)
**And** it respects API rate limits during retry
**And** it logs each retry attempt with error details

**Given** all retry attempts are exhausted
**When** the middleware reports failure
**Then** it marks the operation as `INCOMPLETE` (not failed)
**And** it queues the operation for later retry
**And** it allows the rest of the pipeline to continue (graceful degradation)
**And** it sends Discord alert for API errors (if Discord is available)

**Given** an API returns rate limit response (429)
**When** the middleware handles it
**Then** it waits for the specified retry-after duration
**And** it does not count this as a retry attempt

---

## Epic 2: Research Intelligence Pipeline

**Goal:** Fresh content opportunities from Reddit, YouTube, PubMed, Instagram, and industry news flow into the Research Pool daily

**User Value:** The operator has a continuously refreshed pool of validated, compliance-checked research insights to fuel content creation without manual research effort.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8

### Story 2.1: Research Pool Database & Storage

As an **operator**,
I want research items stored in a searchable database with metadata,
So that content teams can discover and use the best research for posts.

**Acceptance Criteria:**

**Given** a research item is ready for storage
**When** the research publisher saves it to the Research Pool
**Then** the following fields are stored:
- `id`: unique identifier
- `source`: reddit | youtube | instagram | news | pubmed
- `title`: headline or summary
- `content`: full text or transcript excerpt
- `url`: source link
- `tags`: topic/theme tags (e.g., #lions_mane, #cognition)
- `metadata`: source-specific data (author, subreddit, channel, DOI)
- `created_at`: timestamp of discovery
- `score`: content potential score (0-10)
- `compliance_status`: COMPLIANT | WARNING | REJECTED

**Given** a content team needs research
**When** they query the Research Pool
**Then** they can filter by: source, tags, score threshold, date range
**And** results are sorted by score descending by default
**And** queries complete in < 500ms for pools up to 10,000 items

---

### Story 2.2: Research Item Scoring Engine

As an **operator**,
I want research items scored for content potential,
So that the best opportunities surface to the top.

**Acceptance Criteria:**

**Given** a research item enters the pool
**When** the scoring engine evaluates it
**Then** it calculates a score (0-10) based on:
- Relevance to DAWO products (mushroom types, wellness themes)
- Recency (newer = higher, decay over 30 days)
- Source quality (peer-reviewed > social media)
- Engagement indicators (upvotes, views, citations)
- Compliance status (COMPLIANT gets +1, WARNING neutral, REJECTED = 0)

**Given** a PubMed study is found
**When** it's a peer-reviewed RCT with significant findings
**Then** it scores 8+ automatically

**Given** a Reddit post is found
**When** it has high engagement but unverified claims
**Then** it scores 4-6 (content opportunity, needs fact-checking)

---

### Story 2.3: Reddit Research Scanner

As an **operator**,
I want Reddit monitored for mushroom/wellness discussions,
So that trending topics and user questions fuel content ideas.

**Acceptance Criteria:**

**Given** the Reddit scanner is scheduled (daily 2 AM)
**When** it executes
**Then** it scans configured subreddits: r/Nootropics, r/Supplements, r/MushroomSupplements, r/Biohackers
**And** it searches for keywords: lion's mane, chaga, reishi, cordyceps, shiitake, maitake
**And** it collects posts from the last 24 hours with 10+ upvotes

**Given** a Reddit post is collected
**When** the harvester processes it
**Then** it extracts: title, body text, upvotes, comment count, permalink
**And** the transformer standardizes format for Research Pool
**And** the validator checks EU compliance
**And** the publisher saves to Research Pool with source=reddit

**Given** Reddit API is unavailable
**When** retry middleware exhausts attempts
**Then** the scan is marked INCOMPLETE and queued for next cycle
**And** previous research remains available

---

### Story 2.4: YouTube Research Scanner

As an **operator**,
I want YouTube searched for mushroom supplement content,
So that video insights and trends inform our content strategy.

**Acceptance Criteria:**

**Given** the YouTube scanner is scheduled (weekly Sunday 3 AM)
**When** it executes
**Then** it searches YouTube Data API for: mushroom supplements, lion's mane benefits, adaptogen reviews
**And** it filters for videos from last 7 days with 1,000+ views
**And** it prioritizes health/wellness channels

**Given** a video is selected
**When** the harvester processes it
**Then** it extracts video transcript using YouTube transcript API
**And** key_insight_extractor (Sonnet) summarizes main points
**And** it captures: title, channel, views, publish date, transcript summary

**Given** a video transcript is extracted
**When** the transformer processes it
**Then** it identifies quotable insights (max 3 per video)
**And** it tags with relevant topics
**And** it validates compliance before pool entry

---

### Story 2.5: Instagram Trend Scanner

As an **operator**,
I want Instagram hashtags and competitors monitored,
So that I stay aware of trending content and competitor activity.

**Acceptance Criteria:**

**Given** the Instagram scanner is scheduled (daily 2:30 AM)
**When** it executes
**Then** it monitors hashtags: #lionsmane, #mushroomsupplements, #adaptogens, #biohacking
**And** it monitors configured competitor accounts
**And** it collects top posts from last 24 hours

**Given** a trending post is found
**When** the harvester processes it
**Then** it extracts: caption text, hashtags, engagement metrics, account name
**And** it does NOT download or store images (privacy/copyright)
**And** it captures content themes and messaging patterns

**Given** competitor content is detected
**When** it contains health claims
**Then** it flags for potential CleanMarket review (Epic 6 integration point)
**And** it still enters Research Pool as trend data

---

### Story 2.6: Industry News Scanner

As an **operator**,
I want health/wellness industry news aggregated,
So that I can respond to industry developments in content.

**Acceptance Criteria:**

**Given** the news scanner is scheduled (daily 6 AM)
**When** it executes
**Then** it scans configured RSS feeds and news sources
**And** it searches for: functional mushrooms, adaptogens, supplements industry, EU regulations
**And** it collects articles from last 24 hours

**Given** a news article is found
**When** the harvester processes it
**Then** it extracts: headline, summary, source, publish date, URL
**And** it categorizes: product news, regulatory, research, competitor

**Given** regulatory news is detected (EU, Mattilsynet)
**When** it mentions health claims or novel food
**Then** it's flagged high priority for operator attention
**And** it scores 8+ automatically

---

### Story 2.7: PubMed Scientific Research Scanner

As an **operator**,
I want scientific studies on mushroom compounds queried,
So that content can reference peer-reviewed evidence.

**Acceptance Criteria:**

**Given** the PubMed scanner is scheduled (weekly Sunday 4 AM)
**When** it executes
**Then** it queries Entrez API for: lion's mane cognition, chaga antioxidant, reishi immune, cordyceps performance
**And** it filters for studies from last 90 days
**And** it prioritizes RCTs and meta-analyses

**Given** a study is found
**When** the harvester processes it
**Then** it extracts: title, authors, journal, DOI, abstract, conclusions
**And** finding_summarizer (Sonnet) creates plain-language summary
**And** it captures study type, sample size, significance

**Given** a study makes claims about DAWO products
**When** the claim_validator checks it
**Then** it cross-references with EU approved claims
**And** it notes: "Can cite study, cannot claim treatment"
**And** it includes DOI link for content attribution

---

### Story 2.8: Research Compliance Validation

As an **operator**,
I want all research validated for EU compliance before pool entry,
So that only safe-to-use research fuels content creation.

**Acceptance Criteria:**

**Given** a research item completes harvester processing
**When** the validator stage runs
**Then** it calls EU Compliance Checker (from Epic 1)
**And** it evaluates extracted insights for prohibited claims
**And** it sets compliance_status on the research item

**Given** research contains prohibited language
**When** compliance check returns REJECTED
**Then** the item still enters pool (for awareness)
**And** it's marked with compliance_status=REJECTED
**And** content teams see warning when viewing

**Given** research cites a scientific study
**When** compliance check runs
**Then** study citations with DOI links are marked COMPLIANT
**And** study claims without links are marked WARNING

---

## Epic 3: Content Creation & Assets

**Goal:** The system creates Instagram content with generated graphics, combines research + product data, and queues it for review

**User Value:** The operator receives ready-to-approve Instagram posts with captions, graphics, quality scores, and compliance status without manual content creation.

**FRs covered:** FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR47, FR48, FR50

### Story 3.1: Shopify Product Data Integration

As an **operator**,
I want product data retrieved from Shopify,
So that content can reference accurate product info, pricing, and availability.

**Acceptance Criteria:**

**Given** the Shopify MCP integration is configured
**When** a content generator needs product data
**Then** it can query by: product name, SKU, or collection
**And** it retrieves: title, description, price, variants, images, inventory status
**And** data is cached for 1 hour to reduce API calls

**Given** a product is referenced in content
**When** the generator builds the post
**Then** it can include: product benefits, price point, link with UTM parameters
**And** it respects Novel Food classification (food vs supplement messaging)

**Given** Shopify MCP is unavailable
**When** retry middleware exhausts attempts
**Then** content generation continues with cached data or placeholder
**And** operator is alerted to update product references manually

---

### Story 3.2: Google Drive Asset Storage

As an **operator**,
I want generated assets stored in organized Google Drive folders,
So that all visual content is accessible and properly archived.

**Acceptance Criteria:**

**Given** an asset is generated (Orshot graphic or Nano Banana image)
**When** the asset storage agent saves it
**Then** it's stored in the correct folder:
- `DAWO.ECO/Assets/Generated/` for AI images
- `DAWO.ECO/Assets/Orshot/` for branded graphics
- `DAWO.ECO/Assets/Archive/` for used assets with performance data

**Given** an asset is saved
**When** it's stored in Google Drive
**Then** it includes metadata: generation date, prompt/template used, quality score
**And** filename follows pattern: `{date}_{type}_{topic}_{id}.{ext}`

**Given** the folder structure doesn't exist
**When** the first asset is saved
**Then** the system creates the required folders automatically

---

### Story 3.3: Instagram Caption Generator

As an **operator**,
I want Instagram captions generated in Norwegian using brand voice,
So that posts are ready for review without manual writing.

**Acceptance Criteria:**

**Given** a research item is selected for content
**When** the caption generator runs
**Then** it produces a Norwegian caption (180-220 words)
**And** it follows DAWO brand voice: warm, educational, Nordic simplicity
**And** it includes a clear CTA (call-to-action)
**And** it references the research source appropriately

**Given** product data is available from Shopify
**When** the generator builds the caption
**Then** it weaves in relevant product benefits naturally
**And** it includes product link with UTM parameters
**And** it avoids direct sales language (educational first)

**Given** the caption is generated
**When** it's evaluated
**Then** it's checked against Brand Voice Validator (Epic 1)
**And** revision suggestions are included if needed
**And** generation completes in < 60 seconds

---

### Story 3.4: Orshot Branded Graphics Integration

As an **operator**,
I want branded graphics generated via Orshot using my Canva templates,
So that posts have consistent visual identity without manual design.

**Acceptance Criteria:**

**Given** a content item needs a branded graphic
**When** the Orshot renderer is called
**Then** it uses a template imported from Canva
**And** it injects dynamic content: headline, product name, date
**And** it returns a high-resolution image (1080x1080 for Instagram feed)

**Given** Orshot Starter tier is configured ($30/mo, 3,000 renders)
**When** renders are requested
**Then** usage is tracked against monthly limit
**And** operator is alerted at 80% usage
**And** render requests respect rate limits

**Given** a template is selected
**When** the graphic is generated
**Then** it preserves DAWO brand colors, fonts, and spacing
**And** generated asset is saved to Google Drive (Story 3.2)
**And** quality score is assigned based on template match

---

### Story 3.5: Nano Banana AI Image Generation

As an **operator**,
I want AI images generated for visual variety,
So that content has engaging visuals when product photos aren't suitable.

**Acceptance Criteria:**

**Given** a content item needs an AI-generated image
**When** the Nano Banana (Gemini) generator is called
**Then** it uses a prompt incorporating: topic, mood, Scandinavian aesthetic
**And** it avoids: mushroom close-ups that look unappetizing, medical imagery
**And** it returns a lifestyle-appropriate image

**Given** an AI image is generated
**When** it's evaluated for quality
**Then** it receives a quality score (1-10) based on:
- Aesthetic appeal
- Brand alignment
- AI detectability risk (lower is better)
**And** images scoring < 6 are flagged for human review

**Given** AI detectability is a concern
**When** image is generated
**Then** metadata does NOT include AI generation markers
**And** style emphasizes natural, human-curated aesthetic
**And** asset is saved to Google Drive with generation metadata

---

### Story 3.6: Content Compliance & Rewrite Suggestions

As an **operator**,
I want generated content checked for EU compliance with rewrite suggestions,
So that I can quickly fix issues without manual rewording.

**Acceptance Criteria:**

**Given** a caption is generated
**When** EU Compliance Checker (Epic 1) evaluates it
**Then** it returns: overall status, flagged phrases, severity per phrase
**And** compliance check completes in < 10 seconds

**Given** content contains BORDERLINE phrases
**When** the rewrite suggester runs
**Then** it proposes compliant alternatives:
- "supports healthy metabolism" → keep (borderline acceptable)
- "treats brain fog" → "supports mental clarity"
- "cures fatigue" → "helps you feel refreshed"
**And** suggestions maintain brand voice

**Given** content is REJECTED
**When** rewrite suggestions are generated
**Then** all prohibited phrases have alternatives
**And** operator can accept suggestions with one click
**And** re-validation runs automatically after edits

---

### Story 3.7: Content Quality Scoring

As an **operator**,
I want content scored for quality before I review it,
So that I can prioritize high-quality posts and identify weak ones.

**Acceptance Criteria:**

**Given** a content item is ready for queue
**When** the quality scorer evaluates it
**Then** it calculates a score (1-10) based on:
- Compliance status (25%): COMPLIANT=full, WARNING=-2, REJECTED=0
- Brand voice match (20%): from Brand Voice Validator
- Visual quality (15%): from image quality score
- Platform optimization (15%): hashtags, length, format fit
- Engagement prediction (15%): based on past performance data
- Authenticity (10%): human feel vs AI-generic

**Given** AI detectability is evaluated
**When** content shows AI patterns
**Then** authenticity score is reduced
**And** specific AI markers are flagged (generic phrasing, perfect structure)

**Given** quality score is calculated
**When** content enters approval queue
**Then** score is displayed prominently
**And** items are sorted by score (highest first)

---

### Story 3.8: Auto-Publish Eligibility Tagging

As an **operator**,
I want high-quality compliant content tagged for potential auto-publishing,
So that I can build trust in the system before enabling automation.

**Acceptance Criteria:**

**Given** a content item has quality score ≥ 9
**When** compliance status is COMPLIANT
**Then** it receives tag: `WOULD_AUTO_PUBLISH`
**And** this is displayed in approval queue as badge

**Given** content is tagged WOULD_AUTO_PUBLISH
**When** operator reviews it
**Then** they see: "This post would have auto-published"
**And** system tracks: how many WOULD_AUTO_PUBLISH posts are approved unchanged

**Given** simulation data accumulates
**When** operator views dashboard
**Then** they see: WOULD_AUTO_PUBLISH accuracy rate
**And** they can enable real auto-publish per content type when confident

**Given** auto-publish is disabled (default MVP)
**When** content is tagged WOULD_AUTO_PUBLISH
**Then** it still requires human approval
**And** tag is informational only

---

### Story 3.9: Asset Usage Tracking

As an **operator**,
I want asset usage history tracked with performance correlation,
So that I know which visuals work best.

**Acceptance Criteria:**

**Given** an asset is used in a published post
**When** the post is published
**Then** asset record is updated with: post ID, publish date, platform

**Given** performance data is collected (Epic 7)
**When** post metrics are available
**Then** asset record is updated with: engagement rate, conversions
**And** asset receives a performance score

**Given** asset performance is tracked
**When** content team selects visuals
**Then** they can see: past usage count, average performance
**And** high-performing assets are suggested first

**Given** an asset is archived
**When** moved to Archive folder
**Then** full performance history is preserved
**And** asset remains searchable for analytics

---

## Epic 4: Approval & Auto-Publishing

**Goal:** Review content in a single queue, batch approve, and it auto-publishes to Instagram at optimal times

**User Value:** The operator can review and approve content in under 5 minutes daily, with automatic publishing at scheduled times and Discord notifications keeping them informed.

**FRs covered:** FR35, FR36, FR37, FR38, FR39, FR40, FR41

### Story 4.1: Content Approval Queue UI

As an **operator**,
I want pending content displayed in an approval queue with quality scores,
So that I can efficiently review what needs my attention.

**Acceptance Criteria:**

**Given** content items are pending approval
**When** I open the approval queue in IMAGO dashboard
**Then** I see a list of items with:
- Preview thumbnail (image/graphic)
- Caption excerpt (first 100 chars)
- Quality score (1-10) with color coding (green 8+, yellow 5-7, red <5)
- Compliance status badge (COMPLIANT/WARNING/REJECTED)
- WOULD_AUTO_PUBLISH badge if applicable
- Suggested publish time
- Source type (Instagram post, B2B email, etc.)

**Given** multiple items are in queue
**When** the queue loads
**Then** items are sorted by source-based priority:
1. Trending (time-sensitive)
2. Scheduled (approaching deadline)
3. Evergreen (flexible timing)
4. Research-based (lowest urgency)
**And** queue loads in < 3 seconds

**Given** I click on a queue item
**When** the detail view opens
**Then** I see: full caption, full image, all hashtags, compliance details, quality breakdown
**And** I can expand flagged phrases to see explanations

---

### Story 4.2: Approve, Reject, Edit Actions

As an **operator**,
I want to approve, reject, or edit individual content items,
So that I control exactly what gets published.

**Acceptance Criteria:**

**Given** I'm viewing a content item
**When** I click Approve
**Then** status changes to APPROVED
**And** item moves to scheduled queue
**And** suggested publish time is confirmed (or I can modify)

**Given** I'm viewing a content item
**When** I click Reject
**Then** I must provide a rejection reason (dropdown + optional text)
**And** status changes to REJECTED
**And** item is archived with rejection reason
**And** rejection data feeds back to content generation for learning

**Given** I'm viewing a content item
**When** I click Edit
**Then** caption becomes editable inline
**And** I can accept AI rewrite suggestions with one click
**And** compliance re-validates automatically after edit
**And** quality score recalculates after edit

**Given** I edit content
**When** I save changes
**Then** edit history is preserved (audit trail)
**And** original version remains accessible
**And** I can revert to original if needed

---

### Story 4.3: Batch Approval Capability

As an **operator**,
I want to approve multiple content items at once,
So that daily review takes under 5 minutes.

**Acceptance Criteria:**

**Given** multiple items are in approval queue
**When** I select items using checkboxes
**Then** a batch action bar appears with: Approve All, Reject All

**Given** I've selected multiple items
**When** I click Approve All
**Then** all selected items are approved
**And** each uses its suggested publish time
**And** confirmation shows: "X items approved, scheduled for [dates]"

**Given** I want to quickly approve high-quality items
**When** I use "Approve All WOULD_AUTO_PUBLISH" filter
**Then** only items tagged WOULD_AUTO_PUBLISH are selected
**And** I can approve them with one click

**Given** batch approval completes
**When** I return to queue
**Then** approved items are removed from pending view
**And** remaining items are re-sorted by priority

---

### Story 4.4: Content Scheduling Interface

As an **operator**,
I want to set or modify publish times for approved content,
So that posts go out at optimal times.

**Acceptance Criteria:**

**Given** content is approved
**When** I view the scheduling interface
**Then** I see a calendar view with scheduled posts
**And** each day shows post count and times
**And** optimal times are suggested based on engagement data

**Given** I want to change a publish time
**When** I drag-and-drop a post on the calendar
**Then** publish time is updated
**And** conflicts are highlighted (too many posts same hour)

**Given** I'm scheduling a post
**When** system suggests optimal time
**Then** suggestion is based on:
- Historical engagement data by hour/day
- Platform best practices (Instagram peak times)
- Avoiding conflicts with other scheduled posts

**Given** a scheduled post is approaching
**When** it's within 1 hour of publish time
**Then** status shows "Publishing soon"
**And** editing is locked (or requires confirmation)

---

### Story 4.5: Instagram Graph API Auto-Publishing

As an **operator**,
I want approved content to publish automatically to Instagram,
So that I don't need to manually post at scheduled times.

**Acceptance Criteria:**

**Given** content is approved and scheduled
**When** the scheduled time arrives
**Then** Publisher Team posts via Instagram Graph API
**And** caption, image, and hashtags are included
**And** status changes to PUBLISHED
**And** Instagram post ID is captured for tracking

**Given** Instagram API is available
**When** publish executes
**Then** it completes in < 30 seconds
**And** success is logged with timestamp

**Given** Instagram API fails
**When** retry middleware exhausts attempts
**Then** status changes to PUBLISH_FAILED
**And** Discord alert is sent immediately
**And** item is queued for manual retry
**And** operator can retry from dashboard

**Given** a post is published
**When** I view it in dashboard
**Then** I see: Instagram post link, publish timestamp, initial metrics (if available)

---

### Story 4.6: Discord Approval Notifications

As an **operator**,
I want Discord notifications when approvals are needed,
So that I know when to check the queue without constantly monitoring.

**Acceptance Criteria:**

**Given** new content enters approval queue
**When** queue reaches threshold (5+ items or configurable)
**Then** Discord notification is sent: "🔔 DAWO Agents: X items ready for review"
**And** notification includes: count by type, highest priority item

**Given** notifications are configured
**When** they're sent
**Then** they go to configured webhook URL
**And** format is: embed with summary, link to dashboard
**And** rate limited to max 1 per hour (batched)

**Given** content has compliance warning
**When** it enters queue
**Then** Discord notification mentions: "⚠️ 1 item needs compliance review"

**Given** Discord webhook is unavailable
**When** notification fails
**Then** retry middleware handles it
**And** notifications are queued for later delivery
**And** system continues without blocking

---

### Story 4.7: Discord Publish Notifications

As an **operator**,
I want Discord notifications when posts are published,
So that I have visibility into what went live.

**Acceptance Criteria:**

**Given** a post is successfully published
**When** publish completes
**Then** Discord notification is sent: "✅ Published: [Post title/excerpt]"
**And** notification includes: Instagram link, publish time

**Given** multiple posts publish in short period
**When** notifications would spam
**Then** they're batched: "✅ Published 3 posts in the last hour"
**And** batch summary includes links to each

**Given** a publish fails
**When** all retries are exhausted
**Then** Discord notification is sent: "❌ Publish failed: [Post title]"
**And** notification includes: error reason, link to retry in dashboard

**Given** daily publishing is complete
**When** end of day (configurable, default 10 PM)
**Then** summary notification is sent: "📊 Today: X posts published, Y pending, Z failed"

---

## Epic 5: B2B Sales Pipeline

**Goal:** The system finds potential B2B partners, enriches leads, and drafts personalized outreach emails for approval

**User Value:** The operator receives researched, qualified leads with personalized outreach drafts ready to send, enabling 15+ B2B contacts per week without manual research.

**FRs covered:** FR17, FR18, FR19, FR20, FR21

### Story 5.1: B2B Lead Research Scanner

As an **operator**,
I want potential B2B retail partners automatically discovered,
So that I have a steady pipeline of qualified leads without manual research.

**Acceptance Criteria:**

**Given** the B2B scanner is scheduled (weekly Monday 7 AM)
**When** it executes
**Then** it searches configured sources for: health food stores, wellness retailers, specialty grocers
**And** it filters by: location (Norway/Nordic), size indicators, online presence
**And** it collects: business name, location, website, contact info if public

**Given** a potential lead is discovered
**When** the harvester processes it
**Then** it extracts: company name, address, website URL, social profiles
**And** it validates the business is relevant (health/wellness focus)
**And** it checks for existing relationship in lead database (no duplicates)

**Given** a lead passes initial filtering
**When** it enters the pipeline
**Then** status is set to `DISCOVERED`
**And** lead record is created with discovery timestamp
**And** it's queued for enrichment (Story 5.2)

---

### Story 5.2: Lead Information Enrichment

As an **operator**,
I want discovered leads enriched with detailed business information,
So that outreach can be personalized and relevant.

**Acceptance Criteria:**

**Given** a lead has status `DISCOVERED`
**When** the enrichment agent processes it
**Then** it gathers from public sources:
- Business description and focus areas
- Product categories carried
- Social media presence and activity
- Any existing mushroom/supplement offerings
- Decision maker names if publicly available

**Given** enrichment completes successfully
**When** data is saved
**Then** lead status changes to `ENRICHED`
**And** enrichment confidence score is assigned (1-10)
**And** personalization hooks are identified (e.g., "carries competitor X", "focus on organic")

**Given** enrichment finds insufficient data
**When** confidence score < 5
**Then** lead is flagged for manual research
**And** status changes to `NEEDS_REVIEW`
**And** operator sees what data is missing

**Given** lead is a competitor retailer
**When** they already carry DAWO products
**Then** lead is marked `EXISTING_CUSTOMER` and excluded from outreach

---

### Story 5.3: Personalized Outreach Draft Generator

As an **operator**,
I want personalized outreach emails drafted using lead insights,
So that B2B contacts feel tailored, not mass-mailed.

**Acceptance Criteria:**

**Given** a lead has status `ENRICHED` with confidence ≥ 6
**When** the outreach generator runs
**Then** it creates a personalized email draft including:
- Reference to their business focus (from enrichment)
- Relevant DAWO products for their customer base
- Specific value proposition based on their market
- Clear CTA (meeting request, sample offer, catalog)

**Given** the draft is generated
**When** it's evaluated
**Then** it passes Brand Voice Validator (warm, professional, Norwegian)
**And** it avoids generic sales language
**And** it includes personalization tokens that were filled
**And** draft length is 150-250 words

**Given** a draft is ready
**When** it enters approval queue
**Then** it shows: lead summary, personalization used, suggested send time
**And** operator can edit before approving
**And** status changes to `DRAFT_READY`

**Given** multiple outreach templates exist
**When** generator selects one
**Then** it chooses based on lead type (health store vs. gym vs. online retailer)
**And** template selection is logged for performance tracking

---

### Story 5.4: Gmail API Integration

As an **operator**,
I want approved outreach drafts sent via Gmail API,
So that emails come from my business account with proper tracking.

**Acceptance Criteria:**

**Given** an outreach draft is approved
**When** the Gmail sender executes
**Then** it sends via configured Gmail API account
**And** email includes: proper from address, subject line, body, signature
**And** UTM parameters are added to any links for tracking

**Given** Gmail API credentials are configured
**When** the sender authenticates
**Then** it uses OAuth2 with refresh token
**And** credentials are stored securely (not in code)
**And** authentication failures trigger Discord alert

**Given** an email is sent successfully
**When** send completes
**Then** lead status changes to `CONTACTED`
**And** send timestamp is recorded
**And** email thread ID is captured for follow-up tracking

**Given** Gmail API fails
**When** retry middleware exhausts attempts
**Then** status changes to `SEND_FAILED`
**And** operator is notified via Discord
**And** draft remains approved for manual send or retry

**Given** rate limits apply
**When** many emails are queued
**Then** sends are spaced to respect Gmail limits (20/minute suggested)
**And** queue processes over time rather than bursting

---

### Story 5.5: Lead Pipeline Status Tracking

As an **operator**,
I want lead status tracked through pipeline stages,
So that I can monitor progress and follow up appropriately.

**Acceptance Criteria:**

**Given** leads exist in the system
**When** I view the lead pipeline dashboard
**Then** I see leads organized by status:
- `DISCOVERED` → awaiting enrichment
- `ENRICHED` → ready for outreach draft
- `DRAFT_READY` → awaiting approval
- `CONTACTED` → email sent, awaiting response
- `RESPONDED` → received reply (manual update)
- `CONVERTED` → became customer (manual update)
- `CLOSED_LOST` → declined or unresponsive

**Given** a lead has been contacted
**When** 7 days pass without response
**Then** system suggests follow-up outreach
**And** lead is flagged in dashboard

**Given** I need pipeline metrics
**When** I view the summary
**Then** I see: leads by stage, conversion rate, average time in each stage
**And** weekly trend of new discoveries vs. conversions

**Given** a lead status changes
**When** the change is logged
**Then** full history is preserved: status, timestamp, actor (system/operator)
**And** I can view the complete journey of any lead

**Given** export is needed
**When** I request lead export
**Then** CSV download includes all lead data and status history
**And** export respects any date/status filters applied

---

## Epic 6: CleanMarket & Regulatory Intelligence

**Goal:** Monitor competitors for EU violations and stay ahead of new approved health claims and regulatory changes

**User Value:** The operator has documented evidence of competitor violations for potential regulatory reporting, plus early alerts when new health claims are approved for DAWO products.

**FRs covered:** FR25, FR26, FR27, FR28, FR29, FR30, FR31, FR32, FR33, FR34

### Story 6.1: EU Health Claims Register Monitor

As an **operator**,
I want the EU Health Claims Register monitored for changes,
So that I know when new claims are approved that I can use for DAWO products.

**Acceptance Criteria:**

**Given** the EU Register monitor is scheduled (weekly Sunday 5 AM)
**When** it executes
**Then** it queries the EU Health Claims Register database
**And** it compares current approved claims against cached version
**And** it identifies: new approvals, removed claims, modified wording

**Given** a new health claim is approved
**When** it relates to DAWO product categories (mushrooms, adaptogens, wellness)
**Then** it's flagged as high priority
**And** details are stored: claim text, conditions, product categories, approval date

**Given** no changes are detected
**When** the monitor completes
**Then** it logs successful check with timestamp
**And** no alerts are triggered

---

### Story 6.2: Novel Food Catalogue Monitor

As an **operator**,
I want the EU Novel Food Catalogue monitored,
So that I'm alerted to classification changes affecting DAWO products.

**Acceptance Criteria:**

**Given** the Novel Food monitor is scheduled (weekly Sunday 5:30 AM)
**When** it executes
**Then** it queries EU Novel Food Catalogue for: lion's mane, chaga, reishi, cordyceps, shiitake, maitake
**And** it compares current classifications against cached version
**And** it identifies: new entries, status changes, authorization updates

**Given** a product classification changes
**When** it affects DAWO products (e.g., Chaga status update)
**Then** it's flagged URGENT for operator review
**And** alert includes: previous status, new status, effective date, implications

**Given** a new mushroom species is added
**When** it's relevant to wellness supplements
**Then** it's logged for market opportunity review
**And** compliance implications are noted

---

### Story 6.3: Mattilsynet Regulatory Monitor

As an **operator**,
I want Norwegian Food Safety Authority (Mattilsynet) monitored,
So that I'm aware of local regulatory changes before they affect my business.

**Acceptance Criteria:**

**Given** the Mattilsynet monitor is scheduled (daily 7 AM)
**When** it executes
**Then** it scans mattilsynet.no for: supplement regulations, health claims, enforcement actions
**And** it monitors RSS feeds and news sections
**And** it filters for keywords: kosttilskudd, helsepåstander, sopp, functional foods

**Given** regulatory news is detected
**When** it mentions DAWO product categories
**Then** it's flagged for operator attention
**And** summary is generated with: headline, key points, potential impact

**Given** enforcement action is announced
**When** it involves competitor or similar products
**Then** it's flagged HIGH priority
**And** stored as intelligence for CleanMarket context

---

### Story 6.4: New Claims Activation Alerts

As an **operator**,
I want immediate alerts when new health claims become usable,
So that I can update my content strategy ahead of competitors.

**Acceptance Criteria:**

**Given** a new claim is approved (from Stories 6.1-6.3)
**When** it applies to DAWO products
**Then** Discord alert is sent immediately: "New claim approved: [claim text]"
**And** alert includes: applicable products, wording guidelines, effective date

**Given** a claim alert is generated
**When** operator views details
**Then** they see: full claim text, usage conditions, example compliant phrases
**And** content team is notified to update caption templates

**Given** multiple claims are approved in same period
**When** alerts would spam
**Then** they're batched into summary: "3 new claims for mushroom supplements"
**And** individual claims are linked for review

**Given** a claim has usage restrictions
**When** alert is generated
**Then** restrictions are prominently displayed
**And** compliance checker rules are updated automatically

---

### Story 6.5: Competitor Content Scanner

As an **operator**,
I want competitor Instagram and websites scanned for content,
So that I can identify potential EU violations in their marketing.

**Acceptance Criteria:**

**Given** competitor accounts are configured
**When** the scanner executes (daily 3 AM)
**Then** it scans each competitor's recent Instagram posts (last 7 days)
**And** it scans configured website pages (product pages, blog posts)
**And** it respects rate limits and robots.txt

**Given** competitor content is collected
**When** the harvester processes it
**Then** it extracts: text content, captions, claims made, hashtags used
**And** it captures: source URL, timestamp, account/domain
**And** it does NOT store competitor images (privacy)

**Given** a competitor post is found
**When** it contains wellness/health language
**Then** it's queued for health claim extraction (Story 6.6)
**And** source metadata is preserved for evidence

---

### Story 6.6: Health Claim Extraction Engine

As an **operator**,
I want health claims automatically extracted from competitor content,
So that potential violations can be identified systematically.

**Acceptance Criteria:**

**Given** competitor content is queued for analysis
**When** the extraction engine runs
**Then** it identifies health-related phrases using NLP
**And** it categorizes claims by type: treatment, prevention, enhancement, general wellness
**And** it extracts: exact phrase, surrounding context, claim category

**Given** a phrase is identified as potential claim
**When** it's extracted
**Then** confidence score is assigned (0-100%)
**And** claims with confidence > 70% proceed to violation detection
**And** lower confidence claims are logged for manual review

**Given** multiple claims exist in one post
**When** extraction completes
**Then** each claim is stored separately
**And** all claims link back to source content
**And** extraction uses Sonnet for accuracy

---

### Story 6.7: EU Violation Detection

As an **operator**,
I want extracted claims checked against EU regulations,
So that actual violations are flagged for evidence collection.

**Acceptance Criteria:**

**Given** a claim is extracted from competitor content
**When** the violation detector evaluates it
**Then** it checks against: EU Health Claims Register (approved list), EC 1924/2006 rules
**And** it classifies as: VIOLATION (prohibited claim), SUSPECT (borderline), COMPLIANT

**Given** a claim is classified as VIOLATION
**When** detection completes
**Then** violation record is created with:
- Claim text
- Regulation violated (specific article)
- Competitor source
- Detection timestamp
- Confidence level

**Given** a competitor claims treatment/cure
**When** no EU-approved claim exists
**Then** it's automatically classified as VIOLATION
**And** severity is marked HIGH

**Given** a claim uses borderline language
**When** context suggests medical intent
**Then** it's classified as SUSPECT for operator review
**And** detection reasoning is documented

---

### Story 6.8: Evidence Collection & Screenshots

As an **operator**,
I want violation evidence collected with screenshots and timestamps,
So that I have legally defensible documentation.

**Acceptance Criteria:**

**Given** a violation is detected
**When** evidence collection runs
**Then** it captures screenshot of source page/post
**And** screenshot includes visible timestamp (system clock overlay)
**And** screenshot is saved to immutable storage

**Given** evidence is collected
**When** it's stored
**Then** record includes:
- Screenshot file (PNG)
- Source URL
- Captured timestamp (ISO 8601)
- Hash of screenshot for integrity verification
- Claim text and violation type

**Given** Instagram post is evidence source
**When** screenshot is taken
**Then** it captures: post image area, caption, engagement metrics, timestamp
**And** account name is visible

**Given** evidence is stored
**When** any modification is attempted
**Then** modification is BLOCKED (immutable)
**And** audit log records the attempt
**And** original evidence is preserved

---

### Story 6.9: Searchable Evidence Database

As an **operator**,
I want violation evidence searchable and filterable,
So that I can find specific violations quickly for reporting.

**Acceptance Criteria:**

**Given** evidence exists in the database
**When** I open the CleanMarket evidence view
**Then** I see evidence records with: competitor, violation type, date, severity
**And** thumbnails of screenshots are displayed
**And** list loads in < 3 seconds for up to 1,000 records

**Given** I need to find specific evidence
**When** I use search/filter
**Then** I can filter by:
- Competitor name
- Violation type (treatment claims, prevention claims, etc.)
- Date range
- Severity level
- Claim keywords

**Given** I click on an evidence record
**When** detail view opens
**Then** I see: full screenshot, claim text, regulation violated, source URL
**And** I can download evidence package (screenshot + metadata)
**And** evidence integrity hash is displayed

**Given** evidence links to competitor
**When** I view competitor profile
**Then** I see all violations by that competitor
**And** violation trend over time is displayed

---

### Story 6.10: On-Demand Violation Reports

As an **operator**,
I want violation reports generated on demand,
So that I can submit formal complaints to regulatory authorities.

**Acceptance Criteria:**

**Given** I select evidence records
**When** I request report generation
**Then** a PDF report is created containing:
- Executive summary of violations
- Evidence for each violation (screenshot, claim, regulation)
- Timeline of violations by competitor
- Appendix with raw evidence data

**Given** a report is generated
**When** I download it
**Then** report includes: generation date, evidence integrity hashes, page numbers
**And** format is suitable for regulatory submission
**And** report can be regenerated identically (deterministic)

**Given** I need report for specific competitor
**When** I filter by competitor
**Then** report focuses on that competitor only
**And** includes all violations in date range

**Given** regulatory body has specific requirements
**When** I configure report template
**Then** template can be customized for: Mattilsynet, EU authorities, legal counsel
**And** required fields are included per template

---

## Epic 7: Analytics & System Operations

**Goal:** See what content performs best, the system learns from success, and manage agent schedules and execution

**User Value:** The operator understands ROI per content type, the system continuously improves predictions, and agents run on schedule with full visibility into execution status.

**FRs covered:** FR42, FR43, FR44, FR45, FR46, FR51, FR52, FR53, FR54, FR55

### Story 7.1: Instagram Engagement Metrics Collection

As an **operator**,
I want Instagram engagement metrics collected at regular intervals,
So that I can measure content performance over time.

**Acceptance Criteria:**

**Given** a post is published to Instagram
**When** 24 hours have passed
**Then** the metrics collector retrieves: likes, comments, shares, saves, reach, impressions
**And** metrics are stored with post ID and timestamp
**And** collection repeats at 48h and 7d intervals

**Given** Instagram API is available
**When** metrics are collected
**Then** data is retrieved in < 10 seconds per post
**And** all available metrics are captured
**And** collection respects rate limits

**Given** metrics are collected at multiple intervals
**When** I view post performance
**Then** I see trend: initial engagement, growth over time, final metrics
**And** comparison to average post performance is shown

**Given** Instagram API is unavailable
**When** scheduled collection fails
**Then** it's queued for retry at next opportunity
**And** partial data is preserved
**And** operator is notified of gaps in data

---

### Story 7.2: UTM Click-Through Tracking

As an **operator**,
I want click-throughs from posts tracked via UTM parameters,
So that I can attribute website traffic to specific content.

**Acceptance Criteria:**

**Given** content is published with UTM-tagged links
**When** users click through to website
**Then** UTM parameters are captured: source, medium, campaign, content
**And** clicks are counted and stored by post ID

**Given** UTM tracking is configured
**When** link is generated for a post
**Then** UTM contains: utm_source=instagram, utm_medium=post, utm_campaign={content_type}, utm_content={post_id}
**And** links are shortened if needed

**Given** click data is collected
**When** I view post analytics
**Then** I see: total clicks, click-through rate, clicks by day
**And** comparison to average CTR is shown

**Given** user completes action on website
**When** session includes UTM from post
**Then** conversion is attributed to that post
**And** attribution window is configurable (default 7 days)

---

### Story 7.3: Shopify Sales Attribution

As an **operator**,
I want Shopify sales attributed to content that drove them,
So that I understand revenue impact of each post.

**Acceptance Criteria:**

**Given** a Shopify order is placed
**When** session contains UTM from Instagram post
**Then** order revenue is attributed to that post
**And** attribution includes: order ID, revenue, products purchased

**Given** multiple posts contributed to a sale
**When** user visited from multiple posts before purchase
**Then** attribution uses last-touch model (most recent post)
**And** all touchpoints are recorded for analysis

**Given** attribution data exists
**When** I view post performance
**Then** I see: attributed revenue, orders, average order value
**And** ROI can be calculated (if cost data available)

**Given** a sale occurs within attribution window
**When** attribution is calculated
**Then** revenue is correctly linked to post
**And** products are categorized (which product lines perform best)
**And** data updates in dashboard within 1 hour of sale

---

### Story 7.4: Post-Publish Quality Scoring

As an **operator**,
I want posts scored after publish based on actual performance,
So that I can validate pre-publish quality predictions.

**Acceptance Criteria:**

**Given** post metrics are collected at 7 days
**When** post-publish scorer runs
**Then** it calculates actual performance score (1-10) based on:
- Engagement rate vs. average
- Reach vs. predicted
- Click-through rate
- Conversions attributed
- Comments sentiment (positive/negative)

**Given** post-publish score is calculated
**When** compared to pre-publish quality score
**Then** variance is recorded: predicted vs. actual
**And** large variances (>3 points) are flagged for review

**Given** variance data accumulates
**When** 50+ posts have both scores
**Then** correlation analysis runs automatically
**And** quality scorer weights are recommended for adjustment

**Given** a post significantly outperforms prediction
**When** I review it
**Then** I see: what made it successful, suggested learnings
**And** similar content patterns are identified

---

### Story 7.5: Performance Feedback Loop

As an **operator**,
I want performance data to improve future content predictions,
So that the system learns from success and failure.

**Acceptance Criteria:**

**Given** post-publish scores exist for 100+ posts
**When** the feedback loop runs (weekly)
**Then** it analyzes: what content types perform best, optimal posting times, effective hashtags
**And** recommendations are generated for content strategy

**Given** analysis identifies successful patterns
**When** content scorer evaluates new content
**Then** it weights those patterns higher
**And** engagement prediction improves over time

**Given** research sources have varied performance
**When** source attribution is analyzed
**Then** scoring engine adjusts source weights:
- High-performing sources get +weight
- Low-performing sources get -weight

**Given** operator rejects or heavily edits content
**When** feedback is analyzed
**Then** patterns that lead to rejection are identified
**And** generators are tuned to avoid those patterns
**And** learning updates are logged for transparency

---

### Story 7.6: Agent Schedule Configuration

As an **operator**,
I want to configure when agents run,
So that tasks execute at optimal times for my workflow.

**Acceptance Criteria:**

**Given** I open the agent scheduler configuration
**When** I view the schedule
**Then** I see all scheduled agents with: name, schedule, next run time, last run status

**Given** I want to modify an agent's schedule
**When** I edit the schedule
**Then** I can set: frequency (hourly/daily/weekly), specific time, timezone
**And** changes take effect from next scheduled run
**And** previous schedule is logged for audit

**Given** agents have dependencies
**When** I schedule them
**Then** system warns of conflicts (e.g., scanner before harvester)
**And** suggested ordering is provided

**Given** a schedule is configured
**When** time arrives
**Then** agent is triggered via ARQ job queue
**And** execution status is tracked

---

### Story 7.7: Manual Team/Agent Triggers

As an **operator**,
I want to manually trigger agents or teams,
So that I can run tasks on-demand when needed.

**Acceptance Criteria:**

**Given** I view the agent/team list
**When** I select an agent
**Then** I see a "Run Now" button
**And** last execution status is displayed

**Given** I click "Run Now"
**When** the agent is not already running
**Then** it executes immediately
**And** execution appears in logs
**And** button shows "Running..." state

**Given** I trigger a team
**When** the team has multiple agents
**Then** all team agents execute in configured order
**And** team status shows overall progress

**Given** an agent is already running
**When** I try to trigger it
**Then** I see warning: "Agent already running"
**And** I can choose to queue or cancel

**Given** I need to trigger with parameters
**When** I run a scanner with custom keywords
**Then** I can override default config for this run
**And** override is logged but doesn't change schedule config

---

### Story 7.8: Execution Logs & Status Dashboard

As an **operator**,
I want to see agent execution status and logs,
So that I know what's running and can debug issues.

**Acceptance Criteria:**

**Given** I open the execution dashboard
**When** it loads
**Then** I see: currently running agents, recent completions, failures

**Given** agents are running
**When** I view the dashboard
**Then** I see real-time status: agent name, start time, progress indicator
**And** dashboard updates every 30 seconds

**Given** I click on an agent execution
**When** detail view opens
**Then** I see: start/end time, duration, status (success/failed/incomplete)
**And** log output is displayed (last 1000 lines)
**And** errors are highlighted

**Given** an agent failed
**When** I view the failure
**Then** I see: error message, stack trace (if available), retry count
**And** I can trigger manual retry from this view

**Given** I need historical data
**When** I filter by date range
**Then** I see all executions in that period
**And** I can filter by: agent, status, team

---

### Story 7.9: Google Calendar Sync

As an **operator**,
I want my content schedule visible in Google Calendar,
So that I can see posting schedule alongside other commitments.

**Acceptance Criteria:**

**Given** Google Calendar integration is configured
**When** content is scheduled for publish
**Then** a calendar event is created: title=post summary, time=publish time
**And** event includes link to content in dashboard

**Given** a scheduled post changes
**When** publish time is modified
**Then** calendar event is updated automatically
**And** sync happens within 5 minutes

**Given** content is published
**When** publish completes
**Then** calendar event is updated to show PUBLISHED status
**And** event moves to "completed" style (optional color change)

**Given** I view my Google Calendar
**When** content events appear
**Then** they're in a dedicated "DAWO Content" calendar
**And** I can toggle visibility without affecting sync

**Given** calendar API is unavailable
**When** sync fails
**Then** changes are queued for later sync
**And** operator is not blocked from scheduling

---

### Story 7.10: Graceful API Degradation Handling

As an **operator**,
I want the system to continue operating when external APIs fail,
So that temporary outages don't stop my workflow.

**Acceptance Criteria:**

**Given** an external API is unavailable (Instagram, Shopify, Discord, etc.)
**When** an operation requires that API
**Then** it follows graceful degradation strategy:
- Retry with backoff (from Story 1.5)
- Mark operation INCOMPLETE if retries fail
- Continue other operations that don't need that API

**Given** Instagram API is down
**When** publishing is scheduled
**Then** publish is queued for retry
**And** other content generation continues
**And** Discord notification is sent about the issue

**Given** Shopify MCP is unavailable
**When** content generator needs product data
**Then** it uses cached data if available (< 24h old)
**And** content proceeds with placeholder if no cache
**And** operator is notified to review product references

**Given** multiple APIs are down
**When** operator views system status
**Then** they see: which APIs are affected, what operations are queued
**And** estimated impact is shown (X posts waiting)

**Given** an API recovers
**When** it becomes available again
**Then** queued operations process automatically
**And** Discord notification announces recovery
**And** catch-up processing respects rate limits

---

## Document Summary

**Total Epics:** 7
**Total Stories:** 51

| Epic | Stories | FRs Covered |
|------|---------|-------------|
| 1 | 5 | FR22-24, FR49 |
| 2 | 8 | FR1-8 |
| 3 | 9 | FR9-16, FR47-48, FR50 |
| 4 | 7 | FR35-41 |
| 5 | 5 | FR17-21 |
| 6 | 10 | FR25-34 |
| 7 | 10 | FR42-46, FR51-55 |

**FR Coverage:** 55/55 (100%)
