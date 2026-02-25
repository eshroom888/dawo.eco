"""Mattilsynet regulatory monitor scanner.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.

Monitors the Norwegian Food Safety Authority (Mattilsynet) for regulatory
changes via RSS feeds and hash-based page change detection.
"""

from teams.dawo.scanners.mattilsynet.change_detector import PageChangeDetector
from teams.dawo.scanners.mattilsynet.client import (
    MattilsynetClient,
    MattilsynetClientError,
    RetryMiddlewareProtocol,
    RetryResultProtocol,
)
from teams.dawo.scanners.mattilsynet.config import (
    FeedConfig,
    MattilsynetMonitorConfig,
    MonitoredPageConfig,
    build_mattilsynet_config,
)
from teams.dawo.scanners.mattilsynet.feed_parser import (
    FeedParseError,
    MattilsynetFeedParser,
)
from teams.dawo.scanners.mattilsynet.keyword_matcher import NorwegianKeywordMatcher
from teams.dawo.scanners.mattilsynet.page_parser import (
    MattilsynetPageParser,
    PageParseError,
)
from teams.dawo.scanners.mattilsynet.pipeline import MattilsynetMonitorPipeline
from teams.dawo.scanners.mattilsynet.repository import MattilsynetRepository
from teams.dawo.scanners.mattilsynet.schemas import (
    ArticleRecord,
    FeedItemRecord,
    KeywordMatchResult,
    MattilsynetMonitorResult,
    PageChangeResult,
    RegulatoryUpdateRecord,
)

__all__ = [
    "ArticleRecord",
    "FeedConfig",
    "FeedItemRecord",
    "FeedParseError",
    "KeywordMatchResult",
    "MattilsynetClient",
    "MattilsynetClientError",
    "MattilsynetMonitorConfig",
    "MattilsynetMonitorPipeline",
    "MattilsynetMonitorResult",
    "MattilsynetPageParser",
    "MattilsynetFeedParser",
    "MattilsynetRepository",
    "MonitoredPageConfig",
    "NorwegianKeywordMatcher",
    "PageChangeDetector",
    "PageChangeResult",
    "PageParseError",
    "RegulatoryUpdateRecord",
    "RetryMiddlewareProtocol",
    "RetryResultProtocol",
    "build_mattilsynet_config",
]
