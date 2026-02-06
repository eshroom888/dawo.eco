# Epic 2 Preparation: Research Intelligence Pipeline

**Created:** 2026-02-06
**Status:** In Progress
**Epic:** 2 - Research Intelligence Pipeline (8 stories)

---

## Overview

Epic 2 builds the Research Intelligence Pipeline - automated research collection from Reddit, YouTube, Instagram, Industry News, and PubMed flowing into a searchable Research Pool.

**Dependencies from Epic 1:**
- ✅ EU Compliance Checker (Story 1.2) → Research validation
- ✅ Retry Middleware (Story 1.5) → All external API calls
- ✅ LLM Tier Config (Story 1.4) → Scanners use "scan" tier

---

## 1. Research Pool Database Schema

### Table: `research_items`

```sql
CREATE TABLE research_items (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source identification
    source VARCHAR(20) NOT NULL CHECK (source IN ('reddit', 'youtube', 'instagram', 'news', 'pubmed')),
    source_id VARCHAR(255),  -- Original ID from source (e.g., Reddit post ID)
    url TEXT NOT NULL,

    -- Content
    title VARCHAR(500) NOT NULL,
    content TEXT,  -- Full text, transcript excerpt, or abstract
    summary TEXT,  -- LLM-generated summary (for YouTube/PubMed)

    -- Metadata (JSONB for source-specific data)
    metadata JSONB DEFAULT '{}',
    -- Reddit: {subreddit, author, upvotes, comment_count, permalink}
    -- YouTube: {channel, views, duration, publish_date, transcript_available}
    -- Instagram: {account, likes, comments, hashtags}
    -- News: {publication, author, category}
    -- PubMed: {authors, journal, doi, study_type, sample_size}

    -- Tags and classification
    tags TEXT[] DEFAULT '{}',  -- Topic tags: lions_mane, cognition, etc.
    topics TEXT[] DEFAULT '{}',  -- Broader topics: wellness, research, trend

    -- Scoring
    score DECIMAL(3,1) DEFAULT 0.0 CHECK (score >= 0 AND score <= 10),
    score_breakdown JSONB DEFAULT '{}',  -- {relevance: 2.0, recency: 1.5, ...}

    -- Compliance
    compliance_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (compliance_status IN ('pending', 'compliant', 'warning', 'rejected')),
    compliance_notes TEXT,
    compliance_checked_at TIMESTAMPTZ,

    -- Timestamps
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- When we found it
    source_published_at TIMESTAMPTZ,  -- When original was published
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Tracking
    scan_batch_id UUID,  -- Which scan run discovered this
    processed BOOLEAN DEFAULT FALSE,  -- Used by content generators

    -- Indexes for common queries
    CONSTRAINT unique_source_item UNIQUE (source, source_id)
);

-- Indexes for performance (< 500ms queries on 10k items)
CREATE INDEX idx_research_items_source ON research_items(source);
CREATE INDEX idx_research_items_score ON research_items(score DESC);
CREATE INDEX idx_research_items_compliance ON research_items(compliance_status);
CREATE INDEX idx_research_items_discovered ON research_items(discovered_at DESC);
CREATE INDEX idx_research_items_tags ON research_items USING GIN(tags);
CREATE INDEX idx_research_items_topics ON research_items USING GIN(topics);
CREATE INDEX idx_research_items_processed ON research_items(processed) WHERE processed = FALSE;
```

### Table: `scan_batches`

```sql
CREATE TABLE scan_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'incomplete', 'failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    items_found INTEGER DEFAULT 0,
    items_stored INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'  -- Config used, subreddits scanned, etc.
);
```

### SQLAlchemy Models

```python
# teams/dawo/models/research.py
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import String, Text, DECIMAL, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class ResearchItem(Base):
    __tablename__ = "research_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    topics: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    score: Mapped[float] = mapped_column(DECIMAL(3, 1), default=0.0)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)

    compliance_status: Mapped[str] = mapped_column(String(20), default="pending")
    compliance_notes: Mapped[Optional[str]] = mapped_column(Text)
    compliance_checked_at: Mapped[Optional[datetime]]

    discovered_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    source_published_at: Mapped[Optional[datetime]]
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    scan_batch_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
```

---

## 2. External API Requirements

### 2.1 Reddit API (PRAW)

**Used by:** Story 2.3 - Reddit Research Scanner

```python
# Config: config/dawo_reddit_config.json
{
    "client_id": "${REDDIT_CLIENT_ID}",
    "client_secret": "${REDDIT_CLIENT_SECRET}",
    "user_agent": "DAWO.ECO Research Scanner v1.0",
    "subreddits": [
        "Nootropics",
        "Supplements",
        "MushroomSupplements",
        "Biohackers"
    ],
    "keywords": [
        "lion's mane", "lions mane",
        "chaga", "reishi", "cordyceps",
        "shiitake", "maitake",
        "functional mushrooms", "adaptogens"
    ],
    "min_upvotes": 10,
    "lookback_hours": 24,
    "schedule": "0 2 * * *"  # Daily 2 AM
}
```

**API Rate Limits:**
- 60 requests/minute (authenticated)
- Uses OAuth2 authentication
- Retry middleware handles 429 responses

**Required Credentials:**
- [ ] Create Reddit app at https://www.reddit.com/prefs/apps
- [ ] Get CLIENT_ID and CLIENT_SECRET
- [ ] Store in environment variables

### 2.2 YouTube Data API v3

**Used by:** Story 2.4 - YouTube Research Scanner

```python
# Config: config/dawo_youtube_config.json
{
    "api_key": "${YOUTUBE_API_KEY}",
    "search_queries": [
        "mushroom supplements",
        "lion's mane benefits",
        "adaptogen reviews",
        "functional mushrooms"
    ],
    "min_views": 1000,
    "lookback_days": 7,
    "max_results_per_query": 25,
    "schedule": "0 3 * * 0"  # Weekly Sunday 3 AM
}
```

**API Rate Limits:**
- 10,000 units/day quota
- Search: 100 units per request
- Video details: 1 unit per request
- Captions: 50 units per request

**Transcript Extraction:**
- Use `youtube-transcript-api` library (no quota cost)
- Falls back gracefully if no transcript available

**Required Credentials:**
- [ ] Enable YouTube Data API v3 in Google Cloud Console
- [ ] Create API key
- [ ] Store in environment variable

### 2.3 Instagram Graph API

**Used by:** Story 2.5 - Instagram Trend Scanner

```python
# Config: config/dawo_instagram_config.json
{
    "access_token": "${INSTAGRAM_ACCESS_TOKEN}",
    "business_account_id": "${INSTAGRAM_BUSINESS_ID}",
    "hashtags_to_monitor": [
        "lionsmane",
        "mushroomsupplements",
        "adaptogens",
        "biohacking",
        "functionalfoods"
    ],
    "competitor_accounts": [
        // Configured via UI
    ],
    "lookback_hours": 24,
    "schedule": "30 2 * * *"  # Daily 2:30 AM
}
```

**API Limitations:**
- Hashtag search requires Business/Creator account
- 30 hashtag queries per 7 days (rolling)
- Cannot access private accounts
- NO image/media download (privacy compliance)

**Required Credentials:**
- [ ] Instagram Business Account connected to Facebook Page
- [ ] Facebook Developer App with instagram_basic, instagram_content_publish
- [ ] Long-lived access token (60-day refresh)

### 2.4 PubMed Entrez API (E-utilities)

**Used by:** Story 2.7 - PubMed Scientific Research Scanner

```python
# Config: config/dawo_pubmed_config.json
{
    "email": "${PUBMED_EMAIL}",  # Required for identification
    "api_key": "${PUBMED_API_KEY}",  # Optional, increases rate limit
    "search_queries": [
        "lion's mane cognition",
        "chaga antioxidant",
        "reishi immune",
        "cordyceps performance",
        "Hericium erinaceus",
        "Inonotus obliquus"
    ],
    "filters": {
        "publication_types": ["Randomized Controlled Trial", "Meta-Analysis", "Review"],
        "lookback_days": 90
    },
    "schedule": "0 4 * * 0"  # Weekly Sunday 4 AM
}
```

**API Rate Limits:**
- Without API key: 3 requests/second
- With API key: 10 requests/second
- No daily quota limit

**Required Credentials:**
- [ ] Register email with NCBI (no approval needed)
- [ ] Optional: Request API key at https://www.ncbi.nlm.nih.gov/account/settings/

### 2.5 RSS/News Feeds

**Used by:** Story 2.6 - Industry News Scanner

```python
# Config: config/dawo_news_config.json
{
    "feeds": [
        {
            "name": "NutraIngredients",
            "url": "https://www.nutraingredients.com/rss/",
            "category": "industry"
        },
        {
            "name": "Supplement Industry News",
            "url": "https://...",
            "category": "industry"
        },
        {
            "name": "EU Food Safety Authority",
            "url": "https://www.efsa.europa.eu/en/rss",
            "category": "regulatory"
        }
    ],
    "keywords": [
        "functional mushrooms",
        "adaptogens",
        "EU health claims",
        "novel food",
        "supplement regulation"
    ],
    "lookback_hours": 24,
    "schedule": "0 6 * * *"  # Daily 6 AM
}
```

**No API credentials needed** - RSS feeds are public.

Library: `feedparser` for RSS parsing.

---

## 3. Harvester Framework Pattern

### Architecture

All scanners follow the Harvester Framework pattern:

```
[Scanner] → [Harvester] → [Transformer] → [Validator] → [Publisher]
    ↓           ↓             ↓              ↓             ↓
  Discover   Fetch Full    Standardize    Compliance    Research
  Sources    Content       Format         Check         Pool
```

### Base Classes

```python
# teams/dawo/scanners/base/__init__.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional
from datetime import datetime

@dataclass
class RawResearchItem:
    """Raw item from source before transformation."""
    source: str
    source_id: str
    url: str
    title: str
    raw_content: dict  # Source-specific raw data
    discovered_at: datetime

@dataclass
class TransformedResearchItem:
    """Standardized item ready for validation."""
    source: str
    source_id: str
    url: str
    title: str
    content: str
    summary: Optional[str]
    metadata: dict
    tags: list[str]
    source_published_at: Optional[datetime]

@dataclass
class ValidatedResearchItem:
    """Item with compliance status ready for storage."""
    # All TransformedResearchItem fields plus:
    compliance_status: str  # compliant | warning | rejected
    compliance_notes: Optional[str]
    score: float
    score_breakdown: dict


class BaseScanner(ABC):
    """Discovers sources to harvest."""

    @abstractmethod
    async def scan(self) -> AsyncIterator[RawResearchItem]:
        """Yield raw items from source."""
        pass


class BaseHarvester(ABC):
    """Fetches full content for raw items."""

    @abstractmethod
    async def harvest(self, item: RawResearchItem) -> RawResearchItem:
        """Enrich raw item with full content."""
        pass


class BaseTransformer(ABC):
    """Transforms raw items to standard format."""

    @abstractmethod
    async def transform(self, item: RawResearchItem) -> TransformedResearchItem:
        """Convert to standardized format."""
        pass


class BaseValidator(ABC):
    """Validates compliance and calculates score."""

    @abstractmethod
    async def validate(self, item: TransformedResearchItem) -> ValidatedResearchItem:
        """Check compliance and score item."""
        pass


class BasePublisher(ABC):
    """Stores validated items in Research Pool."""

    @abstractmethod
    async def publish(self, item: ValidatedResearchItem) -> str:
        """Store in database, return item ID."""
        pass
```

### Pipeline Orchestration

```python
# teams/dawo/scanners/pipeline.py

class ResearchPipeline:
    """Orchestrates the harvester framework pipeline."""

    def __init__(
        self,
        scanner: BaseScanner,
        harvester: BaseHarvester,
        transformer: BaseTransformer,
        validator: BaseValidator,
        publisher: BasePublisher,
        batch_id: UUID
    ):
        self.scanner = scanner
        self.harvester = harvester
        self.transformer = transformer
        self.validator = validator
        self.publisher = publisher
        self.batch_id = batch_id

    async def run(self) -> PipelineResult:
        """Execute full pipeline."""
        results = PipelineResult(batch_id=self.batch_id)

        async for raw_item in self.scanner.scan():
            try:
                # Harvest full content
                enriched = await self.harvester.harvest(raw_item)

                # Transform to standard format
                transformed = await self.transformer.transform(enriched)

                # Validate compliance and score
                validated = await self.validator.validate(transformed)

                # Publish to Research Pool
                item_id = await self.publisher.publish(validated)

                results.items_stored += 1

            except Exception as e:
                results.errors.append(f"{raw_item.source_id}: {str(e)}")
                continue

        return results
```

---

## 4. Config Files to Create

| File | Purpose | Story |
|------|---------|-------|
| `config/dawo_reddit_config.json` | Reddit API settings | 2.3 |
| `config/dawo_youtube_config.json` | YouTube API settings | 2.4 |
| `config/dawo_instagram_config.json` | Instagram API settings | 2.5 |
| `config/dawo_news_config.json` | RSS feed settings | 2.6 |
| `config/dawo_pubmed_config.json` | PubMed API settings | 2.7 |
| `config/dawo_scoring_config.json` | Scoring weights | 2.2 |

---

## 5. Environment Variables Needed

```bash
# Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret

# YouTube
YOUTUBE_API_KEY=your_api_key

# Instagram (already needed for Epic 4)
INSTAGRAM_ACCESS_TOKEN=your_token
INSTAGRAM_BUSINESS_ID=your_id

# PubMed (optional but recommended)
PUBMED_EMAIL=your_email@example.com
PUBMED_API_KEY=your_api_key
```

---

## 6. Python Dependencies

Add to `requirements.txt`:

```
# Research scanners (Epic 2)
praw>=7.7.0           # Reddit API
google-api-python-client>=2.100.0  # YouTube API
youtube-transcript-api>=0.6.0      # YouTube transcripts
feedparser>=6.0.0     # RSS parsing
biopython>=1.81       # PubMed Entrez
```

---

## 7. Story Execution Order

Recommended order for Epic 2 implementation:

1. **Story 2.1** - Research Pool Database & Storage (foundation)
2. **Story 2.2** - Research Item Scoring Engine (needed by all scanners)
3. **Story 2.8** - Research Compliance Validation (integrates Epic 1 validators)
4. **Story 2.3** - Reddit Research Scanner (simplest API)
5. **Story 2.7** - PubMed Scientific Research Scanner (high-value, simple API)
6. **Story 2.6** - Industry News Scanner (RSS, no auth)
7. **Story 2.4** - YouTube Research Scanner (moderate complexity)
8. **Story 2.5** - Instagram Trend Scanner (most complex API limits)

---

## Checklist Before Starting Epic 2

### Credentials
- [ ] Reddit app created, CLIENT_ID and CLIENT_SECRET obtained
- [ ] YouTube Data API enabled, API key created
- [ ] Instagram Business Account connected (may already have from Epic 4 prep)
- [ ] PubMed email registered (optional API key)

### Infrastructure
- [ ] PostgreSQL database accessible
- [ ] Redis running for job queue
- [ ] Alembic migrations configured

### Dependencies
- [ ] Python packages installed: praw, google-api-python-client, youtube-transcript-api, feedparser, biopython

### Codebase
- [x] EU Compliance Checker ready (Story 1.2)
- [x] Retry Middleware ready (Story 1.5)
- [x] LLM Tier Config ready (Story 1.4)
- [x] Code Review Checklist updated (Retro action item)
- [x] Module template created (Retro action item)

---

*Generated during Epic 2 Preparation - 2026-02-06*
