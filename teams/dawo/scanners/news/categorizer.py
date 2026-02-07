"""NewsCategorizer for rule-based news categorization.

Implements rule-based categorization for news articles.
Uses tier="scan" - NO LLM calls, pure pattern matching.

Categories:
    - REGULATORY: EU, FDA, Mattilsynet, compliance
    - RESEARCH: Studies, clinical trials
    - PRODUCT_NEWS: Launches, announcements
    - COMPETITOR: Competitor brand mentions
    - GENERAL: Other industry news

Usage:
    categorizer = NewsCategorizer(competitor_brands=["Brand1"])
    result = categorizer.categorize(article)
"""

import logging
import re
from typing import Optional

from .schemas import HarvestedArticle, NewsCategory, PriorityLevel, CategoryResult
from .patterns import (
    REGULATORY_PATTERNS,
    HIGH_PRIORITY_KEYWORDS,
    RESEARCH_PATTERNS,
    PRODUCT_NEWS_PATTERNS,
)

logger = logging.getLogger(__name__)


class NewsCategorizer:
    """Rule-based news article categorizer.

    Uses tier="scan" - NO LLM calls, pattern matching only.
    Classifies articles into categories based on keyword patterns.

    Attributes:
        _competitor_patterns: Compiled patterns for competitor detection
    """

    def __init__(self, competitor_brands: Optional[list[str]] = None) -> None:
        """Initialize categorizer.

        Args:
            competitor_brands: List of competitor brand names to detect
        """
        self._competitor_patterns: list[re.Pattern[str]] = []
        if competitor_brands:
            for brand in competitor_brands:
                self._competitor_patterns.append(
                    re.compile(rf"\b{re.escape(brand)}\b", re.IGNORECASE)
                )

    def categorize(self, article: HarvestedArticle) -> CategoryResult:
        """Categorize a news article using pattern matching.

        Args:
            article: Harvested news article

        Returns:
            CategoryResult with category, priority, and flags
        """
        text = f"{article.title} {article.summary}"
        text_lower = text.lower()
        matched_patterns: list[str] = []

        # Check regulatory (highest priority)
        is_regulatory = False
        for pattern in REGULATORY_PATTERNS:
            if pattern.search(text):
                is_regulatory = True
                matched_patterns.append(pattern.pattern)

        if is_regulatory:
            # Check for high-priority regulatory keywords
            is_high_priority = any(kw in text_lower for kw in HIGH_PRIORITY_KEYWORDS)
            return CategoryResult(
                category=NewsCategory.REGULATORY,
                confidence=0.9 if len(matched_patterns) > 1 else 0.7,
                is_regulatory=True,
                priority_level=PriorityLevel.HIGH if is_high_priority else PriorityLevel.MEDIUM,
                matched_patterns=matched_patterns,
                requires_operator_attention=is_high_priority,
            )

        # Check research
        matched_patterns = []
        for pattern in RESEARCH_PATTERNS:
            if pattern.search(text):
                matched_patterns.append(pattern.pattern)
        if matched_patterns:
            return CategoryResult(
                category=NewsCategory.RESEARCH,
                confidence=0.8 if len(matched_patterns) > 1 else 0.6,
                is_regulatory=False,
                priority_level=PriorityLevel.LOW,
                matched_patterns=matched_patterns,
                requires_operator_attention=False,
            )

        # Check competitor
        matched_patterns = []
        for pattern in self._competitor_patterns:
            if pattern.search(text):
                matched_patterns.append(pattern.pattern)
        if matched_patterns:
            return CategoryResult(
                category=NewsCategory.COMPETITOR,
                confidence=0.9,
                is_regulatory=False,
                priority_level=PriorityLevel.LOW,
                matched_patterns=matched_patterns,
                requires_operator_attention=False,
            )

        # Check product news
        matched_patterns = []
        for pattern in PRODUCT_NEWS_PATTERNS:
            if pattern.search(text):
                matched_patterns.append(pattern.pattern)
        if matched_patterns:
            return CategoryResult(
                category=NewsCategory.PRODUCT_NEWS,
                confidence=0.7,
                is_regulatory=False,
                priority_level=PriorityLevel.LOW,
                matched_patterns=matched_patterns,
                requires_operator_attention=False,
            )

        # Default: general
        return CategoryResult(
            category=NewsCategory.GENERAL,
            confidence=0.5,
            is_regulatory=False,
            priority_level=PriorityLevel.LOW,
            matched_patterns=[],
            requires_operator_attention=False,
        )
