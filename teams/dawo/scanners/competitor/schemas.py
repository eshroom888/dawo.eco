"""Competitor Scanner Schemas and DTOs.

Epic 6, Story 6-5, Task 9: Data transfer objects for competitor scanning pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CompetitorScanStatus(str, Enum):
    """Status of a competitor scan execution.

    Values:
        COMPLETE: All competitors scanned successfully
        PARTIAL: Some competitors failed, others succeeded
        FAILED: All competitors failed
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class ParsedContent:
    """Parsed competitor content item ready for storage.

    Attributes:
        source_type: Content source (instagram or website)
        competitor_name: Name of the competitor
        source_url: URL of the content
        content_text: Full text content
        hashtags: List of hashtags (empty for websites)
        account_or_domain: Instagram account or website domain
        published_at: When content was published
        content_hash: SHA-256 of normalized content for dedup
        has_health_language: Whether health language was detected
        health_keywords_matched: List of matched keywords
    """

    source_type: str
    competitor_name: str
    source_url: str
    content_text: str
    hashtags: list[str]
    account_or_domain: str
    published_at: Optional[datetime]
    content_hash: str
    has_health_language: bool
    health_keywords_matched: list[str]


@dataclass
class ScrapedPage:
    """Result of scraping a single website page.

    Attributes:
        url: Page URL
        title: Page title from <title> tag
        content_text: Extracted main text content
        meta_description: Content of <meta name="description">
        links: List of outbound links found
        fetched_at: When the page was fetched
    """

    url: str
    title: str
    content_text: str
    meta_description: str
    links: list[str]
    fetched_at: datetime


@dataclass
class RobotsTxtResult:
    """Result of checking robots.txt for a URL.

    Attributes:
        allowed: Whether the URL is allowed by robots.txt
        checked_at: When the check was performed
        robots_url: URL of the robots.txt file checked
    """

    allowed: bool
    checked_at: datetime
    robots_url: str


@dataclass
class HealthLanguageResult:
    """Result of health language keyword detection.

    Attributes:
        has_health_language: Whether any health keywords were found
        keywords_matched: List of keywords that matched
        keyword_count: Number of keywords matched
    """

    has_health_language: bool
    keywords_matched: list[str]
    keyword_count: int


@dataclass
class CompetitorScanResult:
    """Aggregate result of a complete competitor scan execution.

    Attributes:
        status: Scan execution status
        competitors_scanned: Number of competitors scanned
        total_content_found: Total content items discovered
        new_content_saved: New items saved to database
        duplicates_skipped: Items skipped as duplicates
        health_language_detected: Items flagged with health language
        errors: List of error messages from failed operations
    """

    status: CompetitorScanStatus
    competitors_scanned: int
    total_content_found: int
    new_content_saved: int
    duplicates_skipped: int
    health_language_detected: int
    errors: list[str] = field(default_factory=list)


__all__ = [
    "CompetitorScanResult",
    "CompetitorScanStatus",
    "HealthLanguageResult",
    "ParsedContent",
    "RobotsTxtResult",
    "ScrapedPage",
]
