"""Finding Summarizer - LLM-powered scientific finding summarization.

Implements the summarization stage of the Harvester Framework:
    Scanner -> Harvester -> [FindingSummarizer] -> ClaimValidator -> Transformer -> Validator -> Publisher

The FindingSummarizer:
    1. Takes HarvestedArticle with abstract
    2. Uses LLM (tier="generate") to analyze abstract
    3. Extracts compound studied, effect measured, key findings
    4. Flags content potential for marketing use
    5. Returns FindingSummary with plain-language summary

Registration: team_spec.py with tier="generate" (maps to Sonnet at runtime)

Usage:
    # Created by Team Builder with injected LLM client
    summarizer = FindingSummarizer(llm_client)

    # Execute summarization
    summary = await summarizer.summarize(harvested_article)
"""

import json
import logging
from typing import Any, Optional

from .schemas import HarvestedArticle, FindingSummary
from .prompts import FINDING_SUMMARIZATION_PROMPT


# Module logger
logger = logging.getLogger(__name__)


class SummarizationError(Exception):
    """Exception raised for summarization errors.

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


class FindingSummarizer:
    """LLM-powered scientific finding summarizer.

    Uses tier="generate" (Sonnet) for quality scientific summarization.
    Creates plain-language summaries suitable for content inspiration.

    Features:
        - Compound and effect extraction
        - Statistical significance detection
        - Study strength assessment
        - Content potential tagging
        - Standard caveat inclusion

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _llm: LLM client configured for tier="generate"
    """

    def __init__(self, llm_client: Any):
        """Initialize finding summarizer with injected LLM client.

        Args:
            llm_client: LLM client configured for tier="generate"
        """
        self._llm = llm_client

    async def summarize(
        self,
        article: HarvestedArticle,
    ) -> FindingSummary:
        """Generate plain-language summary of research finding.

        Args:
            article: HarvestedArticle with abstract to summarize

        Returns:
            FindingSummary with extracted information

        Raises:
            SummarizationError: If summarization fails
        """
        if not article.abstract or not article.abstract.strip():
            # Return default summary for articles without abstracts
            return self._default_summary(article)

        # Format prompt
        prompt = FINDING_SUMMARIZATION_PROMPT.format(
            title=article.title,
            study_type=article.study_type.value,
            abstract=article.abstract[:4000],  # Truncate very long abstracts
        )

        try:
            # Call LLM
            response = await self._llm.generate(
                prompt=prompt,
                max_tokens=800,
            )

            # Parse response
            return self._parse_response(response, article)

        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse LLM response as JSON for %s: %s",
                article.pmid,
                e,
            )
            return self._default_summary(article)
        except Exception as e:
            logger.error(
                "Summarization failed for %s: %s",
                article.pmid,
                e,
            )
            raise SummarizationError(
                f"Failed to summarize: {e}",
                pmid=article.pmid,
            ) from e

    async def summarize_batch(
        self,
        articles: list[HarvestedArticle],
    ) -> dict[str, FindingSummary]:
        """Summarize multiple articles.

        Args:
            articles: List of HarvestedArticle

        Returns:
            Dict mapping PMID to FindingSummary
        """
        results: dict[str, FindingSummary] = {}

        for article in articles:
            try:
                summary = await self.summarize(article)
                results[article.pmid] = summary
            except SummarizationError as e:
                logger.warning("Summarization failed for %s: %s", article.pmid, e)
                results[article.pmid] = self._default_summary(article)

        return results

    def _parse_response(
        self,
        response: str,
        article: HarvestedArticle,
    ) -> FindingSummary:
        """Parse LLM response into FindingSummary.

        Args:
            response: Raw LLM response text
            article: Original article for fallback values

        Returns:
            FindingSummary parsed from response
        """
        # Handle potential markdown code blocks
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            text = "\n".join(lines[1:-1])

        data = json.loads(text)

        return FindingSummary(
            compound_studied=data.get("compound_studied", "Unknown compound"),
            effect_measured=data.get("effect_measured", "Unknown effect"),
            key_findings=data.get("key_findings", article.abstract[:200] + "..."),
            statistical_significance=data.get("statistical_significance"),
            study_strength=data.get("study_strength", "weak"),
            content_potential=data.get("content_potential", ["educational"]),
            caveat=data.get(
                "caveat",
                "Research finding - not an approved health claim. "
                "Can cite study but cannot claim treatment/prevention/cure.",
            ),
        )

    def _default_summary(self, article: HarvestedArticle) -> FindingSummary:
        """Create default FindingSummary for failed summarizations.

        Args:
            article: Original article

        Returns:
            Default FindingSummary with basic information
        """
        # Extract compound from title if possible
        compound = "Functional mushroom compound"
        for mushroom in ["lion's mane", "chaga", "reishi", "cordyceps"]:
            if mushroom in article.title.lower():
                compound = mushroom.title()
                break

        return FindingSummary(
            compound_studied=compound,
            effect_measured="See abstract for details",
            key_findings=article.abstract[:300] + "..." if article.abstract else "No abstract available",
            statistical_significance=None,
            study_strength="unknown",
            content_potential=["educational"],
            caveat=(
                "Research finding - not an approved health claim. "
                "Can cite study but cannot claim treatment/prevention/cure."
            ),
        )
