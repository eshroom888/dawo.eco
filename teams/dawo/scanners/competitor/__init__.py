"""Competitor Content Scanner package.

Epic 6, Story 6-5: Scans competitor Instagram accounts and websites
for content, detects health language keywords for evidence collection.

This is the first scanner in the CleanMarket evidence chain
(Stories 6-5 → 6-6 → 6-7 → 6-8 → 6-9 → 6-10).
"""

from teams.dawo.scanners.competitor.config import (
    CompetitorConfig,
    CompetitorScannerConfig,
    InstagramScanConfig,
    WebsiteScanConfig,
    build_competitor_scanner_config,
)
from teams.dawo.scanners.competitor.duplicate_checker import CompetitorDuplicateChecker
from teams.dawo.scanners.competitor.parser import CompetitorContentParser
from teams.dawo.scanners.competitor.pipeline import CompetitorScanPipeline
from teams.dawo.scanners.competitor.repository import CompetitorRepository
from teams.dawo.scanners.competitor.schemas import (
    CompetitorScanResult,
    CompetitorScanStatus,
    HealthLanguageResult,
    ParsedContent,
    RobotsTxtResult,
    ScrapedPage,
)
from teams.dawo.scanners.competitor.website_client import WebsiteScraperClient

__all__ = [
    "CompetitorConfig",
    "CompetitorContentParser",
    "CompetitorDuplicateChecker",
    "CompetitorRepository",
    "CompetitorScannerConfig",
    "CompetitorScanPipeline",
    "CompetitorScanResult",
    "CompetitorScanStatus",
    "HealthLanguageResult",
    "InstagramScanConfig",
    "ParsedContent",
    "RobotsTxtResult",
    "ScrapedPage",
    "WebsiteScraperClient",
    "WebsiteScanConfig",
    "build_competitor_scanner_config",
]
