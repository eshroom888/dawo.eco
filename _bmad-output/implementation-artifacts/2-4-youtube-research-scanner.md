# Story 2.4: YouTube Research Scanner

Status: completed

---

## Story

As an **operator**,
I want YouTube searched for mushroom supplement content,
So that video insights and trends inform our content strategy.

---

## Acceptance Criteria

1. **Given** the YouTube scanner is scheduled (weekly Sunday 3 AM)
   **When** it executes
   **Then** it searches YouTube Data API for: mushroom supplements, lion's mane benefits, adaptogen reviews
   **And** it filters for videos from last 7 days with 1,000+ views
   **And** it prioritizes health/wellness channels

2. **Given** a video is selected
   **When** the harvester processes it
   **Then** it extracts video transcript using YouTube transcript API
   **And** key_insight_extractor (Sonnet) summarizes main points
   **And** it captures: title, channel, views, publish date, transcript summary

3. **Given** a video transcript is extracted
   **When** the transformer processes it
   **Then** it identifies quotable insights (max 3 per video)
   **And** it tags with relevant topics
   **And** it validates compliance before pool entry

4. **Given** YouTube API is unavailable
   **When** retry middleware exhausts attempts
   **Then** the scan is marked INCOMPLETE and queued for next cycle
   **And** previous research remains available

---

## Tasks / Subtasks

- [x] Task 1: Create YouTube scanner agent structure (AC: #1, #2)
  - [x] 1.1 Create `teams/dawo/scanners/youtube/` directory structure
  - [x] 1.2 Create `__init__.py` with complete exports
  - [x] 1.3 Create `agent.py` with `YouTubeScanner` class
  - [x] 1.4 Create `prompts.py` with key insight extraction prompts (uses generate tier)
  - [x] 1.5 Create `tools.py` with YouTube API tools
  - [x] 1.6 Create `config.py` with `YouTubeScannerConfig` dataclass
  - [x] 1.7 Create `schemas.py` with `RawYouTubeVideo`, `HarvestedVideo`, `QuotableInsight` schemas

- [x] Task 2: Implement YouTube Data API client (AC: #1, #4)
  - [x] 2.1 Create `YouTubeClient` class in `tools.py`
  - [x] 2.2 Accept API key via dependency injection
  - [x] 2.3 Implement `search_videos(query: str, published_after: datetime, max_results: int) -> list[dict]`
  - [x] 2.4 Filter by: video type, relevanceLanguage=en, videoCategoryId (health/wellness)
  - [x] 2.5 Implement `get_video_details(video_id: str) -> dict` for statistics
  - [x] 2.6 Add rate limiting (10,000 units/day quota, cost varies by endpoint)
  - [x] 2.7 Wrap all API calls with retry middleware (Story 1.5)

- [x] Task 3: Implement YouTube Transcript API client (AC: #2)
  - [x] 3.1 Use `youtube-transcript-api` Python package
  - [x] 3.2 Create `get_transcript(video_id: str, languages: list[str]) -> str`
  - [x] 3.3 Handle missing transcripts gracefully (auto-generated, unavailable)
  - [x] 3.4 Prefer manual captions over auto-generated when available
  - [x] 3.5 Concatenate transcript segments into full text
  - [x] 3.6 Wrap with retry middleware

- [x] Task 4: Implement scanner stage (AC: #1)
  - [x] 4.1 Create `scan()` method that searches configured queries
  - [x] 4.2 Search queries: "mushroom supplements", "lion's mane benefits", "adaptogen reviews"
  - [x] 4.3 Filter results by: published date (last 7 days), view count (1,000+)
  - [x] 4.4 Deduplicate results by video ID
  - [x] 4.5 Return list of `RawYouTubeVideo` objects
  - [x] 4.6 Log scan statistics: queries searched, videos found, duplicates removed

- [x] Task 5: Implement harvester stage (AC: #2)
  - [x] 5.1 Create `YouTubeHarvester` class
  - [x] 5.2 Accept `YouTubeClient` and `TranscriptClient` via dependency injection
  - [x] 5.3 Implement `harvest(raw_videos: list[RawYouTubeVideo]) -> list[HarvestedVideo]`
  - [x] 5.4 For each video, fetch: full details (title, channel, views, publish date), transcript
  - [x] 5.5 Handle videos without transcripts (skip with log, set transcript_available=False)
  - [x] 5.6 Rate limit API calls per YouTube quota guidelines

- [x] Task 6: Implement key insight extractor (AC: #2)
  - [x] 6.1 Create `KeyInsightExtractor` class
  - [x] 6.2 Use `tier="generate"` (Sonnet) for summarization quality
  - [x] 6.3 Implement `extract_insights(transcript: str, title: str) -> InsightResult`
  - [x] 6.4 Generate: main_summary (100-200 words), quotable_insights (max 3), key_topics
  - [x] 6.5 Prompt to identify: actionable claims, product mentions, research references
  - [x] 6.6 Return structured InsightResult with summary and insights list

- [x] Task 7: Implement transformer stage (AC: #3)
  - [x] 7.1 Create `YouTubeTransformer` class
  - [x] 7.2 Accept `KeyInsightExtractor` via dependency injection
  - [x] 7.3 Implement `transform(harvested: list[HarvestedVideo]) -> list[TransformedResearch]`
  - [x] 7.4 Map YouTube fields to Research Pool schema:
        - `source`: "youtube"
        - `title`: video title
        - `content`: transcript summary + quotable insights
        - `url`: full YouTube video URL
        - `tags`: auto-generate from topics + mushroom keywords
        - `source_metadata`: {channel, views, publish_date, video_id, has_transcript, insight_count}
        - `created_at`: video publish timestamp
  - [x] 7.5 Create separate research item for each quotable insight (optional, configurable)
  - [x] 7.6 Sanitize content: remove URLs, truncate if > 10,000 chars

- [x] Task 8: Implement validator stage (AC: #3)
  - [x] 8.1 Create `YouTubeValidator` class
  - [x] 8.2 Accept `EUComplianceChecker` via dependency injection (from Story 1.2)
  - [x] 8.3 Implement `validate(items: list[TransformedResearch]) -> list[ValidatedResearch]`
  - [x] 8.4 Call compliance checker on summary + insights
  - [x] 8.5 Set `compliance_status` based on checker result (COMPLIANT, WARNING, REJECTED)
  - [x] 8.6 Log validation statistics: passed, warned, rejected

- [x] Task 9: Integrate with Research Publisher (AC: #3)
  - [x] 9.1 Accept `ResearchPublisher` via dependency injection (from Story 2.1)
  - [x] 9.2 Accept `ResearchItemScorer` via dependency injection (from Story 2.2)
  - [x] 9.3 Implement `publish_results(validated: list[ValidatedResearch]) -> list[ResearchItem]`
  - [x] 9.4 Score each item before publishing (boost for peer-reviewed channel content)
  - [x] 9.5 Publish to Research Pool via publisher
  - [x] 9.6 Return created ResearchItem list with IDs

- [x] Task 10: Create orchestrated pipeline (AC: #1, #2, #3)
  - [x] 10.1 Create `YouTubeResearchPipeline` class
  - [x] 10.2 Accept all stage components via dependency injection
  - [x] 10.3 Implement `execute() -> PipelineResult`
  - [x] 10.4 Chain stages: scan -> harvest -> extract_insights -> transform -> validate -> score -> publish
  - [x] 10.5 Track and return statistics: total_found, harvested, transcripts_extracted, insights_generated, validated, published
  - [x] 10.6 Handle partial failures: continue pipeline even if some videos fail

- [x] Task 11: Implement graceful degradation (AC: #4)
  - [x] 11.1 Wrap pipeline execution in try/catch
  - [x] 11.2 On API failure (after retries), mark scan as INCOMPLETE
  - [x] 11.3 Log failure details for debugging
  - [x] 11.4 Queue for next scheduled run (via ARQ job queue)
  - [x] 11.5 Ensure existing Research Pool data remains intact
  - [x] 11.6 Handle quota exhaustion separately (wait until next day, notify operator)

- [x] Task 12: Register in team_spec.py (AC: #1)
  - [x] 12.1 Add `YouTubeScanner` as RegisteredAgent with tier="scan"
  - [x] 12.2 Add `KeyInsightExtractor` as RegisteredAgent with tier="generate" (Sonnet for quality)
  - [x] 12.3 Add `YouTubeHarvester` as RegisteredService
  - [x] 12.4 Add `YouTubeTransformer` as RegisteredService
  - [x] 12.5 Add `YouTubeValidator` as RegisteredService
  - [x] 12.6 Add `YouTubeResearchPipeline` as RegisteredService with capability="youtube_research"
  - [x] 12.7 Ensure all components are injectable via Team Builder

- [x] Task 13: Create configuration file (AC: #1)
  - [x] 13.1 Create `config/dawo_youtube_scanner.json`
  - [x] 13.2 Define search queries: ["mushroom supplements", "lion's mane benefits", "adaptogen reviews"]
  - [x] 13.3 Define filters: min_views=1000, days_back=7
  - [x] 13.4 Define schedule: cron expression for weekly Sunday 3 AM
  - [x] 13.5 Define max_videos_per_query: 50
  - [x] 13.6 Define languages for transcript: ["en", "en-US", "en-GB"]
  - [x] 13.7 Add YouTube API key placeholder (loaded from env vars)

- [x] Task 14: Create comprehensive unit tests
  - [x] 14.1 Test YouTubeClient search and detail methods
  - [x] 14.2 Test TranscriptClient with various caption scenarios
  - [x] 14.3 Test scanner filtering (views, date, keywords)
  - [x] 14.4 Test harvester data extraction
  - [x] 14.5 Test KeyInsightExtractor prompt and response parsing
  - [x] 14.6 Test transformer field mapping and insight splitting
  - [x] 14.7 Test validator compliance integration
  - [x] 14.8 Test pipeline orchestration
  - [x] 14.9 Test graceful degradation on API failure
  - [x] 14.10 Test quota exhaustion handling
  - [x] 14.11 Mock YouTube API responses for all tests

- [x] Task 15: Create integration tests
  - [x] 15.1 Test full pipeline with mocked YouTube API
  - [x] 15.2 Test Research Pool insertion (with test database)
  - [x] 15.3 Test scoring integration
  - [x] 15.4 Test retry middleware integration
  - [x] 15.5 Test LLM insight extraction with mock responses

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Harvester-Framework], [project-context.md#Code-Organization]

This is the **SECOND scanner** in the Harvester Framework - it MUST follow the exact pattern established by Reddit Scanner (Story 2.3).

**Harvester Framework Pipeline (Extended for YouTube):**
```
[Scanner] -> [Harvester] -> [Insight Extractor] -> [Transformer] -> [Validator] -> [Scorer] -> [Publisher] -> [Research Pool]
     |           |                  |                    |              |            |           |
   scan()    harvest()        extract_insights()    transform()    validate()    score()    publish()
   tier=scan  tier=scan        tier=generate         tier=scan      tier=scan   tier=scan   tier=scan
```

**Key Difference from Reddit Scanner:** YouTube pipeline includes an additional LLM-powered stage (`KeyInsightExtractor`) that uses `tier="generate"` (Sonnet) for quality summarization of video transcripts.

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Directory-Structure]

```
teams/dawo/
├── scanners/
│   ├── reddit/                        # EXISTS from Story 2.3
│   │   └── ...
│   └── youtube/                       # CREATE THIS MODULE
│       ├── __init__.py                # Export all public types
│       ├── agent.py                   # YouTubeScanner main class
│       ├── prompts.py                 # KeyInsightExtractor prompts (REQUIRED - uses LLM)
│       ├── tools.py                   # YouTubeClient, TranscriptClient, API tools
│       ├── config.py                  # YouTubeScannerConfig
│       ├── schemas.py                 # RawYouTubeVideo, HarvestedVideo, QuotableInsight
│       ├── harvester.py               # YouTubeHarvester
│       ├── insight_extractor.py       # KeyInsightExtractor (tier=generate)
│       ├── transformer.py             # YouTubeTransformer
│       ├── validator.py               # YouTubeValidator
│       └── pipeline.py                # YouTubeResearchPipeline
├── research/                          # Exists from Story 2.1
│   ├── models.py                      # ResearchItem, ResearchSource
│   ├── repository.py                  # ResearchPoolRepository
│   ├── publisher.py                   # ResearchPublisher
│   └── scoring/                       # Exists from Story 2.2
│       └── scorer.py                  # ResearchItemScorer

config/
└── dawo_youtube_scanner.json          # CREATE: Scanner configuration

tests/teams/dawo/
└── test_scanners/
    ├── test_reddit/                   # EXISTS from Story 2.3
    └── test_youtube/                  # CREATE THIS
        ├── __init__.py
        ├── conftest.py                # Fixtures, mocks
        ├── test_client.py             # YouTubeClient tests
        ├── test_transcript.py         # TranscriptClient tests
        ├── test_scanner.py            # Scanner stage tests
        ├── test_harvester.py          # Harvester stage tests
        ├── test_insight_extractor.py  # LLM insight tests
        ├── test_transformer.py        # Transformer stage tests
        ├── test_validator.py          # Validator stage tests
        ├── test_pipeline.py           # Full pipeline tests
        └── test_integration.py        # Integration with Research Pool
```

### YouTube Data API v3 Integration

**Source:** [prd.md#Integration-Requirements], [architecture.md#External-Integration-Points]

**API Details:**
- **Base URL:** `https://www.googleapis.com/youtube/v3`
- **Auth:** API Key (server-side)
- **Quota:** 10,000 units/day
- **Quota Costs:**
  - search.list: 100 units
  - videos.list: 1 unit per video (batch up to 50)

**Search Endpoint:**
```python
# tools.py
class YouTubeClient:
    """YouTube Data API v3 client.

    Accepts API key via dependency injection - NEVER loads from file.
    """

    SEARCH_COST = 100  # units per search call
    VIDEO_COST = 1     # units per video in batch (max 50)
    DAILY_QUOTA = 10000

    def __init__(self, config: YouTubeClientConfig, retry_middleware: RetryMiddleware):
        """Accept config via injection from Team Builder."""
        self._config = config
        self._retry = retry_middleware
        self._session: Optional[aiohttp.ClientSession] = None
        self._quota_used_today = 0

    @with_retry(RetryConfig(max_attempts=3, backoff_base=2.0))
    async def search_videos(
        self,
        query: str,
        published_after: datetime,
        max_results: int = 50
    ) -> list[dict]:
        """Search for videos matching query.

        Args:
            query: Search keywords
            published_after: Only videos published after this date
            max_results: Max results (YouTube caps at 50)

        Returns:
            List of video search results

        Raises:
            QuotaExhaustedError: If daily quota exceeded
        """
        if self._quota_used_today + self.SEARCH_COST > self.DAILY_QUOTA:
            raise QuotaExhaustedError("YouTube daily quota exhausted")

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "publishedAfter": published_after.isoformat() + "Z",
            "maxResults": max_results,
            "order": "relevance",
            "relevanceLanguage": "en",
            "key": self._config.api_key
        }
        # ... API call with retry middleware
        self._quota_used_today += self.SEARCH_COST
```

**Video Details Endpoint (for view counts):**
```python
async def get_video_statistics(
    self,
    video_ids: list[str]
) -> dict[str, dict]:
    """Get statistics for multiple videos (batch).

    Args:
        video_ids: List of video IDs (max 50)

    Returns:
        Dict mapping video_id to statistics
    """
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "statistics,snippet,contentDetails",
        "id": ",".join(video_ids[:50]),
        "key": self._config.api_key
    }
    # ... API call
    self._quota_used_today += len(video_ids)
```

### YouTube Transcript API Integration

**Source:** [epics.md#Story-2.4]

**Package:** `youtube-transcript-api` (Python)
**Installation:** `pip install youtube-transcript-api`

```python
# tools.py
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

class TranscriptClient:
    """YouTube transcript extraction client."""

    PREFERRED_LANGUAGES = ["en", "en-US", "en-GB"]

    def __init__(self, retry_middleware: RetryMiddleware):
        self._retry = retry_middleware

    async def get_transcript(
        self,
        video_id: str,
        languages: Optional[list[str]] = None
    ) -> TranscriptResult:
        """Extract transcript from YouTube video.

        Args:
            video_id: YouTube video ID
            languages: Preferred languages (falls back to auto-generated)

        Returns:
            TranscriptResult with text and metadata
        """
        languages = languages or self.PREFERRED_LANGUAGES

        try:
            # Prefer manual captions
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
                is_auto_generated = False
            except NoTranscriptFound:
                transcript = transcript_list.find_generated_transcript(languages)
                is_auto_generated = True

            segments = transcript.fetch()
            full_text = " ".join(seg["text"] for seg in segments)

            return TranscriptResult(
                text=full_text,
                language=transcript.language_code,
                is_auto_generated=is_auto_generated,
                duration_seconds=segments[-1]["start"] + segments[-1]["duration"] if segments else 0
            )

        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video {video_id}")
            return TranscriptResult(text="", available=False, reason="disabled")
        except NoTranscriptFound:
            logger.warning(f"No transcript found for video {video_id}")
            return TranscriptResult(text="", available=False, reason="not_found")
```

### Key Insight Extractor (LLM Stage)

**Source:** [epics.md#Story-2.4], [project-context.md#LLM-Tier-Assignment]

**CRITICAL:** This is the first scanner pipeline that uses an LLM stage. Use `tier="generate"` (maps to Sonnet) for quality summarization.

```python
# insight_extractor.py
from dataclasses import dataclass

@dataclass
class InsightResult:
    """Result from key insight extraction."""
    main_summary: str  # 100-200 words
    quotable_insights: list[QuotableInsight]  # Max 3
    key_topics: list[str]
    confidence_score: float

@dataclass
class QuotableInsight:
    """A quotable insight from the video."""
    text: str  # The quotable statement
    context: str  # Surrounding context
    topic: str  # Related topic
    is_claim: bool  # Whether it makes a health claim

class KeyInsightExtractor:
    """LLM-powered insight extraction from video transcripts.

    Uses tier="generate" (Sonnet) for quality summarization.
    """

    def __init__(self, llm_client: LLMClient):
        """Accept LLM client via injection."""
        self._llm = llm_client

    async def extract_insights(
        self,
        transcript: str,
        video_title: str,
        channel_name: str
    ) -> InsightResult:
        """Extract key insights from video transcript.

        Args:
            transcript: Full video transcript text
            video_title: Video title for context
            channel_name: Channel name for credibility assessment

        Returns:
            InsightResult with summary and quotable insights
        """
        # See prompts.py for the full extraction prompt
        ...
```

**prompts.py:**
```python
# prompts.py
"""System prompts for YouTube insight extraction.

Uses tier="generate" (Sonnet) for quality summarization.
"""

KEY_INSIGHT_EXTRACTION_PROMPT = """
You are a research analyst extracting key insights from mushroom supplement video content.

VIDEO CONTEXT:
- Title: {video_title}
- Channel: {channel_name}
- Transcript length: {transcript_length} words

TASK:
Analyze this video transcript and extract:

1. MAIN SUMMARY (100-200 words):
   - Core message of the video
   - Key claims or information presented
   - Target audience and tone

2. QUOTABLE INSIGHTS (max 3):
   For each insight, provide:
   - text: The exact or near-exact quotable statement
   - context: Brief context explaining relevance
   - topic: Primary topic (e.g., "lion's mane cognition", "dosage")
   - is_claim: true if it makes a health claim, false otherwise

3. KEY TOPICS (3-7 topics):
   Tag with relevant topics from: lions_mane, chaga, reishi, cordyceps, shiitake, maitake,
   cognition, energy, immunity, dosage, research, anecdotal, beginner, expert

IMPORTANT:
- Focus on factual information and research references
- Flag any unsubstantiated health claims
- Identify if the channel is medical/research-focused or lifestyle/influencer
- Do NOT include promotional or affiliate content

TRANSCRIPT:
{transcript}

Respond in JSON format:
{{
    "main_summary": "...",
    "quotable_insights": [
        {{"text": "...", "context": "...", "topic": "...", "is_claim": true/false}}
    ],
    "key_topics": ["...", "..."],
    "confidence_score": 0.0-1.0
}}
"""
```

### YouTube Video Data Structure

**Source:** [2-1-research-pool-database-storage.md#Metadata-JSONB-Structure]

**Raw YouTube API Response:**
```python
{
    "kind": "youtube#searchResult",
    "id": {"videoId": "abc123xyz"},
    "snippet": {
        "publishedAt": "2026-02-01T10:00:00Z",
        "channelId": "UCxxxxxxx",
        "title": "Lion's Mane Benefits: What Science Actually Says",
        "description": "In this video we explore...",
        "channelTitle": "Health Science Channel",
        "thumbnails": {...}
    }
}

# After videos.list call for statistics:
{
    "statistics": {
        "viewCount": "15234",
        "likeCount": "1200",
        "commentCount": "89"
    },
    "contentDetails": {
        "duration": "PT15M30S"  # 15 minutes 30 seconds
    }
}
```

**Transformed to Research Pool Schema:**
```python
ResearchItem(
    source=ResearchSource.YOUTUBE,
    title="Lion's Mane Benefits: What Science Actually Says",
    content="""
    SUMMARY: This video from Health Science Channel explores the scientific evidence
    behind lion's mane mushroom benefits...

    KEY INSIGHTS:
    1. "Studies show lion's mane may support nerve growth factor production" - Research reference
    2. "Typical dosage ranges from 500mg to 3000mg daily" - Dosage information
    """,
    url="https://www.youtube.com/watch?v=abc123xyz",
    tags=["lions_mane", "cognition", "research", "dosage"],
    source_metadata={
        "channel": "Health Science Channel",
        "channel_id": "UCxxxxxxx",
        "video_id": "abc123xyz",
        "views": 15234,
        "likes": 1200,
        "comments": 89,
        "duration_seconds": 930,
        "publish_date": "2026-02-01T10:00:00Z",
        "has_transcript": True,
        "transcript_language": "en",
        "is_auto_generated": False,
        "insight_count": 2
    },
    created_at=datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
    compliance_status=ComplianceStatus.WARNING  # From validator
)
```

### Configuration Schema

**Source:** [project-context.md#Configuration-Loading]

```python
# config.py
from dataclasses import dataclass, field

@dataclass
class YouTubeClientConfig:
    """YouTube API credentials - loaded from environment variables."""
    api_key: str

@dataclass
class TranscriptConfig:
    """Transcript extraction configuration."""
    preferred_languages: list[str] = field(default_factory=lambda: ["en", "en-US", "en-GB"])
    max_transcript_length: int = 50000  # chars

@dataclass
class YouTubeScannerConfig:
    """Scanner configuration - loaded from config file via injection."""
    search_queries: list[str] = field(default_factory=lambda: [
        "mushroom supplements",
        "lion's mane benefits",
        "adaptogen reviews",
        "cordyceps supplement",
        "reishi mushroom health"
    ])
    min_views: int = 1000
    days_back: int = 7
    max_videos_per_query: int = 50
    health_channel_keywords: list[str] = field(default_factory=lambda: [
        "health", "science", "medical", "nutrition", "wellness", "doctor", "research"
    ])
```

**config/dawo_youtube_scanner.json:**
```json
{
  "search_queries": [
    "mushroom supplements",
    "lion's mane benefits",
    "adaptogen reviews",
    "cordyceps supplement",
    "reishi mushroom health"
  ],
  "min_views": 1000,
  "days_back": 7,
  "max_videos_per_query": 50,
  "health_channel_keywords": [
    "health", "science", "medical", "nutrition", "wellness", "doctor", "research"
  ],
  "transcript_config": {
    "preferred_languages": ["en", "en-US", "en-GB"],
    "max_transcript_length": 50000
  },
  "schedule": {
    "cron": "0 3 * * 0",
    "timezone": "Europe/Oslo"
  }
}
```

### Retry Middleware Integration

**Source:** [1-5-external-api-retry-middleware.md], [project-context.md#External-API-Calls]

**ALL YouTube API calls MUST go through retry middleware:**

```python
# tools.py
from teams.dawo.middleware.retry import with_retry, RetryConfig

class YouTubeClient:
    def __init__(
        self,
        config: YouTubeClientConfig,
        retry_middleware: RetryMiddleware  # Inject from Story 1.5
    ):
        self._config = config
        self._retry = retry_middleware

    @with_retry(RetryConfig(max_attempts=3, backoff_base=2.0))
    async def search_videos(self, query: str, ...) -> list[dict]:
        """Search with automatic retry on failure."""
        # API call implementation
        ...
```

### Integration with Existing Components

**Source:** [2-1-research-pool-database-storage.md#Integration-Points], [2-2-research-item-scoring-engine.md#Integration-Points], [2-3-reddit-research-scanner.md#Integration-Points]

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

**Story 2.3 - Reddit Scanner (Pattern Reference):**
```python
# Follow same patterns established in Reddit Scanner:
# - Pipeline structure
# - Graceful degradation
# - Logging conventions
# - Test patterns
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment], [project-context.md#Code-Review-Checklist]

**UNIQUE to YouTube Scanner:** This pipeline has TWO different tiers:
- `YouTubeScanner`, `YouTubeHarvester`, `YouTubeTransformer`, `YouTubeValidator`: `tier="scan"` (Haiku)
- `KeyInsightExtractor`: `tier="generate"` (Sonnet) - required for quality summarization

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- `claude-haiku`, `claude-sonnet`, `claude-opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="youtube_scanner",
    agent_class=YouTubeScanner,
    capabilities=["youtube_research", "research_scanning"],
    tier="scan"  # Maps to Haiku at runtime
)

RegisteredAgent(
    name="key_insight_extractor",
    agent_class=KeyInsightExtractor,
    capabilities=["insight_extraction", "content_summarization"],
    tier="generate"  # Maps to Sonnet at runtime - REQUIRED for quality
)
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [2-3-reddit-research-scanner.md#Completion-Notes-List]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="scan"` or `tier="generate"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| SQLAlchemy reserved word fix | Use `source_metadata` not `metadata` |
| Add logging to exception handlers | All exceptions logged before re-raising |
| Extract magic numbers to constants | `MIN_VIEWS = 1000`, `DAYS_BACK = 7`, etc. |
| TDD approach | Write tests first for each task |
| Unit tests with mocking | Mock YouTube API for all tests |
| Mock patterns: async vs sync | `ResearchItemScorer.calculate_score()` is sync - use `MagicMock` |
| Pipeline return value handling | Track batch vs individual publish counts |
| Rate limiting implementation | Track quota usage for YouTube's daily limit |
| Graceful degradation | Return INCOMPLETE on API failure, PARTIAL on item failures |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], [architecture.md#Anti-Patterns]

1. **NEVER load config directly** - Accept via injection
   ```python
   # WRONG
   with open("config/dawo_youtube_scanner.json") as f:
       config = json.load(f)

   # CORRECT
   def __init__(self, config: YouTubeScannerConfig):
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
   tier="haiku"  # X
   tier="sonnet" # X

   # CORRECT
   tier="scan"     # Y (for high-volume tasks)
   tier="generate" # Y (for insight extraction)
   ```

4. **NEVER swallow exceptions without logging**
   ```python
   # WRONG
   try:
       videos = await self._client.search(...)
   except Exception:
       return []  # Silent failure

   # CORRECT
   try:
       videos = await self._client.search(...)
   except Exception as e:
       logger.error(f"YouTube search failed for {query}: {e}")
       raise YouTubeScanError(f"Search failed: {e}") from e
   ```

### Graceful Degradation Pattern

**Source:** [prd.md#Technical-Constraints], [architecture.md#Error-Handling]

```python
# pipeline.py
class YouTubeResearchPipeline:
    async def execute(self) -> PipelineResult:
        """Execute full pipeline with graceful degradation."""
        try:
            raw_videos = await self._scanner.scan()
            harvested = await self._harvester.harvest(raw_videos)
            with_insights = await self._extract_insights(harvested)
            transformed = await self._transformer.transform(with_insights)
            validated = await self._validator.validate(transformed)
            scored = await self._score_items(validated)
            published = await self._publisher.publish_batch(scored)

            return PipelineResult(
                status=PipelineStatus.COMPLETE,
                stats=self._calculate_stats(...)
            )

        except QuotaExhaustedError as e:
            logger.warning(f"YouTube quota exhausted: {e}")
            # Wait until tomorrow, notify operator
            return PipelineResult(
                status=PipelineStatus.QUOTA_EXCEEDED,
                error=str(e),
                retry_after=self._next_quota_reset()
            )

        except YouTubeAPIError as e:
            logger.error(f"YouTube API failure: {e}")
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

### Quota Management

**Source:** YouTube Data API Documentation

YouTube has a daily quota of 10,000 units. Track usage carefully:

```python
# tools.py
class QuotaTracker:
    """Track YouTube API quota usage."""

    DAILY_LIMIT = 10000

    def __init__(self):
        self._used_today = 0
        self._reset_date = datetime.now(timezone.utc).date()

    def check_and_use(self, cost: int) -> None:
        """Check if quota available, raise if not."""
        self._maybe_reset()
        if self._used_today + cost > self.DAILY_LIMIT:
            raise QuotaExhaustedError(
                f"Would exceed quota: {self._used_today + cost} > {self.DAILY_LIMIT}"
            )
        self._used_today += cost

    def _maybe_reset(self) -> None:
        """Reset counter if new day."""
        today = datetime.now(timezone.utc).date()
        if today > self._reset_date:
            self._used_today = 0
            self._reset_date = today
```

### Exports Template (MUST FOLLOW)

**Source:** [project-context.md#Module-Exports]

```python
# teams/dawo/scanners/youtube/__init__.py
"""YouTube Research Scanner for DAWO research intelligence pipeline."""

from .agent import YouTubeScanner
from .tools import YouTubeClient, TranscriptClient, QuotaTracker
from .config import YouTubeClientConfig, TranscriptConfig, YouTubeScannerConfig
from .schemas import (
    RawYouTubeVideo,
    HarvestedVideo,
    TranscriptResult,
    QuotableInsight,
    InsightResult,
    ScanResult,
    PipelineResult
)
from .harvester import YouTubeHarvester
from .insight_extractor import KeyInsightExtractor
from .transformer import YouTubeTransformer
from .validator import YouTubeValidator
from .pipeline import YouTubeResearchPipeline

__all__ = [
    # Main agent
    "YouTubeScanner",
    # Clients
    "YouTubeClient",
    "TranscriptClient",
    "QuotaTracker",
    # Config
    "YouTubeClientConfig",
    "TranscriptConfig",
    "YouTubeScannerConfig",
    # Schemas
    "RawYouTubeVideo",
    "HarvestedVideo",
    "TranscriptResult",
    "QuotableInsight",
    "InsightResult",
    "ScanResult",
    "PipelineResult",
    # Pipeline stages
    "YouTubeHarvester",
    "KeyInsightExtractor",
    "YouTubeTransformer",
    "YouTubeValidator",
    "YouTubeResearchPipeline",
]
```

### Test Fixtures

**Source:** [2-3-reddit-research-scanner.md#Test-Fixtures]

```python
# tests/teams/dawo/test_scanners/test_youtube/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

@pytest.fixture
def mock_youtube_search_response():
    """Mock YouTube Data API search response."""
    return {
        "items": [
            {
                "kind": "youtube#searchResult",
                "id": {"videoId": "abc123xyz"},
                "snippet": {
                    "publishedAt": "2026-02-01T10:00:00Z",
                    "channelId": "UCxxxxxxx",
                    "title": "Lion's Mane Benefits: What Science Actually Says",
                    "description": "In this video we explore...",
                    "channelTitle": "Health Science Channel"
                }
            }
        ]
    }

@pytest.fixture
def mock_video_statistics_response():
    """Mock YouTube Data API videos.list response."""
    return {
        "items": [
            {
                "id": "abc123xyz",
                "statistics": {
                    "viewCount": "15234",
                    "likeCount": "1200",
                    "commentCount": "89"
                },
                "contentDetails": {
                    "duration": "PT15M30S"
                }
            }
        ]
    }

@pytest.fixture
def mock_transcript():
    """Mock transcript text."""
    return """
    Today we're talking about lion's mane mushroom and what the research actually shows.
    Studies indicate that lion's mane may support nerve growth factor production.
    The typical dosage ranges from 500mg to 3000mg daily, depending on the form.
    Let's look at the key studies...
    """

@pytest.fixture
def mock_youtube_client(mock_youtube_search_response, mock_video_statistics_response):
    """Mock YouTubeClient for testing without API calls."""
    client = AsyncMock(spec=YouTubeClient)
    client.search_videos.return_value = mock_youtube_search_response["items"]
    client.get_video_statistics.return_value = {
        "abc123xyz": mock_video_statistics_response["items"][0]
    }
    return client

@pytest.fixture
def mock_transcript_client(mock_transcript):
    """Mock TranscriptClient for testing."""
    client = AsyncMock(spec=TranscriptClient)
    client.get_transcript.return_value = TranscriptResult(
        text=mock_transcript,
        language="en",
        is_auto_generated=False,
        available=True,
        duration_seconds=930
    )
    return client

@pytest.fixture
def scanner_config():
    """Test scanner configuration."""
    return YouTubeScannerConfig(
        search_queries=["lion's mane benefits"],
        min_views=1000,
        days_back=7,
        max_videos_per_query=10
    )
```

### Project Structure Notes

- **Second scanner**: Follows pattern established by Reddit Scanner (Story 2.3)
- **First LLM-enhanced scanner**: Includes KeyInsightExtractor with `tier="generate"`
- **Follows Harvester Framework**: scan -> harvest -> extract -> transform -> validate -> publish
- **Integrates with**: Research Pool (2.1), Scoring Engine (2.2), EU Compliance (1.2), Retry Middleware (1.5)
- **Primary tier**: `scan` (Haiku) for most stages
- **LLM tier**: `generate` (Sonnet) for KeyInsightExtractor

### References

- [Source: epics.md#Story-2.4] - Original story requirements
- [Source: architecture.md#Harvester-Framework] - Pipeline pattern
- [Source: architecture.md#External-Integration-Points] - YouTube integration
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology
- [Source: prd.md#Integration-Requirements] - YouTube API specs
- [Source: 2-1-research-pool-database-storage.md] - Research Pool integration
- [Source: 2-2-research-item-scoring-engine.md] - Scoring integration
- [Source: 2-3-reddit-research-scanner.md] - Pattern reference (FOLLOW THIS)
- [Source: 1-2-eu-compliance-checker-validator.md] - Compliance integration
- [Source: 1-5-external-api-retry-middleware.md] - Retry middleware integration

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- All 130 tests passing (119 unit + 11 integration)
- Code review fixes applied: integration tests created, config terminology fixed, conftest.py added

### File List

**Implementation Files (teams/dawo/scanners/youtube/):**
- `__init__.py` - Module exports with complete `__all__` list
- `agent.py` - YouTubeScanner main agent class
- `config.py` - YouTubeClientConfig, TranscriptConfig, YouTubeScannerConfig dataclasses
- `schemas.py` - RawYouTubeVideo, HarvestedVideo, TranscriptResult, InsightResult, ValidatedResearch, PipelineResult
- `tools.py` - YouTubeClient, TranscriptClient, QuotaTracker, exceptions
- `prompts.py` - KEY_INSIGHT_EXTRACTION_PROMPT, TAG_GENERATION_PROMPT
- `harvester.py` - YouTubeHarvester for detail/transcript enrichment
- `insight_extractor.py` - KeyInsightExtractor (tier=generate)
- `transformer.py` - YouTubeTransformer for Research Pool schema conversion
- `validator.py` - YouTubeValidator for EU compliance checking
- `pipeline.py` - YouTubeResearchPipeline orchestrator

**Configuration Files:**
- `config/dawo_youtube_scanner.json` - Scanner configuration with schedule

**Test Files (tests/teams/dawo/test_scanners/test_youtube/):**
- `__init__.py` - Test package init
- `conftest.py` - Shared test fixtures
- `test_schemas.py` - Schema tests
- `test_config.py` - Config tests
- `test_client.py` - YouTubeClient tests
- `test_transcript.py` - TranscriptClient tests
- `test_scanner.py` - Scanner stage tests
- `test_harvester.py` - Harvester stage tests
- `test_insight_extractor.py` - KeyInsightExtractor tests
- `test_transformer.py` - Transformer stage tests
- `test_validator.py` - Validator stage tests
- `test_pipeline.py` - Pipeline orchestration tests
- `test_integration.py` - Integration tests (Task 15)

**Modified Files:**
- `teams/dawo/team_spec.py` - Added YouTubeScanner registrations

