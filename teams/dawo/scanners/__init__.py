"""DAWO Scanner agents - Research and discovery.

Scanner agents discover content opportunities from external sources:
- Reddit, YouTube, PubMed, Instagram, News
- B2B lead research
- Competitor monitoring

All scanners operate at the 'scan' tier (maps to fast model at runtime).

Note: Use tier terminology, NEVER model names like "haiku" in code.
"""

from .reddit import (
    # Main agent
    RedditScanner,
    # Client
    RedditClient,
    # Config
    RedditClientConfig,
    RedditScannerConfig,
    # Config constants
    DEFAULT_MIN_UPVOTES,
    DEFAULT_TIME_FILTER,
    DEFAULT_MAX_POSTS_PER_SUBREDDIT,
    DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE,
    DEFAULT_SUBREDDITS,
    DEFAULT_KEYWORDS,
    MAX_CONTENT_LENGTH,
    # Schemas
    RawRedditPost,
    HarvestedPost,
    ValidatedResearch,
    ScanResult,
    ScanStatistics,
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
    # Pipeline stages
    RedditHarvester,
    RedditTransformer,
    RedditValidator,
    RedditResearchPipeline,
    # Exceptions
    RedditAPIError,
    RedditAuthError,
    RedditRateLimitError,
    RedditScanError,
    HarvesterError,
    TransformerError,
    ValidatorError,
    PipelineError,
)

__all__: list[str] = [
    # Reddit Scanner
    "RedditScanner",
    "RedditClient",
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
    # Pipeline stages
    "RedditHarvester",
    "RedditTransformer",
    "RedditValidator",
    "RedditResearchPipeline",
    # Exceptions
    "RedditAPIError",
    "RedditAuthError",
    "RedditRateLimitError",
    "RedditScanError",
    "HarvesterError",
    "TransformerError",
    "ValidatorError",
    "PipelineError",
]
