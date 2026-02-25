"""Mattilsynet monitor data transfer objects.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.

Dataclasses for passing data between pipeline stages.
These are NOT SQLAlchemy models — they are plain data containers.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional


@dataclass
class FeedItemRecord:
    """DTO for a parsed RSS/Atom feed item.

    Attributes:
        title: Feed item title
        url: Feed item link URL
        published_at: Publication datetime (timezone-aware)
        summary: Feed item summary/description
        categories: Feed item categories/tags
        content_hash: SHA-256 hash of item content
        feed_name: Name of the source feed
    """

    title: str
    url: str
    published_at: Optional[datetime] = None
    summary: str = ""
    categories: tuple[str, ...] = ()
    content_hash: str = ""
    feed_name: str = ""


@dataclass
class ArticleRecord:
    """DTO for a parsed HTML article page.

    Attributes:
        title: Article title from h1
        url: Source page URL
        published_at: Publication date extracted from page
        body_text: Extracted body text content
        content_hash: SHA-256 hash of extracted content
    """

    title: str
    url: str
    published_at: Optional[datetime] = None
    body_text: str = ""
    content_hash: str = ""


@dataclass
class KeywordMatchResult:
    """Result of keyword matching against text.

    Attributes:
        is_relevant: Whether any keywords matched
        relevance_tier: Matched tier (0=none, 1=high, 2=medium)
        matched_keywords: Tuple of matched keyword strings
        is_enforcement: Whether enforcement keywords matched
    """

    is_relevant: bool = False
    relevance_tier: int = 0
    matched_keywords: tuple[str, ...] = ()
    is_enforcement: bool = False


@dataclass
class PageChangeResult:
    """Result of page change detection.

    Attributes:
        url: Monitored page URL
        changed: Whether content changed since last check
        current_hash: Current SHA-256 hash of content
        content: Extracted content (only if changed)
    """

    url: str
    changed: bool = False
    current_hash: str = ""
    content: Optional[str] = None


@dataclass
class RegulatoryUpdateRecord:
    """DTO for a regulatory update to persist.

    Attributes:
        title: Update headline
        url: Source URL
        content_summary: Brief summary
        published_at: Publication datetime
        source_type: MattilsynetSourceType value
        category: MattilsynetCategory value
        keywords_matched: List of matched keywords
        relevance_tier: Keyword tier (0, 1, 2)
        severity: Alert severity
        is_relevant: Whether relevant to DAWO
        is_enforcement: Whether enforcement keywords matched
        raw_content_hash: SHA-256 of raw content
    """

    title: str
    url: str
    content_summary: str = ""
    published_at: Optional[datetime] = None
    source_type: str = ""
    category: str = ""
    keywords_matched: list[str] = field(default_factory=list)
    relevance_tier: int = 0
    severity: str = "low"
    is_relevant: bool = False
    is_enforcement: bool = False
    raw_content_hash: str = ""


@dataclass
class MattilsynetMonitorResult:
    """Result of a Mattilsynet monitor pipeline execution.

    Attributes:
        status: Execution status (complete/incomplete/partial/failed)
        total_updates: Total updates found
        relevant_updates: Relevant updates
        page_changes: Number of page changes detected
        feeds_checked: Number of feeds checked
        pages_checked: Number of pages checked
        errors: List of error messages
        scan_duration_seconds: Total scan time
        executed_at: When pipeline ran
    """

    status: str = "complete"
    total_updates: int = 0
    relevant_updates: int = 0
    page_changes: int = 0
    feeds_checked: int = 0
    pages_checked: int = 0
    errors: list[str] = field(default_factory=list)
    scan_duration_seconds: float = 0.0
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "status": self.status,
            "total_updates": self.total_updates,
            "relevant_updates": self.relevant_updates,
            "page_changes": self.page_changes,
            "feeds_checked": self.feeds_checked,
            "pages_checked": self.pages_checked,
            "errors": self.errors,
            "scan_duration_seconds": self.scan_duration_seconds,
            "executed_at": self.executed_at.isoformat(),
        }


__all__ = [
    "ArticleRecord",
    "FeedItemRecord",
    "KeywordMatchResult",
    "MattilsynetMonitorResult",
    "PageChangeResult",
    "RegulatoryUpdateRecord",
]
