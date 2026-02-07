"""PubMed Transformer - Transforms harvested articles to Research Pool format.

Implements the transformer stage of the Harvester Framework:
    Scanner -> Harvester -> FindingSummarizer -> ClaimValidator -> [Transformer] -> Validator -> Publisher

The PubMedTransformer:
    1. Takes HarvestedArticle, FindingSummary, and ClaimValidationResult
    2. Maps PubMed fields to Research Pool schema
    3. Generates tags from compound, effect, study type
    4. Builds content with abstract + summary + usage guidance
    5. Returns ValidatedResearch ready for compliance validation

Registration: team_spec.py as RegisteredService (no LLM calls)

Usage:
    # Created by Team Builder
    transformer = PubMedTransformer()

    # Execute transformation
    transformed = await transformer.transform(harvested, summaries, validations)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .schemas import (
    HarvestedArticle,
    FindingSummary,
    ClaimValidationResult,
    ValidatedResearch,
    StudyType,
    ContentPotential,
)


# Module logger
logger = logging.getLogger(__name__)

# Content length limits
MAX_CONTENT_LENGTH = 10000
MAX_SUMMARY_LENGTH = 500


class TransformerError(Exception):
    """Exception raised for transformer errors.

    Attributes:
        message: Error description
        pmid: PMID of the article that failed
    """

    def __init__(
        self,
        message: str,
        pmid: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.pmid = pmid


class PubMedTransformer:
    """PubMed Transformer - Transforms to Research Pool format.

    Uses tier="scan" (no actual LLM calls - pure data transformation).
    Maps PubMed fields to Research Pool schema.

    Features:
        - Field mapping to Research Pool schema
        - Tag generation from compound/effect/study type
        - Content assembly with abstract + summary + guidance
        - Score boosting for high-evidence studies

    No external dependencies required.

    Attributes:
        None - stateless service
    """

    async def transform(
        self,
        articles: list[HarvestedArticle],
        summaries: dict[str, FindingSummary],
        validations: dict[str, ClaimValidationResult],
    ) -> list[ValidatedResearch]:
        """Transform harvested articles to Research Pool format.

        Args:
            articles: List of HarvestedArticle
            summaries: Dict mapping PMID to FindingSummary
            validations: Dict mapping PMID to ClaimValidationResult

        Returns:
            List of ValidatedResearch ready for compliance validation
        """
        transformed: list[ValidatedResearch] = []
        failed_count = 0

        logger.info("Transforming %d articles", len(articles))

        for article in articles:
            try:
                summary = summaries.get(article.pmid)
                validation = validations.get(article.pmid)

                research = self._transform_single(article, summary, validation)
                transformed.append(research)
            except Exception as e:
                failed_count += 1
                logger.warning(
                    "Failed to transform article %s: %s",
                    article.pmid,
                    e,
                )
                continue

        logger.info(
            "Transformed %d articles (%d failed)",
            len(transformed),
            failed_count,
        )

        return transformed

    def _transform_single(
        self,
        article: HarvestedArticle,
        summary: Optional[FindingSummary],
        validation: Optional[ClaimValidationResult],
    ) -> ValidatedResearch:
        """Transform a single article to ValidatedResearch.

        Args:
            article: HarvestedArticle to transform
            summary: Optional FindingSummary
            validation: Optional ClaimValidationResult

        Returns:
            ValidatedResearch ready for compliance validation
        """
        # Generate tags
        tags = self._generate_tags(article, summary)

        # Build content
        content = self._build_content(article, summary, validation)

        # Build summary text
        summary_text = self._build_summary_text(article, summary)

        # Build source metadata
        source_metadata = self._build_metadata(article, summary, validation)

        return ValidatedResearch(
            source="pubmed",
            source_id=article.pmid,
            title=article.title[:500],  # Limit title length
            content=content[:MAX_CONTENT_LENGTH],
            summary=summary_text[:MAX_SUMMARY_LENGTH],
            url=article.pubmed_url,
            tags=tags,
            source_metadata=source_metadata,
            created_at=article.pub_date,
            compliance_status="PENDING",  # Set by validator
            score=0.0,  # Set by scorer
        )

    def _generate_tags(
        self,
        article: HarvestedArticle,
        summary: Optional[FindingSummary],
    ) -> list[str]:
        """Generate tags from article and summary.

        Args:
            article: HarvestedArticle
            summary: Optional FindingSummary

        Returns:
            List of tags for the research item
        """
        tags = []

        # Add study type tag
        study_type_tags = {
            StudyType.RCT: "rct",
            StudyType.META_ANALYSIS: "meta-analysis",
            StudyType.SYSTEMATIC_REVIEW: "systematic-review",
            StudyType.REVIEW: "review",
        }
        if article.study_type in study_type_tags:
            tags.append(study_type_tags[article.study_type])

        # Add source tag
        tags.append("pubmed")
        tags.append("scientific-research")

        # Add compound tag from summary
        if summary:
            compound_lower = summary.compound_studied.lower()
            for mushroom in ["lion's mane", "chaga", "reishi", "cordyceps", "turkey tail"]:
                if mushroom in compound_lower:
                    tags.append(mushroom.replace("'", "").replace(" ", "-"))
                    break

            # Add effect tag if it's concise
            effect_lower = summary.effect_measured.lower()
            for effect in ["cognitive", "immune", "antioxidant", "energy", "stress", "sleep"]:
                if effect in effect_lower:
                    tags.append(effect)
                    break

        # Deduplicate and limit
        return list(dict.fromkeys(tags))[:10]

    def _build_content(
        self,
        article: HarvestedArticle,
        summary: Optional[FindingSummary],
        validation: Optional[ClaimValidationResult],
    ) -> str:
        """Build content string for Research Pool.

        Args:
            article: HarvestedArticle
            summary: Optional FindingSummary
            validation: Optional ClaimValidationResult

        Returns:
            Combined content string
        """
        parts = []

        # Add abstract
        if article.abstract:
            parts.append(f"**Abstract:**\n{article.abstract}")

        # Add summary if available
        if summary:
            parts.append(f"\n\n**Key Findings:**\n{summary.key_findings}")

            if summary.statistical_significance:
                parts.append(f"\n\n**Statistical Significance:** {summary.statistical_significance}")

            parts.append(f"\n\n**Study Strength:** {summary.study_strength}")

        # Add usage guidance if available
        if validation:
            parts.append(f"\n\n**Content Potential:** {', '.join(p.value for p in validation.content_potential)}")
            parts.append(f"\n\n**Usage Guidance:**\n{validation.usage_guidance}")
            parts.append(f"\n\n**Important:** {validation.caveat}")

        return "".join(parts)

    def _build_summary_text(
        self,
        article: HarvestedArticle,
        summary: Optional[FindingSummary],
    ) -> str:
        """Build summary text for Research Pool.

        Args:
            article: HarvestedArticle
            summary: Optional FindingSummary

        Returns:
            Summary text string
        """
        if summary and summary.key_findings:
            return summary.key_findings

        # Fallback to truncated abstract
        if article.abstract:
            return article.abstract[:300] + "..."

        return "See full article for details."

    def _build_metadata(
        self,
        article: HarvestedArticle,
        summary: Optional[FindingSummary],
        validation: Optional[ClaimValidationResult],
    ) -> dict:
        """Build source metadata dictionary.

        Args:
            article: HarvestedArticle
            summary: Optional FindingSummary
            validation: Optional ClaimValidationResult

        Returns:
            Metadata dictionary
        """
        metadata = {
            "pmid": article.pmid,
            "authors": article.authors,
            "journal": article.journal,
            "study_type": article.study_type.value,
            "publication_date": article.pub_date.isoformat(),
        }

        if article.doi:
            metadata["doi"] = article.doi

        if article.sample_size:
            metadata["sample_size"] = article.sample_size

        if summary:
            metadata["compound_studied"] = summary.compound_studied
            metadata["effect_measured"] = summary.effect_measured
            metadata["study_strength"] = summary.study_strength

        if validation:
            metadata["claim_potential"] = [p.value for p in validation.content_potential]
            metadata["can_cite_study"] = validation.can_cite_study
            metadata["can_make_claim"] = validation.can_make_claim
            metadata["eu_claim_status"] = validation.eu_claim_status

        return metadata
