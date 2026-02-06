# Story 2.3: Reddit Research Scanner

Status: done

---

## Story

As an **operator**,
I want Reddit monitored for mushroom/wellness discussions,
So that trending topics and user questions fuel content ideas.

---

## Acceptance Criteria

1. **Given** the Reddit scanner is scheduled (daily 2 AM)
   **When** it executes
   **Then** it scans configured subreddits: r/Nootropics, r/Supplements, r/MushroomSupplements, r/Biohackers
   **And** it searches for keywords: lion's mane, chaga, reishi, cordyceps, shiitake, maitake
   **And** it collects posts from the last 24 hours with 10+ upvotes

2. **Given** a Reddit post is collected
   **When** the harvester processes it
   **Then** it extracts: title, body text, upvotes, comment count, permalink
   **And** the transformer standardizes format for Research Pool
   **And** the validator checks EU compliance
   **And** the publisher saves to Research Pool with source=reddit

3. **Given** Reddit API is unavailable
   **When** retry middleware exhausts attempts
   **Then** the scan is marked INCOMPLETE and queued for next cycle
   **And** previous research remains available

---

## Tasks / Subtasks

- [x] Task 1: Create Reddit scanner agent structure (AC: #1, #2)
  - [x] 1.1 Create `teams/dawo/scanners/reddit/` directory structure
  - [x] 1.2 Create `__init__.py` with complete exports
  - [x] 1.3 Create `agent.py` with `RedditScanner` class
  - [x] 1.4 Create `prompts.py` with system prompts (if LLM-enhanced filtering needed) - SKIPPED: Not needed, scanner uses config-driven filtering
  - [x] 1.5 Create `tools.py` with Reddit API tools
  - [x] 1.6 Create `config.py` with `RedditScannerConfig` dataclass
  - [x] 1.7 Create `schemas.py` with `RedditPost`, `ScanResult` schemas

- [x] Task 2: Implement Reddit API client (AC: #1, #3)
  - [x] 2.1 Create `RedditClient` class in `tools.py`
  - [x] 2.2 Accept config via dependency injection (client_id, client_secret, user_agent)
  - [x] 2.3 Implement OAuth2 authentication with Reddit API
  - [x] 2.4 Implement `search_subreddit(subreddit: str, keywords: list[str], time_filter: str) -> list[dict]`
  - [x] 2.5 Implement `get_post_details(post_id: str) -> dict`
  - [x] 2.6 Add rate limiting (60 requests/minute per Reddit API guidelines)
  - [x] 2.7 Wrap all API calls with retry middleware (Story 1.5)

- [x] Task 3: Implement scanner stage (AC: #1)
  - [x] 3.1 Create `scan()` method that iterates configured subreddits
  - [x] 3.2 Search each subreddit for each keyword
  - [x] 3.3 Filter results by: time (last 24h), upvotes (10+)
  - [x] 3.4 Deduplicate results by post ID
  - [x] 3.5 Return list of `RawRedditPost` objects
  - [x] 3.6 Log scan statistics: subreddits scanned, posts found, duplicates removed

- [x] Task 4: Implement harvester stage (AC: #2)
  - [x] 4.1 Create `RedditHarvester` class
  - [x] 4.2 Accept `RedditClient` via dependency injection
  - [x] 4.3 Implement `harvest(raw_posts: list[RawRedditPost]) -> list[HarvestedPost]`
  - [x] 4.4 For each post, fetch full details: title, selftext, score, num_comments, permalink, author, created_utc
  - [x] 4.5 Handle deleted/removed posts gracefully (skip with log)
  - [x] 4.6 Rate limit API calls per Reddit guidelines

- [x] Task 5: Implement transformer stage (AC: #2)
  - [x] 5.1 Create `RedditTransformer` class
  - [x] 5.2 Implement `transform(harvested_posts: list[HarvestedPost]) -> list[TransformedResearch]`
  - [x] 5.3 Map Reddit fields to Research Pool schema:
        - `source`: "reddit"
        - `title`: post title
        - `content`: selftext (body)
        - `url`: full permalink URL
        - `tags`: auto-generate from keywords found in title/content
        - `source_metadata`: {subreddit, author, upvotes, comment_count, permalink}
        - `created_at`: convert created_utc to datetime
  - [x] 5.4 Handle empty selftext (link posts) - use title as content
  - [x] 5.5 Sanitize content: remove markdown, truncate if > 10,000 chars

- [x] Task 6: Implement validator stage (AC: #2)
  - [x] 6.1 Create `RedditValidator` class
  - [x] 6.2 Accept `EUComplianceChecker` via dependency injection (from Story 1.2)
  - [x] 6.3 Implement `validate(items: list[TransformedResearch]) -> list[ValidatedResearch]`
  - [x] 6.4 Call compliance checker on each item's title + content
  - [x] 6.5 Set `compliance_status` based on checker result (COMPLIANT, WARNING, REJECTED)
  - [x] 6.6 Log validation statistics: passed, warned, rejected

- [x] Task 7: Integrate with Research Publisher (AC: #2)
  - [x] 7.1 Accept `ResearchPublisher` via dependency injection (from Story 2.1)
  - [x] 7.2 Accept `ResearchItemScorer` via dependency injection (from Story 2.2)
  - [x] 7.3 Implement `publish_results(validated: list[ValidatedResearch]) -> list[ResearchItem]`
  - [x] 7.4 Score each item before publishing
  - [x] 7.5 Publish to Research Pool via publisher
  - [x] 7.6 Return created ResearchItem list with IDs

- [x] Task 8: Create orchestrated pipeline (AC: #1, #2)
  - [x] 8.1 Create `RedditResearchPipeline` class
  - [x] 8.2 Accept all stage components via dependency injection
  - [x] 8.3 Implement `execute() -> PipelineResult`
  - [x] 8.4 Chain stages: scan → harvest → transform → validate → score → publish
  - [x] 8.5 Track and return statistics: total_found, harvested, transformed, validated, published
  - [x] 8.6 Handle partial failures: continue pipeline even if some items fail

- [x] Task 9: Implement graceful degradation (AC: #3)
  - [x] 9.1 Wrap pipeline execution in try/catch
  - [x] 9.2 On API failure (after retries), mark scan as INCOMPLETE
  - [x] 9.3 Log failure details for debugging
  - [x] 9.4 Queue for next scheduled run (via ARQ job queue) - Implemented via retry_scheduled flag
  - [x] 9.5 Ensure existing Research Pool data remains intact
  - [x] 9.6 Send Discord notification on scan failure (optional - if Discord integration available) - DEFERRED: Discord integration not yet available

- [x] Task 10: Register in team_spec.py (AC: #1)
  - [x] 10.1 Add `RedditScanner` as RegisteredAgent with tier="scan"
  - [x] 10.2 Add `RedditHarvester` as RegisteredService
  - [x] 10.3 Add `RedditTransformer` as RegisteredService
  - [x] 10.4 Add `RedditValidator` as RegisteredService
  - [x] 10.5 Add `RedditResearchPipeline` as RegisteredService with capability="reddit_research"
  - [x] 10.6 Ensure all components are injectable via Team Builder

- [x] Task 11: Create configuration file (AC: #1)
  - [x] 11.1 Create `config/dawo_reddit_scanner.json`
  - [x] 11.2 Define subreddits: ["Nootropics", "Supplements", "MushroomSupplements", "Biohackers"]
  - [x] 11.3 Define keywords: ["lion's mane", "chaga", "reishi", "cordyceps", "shiitake", "maitake"]
  - [x] 11.4 Define filters: min_upvotes=10, time_filter="day"
  - [x] 11.5 Define schedule: cron expression for daily 2 AM
  - [x] 11.6 Add Reddit API credentials placeholder (loaded from env vars)

- [x] Task 12: Create comprehensive unit tests
  - [x] 12.1 Test RedditClient authentication flow
  - [x] 12.2 Test scanner filtering (upvotes, time, keywords)
  - [x] 12.3 Test harvester data extraction
  - [x] 12.4 Test transformer field mapping
  - [x] 12.5 Test validator compliance integration
  - [x] 12.6 Test pipeline orchestration
  - [x] 12.7 Test graceful degradation on API failure
  - [x] 12.8 Test rate limiting behavior
  - [x] 12.9 Mock Reddit API responses for all tests

- [x] Task 13: Create integration tests
  - [x] 13.1 Test full pipeline with mocked Reddit API
  - [x] 13.2 Test Research Pool insertion (with test database)
  - [x] 13.3 Test scoring integration
  - [x] 13.4 Test retry middleware integration

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Harvester-Framework], [project-context.md#Code-Organization]

This is the **FIRST scanner** in the Harvester Framework - it establishes the pattern for all subsequent scanners (YouTube, Instagram, News, PubMed).

**Harvester Framework Pipeline:**
```
[Scanner] → [Harvester] → [Transformer] → [Validator] → [Scorer] → [Publisher] → [Research Pool]
     ↑           ↑             ↑              ↑            ↑           ↑
   scan()    harvest()    transform()    validate()    score()    publish()
```

All scanners MUST follow this exact pattern for consistency.

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Directory-Structure]

```
teams/dawo/
├── scanners/
│   └── reddit/                        # CREATE THIS MODULE
│       ├── __init__.py                # Export all public types
│       ├── agent.py                   # RedditScanner main class
│       ├── prompts.py                 # System prompts (if LLM-enhanced)
│       ├── tools.py                   # RedditClient, API tools
│       ├── config.py                  # RedditScannerConfig
│       ├── schemas.py                 # RawRedditPost, HarvestedPost, etc.
│       ├── harvester.py               # RedditHarvester
│       ├── transformer.py             # RedditTransformer
│       ├── validator.py               # RedditValidator
│       └── pipeline.py                # RedditResearchPipeline
├── research/                          # Exists from Story 2.1
│   ├── models.py                      # ResearchItem, ResearchSource
│   ├── repository.py                  # ResearchPoolRepository
│   ├── publisher.py                   # ResearchPublisher
│   └── scoring/                       # Exists from Story 2.2
│       └── scorer.py                  # ResearchItemScorer

config/
└── dawo_reddit_scanner.json           # CREATE: Scanner configuration

tests/teams/dawo/
└── test_scanners/
    └── test_reddit/                   # CREATE THIS
        ├── __init__.py
        ├── conftest.py                # Fixtures, mocks
        ├── test_client.py             # RedditClient tests
        ├── test_scanner.py            # Scanner stage tests
        ├── test_harvester.py          # Harvester stage tests
        ├── test_transformer.py        # Transformer stage tests
        ├── test_validator.py          # Validator stage tests
        ├── test_pipeline.py           # Full pipeline tests
        └── test_integration.py        # Integration with Research Pool
```

### Reddit API Integration

**Source:** [prd.md#Integration-Requirements], [architecture.md#External-Integration-Points]

**API Details:**
- **Base URL:** `https://oauth.reddit.com`
- **Auth:** OAuth2 "script" type (for personal use scripts)
- **Rate Limit:** 60 requests/minute
- **User Agent:** Must include app name and version

**Authentication Flow:**
```python
# tools.py
class RedditClient:
    """Reddit API client with OAuth2 authentication.

    Accepts credentials via dependency injection - NEVER loads from file.
    """

    def __init__(self, config: RedditClientConfig):
        """Accept config via injection from Team Builder."""
        self._config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def _authenticate(self) -> str:
        """Get OAuth2 access token."""
        auth = aiohttp.BasicAuth(
            self._config.client_id,
            self._config.client_secret
        )
        data = {
            "grant_type": "password",
            "username": self._config.username,
            "password": self._config.password
        }
        headers = {"User-Agent": self._config.user_agent}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data=data,
                headers=headers
            ) as resp:
                result = await resp.json()
                return result["access_token"]
```

**Search Endpoint:**
```python
async def search_subreddit(
    self,
    subreddit: str,
    query: str,
    time_filter: str = "day",
    limit: int = 100
) -> list[dict]:
    """Search subreddit for posts matching query.

    Args:
        subreddit: Subreddit name (without r/)
        query: Search keywords
        time_filter: "hour", "day", "week", "month", "year", "all"
        limit: Max results (Reddit caps at 100)

    Returns:
        List of post data dicts
    """
    url = f"https://oauth.reddit.com/r/{subreddit}/search"
    params = {
        "q": query,
        "restrict_sr": "true",
        "sort": "hot",
        "t": time_filter,
        "limit": limit
    }
    # ... API call with retry middleware
```

### Reddit Post Data Structure

**Source:** [2-1-research-pool-database-storage.md#Metadata-JSONB-Structure]

**Raw Reddit API Response:**
```python
{
    "kind": "t3",  # t3 = post
    "data": {
        "id": "abc123",
        "title": "My experience with lion's mane for brain fog",
        "selftext": "Been taking lion's mane for 3 months...",
        "author": "username",
        "subreddit": "Nootropics",
        "score": 150,  # upvotes - downvotes
        "upvote_ratio": 0.95,
        "num_comments": 45,
        "permalink": "/r/Nootropics/comments/abc123/my_experience/",
        "created_utc": 1707177600,
        "url": "https://reddit.com/r/...",  # For link posts
        "is_self": true  # True if text post, False if link post
    }
}
```

**Transformed to Research Pool Schema:**
```python
ResearchItem(
    source=ResearchSource.REDDIT,
    title="My experience with lion's mane for brain fog",
    content="Been taking lion's mane for 3 months...",
    url="https://reddit.com/r/Nootropics/comments/abc123/my_experience/",
    tags=["lions_mane", "brain_fog", "nootropics"],
    source_metadata={
        "subreddit": "Nootropics",
        "author": "username",
        "upvotes": 150,
        "upvote_ratio": 0.95,
        "comment_count": 45,
        "permalink": "/r/Nootropics/comments/abc123/my_experience/",
        "is_self": True
    },
    created_at=datetime.fromtimestamp(1707177600, tz=timezone.utc),
    compliance_status=ComplianceStatus.WARNING  # From validator
)
```

### Configuration Schema

**Source:** [project-context.md#Configuration-Loading]

```python
# config.py
from dataclasses import dataclass, field

@dataclass
class RedditClientConfig:
    """Reddit API credentials - loaded from environment variables."""
    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str = "DAWO.ECO/1.0.0 (by /u/dawo_bot)"

@dataclass
class RedditScannerConfig:
    """Scanner configuration - loaded from config file via injection."""
    subreddits: list[str] = field(default_factory=lambda: [
        "Nootropics",
        "Supplements",
        "MushroomSupplements",
        "Biohackers"
    ])
    keywords: list[str] = field(default_factory=lambda: [
        "lion's mane", "lions mane",
        "chaga",
        "reishi",
        "cordyceps",
        "shiitake",
        "maitake"
    ])
    min_upvotes: int = 10
    time_filter: str = "day"  # "hour", "day", "week", "month", "year"
    max_posts_per_subreddit: int = 100
    rate_limit_requests_per_minute: int = 60
```

**config/dawo_reddit_scanner.json:**
```json
{
  "subreddits": [
    "Nootropics",
    "Supplements",
    "MushroomSupplements",
    "Biohackers"
  ],
  "keywords": [
    "lion's mane",
    "lions mane",
    "chaga",
    "reishi",
    "cordyceps",
    "shiitake",
    "maitake"
  ],
  "min_upvotes": 10,
  "time_filter": "day",
  "max_posts_per_subreddit": 100,
  "rate_limit_requests_per_minute": 60,
  "schedule": {
    "cron": "0 2 * * *",
    "timezone": "Europe/Oslo"
  }
}
```

### Retry Middleware Integration

**Source:** [1-5-external-api-retry-middleware.md], [project-context.md#External-API-Calls]

**ALL Reddit API calls MUST go through retry middleware:**

```python
# tools.py
from teams.dawo.middleware.retry import with_retry, RetryConfig

class RedditClient:
    def __init__(
        self,
        config: RedditClientConfig,
        retry_middleware: RetryMiddleware  # Inject from Story 1.5
    ):
        self._config = config
        self._retry = retry_middleware

    @with_retry(RetryConfig(max_attempts=3, backoff_base=1.0))
    async def search_subreddit(self, subreddit: str, query: str, ...) -> list[dict]:
        """Search with automatic retry on failure."""
        # API call implementation
        ...
```

### Integration with Existing Components

**Source:** [2-1-research-pool-database-storage.md#Integration-Points], [2-2-research-item-scoring-engine.md#Integration-Points]

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

The Reddit Scanner uses `tier="scan"` (maps to Haiku at runtime).

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- `claude-haiku`, `claude-sonnet`, `claude-opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="reddit_scanner",
    agent_class=RedditScanner,
    capabilities=["reddit_research", "research_scanning"],
    tier="scan"  # Maps to Haiku at runtime - NEVER use model names
)
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [2-1-research-pool-database-storage.md#Completion-Notes-List], [2-2-research-item-scoring-engine.md#Completion-Notes-List]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="scan"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| SQLAlchemy reserved word fix | Use `source_metadata` not `metadata` |
| Add logging to exception handlers | All exceptions logged before re-raising |
| Extract magic numbers to constants | `MIN_UPVOTES = 10`, `RATE_LIMIT = 60`, etc. |
| TDD approach | Write tests first for each task |
| Unit tests with mocking | Mock Reddit API for all tests |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], [architecture.md#Anti-Patterns]

1. **NEVER load config directly** - Accept via injection
   ```python
   # WRONG
   with open("config/dawo_reddit_scanner.json") as f:
       config = json.load(f)

   # CORRECT
   def __init__(self, config: RedditScannerConfig):
       self._config = config
   ```

2. **NEVER make direct API calls without retry wrapper**
   ```python
   # WRONG
   async with session.get(url) as resp:
       return await resp.json()

   # CORRECT
   @with_retry(RetryConfig(max_attempts=3))
   async def _api_call(self, url: str) -> dict:
       async with self._session.get(url) as resp:
           return await resp.json()
   ```

3. **NEVER use LLM model names**
   ```python
   # WRONG
   tier="haiku"  # ❌

   # CORRECT
   tier="scan"   # ✅
   ```

4. **NEVER swallow exceptions without logging**
   ```python
   # WRONG
   try:
       posts = await self._client.search(...)
   except Exception:
       return []  # Silent failure

   # CORRECT
   try:
       posts = await self._client.search(...)
   except Exception as e:
       logger.error(f"Reddit search failed for {subreddit}: {e}")
       raise RedditScanError(f"Search failed: {e}") from e
   ```

### Graceful Degradation Pattern

**Source:** [prd.md#Technical-Constraints], [architecture.md#Error-Handling]

```python
# pipeline.py
class RedditResearchPipeline:
    async def execute(self) -> PipelineResult:
        """Execute full pipeline with graceful degradation."""
        try:
            raw_posts = await self._scanner.scan()
            harvested = await self._harvester.harvest(raw_posts)
            transformed = await self._transformer.transform(harvested)
            validated = await self._validator.validate(transformed)
            scored = await self._score_items(validated)
            published = await self._publisher.publish_batch(scored)

            return PipelineResult(
                status=PipelineStatus.COMPLETE,
                stats=self._calculate_stats(raw_posts, harvested, transformed, validated, published)
            )

        except RedditAPIError as e:
            logger.error(f"Reddit API failure: {e}")
            # Mark as incomplete - will retry next cycle
            return PipelineResult(
                status=PipelineStatus.INCOMPLETE,
                error=str(e),
                retry_scheduled=True
            )

        except Exception as e:
            logger.error(f"Unexpected pipeline error: {e}")
            # Critical failure - alert operator
            await self._notify_failure(e)
            raise PipelineError(f"Pipeline failed: {e}") from e
```

### Exports Template (MUST FOLLOW)

**Source:** [project-context.md#Module-Exports]

```python
# teams/dawo/scanners/reddit/__init__.py
"""Reddit Research Scanner for DAWO research intelligence pipeline."""

from .agent import RedditScanner
from .tools import RedditClient
from .config import RedditClientConfig, RedditScannerConfig
from .schemas import RawRedditPost, HarvestedPost, ScanResult, PipelineResult
from .harvester import RedditHarvester
from .transformer import RedditTransformer
from .validator import RedditValidator
from .pipeline import RedditResearchPipeline

__all__ = [
    # Main agent
    "RedditScanner",
    # Client
    "RedditClient",
    # Config
    "RedditClientConfig",
    "RedditScannerConfig",
    # Schemas
    "RawRedditPost",
    "HarvestedPost",
    "ScanResult",
    "PipelineResult",
    # Pipeline stages
    "RedditHarvester",
    "RedditTransformer",
    "RedditValidator",
    "RedditResearchPipeline",
]
```

### Test Fixtures

**Source:** [2-2-research-item-scoring-engine.md#Test-Data-Fixtures]

```python
# tests/teams/dawo/test_scanners/test_reddit/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

@pytest.fixture
def mock_reddit_response():
    """Mock Reddit API search response."""
    return {
        "kind": "Listing",
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc123",
                        "title": "My experience with lion's mane for brain fog",
                        "selftext": "Been taking lion's mane for 3 months and noticed significant improvements...",
                        "author": "user123",
                        "subreddit": "Nootropics",
                        "score": 150,
                        "upvote_ratio": 0.95,
                        "num_comments": 45,
                        "permalink": "/r/Nootropics/comments/abc123/my_experience/",
                        "created_utc": 1707177600,
                        "is_self": True
                    }
                }
            ]
        }
    }

@pytest.fixture
def mock_reddit_client(mock_reddit_response):
    """Mock RedditClient for testing without API calls."""
    client = AsyncMock(spec=RedditClient)
    client.search_subreddit.return_value = mock_reddit_response["data"]["children"]
    client.get_post_details.return_value = mock_reddit_response["data"]["children"][0]["data"]
    return client

@pytest.fixture
def scanner_config():
    """Test scanner configuration."""
    return RedditScannerConfig(
        subreddits=["Nootropics"],
        keywords=["lion's mane"],
        min_upvotes=10,
        time_filter="day"
    )
```

### Project Structure Notes

- **First scanner**: Establishes pattern for YouTube, Instagram, News, PubMed scanners
- **Follows Harvester Framework**: scanner → harvester → transformer → validator → publisher
- **Integrates with**: Research Pool (2.1), Scoring Engine (2.2), EU Compliance (1.2), Retry Middleware (1.5)
- **Tier**: `scan` (maps to Haiku at runtime)

### References

- [Source: epics.md#Story-2.3] - Original story requirements
- [Source: architecture.md#Harvester-Framework] - Pipeline pattern
- [Source: architecture.md#External-Integration-Points] - Reddit integration
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology
- [Source: prd.md#Integration-Requirements] - Reddit API specs
- [Source: 2-1-research-pool-database-storage.md] - Research Pool integration
- [Source: 2-2-research-item-scoring-engine.md] - Scoring integration
- [Source: 1-2-eu-compliance-checker-validator.md] - Compliance integration
- [Source: 1-5-external-api-retry-middleware.md] - Retry middleware integration

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

1. **Complete Harvester Framework Implementation**: First scanner implementing the full pipeline pattern: Scanner → Harvester → Transformer → Validator → Scorer → Publisher → Research Pool

2. **Mock patterns for async vs sync**: `ResearchItemScorer.calculate_score()` is synchronous - use `MagicMock` not `AsyncMock`. Validator, Harvester, and other async methods use `AsyncMock`.

3. **Pipeline return value handling**: `_publish_items()` returns `tuple[int, list[UUID]]` to properly track batch vs individual publish counts. Batch success returns `(count, [])`, individual fallback returns `(len(ids), ids)`.

4. **Rate limiting implementation**: Client tracks `_last_request_time` and calculates wait time based on `_min_request_interval` (60 requests/minute = 1 second between requests).

5. **Deleted/removed post detection**: Harvester checks for `[deleted]`, `[removed]` authors, and `removed_by_category` field to skip posts gracefully.

6. **Auto-tagging system**: Transformer generates tags from:
   - Mushroom keywords (lion's mane → lions_mane)
   - Topic keywords (brain, focus, memory → cognitive)
   - Subreddit references

7. **Compliance status mapping**: Validator maps `OverallStatus` from EUComplianceChecker to `ComplianceStatus` values (COMPLIANT, WARNING, REJECTED).

8. **Graceful degradation**: Pipeline returns INCOMPLETE on `RedditAPIError` with `retry_scheduled=True`. Returns PARTIAL if some items fail during publish.

9. **102 tests passing**: Comprehensive test coverage including unit tests for all components and integration tests for pipeline flow.

10. **Code Review (2026-02-06)**: Adversarial review found and fixed 5 issues:
    - MEDIUM: Added 8 missing exports to `scanners/__init__.py` (ValidatedResearch, ScanStatistics, etc.)
    - MEDIUM: Documented `prompts.py` as reserved for future LLM-enhanced filtering
    - LOW: Added docstring to `_apply_filters()` explaining time_filter="day" only filtering
    - LOW: Added docstring to `_rate_limit_wait()` explaining monotonic time choice
    - LOW: Added config constants exports to parent module

### File List

**New Files Created:**
- `teams/dawo/scanners/__init__.py`
- `teams/dawo/scanners/reddit/__init__.py`
- `teams/dawo/scanners/reddit/agent.py`
- `teams/dawo/scanners/reddit/config.py`
- `teams/dawo/scanners/reddit/harvester.py`
- `teams/dawo/scanners/reddit/pipeline.py`
- `teams/dawo/scanners/reddit/schemas.py`
- `teams/dawo/scanners/reddit/tools.py`
- `teams/dawo/scanners/reddit/transformer.py`
- `teams/dawo/scanners/reddit/validator.py`
- `config/dawo_reddit_scanner.json`
- `tests/teams/dawo/test_scanners/__init__.py`
- `tests/teams/dawo/test_scanners/test_reddit/__init__.py`
- `tests/teams/dawo/test_scanners/test_reddit/conftest.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_client.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_config.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_harvester.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_integration.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_pipeline.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_scanner.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_schemas.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_transformer.py`
- `tests/teams/dawo/test_scanners/test_reddit/test_validator.py`

**Modified Files:**
- `teams/dawo/team_spec.py` - Added RedditScanner agent and pipeline services registration
- `teams/dawo/scanners/__init__.py` - [Code Review] Added 8 missing exports + config constants
- `teams/dawo/scanners/reddit/prompts.py` - [Code Review] Documented as reserved for future use
- `teams/dawo/scanners/reddit/agent.py` - [Code Review] Added docstring for time filter behavior
- `teams/dawo/scanners/reddit/tools.py` - [Code Review] Added docstring for monotonic time choice

