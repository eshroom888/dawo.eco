"""PubMed Scanner Agent - Main agent for scientific research discovery.

Implements the scanner stage of the Harvester Framework:
    [Scanner] -> Harvester -> FindingSummarizer -> ClaimValidator -> Transformer -> Validator -> Publisher

The PubMedScanner:
    1. Executes configured search queries against PubMed
    2. Filters by publication type (RCT, Meta-Analysis, Review)
    3. Filters by publication date (default: last 90 days)
    4. Deduplicates results by PMID
    5. Returns list of RawPubMedArticle for harvesting

Registration: team_spec.py with tier="scan" (no actual LLM calls in scan stage)

Usage:
    # Created by Team Builder with injected dependencies
    scanner = PubMedScanner(config, pubmed_client)

    # Execute scan stage
    result = await scanner.scan()
"""

import logging
from typing import Any, Optional

from .config import PubMedScannerConfig
from .schemas import RawPubMedArticle, ScanResult, ScanStatistics
from .tools import PubMedClient, PubMedSearchError


# Module logger
logger = logging.getLogger(__name__)


class PubMedScanError(Exception):
    """Exception raised for PubMed scanner errors.

    Attributes:
        message: Error description
        partial_results: Any results collected before failure
    """

    def __init__(
        self,
        message: str,
        partial_results: Optional[list[RawPubMedArticle]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.partial_results = partial_results or []


class PubMedScanner:
    """PubMed Scanner Agent for scientific research discovery.

    Uses tier="scan" (no actual LLM calls - just API queries).
    Executes configured searches against PubMed via Entrez API.

    Features:
        - Multiple configurable search queries
        - Publication type filtering (RCT, Meta-Analysis, Review)
        - Date filtering (default: last 90 days)
        - PMID deduplication across queries
        - Statistics tracking for monitoring

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _config: Scanner configuration
        _client: PubMed Entrez client
    """

    def __init__(
        self,
        config: PubMedScannerConfig,
        client: PubMedClient,
    ):
        """Initialize scanner with injected dependencies.

        Args:
            config: Scanner configuration with queries and filters
            client: PubMed client for Entrez API access
        """
        self._config = config
        self._client = client

    async def scan(self) -> ScanResult:
        """Execute scan stage: search PubMed for relevant articles.

        Executes all configured search queries, applies filters,
        and deduplicates results by PMID.

        Returns:
            ScanResult with RawPubMedArticle list and statistics

        Raises:
            PubMedScanError: If all queries fail
        """
        all_pmids: set[str] = set()
        total_found = 0
        queries_executed = 0
        queries_failed = 0
        errors: list[str] = []

        logger.info(
            "Starting PubMed scan with %d queries, lookback=%d days",
            len(self._config.search_queries),
            self._config.lookback_days,
        )

        # Execute each search query
        for query in self._config.search_queries:
            try:
                pmids = await self._client.search(
                    query=query,
                    max_results=self._config.max_results_per_query,
                    date_filter=self._config.lookback_days,
                    publication_types=self._config.publication_type_filters,
                )
                queries_executed += 1
                total_found += len(pmids)
                all_pmids.update(pmids)

                logger.debug(
                    "Query '%s' returned %d PMIDs (%d unique total)",
                    query,
                    len(pmids),
                    len(all_pmids),
                )

            except PubMedSearchError as e:
                queries_failed += 1
                errors.append(f"Query '{query}' failed: {e.message}")
                logger.warning("Query '%s' failed: %s", query, e.message)
                continue

        # Check if all queries failed
        if queries_failed == len(self._config.search_queries):
            raise PubMedScanError(
                f"All {queries_failed} queries failed",
                partial_results=[],
            )

        # Fetch article details for all unique PMIDs
        articles = await self._fetch_article_details(list(all_pmids))

        statistics = ScanStatistics(
            queries_executed=queries_executed,
            total_pmids_found=total_found,
            pmids_after_dedup=len(all_pmids),
            queries_failed=queries_failed,
        )

        logger.info(
            "PubMed scan complete: %d queries, %d total PMIDs, %d unique, %d articles",
            queries_executed,
            total_found,
            len(all_pmids),
            len(articles),
        )

        return ScanResult(
            articles=articles,
            statistics=statistics,
            errors=errors,
        )

    async def _fetch_article_details(
        self,
        pmids: list[str],
    ) -> list[RawPubMedArticle]:
        """Fetch article details and convert to RawPubMedArticle.

        Args:
            pmids: List of PMIDs to fetch

        Returns:
            List of RawPubMedArticle objects
        """
        if not pmids:
            return []

        try:
            raw_articles = await self._client.fetch_details(pmids)

            articles = []
            for article_data in raw_articles:
                article = RawPubMedArticle(
                    pmid=article_data["pmid"],
                    title=article_data["title"],
                    abstract=article_data.get("abstract", ""),
                    authors=article_data.get("authors", []),
                    journal=article_data.get("journal", ""),
                    pub_date=article_data.get("pub_date"),
                    doi=article_data.get("doi"),
                    publication_types=article_data.get("publication_types", []),
                )
                articles.append(article)

            return articles

        except Exception as e:
            logger.error("Failed to fetch article details: %s", e)
            return []

    async def scan_single_query(self, query: str) -> ScanResult:
        """Execute a single search query (for testing/debugging).

        Args:
            query: Search query to execute

        Returns:
            ScanResult for the single query
        """
        try:
            pmids = await self._client.search(
                query=query,
                max_results=self._config.max_results_per_query,
                date_filter=self._config.lookback_days,
                publication_types=self._config.publication_type_filters,
            )

            articles = await self._fetch_article_details(pmids)

            return ScanResult(
                articles=articles,
                statistics=ScanStatistics(
                    queries_executed=1,
                    total_pmids_found=len(pmids),
                    pmids_after_dedup=len(pmids),
                    queries_failed=0,
                ),
                errors=[],
            )

        except PubMedSearchError as e:
            return ScanResult(
                articles=[],
                statistics=ScanStatistics(
                    queries_executed=1,
                    total_pmids_found=0,
                    pmids_after_dedup=0,
                    queries_failed=1,
                ),
                errors=[f"Query '{query}' failed: {e.message}"],
            )
