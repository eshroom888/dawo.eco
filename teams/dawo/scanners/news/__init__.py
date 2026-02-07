"""Industry News Scanner for DAWO research intelligence pipeline.

This module implements the FOURTH scanner in the Harvester Framework,
following the pattern established by Reddit Scanner (Story 2.3),
YouTube Scanner (Story 2.4), and Instagram Scanner (Story 2.5).

UNIQUE to News Scanner:
    - Fully rule-based: NO LLM stages (unlike Instagram's ThemeExtractor/ClaimDetector)
    - Uses tier="scan" for ALL components (pattern matching, no model calls)
    - Categorization and priority scoring use keyword pattern matching
    - Lower cost per execution, suitable for daily frequency

Harvester Framework Pipeline:
    [Scanner] -> [Harvester] -> [Categorizer] -> [PriorityScorer] -> [Transformer] -> [Validator] -> [Scorer] -> [Publisher] -> [Research Pool]
         |           |               |                  |                  |              |            |           |
       scan()     harvest()     categorize()   calculate_priority()    transform()    validate()    score()    publish()
       tier=scan  tier=scan      tier=scan           tier=scan           tier=scan      tier=scan   tier=scan   tier=scan

Components:
    - NewsScanner: Main agent class for scan stage
    - NewsFeedClient: RSS/Atom feed client
    - NewsHarvester: Cleans and normalizes articles
    - NewsCategorizer: Rule-based categorization (tier=scan, no LLM)
    - NewsPriorityScorer: Rule-based priority scoring (tier=scan, no LLM)
    - NewsTransformer: Standardizes data for Research Pool
    - NewsValidator: EU compliance validation
    - NewsResearchPipeline: Orchestrates full pipeline

Configuration:
    - FeedSource: Individual feed configuration
    - NewsFeedClientConfig: Feed client settings
    - NewsScannerConfig: Scanner behavior settings

Schemas:
    - RawNewsArticle: Raw RSS feed entry
    - HarvestedArticle: Cleaned article
    - NewsCategory: Article category enum
    - PriorityLevel: Priority level enum
    - CategoryResult: Categorization result
    - PriorityScore: Priority scoring result
    - ValidatedResearch: Post-compliance data
    - ScanResult: Scanner output with stats
    - PipelineResult: Full pipeline result
    - PipelineStatus: Pipeline status enum

Exceptions:
    - NewsScanError: Scanner-level errors
    - FeedFetchError: Feed fetch failures
    - FeedParseError: Feed parse failures
    - HarvesterError: Harvester stage errors
    - TransformerError: Transformer stage errors
    - ValidatorError: Validator stage errors
    - PipelineError: Pipeline orchestration errors

Usage:
    from teams.dawo.scanners.news import (
        NewsScanner,
        NewsFeedClient,
        NewsScannerConfig,
        NewsResearchPipeline,
    )

    # Components are created and wired by Team Builder
    pipeline = NewsResearchPipeline(
        scanner, harvester, transformer, validator, scorer, publisher
    )
    result = await pipeline.execute()

Registration:
    All components registered in teams/dawo/team_spec.py
    - All stages use tier="scan" (rule-based, no actual LLM calls)
"""

from .agent import NewsScanner, NewsScanError
from .tools import (
    NewsFeedClient,
    FeedFetchError,
    FeedParseError,
)
from .config import (
    FeedSource,
    NewsFeedClientConfig,
    NewsScannerConfig,
    # Config constants
    DEFAULT_FETCH_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_HOURS_BACK,
    DEFAULT_KEYWORDS,
    MAX_SUMMARY_LENGTH,
)
from .schemas import (
    RawNewsArticle,
    HarvestedArticle,
    NewsCategory,
    PriorityLevel,
    CategoryResult,
    PriorityScore,
    ValidatedResearch,
    ScanResult,
    ScanStatistics,
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
)
from .patterns import (
    REGULATORY_PATTERNS,
    HIGH_PRIORITY_KEYWORDS,
    RESEARCH_PATTERNS,
    PRODUCT_NEWS_PATTERNS,
    MUSHROOM_KEYWORDS,
)

# Pipeline stages
from .harvester import NewsHarvester, HarvesterError
from .categorizer import NewsCategorizer
from .priority_scorer import NewsPriorityScorer
from .transformer import NewsTransformer, TransformerError
from .validator import NewsValidator, ValidatorError
from .pipeline import NewsResearchPipeline, PipelineError

__all__ = [
    # Main agent
    "NewsScanner",
    # Clients
    "NewsFeedClient",
    # Config
    "FeedSource",
    "NewsFeedClientConfig",
    "NewsScannerConfig",
    # Config constants
    "DEFAULT_FETCH_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_HOURS_BACK",
    "DEFAULT_KEYWORDS",
    "MAX_SUMMARY_LENGTH",
    # Schemas
    "RawNewsArticle",
    "HarvestedArticle",
    "NewsCategory",
    "PriorityLevel",
    "CategoryResult",
    "PriorityScore",
    "ValidatedResearch",
    "ScanResult",
    "ScanStatistics",
    "PipelineResult",
    "PipelineStatistics",
    "PipelineStatus",
    # Patterns (rule-based categorization)
    "REGULATORY_PATTERNS",
    "HIGH_PRIORITY_KEYWORDS",
    "RESEARCH_PATTERNS",
    "PRODUCT_NEWS_PATTERNS",
    "MUSHROOM_KEYWORDS",
    # Exceptions
    "NewsScanError",
    "FeedFetchError",
    "FeedParseError",
    "HarvesterError",
    "TransformerError",
    "ValidatorError",
    "PipelineError",
    # Pipeline stages
    "NewsHarvester",
    "NewsCategorizer",
    "NewsPriorityScorer",
    "NewsTransformer",
    "NewsValidator",
    "NewsResearchPipeline",
]
