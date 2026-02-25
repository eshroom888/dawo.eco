"""Configuration for Lead Enrichment.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment

Provides configuration dataclasses for:
- EnrichmentConfig: Main enrichment service configuration
- ConfidenceScoreWeights: Confidence score weights
- LeadScoreWeights: Lead qualification score weights
"""

from dataclasses import dataclass, field


# Configuration constants
MIN_CONFIDENCE_THRESHOLD = 5
DEFAULT_BATCH_SIZE = 10
DEFAULT_WEBSITE_TIMEOUT = 5
DEFAULT_RATE_LIMIT_PER_SECOND = 1.0


# DAWO product keywords for existing customer detection
DAWO_PRODUCT_KEYWORDS = [
    "dawo",
    "dawo mushrooms",
    "dawo.eco",
    "lion's mane dawo",
    "chaga dawo",
    "reishi dawo",
    "cordyceps dawo",
]


@dataclass
class ConfidenceScoreWeights:
    """Weights for confidence score calculation.

    Maximum total score: 10.0

    Attributes:
        verified_email: Weight for verified email (+2)
        business_description: Weight for business description (+2)
        social_presence: Weight for social media presence (+1)
        decision_maker: Weight for decision maker contact (+1)
        industry_match: Weight for industry match (+1)
        product_categories: Weight for product categories (+1)
        personalization_hooks: Weight for personalization hooks (+1)
        website_accessible: Weight for accessible website (+1)
    """

    verified_email: float = 2.0
    business_description: float = 2.0
    social_presence: float = 1.0
    decision_maker: float = 1.0
    industry_match: float = 1.0
    product_categories: float = 1.0
    personalization_hooks: float = 1.0
    website_accessible: float = 1.0


@dataclass
class LeadScoreWeights:
    """Weights for lead qualification score calculation.

    Total maximum score: 100

    Attributes:
        industry_relevance_max: Max score for industry relevance (0-30)
        company_size_max: Max score for company size fit (0-20)
        geographic_max: Max score for geographic fit (0-20)
        engagement_potential_max: Max score for engagement potential (0-15)
        data_completeness_max: Max score for data completeness (0-15)
    """

    industry_relevance_max: int = 30
    company_size_max: int = 20
    geographic_max: int = 20
    engagement_potential_max: int = 15
    data_completeness_max: int = 15


@dataclass
class EnrichmentConfig:
    """Lead Enrichment service configuration.

    Loaded via dependency injection from Team Builder.
    NEVER loads config files directly.

    Attributes:
        min_confidence_threshold: Minimum score for QUALIFIED status
        website_timeout_seconds: Timeout for website requests
        website_rate_limit_per_second: Max website requests per second
        batch_size: Number of leads to process per batch
        dawo_product_keywords: Keywords for existing customer detection
        score_weights: Confidence score calculation weights
        lead_score_weights: Lead qualification score weights
        schedule_cron: Cron schedule for enrichment agent
        schedule_timezone: Timezone for scheduling
    """

    # Thresholds
    min_confidence_threshold: float = float(MIN_CONFIDENCE_THRESHOLD)

    # Website analysis settings
    website_timeout_seconds: int = DEFAULT_WEBSITE_TIMEOUT
    website_rate_limit_per_second: float = DEFAULT_RATE_LIMIT_PER_SECOND

    # Pipeline settings
    batch_size: int = DEFAULT_BATCH_SIZE

    # DAWO product detection
    dawo_product_keywords: list[str] = field(
        default_factory=lambda: DAWO_PRODUCT_KEYWORDS.copy()
    )

    # Scoring weights
    score_weights: ConfidenceScoreWeights = field(
        default_factory=ConfidenceScoreWeights
    )
    lead_score_weights: LeadScoreWeights = field(
        default_factory=LeadScoreWeights
    )

    # Schedule (for reference - actual scheduling done by ARQ)
    schedule_cron: str = "0 8 * * *"  # Daily 8 AM (after scanner)
    schedule_timezone: str = "Europe/Oslo"
