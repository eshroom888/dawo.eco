# Story 2.6: Industry News Scanner

Status: done

---

## Story

As an **operator**,
I want health/wellness industry news aggregated,
So that I can respond to industry developments in content.

---

## Acceptance Criteria

1. **Given** the news scanner is scheduled (daily 6 AM)
   **When** it executes
   **Then** it scans configured RSS feeds and news sources
   **And** it searches for: functional mushrooms, adaptogens, supplements industry, EU regulations
   **And** it collects articles from last 24 hours

2. **Given** a news article is found
   **When** the harvester processes it
   **Then** it extracts: headline, summary, source, publish date, URL
   **And** it categorizes: product news, regulatory, research, competitor

3. **Given** regulatory news is detected (EU, Mattilsynet)
   **When** it mentions health claims or novel food
   **Then** it's flagged high priority for operator attention
   **And** it scores 8+ automatically

4. **Given** a news API/RSS feed is unavailable
   **When** retry middleware exhausts attempts
   **Then** the scan is marked INCOMPLETE and queued for next cycle
   **And** previous research remains available

---

## Tasks / Subtasks

- [x] Task 1: Create news scanner agent structure (AC: #1, #2)
  - [x] 1.1 Create `teams/dawo/scanners/news/` directory structure
  - [x] 1.2 Create `__init__.py` with complete exports and `__all__` list
  - [x] 1.3 Create `agent.py` with `NewsScanner` class
  - [x] 1.4 Create `prompts.py` with news categorization prompts (uses scan tier, rule-based)
  - [x] 1.5 Create `tools.py` with RSS/feed parser tools
  - [x] 1.6 Create `config.py` with `NewsScannerConfig` dataclass
  - [x] 1.7 Create `schemas.py` with `RawNewsArticle`, `HarvestedArticle`, `NewsCategory` schemas

- [x] Task 2: Implement news fetching client (AC: #1, #4)
  - [x] 2.1 Create `NewsFeedClient` class in `tools.py`
  - [x] 2.2 Support RSS/Atom feed parsing using `feedparser` library
  - [x] 2.3 Implement `fetch_feed(feed_url: str, hours_back: int) -> list[RawNewsArticle]`
  - [x] 2.4 Implement keyword filtering during fetch
  - [x] 2.5 Add timeout and connection error handling
  - [x] 2.6 Wrap all fetches with retry middleware (Story 1.5)

- [x] Task 3: Implement scanner stage (AC: #1)
  - [x] 3.1 Create `scan()` method that processes configured feed URLs
  - [x] 3.2 Configure default feeds: NutraIngredients, Nutraceuticals World, EU regulatory feeds
  - [x] 3.3 Default keywords: "functional mushrooms", "adaptogens", "supplements", "EU regulations", "health claims", "novel food", "Mattilsynet"
  - [x] 3.4 Filter results by: published date (last 24 hours)
  - [x] 3.5 Deduplicate results by URL
  - [x] 3.6 Return list of `RawNewsArticle` objects
  - [x] 3.7 Log scan statistics: feeds processed, articles found, filtered count

- [x] Task 4: Implement harvester stage (AC: #2)
  - [x] 4.1 Create `NewsHarvester` class
  - [x] 4.2 Accept `NewsFeedClient` via dependency injection
  - [x] 4.3 Implement `harvest(raw_articles: list[RawNewsArticle]) -> list[HarvestedArticle]`
  - [x] 4.4 For each article, extract: full headline, summary/description, source name, publish date, URL
  - [x] 4.5 Clean HTML tags from content using `beautifulsoup4`
  - [x] 4.6 Handle encoding issues gracefully
  - [x] 4.7 Log extraction statistics

- [x] Task 5: Implement news categorizer (AC: #2, #3)
  - [x] 5.1 Create `NewsCategorizer` class
  - [x] 5.2 Use `tier="scan"` - rule-based categorization, no LLM needed
  - [x] 5.3 Implement `categorize(article: HarvestedArticle) -> CategoryResult`
  - [x] 5.4 Define categories enum: REGULATORY, PRODUCT_NEWS, RESEARCH, COMPETITOR, GENERAL
  - [x] 5.5 Regulatory detection patterns: "EU", "FDA", "Mattilsynet", "health claims", "novel food", "regulation", "compliance"
  - [x] 5.6 Product news patterns: "launch", "new product", "announces", brand names
  - [x] 5.7 Research patterns: "study", "research", "clinical trial", "findings"
  - [x] 5.8 Competitor patterns: configured competitor brand names
  - [x] 5.9 Return category with confidence score and is_regulatory flag

- [x] Task 6: Implement priority scorer (AC: #3)
  - [x] 6.1 Create `NewsPriorityScorer` class
  - [x] 6.2 Use `tier="scan"` - rule-based scoring
  - [x] 6.3 Implement `calculate_priority(article: HarvestedArticle, category: CategoryResult) -> float`
  - [x] 6.4 Priority rules:
        - REGULATORY + health claims/novel food keywords → priority=HIGH, base_score=8.0
        - REGULATORY other → priority=MEDIUM, base_score=6.0
        - RESEARCH + mushroom compounds → base_score=5.0
        - PRODUCT_NEWS → base_score=4.0
        - COMPETITOR → base_score=4.0
        - GENERAL → base_score=2.0
  - [x] 6.5 Score boosters: recency (+0.5 for <6 hours), source reputation (+0.5 for tier-1 sources)
  - [x] 6.6 Set `requires_operator_attention=True` if regulatory + high priority

- [x] Task 7: Implement transformer stage (AC: #2, #3)
  - [x] 7.1 Create `NewsTransformer` class
  - [x] 7.2 Accept `NewsCategorizer` and `NewsPriorityScorer` via dependency injection
  - [x] 7.3 Implement `transform(harvested: list[HarvestedArticle]) -> list[TransformedResearch]`
  - [x] 7.4 Map news fields to Research Pool schema:
        - `source`: "news"
        - `title`: article headline
        - `content`: article summary + category info
        - `url`: article URL
        - `tags`: auto-generate from category + detected keywords
        - `source_metadata`: {source_name, category, is_regulatory, priority_level, requires_attention}
        - `created_at`: article publish timestamp
  - [x] 7.5 Set `score` from priority scorer
  - [x] 7.6 Sanitize content: truncate if > 10,000 chars, clean HTML entities

- [x] Task 8: Implement validator stage (AC: #2)
  - [x] 8.1 Create `NewsValidator` class
  - [x] 8.2 Accept `EUComplianceChecker` via dependency injection (from Story 1.2)
  - [x] 8.3 Implement `validate(items: list[TransformedResearch]) -> list[ValidatedResearch]`
  - [x] 8.4 Call compliance checker on article content
  - [x] 8.5 Set `compliance_status` based on checker result (COMPLIANT, WARNING, REJECTED)
  - [x] 8.6 Preserve `is_regulatory` flag for operator attention routing
  - [x] 8.7 Log validation statistics: passed, warned, rejected

- [x] Task 9: Integrate with Research Publisher (AC: #2, #3)
  - [x] 9.1 Accept `ResearchPublisher` via dependency injection (from Story 2.1)
  - [x] 9.2 Accept `ResearchItemScorer` via dependency injection (from Story 2.2)
  - [x] 9.3 Implement `publish_results(validated: list[ValidatedResearch]) -> list[ResearchItem]`
  - [x] 9.4 Use priority score as base, then apply Research Item Scorer adjustments
  - [x] 9.5 Publish to Research Pool via publisher
  - [x] 9.6 Return created ResearchItem list with IDs

- [x] Task 10: Create orchestrated pipeline (AC: #1, #2, #3, #4)
  - [x] 10.1 Create `NewsResearchPipeline` class
  - [x] 10.2 Accept all stage components via dependency injection
  - [x] 10.3 Implement `execute() -> PipelineResult`
  - [x] 10.4 Chain stages: scan -> harvest -> categorize -> prioritize -> transform -> validate -> publish
  - [x] 10.5 Track and return statistics: feeds_processed, articles_found, categorized, regulatory_flagged, published
  - [x] 10.6 Handle partial failures: continue pipeline even if some feeds/articles fail

- [x] Task 11: Implement graceful degradation (AC: #4)
  - [x] 11.1 Wrap pipeline execution in try/catch
  - [x] 11.2 On feed fetch failure (after retries), mark scan as INCOMPLETE
  - [x] 11.3 Track which feeds succeeded/failed separately
  - [x] 11.4 Log failure details for debugging
  - [x] 11.5 Queue for next scheduled run (via ARQ job queue)
  - [x] 11.6 Ensure existing Research Pool data remains intact

- [x] Task 12: Register in team_spec.py (AC: #1)
  - [x] 12.1 Add `NewsScanner` as RegisteredAgent with tier="scan"
  - [x] 12.2 Add `NewsCategorizer` as RegisteredService
  - [x] 12.3 Add `NewsPriorityScorer` as RegisteredService
  - [x] 12.4 Add `NewsHarvester` as RegisteredService
  - [x] 12.5 Add `NewsTransformer` as RegisteredService
  - [x] 12.6 Add `NewsValidator` as RegisteredService
  - [x] 12.7 Add `NewsResearchPipeline` as RegisteredService with capability="news_research"
  - [x] 12.8 Ensure all components are injectable via Team Builder

- [x] Task 13: Create configuration file (AC: #1)
  - [x] 13.1 Create `config/dawo_news_scanner.json`
  - [x] 13.2 Define feeds list with URLs and source names
  - [x] 13.3 Define keywords: ["functional mushrooms", "adaptogens", "supplements", "EU regulations", "health claims", "novel food", "Mattilsynet", "lion's mane", "chaga", "reishi"]
  - [x] 13.4 Define filters: hours_back=24
  - [x] 13.5 Define schedule: cron expression for daily 6 AM
  - [x] 13.6 Define tier_1_sources: ["NutraIngredients", "Nutraceuticals World", "FoodNavigator"]
  - [x] 13.7 Define competitor_brands: [] (operator configures)

- [x] Task 14: Create comprehensive unit tests
  - [x] 14.1 Test NewsFeedClient RSS parsing and timeout handling
  - [x] 14.2 Test scanner keyword filtering and deduplication
  - [x] 14.3 Test harvester content extraction and HTML cleaning
  - [x] 14.4 Test NewsCategorizer pattern matching for all categories
  - [x] 14.5 Test NewsPriorityScorer scoring rules and boosters
  - [x] 14.6 Test transformer field mapping and regulatory flagging
  - [x] 14.7 Test validator compliance integration
  - [x] 14.8 Test pipeline orchestration
  - [x] 14.9 Test graceful degradation on feed failure
  - [x] 14.10 Test partial failure handling (some feeds fail)
  - [x] 14.11 Mock feed responses for all tests

- [x] Task 15: Create integration tests
  - [x] 15.1 Test full pipeline with mocked RSS feeds
  - [x] 15.2 Test Research Pool insertion (with test database)
  - [x] 15.3 Test scoring integration with regulatory boost
  - [x] 15.4 Test retry middleware integration
  - [x] 15.5 Test operator attention flagging propagation
  - [x] 15.6 Test category-based tag generation

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Harvester-Framework], [project-context.md#Code-Organization]

This is the **FOURTH scanner** in the Harvester Framework - it MUST follow the exact pattern established by Reddit Scanner (Story 2.3), YouTube Scanner (Story 2.4), and Instagram Scanner (Story 2.5).

**Harvester Framework Pipeline:**
```
[Scanner] -> [Harvester] -> [Categorizer] -> [Priority Scorer] -> [Transformer] -> [Validator] -> [Scorer] -> [Publisher] -> [Research Pool]
     |           |               |                  |                   |              |            |           |
   scan()    harvest()      categorize()     calculate_priority()   transform()    validate()    score()    publish()
   tier=scan  tier=scan      tier=scan           tier=scan            tier=scan      tier=scan   tier=scan   tier=scan
```

**Key Difference from Other Scanners:**
- News Scanner is **fully rule-based** - NO LLM stages (unlike YouTube's InsightExtractor or Instagram's ThemeExtractor/ClaimDetector)
- Uses `tier="scan"` for ALL components
- Categorization and priority scoring use keyword pattern matching
- Lower cost per execution, suitable for daily frequency

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Directory-Structure]

```
teams/dawo/
├── scanners/
│   ├── reddit/                        # EXISTS from Story 2.3
│   │   └── ...
│   ├── youtube/                       # EXISTS from Story 2.4
│   │   └── ...
│   ├── instagram/                     # EXISTS from Story 2.5
│   │   └── ...
│   └── news/                          # CREATE THIS MODULE
│       ├── __init__.py                # Export all public types
│       ├── agent.py                   # NewsScanner main class
│       ├── prompts.py                 # Categorization rules (no LLM prompts)
│       ├── tools.py                   # NewsFeedClient, feed parsing
│       ├── config.py                  # NewsScannerConfig
│       ├── schemas.py                 # RawNewsArticle, HarvestedArticle, NewsCategory, PriorityLevel
│       ├── harvester.py               # NewsHarvester
│       ├── categorizer.py             # NewsCategorizer (rule-based)
│       ├── priority_scorer.py         # NewsPriorityScorer (rule-based)
│       ├── transformer.py             # NewsTransformer
│       ├── validator.py               # NewsValidator
│       └── pipeline.py                # NewsResearchPipeline
├── research/                          # Exists from Story 2.1
│   ├── models.py                      # ResearchItem, ResearchSource
│   ├── repository.py                  # ResearchPoolRepository
│   ├── publisher.py                   # ResearchPublisher
│   └── scoring/                       # Exists from Story 2.2
│       └── scorer.py                  # ResearchItemScorer

config/
└── dawo_news_scanner.json             # CREATE: Scanner configuration

tests/teams/dawo/
└── test_scanners/
    ├── test_reddit/                   # EXISTS from Story 2.3
    ├── test_youtube/                  # EXISTS from Story 2.4
    ├── test_instagram/                # EXISTS from Story 2.5
    └── test_news/                     # CREATE THIS
        ├── __init__.py
        ├── conftest.py                # Fixtures, mocks
        ├── test_client.py             # NewsFeedClient tests
        ├── test_scanner.py            # Scanner stage tests
        ├── test_harvester.py          # Harvester stage tests
        ├── test_categorizer.py        # Categorization tests
        ├── test_priority_scorer.py    # Priority scoring tests
        ├── test_transformer.py        # Transformer stage tests
        ├── test_validator.py          # Validator stage tests
        ├── test_pipeline.py           # Full pipeline tests
        └── test_integration.py        # Integration with Research Pool
```

### RSS/Feed Parsing Implementation

**Source:** [epics.md#Story-2.6]

**Dependencies:**
- `feedparser` for RSS/Atom parsing (standard Python library)
- `beautifulsoup4` for HTML content cleaning
- `aiohttp` for async HTTP requests

**NewsFeedClient:**
```python
# tools.py
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional
import aiohttp
import asyncio

@dataclass
class FeedSource:
    """Configured news feed source."""
    name: str
    url: str
    is_tier_1: bool = False  # Higher reputation sources

class NewsFeedClient:
    """RSS/Atom feed client for news aggregation.

    Accepts configuration via dependency injection - NEVER loads files directly.
    Wraps all fetches with retry middleware (Story 1.5).
    """

    FETCH_TIMEOUT = 30  # seconds

    def __init__(
        self,
        config: NewsFeedClientConfig,
        retry_middleware: RetryMiddleware
    ):
        """Accept config via injection from Team Builder."""
        self._config = config
        self._retry = retry_middleware
        self._session: Optional[aiohttp.ClientSession] = None

    @with_retry(RetryConfig(max_attempts=3, backoff_base=2.0))
    async def fetch_feed(
        self,
        feed: FeedSource,
        hours_back: int = 24,
        keywords: list[str] | None = None
    ) -> list[dict]:
        """Fetch and parse RSS/Atom feed.

        Args:
            feed: Feed source configuration
            hours_back: Only include articles from last N hours
            keywords: Optional keyword filter (any match)

        Returns:
            List of article entries matching filters

        Raises:
            FeedFetchError: On connection/parsing failure
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.FETCH_TIMEOUT)) as session:
                async with session.get(feed.url) as response:
                    content = await response.text()

            # Parse feed
            parsed = feedparser.parse(content)

            if parsed.bozo and parsed.bozo_exception:
                logger.warning("Feed parse warning for %s: %s", feed.name, parsed.bozo_exception)

            # Filter by date
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            articles = []

            for entry in parsed.entries:
                # Parse published date
                pub_date = self._parse_date(entry)
                if pub_date and pub_date < cutoff:
                    continue

                # Keyword filter
                if keywords:
                    text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                    if not any(kw.lower() in text for kw in keywords):
                        continue

                articles.append({
                    'title': entry.get('title', ''),
                    'summary': self._clean_html(entry.get('summary', '')),
                    'url': entry.get('link', ''),
                    'published': pub_date,
                    'source_name': feed.name,
                    'is_tier_1': feed.is_tier_1,
                })

            return articles

        except asyncio.TimeoutError as e:
            logger.error("Timeout fetching feed %s: %s", feed.name, e)
            raise FeedFetchError(f"Timeout fetching {feed.name}") from e
        except Exception as e:
            logger.error("Error fetching feed %s: %s", feed.name, e)
            raise FeedFetchError(f"Failed to fetch {feed.name}: {e}") from e

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ').strip()

    def _parse_date(self, entry: dict) -> Optional[datetime]:
        """Parse publication date from feed entry."""
        # feedparser normalizes to published_parsed or updated_parsed
        parsed = entry.get('published_parsed') or entry.get('updated_parsed')
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        return None
```

### News Categorizer (Rule-Based)

**Source:** [epics.md#Story-2.6], Pattern from Instagram's ClaimDetector

**CRITICAL:** This is rule-based, NOT LLM-based. Uses `tier="scan"` because no model calls needed.

```python
# categorizer.py
from dataclasses import dataclass
from enum import Enum
import re

class NewsCategory(Enum):
    """News article category."""
    REGULATORY = "regulatory"      # EU, FDA, Mattilsynet, compliance
    PRODUCT_NEWS = "product_news"  # Launches, announcements
    RESEARCH = "research"          # Studies, clinical trials
    COMPETITOR = "competitor"      # Competitor brand mentions
    GENERAL = "general"            # Other industry news

class PriorityLevel(Enum):
    """Priority level for operator attention."""
    HIGH = "high"      # Regulatory + health claims/novel food
    MEDIUM = "medium"  # Regulatory other
    LOW = "low"        # Non-regulatory

@dataclass
class CategoryResult:
    """Result from news categorization."""
    category: NewsCategory
    confidence: float  # 0.0-1.0
    is_regulatory: bool
    priority_level: PriorityLevel
    matched_patterns: list[str]  # Which patterns triggered classification
    requires_operator_attention: bool

class NewsCategorizer:
    """Rule-based news article categorization.

    Uses tier="scan" - NO LLM calls, pattern matching only.
    """

    # Regulatory patterns - highest priority
    REGULATORY_PATTERNS = [
        r'\bEU\s+(?:health\s+claims?|regulation|directive|commission)\b',
        r'\bEC\s+1924/2006\b',
        r'\bnovel\s+food\b',
        r'\bMattilsynet\b',
        r'\bFDA\s+(?:approval|warning|regulation)\b',
        r'\bhealth\s+claims?\s+(?:register|regulation|compliance)\b',
        r'\bregulatory\s+(?:update|change|approval|enforcement)\b',
        r'\bcompliance\s+(?:update|requirement|warning)\b',
    ]

    # High-priority regulatory keywords (boost to HIGH priority)
    HIGH_PRIORITY_KEYWORDS = [
        'health claims', 'novel food', 'EC 1924', 'compliance violation',
        'enforcement action', 'regulatory warning', 'product recall',
    ]

    # Research patterns
    RESEARCH_PATTERNS = [
        r'\bclinical\s+(?:trial|study|research)\b',
        r'\bstudy\s+(?:finds|shows|reveals|demonstrates)\b',
        r'\bresearch(?:ers)?\s+(?:found|discover|report)\b',
        r'\bpeer[- ]reviewed\b',
        r'\bscientific\s+evidence\b',
    ]

    # Product news patterns
    PRODUCT_PATTERNS = [
        r'\blaunches?\b',
        r'\bnew\s+product\b',
        r'\bannounces?\b',
        r'\bintroduces?\b',
        r'\bpartnership\b',
        r'\bacquisition\b',
    ]

    def __init__(self, competitor_brands: list[str] | None = None):
        """Initialize with optional competitor brand list."""
        self._competitor_patterns = []
        if competitor_brands:
            for brand in competitor_brands:
                self._competitor_patterns.append(
                    re.compile(rf'\b{re.escape(brand)}\b', re.IGNORECASE)
                )

    def categorize(self, article: 'HarvestedArticle') -> CategoryResult:
        """Categorize a news article using pattern matching.

        Args:
            article: Harvested news article

        Returns:
            CategoryResult with category, priority, and flags
        """
        text = f"{article.title} {article.summary}".lower()
        text_original = f"{article.title} {article.summary}"  # For case-sensitive patterns

        matched_patterns: list[str] = []

        # Check regulatory (highest priority)
        is_regulatory = False
        for pattern in self.REGULATORY_PATTERNS:
            if re.search(pattern, text_original, re.IGNORECASE):
                is_regulatory = True
                matched_patterns.append(pattern)

        if is_regulatory:
            # Check for high-priority regulatory keywords
            is_high_priority = any(kw in text for kw in self.HIGH_PRIORITY_KEYWORDS)
            return CategoryResult(
                category=NewsCategory.REGULATORY,
                confidence=0.9 if len(matched_patterns) > 1 else 0.7,
                is_regulatory=True,
                priority_level=PriorityLevel.HIGH if is_high_priority else PriorityLevel.MEDIUM,
                matched_patterns=matched_patterns,
                requires_operator_attention=is_high_priority,
            )

        # Check research
        for pattern in self.RESEARCH_PATTERNS:
            if re.search(pattern, text_original, re.IGNORECASE):
                matched_patterns.append(pattern)
        if matched_patterns:
            return CategoryResult(
                category=NewsCategory.RESEARCH,
                confidence=0.8 if len(matched_patterns) > 1 else 0.6,
                is_regulatory=False,
                priority_level=PriorityLevel.LOW,
                matched_patterns=matched_patterns,
                requires_operator_attention=False,
            )

        # Check competitor
        matched_patterns = []
        for pattern in self._competitor_patterns:
            if pattern.search(text_original):
                matched_patterns.append(pattern.pattern)
        if matched_patterns:
            return CategoryResult(
                category=NewsCategory.COMPETITOR,
                confidence=0.9,
                is_regulatory=False,
                priority_level=PriorityLevel.LOW,
                matched_patterns=matched_patterns,
                requires_operator_attention=False,
            )

        # Check product news
        matched_patterns = []
        for pattern in self.PRODUCT_PATTERNS:
            if re.search(pattern, text_original, re.IGNORECASE):
                matched_patterns.append(pattern)
        if matched_patterns:
            return CategoryResult(
                category=NewsCategory.PRODUCT_NEWS,
                confidence=0.7,
                is_regulatory=False,
                priority_level=PriorityLevel.LOW,
                matched_patterns=matched_patterns,
                requires_operator_attention=False,
            )

        # Default: general
        return CategoryResult(
            category=NewsCategory.GENERAL,
            confidence=0.5,
            is_regulatory=False,
            priority_level=PriorityLevel.LOW,
            matched_patterns=[],
            requires_operator_attention=False,
        )
```

### Priority Scorer (Rule-Based)

**Source:** [epics.md#Story-2.6]

```python
# priority_scorer.py
from dataclasses import dataclass

@dataclass
class PriorityScore:
    """Priority score result."""
    base_score: float  # Category-based score
    final_score: float  # After boosters applied
    boosters_applied: list[str]  # Which boosters triggered
    requires_attention: bool

class NewsPriorityScorer:
    """Rule-based priority scoring for news articles.

    Uses tier="scan" - NO LLM calls, rule-based scoring only.

    Score ranges map to Research Item Scorer expectations:
        - 8-10: High priority (regulatory + health claims)
        - 5-7: Medium priority (research, some regulatory)
        - 2-4: Standard priority (product news, competitor, general)
    """

    # Base scores by category
    CATEGORY_BASE_SCORES = {
        NewsCategory.REGULATORY: 6.0,  # Base, can boost to 8+
        NewsCategory.RESEARCH: 5.0,
        NewsCategory.PRODUCT_NEWS: 4.0,
        NewsCategory.COMPETITOR: 4.0,
        NewsCategory.GENERAL: 2.0,
    }

    # Boosters
    RECENCY_BOOST = 0.5        # Article < 6 hours old
    TIER_1_SOURCE_BOOST = 0.5  # From high-reputation source
    REGULATORY_HIGH_BOOST = 2.0  # Regulatory + high priority keywords
    MUSHROOM_RESEARCH_BOOST = 1.0  # Research specifically about mushroom compounds

    MUSHROOM_KEYWORDS = [
        'lion\'s mane', 'hericium', 'chaga', 'inonotus',
        'reishi', 'ganoderma', 'cordyceps', 'shiitake',
        'maitake', 'functional mushroom', 'adaptogen',
    ]

    def calculate_priority(
        self,
        article: 'HarvestedArticle',
        category_result: CategoryResult,
    ) -> PriorityScore:
        """Calculate priority score for article.

        Args:
            article: Harvested news article
            category_result: Categorization result

        Returns:
            PriorityScore with final score and boosters
        """
        base = self.CATEGORY_BASE_SCORES.get(category_result.category, 2.0)
        boosters: list[str] = []

        # Regulatory high-priority boost
        if (category_result.category == NewsCategory.REGULATORY and
            category_result.priority_level == PriorityLevel.HIGH):
            base += self.REGULATORY_HIGH_BOOST
            boosters.append("regulatory_high_priority")

        # Recency boost
        if article.published:
            from datetime import datetime, timezone, timedelta
            hours_old = (datetime.now(timezone.utc) - article.published).total_seconds() / 3600
            if hours_old < 6:
                base += self.RECENCY_BOOST
                boosters.append("recent_article")

        # Tier-1 source boost
        if article.is_tier_1:
            base += self.TIER_1_SOURCE_BOOST
            boosters.append("tier_1_source")

        # Mushroom research boost
        if category_result.category == NewsCategory.RESEARCH:
            text = f"{article.title} {article.summary}".lower()
            if any(kw in text for kw in self.MUSHROOM_KEYWORDS):
                base += self.MUSHROOM_RESEARCH_BOOST
                boosters.append("mushroom_research")

        # Cap at 10
        final = min(base, 10.0)

        return PriorityScore(
            base_score=self.CATEGORY_BASE_SCORES.get(category_result.category, 2.0),
            final_score=final,
            boosters_applied=boosters,
            requires_attention=category_result.requires_operator_attention,
        )
```

### Configuration Schema

**Source:** [project-context.md#Configuration-Loading]

```python
# config.py
from dataclasses import dataclass, field

@dataclass
class FeedSource:
    """News feed source configuration."""
    name: str
    url: str
    is_tier_1: bool = False

@dataclass
class NewsFeedClientConfig:
    """Feed client configuration - timeouts and retries."""
    fetch_timeout: int = 30
    max_retries: int = 3

@dataclass
class NewsScannerConfig:
    """Scanner configuration - loaded from config file via injection."""
    feeds: list[FeedSource] = field(default_factory=lambda: [
        FeedSource("NutraIngredients", "https://www.nutraingredients.com/rss/", is_tier_1=True),
        FeedSource("Nutraceuticals World", "https://www.nutraceuticalsworld.com/rss/", is_tier_1=True),
        FeedSource("FoodNavigator", "https://www.foodnavigator.com/rss/", is_tier_1=True),
    ])
    keywords: list[str] = field(default_factory=lambda: [
        "functional mushrooms", "adaptogens", "supplements",
        "EU regulations", "health claims", "novel food",
        "Mattilsynet", "lion's mane", "chaga", "reishi",
    ])
    competitor_brands: list[str] = field(default_factory=list)  # Operator configures
    hours_back: int = 24
```

**config/dawo_news_scanner.json:**
```json
{
  "feeds": [
    {"name": "NutraIngredients", "url": "https://www.nutraingredients.com/rss/news", "is_tier_1": true},
    {"name": "Nutraceuticals World", "url": "https://www.nutraceuticalsworld.com/rss/news", "is_tier_1": true},
    {"name": "FoodNavigator", "url": "https://www.foodnavigator.com/rss/news", "is_tier_1": true},
    {"name": "NutritionInsight", "url": "https://www.nutritioninsight.com/rss/", "is_tier_1": false},
    {"name": "EU Food Safety", "url": "https://www.efsa.europa.eu/en/rss", "is_tier_1": true}
  ],
  "keywords": [
    "functional mushrooms",
    "adaptogens",
    "supplements industry",
    "EU regulations",
    "health claims",
    "novel food",
    "Mattilsynet",
    "lion's mane",
    "chaga",
    "reishi",
    "cordyceps",
    "mushroom extract"
  ],
  "competitor_brands": [],
  "hours_back": 24,
  "schedule": {
    "cron": "0 6 * * *",
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

**UNIQUE to News Scanner:** This pipeline is **fully rule-based** - NO LLM stages:
- All components use `tier="scan"` (Haiku not actually called - rule-based)
- Categorization uses pattern matching
- Priority scoring uses rule-based scoring

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- `claude-haiku`, `claude-sonnet`, `claude-opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="news_scanner",
    agent_class=NewsScanner,
    capabilities=["news_research", "research_scanning", "regulatory_monitoring"],
    tier="scan"  # Rule-based, no actual LLM calls
)
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [2-3-reddit-research-scanner.md], [2-4-youtube-research-scanner.md], [2-5-instagram-trend-scanner.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="scan"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| SQLAlchemy reserved word fix | Use `source_metadata` not `metadata` |
| Add logging to exception handlers | All exceptions logged before re-raising |
| Extract magic numbers to constants | `HOURS_BACK = 24`, `FETCH_TIMEOUT = 30`, etc. |
| TDD approach | Write tests first for each task |
| Unit tests with mocking | Mock feed responses for all tests |
| Mock patterns: async vs sync | `ResearchItemScorer.calculate_score()` is sync - use `MagicMock` |
| Pipeline return value handling | Track batch vs individual publish counts |
| Graceful degradation | Return INCOMPLETE on feed failure, PARTIAL on item failures |
| Integration tests separate | Create test_integration.py with conftest.py fixtures |
| Track partial success | Track which feeds succeeded/failed separately |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], [architecture.md#Anti-Patterns]

1. **NEVER load config directly** - Accept via injection
2. **NEVER make direct HTTP requests without retry wrapper**
3. **NEVER use LLM model names** - Use tier system
4. **NEVER swallow exceptions without logging**
5. **NEVER assume all feeds succeed** - Handle partial failures

### Exports Template (MUST FOLLOW)

**Source:** [project-context.md#Module-Exports]

```python
# teams/dawo/scanners/news/__init__.py
"""Industry News Scanner for DAWO research intelligence pipeline."""

from .agent import NewsScanner, NewsScanError
from .tools import (
    NewsFeedClient,
    FeedFetchError,
    FeedParseError,
)
from .config import (
    FeedSource,
    NewsFeedClientConfig,
    NewsScannerConfig,
    DEFAULT_HOURS_BACK,
    DEFAULT_FETCH_TIMEOUT,
)
from .schemas import (
    RawNewsArticle,
    HarvestedArticle,
    NewsCategory,
    PriorityLevel,
    CategoryResult,
    PriorityScore,
    ScanResult,
    PipelineResult,
    PipelineStatus,
)
from .harvester import NewsHarvester, HarvesterError
from .categorizer import NewsCategorizer
from .priority_scorer import NewsPriorityScorer
from .transformer import NewsTransformer, TransformerError
from .validator import NewsValidator, ValidatorError
from .pipeline import NewsResearchPipeline, PipelineError

__all__ = [
    # Main agent
    "NewsScanner",
    # Client
    "NewsFeedClient",
    # Config
    "FeedSource",
    "NewsFeedClientConfig",
    "NewsScannerConfig",
    "DEFAULT_HOURS_BACK",
    "DEFAULT_FETCH_TIMEOUT",
    # Schemas
    "RawNewsArticle",
    "HarvestedArticle",
    "NewsCategory",
    "PriorityLevel",
    "CategoryResult",
    "PriorityScore",
    "ScanResult",
    "PipelineResult",
    "PipelineStatus",
    # Exceptions
    "NewsScanError",
    "FeedFetchError",
    "FeedParseError",
    "HarvesterError",
    "TransformerError",
    "ValidatorError",
    "PipelineError",
    # Pipeline stages
    "NewsHarvester",
    "NewsCategorizer",
    "NewsPriorityScorer",
    "NewsTransformer",
    "NewsValidator",
    "NewsResearchPipeline",
]
```

### Test Fixtures

**Source:** [2-5-instagram-trend-scanner.md#Test-Fixtures]

```python
# tests/teams/dawo/test_scanners/test_news/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

@pytest.fixture
def mock_rss_feed_response():
    """Mock RSS feed parsed response."""
    now = datetime.now(timezone.utc)
    return {
        'entries': [
            {
                'title': 'EU Approves New Health Claim for Lion\'s Mane Extract',
                'summary': '<p>The European Commission has approved a new health claim...</p>',
                'link': 'https://example.com/eu-lions-mane-claim',
                'published_parsed': now.timetuple()[:6],
            },
            {
                'title': 'Study Shows Reishi Benefits for Immune Function',
                'summary': 'New clinical research demonstrates significant immune benefits...',
                'link': 'https://example.com/reishi-study',
                'published_parsed': (now - timedelta(hours=12)).timetuple()[:6],
            },
            {
                'title': 'Supplement Company Launches New Mushroom Line',
                'summary': 'XYZ Supplements announces new line of functional mushroom products...',
                'link': 'https://example.com/new-product-launch',
                'published_parsed': (now - timedelta(hours=6)).timetuple()[:6],
            },
        ],
        'bozo': False,
        'bozo_exception': None,
    }

@pytest.fixture
def mock_regulatory_article():
    """Regulatory news article for testing high-priority flagging."""
    return HarvestedArticle(
        title='Mattilsynet Issues Warning on Health Claims Compliance',
        summary='Norwegian Food Safety Authority warns supplement companies about EU health claims regulation compliance...',
        url='https://example.com/mattilsynet-warning',
        source_name='NutraIngredients',
        is_tier_1=True,
        published=datetime.now(timezone.utc) - timedelta(hours=2),
    )

@pytest.fixture
def mock_news_feed_client(mock_rss_feed_response):
    """Mock NewsFeedClient for testing without HTTP calls."""
    client = AsyncMock(spec=NewsFeedClient)
    client.fetch_feed.return_value = [
        {
            'title': entry['title'],
            'summary': entry['summary'],
            'url': entry['link'],
            'published': datetime(*entry['published_parsed'][:6], tzinfo=timezone.utc),
            'source_name': 'TestFeed',
            'is_tier_1': True,
        }
        for entry in mock_rss_feed_response['entries']
    ]
    return client

@pytest.fixture
def scanner_config():
    """Test scanner configuration."""
    return NewsScannerConfig(
        feeds=[
            FeedSource("TestFeed", "https://test.com/rss", is_tier_1=True),
        ],
        keywords=["mushrooms", "supplements", "EU regulations"],
        competitor_brands=["CompetitorBrand"],
        hours_back=24,
    )
```

### Operator Attention Routing

**Source:** [epics.md#Story-2.6]

When regulatory news with health claims/novel food keywords is detected:
1. `requires_operator_attention=True` is set in CategoryResult
2. `priority_level=HIGH` triggers score boost to 8+
3. `source_metadata.is_regulatory=True` enables filtering in Research Pool
4. Approval queue can filter by `requires_attention` flag

```python
# In transformer.py
if category_result.requires_operator_attention:
    research_item.source_metadata["requires_attention"] = True
    research_item.source_metadata["attention_reason"] = "regulatory_health_claims"
```

### Project Structure Notes

- **Fourth scanner**: Follows pattern established by Reddit (2.3), YouTube (2.4), Instagram (2.5)
- **Fully rule-based**: NO LLM stages - categorization and priority use pattern matching
- **Daily schedule**: 6 AM for morning operator review
- **Regulatory priority**: Health claims/novel food news automatically scores 8+
- **Follows Harvester Framework**: scan -> harvest -> categorize -> prioritize -> transform -> validate -> publish
- **Integrates with**: Research Pool (2.1), Scoring Engine (2.2), EU Compliance (1.2), Retry Middleware (1.5)

### References

- [Source: epics.md#Story-2.6] - Original story requirements
- [Source: architecture.md#Harvester-Framework] - Pipeline pattern
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology
- [Source: 2-1-research-pool-database-storage.md] - Research Pool integration
- [Source: 2-2-research-item-scoring-engine.md] - Scoring integration
- [Source: 2-3-reddit-research-scanner.md] - Pattern reference (first scanner)
- [Source: 2-4-youtube-research-scanner.md] - Pattern reference (LLM stage pattern)
- [Source: 2-5-instagram-trend-scanner.md] - Pattern reference (FOLLOW THIS for structure)
- [Source: 1-2-eu-compliance-checker-validator.md] - Compliance integration
- [Source: 1-5-external-api-retry-middleware.md] - Retry middleware integration

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No significant debug issues encountered.

### Completion Notes List

- **AC #1 SATISFIED**: News scanner scans configured RSS feeds (5 tier-1 and tier-2 sources), searches for configured keywords (functional mushrooms, adaptogens, supplements, EU regulations, health claims, novel food, Mattilsynet), and collects articles from last 24 hours. Schedule configured for daily 6 AM.
- **AC #2 SATISFIED**: Harvester extracts headline, summary, source, publish date, URL. Categorizer classifies articles as REGULATORY, PRODUCT_NEWS, RESEARCH, COMPETITOR, or GENERAL using rule-based pattern matching.
- **AC #3 SATISFIED**: Regulatory news with health claims/novel food keywords is flagged HIGH priority with `requires_operator_attention=True` and scores 8+ (base 6.0 + 2.0 regulatory high boost + source/recency boosters).
- **AC #4 SATISFIED**: Pipeline returns INCOMPLETE status when all feeds fail, PARTIAL when some feeds fail. Graceful degradation ensures partial results are published and pipeline can continue even with some failures.
- **UNIQUE DESIGN**: This is the FOURTH scanner (after Reddit, YouTube, Instagram) and the first fully rule-based scanner - NO LLM stages. All categorization and priority scoring use regex pattern matching, making it cost-effective for daily execution.
- **107 unit tests** + integration tests pass, covering all pipeline stages.
- **959 total tests pass** (full test suite) with no regressions.

### File List

#### New Files Created
- `teams/dawo/scanners/news/__init__.py` - Module exports with `__all__` list
- `teams/dawo/scanners/news/agent.py` - NewsScanner class
- `teams/dawo/scanners/news/tools.py` - NewsFeedClient with RSS/Atom parsing
- `teams/dawo/scanners/news/config.py` - FeedSource, NewsFeedClientConfig, NewsScannerConfig
- `teams/dawo/scanners/news/schemas.py` - RawNewsArticle, HarvestedArticle, NewsCategory, PriorityLevel, CategoryResult, PriorityScore, ValidatedResearch, PipelineStatus, PipelineResult
- `teams/dawo/scanners/news/patterns.py` - Rule-based patterns for categorization (renamed from prompts.py)
- `teams/dawo/scanners/news/harvester.py` - NewsHarvester class
- `teams/dawo/scanners/news/categorizer.py` - NewsCategorizer class (rule-based)
- `teams/dawo/scanners/news/priority_scorer.py` - NewsPriorityScorer class (rule-based)
- `teams/dawo/scanners/news/transformer.py` - NewsTransformer class
- `teams/dawo/scanners/news/validator.py` - NewsValidator class
- `teams/dawo/scanners/news/pipeline.py` - NewsResearchPipeline class
- `config/dawo_news_scanner.json` - Scanner configuration
- `tests/teams/dawo/test_scanners/test_news/__init__.py`
- `tests/teams/dawo/test_scanners/test_news/conftest.py` - Test fixtures
- `tests/teams/dawo/test_scanners/test_news/test_schemas.py` - Schema tests
- `tests/teams/dawo/test_scanners/test_news/test_config.py` - Config tests
- `tests/teams/dawo/test_scanners/test_news/test_client.py` - Client tests
- `tests/teams/dawo/test_scanners/test_news/test_scanner.py` - Scanner tests
- `tests/teams/dawo/test_scanners/test_news/test_harvester.py` - Harvester tests
- `tests/teams/dawo/test_scanners/test_news/test_categorizer.py` - Categorizer tests
- `tests/teams/dawo/test_scanners/test_news/test_priority_scorer.py` - Priority scorer tests
- `tests/teams/dawo/test_scanners/test_news/test_transformer.py` - Transformer tests
- `tests/teams/dawo/test_scanners/test_news/test_validator.py` - Validator tests
- `tests/teams/dawo/test_scanners/test_news/test_pipeline.py` - Pipeline tests
- `tests/teams/dawo/test_scanners/test_news/test_integration.py` - Integration tests

#### Modified Files
- `teams/dawo/team_spec.py` - Added NewsScanner agent + 6 service registrations

### Change Log

- 2026-02-06: Implemented Industry News Scanner (Story 2.6) - Fourth scanner in Harvester Framework, fully rule-based (no LLM stages), 107 tests passing
- 2026-02-06: Code Review Fixes Applied:
  - H1: Retry middleware now actually wraps HTTP calls in tools.py (was accepted but ignored)
  - M1: Config validation fixed - feeds field now has sensible default using _default_feeds()
  - M2: Harvester HTML cleaning kept for defense-in-depth with clear docstring
  - M3: Renamed prompts.py to patterns.py (no LLM prompts, just regex patterns)
  - L1: Deleted nul Windows artifact
  - L2: Synced config.py DEFAULT_KEYWORDS with config/dawo_news_scanner.json
  - All 107 tests passing after fixes
