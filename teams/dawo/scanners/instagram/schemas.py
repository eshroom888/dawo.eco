"""Pydantic schemas for Instagram Trend Scanner.

Defines data structures for each stage of the Harvester Framework pipeline:
    Scanner -> Harvester -> ThemeExtractor -> ClaimDetector -> Transformer -> Validator -> Publisher

UNIQUE to Instagram Scanner:
    - Two LLM stages: ThemeExtractor AND HealthClaimDetector (both use tier="generate")
    - CleanMarket integration for flagging competitor health claims (Epic 6)
    - NO image/video storage - text and metadata only (privacy/copyright compliance)

Schemas:
    - RawInstagramPost: Raw data from Instagram Graph API
    - HarvestedPost: Enriched post with metadata (NO images)
    - ThemeResult: Result from theme extraction
    - DetectedClaim: Individual health claim detected
    - ClaimDetectionResult: Full result from claim detection
    - ClaimCategory: Health claim categories
    - TransformedResearch: Post-transformation data for Research Pool
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
        RATE_LIMITED: Instagram API rate limit exceeded (wait until reset)
    """

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"


class ClaimCategory(str, Enum):
    """Health claim categories based on EU Health Claims Regulation.

    Values:
        TREATMENT: Claims product treats/cures conditions (HIGH severity)
        PREVENTION: Claims product prevents conditions (HIGH severity)
        ENHANCEMENT: Claims product improves body functions (MEDIUM severity)
        GENERAL_WELLNESS: Vague wellness language (LOW severity)
    """

    TREATMENT = "treatment"
    PREVENTION = "prevention"
    ENHANCEMENT = "enhancement"
    GENERAL_WELLNESS = "wellness"


class RawInstagramPost(BaseModel):
    """Raw Instagram post data from Graph API search response.

    Represents minimal data extracted from Instagram hashtag search
    or competitor account media before full detail harvesting.

    Attributes:
        media_id: Instagram media ID
        permalink: Full URL to the post
        timestamp: Post creation timestamp
        caption: Post caption text (may be truncated)
        media_type: Type of media (IMAGE, VIDEO, CAROUSEL_ALBUM)
        hashtag_source: Which hashtag search found this post (if any)
        is_competitor: Whether from a monitored competitor account
    """

    media_id: str = Field(..., description="Instagram media ID")
    permalink: str = Field(..., description="Full URL to post")
    timestamp: datetime = Field(..., description="Post creation timestamp")
    caption: str = Field(default="", description="Post caption text")
    media_type: str = Field(default="IMAGE", description="Type of media")
    hashtag_source: Optional[str] = Field(default=None, description="Source hashtag")
    is_competitor: bool = Field(default=False, description="From competitor account")

    model_config = {"frozen": True}


class HarvestedPost(BaseModel):
    """Instagram post data - TEXT AND METADATA ONLY.

    CRITICAL: Do NOT add image_url, media_data, or any image storage.
    This is intentional for privacy/copyright compliance with Meta's ToS.

    Contains complete post data after harvesting from Instagram Graph API,
    including full caption, hashtags, and engagement metrics.

    Attributes:
        media_id: Instagram media ID
        permalink: Full URL to post
        caption: Full caption text
        hashtags: List of hashtags used
        likes: Total like count
        comments: Total comment count
        media_type: Type of media (IMAGE, VIDEO, CAROUSEL_ALBUM) - for stats only
        account_name: Instagram username
        account_type: Account type (business, creator)
        timestamp: Post creation timestamp
        is_competitor: Whether from a monitored competitor account
        hashtag_source: Which hashtag search found this post (if any)
    """

    media_id: str = Field(..., description="Instagram media ID")
    permalink: str = Field(..., description="Full URL to post")
    caption: str = Field(default="", description="Full caption text")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags used")
    likes: int = Field(default=0, ge=0, description="Total likes")
    comments: int = Field(default=0, ge=0, description="Total comments")
    media_type: str = Field(default="IMAGE", description="Media type - stats only")
    account_name: str = Field(default="", description="Instagram username")
    account_type: str = Field(default="business", description="Account type")
    timestamp: datetime = Field(..., description="Post creation timestamp")
    is_competitor: bool = Field(default=False, description="From competitor account")
    hashtag_source: Optional[str] = Field(default=None, description="Source hashtag")
    # NOTE: NO image_url field - intentionally excluded for privacy compliance

    model_config = {"frozen": True}


@dataclass
class ThemeResult:
    """Result from theme extraction.

    Attributes:
        content_type: educational, promotional, lifestyle, testimonial
        messaging_patterns: Patterns identified (question_hook, before_after, etc.)
        detected_products: Product/brand mentions
        influencer_indicators: Whether paid partnership indicators found
        key_topics: 3-7 relevant topic tags
        confidence_score: Model confidence in extraction (0-1)
    """

    content_type: str
    messaging_patterns: list[str] = field(default_factory=list)
    detected_products: list[str] = field(default_factory=list)
    influencer_indicators: bool = False
    key_topics: list[str] = field(default_factory=list)
    confidence_score: float = 0.0

    def __post_init__(self) -> None:
        """Validate theme result."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"confidence_score must be 0-1, got {self.confidence_score}")


@dataclass
class DetectedClaim:
    """A detected health claim from content.

    Attributes:
        claim_text: The exact phrase containing the claim
        category: Claim category (treatment, prevention, enhancement, wellness)
        confidence: Detection confidence (0-1)
        severity: Risk level based on EU regulation (high, medium, low)
    """

    claim_text: str
    category: ClaimCategory
    confidence: float = 0.0
    severity: str = "low"

    def __post_init__(self) -> None:
        """Validate detected claim."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")
        if self.severity not in ("high", "medium", "low"):
            raise ValueError(f"severity must be high/medium/low, got {self.severity}")


@dataclass
class ClaimDetectionResult:
    """Result from health claim detection.

    Attributes:
        claims_detected: List of detected health claims
        requires_cleanmarket_review: True if any claims detected
        overall_risk_level: Aggregate risk (none, low, medium, high)
        summary: Brief description for CleanMarket queue
    """

    claims_detected: list[DetectedClaim] = field(default_factory=list)
    requires_cleanmarket_review: bool = False
    overall_risk_level: str = "none"
    summary: str = ""

    def __post_init__(self) -> None:
        """Validate claim detection result."""
        valid_risk_levels = ("none", "low", "medium", "high")
        if self.overall_risk_level not in valid_risk_levels:
            raise ValueError(
                f"overall_risk_level must be one of {valid_risk_levels}, "
                f"got {self.overall_risk_level}"
            )


class ValidatedResearch(BaseModel):
    """Research item after EU compliance validation.

    Extends transformed research with compliance status set by validator.

    Attributes:
        source: Research source ("instagram")
        title: Post title (truncated caption or account-based)
        content: Caption + theme analysis summary
        url: Instagram post permalink
        tags: Auto-generated from hashtags + detected themes
        source_metadata: Instagram-specific metadata including claims
        created_at: Post timestamp
        compliance_status: EU compliance check result
        cleanmarket_flag: Whether flagged for CleanMarket review
        score: Research relevance score (0-10)
    """

    source: str = Field(default="instagram", description="Source identifier")
    title: str = Field(..., max_length=500, description="Post title")
    content: str = Field(..., min_length=1, description="Caption + theme analysis")
    url: str = Field(..., max_length=2048, description="Instagram permalink")
    tags: list[str] = Field(default_factory=list, description="Topic tags")
    source_metadata: dict = Field(default_factory=dict, description="Instagram metadata")
    created_at: datetime = Field(..., description="Post timestamp")
    compliance_status: str = Field(
        default="COMPLIANT",
        description="EU compliance status: COMPLIANT, WARNING, REJECTED",
    )
    cleanmarket_flag: bool = Field(
        default=False,
        description="Whether flagged for CleanMarket review (Epic 6)",
    )
    score: float = Field(default=0.0, ge=0.0, le=10.0, description="Research score")

    model_config = {"from_attributes": True}


@dataclass
class ScanStatistics:
    """Statistics from scanner stage execution.

    Attributes:
        hashtags_searched: Number of hashtags processed
        accounts_monitored: Number of competitor accounts checked
        total_posts_found: Raw posts from API
        posts_after_filter: Posts meeting date criteria
        duplicates_removed: Posts deduplicated by media ID
        api_calls_made: Total Instagram API calls
    """

    hashtags_searched: int = 0
    accounts_monitored: int = 0
    total_posts_found: int = 0
    posts_after_filter: int = 0
    duplicates_removed: int = 0
    api_calls_made: int = 0


@dataclass
class ScanResult:
    """Result of scanner stage execution.

    Attributes:
        posts: List of raw Instagram posts passing filters
        statistics: Scan execution statistics
        errors: Any non-fatal errors encountered
    """

    posts: list[RawInstagramPost] = field(default_factory=list)
    statistics: ScanStatistics = field(default_factory=ScanStatistics)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineStatistics:
    """Full pipeline execution statistics.

    Tracks item counts through each pipeline stage.
    UNIQUE to Instagram: includes themes_extracted, claims_detected, cleanmarket_flagged

    Attributes:
        total_found: Raw posts from scanner
        harvested: Posts with full details retrieved
        themes_extracted: Posts with theme analysis
        claims_detected: Posts with health claims found
        cleanmarket_flagged: Posts flagged for CleanMarket review
        transformed: Posts standardized for Research Pool
        validated: Posts passing compliance check
        scored: Posts with relevance scores
        published: Items saved to Research Pool
        failed: Items that failed at any stage
        api_calls_made: Total Instagram API calls
    """

    total_found: int = 0
    harvested: int = 0
    themes_extracted: int = 0
    claims_detected: int = 0
    cleanmarket_flagged: int = 0
    transformed: int = 0
    validated: int = 0
    scored: int = 0
    published: int = 0
    failed: int = 0
    api_calls_made: int = 0


@dataclass
class PipelineResult:
    """Result of full pipeline execution.

    Attributes:
        status: Pipeline completion status
        statistics: Item counts through each stage
        error: Error message if failed/incomplete
        retry_scheduled: True if queued for next cycle
        retry_after: Timestamp when retry is allowed (for rate limit)
        published_ids: UUIDs of successfully published items
    """

    status: PipelineStatus
    statistics: PipelineStatistics = field(default_factory=PipelineStatistics)
    error: Optional[str] = None
    retry_scheduled: bool = False
    retry_after: Optional[datetime] = None
    published_ids: list[UUID] = field(default_factory=list)
