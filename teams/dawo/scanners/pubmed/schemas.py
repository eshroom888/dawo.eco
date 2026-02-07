"""Pydantic schemas for PubMed Scientific Research Scanner.

Defines data structures for each stage of the Harvester Framework pipeline:
    Scanner -> Harvester -> FindingSummarizer -> ClaimValidator -> Transformer -> Validator -> Publisher

UNIQUE to PubMed Scanner:
    - Has TWO LLM stages: FindingSummarizer AND ClaimValidator (both tier="generate")
    - Scientific metadata: DOI, study type, sample size, authors, publication types
    - Claim validation specific to EU Health Claims context
    - Content potential tagging for compliant content usage

Schemas:
    - RawPubMedArticle: Raw data from Entrez efetch
    - HarvestedArticle: Article with parsed metadata and study type
    - FindingSummary: LLM-generated summary of research findings
    - ClaimValidationResult: EU claim potential assessment
    - ValidatedResearch: Post-compliance check data for Research Pool
    - ScanResult: Scanner stage output with statistics
    - PipelineResult: Full pipeline execution result
    - PipelineStatus: Pipeline completion status enum
    - ContentPotential: Content usage categories
    - StudyType: Study type classification
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


class ContentPotential(str, Enum):
    """Content usage categories for research findings.

    Determines how research can be used for marketing content
    under EU Health Claims Regulation (EC 1924/2006).

    Values:
        CITATION_ONLY: Can cite study with DOI link, no claims
        EDUCATIONAL: Can discuss the science generally
        TREND_AWARENESS: Indicates research direction in the field
        NO_CLAIM: Cannot use for marketing claims
    """

    CITATION_ONLY = "citation_only"
    EDUCATIONAL = "educational"
    TREND_AWARENESS = "trend_awareness"
    NO_CLAIM = "no_claim"


class StudyType(str, Enum):
    """Study type classification based on PubMed publication types.

    Used for scoring and filtering research relevance.

    Values:
        RCT: Randomized Controlled Trial (highest evidence)
        META_ANALYSIS: Meta-Analysis (highest evidence)
        SYSTEMATIC_REVIEW: Systematic Review
        REVIEW: General Review article
        OTHER: Other publication types
    """

    RCT = "rct"
    META_ANALYSIS = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    REVIEW = "review"
    OTHER = "other"


class RawPubMedArticle(BaseModel):
    """Raw PubMed article data from Entrez efetch.

    Represents minimal data extracted from Entrez before full processing.

    Attributes:
        pmid: PubMed ID (unique identifier)
        title: Article title
        abstract: Abstract text (may be empty for some articles)
        authors: List of author names
        journal: Journal name
        pub_date: Publication date
        doi: Digital Object Identifier (optional)
        publication_types: List of MeSH publication types
    """

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Article title")
    abstract: str = Field(default="", description="Abstract text")
    authors: list[str] = Field(default_factory=list, description="Author names")
    journal: str = Field(default="", description="Journal name")
    pub_date: Optional[datetime] = Field(default=None, description="Publication date")
    doi: Optional[str] = Field(default=None, description="DOI identifier")
    publication_types: list[str] = Field(
        default_factory=list,
        description="MeSH publication types",
    )

    model_config = {"frozen": True}


class HarvestedArticle(BaseModel):
    """PubMed article after harvesting with parsed metadata.

    Contains article data with study type classified and sample size extracted.

    Attributes:
        pmid: PubMed ID
        title: Article title
        abstract: Abstract text
        authors: List of author names (limited to first 10)
        journal: Journal name
        pub_date: Publication date
        doi: Digital Object Identifier (optional)
        study_type: Classified study type
        sample_size: Extracted sample size (optional)
        pubmed_url: Direct link to PubMed article
    """

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Article title")
    abstract: str = Field(..., description="Abstract text")
    authors: list[str] = Field(default_factory=list, description="Author names")
    journal: str = Field(..., description="Journal name")
    pub_date: datetime = Field(..., description="Publication date")
    doi: Optional[str] = Field(default=None, description="DOI identifier")
    study_type: StudyType = Field(..., description="Classified study type")
    sample_size: Optional[int] = Field(default=None, description="Extracted sample size")
    pubmed_url: str = Field(..., description="Direct PubMed URL")

    model_config = {"frozen": True}


@dataclass
class FindingSummary:
    """LLM-generated summary of research findings.

    Created by FindingSummarizer (tier="generate") to produce
    plain-language summaries suitable for content inspiration.

    Attributes:
        compound_studied: Main substance studied (e.g., "Lion's mane extract")
        effect_measured: Health/wellness effect investigated
        key_findings: Plain-language summary of results
        statistical_significance: P-values, confidence intervals if stated
        study_strength: "strong", "moderate", or "weak"
        content_potential: Tags for content usage
        caveat: Standard disclaimer about research vs. claims
    """

    compound_studied: str
    effect_measured: str
    key_findings: str
    statistical_significance: Optional[str]
    study_strength: str
    content_potential: list[str]
    caveat: str


@dataclass
class ClaimValidationResult:
    """Result from claim validation against EU Health Claims context.

    Created by ClaimValidator (tier="generate") to assess how
    research findings can be used for marketing content.

    Attributes:
        content_potential: List of usage categories
        usage_guidance: Specific guidance on compliant usage
        eu_claim_status: Current EU claim status for this type
        caveat: Standard disclaimer
        can_cite_study: Whether study can be cited
        can_make_claim: Whether marketing claims can be made
    """

    content_potential: list[ContentPotential]
    usage_guidance: str
    eu_claim_status: str
    caveat: str
    can_cite_study: bool
    can_make_claim: bool


class ValidatedResearch(BaseModel):
    """Research item after EU compliance validation.

    Ready for publication to Research Pool via ResearchPublisher.

    Attributes:
        source: Research source ("pubmed")
        source_id: PubMed ID
        title: Article title
        content: Abstract + finding summary + usage guidance
        summary: Plain-language summary of findings
        url: PubMed URL
        tags: Auto-generated from compound, effect, study type
        source_metadata: Scientific metadata (authors, journal, doi, etc.)
        created_at: Publication date
        compliance_status: EU compliance check result
        score: Research relevance score (0-10)
    """

    source: str = Field(default="pubmed", description="Source identifier")
    source_id: str = Field(..., description="PubMed ID")
    title: str = Field(..., max_length=500, description="Article title")
    content: str = Field(..., min_length=1, description="Abstract + summary + guidance")
    summary: str = Field(..., description="Plain-language summary")
    url: str = Field(..., max_length=2048, description="PubMed URL")
    tags: list[str] = Field(default_factory=list, description="Topic tags")
    source_metadata: dict = Field(default_factory=dict, description="Scientific metadata")
    created_at: datetime = Field(..., description="Publication date")
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
        queries_executed: Number of search queries run
        total_pmids_found: Total PMIDs returned across all queries
        pmids_after_dedup: PMIDs after deduplication
        queries_failed: Number of queries that failed
    """

    queries_executed: int = 0
    total_pmids_found: int = 0
    pmids_after_dedup: int = 0
    queries_failed: int = 0


@dataclass
class ScanResult:
    """Result of scanner stage execution.

    Attributes:
        articles: List of raw articles from PubMed
        statistics: Scan execution statistics
        errors: Any non-fatal errors encountered
    """

    articles: list[RawPubMedArticle] = field(default_factory=list)
    statistics: ScanStatistics = field(default_factory=ScanStatistics)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineStatistics:
    """Full pipeline execution statistics.

    Tracks item counts through each pipeline stage.
    UNIQUE to PubMed: includes summarized, claim_validated counts.

    Attributes:
        total_found: Raw PMIDs from scanner
        harvested: Articles fetched and parsed
        summarized: Articles with LLM summaries generated
        claim_validated: Articles with claim potential assessed
        transformed: Articles standardized for Research Pool
        validated: Articles passing compliance check
        scored: Articles with relevance scores
        published: Items saved to Research Pool
        failed: Items that failed at any stage
        queries_executed: Number of search queries run
        queries_failed: Number of queries that failed
    """

    total_found: int = 0
    harvested: int = 0
    summarized: int = 0
    claim_validated: int = 0
    transformed: int = 0
    validated: int = 0
    scored: int = 0
    published: int = 0
    failed: int = 0
    queries_executed: int = 0
    queries_failed: int = 0


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
