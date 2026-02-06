"""Pydantic schemas for YouTube Research Scanner.

Defines data structures for each stage of the Harvester Framework pipeline:
    Scanner -> Harvester -> InsightExtractor -> Transformer -> Validator -> Publisher

Schemas:
    - RawYouTubeVideo: Raw data from YouTube search API
    - HarvestedVideo: Enriched video with statistics and transcript
    - TranscriptResult: Result of transcript extraction attempt
    - QuotableInsight: Individual quotable insight from video
    - InsightResult: Full result from key insight extraction
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
        QUOTA_EXCEEDED: YouTube API quota exhausted (wait until reset)
    """

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


class RawYouTubeVideo(BaseModel):
    """Raw YouTube video data from API search response.

    Represents minimal data extracted from YouTube search results
    before full detail harvesting.

    Attributes:
        video_id: YouTube video ID (e.g., "abc123xyz")
        title: Video title
        channel_id: YouTube channel ID
        channel_title: Channel display name
        published_at: Video publish timestamp
        description: Video description snippet
        thumbnail_url: URL to video thumbnail
    """

    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    channel_id: str = Field(..., description="Channel ID")
    channel_title: str = Field(..., description="Channel display name")
    published_at: datetime = Field(..., description="Publish timestamp")
    description: str = Field(default="", description="Video description")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL")

    model_config = {"frozen": True}


class HarvestedVideo(BaseModel):
    """Enriched YouTube video with full details.

    Contains complete video data after harvesting from YouTube API,
    including statistics, duration, and transcript availability.

    Attributes:
        video_id: YouTube video ID
        title: Video title
        channel_id: YouTube channel ID
        channel_title: Channel display name
        published_at: Video publish timestamp
        description: Full video description
        view_count: Total view count
        like_count: Total like count
        comment_count: Total comment count
        duration_seconds: Video duration in seconds
        thumbnail_url: URL to video thumbnail
        transcript: Full transcript text (if available)
        transcript_available: Whether transcript was extracted
        transcript_language: Language of transcript
        is_auto_generated: Whether transcript is auto-generated
    """

    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    channel_id: str = Field(..., description="Channel ID")
    channel_title: str = Field(..., description="Channel display name")
    published_at: datetime = Field(..., description="Publish timestamp")
    description: str = Field(default="", description="Video description")
    view_count: int = Field(default=0, ge=0, description="Total views")
    like_count: int = Field(default=0, ge=0, description="Total likes")
    comment_count: int = Field(default=0, ge=0, description="Total comments")
    duration_seconds: int = Field(default=0, ge=0, description="Duration in seconds")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL")
    transcript: str = Field(default="", description="Full transcript text")
    transcript_available: bool = Field(default=False, description="Transcript extracted")
    transcript_language: Optional[str] = Field(default=None, description="Transcript language")
    is_auto_generated: bool = Field(default=False, description="Auto-generated transcript")

    model_config = {"frozen": True}


@dataclass
class TranscriptResult:
    """Result of transcript extraction attempt.

    Attributes:
        text: Full transcript text (empty if unavailable)
        language: Detected language code
        is_auto_generated: Whether transcript is auto-generated
        available: Whether transcript was successfully extracted
        reason: Reason if unavailable (disabled, not_found)
        duration_seconds: Video duration from transcript segments
    """

    text: str = ""
    language: Optional[str] = None
    is_auto_generated: bool = False
    available: bool = True
    reason: Optional[str] = None
    duration_seconds: int = 0


@dataclass
class QuotableInsight:
    """A quotable insight extracted from video transcript.

    Represents a key statement from the video that could be
    valuable for content creation.

    Attributes:
        text: The exact or near-exact quotable statement
        context: Brief context explaining relevance
        topic: Primary topic tag (e.g., "lion's mane cognition")
        is_claim: True if it makes a health claim
    """

    text: str
    context: str
    topic: str
    is_claim: bool = False


@dataclass
class InsightResult:
    """Result from key insight extraction.

    Contains the full output from LLM-powered insight extraction,
    including summary, quotable insights, and topic tags.

    Attributes:
        main_summary: 100-200 word summary of video content
        quotable_insights: Max 3 quotable insights
        key_topics: 3-7 relevant topic tags
        confidence_score: Model confidence in extraction (0-1)
    """

    main_summary: str
    quotable_insights: list[QuotableInsight] = field(default_factory=list)
    key_topics: list[str] = field(default_factory=list)
    confidence_score: float = 0.0

    def __post_init__(self) -> None:
        """Validate insight result."""
        if len(self.quotable_insights) > 3:
            # Truncate to max 3 insights
            self.quotable_insights = self.quotable_insights[:3]

        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"confidence_score must be 0-1, got {self.confidence_score}")


class ValidatedResearch(BaseModel):
    """Research item after EU compliance validation.

    Extends transformed research with compliance status set by validator.

    Attributes:
        source: Research source ("youtube")
        title: Video title
        content: Summary + quotable insights text
        url: Full YouTube video URL
        tags: Auto-generated topic tags
        source_metadata: YouTube-specific metadata
        created_at: Video publish datetime
        compliance_status: EU compliance check result
        score: Research relevance score (0-10)
    """

    source: str = Field(default="youtube", description="Source identifier")
    title: str = Field(..., max_length=500, description="Video title")
    content: str = Field(..., min_length=1, description="Summary + insights")
    url: str = Field(..., max_length=2048, description="Full YouTube URL")
    tags: list[str] = Field(default_factory=list, description="Topic tags")
    source_metadata: dict = Field(default_factory=dict, description="YouTube metadata")
    created_at: datetime = Field(..., description="Publish timestamp")
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
        queries_searched: Number of search queries executed
        total_videos_found: Raw videos from API
        videos_after_filter: Videos meeting view/date criteria
        duplicates_removed: Videos deduplicated by ID
        quota_used: YouTube API quota units consumed
    """

    queries_searched: int = 0
    total_videos_found: int = 0
    videos_after_filter: int = 0
    duplicates_removed: int = 0
    quota_used: int = 0


@dataclass
class ScanResult:
    """Result of scanner stage execution.

    Attributes:
        videos: List of raw YouTube videos passing filters
        statistics: Scan execution statistics
        errors: Any non-fatal errors encountered
    """

    videos: list[RawYouTubeVideo] = field(default_factory=list)
    statistics: ScanStatistics = field(default_factory=ScanStatistics)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineStatistics:
    """Full pipeline execution statistics.

    Tracks item counts through each pipeline stage.

    Attributes:
        total_found: Raw videos from scanner
        harvested: Videos with full details retrieved
        transcripts_extracted: Videos with transcript text
        insights_generated: Videos with LLM insights
        transformed: Videos standardized for Research Pool
        validated: Videos passing compliance check
        scored: Videos with relevance scores
        published: Items saved to Research Pool
        failed: Items that failed at any stage
        quota_used: YouTube API quota units consumed
    """

    total_found: int = 0
    harvested: int = 0
    transcripts_extracted: int = 0
    insights_generated: int = 0
    transformed: int = 0
    validated: int = 0
    scored: int = 0
    published: int = 0
    failed: int = 0
    quota_used: int = 0


@dataclass
class PipelineResult:
    """Result of full pipeline execution.

    Attributes:
        status: Pipeline completion status
        statistics: Item counts through each stage
        error: Error message if failed/incomplete
        retry_scheduled: True if queued for next cycle
        retry_after: Timestamp when retry is allowed (for quota exceeded)
        published_ids: UUIDs of successfully published items
    """

    status: PipelineStatus
    statistics: PipelineStatistics = field(default_factory=PipelineStatistics)
    error: Optional[str] = None
    retry_scheduled: bool = False
    retry_after: Optional[datetime] = None
    published_ids: list[UUID] = field(default_factory=list)
