"""YouTube Research Scanner for DAWO research intelligence pipeline.

This module implements the second scanner in the Harvester Framework,
following the pattern established by Reddit Scanner (Story 2.3).

UNIQUE to YouTube Scanner: Includes LLM-powered KeyInsightExtractor stage
that uses tier="generate" (Sonnet) for quality summarization of transcripts.

Harvester Framework Pipeline (Extended for YouTube):
    [Scanner] -> [Harvester] -> [InsightExtractor] -> [Transformer] -> [Validator] -> [Scorer] -> [Publisher] -> [Research Pool]
         |           |               |                    |              |            |           |
       scan()     harvest()    extract_insights()     transform()    validate()    score()    publish()
       tier=scan  tier=scan    tier=generate          tier=scan      tier=scan   tier=scan   tier=scan

Components:
    - YouTubeScanner: Main agent class for scan stage
    - YouTubeClient: YouTube Data API v3 client
    - TranscriptClient: YouTube transcript extraction
    - YouTubeHarvester: Enriches videos with details and transcript
    - KeyInsightExtractor: LLM-powered insight extraction (tier=generate)
    - YouTubeTransformer: Standardizes data for Research Pool
    - YouTubeValidator: EU compliance validation
    - YouTubeResearchPipeline: Orchestrates full pipeline

Configuration:
    - YouTubeClientConfig: API key (from environment)
    - TranscriptConfig: Transcript extraction settings
    - YouTubeScannerConfig: Scanner behavior settings

Schemas:
    - RawYouTubeVideo: Raw API search result
    - HarvestedVideo: Enriched video with statistics
    - TranscriptResult: Transcript extraction result
    - QuotableInsight: Individual quotable insight
    - InsightResult: Full insight extraction result
    - ValidatedResearch: Post-compliance data
    - ScanResult: Scanner output with stats
    - PipelineResult: Full pipeline result
    - PipelineStatus: Pipeline status enum

Exceptions:
    - YouTubeAPIError: API-level errors
    - QuotaExhaustedError: Daily quota exceeded
    - YouTubeScanError: Scanner-level errors
    - TranscriptError: Transcript extraction errors

Usage:
    from teams.dawo.scanners.youtube import (
        YouTubeScanner,
        YouTubeClient,
        YouTubeClientConfig,
        YouTubeScannerConfig,
        YouTubeResearchPipeline,
    )

    # Components are created and wired by Team Builder
    pipeline = YouTubeResearchPipeline(scanner, harvester, extractor, transformer, validator, publisher)
    result = await pipeline.execute()

Registration:
    All components registered in teams/dawo/team_spec.py
    - Scanner stages: tier="scan" (maps to fast model at runtime)
    - KeyInsightExtractor: tier="generate" (maps to quality model at runtime)
"""

from .agent import YouTubeScanner
from .tools import (
    YouTubeClient,
    TranscriptClient,
    QuotaTracker,
    YouTubeAPIError,
    QuotaExhaustedError,
    YouTubeScanError,
    TranscriptError,
)
from .config import (
    YouTubeClientConfig,
    TranscriptConfig,
    YouTubeScannerConfig,
    # Config constants
    YOUTUBE_DAILY_QUOTA,
    SEARCH_QUOTA_COST,
    VIDEO_QUOTA_COST,
    DEFAULT_SEARCH_QUERIES,
    DEFAULT_MIN_VIEWS,
    DEFAULT_DAYS_BACK,
    DEFAULT_MAX_VIDEOS_PER_QUERY,
    DEFAULT_PREFERRED_LANGUAGES,
    DEFAULT_MAX_TRANSCRIPT_LENGTH,
    MAX_CONTENT_LENGTH,
    DEFAULT_HEALTH_CHANNEL_KEYWORDS,
)
from .schemas import (
    RawYouTubeVideo,
    HarvestedVideo,
    TranscriptResult,
    QuotableInsight,
    InsightResult,
    ValidatedResearch,
    ScanResult,
    ScanStatistics,
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
)
from .prompts import (
    KEY_INSIGHT_EXTRACTION_PROMPT,
    KEY_INSIGHT_EXTRACTION_SHORT_PROMPT,
    TAG_GENERATION_PROMPT,
    SHORT_TRANSCRIPT_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
)

# Pipeline stages - added as implemented
from .harvester import YouTubeHarvester, HarvesterError
from .insight_extractor import KeyInsightExtractor, InsightExtractionError
from .transformer import YouTubeTransformer, TransformerError
from .validator import YouTubeValidator, ValidatorError
from .pipeline import YouTubeResearchPipeline, PipelineError

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
    # Config constants
    "YOUTUBE_DAILY_QUOTA",
    "SEARCH_QUOTA_COST",
    "VIDEO_QUOTA_COST",
    "DEFAULT_SEARCH_QUERIES",
    "DEFAULT_MIN_VIEWS",
    "DEFAULT_DAYS_BACK",
    "DEFAULT_MAX_VIDEOS_PER_QUERY",
    "DEFAULT_PREFERRED_LANGUAGES",
    "DEFAULT_MAX_TRANSCRIPT_LENGTH",
    "MAX_CONTENT_LENGTH",
    "DEFAULT_HEALTH_CHANNEL_KEYWORDS",
    # Schemas
    "RawYouTubeVideo",
    "HarvestedVideo",
    "TranscriptResult",
    "QuotableInsight",
    "InsightResult",
    "ValidatedResearch",
    "ScanResult",
    "ScanStatistics",
    "PipelineResult",
    "PipelineStatistics",
    "PipelineStatus",
    # Prompts
    "KEY_INSIGHT_EXTRACTION_PROMPT",
    "KEY_INSIGHT_EXTRACTION_SHORT_PROMPT",
    "TAG_GENERATION_PROMPT",
    "SHORT_TRANSCRIPT_THRESHOLD",
    "LOW_CONFIDENCE_THRESHOLD",
    # Exceptions
    "YouTubeAPIError",
    "QuotaExhaustedError",
    "YouTubeScanError",
    "TranscriptError",
    "HarvesterError",
    "InsightExtractionError",
    "TransformerError",
    "ValidatorError",
    "PipelineError",
    # Pipeline stages - added as implemented
    "YouTubeHarvester",
    "KeyInsightExtractor",
    "YouTubeTransformer",
    "YouTubeValidator",
    "YouTubeResearchPipeline",
]
