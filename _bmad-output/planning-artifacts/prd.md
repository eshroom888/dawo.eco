---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - docs/bmad/project-brief.md
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 0
workflowType: 'prd'
classification:
  projectType: Internal AI Operations System
  domain: Regulated E-commerce Automation
  complexity: High
  projectContext: Greenfield on existing foundation
---

# Product Requirements Document - DAWO.ECO

**Author:** eshroom
**Date:** 2026-01-15

## Success Criteria

### User Success (CEO/Supervisor)
- **Feeling of automation:** Daily/weekly rhythm where agents propose, you approve, work gets done - not "another tool to babysit"
- **Trust threshold:** Routine outputs require minimal edits (<20% revision rate)
- **Time reclaimed:** 10+ hours/week freed from content, outreach, and monitoring tasks

### Business Success
- **B2C metric:** Content driving organic traffic - 7+ compliant posts/week within 30 days
- **B2B metric:** Pipeline growth - 20+ qualified leads researched/week within 60 days
- **B2B outreach:** 15+/week with personalized, compliant messaging
- **Revenue indicators:**
  - B2C: Measurable traffic increase from AI-generated content within 60 days
  - B2B: First retail partnership closed via agent-sourced lead within 90 days
- **ROI threshold:** Positive ROI within 90 days, scalable model proven by 180 days

### Technical Success
- **Compliance rate:** 100% of published content passes EU Health Claims validation
- **False positive rate:** <5% of agent outputs flagged as compliance issues that turn out to be fine
- **Integration reliability:** Shopify MCP, Discord webhooks operational 99%+ of the time

### Measurable Outcomes

| Metric | Baseline | Target | Timeframe |
|--------|----------|--------|-----------|
| Content pieces/week (B2C) | 1-2 | 7+ | 30 days |
| B2B leads researched/week | 0-2 | 20+ | 60 days |
| B2B outreach/week | 0-5 | 15+ | 60 days |
| Compliance violations | Unknown | 0 | Ongoing |
| First B2B sale from agent lead | N/A | 1+ | 90 days |

## Product Scope

### MVP - Minimum Viable Product
- **Content Department** with platform-specific teams (see Architecture below)
- **Sales Team** for B2B lead research and outreach drafts
- **CleanMarket Team** for competitor compliance monitoring (evidence collection mode)
- **Full Research Pipeline** - Reddit, YouTube, Instagram, News, PubMed
- **IMAGO.ECO dashboard** as primary interaction point (approval workflows)
- **Discord notifications** for alerting when approvals needed
- **Shopify MCP integration** for product data
- Focus: Both B2C (content) and B2B (sales) channels equally

### Growth Features (Post-MVP)
- Mobile app / PWA for on-the-go approvals
- Trust-based autonomy: some content types auto-approved after track record
- Klaviyo integration for email campaigns
- Analytics dashboard showing agent ROI per channel (B2C vs B2B)

### Vision (Future)
- **Support Team** with tiered escalation
- Full EU Health Claims Register API integration
- Multi-language content for international expansion
- Cross-team collaboration (Sales → Content handoffs via A2A)
- Google UCP integration for AI shopping surfaces

## System Architecture

### Architecture Philosophy

Following the IMAGO.ECO REDIS team pattern and ADK best practices:
- **Departments** contain multiple **Teams**
- **Teams** are SequentialAgent pipelines with specialized **Stage Agents**
- **Stage Agents** are reusable across teams (e.g., EU Compliance Checker)
- **Root Conductor** orchestrates user interaction and delegates to pipelines

This creates a **reusable agent library** where specialized agents can be recombined into new team workflows.

### LLM Strategy

**Primary LLM Provider:** Anthropic Claude (via Claude Agent SDK / API)

| Model | Use Case | Cost Tier |
|-------|----------|-----------|
| **Claude Haiku 4** | High-volume, simple tasks (scanning, formatting, queue ops) | Low |
| **Claude Sonnet 4** | Complex reasoning (content writing, compliance checking, strategy) | Medium |
| **Claude Opus 4.5** | Critical decisions (campaign architecture, brand voice definition) | High |

**Model Selection by Agent Type:**
- Scanner agents → Haiku (volume, speed)
- Writer agents → Sonnet (quality, creativity)
- Compliance agents → Sonnet (accuracy, reasoning)
- Strategy agents → Opus 4.5 (complex planning)
- Quality scoring → Sonnet (balanced judgment)

### DAWO Agent Organization

```
DAWO Supervisor (Root Conductor) [Opus 4.5]
│
├── MARKETING DEPARTMENT
│   │
│   ├── Strategy & Intelligence
│   │   │
│   │   ├── Marketing Strategy Team [Opus 4.5]
│   │   │   ├── trend_analyzer        → Monitor emerging topics (SEvO approach)
│   │   │   ├── campaign_architect    → Design campaign themes & narratives
│   │   │   ├── calendar_planner      → Content calendar, seasonal planning
│   │   │   ├── audience_analyzer     → Segment analysis, persona refinement
│   │   │   └── performance_strategist→ Adjust strategy based on analytics
│   │   │
│   │   ├── Platform Intelligence Team [Sonnet]
│   │   │   ├── sevo_optimizer        → Search Everywhere Optimization
│   │   │   ├── geo_optimizer         → Generative Engine Optimization (AI citations)
│   │   │   ├── hashtag_researcher    → Platform-specific keyword/hashtag research
│   │   │   └── algorithm_tracker     → Track platform algorithm changes
│   │   │
│   │   └── Brand Identity Team [Opus 4.5]
│   │       ├── voice_guardian        → Brand voice guidelines & enforcement
│   │       ├── visual_guardian       → Colors, fonts, logo, spacing rules
│   │       ├── tone_adapter          → Platform-specific tone variations
│   │       └── authenticity_auditor  → Ensure human feel, not AI-generic
│   │
│   ├── Research Teams (Source Monitoring)
│   │   │
│   │   ├── Reddit Research Team [Haiku] (extends REDIS pattern)
│   │   │   ├── reddit_scanner        → Scan health/wellness subreddits
│   │   │   ├── harvester_agent       → Collect full content
│   │   │   ├── transformer_agent     → Standardize format
│   │   │   ├── validator_agent       → Quality filter
│   │   │   └── research_publisher    → Output to Research Pool
│   │   │
│   │   ├── YouTube Research Team [Haiku]
│   │   │   ├── youtube_scanner       → Scan health/wellness channels
│   │   │   ├── transcript_extractor  → Get video transcripts
│   │   │   ├── key_insight_extractor → Pull main points [Sonnet]
│   │   │   ├── trend_tagger          → Tag with topics/themes
│   │   │   └── research_publisher    → Output to Research Pool
│   │   │
│   │   ├── PubMed Research Team [Sonnet]
│   │   │   ├── pubmed_scanner        → Search mushroom/adaptogen studies
│   │   │   ├── abstract_harvester    → Collect abstracts & metadata
│   │   │   ├── finding_summarizer    → Summarize key findings
│   │   │   ├── claim_validator       → Cross-ref with EU approved claims
│   │   │   └── research_publisher    → Output to Research Pool
│   │   │
│   │   ├── TikTok Research Team [Haiku]
│   │   │   ├── tiktok_scanner        → Trending health/wellness topics
│   │   │   ├── content_analyzer      → Analyze viral patterns
│   │   │   └── research_publisher    → Output to Research Pool
│   │   │
│   │   └── Industry News Team [Haiku]
│   │       ├── news_scanner          → Health/wellness industry news
│   │       ├── competitor_watcher    → Monitor competitor content
│   │       └── research_publisher    → Output to Research Pool
│   │
│   ├── Asset Generation Team [Sonnet + APIs]
│   │   ├── nano_banana_generator     → AI images (Gemini Nano Banana Pro)
│   │   ├── orshot_renderer           → Branded graphics (Orshot API)
│   │   ├── cope_transformer          → One asset → multiple formats
│   │   ├── pre_quality_scorer        → Pre-publish quality score (1-10)
│   │   └── asset_storage_agent       → Save to Asset Database
│   │
│   ├── Content Creation Teams
│   │   │
│   │   ├── Instagram Team [Sonnet]
│   │   │   ├── topic_selector        → Choose from Research Pool
│   │   │   ├── caption_writer        → Instagram-optimized copy
│   │   │   ├── hashtag_optimizer     → Platform-specific hashtags
│   │   │   ├── compliance_checker    → (SHARED)
│   │   │   ├── brand_validator       → (SHARED)
│   │   │   ├── image_assembler       → Match content with asset
│   │   │   └── queue_agent           → Send to approval queue
│   │   │
│   │   ├── LinkedIn Team [Sonnet]
│   │   │   ├── topic_selector
│   │   │   ├── post_writer           → Professional tone
│   │   │   ├── compliance_checker    → (SHARED)
│   │   │   ├── brand_validator       → (SHARED)
│   │   │   └── queue_agent
│   │   │
│   │   ├── Blog Team [Sonnet]
│   │   │   ├── topic_selector
│   │   │   ├── outline_writer        → Create structure
│   │   │   ├── content_writer        → Draft long-form
│   │   │   ├── geo_optimizer         → Structure for AI citation
│   │   │   ├── seo_optimizer         → Keywords, meta
│   │   │   ├── compliance_checker    → (SHARED)
│   │   │   ├── brand_validator       → (SHARED)
│   │   │   └── queue_agent
│   │   │
│   │   └── Email Team [Sonnet] (Klaviyo - Post-MVP)
│   │       └── ...
│   │
│   └── Publishing & Distribution
│       │
│       └── Publisher Team [Haiku]
│           ├── scheduler_agent       → Optimal timing per platform
│           ├── instagram_publisher   → Instagram Graph API
│           ├── email_publisher       → Klaviyo API
│           └── cross_poster          → COPE distribution
│
├── SALES DEPARTMENT
│   │
│   └── B2B Outreach Team [Sonnet]
│       ├── lead_researcher           → Find health food stores
│       ├── lead_qualifier            → Score/filter leads
│       ├── contact_enricher          → Get decision maker info
│       ├── outreach_drafter          → Personalized email draft
│       ├── compliance_checker        → (SHARED)
│       └── queue_agent               → Send to approval queue
│
├── COMPLIANCE DEPARTMENT (Post-MVP)
│   │
│   └── CleanMarket Team [Sonnet]
│       ├── competitor_scanner        → Find competitor content
│       ├── claim_extractor           → Parse health claims
│       ├── violation_detector        → Check against EU register
│       ├── evidence_collector        → Screenshot/archive
│       └── report_generator          → Weekly summary
│
└── ANALYTICS & LEARNING
    │
    └── Performance Team [Sonnet]
        ├── engagement_tracker        → Likes, comments, shares, saves
        ├── conversion_tracker        → Click-throughs, website visits
        ├── sales_attributor          → Connect output → revenue
        ├── post_quality_scorer       → Post-publish scoring
        ├── pattern_analyzer          → What content types work best
        └── feedback_loop_agent       → Feed insights to Strategy
```

### Shared/Reusable Agents

| Agent | Capability | Model | Used By |
|-------|------------|-------|---------|
| `compliance_checker` | EU Health Claims validation | Sonnet | All Content teams, Sales |
| `brand_validator` | Voice/style consistency | Sonnet | All Content teams |
| `queue_agent` | Send to IMAGO approval queue | Haiku | All teams |
| `shopify_data_agent` | Fetch product info via MCP | Haiku | Content, Sales |
| `research_publisher` | Output to Research Pool | Haiku | All Research teams |

### Quality Scoring System

#### Pre-Publish Score (AI-assessed, 1-10)

| Factor | Weight | Measured By |
|--------|--------|-------------|
| Compliance | 25% | EU Health Claims checker |
| Brand Voice Match | 20% | Voice guardian agent |
| Visual Quality | 15% | Image quality assessment |
| Platform Optimization | 15% | Hashtags, length, format fit |
| Engagement Prediction | 15% | AI prediction based on past data |
| Authenticity | 10% | Human feel vs AI-generic |

#### Post-Publish Score (Data-driven, 1-10)

| Factor | Weight | Data Source |
|--------|--------|-------------|
| Engagement Rate | 30% | Likes, comments, shares, saves / reach |
| Click-Through Rate | 25% | Link clicks / impressions |
| Conversion | 25% | Website visits → purchases attributed |
| Reach/Impressions | 10% | Total audience reached |
| Saves/Bookmarks | 10% | Long-term value indicator |

#### Feedback Loop

Post-publish scores feed back to:
- Strategy Team → Adjust campaign focus
- Asset Generation → Learn what visuals work
- Content Teams → Learn what topics/tones work
- Quality Scorer → Improve pre-publish predictions

### Campaign Types (AI-Driven Organic Marketing)

| Campaign Type | Description | Example for DAWO |
|---------------|-------------|------------------|
| **Evergreen Authority** | Always-on content establishing expertise | "Science of Lion's Mane" series |
| **Trend Hijacking** | Jump on viral topics with relevant angle | Link mushrooms to trending health topic |
| **COPE Campaigns** | One hero piece → 10+ derivative assets | Blog → carousel → LinkedIn → email |
| **Community Building** | Engage followers, UGC, stories | Customer spotlight, behind-the-scenes |
| **GEO Optimized** | Content designed to be cited by AI | FAQ-rich, structured, authoritative |
| **Seasonal/Event** | Tied to calendar moments | "Winter immunity", "New Year wellness" |
| **Educational Series** | Multi-part deep dives | "Mushroom Monday" weekly series |
| **Social Proof** | Reviews, testimonials, case studies | B2B retailer success stories |

### Team Definition Pattern (Following REDIS)

Each team will have a YAML definition:
```yaml
- id: "instagram_content"
  name: "Instagram Content Team"
  description: "Creates EU-compliant Instagram posts for DAWO"
  version: "1.0.0"
  status: "active"
  path: "teams/dawo/instagram_content"

  llm:
    provider: "anthropic"
    default_model: "claude-sonnet-4"
    model_overrides:
      queue_agent: "claude-haiku-4"

  stages:
    - id: "select"
      agent: "topic_selector"
      description: "Selects topic from research pool"
    - id: "write"
      agent: "caption_writer"
      description: "Drafts Instagram caption"
    - id: "hashtag"
      agent: "hashtag_optimizer"
      description: "Adds platform-optimized hashtags"
    - id: "comply"
      agent: "compliance_checker"
      description: "EU Health Claims validation"
    - id: "brand"
      agent: "brand_validator"
      description: "Voice and style check"
    - id: "image"
      agent: "image_assembler"
      description: "Matches content with asset from Asset DB"
    - id: "queue"
      agent: "queue_agent"
      description: "Sends to approval queue"

  config:
    research_pool: "research_pool_db"
    compliance_rules: "eu_health_claims.yaml"
    brand_voice: "dawo_brand.yaml"
    asset_db: "asset_database"
```

### Content Lifecycle with Auto-Publishing

```
1. RESEARCH
   └── Research Teams scan sources (Reddit, YouTube, PubMed, TikTok, News)
   └── Findings stored in Research Pool with topic tags

2. STRATEGY
   └── Strategy Team plans campaigns
   └── Campaign briefs stored in Campaign DB

3. GENERATION
   └── Content Team selects topic from Research Pool
   └── Asset Team generates/selects image
   └── Pre-publish quality scored (1-10)

4. QUEUE
   └── Combined content sent to Content Queue
   └── Status: PENDING_APPROVAL
   └── Suggested publish time

5. NOTIFICATION
   └── Discord: "5 items ready for review"

6. REVIEW (IMAGO Dashboard)
   └── Preview: Caption + Image + Hashtags
   └── Quality score displayed
   └── Compliance status
   └── Actions: Approve / Edit / Reject / Reschedule

7. APPROVED → SCHEDULED
   └── Status: SCHEDULED
   └── Publish time confirmed

8. AUTO-PUBLISH
   └── Publisher Team executes at scheduled time
   └── Instagram: Posts via Graph API
   └── Email: Triggers Klaviyo campaign
   └── Status: PUBLISHED

9. TRACK
   └── 24h, 48h, 7d engagement snapshots
   └── Conversion tracking (UTM parameters)
   └── Sales attribution (Shopify order tags)
   └── Post-publish quality score calculated

10. LEARN
    └── Performance data feeds back to Strategy
    └── Patterns stored for future optimization
```

### Databases

| Database | Purpose | Key Data |
|----------|---------|----------|
| **Research Pool** | Curated research findings | Topics, sources, insights, tags |
| **Asset Database** | Generated/stored assets | Images, quality scores, usage history, performance |
| **Content Queue** | Approval workflow | Pending, scheduled, published, rejected items |
| **Performance Database** | Analytics & learning | Per-post metrics, conversions, patterns |
| **Campaign Database** | Strategy tracking | Campaign definitions, performance, learnings |
| **Brand Identity Database** | Brand guidelines | Voice, visuals, compliance rules |

### Platform Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| IMAGO.ECO Dashboard | Primary UI, approval workflows | 90% - needs approval queue UI |
| Anthropic Claude API | LLM (Haiku/Sonnet/Opus 4.5) | Ready |
| Shopify MCP | Product data, sales attribution | Needs verification |
| Discord Webhooks | Notifications | Needs implementation |
| Instagram Graph API | Auto-publishing | Needs setup |
| Klaviyo API | Email automation | Post-MVP |
| Orshot API | Branded graphics (Canva import) | Needs setup |
| Nano Banana (Gemini) | AI image generation | Ready |
| YouTube Data API | Video research | Needs setup |
| PubMed API (Entrez) | Scientific research | Needs setup |

## User Journeys

### Journey 1: Even's Daily Supervisor Flow (Success Path)

**Opening Scene:**
It's Tuesday morning, 8:15 AM. Even is having coffee before heading to the warehouse to pack orders. His phone buzzes - a Discord notification: "🔔 DAWO Agents: 5 items ready for review (3 Instagram, 2 B2B outreach)"

**Rising Action:**
Even opens the IMAGO.ECO dashboard on his laptop. The Approval Queue shows:
- ✅ Instagram Post - Lion's Mane Focus (Quality: 8.5, COMPLIANT)
- ✅ Instagram Post - Chaga Morning Ritual (Quality: 9.0, COMPLIANT)
- ⚠️ Instagram Post - Maitake Benefits (Quality: 7.8, WARNING)
- ✅ B2B Outreach - Sunkost Oslo (Quality: 8.2, COMPLIANT)
- ✅ B2B Outreach - Life Majorstuen (Quality: 8.5, COMPLIANT)

He clicks the warning item. The compliance checker flagged "supports healthy metabolism" as borderline but acceptable. He reviews the full post, sees the generated image (lifestyle photo of morning tea via Nano Banana), and confirms the scheduled publish time (tomorrow 9:00 AM).

**Climax:**
Even batch-approves the 3 Instagram posts and 2 outreach emails in under 5 minutes. The posts are now SCHEDULED for auto-publishing at optimal times.

**Resolution:**
By 8:25 AM, Even is done. His "AI employees" did 3 hours of work while he slept. The content will auto-publish without him needing to do anything more. He feels the rhythm: agents propose, he approves, work gets done automatically.

---

### Journey 2: Research Pipeline Execution (Agent Journey)

**Opening Scene:**
Sunday 2:00 AM. The PubMed Research Team runs its weekly scan.

**Pipeline Execution:**
```
PUBMED RESEARCH TEAM [Sonnet] EXECUTING...

[pubmed_scanner] → Searching: "lion's mane cognition" AND "2025"
                → Found: 12 new studies since last scan

[abstract_harvester] → Collecting abstracts & metadata
                     → Extracted: Authors, journal, DOI, conclusions

[finding_summarizer] → Key finding: "Lion's mane showed significant
                       improvement in mild cognitive impairment in
                       12-week RCT (n=77, p<0.05)"

[claim_validator] → Cross-referencing with EU approved claims
                  → Note: Can cite study but NOT claim treatment

[research_publisher] → Adding to Research Pool
                     → Tags: #lions_mane, #cognition, #clinical_study
                     → Quality: 9.2 (peer-reviewed, recent, relevant)
```

**Resolution:**
Content teams now have fresh, validated scientific material to reference in upcoming posts.

---

### Journey 3: Content Generation & Auto-Publish (Agent Journey)

**Opening Scene:**
Monday 3:00 AM. The Instagram Content Team runs its daily generation cycle.

**Pipeline Execution:**
```
INSTAGRAM CONTENT TEAM [Sonnet] EXECUTING...

[topic_selector] → Checking Research Pool
                → Selected: Lion's Mane cognition study (score: 9.2)
                → Campaign context: "Science Series" (from Strategy)

[caption_writer] → Drafting Instagram caption
                → Tone: Warm, educational, Nordic simplicity
                → Length: 180 words + CTA

[hashtag_optimizer] → Adding hashtags
                    → #lionsmane #brainhealth #adaptogens #organiclife

[compliance_checker] → Scanning for EU Health Claims violations
                     → "supports mental clarity" → ✅ ALLOWED
                     → Citation included → ✅ GOOD
                     → Overall: COMPLIANT

[brand_validator] → Checking voice consistency
                  → Tone: ✅ Warm, educational
                  → No medicinal language: ✅
                  → DAWO personality: ✅

[image_assembler] → Requesting from Asset Team
                  → Nano Banana prompt: "Peaceful morning scene,
                    person with tea, soft natural light,
                    Scandinavian aesthetic, mushroom elements subtle"
                  → Image generated, quality score: 8.7

[queue_agent] → Sending to approval queue
              → Pre-publish quality score: 8.5
              → Suggested publish: Tuesday 9:00 AM (optimal engagement)
              → Status: PENDING_APPROVAL
```

**Tuesday 9:00 AM (After Approval):**
```
PUBLISHER TEAM [Haiku] EXECUTING...

[instagram_publisher] → Posting to Instagram Graph API
                      → Caption: [approved content]
                      → Image: [approved asset]
                      → Hashtags: [approved]
                      → Status: PUBLISHED
                      → Post ID: 12345678
```

**Tuesday + 24h:**
```
PERFORMANCE TEAM [Sonnet] COLLECTING...

[engagement_tracker] → Likes: 156, Comments: 23, Saves: 45, Reach: 2,340
[conversion_tracker] → Link clicks: 34, Website visits: 28
[sales_attributor] → Orders with UTM: 3 (Revenue: 1,450 NOK)
[post_quality_scorer] → Post-publish score: 8.9 (above prediction!)
[feedback_loop_agent] → Flagging "Science Series" as high performer
                      → Updating Strategy Team recommendations
```

---

### Journey 4: Compliance Rejection & Edit Flow

**Opening Scene:**
Friday afternoon. Even checks the dashboard and sees a rejected item.

**The Issue:**
```
❌ Blog Post - "How Lion's Mane Treats Brain Fog"
   COMPLIANCE: REJECTED
   Reason: "treats" implies medicinal claim (EC 1924/2006 violation)
   Flagged phrases:
   - "treats brain fog" → ❌ MEDICINAL CLAIM
   - "cures mental fatigue" → ❌ DISEASE REFERENCE
```

**Resolution Options:**
Even clicks to see AI-suggested rewrites:
- "treats brain fog" → "supports mental clarity"
- "cures mental fatigue" → "helps you feel refreshed"

He chooses Edit, accepts the suggestions, and the content re-validates as COMPLIANT. He approves and schedules for Monday.

---

### Journey Requirements Summary

| Journey | Key Capabilities Required |
|---------|---------------------------|
| **Supervisor Daily Flow** | Approval Queue UI, quality scores, batch actions, scheduling, Discord notifications |
| **Research Pipeline** | PubMed API, YouTube API, claim validation, Research Pool database |
| **Content & Auto-Publish** | Claude Sonnet, Nano Banana, Orshot, Instagram Graph API, scheduling |
| **Compliance Rejection** | Clear violation explanation, AI-suggested rewrites, re-validation |
| **Performance Tracking** | Engagement APIs, UTM tracking, Shopify attribution, feedback loop |

## Domain-Specific Requirements

### Regulatory Landscape

#### EU Health Claims Regulation (EC 1924/2006)

**Current State**: Zero approved health claims for DAWO mushroom products (Lion's Mane, Chaga, Shiitake, Maitake, Reishi, Cordyceps).

**Implications**:
- All marketing must operate in permissible "gray area" language
- Cannot make specific health claims without EU Register approval
- Rumored Shiitake claim pending - must monitor for activation opportunity

**Monitoring Requirement**: Weekly scraping of EU Register (no API available - web portal/PDF only)

**Gray Area Language Strategy**:
The compliance checker must distinguish between:
- ❌ **Prohibited**: "treats", "cures", "prevents", disease references, medicinal claims
- ⚠️ **Borderline**: "supports", "promotes", "contributes to" (context-dependent)
- ✅ **Permitted**: General wellness language, lifestyle references, citing studies (with links)

#### EU Novel Food Regulation

**Product Classification**:
| Product | Novel Food Status | Marketing Constraints |
|---------|-------------------|----------------------|
| Lion's Mane | Food | Can market as food product |
| Shiitake | Food | Can market as food product |
| Maitake | Food | Can market as food product |
| Chaga | Supplement only | Cannot market as food, supplement rules apply |
| Reishi | TBD | Verify before launch |
| Cordyceps | TBD | Verify before launch |

**Critical Rule**: Cannot market a supplement as a food. Compliance checker must know product → classification mapping and validate marketing accordingly.

#### EU AI Act (Effective August 2026)

**Article 50 Transparency Obligations**:
- Requires disclosure of AI-generated content in machine-readable format
- **Exemption applies**: Human-reviewed and approved content does not require labeling
- Since all DAWO content is human-approved before publication, no mandatory label required

**Decision**: Do not add AI disclosure labels unless regulations require it. Human-in-loop approval provides exemption.

#### Norwegian Authority (Mattilsynet)

**Context**: Prior enforcement history - DAWO was temporarily closed for non-compliance during EU regulation transition. This drives heightened compliance focus.

**Monitoring Requirement**: Active scanning of Mattilsynet.no for guidance updates, regulation changes, and new approved claims.

### Regulatory & Compliance Department (NEW)

Based on domain complexity, adding a dedicated department:

```
REGULATORY & COMPLIANCE DEPARTMENT [Sonnet]
│
├── EU Health Claims Team [Sonnet]
│   ├── register_monitor         → Weekly scrape of EU Register for new approvals
│   ├── claim_evaluator          → Assess gray area language permissibility
│   ├── approved_claims_db       → Maintain internal database of allowed claims
│   └── activation_alerter       → Notify when new claims available for DAWO products
│
├── Novel Food Compliance Team [Sonnet]
│   ├── catalogue_monitor        → Monitor Novel Food status changes
│   ├── classification_tracker   → Track food vs supplement status per product
│   ├── labeling_validator       → Verify labels match classification
│   └── regulation_scanner       → Scan for new Novel Food guidance
│
├── Mattilsynet Monitor Team [Haiku]
│   ├── mattilsynet_scanner      → Monitor Mattilsynet.no for updates
│   ├── guidance_extractor       → Extract and summarize new guidance docs
│   ├── impact_assessor          → Assess impact on DAWO operations [Sonnet]
│   └── alert_generator          → Create human review alerts
│
└── CleanMarket Team [Sonnet] (Evidence Collection Mode)
    ├── competitor_scanner       → Find competitor content (Instagram, web)
    ├── claim_extractor          → Parse health claims they're making
    ├── violation_detector       → Check against EU register + Novel Food
    ├── evidence_collector       → Screenshot, archive, timestamp
    ├── evidence_database        → Store with metadata, searchable
    └── report_generator         → Generate report ON DEMAND (human triggers)
```

**CleanMarket Operating Mode**: Evidence collection only. Human decides when to report to authorities.

### Technical Constraints

#### Instagram Algorithm & AI Content

**Research Findings**:
| Impact | Details |
|--------|---------|
| AI-labeled posts | 23-47% lower engagement |
| Purely AI-generated posts | Up to 80% reach reduction |
| Deepfake-style content | 60-80% reduction |
| Detection methods | C2PA/IPTC metadata, pattern recognition |

**Mitigation Strategy**:
- Use AI for drafts/ideation, human polish for final output
- Real product photos (not AI-generated mushroom images)
- Add authenticity scoring to quality system
- Mix AI efficiency with human authenticity markers

**Quality Scoring Update**: Add "AI Detectability Risk" factor (lower is better)

#### Progressive Auto-Publish System

**Phase 1: Simulated Auto-Publish (MVP)**
```
Score 9+ AND Compliance PASS → Status: "WOULD_AUTO_PUBLISH"
├── All posts still require human approval
├── Dashboard shows: "✅ Would have auto-published" badge
├── Track: How many "would auto" posts human approves without changes
└── Build trust data for Phase 2
```

**Phase 2: Real Auto-Publish (Post-Validation)**
```
User enables after seeing simulation accuracy
├── Score 9+ AND Compliance PASS → Auto-publishes
├── Lower scores still require human review
└── Kill switch: Disable instantly if issues arise
```

#### Data Handling & GDPR

- Performance tracking stores engagement metrics (aggregated, non-PII)
- Sales attribution connects posts to Shopify orders via UTM parameters
- Data retention policy: To be developed with legal guidance
- Privacy-compliant tracking configuration required

### Integration Requirements

| Integration | API Available? | Approach |
|-------------|---------------|----------|
| EU Health Claims Register | No | Weekly web scrape / PDF parse |
| Novel Food Catalogue | No | Weekly web scrape |
| Mattilsynet.no | No | Norwegian language web scrape |
| Instagram Graph API | Yes | Standard OAuth integration |
| PubMed (Entrez) | Yes | REST API |
| YouTube Data API | Yes | REST API |
| Scientific sources | N/A | Always include DOI/URL links |

### Risk Mitigations

| Risk | Impact | Mitigation | Owner |
|------|--------|------------|-------|
| Prohibited health claim published | Legal fines, reputation | Multi-layer compliance checking + human approval | Compliance Dept |
| AI content detected, reach penalized | 50%+ engagement loss | Authenticity scoring, human polish, real photos | Brand Identity Team |
| Novel Food misclassification | Product recall | Per-product classification database | Novel Food Team |
| Competitor complaint to authorities | Investigation | Proactive compliance audit trail | Regulatory Dept |
| New regulation missed | Enforcement action | Active monitoring of EU/Mattilsynet sources | Mattilsynet Monitor |
| Shiitake claim approved, not activated | Competitive disadvantage | Weekly register monitoring + activation workflow | Health Claims Team |

### B2B Competitive Positioning

| Value Proposition | Description |
|-------------------|-------------|
| **Regulatory Compliance** | One of few companies properly following EU Health Claims & Novel Food regulations |
| **100% European Supply Chain** | No geopolitical supply risk, aligned with EU food security priorities |
| **Clean Competition** | Can demonstrate competitor non-compliance with documented evidence |
| **Audit Trail** | Full documentation of compliance processes for retailer due diligence |

## Innovation & Novel Patterns

### Detected Innovation Areas

| Area | Innovation Level | Notes |
|------|------------------|-------|
| Multi-agent SMB automation | **Market trend** | Well-timed but not novel - 77% of SMBs adopting AI |
| EU Health Claims AI compliance | **Novel combination** | No existing tools combine AI content generation with EC 1924/2006 |
| CleanMarket competitor monitoring | **Novel application** | Systematic compliance-as-weapon approach unique in industry |
| Progressive auto-publish simulation | **Incremental innovation** | "WOULD_AUTO_PUBLISH" trust-building UX pattern |

### What Makes DAWO Novel

#### 1. First EU Health Claims-Aware AI Content System

**The Gap**: AI content tools exist. Compliance tools exist. But no tool combines:
- AI content generation (Claude)
- EU Health Claims validation (EC 1924/2006)
- Novel Food classification awareness
- Gray area language evaluation

Existing solutions focus on:
- FDA compliance (US-centric)
- Manufacturing/labeling automation
- General content generation without regulatory awareness

**DAWO's Approach**: Every piece of generated content flows through compliance checking before it reaches the approval queue. The compliance checker understands the difference between "treats brain fog" (prohibited) and "supports mental clarity" (permitted gray area).

**Validation Metrics**:
- False positive rate (flagging compliant content)
- False negative rate (missing violations)
- Target: <5% false positive, 0% false negative

#### 2. CleanMarket: Compliance as Competitive Weapon

**The Gap**: Companies monitor their own compliance. Regulators do enforcement. But no systematic tool exists for:
- Automated competitor content scanning
- Health claims extraction and classification
- Violation evidence collection with timestamps
- Report generation for regulatory submission

**DAWO's Approach**: Turn regulatory compliance from a cost center into a competitive advantage. Document competitor violations systematically, report strategically.

**Why This Matters**: In markets where 58% of inspected facilities have violations (per FDA data), compliant operators are disadvantaged against non-compliant competitors. CleanMarket levels the playing field.

**Validation Metrics**:
- Competitor coverage (% of market monitored)
- Violation detection accuracy
- Evidence quality (legally usable)

#### 3. Progressive Autonomy Through Simulation

**The Pattern**: Rather than binary "manual vs automated" publishing:
1. **Phase 1**: System tags posts as "WOULD_AUTO_PUBLISH" but requires approval
2. **Human sees**: Track record of what the system would have done
3. **Trust builds**: After N successful predictions, enable real auto-publish
4. **Kill switch**: Instant revert if issues arise

**Why This Matters**: Addresses the core trust problem with AI automation. User sees proof before taking the leap.

### Market Context

**AI Agent Market**: Growing from $7.84B (2025) to $52.62B (2030) at 46.3% CAGR. Multi-agent systems trending with CrewAI, AutoGen, LangGraph.

**Supplement Compliance**: AI compliance monitoring market at $1.8B (2024) → $5.2B (2030). But focused on manufacturing, not content generation.

**EU Regulatory Environment**: Health claims regulation (EC 1924/2006) strictly enforced. No approved claims for functional mushrooms creates content challenge that DAWO's system addresses.

### Risk Mitigation for Innovations

| Innovation | Risk | Mitigation |
|------------|------|------------|
| EU compliance checker | False negatives allow violations | Multi-layer checking, human approval, continuous refinement |
| CleanMarket | Legal exposure from competitor monitoring | Evidence collection only, human decides reporting |
| Auto-publish simulation | User never enables real auto-publish | Clear metrics dashboard, gradual trust building |

### Product Differentiation (DAWO Biohack Products)

While this PRD focuses on the DAWO.ECO system, the product differentiation supports content strategy:

| Differentiator | Marketing Angle |
|----------------|-----------------|
| **Ultrasonic-assisted extraction** | Higher bioavailability, better chitin breakdown, preserves compounds |
| **100% organic** | Clean label, no additives, pure mushroom |
| **100% European supply chain** | Geopolitical stability, EU quality standards |
| **No additives** | Transparency, purity focus |

These differentiators feed into Research → Content pipeline for authentic, science-backed content.

## Market Expansion Strategy

### Current Focus: Norway

- **Language**: Norwegian
- **Platforms**: Instagram (primary), LinkedIn (B2B)
- **Regulatory Body**: Mattilsynet
- **Currency**: NOK

### Phase 2: Nordic Expansion

| Market | Language | Regulatory Body | Notes |
|--------|----------|-----------------|-------|
| Sweden | Swedish | Livsmedelsverket | Largest Nordic market |
| Denmark | Danish | Fødevarestyrelsen | Strong organic culture |
| Finland | Finnish | Ruokavirasto | Health-conscious market |

**System Requirements**:
- Multi-language content generation
- Per-market hashtag/keyword research
- Localized brand voice variations
- Market-specific performance tracking

### Phase 3: EU Expansion

- Same EU regulations (EC 1924/2006, Novel Food)
- Different languages and platforms
- Local influencer/retailer networks
- Currency handling (EUR vs local)

### Strategy Team Responsibility

The Marketing Strategy Team will handle:
- Market entry prioritization
- Language/localization planning
- Platform strategy per market
- Budget allocation across markets

Content teams receive market context from Strategy before generation.

## Google Workspace Integration

DAWO.ECO has Google Workspace available. Integration opportunities:

| Service | Use Case | Priority |
|---------|----------|----------|
| **Google Drive** | Asset storage, document management | MVP |
| **Google Calendar** | Content calendar, scheduling visibility | MVP |
| **Gmail** | B2B outreach sending (with human approval) | MVP |
| **Google Docs** | Long-form content drafts, collaborative editing | Growth |
| **Google Sheets** | Performance data export, reporting | Growth |

**Integration Approach**:
- Publisher Team can send approved B2B emails via Gmail API
- Calendar sync for scheduled content visibility
- Drive integration for asset storage (alternative to dedicated Asset DB)
- Performance data export to Sheets for manual analysis

## Internal AI Operations System - Technical Requirements

### System Architecture Overview

DAWO.ECO is an **Internal AI Operations System** built on the **IMAGO.ECO platform**. It operates as a multi-agent system designed for a single operator (one-person business) with future multi-tenant capabilities.

```
┌─────────────────────────────────────────────────────────────────┐
│                        IMAGO.ECO PLATFORM                       │
│  (Multi-tenant foundation, DAWO is first customer/test case)    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   DAWO.ECO   │    │  Future Co.  │    │  Future Co.  │      │
│  │   Customer   │    │   Customer   │    │   Customer   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                                                       │
│  ┌──────┴─────────────────────────────────────────────────┐    │
│  │              DAWO Agent Departments                     │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │    │
│  │  │Marketing│ │  Sales  │ │Compliance│ │Analytics│       │    │
│  │  │  Dept   │ │  Dept   │ │  Dept   │ │  Dept   │       │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     EXTERNAL INTEGRATIONS                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Claude  │ │Instagram│ │ Shopify │ │ Google  │ │ Orshot  │  │
│  │   API   │ │Graph API│ │   MCP   │ │Workspace│ │   API   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Technical Architecture Decisions

#### Multi-Tenancy Model

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **IMAGO.ECO** | Multi-tenant | Platform serves multiple customers |
| **DAWO.ECO** | First tenant | Test case, validates platform |
| **Data isolation** | Per-customer databases | Compliance, security |
| **Configuration** | Per-customer teams/agents | Customizable workflows |

#### Permission Model

**MVP (Single Operator)**:
- One user (Even) with full access
- No complex RBAC needed
- Agent permissions via approval workflow

**Future (Team Features)**:
| Role | Permissions |
|------|-------------|
| Owner | Full access, settings, billing |
| Editor | Create/edit content, approve |
| Viewer | View dashboards, reports only |

#### Scheduling & Orchestration

**Trigger Types**:

| Trigger | Use Case | Example |
|---------|----------|---------|
| **Scheduled (cron)** | Regular scans, batch generation | Research teams at 2 AM |
| **Event-driven** | Reactive processing | New research → content generation |
| **Manual** | On-demand execution | User triggers specific team |
| **Time-based** | Scheduled publishing | Approved content publishes at 9 AM |

**Agent Execution Schedule (Default)**:

| Team | Schedule | Trigger Type |
|------|----------|--------------|
| Reddit Research | Daily 2 AM | Scheduled |
| YouTube Research | Weekly Sunday 3 AM | Scheduled |
| PubMed Research | Weekly Sunday 4 AM | Scheduled |
| TikTok Research | Daily 2:30 AM | Scheduled |
| Industry News | Daily 6 AM | Scheduled |
| Instagram Content | Daily 3 AM | Scheduled |
| LinkedIn Content | Mon/Wed/Fri 4 AM | Scheduled |
| Blog Content | Weekly Monday 5 AM | Scheduled |
| B2B Outreach | Daily 7 AM | Scheduled |
| Publisher | As scheduled per post | Time-based |
| Performance Tracker | 24h/48h/7d post-publish | Event-driven |
| Compliance Monitor | Weekly | Scheduled |
| CleanMarket | Weekly | Scheduled |

#### Data Architecture

**Google Workspace as Primary Storage**:

| Data Type | Storage | Format |
|-----------|---------|--------|
| **Assets** | Google Drive | Images, videos, PDFs |
| **Research Pool** | IMAGO DB | Structured JSON |
| **Content Queue** | IMAGO DB | Structured records |
| **Performance Data** | IMAGO DB + Google Sheets export | Metrics, reports |
| **Compliance Records** | IMAGO DB | Audit trail |
| **Brand Guidelines** | Google Drive (docs) + IMAGO DB (queryable) | YAML/JSON |
| **Templates** | Orshot | Design files |

**Google Drive Folder Structure**:
```
DAWO.ECO/
├── Assets/
│   ├── Generated/        # AI-generated images
│   ├── Orshot/           # Branded graphics from Orshot
│   ├── Product Photos/   # Real product images
│   └── Archive/          # Used assets with performance data
├── Content/
│   ├── Drafts/           # Long-form content drafts
│   ├── Published/        # Archive of published content
│   └── Rejected/         # Rejected content for learning
├── Brand/
│   ├── Guidelines/       # Brand voice, visual identity docs
│   └── Templates/        # Canva source files (import to Orshot)
├── Reports/
│   ├── Performance/      # Weekly/monthly performance exports
│   └── Compliance/       # CleanMarket evidence, reports
└── Research/
    └── Sources/          # Downloaded PDFs, transcripts
```

#### Deployment Model

**Self-Hosted (Development & Production)**:

| Component | Hosting | Notes |
|-----------|---------|-------|
| IMAGO.ECO Platform | Self-hosted server | Primary runtime |
| Agent Execution | Self-hosted (Vertex-compatible) | Can migrate to cloud |
| Database | Self-hosted PostgreSQL | IMAGO DB |
| Asset Storage | Google Drive | External service |
| LLM | Anthropic Claude API | External service |
| Graphics | Orshot API | External service |

**Cloud Migration Path**:
- Architecture designed for Vertex Agent Engine compatibility
- Can migrate to Google Cloud if self-hosted becomes unstable
- Containerized deployment enables portability

### Integration Specifications

#### Full Integration List

**MVP Integrations**:

| Integration | Purpose | API Type | Auth |
|-------------|---------|----------|------|
| **Anthropic Claude** | LLM (Haiku/Sonnet/Opus) | REST | API Key |
| **Instagram Graph** | Auto-publishing | REST/OAuth | OAuth 2.0 |
| **Shopify** | Product data, sales | MCP | OAuth 2.0 |
| **Discord** | Notifications | Webhooks | Webhook URL |
| **Google Drive** | Asset storage | REST | OAuth 2.0 |
| **Google Calendar** | Scheduling visibility | REST | OAuth 2.0 |
| **Gmail** | B2B email sending | REST | OAuth 2.0 |
| **Orshot** | Branded graphics | REST | API Key |
| **Nano Banana (Gemini)** | AI image generation | REST | API Key |
| **PubMed (Entrez)** | Scientific research | REST | API Key (optional) |
| **YouTube Data** | Video research | REST | API Key |

**Post-MVP Integrations**:

| Integration | Purpose | Phase |
|-------------|---------|-------|
| Klaviyo | Email automation | Growth |
| TikTok API | Research (if available) | Growth |
| LinkedIn API | Publishing | Growth |
| Google Sheets | Reporting | Growth |

#### Orshot Integration

**MVP Tier**: Starter ($30/month, 3,000 renders)
**Growth Tier**: Higher tiers available up to $349/month (200K renders)

| Feature | Starter (MVP) | Growth |
|---------|---------------|--------|
| Renders | 3,000/month | Scales to 200K |
| Video support | Yes (included) | Yes |
| **Canva Import** | Yes (direct, ~30 sec) | Yes |
| API access | Full (all tiers) | Full |
| Team seats | Unlimited | Unlimited |
| Dynamic URLs | Yes | Yes |

**Why Orshot:**
- Direct Canva import preserves fonts, colors, spacing
- Best value: $30/mo for 3,000 renders ($10 per 1K)
- Design in Canva (familiar), import to Orshot (API)
- Easy platform switching - Canva remains source of truth
- All features included on all tiers (no feature gating)

**Integration Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│                     IMAGO.ECO Platform                       │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐   │
│  │   Canva          │    │     Asset Generation Team     │   │
│  │   (External)     │───►│                              │   │
│  │                  │    │  ┌──────────────────────┐    │   │
│  │  - Design        │    │  │ orshot_renderer      │────┼───┼──► Orshot API
│  │  - Export        │    │  └──────────────────────┘    │   │
│  │  - Import        │    │                              │   │
│  └──────────────────┘    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Workflow**:
1. User designs templates in Canva (source of truth)
2. Import to Orshot (~30 seconds, preserves design)
3. `orshot_renderer` agent calls API with dynamic content
4. Generated assets saved to Google Drive
5. Content teams assemble posts with assets
6. If platform switch needed: re-import Canva templates to new service

### Language & Localization Strategy

**MVP**: Norwegian only (home market)

**Expansion Strategy**:

| Phase | Markets | Languages | Approach |
|-------|---------|-----------|----------|
| MVP | Norway | Norwegian | Full local content |
| Nordic | Sweden, Denmark, Finland | English bridge → local if data supports | Test engagement |
| EU | Germany, Netherlands, etc. | English primary | Local for top performers |

**System Support**:
- Claude handles multi-language generation
- Orshot templates per language (or dynamic text via Canva)
- Per-market performance tracking
- Strategy Team decides language investment based on data

### Implementation Considerations

#### MVP Technical Scope

| Component | MVP Scope | Deferred |
|-----------|-----------|----------|
| User management | Single user | Team features, RBAC |
| Content types | Instagram posts, B2B emails | Blog, LinkedIn, video |
| Research sources | All 5: Reddit, YouTube, Instagram, News, PubMed | TikTok publishing |
| Publishing | Instagram auto-publish | Multi-platform |
| Analytics | Basic engagement tracking | Advanced attribution, ML insights |
| Compliance | EU Health Claims checker + CleanMarket (evidence mode) | Real auto-publish |

#### Technical Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Instagram API rate limits | Publishing delays | Queue management, spread posting |
| Claude API costs | Budget overrun | Haiku for high-volume, Opus for critical only |
| Self-hosted downtime | Missed schedules | Monitoring, cloud fallback plan |
| Orshot API changes | Template rework | Canva source of truth, re-import if needed |
| Google Workspace limits | Storage issues | Archive old assets, clean up |

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP with comprehensive research foundation

The MVP prioritizes building a complete research-to-publish pipeline that delivers high-quality, compliant content from day one. Rather than starting minimal and iterating, this approach invests upfront in the research infrastructure that enables quality output.

**Rationale:**
- Content quality depends on research quality - skipping research sources produces generic content
- EU compliance requires evidence-backed claims - research sources provide that foundation
- B2B outreach requires personalized insights - research enables meaningful personalization
- CleanMarket provides competitive intelligence from launch

**Resource Requirements:**
- Single operator (Even) with full approval authority
- IMAGO.ECO platform (90% complete) as foundation
- External services: Anthropic Claude, Orshot Starter ($30/mo, 3,000 renders), Google Workspace

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

| Journey | MVP Support |
|---------|-------------|
| Supervisor Daily Flow | Full - Approval queue, batch actions, scheduling |
| Research Pipeline | Full - All 5 sources (Reddit, YouTube, Instagram, News, PubMed) |
| Content & Auto-Publish | Full - Instagram with simulated auto-publish |
| Compliance Rejection | Full - Clear explanations, AI rewrites, re-validation |
| Performance Tracking | Basic - Engagement metrics, UTM tracking |
| B2B Outreach | Full - Lead research, personalized drafts, Gmail sending |
| CleanMarket | Full - Evidence collection mode (human-triggered reports) |

**Must-Have Capabilities:**

| Category | Capabilities |
|----------|--------------|
| **Research** | Reddit monitoring, YouTube research, Instagram trends, Industry news, PubMed scientific |
| **Content** | Instagram post generation, branded graphics (Orshot), compliance checking |
| **Publishing** | Instagram Graph API auto-publish, scheduling, queue management |
| **Sales** | B2B lead research, personalized outreach drafts, Gmail integration |
| **Compliance** | EU Health Claims checker, Novel Food validation, gray area language evaluation |
| **CleanMarket** | Competitor scanning, violation detection, evidence collection, on-demand reports |
| **Infrastructure** | IMAGO approval queue, Discord notifications, Google Workspace integration |

### Post-MVP Features

**Phase 2 (Growth):**

| Feature | Value | Dependency |
|---------|-------|------------|
| LinkedIn publishing | Professional B2B presence | LinkedIn API integration |
| Advanced analytics | ML-powered content insights | Sufficient performance data |
| Orshot higher tier | More renders, advanced features | Volume growth |
| Nordic market prep | Swedish, Danish, Finnish content | Validated Norwegian success |
| Blog content team | Long-form SEO content | Proven short-form pipeline |

**Phase 3 (Expansion):**

| Feature | Value | Dependency |
|---------|-------|------------|
| Klaviyo email automation | Automated email campaigns | Email list growth |
| Nordic/EU market launch | Geographic expansion | Localization infrastructure |
| Mobile approval app | On-the-go approvals | Proven desktop workflow |
| Real auto-publish | Trust-based autonomy | Simulation data validates accuracy |
| Video content | Reels, TikTok | Content team maturity |

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Full research pipeline complexity | Longer MVP timeline | Prioritize Reddit + PubMed first, add others incrementally |
| Multiple API integrations | Integration failures | Test each in isolation, graceful degradation |
| Claude API costs at scale | Budget overrun | Haiku for scanning, Sonnet for writing, Opus sparingly |
| Self-hosted reliability | Missed schedules | Monitoring alerts, cloud fallback architecture |

**Market Risks:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| EU compliance checker accuracy | Legal exposure | Conservative gray area evaluation, human approval always |
| Instagram algorithm changes | Reach reduction | Authenticity scoring, human polish, real photos |
| Competitor response to CleanMarket | Retaliation reports | Proactive compliance audit trail |

**Resource Risks:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Single operator bottleneck | Approval backlog | Batch approval UI, quality thresholds, scheduled review times |
| IMAGO platform gaps | MVP delays | Track in imago-platform-gaps.md, prioritize P1 items |
| Learning curve | Slow adoption | Start with familiar workflows, iterate based on usage |

### Scope Boundaries

**In Scope (MVP):**
- Norwegian market only
- Instagram + B2B email channels
- All 5 research sources (Reddit, YouTube, Instagram, News, PubMed)
- CleanMarket evidence collection
- Simulated auto-publish (builds trust data)
- Basic performance tracking

**Explicitly Out of Scope (MVP):**
- Multi-language content
- LinkedIn/TikTok/Blog publishing
- Real auto-publish (requires trust data)
- Advanced ML analytics
- Mobile app
- Team/RBAC features

### Success Gate for Phase 2

Move to Phase 2 when MVP achieves:
- 7+ compliant posts/week for 4 consecutive weeks
- 20+ B2B leads researched/week for 2 consecutive weeks
- <5% false positive compliance rate
- Simulated auto-publish accuracy >95%
- First B2B sale from agent-sourced lead

## Functional Requirements

### Research & Intelligence

- **FR1:** System can monitor Reddit for mushroom-related discussions and trending topics
- **FR2:** System can search YouTube for mushroom supplement content and extract key insights
- **FR3:** System can monitor Instagram hashtags and competitor accounts for trend detection
- **FR4:** System can aggregate industry news from configured sources
- **FR5:** System can query PubMed for scientific research on mushroom compounds
- **FR6:** System can validate research findings against EU Health Claims compliance
- **FR7:** System can store research items in a searchable Research Pool with metadata
- **FR8:** System can score research items for content potential and relevance

### Content Generation

- **FR9:** System can generate Instagram post captions in Norwegian using brand voice guidelines
- **FR10:** System can generate branded graphics via Orshot API (with Canva template import)
- **FR11:** System can generate AI images via Nano Banana (Gemini) for visual content
- **FR12:** System can combine research insights with product data to create content drafts
- **FR13:** System can apply EU Health Claims compliance checking to all generated content
- **FR14:** System can suggest compliant rewrites when content fails compliance
- **FR15:** System can score content quality including AI detectability risk
- **FR16:** System can tag content with "WOULD_AUTO_PUBLISH" status when score ≥9 and compliance passes

### B2B Sales & Outreach

- **FR17:** System can research potential B2B retail partners using configured criteria
- **FR18:** System can extract business information from public sources for lead enrichment
- **FR19:** System can generate personalized B2B outreach drafts referencing lead-specific insights
- **FR20:** System can queue approved outreach emails for sending via Gmail API
- **FR21:** System can track B2B lead status through pipeline stages

### Compliance & Regulatory

- **FR22:** System can evaluate content against EU Health Claims Regulation (EC 1924/2006)
- **FR23:** System can classify language as prohibited, borderline, or permitted
- **FR24:** System can validate content against Novel Food product classifications
- **FR25:** System can monitor EU Health Claims Register for new approved claims
- **FR26:** System can monitor Novel Food Catalogue for status changes
- **FR27:** System can monitor Mattilsynet.no for Norwegian regulatory updates
- **FR28:** System can alert operator when new claims become available for DAWO products

### CleanMarket (Competitor Intelligence)

- **FR29:** System can scan competitor Instagram accounts and websites for health claims
- **FR30:** System can extract and classify competitor health claims
- **FR31:** System can detect potential EU Health Claims violations in competitor content
- **FR32:** System can collect evidence (screenshots, timestamps, URLs) of violations
- **FR33:** System can store evidence in searchable database with metadata
- **FR34:** Operator can generate compliance violation reports on demand

### Approval & Publishing

- **FR35:** Operator can view pending content in approval queue with quality scores
- **FR36:** Operator can approve, reject, or edit content items
- **FR37:** Operator can batch approve multiple content items
- **FR38:** Operator can schedule approved content for future publication
- **FR39:** System can publish approved content to Instagram via Graph API at scheduled time
- **FR40:** System can send Discord notifications when approvals are needed
- **FR41:** System can send Discord notifications when scheduled posts are published

### Performance Tracking

- **FR42:** System can collect engagement metrics (likes, comments, shares, saves, reach) from Instagram
- **FR43:** System can track click-through rates via UTM parameters
- **FR44:** System can attribute Shopify sales to specific posts via UTM correlation
- **FR45:** System can calculate post-publish quality scores based on engagement
- **FR46:** System can feed performance data back to content scoring algorithms

### Asset & Brand Management

- **FR47:** System can store generated assets in Google Drive with organized folder structure
- **FR48:** System can retrieve product data from Shopify via MCP
- **FR49:** System can apply brand voice guidelines to all generated content
- **FR50:** System can track asset usage history and performance correlation

### System Administration

- **FR51:** Operator can configure agent execution schedules
- **FR52:** Operator can manually trigger specific teams or agents
- **FR53:** Operator can view agent execution logs and status
- **FR54:** System can sync content calendar to Google Calendar
- **FR55:** System can gracefully degrade when external APIs are unavailable

## Non-Functional Requirements

### Performance

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| Approval queue load time | < 3 seconds | Operator efficiency during daily review |
| Content generation (per post) | < 60 seconds | Reasonable batch processing |
| Research scan (per source) | < 5 minutes | Acceptable for scheduled background tasks |
| Instagram publish latency | < 30 seconds from trigger | Timely scheduled posting |
| Compliance check | < 10 seconds per item | Fast feedback during generation |

### Security

| Requirement | Specification |
|-------------|---------------|
| API key storage | Encrypted at rest, never logged in plaintext |
| Data in transit | TLS 1.3 for all external API calls |
| Access control | Single operator with full access (MVP); RBAC ready for Growth |
| Session management | Secure token-based auth, 24-hour expiry |
| Audit logging | All approval actions logged with timestamp and user |
| GDPR compliance | B2B contact data erasable on request, no personal data retention beyond business need |

### Reliability

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| Scheduled publish success rate | > 99% | Auto-publishing must be dependable |
| Agent execution success rate | > 95% | Failed runs should be rare |
| System availability (core functions) | 99% uptime | Acceptable for internal tool |
| Data backup frequency | Daily | Protect research pool, performance data |
| Graceful degradation | System continues with available APIs | If one API fails, others still work |

### Integration

| Requirement | Specification |
|-------------|---------------|
| API timeout handling | Max 30 seconds, then fail gracefully with retry queue |
| Rate limit compliance | Respect all API rate limits, implement backoff |
| API version tracking | Document all API versions, alert on deprecation notices |
| Webhook reliability | Retry failed Discord notifications 3x with exponential backoff |
| External service monitoring | Health checks for all critical APIs (Instagram, Gmail, Orshot) |

### Compliance

| Requirement | Specification |
|-------------|---------------|
| EU Health Claims accuracy | 100% - no prohibited claims published |
| Compliance audit trail | Full history of all compliance checks with reasoning |
| AI-generated content disclosure | Compliant with EU AI Act Article 50 (human approval = exemption) |
| Data retention | Research data: 2 years; Performance data: indefinite; B2B contacts: until relationship ends |
| Evidence preservation | CleanMarket evidence immutable once collected |

### Operational

| Requirement | Specification |
|-------------|---------------|
| Monitoring & alerting | Discord alerts for: failed publishes, compliance warnings, API errors |
| Log retention | 30 days operational logs, 1 year audit logs |
| Recovery time objective (RTO) | < 4 hours for critical functions |
| Recovery point objective (RPO) | < 24 hours (daily backups) |
| Cost monitoring | Monthly API spend tracking, alerts at 80% budget |

