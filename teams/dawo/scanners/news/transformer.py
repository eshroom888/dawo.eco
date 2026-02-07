"""NewsTransformer for transforming articles to Research Pool format.

Implements the transformer stage of the Harvester Framework for news.
Maps news fields to Research Pool schema.

Usage:
    transformer = NewsTransformer(categorizer, priority_scorer)
    transformed = transformer.transform(harvested_articles)
"""

import logging
from datetime import datetime, timezone
from typing import Protocol

from .schemas import (
    HarvestedArticle,
    ValidatedResearch,
    CategoryResult,
    PriorityScore,
)
from .config import MAX_SUMMARY_LENGTH

logger = logging.getLogger(__name__)


class TransformerError(Exception):
    """Raised when transformation fails."""

    pass


class CategorizerProtocol(Protocol):
    """Protocol for categorizer dependency injection."""

    def categorize(self, article: HarvestedArticle) -> CategoryResult:
        ...


class PriorityScorerProtocol(Protocol):
    """Protocol for priority scorer dependency injection."""

    def calculate_priority(
        self,
        article: HarvestedArticle,
        category_result: CategoryResult,
    ) -> PriorityScore:
        ...


class NewsTransformer:
    """Transformer for news articles.

    Accepts NewsCategorizer and NewsPriorityScorer via dependency injection.
    Maps news fields to Research Pool schema.

    Attributes:
        _categorizer: News categorizer for classification
        _scorer: Priority scorer for scoring
    """

    def __init__(
        self,
        categorizer: CategorizerProtocol,
        priority_scorer: PriorityScorerProtocol,
    ) -> None:
        """Initialize transformer.

        Args:
            categorizer: News categorizer
            priority_scorer: Priority scorer
        """
        self._categorizer = categorizer
        self._scorer = priority_scorer

    def transform(
        self,
        articles: list[HarvestedArticle],
    ) -> list[tuple[ValidatedResearch, CategoryResult, PriorityScore]]:
        """Transform harvested articles to Research Pool format.

        Args:
            articles: Harvested news articles

        Returns:
            List of (ValidatedResearch, CategoryResult, PriorityScore) tuples
        """
        transformed: list[tuple[ValidatedResearch, CategoryResult, PriorityScore]] = []
        errors_count = 0

        for article in articles:
            try:
                result = self._transform_article(article)
                transformed.append(result)
            except Exception as e:
                errors_count += 1
                logger.warning("Failed to transform article %s: %s", article.url, e)

        logger.info(
            "Transformed %d articles, %d failed",
            len(transformed),
            errors_count,
        )
        return transformed

    def _transform_article(
        self,
        article: HarvestedArticle,
    ) -> tuple[ValidatedResearch, CategoryResult, PriorityScore]:
        """Transform a single article.

        Args:
            article: Harvested article to transform

        Returns:
            Tuple of (ValidatedResearch, CategoryResult, PriorityScore)
        """
        # Categorize
        category_result = self._categorizer.categorize(article)

        # Calculate priority score
        priority_score = self._scorer.calculate_priority(article, category_result)

        # Generate tags from category + keywords
        tags = self._generate_tags(article, category_result)

        # Build content with category context
        content = self._build_content(article, category_result)

        # Truncate if needed
        if len(content) > MAX_SUMMARY_LENGTH:
            content = content[:MAX_SUMMARY_LENGTH] + "..."

        # Build source metadata
        source_metadata = {
            "source_name": article.source_name,
            "is_tier_1": article.is_tier_1,
            "category": category_result.category.value,
            "is_regulatory": category_result.is_regulatory,
            "priority_level": category_result.priority_level.value,
            "requires_attention": category_result.requires_operator_attention,
            "matched_patterns": category_result.matched_patterns,
            "boosters_applied": priority_score.boosters_applied,
        }

        research = ValidatedResearch(
            source="news",
            title=article.title[:500],  # Truncate title if needed
            content=content,
            url=article.url,
            tags=tags,
            source_metadata=source_metadata,
            created_at=article.published or datetime.now(timezone.utc),
            compliance_status="PENDING",  # Set by validator
            score=priority_score.final_score,
        )

        return research, category_result, priority_score

    def _generate_tags(
        self,
        article: HarvestedArticle,
        category_result: CategoryResult,
    ) -> list[str]:
        """Generate tags for article.

        Args:
            article: Source article
            category_result: Categorization result

        Returns:
            List of tag strings
        """
        tags = [
            "news",
            category_result.category.value,
            article.source_name.lower().replace(" ", "_"),
        ]

        if category_result.is_regulatory:
            tags.append("regulatory")
        if category_result.requires_operator_attention:
            tags.append("attention_required")
        if article.is_tier_1:
            tags.append("tier_1_source")

        return tags

    def _build_content(
        self,
        article: HarvestedArticle,
        category_result: CategoryResult,
    ) -> str:
        """Build content string for Research Pool.

        Args:
            article: Source article
            category_result: Categorization result

        Returns:
            Formatted content string
        """
        parts = [article.summary]

        if category_result.is_regulatory:
            parts.append(
                f"\n\n[REGULATORY] Category: {category_result.category.value}, "
                f"Priority: {category_result.priority_level.value}"
            )
            if category_result.requires_operator_attention:
                parts.append("[REQUIRES ATTENTION]")

        return "".join(parts)
