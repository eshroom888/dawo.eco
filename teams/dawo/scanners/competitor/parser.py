"""Competitor Content Parser.

Epic 6, Story 6-5, Task 5: Parse Instagram posts and website pages,
detect health language via keyword pre-filter.

This is a SIMPLE keyword pre-filter, NOT LLM-based claim extraction
(that's Story 6-6).
"""

import hashlib
import logging
import re
from datetime import datetime, UTC
from typing import Optional
from urllib.parse import urlparse

from teams.dawo.scanners.competitor.config import CompetitorConfig
from teams.dawo.scanners.competitor.schemas import (
    HealthLanguageResult,
    ParsedContent,
    ScrapedPage,
)

logger = logging.getLogger(__name__)


class CompetitorContentParser:
    """Parser for competitor content from Instagram and websites.

    Extracts text content and runs keyword-based health language detection.
    No LLM calls — pure deterministic processing.

    Args:
        health_language_keywords: Tuple of keywords to match (English + Norwegian)
    """

    def __init__(self, health_language_keywords: tuple[str, ...]) -> None:
        self._keywords = health_language_keywords

    def parse_instagram_post(
        self, post_data: dict, competitor: CompetitorConfig
    ) -> ParsedContent:
        """Parse an Instagram post from API response format.

        Args:
            post_data: Dict from InstagramClient.get_user_media()
            competitor: Competitor configuration

        Returns:
            ParsedContent with extracted data
        """
        caption = post_data.get("caption") or ""
        permalink = post_data.get("permalink", "")
        timestamp_str = post_data.get("timestamp", "")

        # Extract hashtags from caption
        hashtags = re.findall(r"#\w+", caption) if caption else []

        # Parse timestamp
        published_at: Optional[datetime] = None
        if timestamp_str:
            try:
                published_at = datetime.fromisoformat(
                    timestamp_str.replace("+0000", "+00:00")
                )
            except (ValueError, TypeError):
                logger.debug("Failed to parse timestamp: %s", timestamp_str)

        # Detect health language
        health_result = self.detect_health_language(caption)

        # Compute content hash
        content_hash = self.compute_content_hash(caption)

        return ParsedContent(
            source_type="instagram",
            competitor_name=competitor.name,
            source_url=permalink,
            content_text=caption,
            hashtags=hashtags,
            account_or_domain=competitor.instagram_username or competitor.name,
            published_at=published_at,
            content_hash=content_hash,
            has_health_language=health_result.has_health_language,
            health_keywords_matched=health_result.keywords_matched,
        )

    def parse_website_page(
        self, page: ScrapedPage, competitor: CompetitorConfig
    ) -> ParsedContent:
        """Parse a scraped website page.

        Args:
            page: ScrapedPage from WebsiteScraperClient
            competitor: Competitor configuration

        Returns:
            ParsedContent with extracted data
        """
        # Extract domain from URL
        domain = urlparse(page.url).netloc

        # Combine title + content for full text
        full_text = f"{page.title} {page.content_text}".strip()

        # Detect health language
        health_result = self.detect_health_language(full_text)

        # Compute content hash
        content_hash = self.compute_content_hash(full_text)

        return ParsedContent(
            source_type="website",
            competitor_name=competitor.name,
            source_url=page.url,
            content_text=full_text,
            hashtags=[],
            account_or_domain=domain,
            published_at=None,
            content_hash=content_hash,
            has_health_language=health_result.has_health_language,
            health_keywords_matched=health_result.keywords_matched,
        )

    def detect_health_language(self, text: str) -> HealthLanguageResult:
        """Detect health language keywords in text.

        Case-insensitive keyword matching against configured keyword list.
        This is a SIMPLE pre-filter, NOT LLM-based claim extraction.

        Args:
            text: Text content to analyze

        Returns:
            HealthLanguageResult with match details
        """
        if not text:
            return HealthLanguageResult(
                has_health_language=False,
                keywords_matched=[],
                keyword_count=0,
            )

        text_lower = text.lower()
        matched: list[str] = []

        for keyword in self._keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)

        return HealthLanguageResult(
            has_health_language=len(matched) > 0,
            keywords_matched=matched,
            keyword_count=len(matched),
        )

    def compute_content_hash(self, text: str) -> str:
        """Compute SHA-256 hash of normalized text for deduplication.

        Normalization: lowercase, whitespace collapsed.

        Args:
            text: Text to hash

        Returns:
            Hex-encoded SHA-256 hash string (64 chars)
        """
        normalized = re.sub(r"\s+", " ", text.lower().strip())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


__all__ = [
    "CompetitorContentParser",
]
