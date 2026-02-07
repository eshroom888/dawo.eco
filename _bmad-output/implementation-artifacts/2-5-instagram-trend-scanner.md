# Story 2.5: Instagram Trend Scanner

Status: done

---

## Story

As an **operator**,
I want Instagram hashtags and competitors monitored,
So that I stay aware of trending content and competitor activity.

---

## Acceptance Criteria

1. **Given** the Instagram scanner is scheduled (daily 2:30 AM)
   **When** it executes
   **Then** it monitors hashtags: #lionsmane, #mushroomsupplements, #adaptogens, #biohacking
   **And** it monitors configured competitor accounts
   **And** it collects top posts from last 24 hours

2. **Given** a trending post is found
   **When** the harvester processes it
   **Then** it extracts: caption text, hashtags, engagement metrics, account name
   **And** it does NOT download or store images (privacy/copyright)
   **And** it captures content themes and messaging patterns

3. **Given** competitor content is detected
   **When** it contains health claims
   **Then** it flags for potential CleanMarket review (Epic 6 integration point)
   **And** it still enters Research Pool as trend data

4. **Given** Instagram API is unavailable
   **When** retry middleware exhausts attempts
   **Then** the scan is marked INCOMPLETE and queued for next cycle
   **And** previous research remains available

---

## Tasks / Subtasks

- [x] Task 1: Create Instagram scanner agent structure (AC: #1, #2)
  - [x] 1.1 Create `teams/dawo/scanners/instagram/` directory structure
  - [x] 1.2 Create `__init__.py` with complete exports and `__all__` list
  - [x] 1.3 Create `agent.py` with `InstagramScanner` class
  - [x] 1.4 Create `prompts.py` with theme extraction prompts (uses generate tier)
  - [x] 1.5 Create `tools.py` with Instagram Graph API tools
  - [x] 1.6 Create `config.py` with `InstagramScannerConfig` dataclass
  - [x] 1.7 Create `schemas.py` with `RawInstagramPost`, `HarvestedPost`, `TrendAnalysis` schemas

- [x] Task 2: Implement Instagram Graph API client (AC: #1, #4)
  - [x] 2.1 Create `InstagramClient` class in `tools.py`
  - [x] 2.2 Accept access token via dependency injection (Business/Creator account required)
  - [x] 2.3 Implement `search_hashtag(hashtag: str, limit: int) -> list[dict]` using Hashtag Search endpoint
  - [x] 2.4 Implement `get_recent_media(ig_user_id: str, limit: int) -> list[dict]` for competitor accounts
  - [x] 2.5 Implement `get_media_details(media_id: str) -> dict` for engagement metrics
  - [x] 2.6 Add rate limiting (200 calls/hour for Business accounts)
  - [x] 2.7 Wrap all API calls with retry middleware (Story 1.5)

- [x] Task 3: Implement scanner stage (AC: #1)
  - [x] 3.1 Create `scan()` method that processes configured hashtags and competitor accounts
  - [x] 3.2 Default hashtags: #lionsmane, #mushroomsupplements, #adaptogens, #biohacking
  - [x] 3.3 Filter results by: published date (last 24 hours)
  - [x] 3.4 Deduplicate results by media ID
  - [x] 3.5 Return list of `RawInstagramPost` objects
  - [x] 3.6 Log scan statistics: hashtags searched, accounts monitored, posts found

- [x] Task 4: Implement harvester stage (AC: #2)
  - [x] 4.1 Create `InstagramHarvester` class
  - [x] 4.2 Accept `InstagramClient` via dependency injection
  - [x] 4.3 Implement `harvest(raw_posts: list[RawInstagramPost]) -> list[HarvestedPost]`
  - [x] 4.4 For each post, fetch: full caption, all hashtags, engagement metrics (likes, comments)
  - [x] 4.5 Extract account name, account type (business/creator/personal)
  - [x] 4.6 Do NOT download or store images/videos (privacy/copyright compliance)
  - [x] 4.7 Rate limit API calls per Instagram Graph API guidelines

- [x] Task 5: Implement theme extractor (AC: #2)
  - [x] 5.1 Create `ThemeExtractor` class
  - [x] 5.2 Use `tier="generate"` (Sonnet) for quality theme analysis
  - [x] 5.3 Implement `extract_themes(caption: str, hashtags: list[str]) -> ThemeResult`
  - [x] 5.4 Identify: content themes (educational, promotional, lifestyle), messaging patterns
  - [x] 5.5 Detect: product mentions, influencer indicators, brand collaboration hints
  - [x] 5.6 Return structured ThemeResult with themes, patterns, and confidence

- [x] Task 6: Implement health claim detector (AC: #3)
  - [x] 6.1 Create `HealthClaimDetector` class
  - [x] 6.2 Use `tier="generate"` (Sonnet) for accurate claim detection
  - [x] 6.3 Implement `detect_claims(caption: str) -> ClaimDetectionResult`
  - [x] 6.4 Identify potential health claims using patterns from EU compliance rules
  - [x] 6.5 Classify claims: treatment, prevention, enhancement, general wellness
  - [x] 6.6 Set `requires_cleanmarket_review=True` if claims detected
  - [x] 6.7 Include claim text, confidence score, and classification

- [x] Task 7: Implement transformer stage (AC: #2, #3)
  - [x] 7.1 Create `InstagramTransformer` class
  - [x] 7.2 Accept `ThemeExtractor` and `HealthClaimDetector` via dependency injection
  - [x] 7.3 Implement `transform(harvested: list[HarvestedPost]) -> list[TransformedResearch]`
  - [x] 7.4 Map Instagram fields to Research Pool schema:
        - `source`: "instagram"
        - `title`: first 100 chars of caption or "Instagram post from @{account}"
        - `content`: full caption + theme analysis summary
        - `url`: Instagram post permalink
        - `tags`: auto-generate from hashtags + detected themes
        - `source_metadata`: {account, account_type, likes, comments, hashtag_source, is_competitor, detected_claims}
        - `created_at`: post timestamp
  - [x] 7.5 Set `cleanmarket_flag=True` if health claims detected (AC: #3)
  - [x] 7.6 Sanitize content: remove emojis from tags, truncate if > 10,000 chars

- [x] Task 8: Implement validator stage (AC: #3)
  - [x] 8.1 Create `InstagramValidator` class
  - [x] 8.2 Accept `EUComplianceChecker` via dependency injection (from Story 1.2)
  - [x] 8.3 Implement `validate(items: list[TransformedResearch]) -> list[ValidatedResearch]`
  - [x] 8.4 Call compliance checker on caption content
  - [x] 8.5 Set `compliance_status` based on checker result (COMPLIANT, WARNING, REJECTED)
  - [x] 8.6 Preserve `cleanmarket_flag` for Epic 6 integration
  - [x] 8.7 Log validation statistics: passed, warned, rejected, flagged for CleanMarket

- [x] Task 9: Integrate with Research Publisher (AC: #2, #3)
  - [x] 9.1 Accept `ResearchPublisher` via dependency injection (from Story 2.1)
  - [x] 9.2 Accept `ResearchItemScorer` via dependency injection (from Story 2.2)
  - [x] 9.3 Implement `publish_results(validated: list[ValidatedResearch]) -> list[ResearchItem]`
  - [x] 9.4 Score each item before publishing (boost for high engagement, trending hashtags)
  - [x] 9.5 Publish to Research Pool via publisher
  - [x] 9.6 Return created ResearchItem list with IDs

- [x] Task 10: Create orchestrated pipeline (AC: #1, #2, #3)
  - [x] 10.1 Create `InstagramResearchPipeline` class
  - [x] 10.2 Accept all stage components via dependency injection
  - [x] 10.3 Implement `execute() -> PipelineResult`
  - [x] 10.4 Chain stages: scan -> harvest -> extract_themes -> detect_claims -> transform -> validate -> score -> publish
  - [x] 10.5 Track and return statistics: hashtags_searched, accounts_monitored, posts_found, themes_extracted, claims_detected, cleanmarket_flagged, published
  - [x] 10.6 Handle partial failures: continue pipeline even if some posts fail

- [x] Task 11: Implement graceful degradation (AC: #4)
  - [x] 11.1 Wrap pipeline execution in try/catch
  - [x] 11.2 On API failure (after retries), mark scan as INCOMPLETE
  - [x] 11.3 Log failure details for debugging
  - [x] 11.4 Queue for next scheduled run (via ARQ job queue)
  - [x] 11.5 Ensure existing Research Pool data remains intact
  - [x] 11.6 Handle rate limit exhaustion separately (wait until reset, notify operator)

- [x] Task 12: Register in team_spec.py (AC: #1)
  - [x] 12.1 Add `InstagramScanner` as RegisteredAgent with tier="scan"
  - [x] 12.2 Add `ThemeExtractor` as RegisteredAgent with tier="generate"
  - [x] 12.3 Add `HealthClaimDetector` as RegisteredAgent with tier="generate"
  - [x] 12.4 Add `InstagramHarvester` as RegisteredService
  - [x] 12.5 Add `InstagramTransformer` as RegisteredService
  - [x] 12.6 Add `InstagramValidator` as RegisteredService
  - [x] 12.7 Add `InstagramResearchPipeline` as RegisteredService with capability="instagram_research"
  - [x] 12.8 Ensure all components are injectable via Team Builder

- [x] Task 13: Create configuration file (AC: #1)
  - [x] 13.1 Create `config/dawo_instagram_scanner.json`
  - [x] 13.2 Define hashtags: ["lionsmane", "mushroomsupplements", "adaptogens", "biohacking"]
  - [x] 13.3 Define competitor_accounts: [] (operator configures)
  - [x] 13.4 Define filters: hours_back=24
  - [x] 13.5 Define schedule: cron expression for daily 2:30 AM
  - [x] 13.6 Define max_posts_per_hashtag: 25
  - [x] 13.7 Define max_posts_per_account: 10
  - [x] 13.8 Add Instagram access token placeholder (loaded from env vars)

- [x] Task 14: Create comprehensive unit tests
  - [x] 14.1 Test InstagramClient hashtag search and media detail methods
  - [x] 14.2 Test scanner filtering (date, deduplication)
  - [x] 14.3 Test harvester data extraction (no image storage verification)
  - [x] 14.4 Test ThemeExtractor prompt and response parsing
  - [x] 14.5 Test HealthClaimDetector classification accuracy
  - [x] 14.6 Test transformer field mapping and CleanMarket flagging
  - [x] 14.7 Test validator compliance integration
  - [x] 14.8 Test pipeline orchestration
  - [x] 14.9 Test graceful degradation on API failure
  - [x] 14.10 Test rate limit handling
  - [x] 14.11 Mock Instagram API responses for all tests

- [x] Task 15: Create integration tests
  - [x] 15.1 Test full pipeline with mocked Instagram API
  - [x] 15.2 Test Research Pool insertion (with test database)
  - [x] 15.3 Test scoring integration
  - [x] 15.4 Test retry middleware integration
  - [x] 15.5 Test CleanMarket flagging propagation
  - [x] 15.6 Test LLM theme/claim extraction with mock responses

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Harvester-Framework], [project-context.md#Code-Organization]

This is the **THIRD scanner** in the Harvester Framework - it MUST follow the exact pattern established by Reddit Scanner (Story 2.3) and YouTube Scanner (Story 2.4).

**Harvester Framework Pipeline (Extended for Instagram):**
```
[Scanner] -> [Harvester] -> [Theme Extractor] -> [Claim Detector] -> [Transformer] -> [Validator] -> [Scorer] -> [Publisher] -> [Research Pool]
     |           |                  |                   |                  |              |            |           |
   scan()    harvest()        extract_themes()    detect_claims()    transform()    validate()    score()    publish()
   tier=scan  tier=scan        tier=generate       tier=generate       tier=scan      tier=scan   tier=scan   tier=scan
```

**Key Differences from YouTube Scanner:**
- Instagram has TWO LLM stages: ThemeExtractor AND HealthClaimDetector (both use `tier="generate"`)
- CleanMarket integration point for flagging competitor health claims (Epic 6)
- NO image/video storage - text and metadata only (privacy/copyright compliance)
- Daily schedule (vs YouTube's weekly) - more frequent trend monitoring

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Directory-Structure]

```
teams/dawo/
├── scanners/
│   ├── reddit/                        # EXISTS from Story 2.3
│   │   └── ...
│   ├── youtube/                       # EXISTS from Story 2.4
│   │   └── ...
│   └── instagram/                     # CREATE THIS MODULE
│       ├── __init__.py                # Export all public types
│       ├── agent.py                   # InstagramScanner main class
│       ├── prompts.py                 # ThemeExtractor + HealthClaimDetector prompts
│       ├── tools.py                   # InstagramClient, API tools
│       ├── config.py                  # InstagramScannerConfig
│       ├── schemas.py                 # RawInstagramPost, HarvestedPost, ThemeResult, ClaimDetectionResult
│       ├── harvester.py               # InstagramHarvester
│       ├── theme_extractor.py         # ThemeExtractor (tier=generate)
│       ├── claim_detector.py          # HealthClaimDetector (tier=generate)
│       ├── transformer.py             # InstagramTransformer
│       ├── validator.py               # InstagramValidator
│       └── pipeline.py                # InstagramResearchPipeline
├── research/                          # Exists from Story 2.1
│   ├── models.py                      # ResearchItem, ResearchSource
│   ├── repository.py                  # ResearchPoolRepository
│   ├── publisher.py                   # ResearchPublisher
│   └── scoring/                       # Exists from Story 2.2
│       └── scorer.py                  # ResearchItemScorer

config/
└── dawo_instagram_scanner.json        # CREATE: Scanner configuration

tests/teams/dawo/
└── test_scanners/
    ├── test_reddit/                   # EXISTS from Story 2.3
    ├── test_youtube/                  # EXISTS from Story 2.4
    └── test_instagram/                # CREATE THIS
        ├── __init__.py
        ├── conftest.py                # Fixtures, mocks
        ├── test_client.py             # InstagramClient tests
        ├── test_scanner.py            # Scanner stage tests
        ├── test_harvester.py          # Harvester stage tests
        ├── test_theme_extractor.py    # Theme extraction tests
        ├── test_claim_detector.py     # Health claim detection tests
        ├── test_transformer.py        # Transformer stage tests
        ├── test_validator.py          # Validator stage tests
        ├── test_pipeline.py           # Full pipeline tests
        └── test_integration.py        # Integration with Research Pool
```

### Instagram Graph API Integration

**Source:** [prd.md#Integration-Requirements], [architecture.md#External-Integration-Points]

**API Details:**
- **Base URL:** `https://graph.facebook.com/v19.0`
- **Auth:** User Access Token (Business/Creator Account required)
- **Rate Limit:** 200 calls/hour for Business accounts

**CRITICAL: Instagram Graph API Limitations:**
- Hashtag Search requires Business Discovery or approved use case
- Cannot access personal accounts (only Business/Creator)
- Cannot download/store media (only metadata and text)
- Must comply with Meta Platform Terms of Service

**Hashtag Search Endpoint:**
```python
# tools.py
class InstagramClient:
    """Instagram Graph API client.

    Accepts access token via dependency injection - NEVER loads from file.
    CRITICAL: Requires Business/Creator account permissions.
    """

    RATE_LIMIT_PER_HOUR = 200

    def __init__(self, config: InstagramClientConfig, retry_middleware: RetryMiddleware):
        """Accept config via injection from Team Builder."""
        self._config = config
        self._retry = retry_middleware
        self._session: Optional[aiohttp.ClientSession] = None
        self._calls_this_hour = 0
        self._hour_start = datetime.now(timezone.utc)

    @with_retry(RetryConfig(max_attempts=3, backoff_base=2.0))
    async def search_hashtag(
        self,
        hashtag: str,
        limit: int = 25
    ) -> list[dict]:
        """Search for recent media with hashtag.

        Args:
            hashtag: Hashtag without # (e.g., "lionsmane")
            limit: Max results (Instagram caps at 30)

        Returns:
            List of media objects

        Raises:
            RateLimitError: If hourly limit exceeded
        """
        self._check_rate_limit()

        # First, get hashtag ID
        hashtag_url = f"{self.BASE_URL}/ig_hashtag_search"
        hashtag_params = {
            "user_id": self._config.business_account_id,
            "q": hashtag,
            "access_token": self._config.access_token
        }
        hashtag_data = await self._api_call(hashtag_url, hashtag_params)

        if not hashtag_data.get("data"):
            return []

        hashtag_id = hashtag_data["data"][0]["id"]

        # Then get recent media for hashtag
        media_url = f"{self.BASE_URL}/{hashtag_id}/recent_media"
        media_params = {
            "user_id": self._config.business_account_id,
            "fields": "id,caption,permalink,timestamp,like_count,comments_count,media_type",
            "limit": limit,
            "access_token": self._config.access_token
        }
        return await self._api_call(media_url, media_params)
```

**Competitor Account Monitoring:**
```python
async def get_user_media(
    self,
    username: str,
    limit: int = 10
) -> list[dict]:
    """Get recent media from a business/creator account.

    Uses Business Discovery to access other business accounts.

    Args:
        username: Instagram username (without @)
        limit: Max posts to retrieve

    Returns:
        List of media objects with caption, metrics
    """
    self._check_rate_limit()

    url = f"{self.BASE_URL}/{self._config.business_account_id}"
    params = {
        "fields": f"business_discovery.username({username}){{media.limit({limit}){{id,caption,permalink,timestamp,like_count,comments_count,media_type}}}}",
        "access_token": self._config.access_token
    }
    return await self._api_call(url, params)
```

### Theme Extractor (LLM Stage)

**Source:** [epics.md#Story-2.5], [project-context.md#LLM-Tier-Assignment]

```python
# theme_extractor.py
from dataclasses import dataclass

@dataclass
class ThemeResult:
    """Result from theme extraction."""
    content_type: str  # educational, promotional, lifestyle, testimonial
    messaging_patterns: list[str]  # e.g., "question hook", "before/after", "product showcase"
    detected_products: list[str]  # Product/brand mentions
    influencer_indicators: bool  # Paid partnership, affiliate hints
    key_topics: list[str]  # e.g., "cognition", "energy", "dosage"
    confidence_score: float

class ThemeExtractor:
    """LLM-powered theme extraction from Instagram captions.

    Uses tier="generate" (Sonnet) for quality analysis.
    """

    def __init__(self, llm_client: LLMClient):
        """Accept LLM client via injection."""
        self._llm = llm_client

    async def extract_themes(
        self,
        caption: str,
        hashtags: list[str],
        account_name: str
    ) -> ThemeResult:
        """Extract themes and patterns from Instagram post.

        Args:
            caption: Full post caption text
            hashtags: List of hashtags used
            account_name: Instagram account name

        Returns:
            ThemeResult with themes, patterns, and topics
        """
        # See prompts.py for the full extraction prompt
        ...
```

**prompts.py:**
```python
# prompts.py
"""System prompts for Instagram theme and claim extraction.

Uses tier="generate" (Sonnet) for quality analysis.
"""

THEME_EXTRACTION_PROMPT = """
You are a social media analyst extracting themes from mushroom supplement Instagram content.

POST CONTEXT:
- Account: @{account_name}
- Hashtags: {hashtags}
- Caption length: {caption_length} chars

TASK:
Analyze this Instagram caption and extract:

1. CONTENT TYPE (one of):
   - educational: Informative content about benefits, usage, science
   - promotional: Direct product promotion, sales messaging
   - lifestyle: Personal stories, daily routines, aesthetic content
   - testimonial: User experiences, reviews, before/after claims

2. MESSAGING PATTERNS (identify any):
   - question_hook: Starts with engaging question
   - before_after: Transformation narrative
   - product_showcase: Direct product featuring
   - science_reference: Cites studies or research
   - personal_story: First-person narrative
   - call_to_action: Link in bio, shop now, etc.

3. DETECTED PRODUCTS/BRANDS (list any mentioned)

4. INFLUENCER INDICATORS (true/false):
   - Contains: #ad, #sponsored, #partner, "gifted", "paid partnership"
   - Or affiliate language: "use code", "discount link"

5. KEY TOPICS (3-7 from):
   lions_mane, chaga, reishi, cordyceps, shiitake, maitake,
   cognition, energy, immunity, focus, sleep, stress, dosage,
   morning_routine, workout, productivity, wellness

CAPTION:
{caption}

Respond in JSON format:
{{
    "content_type": "...",
    "messaging_patterns": ["...", "..."],
    "detected_products": ["...", "..."],
    "influencer_indicators": true/false,
    "key_topics": ["...", "..."],
    "confidence_score": 0.0-1.0
}}
"""
```

### Health Claim Detector (LLM Stage - CleanMarket Integration)

**Source:** [epics.md#Story-2.5], [epics.md#Epic-6-CleanMarket]

**CRITICAL:** This is the integration point with CleanMarket (Epic 6). Flagged posts will be available for competitor violation analysis.

```python
# claim_detector.py
from dataclasses import dataclass
from enum import Enum

class ClaimCategory(Enum):
    TREATMENT = "treatment"      # "treats", "cures", disease references
    PREVENTION = "prevention"    # "prevents", "protects against"
    ENHANCEMENT = "enhancement"  # "boosts", "enhances", "improves"
    GENERAL_WELLNESS = "wellness"  # General health, lifestyle claims

@dataclass
class DetectedClaim:
    """A detected health claim from content."""
    claim_text: str  # The exact phrase
    category: ClaimCategory
    confidence: float  # 0.0-1.0
    severity: str  # high, medium, low (based on EU regulation risk)

@dataclass
class ClaimDetectionResult:
    """Result from health claim detection."""
    claims_detected: list[DetectedClaim]
    requires_cleanmarket_review: bool  # True if any claims detected
    overall_risk_level: str  # none, low, medium, high
    summary: str  # Brief description for CleanMarket queue

class HealthClaimDetector:
    """LLM-powered health claim detection for CleanMarket integration.

    Uses tier="generate" (Sonnet) for accurate claim detection.
    Flags competitor content containing health claims for Epic 6 review.
    """

    def __init__(self, llm_client: LLMClient, compliance_patterns: dict):
        """Accept LLM client and compliance patterns via injection."""
        self._llm = llm_client
        self._patterns = compliance_patterns  # From dawo_compliance_rules.json

    async def detect_claims(
        self,
        caption: str,
        account_name: str,
        is_competitor: bool
    ) -> ClaimDetectionResult:
        """Detect potential health claims in Instagram caption.

        Args:
            caption: Full post caption text
            account_name: Instagram account name
            is_competitor: Whether this is a monitored competitor

        Returns:
            ClaimDetectionResult with detected claims and flags
        """
        ...
```

**prompts.py (claim detection):**
```python
HEALTH_CLAIM_DETECTION_PROMPT = """
You are an EU Health Claims Regulation expert analyzing Instagram content for potential violations.

REGULATORY CONTEXT:
- EC 1924/2006 prohibits health claims on food/supplements unless explicitly authorized
- Zero approved health claims exist for functional mushrooms (lion's mane, chaga, reishi, etc.)
- Prohibited language: "treats", "cures", "prevents" disease, medical terminology

POST CONTEXT:
- Account: @{account_name}
- Is Competitor: {is_competitor}

TASK:
Scan this caption for health claims and classify each:

CLAIM CATEGORIES:
1. TREATMENT: Claims the product treats/cures conditions
   Examples: "treats brain fog", "cures fatigue", "heals inflammation"
   Severity: HIGH

2. PREVENTION: Claims the product prevents conditions
   Examples: "prevents cognitive decline", "protects against disease"
   Severity: HIGH

3. ENHANCEMENT: Claims the product improves body functions
   Examples: "boosts immunity", "enhances cognition", "improves focus"
   Severity: MEDIUM

4. GENERAL WELLNESS: Vague wellness language
   Examples: "supports wellbeing", "for your health journey"
   Severity: LOW

CAPTION:
{caption}

Respond in JSON format:
{{
    "claims_detected": [
        {{"claim_text": "exact phrase", "category": "treatment|prevention|enhancement|wellness", "confidence": 0.0-1.0, "severity": "high|medium|low"}}
    ],
    "requires_cleanmarket_review": true/false,
    "overall_risk_level": "none|low|medium|high",
    "summary": "Brief description for CleanMarket queue"
}}

Return empty claims_detected array if no health claims found.
"""
```

### Privacy & Copyright Compliance (CRITICAL)

**Source:** [epics.md#Story-2.5], Meta Platform Terms

**DO NOT store:**
- Images or videos from Instagram posts
- User profile pictures
- Any media content

**DO store:**
- Caption text (for analysis only)
- Hashtags used
- Engagement metrics (public data)
- Account name (public data)
- Post permalink (for reference)
- Extracted themes and detected claims

```python
# schemas.py
@dataclass
class HarvestedPost:
    """Instagram post data - TEXT AND METADATA ONLY.

    CRITICAL: Do NOT add image_url, media_data, or any image storage.
    This is intentional for privacy/copyright compliance.
    """
    media_id: str
    permalink: str
    caption: str
    hashtags: list[str]
    likes: int
    comments: int
    media_type: str  # IMAGE, VIDEO, CAROUSEL - for stats only, not storage
    account_name: str
    account_type: str  # business, creator
    timestamp: datetime
    is_competitor: bool
    # NO image_url field - intentionally excluded
```

### Configuration Schema

**Source:** [project-context.md#Configuration-Loading]

```python
# config.py
from dataclasses import dataclass, field

@dataclass
class InstagramClientConfig:
    """Instagram API credentials - loaded from environment variables."""
    access_token: str
    business_account_id: str

@dataclass
class InstagramScannerConfig:
    """Scanner configuration - loaded from config file via injection."""
    hashtags: list[str] = field(default_factory=lambda: [
        "lionsmane",
        "mushroomsupplements",
        "adaptogens",
        "biohacking",
        "functionalmushrooms"
    ])
    competitor_accounts: list[str] = field(default_factory=list)  # Operator configures
    hours_back: int = 24
    max_posts_per_hashtag: int = 25
    max_posts_per_account: int = 10
```

**config/dawo_instagram_scanner.json:**
```json
{
  "hashtags": [
    "lionsmane",
    "mushroomsupplements",
    "adaptogens",
    "biohacking",
    "functionalmushrooms"
  ],
  "competitor_accounts": [],
  "hours_back": 24,
  "max_posts_per_hashtag": 25,
  "max_posts_per_account": 10,
  "schedule": {
    "cron": "30 2 * * *",
    "timezone": "Europe/Oslo"
  }
}
```

### Integration with Existing Components

**Source:** [2-1-research-pool-database-storage.md], [2-2-research-item-scoring-engine.md], [1-2-eu-compliance-checker-validator.md]

**Story 2.1 - Research Pool:**
```python
from teams.dawo.research import (
    ResearchItem,
    ResearchSource,
    ComplianceStatus,
    ResearchPublisher,
    TransformedResearch
)
```

**Story 2.2 - Scoring Engine:**
```python
from teams.dawo.research.scoring import (
    ResearchItemScorer,
    ScoringResult
)
```

**Story 1.2 - EU Compliance Checker:**
```python
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ComplianceResult
)
```

**Story 1.5 - Retry Middleware:**
```python
from teams.dawo.middleware.retry import (
    RetryMiddleware,
    with_retry,
    RetryConfig
)
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment], [project-context.md#Code-Review-Checklist]

**UNIQUE to Instagram Scanner:** This pipeline has THREE different tiers:
- `InstagramScanner`, `InstagramHarvester`, `InstagramTransformer`, `InstagramValidator`: `tier="scan"` (Haiku)
- `ThemeExtractor`: `tier="generate"` (Sonnet) - required for quality theme analysis
- `HealthClaimDetector`: `tier="generate"` (Sonnet) - required for accurate claim detection

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- `claude-haiku`, `claude-sonnet`, `claude-opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="instagram_scanner",
    agent_class=InstagramScanner,
    capabilities=["instagram_research", "research_scanning", "trend_monitoring"],
    tier="scan"  # Maps to Haiku at runtime
)

RegisteredAgent(
    name="theme_extractor",
    agent_class=ThemeExtractor,
    capabilities=["theme_extraction", "content_analysis"],
    tier="generate"  # Maps to Sonnet at runtime
)

RegisteredAgent(
    name="health_claim_detector",
    agent_class=HealthClaimDetector,
    capabilities=["claim_detection", "compliance_screening"],
    tier="generate"  # Maps to Sonnet at runtime - REQUIRED for accuracy
)
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [2-3-reddit-research-scanner.md], [2-4-youtube-research-scanner.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="scan"` or `tier="generate"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| SQLAlchemy reserved word fix | Use `source_metadata` not `metadata` |
| Add logging to exception handlers | All exceptions logged before re-raising |
| Extract magic numbers to constants | `HOURS_BACK = 24`, `MAX_POSTS_PER_HASHTAG = 25`, etc. |
| TDD approach | Write tests first for each task |
| Unit tests with mocking | Mock Instagram API for all tests |
| Mock patterns: async vs sync | `ResearchItemScorer.calculate_score()` is sync - use `MagicMock` |
| Pipeline return value handling | Track batch vs individual publish counts |
| Rate limiting implementation | Track calls per hour for Instagram's limit |
| Graceful degradation | Return INCOMPLETE on API failure, PARTIAL on item failures |
| Integration tests separate | Create test_integration.py with conftest.py fixtures |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], [architecture.md#Anti-Patterns]

1. **NEVER load config directly** - Accept via injection
2. **NEVER make direct API calls without retry wrapper**
3. **NEVER use LLM model names** - Use tier system
4. **NEVER swallow exceptions without logging**
5. **NEVER store Instagram images/videos** - Text and metadata only

### Exports Template (MUST FOLLOW)

**Source:** [project-context.md#Module-Exports]

```python
# teams/dawo/scanners/instagram/__init__.py
"""Instagram Trend Scanner for DAWO research intelligence pipeline."""

from .agent import InstagramScanner
from .tools import InstagramClient, RateLimitTracker
from .config import InstagramClientConfig, InstagramScannerConfig
from .schemas import (
    RawInstagramPost,
    HarvestedPost,
    ThemeResult,
    DetectedClaim,
    ClaimDetectionResult,
    ClaimCategory,
    ScanResult,
    PipelineResult
)
from .harvester import InstagramHarvester
from .theme_extractor import ThemeExtractor
from .claim_detector import HealthClaimDetector
from .transformer import InstagramTransformer
from .validator import InstagramValidator
from .pipeline import InstagramResearchPipeline

__all__ = [
    # Main agent
    "InstagramScanner",
    # Clients
    "InstagramClient",
    "RateLimitTracker",
    # Config
    "InstagramClientConfig",
    "InstagramScannerConfig",
    # Schemas
    "RawInstagramPost",
    "HarvestedPost",
    "ThemeResult",
    "DetectedClaim",
    "ClaimDetectionResult",
    "ClaimCategory",
    "ScanResult",
    "PipelineResult",
    # Pipeline stages
    "InstagramHarvester",
    "ThemeExtractor",
    "HealthClaimDetector",
    "InstagramTransformer",
    "InstagramValidator",
    "InstagramResearchPipeline",
]
```

### Test Fixtures

**Source:** [2-4-youtube-research-scanner.md#Test-Fixtures]

```python
# tests/teams/dawo/test_scanners/test_instagram/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

@pytest.fixture
def mock_hashtag_search_response():
    """Mock Instagram Graph API hashtag search response."""
    return {
        "data": [
            {
                "id": "17841563789012345",
                "caption": "Starting my morning with lion's mane coffee! #lionsmane #morningroutine",
                "permalink": "https://www.instagram.com/p/ABC123/",
                "timestamp": "2026-02-05T08:00:00+0000",
                "like_count": 1500,
                "comments_count": 45,
                "media_type": "IMAGE"
            }
        ]
    }

@pytest.fixture
def mock_competitor_media_response():
    """Mock Instagram Business Discovery response."""
    return {
        "business_discovery": {
            "media": {
                "data": [
                    {
                        "id": "17841563789012346",
                        "caption": "Our lion's mane extract boosts your brain power! Shop now! #sponsored",
                        "permalink": "https://www.instagram.com/p/DEF456/",
                        "timestamp": "2026-02-05T10:00:00+0000",
                        "like_count": 3200,
                        "comments_count": 89,
                        "media_type": "IMAGE"
                    }
                ]
            }
        }
    }

@pytest.fixture
def mock_instagram_client(mock_hashtag_search_response, mock_competitor_media_response):
    """Mock InstagramClient for testing without API calls."""
    client = AsyncMock(spec=InstagramClient)
    client.search_hashtag.return_value = mock_hashtag_search_response["data"]
    client.get_user_media.return_value = mock_competitor_media_response["business_discovery"]["media"]["data"]
    return client

@pytest.fixture
def scanner_config():
    """Test scanner configuration."""
    return InstagramScannerConfig(
        hashtags=["lionsmane", "adaptogens"],
        competitor_accounts=["competitor_brand"],
        hours_back=24,
        max_posts_per_hashtag=10,
        max_posts_per_account=5
    )
```

### CleanMarket Integration Point (Epic 6)

**Source:** [epics.md#Epic-6-CleanMarket]

When `HealthClaimDetector` flags content:
1. `cleanmarket_flag=True` is set on the Research Pool item
2. `source_metadata.detected_claims` contains claim details
3. Epic 6 (Story 6.5-6.7) will query flagged items for violation analysis
4. Evidence collection (Story 6.8) can retrieve post via permalink

```python
# In transformer.py
if claim_result.requires_cleanmarket_review:
    research_item.cleanmarket_flag = True
    research_item.source_metadata["detected_claims"] = [
        {
            "text": claim.claim_text,
            "category": claim.category.value,
            "severity": claim.severity
        }
        for claim in claim_result.claims_detected
    ]
    research_item.source_metadata["cleanmarket_summary"] = claim_result.summary
```

### Project Structure Notes

- **Third scanner**: Follows pattern established by Reddit (2.3) and YouTube (2.4)
- **Two LLM stages**: ThemeExtractor and HealthClaimDetector (both tier="generate")
- **CleanMarket integration**: Flags competitor health claims for Epic 6
- **Privacy-first**: NO image/video storage - text and metadata only
- **Daily schedule**: More frequent than YouTube (weekly) for trend monitoring
- **Follows Harvester Framework**: scan -> harvest -> extract -> detect -> transform -> validate -> publish
- **Integrates with**: Research Pool (2.1), Scoring Engine (2.2), EU Compliance (1.2), Retry Middleware (1.5)

### References

- [Source: epics.md#Story-2.5] - Original story requirements
- [Source: architecture.md#Harvester-Framework] - Pipeline pattern
- [Source: architecture.md#External-Integration-Points] - Instagram integration
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology
- [Source: prd.md#Integration-Requirements] - Instagram Graph API specs
- [Source: 2-1-research-pool-database-storage.md] - Research Pool integration
- [Source: 2-2-research-item-scoring-engine.md] - Scoring integration
- [Source: 2-3-reddit-research-scanner.md] - Pattern reference
- [Source: 2-4-youtube-research-scanner.md] - Pattern reference (FOLLOW THIS)
- [Source: 1-2-eu-compliance-checker-validator.md] - Compliance integration
- [Source: 1-5-external-api-retry-middleware.md] - Retry middleware integration
- [Source: epics.md#Epic-6-CleanMarket] - CleanMarket integration point

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No debug issues encountered

### Completion Notes List

1. **All 134 tests passing** - test breakdown: claim_detector(12), client(21), harvester(7), integration(20), pipeline(9), scanner(15), theme_extractor(8), transformer(26), validator(16) = 134 total
2. **Followed YouTube Scanner pattern** - Maintained consistency with Story 2.4
3. **TWO LLM stages** - ThemeExtractor and HealthClaimDetector both use tier="generate"
4. **CleanMarket integration** - Competitor health claims flagged in source_metadata
5. **Privacy compliance** - NO image/video storage, text and metadata only
6. **Rate limiting** - 200 calls/hour tracking via RateLimitTracker
7. **Graceful degradation** - INCOMPLETE status on API failure, RATE_LIMITED on limit exhaustion
8. **All components registered** - 3 agents and 4 services in team_spec.py
9. **Code review fixes applied** - Added test_transformer.py and test_validator.py, fixed type hints in validator.py and tools.py

### File List

**Implementation Files (teams/dawo/scanners/instagram/):**
- `__init__.py` - Module exports with complete `__all__` list
- `agent.py` - InstagramScanner main agent class
- `config.py` - InstagramClientConfig, InstagramScannerConfig dataclasses
- `schemas.py` - RawInstagramPost, HarvestedPost, ThemeResult, ClaimDetectionResult, PipelineResult
- `tools.py` - InstagramClient, RateLimitTracker, exceptions
- `prompts.py` - THEME_EXTRACTION_PROMPT, HEALTH_CLAIM_DETECTION_PROMPT
- `harvester.py` - InstagramHarvester for metadata extraction
- `theme_extractor.py` - ThemeExtractor (tier=generate)
- `claim_detector.py` - HealthClaimDetector (tier=generate)
- `transformer.py` - InstagramTransformer for Research Pool schema conversion
- `validator.py` - InstagramValidator for EU compliance checking
- `pipeline.py` - InstagramResearchPipeline orchestrator

**Configuration Files:**
- `config/dawo_instagram_scanner.json` - Scanner configuration with schedule

**Test Files (tests/teams/dawo/test_scanners/test_instagram/):**
- `__init__.py` - Test package init
- `conftest.py` - Shared test fixtures
- `test_client.py` - InstagramClient tests
- `test_scanner.py` - Scanner stage tests
- `test_harvester.py` - Harvester stage tests
- `test_theme_extractor.py` - ThemeExtractor tests
- `test_claim_detector.py` - HealthClaimDetector tests
- `test_transformer.py` - Transformer stage tests
- `test_validator.py` - Validator stage tests
- `test_pipeline.py` - Pipeline orchestration tests
- `test_integration.py` - Integration with Research Pool

**Modified Files:**
- `teams/dawo/team_spec.py` - Added InstagramScanner registrations
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - Story status tracking
