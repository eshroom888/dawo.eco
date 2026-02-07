"""NewsPriorityScorer for rule-based priority scoring.

Implements rule-based scoring for news articles.
Uses tier="scan" - NO LLM calls, rule-based scoring only.

Score Ranges:
    - 8-10: High priority (regulatory + health claims/novel food)
    - 5-7: Medium priority (research, some regulatory)
    - 2-4: Standard priority (product news, competitor, general)

Boosters:
    - Recency: +0.5 for articles < 6 hours old
    - Tier-1 source: +0.5 for high-reputation sources
    - Regulatory high: +2.0 for regulatory + high priority keywords
    - Mushroom research: +1.0 for research about mushroom compounds

Usage:
    scorer = NewsPriorityScorer()
    priority = scorer.calculate_priority(article, category_result)
"""

import logging
from datetime import datetime, timedelta, timezone

from .schemas import HarvestedArticle, NewsCategory, PriorityLevel, CategoryResult, PriorityScore
from .patterns import MUSHROOM_KEYWORDS

logger = logging.getLogger(__name__)


class NewsPriorityScorer:
    """Rule-based priority scorer for news articles.

    Uses tier="scan" - NO LLM calls, rule-based scoring only.

    Score ranges map to Research Item Scorer expectations:
        - 8-10: High priority (regulatory + health claims)
        - 5-7: Medium priority (research, some regulatory)
        - 2-4: Standard priority (product news, competitor, general)
    """

    # Base scores by category
    CATEGORY_BASE_SCORES: dict[NewsCategory, float] = {
        NewsCategory.REGULATORY: 6.0,
        NewsCategory.RESEARCH: 5.0,
        NewsCategory.PRODUCT_NEWS: 4.0,
        NewsCategory.COMPETITOR: 4.0,
        NewsCategory.GENERAL: 2.0,
    }

    # Boosters
    RECENCY_BOOST = 0.5  # Article < 6 hours old
    TIER_1_SOURCE_BOOST = 0.5  # High-reputation source
    REGULATORY_HIGH_BOOST = 2.0  # Regulatory + high priority keywords
    MUSHROOM_RESEARCH_BOOST = 1.0  # Research about mushroom compounds

    # Recency threshold
    RECENCY_HOURS = 6

    def calculate_priority(
        self,
        article: HarvestedArticle,
        category_result: CategoryResult,
    ) -> PriorityScore:
        """Calculate priority score for article.

        Args:
            article: Harvested news article
            category_result: Categorization result

        Returns:
            PriorityScore with final score and boosters
        """
        base = self.CATEGORY_BASE_SCORES.get(category_result.category, 2.0)
        boosters: list[str] = []

        # Regulatory high-priority boost
        if (
            category_result.category == NewsCategory.REGULATORY
            and category_result.priority_level == PriorityLevel.HIGH
        ):
            base += self.REGULATORY_HIGH_BOOST
            boosters.append("regulatory_high_priority")

        # Recency boost
        if article.published:
            hours_old = (datetime.now(timezone.utc) - article.published).total_seconds() / 3600
            if hours_old < self.RECENCY_HOURS:
                base += self.RECENCY_BOOST
                boosters.append("recent_article")

        # Tier-1 source boost
        if article.is_tier_1:
            base += self.TIER_1_SOURCE_BOOST
            boosters.append("tier_1_source")

        # Mushroom research boost
        if category_result.category == NewsCategory.RESEARCH:
            text_lower = f"{article.title} {article.summary}".lower()
            if any(kw in text_lower for kw in MUSHROOM_KEYWORDS):
                base += self.MUSHROOM_RESEARCH_BOOST
                boosters.append("mushroom_research")

        # Cap at 10
        final = min(base, 10.0)

        return PriorityScore(
            base_score=self.CATEGORY_BASE_SCORES.get(category_result.category, 2.0),
            final_score=final,
            boosters_applied=boosters,
            requires_attention=category_result.requires_operator_attention,
        )
