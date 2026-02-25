"""Mattilsynet HTML page parser.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 6: Extract article content from Mattilsynet HTML pages.
"""

import hashlib
import logging
from datetime import datetime

from bs4 import BeautifulSoup

from teams.dawo.scanners.mattilsynet.schemas import ArticleRecord

logger = logging.getLogger(__name__)

# Multiple fallback selectors for content extraction
CONTENT_SELECTORS = [
    "article.article-body",
    "main .content-area",
    ".article-content",
    "main article",
    "main",
    "#content",
]

TITLE_SELECTORS = ["h1", ".article-title", ".page-title"]

DATE_SELECTORS = ["time[datetime]", ".article-date", ".published-date"]


class PageParseError(Exception):
    """Error parsing HTML page content."""


class MattilsynetPageParser:
    """Parser for Mattilsynet HTML pages.

    Extracts main content, title, date from article pages
    using multiple fallback CSS selectors.
    """

    def extract_main_content(self, data: bytes) -> str:
        """Extract main content area from HTML, stripping nav/footer/sidebar.

        Args:
            data: Raw HTML bytes

        Returns:
            Extracted text content

        Raises:
            PageParseError: If no content selectors match
        """
        soup = BeautifulSoup(data, "lxml")

        # Remove navigation, footer, sidebar
        for tag_name in ["nav", "footer", "aside", "header"]:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Try content selectors in order
        for selector in CONTENT_SELECTORS:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator="\n", strip=True)
                if text:
                    return text

        raise PageParseError(
            "No content found with any selector: "
            + ", ".join(CONTENT_SELECTORS)
        )

    def parse_article(self, data: bytes, url: str) -> ArticleRecord:
        """Parse a single article page.

        Args:
            data: Raw HTML bytes
            url: Source page URL

        Returns:
            ArticleRecord with extracted content

        Raises:
            PageParseError: If content extraction fails
        """
        soup = BeautifulSoup(data, "lxml")

        # Remove nav/footer/sidebar before content extraction
        for tag_name in ["nav", "footer", "aside", "header"]:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        title = self._extract_title(soup)
        published_at = self._extract_date(soup)
        body_text = self._extract_body(soup)
        content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()

        return ArticleRecord(
            title=title,
            url=url,
            published_at=published_at,
            body_text=body_text,
            content_hash=content_hash,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title using fallback selectors."""
        for selector in TITLE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return ""

    def _extract_date(self, soup: BeautifulSoup) -> datetime | None:
        """Extract publication date."""
        for selector in DATE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                dt_attr = element.get("datetime")
                if dt_attr:
                    try:
                        return datetime.fromisoformat(str(dt_attr))
                    except (ValueError, TypeError):
                        logger.debug(
                            "Could not parse datetime attribute: %s", dt_attr
                        )
        return None

    def _extract_body(self, soup: BeautifulSoup) -> str:
        """Extract body text using fallback content selectors."""
        for selector in CONTENT_SELECTORS:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator="\n", strip=True)
                if text:
                    return text
        return ""


__all__ = [
    "MattilsynetPageParser",
    "PageParseError",
]
