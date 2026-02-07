"""Pydantic schemas for Industry News Scanner.

Defines data structures for each stage of the Harvester Framework pipeline:
    Scanner -> Harvester -> Categorizer -> PriorityScorer -> Transformer -> Validator -> Publisher

UNIQUE to News Scanner:
    - Fully rule-based: NO LLM stages (unlike Instagram's ThemeExtractor/ClaimDetector)
    - Uses tier="scan" for ALL components (pattern matching, no model calls)
    - Categorization and priority scoring use keyword pattern matching
    - Lower cost per execution, suitable for daily frequency

Schemas:
    - RawNewsArticle: Raw data from RSS/Atom feed
    - HarvestedArticle: Article with cleaned content
    - NewsCategory: News article categories
    - PriorityLevel: Priority level for operator attention
    - CategoryResult: Result from news categorization
    - PriorityScore: Result from priority scoring
    - TransformedResearch: Post-transformation data for Research Pool
    - ValidatedResearch: Post-compliance check data
    - ScanResult: Scanner stage output with statistics
    - PipelineResult: Full pipeline execution result
    - PipelineStatus: Pipeline completion status enum
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineStatus(str, Enum):
    """Pipeline execution status.

    Values:
        COMPLETE: All stages executed successfully
        INCOMPLETE: Pipeline stopped due to feed failure (retry scheduled)
        PARTIAL: Some items failed but pipeline continued
        FAILED: Critical failure - pipeline aborted
    """

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class NewsCategory(str, Enum):
    """News article category.

    Values:
        REGULATORY: EU, FDA, Mattilsynet, compliance news
        PRODUCT_NEWS: Product launches, announcements
        RESEARCH: Studies, clinical trials, findings
        COMPETITOR: Competitor brand mentions
        GENERAL: Other industry news
    """

    REGULATORY = "regulatory"
    PRODUCT_NEWS = "product_news"
    RESEARCH = "research"
    COMPETITOR = "competitor"
    GENERAL = "general"


class PriorityLevel(str, Enum):
    """Priority level for operator attention.

    Values:
        HIGH: Regulatory + health claims/novel food (score 8+)
        MEDIUM: Regulatory other (score 6-7)
        LOW: Non-regulatory (score 2-5)
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RawNewsArticle(BaseModel):
    """Raw news article data from RSS/Atom feed.

    Represents minimal data extracted from feed before full processing.

    Attributes:
        title: Article headline
        summary: Article summary/description (may contain HTML)
        url: Full URL to article
        published: Publication timestamp
        source_name: Name of the news source
        is_tier_1: Whether from a high-reputation source
    """

    title: str = Field(..., description="Article headline")
    summary: str = Field(default="", description="Article summary/description")
    url: str = Field(..., description="Full URL to article")
    published: Optional[datetime] = Field(default=None, description="Publication timestamp")
    source_name: str = Field(..., description="Name of news source")
    is_tier_1: bool = Field(default=False, description="High-reputation source")

    model_config = {"frozen": True}


class HarvestedArticle(BaseModel):
    """News article after harvesting and cleaning.

    Contains article data with HTML cleaned and content normalized.

    Attributes:
        title: Article headline
        summary: Cleaned summary (HTML removed)
        url: Full URL to article
        published: Publication timestamp
        source_name: Name of the news source
        is_tier_1: Whether from a high-reputation source
    """

    title: str = Field(..., description="Article headline")
    summary: str = Field(default="", description="Cleaned article summary")
    url: str = Field(..., description="Full URL to article")
    published: Optional[datetime] = Field(default=None, description="Publication timestamp")
    source_name: str = Field(..., description="Name of news source")
    is_tier_1: bool = Field(default=False, description="High-reputation source")

    model_config = {"frozen": True}


@dataclass
class CategoryResult:
    """Result from news categorization.

    Attributes:
        category: Detected news category
        confidence: Confidence score (0-1)
        is_regulatory: Whether article relates to regulations
        priority_level: Priority level for attention routing
        matched_patterns: Which patterns triggered classification
        requires_operator_attention: Whether flagged for operator
    """

    category: NewsCategory
    confidence: float = 0.5
    is_regulatory: bool = False
    priority_level: PriorityLevel = PriorityLevel.LOW
    matched_patterns: list[str] = field(default_factory=list)
    requires_operator_attention: bool = False

    def __post_init__(self) -> None:
        """Validate category result."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")


@dataclass
class PriorityScore:
    """Result from priority scoring.

    Attributes:
        base_score: Category-based score before boosters
        final_score: Score after boosters applied (0-10)
        boosters_applied: List of boosters that were applied
        requires_attention: Whether flagged for operator attention
    """

    base_score: float
    final_score: float
    boosters_applied: list[str] = field(default_factory=list)
    requires_attention: bool = False

    def __post_init__(self) -> None:
        """Validate priority score."""
        if not 0.0 <= self.final_score <= 10.0:
            raise ValueError(f"final_score must be 0-10, got {self.final_score}")


class ValidatedResearch(BaseModel):
    """Research item after EU compliance validation.

    Extends transformed research with compliance status set by validator.

    Attributes:
        source: Research source ("news")
        title: Article headline
        content: Article summary + category info
        url: Article URL
        tags: Auto-generated from category + detected keywords
        source_metadata: News-specific metadata
        created_at: Article timestamp
        compliance_status: EU compliance check result
        score: Research relevance score (0-10)
    """

    source: str = Field(default="news", description="Source identifier")
    title: str = Field(..., max_length=500, description="Article headline")
    content: str = Field(..., min_length=1, description="Article summary + analysis")
    url: str = Field(..., max_length=2048, description="Article URL")
    tags: list[str] = Field(default_factory=list, description="Topic tags")
    source_metadata: dict[str, Any] = Field(default_factory=dict, description="News metadata")
    created_at: datetime = Field(..., description="Article timestamp")
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
        feeds_processed: Number of feeds fetched
        feeds_failed: Number of feeds that failed
        total_articles_found: Raw articles from all feeds
        articles_after_filter: Articles meeting date/keyword criteria
        duplicates_removed: Articles deduplicated by URL
    """

    feeds_processed: int = 0
    feeds_failed: int = 0
    total_articles_found: int = 0
    articles_after_filter: int = 0
    duplicates_removed: int = 0


@dataclass
class ScanResult:
    """Result of scanner stage execution.

    Attributes:
        articles: List of raw articles passing filters
        statistics: Scan execution statistics
        errors: Any non-fatal errors encountered
    """

    articles: list[RawNewsArticle] = field(default_factory=list)
    statistics: ScanStatistics = field(default_factory=ScanStatistics)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineStatistics:
    """Full pipeline execution statistics.

    Tracks item counts through each pipeline stage.
    UNIQUE to News: includes categorized, regulatory_flagged counts.

    Attributes:
        total_found: Raw articles from scanner
        harvested: Articles cleaned
        categorized: Articles categorized
        regulatory_flagged: Articles flagged as regulatory
        transformed: Articles standardized for Research Pool
        validated: Articles passing compliance check
        scored: Articles with relevance scores
        published: Items saved to Research Pool
        failed: Items that failed at any stage
        feeds_processed: Number of feeds fetched
        feeds_failed: Number of feeds that failed
    """

    total_found: int = 0
    harvested: int = 0
    categorized: int = 0
    regulatory_flagged: int = 0
    transformed: int = 0
    validated: int = 0
    scored: int = 0
    published: int = 0
    failed: int = 0
    feeds_processed: int = 0
    feeds_failed: int = 0


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
