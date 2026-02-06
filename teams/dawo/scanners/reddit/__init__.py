"""Reddit Research Scanner for DAWO research intelligence pipeline.

This module implements the first scanner in the Harvester Framework,
establishing the pattern for subsequent scanners (YouTube, Instagram, News, PubMed).

Harvester Framework Pipeline:
    [Scanner] → [Harvester] → [Transformer] → [Validator] → [Scorer] → [Publisher] → [Research Pool]

Components:
    - RedditScanner: Main agent class for scan stage
    - RedditClient: OAuth2 Reddit API client
    - RedditHarvester: Enriches posts with full details
    - RedditTransformer: Standardizes data for Research Pool
    - RedditValidator: EU compliance validation
    - RedditResearchPipeline: Orchestrates full pipeline

Configuration:
    - RedditClientConfig: API credentials (from environment)
    - RedditScannerConfig: Scanner behavior settings

Schemas:
    - RawRedditPost: Raw API search result
    - HarvestedPost: Enriched post with details
    - ValidatedResearch: Post-compliance data
    - ScanResult: Scanner output with stats
    - PipelineResult: Full pipeline result
    - PipelineStatus: Pipeline status enum

Exceptions:
    - RedditAPIError: API-level errors
    - RedditAuthError: Authentication failures
    - RedditRateLimitError: Rate limit exceeded
    - RedditScanError: Scanner-level errors

Usage:
    from teams.dawo.scanners.reddit import (
        RedditScanner,
        RedditClient,
        RedditClientConfig,
        RedditScannerConfig,
        RedditResearchPipeline,
    )

    # Components are created and wired by Team Builder
    pipeline = RedditResearchPipeline(scanner, harvester, transformer, validator, publisher)
    result = await pipeline.execute()

Registration:
    All components registered in teams/dawo/team_spec.py
    Scanner uses tier="scan" (maps to fast model at runtime)
"""

from .agent import RedditScanner, RedditScanError
from .tools import (
    RedditClient,
    RedditAPIError,
    RedditAuthError,
    RedditRateLimitError,
)
from .config import (
    RedditClientConfig,
    RedditScannerConfig,
    DEFAULT_MIN_UPVOTES,
    DEFAULT_TIME_FILTER,
    DEFAULT_MAX_POSTS_PER_SUBREDDIT,
    DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE,
    DEFAULT_SUBREDDITS,
    DEFAULT_KEYWORDS,
    MAX_CONTENT_LENGTH,
)
from .schemas import (
    RawRedditPost,
    HarvestedPost,
    ValidatedResearch,
    ScanResult,
    ScanStatistics,
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
)
from .prompts import RELEVANCE_FILTER_PROMPT, TAG_GENERATION_PROMPT
from .harvester import RedditHarvester, HarvesterError
from .transformer import RedditTransformer, TransformerError
from .validator import RedditValidator, ValidatorError
from .pipeline import RedditResearchPipeline, PipelineError

__all__ = [
    # Main agent
    "RedditScanner",
    # Client
    "RedditClient",
    # Config
    "RedditClientConfig",
    "RedditScannerConfig",
    # Config constants
    "DEFAULT_MIN_UPVOTES",
    "DEFAULT_TIME_FILTER",
    "DEFAULT_MAX_POSTS_PER_SUBREDDIT",
    "DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE",
    "DEFAULT_SUBREDDITS",
    "DEFAULT_KEYWORDS",
    "MAX_CONTENT_LENGTH",
    # Schemas
    "RawRedditPost",
    "HarvestedPost",
    "ValidatedResearch",
    "ScanResult",
    "ScanStatistics",
    "PipelineResult",
    "PipelineStatistics",
    "PipelineStatus",
    # Prompts
    "RELEVANCE_FILTER_PROMPT",
    "TAG_GENERATION_PROMPT",
    # Exceptions
    "RedditAPIError",
    "RedditAuthError",
    "RedditRateLimitError",
    "RedditScanError",
    "HarvesterError",
    "TransformerError",
    "ValidatorError",
    "PipelineError",
    # Pipeline stages
    "RedditHarvester",
    "RedditTransformer",
    "RedditValidator",
    "RedditResearchPipeline",
]
