"""PubMed Harvester - Parses and enriches raw article data.

Implements the harvester stage of the Harvester Framework:
    Scanner -> [Harvester] -> FindingSummarizer -> ClaimValidator -> Transformer -> Validator -> Publisher

The PubMedHarvester:
    1. Takes RawPubMedArticle list from scanner
    2. Classifies study type from publication types
    3. Extracts sample size from abstract using regex
    4. Builds PubMed URL for each article
    5. Returns HarvestedArticle list with enriched metadata

Registration: team_spec.py as RegisteredService (no LLM calls)

Usage:
    # Created by Team Builder with injected dependencies
    harvester = PubMedHarvester()

    # Execute harvest stage
    harvested = await harvester.harvest(raw_articles)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .schemas import RawPubMedArticle, HarvestedArticle, StudyType
from .tools import extract_sample_size, classify_study_type


# Module logger
logger = logging.getLogger(__name__)

# PubMed URL template
PUBMED_URL_TEMPLATE = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


class HarvesterError(Exception):
    """Exception raised for harvester errors.

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


class PubMedHarvester:
    """PubMed Harvester - Parses and enriches raw article data.

    Uses tier="scan" (no actual LLM calls - pure data transformation).
    Classifies study type, extracts sample size, builds URLs.

    Features:
        - Study type classification from publication types
        - Sample size extraction from abstracts
        - PubMed URL generation
        - Graceful handling of missing data

    No external dependencies required.

    Attributes:
        None - stateless service
    """

    async def harvest(
        self,
        raw_articles: list[RawPubMedArticle],
    ) -> list[HarvestedArticle]:
        """Harvest raw articles into enriched HarvestedArticle objects.

        Args:
            raw_articles: List of RawPubMedArticle from scanner

        Returns:
            List of HarvestedArticle with enriched metadata
        """
        harvested: list[HarvestedArticle] = []
        failed_count = 0

        logger.info("Harvesting %d articles", len(raw_articles))

        for raw in raw_articles:
            try:
                article = self._harvest_single(raw)
                harvested.append(article)
            except Exception as e:
                failed_count += 1
                logger.warning("Failed to harvest article %s: %s", raw.pmid, e)
                continue

        logger.info(
            "Harvested %d articles (%d failed)",
            len(harvested),
            failed_count,
        )

        return harvested

    def _harvest_single(self, raw: RawPubMedArticle) -> HarvestedArticle:
        """Harvest a single raw article.

        Args:
            raw: RawPubMedArticle to harvest

        Returns:
            HarvestedArticle with enriched metadata

        Raises:
            HarvesterError: If required data is missing
        """
        # Classify study type
        study_type_str = classify_study_type(raw.publication_types)
        study_type = self._map_study_type(study_type_str)

        # Extract sample size from abstract
        sample_size = extract_sample_size(raw.abstract) if raw.abstract else None

        # Build PubMed URL
        pubmed_url = PUBMED_URL_TEMPLATE.format(pmid=raw.pmid)

        # Use publication date or default to now
        pub_date = raw.pub_date or datetime.now(timezone.utc)

        return HarvestedArticle(
            pmid=raw.pmid,
            title=raw.title,
            abstract=raw.abstract,
            authors=raw.authors[:10],  # Limit to 10 authors
            journal=raw.journal,
            pub_date=pub_date,
            doi=raw.doi,
            study_type=study_type,
            sample_size=sample_size,
            pubmed_url=pubmed_url,
        )

    def _map_study_type(self, study_type_str: str) -> StudyType:
        """Map study type string to StudyType enum.

        Args:
            study_type_str: Study type string from classify_study_type

        Returns:
            StudyType enum value
        """
        mapping = {
            "rct": StudyType.RCT,
            "meta_analysis": StudyType.META_ANALYSIS,
            "systematic_review": StudyType.SYSTEMATIC_REVIEW,
            "review": StudyType.REVIEW,
            "other": StudyType.OTHER,
        }
        return mapping.get(study_type_str, StudyType.OTHER)

    async def harvest_batch(
        self,
        raw_articles: list[RawPubMedArticle],
        batch_size: int = 50,
    ) -> list[HarvestedArticle]:
        """Harvest articles in batches (for logging/monitoring).

        Args:
            raw_articles: List of RawPubMedArticle
            batch_size: Number of articles per batch

        Returns:
            List of HarvestedArticle
        """
        all_harvested: list[HarvestedArticle] = []

        for i in range(0, len(raw_articles), batch_size):
            batch = raw_articles[i : i + batch_size]
            logger.debug("Harvesting batch %d-%d", i, i + len(batch))

            harvested = await self.harvest(batch)
            all_harvested.extend(harvested)

        return all_harvested
