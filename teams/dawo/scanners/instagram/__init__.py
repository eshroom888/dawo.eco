"""Instagram Trend Scanner for DAWO research intelligence pipeline.

This module implements the THIRD scanner in the Harvester Framework,
following the pattern established by Reddit Scanner (Story 2.3) and
YouTube Scanner (Story 2.4).

UNIQUE to Instagram Scanner:
    - TWO LLM stages: ThemeExtractor AND HealthClaimDetector (both use tier="generate")
    - CleanMarket integration point for flagging competitor health claims (Epic 6)
    - NO image/video storage - text and metadata only (privacy/copyright compliance)
    - Daily schedule (vs YouTube's weekly) - more frequent trend monitoring

Harvester Framework Pipeline (Extended for Instagram):
    [Scanner] -> [Harvester] -> [ThemeExtractor] -> [ClaimDetector] -> [Transformer] -> [Validator] -> [Scorer] -> [Publisher] -> [Research Pool]
         |           |               |                   |                  |              |            |           |
       scan()     harvest()   extract_themes()    detect_claims()     transform()    validate()    score()    publish()
       tier=scan  tier=scan    tier=generate       tier=generate       tier=scan      tier=scan   tier=scan   tier=scan

Components:
    - InstagramScanner: Main agent class for scan stage
    - InstagramClient: Instagram Graph API client
    - RateLimitTracker: Hourly rate limit management
    - InstagramHarvester: Enriches posts with full metadata
    - ThemeExtractor: LLM-powered theme extraction (tier=generate)
    - HealthClaimDetector: LLM-powered claim detection (tier=generate)
    - InstagramTransformer: Standardizes data for Research Pool
    - InstagramValidator: EU compliance validation
    - InstagramResearchPipeline: Orchestrates full pipeline

Configuration:
    - InstagramClientConfig: API credentials (from environment)
    - InstagramScannerConfig: Scanner behavior settings

Schemas:
    - RawInstagramPost: Raw API search result
    - HarvestedPost: Enriched post with metadata (NO images)
    - ThemeResult: Theme extraction result
    - DetectedClaim: Individual health claim
    - ClaimDetectionResult: Full claim detection result
    - ClaimCategory: Health claim categories
    - ValidatedResearch: Post-compliance data
    - ScanResult: Scanner output with stats
    - PipelineResult: Full pipeline result
    - PipelineStatus: Pipeline status enum

Exceptions:
    - InstagramAPIError: API-level errors
    - RateLimitError: Hourly rate limit exceeded
    - InstagramScanError: Scanner-level errors
    - HarvesterError: Harvester stage errors
    - ThemeExtractionError: Theme extraction errors
    - ClaimDetectionError: Claim detection errors
    - TransformerError: Transformer stage errors
    - ValidatorError: Validator stage errors
    - PipelineError: Pipeline orchestration errors

Usage:
    from teams.dawo.scanners.instagram import (
        InstagramScanner,
        InstagramClient,
        InstagramClientConfig,
        InstagramScannerConfig,
        InstagramResearchPipeline,
    )

    # Components are created and wired by Team Builder
    pipeline = InstagramResearchPipeline(
        scanner, harvester, theme_extractor, claim_detector,
        transformer, validator, scorer, publisher
    )
    result = await pipeline.execute()

Registration:
    All components registered in teams/dawo/team_spec.py
    - Scanner stages: tier="scan" (maps to fast model at runtime)
    - ThemeExtractor: tier="generate" (maps to quality model at runtime)
    - HealthClaimDetector: tier="generate" (maps to quality model at runtime)
"""

from .agent import InstagramScanner
from .tools import (
    InstagramClient,
    RateLimitTracker,
    InstagramAPIError,
    RateLimitError,
    InstagramScanError,
    extract_hashtags,
)
from .config import (
    InstagramClientConfig,
    InstagramScannerConfig,
    # Config constants
    INSTAGRAM_RATE_LIMIT_PER_HOUR,
    INSTAGRAM_MAX_RESULTS_PER_CALL,
    DEFAULT_HASHTAGS,
    DEFAULT_HOURS_BACK,
    DEFAULT_MAX_POSTS_PER_HASHTAG,
    DEFAULT_MAX_POSTS_PER_ACCOUNT,
    MAX_CAPTION_LENGTH,
    MAX_CONTENT_LENGTH,
    HEALTH_CLAIM_INDICATORS,
)
from .schemas import (
    RawInstagramPost,
    HarvestedPost,
    ThemeResult,
    DetectedClaim,
    ClaimDetectionResult,
    ClaimCategory,
    ValidatedResearch,
    ScanResult,
    ScanStatistics,
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
)
from .prompts import (
    THEME_EXTRACTION_PROMPT,
    THEME_EXTRACTION_SHORT_PROMPT,
    HEALTH_CLAIM_DETECTION_PROMPT,
    TAG_GENERATION_PROMPT,
    SHORT_CAPTION_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
)

# Pipeline stages
from .harvester import InstagramHarvester, HarvesterError
from .theme_extractor import ThemeExtractor, ThemeExtractionError
from .claim_detector import HealthClaimDetector, ClaimDetectionError
from .transformer import InstagramTransformer, TransformerError
from .validator import InstagramValidator, ValidatorError
from .pipeline import InstagramResearchPipeline, PipelineError

__all__ = [
    # Main agent
    "InstagramScanner",
    # Clients
    "InstagramClient",
    "RateLimitTracker",
    # Config
    "InstagramClientConfig",
    "InstagramScannerConfig",
    # Config constants
    "INSTAGRAM_RATE_LIMIT_PER_HOUR",
    "INSTAGRAM_MAX_RESULTS_PER_CALL",
    "DEFAULT_HASHTAGS",
    "DEFAULT_HOURS_BACK",
    "DEFAULT_MAX_POSTS_PER_HASHTAG",
    "DEFAULT_MAX_POSTS_PER_ACCOUNT",
    "MAX_CAPTION_LENGTH",
    "MAX_CONTENT_LENGTH",
    "HEALTH_CLAIM_INDICATORS",
    # Schemas
    "RawInstagramPost",
    "HarvestedPost",
    "ThemeResult",
    "DetectedClaim",
    "ClaimDetectionResult",
    "ClaimCategory",
    "ValidatedResearch",
    "ScanResult",
    "ScanStatistics",
    "PipelineResult",
    "PipelineStatistics",
    "PipelineStatus",
    # Prompts
    "THEME_EXTRACTION_PROMPT",
    "THEME_EXTRACTION_SHORT_PROMPT",
    "HEALTH_CLAIM_DETECTION_PROMPT",
    "TAG_GENERATION_PROMPT",
    "SHORT_CAPTION_THRESHOLD",
    "LOW_CONFIDENCE_THRESHOLD",
    # Exceptions
    "InstagramAPIError",
    "RateLimitError",
    "InstagramScanError",
    "HarvesterError",
    "ThemeExtractionError",
    "ClaimDetectionError",
    "TransformerError",
    "ValidatorError",
    "PipelineError",
    # Utility functions
    "extract_hashtags",
    # Pipeline stages
    "InstagramHarvester",
    "ThemeExtractor",
    "HealthClaimDetector",
    "InstagramTransformer",
    "InstagramValidator",
    "InstagramResearchPipeline",
]
