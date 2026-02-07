"""NewsHarvester for cleaning and enriching news articles.

Implements the harvester stage of the Harvester Framework for news.
Cleans HTML content and normalizes article data.

Usage:
    harvester = NewsHarvester()
    harvested = harvester.harvest(raw_articles)
"""

import logging

from bs4 import BeautifulSoup

from .schemas import RawNewsArticle, HarvestedArticle
from .config import MAX_SUMMARY_LENGTH

logger = logging.getLogger(__name__)


class HarvesterError(Exception):
    """Raised when harvesting fails."""

    pass


class NewsHarvester:
    """Harvester for news articles.

    Cleans HTML from content and normalizes article data.
    This is a lightweight stage since RSS feeds provide pre-summarized content.
    """

    def harvest(self, articles: list[RawNewsArticle]) -> list[HarvestedArticle]:
        """Harvest and clean raw articles.

        Args:
            articles: Raw articles from scanner

        Returns:
            List of cleaned HarvestedArticle objects
        """
        harvested: list[HarvestedArticle] = []
        errors_count = 0

        for article in articles:
            try:
                cleaned = self._clean_article(article)
                harvested.append(cleaned)
            except Exception as e:
                errors_count += 1
                logger.warning("Failed to harvest article %s: %s", article.url, e)

        logger.info(
            "Harvested %d articles, %d failed",
            len(harvested),
            errors_count,
        )
        return harvested

    def _clean_article(self, article: RawNewsArticle) -> HarvestedArticle:
        """Clean and normalize a single article.

        Applies HTML cleaning for defense-in-depth (tools.py also cleans during parsing).
        Handles normalization (trimming, truncation).

        Args:
            article: Raw article to clean

        Returns:
            Cleaned HarvestedArticle
        """
        # Clean HTML for defense-in-depth
        summary = self._clean_html(article.summary)

        # Truncate if too long
        if len(summary) > MAX_SUMMARY_LENGTH:
            summary = summary[:MAX_SUMMARY_LENGTH] + "..."

        return HarvestedArticle(
            title=article.title.strip(),
            summary=summary,
            url=article.url,
            published=article.published,
            source_name=article.source_name,
            is_tier_1=article.is_tier_1,
        )

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text.

        Defense-in-depth: tools.py also cleans HTML, but this ensures
        the harvester can handle dirty input from any source.

        Args:
            text: Text potentially containing HTML

        Returns:
            Clean plain text
        """
        if not text:
            return ""
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text(separator=" ").strip()
