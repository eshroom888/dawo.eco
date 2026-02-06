"""Pydantic schemas for Reddit Research Scanner.

Defines data structures for each stage of the Harvester Framework pipeline:
    Scanner → Harvester → Transformer → Validator → Publisher

Schemas:
    - RawRedditPost: Raw data from Reddit API search
    - HarvestedPost: Enriched post with full details
    - TransformedResearch: Standardized for Research Pool (imported from research module)
    - ValidatedResearch: Post-compliance check data
    - ScanResult: Scanner stage output with statistics
    - PipelineResult: Full pipeline execution result
    - PipelineStatus: Pipeline completion status enum
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineStatus(str, Enum):
    """Pipeline execution status.

    Values:
        COMPLETE: All stages executed successfully
        INCOMPLETE: Pipeline stopped due to API failure (retry scheduled)
        PARTIAL: Some items failed but pipeline continued
        FAILED: Critical failure - pipeline aborted
    """

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RawRedditPost(BaseModel):
    """Raw Reddit post data from API search response.

    Represents minimal data extracted from Reddit search results
    before full detail harvesting.

    Attributes:
        id: Reddit post ID (e.g., "abc123")
        subreddit: Subreddit name without r/ prefix
        title: Post title
        score: Upvotes minus downvotes
        created_utc: Unix timestamp of post creation
        permalink: Relative URL path to post
        is_self: True if text post, False if link post
    """

    id: str = Field(..., description="Reddit post ID")
    subreddit: str = Field(..., description="Subreddit name without r/")
    title: str = Field(..., description="Post title")
    score: int = Field(..., description="Net upvotes (upvotes - downvotes)")
    created_utc: float = Field(..., description="Unix timestamp")
    permalink: str = Field(..., description="Relative URL path")
    is_self: bool = Field(default=True, description="True if text post")

    model_config = {"frozen": True}


class HarvestedPost(BaseModel):
    """Enriched Reddit post with full details.

    Contains complete post data after harvesting from Reddit API,
    including full body text and engagement metrics.

    Attributes:
        id: Reddit post ID
        subreddit: Subreddit name
        title: Post title
        selftext: Full post body text (empty for link posts)
        author: Reddit username
        score: Net upvotes
        upvote_ratio: Ratio of upvotes to total votes (0-1)
        num_comments: Comment count
        permalink: Relative URL path
        url: Full URL (for link posts, the external URL)
        created_utc: Unix timestamp
        is_self: True if text post
    """

    id: str = Field(..., description="Reddit post ID")
    subreddit: str = Field(..., description="Subreddit name")
    title: str = Field(..., description="Post title")
    selftext: str = Field(default="", description="Post body text")
    author: str = Field(..., description="Author username")
    score: int = Field(..., description="Net upvotes")
    upvote_ratio: float = Field(default=1.0, description="Upvote ratio")
    num_comments: int = Field(default=0, description="Comment count")
    permalink: str = Field(..., description="Relative URL path")
    url: str = Field(..., description="Full URL or external link")
    created_utc: float = Field(..., description="Unix timestamp")
    is_self: bool = Field(default=True, description="Text post flag")

    model_config = {"frozen": True}


class ValidatedResearch(BaseModel):
    """Research item after EU compliance validation.

    Extends TransformedResearch with compliance status set by validator.

    Attributes:
        source: Research source ("reddit")
        title: Post title
        content: Post body text
        url: Full permalink URL
        tags: Auto-generated topic tags
        source_metadata: Reddit-specific metadata
        created_at: Post creation datetime
        compliance_status: EU compliance check result
    """

    source: str = Field(default="reddit", description="Source identifier")
    title: str = Field(..., max_length=500, description="Post title")
    content: str = Field(..., min_length=1, description="Post body")
    url: str = Field(..., max_length=2048, description="Full URL")
    tags: list[str] = Field(default_factory=list, description="Topic tags")
    source_metadata: dict = Field(default_factory=dict, description="Reddit metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    compliance_status: str = Field(
        default="COMPLIANT",
        description="EU compliance status: COMPLIANT, WARNING, REJECTED",
    )
    score: float = Field(default=0.0, ge=0.0, le=10.0, description="Research score")

    model_config = {"from_attributes": True}


@dataclass
class ScanStatistics:
    """Statistics from scanner stage execution.

    Attributes:
        subreddits_scanned: Number of subreddits processed
        keywords_searched: Number of keywords used
        total_posts_found: Raw posts from API
        posts_after_filter: Posts meeting upvote/time criteria
        duplicates_removed: Posts deduplicated by ID
    """

    subreddits_scanned: int = 0
    keywords_searched: int = 0
    total_posts_found: int = 0
    posts_after_filter: int = 0
    duplicates_removed: int = 0


@dataclass
class ScanResult:
    """Result of scanner stage execution.

    Attributes:
        posts: List of raw Reddit posts passing filters
        statistics: Scan execution statistics
        errors: Any non-fatal errors encountered
    """

    posts: list[RawRedditPost] = field(default_factory=list)
    statistics: ScanStatistics = field(default_factory=ScanStatistics)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineStatistics:
    """Full pipeline execution statistics.

    Tracks item counts through each pipeline stage.

    Attributes:
        total_found: Raw posts from scanner
        harvested: Posts with full details retrieved
        transformed: Posts standardized for Research Pool
        validated: Posts passing compliance check
        scored: Posts with relevance scores
        published: Items saved to Research Pool
        failed: Items that failed at any stage
    """

    total_found: int = 0
    harvested: int = 0
    transformed: int = 0
    validated: int = 0
    scored: int = 0
    published: int = 0
    failed: int = 0


@dataclass
class PipelineResult:
    """Result of full pipeline execution.

    Attributes:
        status: Pipeline completion status
        statistics: Item counts through each stage
        error: Error message if failed/incomplete
        retry_scheduled: True if queued for next cycle
        published_ids: UUIDs of successfully published items
    """

    status: PipelineStatus
    statistics: PipelineStatistics = field(default_factory=PipelineStatistics)
    error: Optional[str] = None
    retry_scheduled: bool = False
    published_ids: list[UUID] = field(default_factory=list)
