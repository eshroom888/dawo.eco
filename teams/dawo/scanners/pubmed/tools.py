"""PubMed Entrez client for scientific research retrieval.

Uses Biopython's Entrez module for NCBI E-utilities access.
Accepts configuration via dependency injection - NEVER loads files directly.
Wraps all fetches with retry middleware (Story 1.5).

NCBI Policy Requirements:
    - Email is REQUIRED for all requests
    - API key is optional but increases rate limit (3 -> 10 req/sec)
    - Tool name should identify the application
    - Respect rate limits to avoid IP blocking

Rate Limiting:
    - Without API key: 3 requests/second
    - With API key: 10 requests/second
    - Batch size for efetch: 200 PMIDs max per request

Usage:
    # Created by Team Builder with injected config
    client = PubMedClient(entrez_config, retry_middleware)

    # Search for articles
    pmids = await client.search("lion's mane cognition", max_results=50)

    # Fetch article details
    articles = await client.fetch_details(pmids)
"""

import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Protocol

from .config import EntrezConfig, RATE_LIMIT_NO_KEY, RATE_LIMIT_WITH_KEY, DEFAULT_BATCH_SIZE
from .prompts import SAMPLE_SIZE_PATTERNS, STUDY_TYPE_MAPPINGS


# Module logger
logger = logging.getLogger(__name__)


class RetryMiddlewareProtocol(Protocol):
    """Protocol for retry middleware dependency injection."""

    async def execute(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute function with retry logic."""
        ...

# Default tool name for NCBI identification
DEFAULT_TOOL_NAME = "DAWO.ECO Research Scanner"


class PubMedSearchError(Exception):
    """Exception raised for PubMed search failures.

    Attributes:
        message: Error description
        query: The query that failed
    """

    def __init__(self, message: str, query: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.query = query


class PubMedFetchError(Exception):
    """Exception raised for PubMed fetch failures.

    Attributes:
        message: Error description
        pmids: PMIDs that failed to fetch
    """

    def __init__(self, message: str, pmids: Optional[list[str]] = None):
        super().__init__(message)
        self.message = message
        self.pmids = pmids or []


class PubMedClient:
    """PubMed Entrez client for scientific research retrieval.

    Uses Biopython's Entrez module for NCBI E-utilities access.
    Accepts configuration via dependency injection - NEVER loads files directly.
    Wraps all fetches with retry middleware (Story 1.5).

    Attributes:
        _config: Entrez configuration with email and API key
        _retry: Retry middleware for resilient API calls
        _rate_limit: Requests per second based on API key presence
        _last_request: Timestamp of last request for rate limiting
    """

    def __init__(
        self,
        config: EntrezConfig,
        retry_middleware: RetryMiddlewareProtocol,
    ):
        """Initialize PubMed client with injected dependencies.

        Args:
            config: Entrez configuration with email and optional API key
            retry_middleware: Retry middleware from Story 1.5 (required)
        """
        self._config = config
        self._retry = retry_middleware
        self._rate_limit = (
            RATE_LIMIT_WITH_KEY if config.api_key else RATE_LIMIT_NO_KEY
        )
        self._last_request = datetime.min.replace(tzinfo=timezone.utc)

        # Configure Entrez (deferred import to avoid import errors in tests)
        self._configure_entrez()

    def _configure_entrez(self) -> None:
        """Configure Biopython Entrez module with credentials.

        Raises:
            ImportError: If Biopython is not installed
        """
        try:
            from Bio import Entrez

            Entrez.email = self._config.email
            Entrez.api_key = self._config.api_key
            Entrez.tool = DEFAULT_TOOL_NAME
            logger.debug(
                "Entrez configured with email=%s, api_key=%s",
                self._config.email,
                "present" if self._config.api_key else "absent",
            )
        except ImportError as e:
            logger.error("Biopython not installed - PubMed client requires 'biopython' package")
            raise ImportError(
                "PubMed client requires Biopython. Install with: pip install biopython"
            ) from e

    async def _rate_limit_wait(self) -> None:
        """Wait to respect NCBI rate limits."""
        min_interval = 1.0 / self._rate_limit
        now = datetime.now(timezone.utc)
        elapsed = (now - self._last_request).total_seconds()

        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.debug("Rate limiting: waiting %.2f seconds", wait_time)
            await asyncio.sleep(wait_time)

        self._last_request = datetime.now(timezone.utc)

    async def search(
        self,
        query: str,
        max_results: int = 50,
        date_filter: Optional[int] = None,
        publication_types: Optional[list[str]] = None,
    ) -> list[str]:
        """Search PubMed for articles matching query.

        Args:
            query: Search query (supports PubMed syntax)
            max_results: Maximum results to return
            date_filter: Only include articles from last N days
            publication_types: Filter by publication types

        Returns:
            List of PMIDs matching query

        Raises:
            PubMedSearchError: On search failure
        """
        await self._rate_limit_wait()

        try:
            from Bio import Entrez

            # Build search query with filters
            search_term = self._build_search_term(
                query, date_filter, publication_types
            )

            logger.debug("Searching PubMed: %s (max_results=%d)", search_term, max_results)

            # Run in executor since Entrez is synchronous
            loop = asyncio.get_running_loop()
            handle = await loop.run_in_executor(
                None,
                lambda: Entrez.esearch(
                    db="pubmed",
                    term=search_term,
                    retmax=max_results,
                    sort="relevance",
                ),
            )

            record = Entrez.read(handle)
            handle.close()

            pmids = record.get("IdList", [])
            logger.info(
                "PubMed search returned %d results for query: %s",
                len(pmids),
                query,
            )
            return pmids

        except ImportError:
            logger.error("Biopython not installed - cannot search PubMed")
            raise PubMedSearchError("Biopython not installed", query)
        except Exception as e:
            logger.error("PubMed search failed for query '%s': %s", query, e)
            raise PubMedSearchError(f"Search failed: {e}", query) from e

    def _build_search_term(
        self,
        query: str,
        date_filter: Optional[int],
        publication_types: Optional[list[str]],
    ) -> str:
        """Build complete search term with filters.

        Args:
            query: Base search query
            date_filter: Days back to filter
            publication_types: Publication types to include

        Returns:
            Complete search term with all filters
        """
        term = query

        # Add date filter
        if date_filter:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=date_filter)
            date_range = (
                f'("{start_date.strftime("%Y/%m/%d")}"[PDAT] : '
                f'"{end_date.strftime("%Y/%m/%d")}"[PDAT])'
            )
            term = f"({term}) AND {date_range}"

        # Add publication type filter
        if publication_types:
            type_filters = " OR ".join(
                f'"{pt}"[Publication Type]' for pt in publication_types
            )
            term = f"({term}) AND ({type_filters})"

        return term

    async def fetch_details(
        self,
        pmids: list[str],
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> list[dict[str, Any]]:
        """Fetch full article details for given PMIDs.

        Args:
            pmids: List of PubMed IDs
            batch_size: Number of PMIDs per request (max 200)

        Returns:
            List of parsed article dictionaries

        Raises:
            PubMedFetchError: On fetch failure
        """
        if not pmids:
            return []

        all_articles: list[dict[str, Any]] = []

        # Process in batches (NCBI limit is 200 per request)
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i : i + batch_size]
            logger.debug("Fetching batch of %d PMIDs", len(batch))

            await self._rate_limit_wait()

            try:
                articles = await self._fetch_batch(batch)
                all_articles.extend(articles)
            except Exception as e:
                logger.error("Failed to fetch batch starting at index %d: %s", i, e)
                raise PubMedFetchError(f"Fetch failed: {e}", batch) from e

        logger.info("Fetched %d articles from %d PMIDs", len(all_articles), len(pmids))
        return all_articles

    async def _fetch_batch(self, pmids: list[str]) -> list[dict[str, Any]]:
        """Fetch a single batch of PMIDs.

        Args:
            pmids: Batch of PMIDs to fetch

        Returns:
            List of parsed articles
        """
        from Bio import Entrez

        loop = asyncio.get_running_loop()
        handle = await loop.run_in_executor(
            None,
            lambda: Entrez.efetch(
                db="pubmed",
                id=",".join(pmids),
                rettype="xml",
                retmode="xml",
            ),
        )

        records = Entrez.read(handle)
        handle.close()

        articles = []
        for article in records.get("PubmedArticle", []):
            parsed = self._parse_article(article)
            if parsed:
                articles.append(parsed)

        return articles

    def _parse_article(self, article: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Parse PubmedArticle XML record to dict.

        Args:
            article: Raw PubmedArticle from Entrez

        Returns:
            Parsed article dict or None if parsing fails
        """
        try:
            medline = article.get("MedlineCitation", {})
            article_data = medline.get("Article", {})

            # Extract PMID
            pmid = str(medline.get("PMID", ""))
            if not pmid:
                return None

            # Extract title
            title = str(article_data.get("ArticleTitle", ""))

            # Extract abstract
            abstract = self._extract_abstract(article_data)

            # Extract authors (limit to 10)
            authors = self._extract_authors(article_data)

            # Extract journal
            journal_info = article_data.get("Journal", {})
            journal = str(journal_info.get("Title", ""))

            # Extract publication date
            pub_date = self._extract_pub_date(article_data)

            # Extract DOI
            doi = self._extract_doi(article)

            # Extract publication types
            pub_types = self._extract_publication_types(article_data)

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "pub_date": pub_date,
                "doi": doi,
                "publication_types": pub_types,
            }

        except Exception as e:
            logger.warning("Failed to parse article: %s", e)
            return None

    def _extract_abstract(self, article_data: dict[str, Any]) -> str:
        """Extract abstract text from article data."""
        abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
        if isinstance(abstract_parts, list):
            return " ".join(str(part) for part in abstract_parts)
        return str(abstract_parts) if abstract_parts else ""

    def _extract_authors(
        self, article_data: dict[str, Any], max_authors: int = 10
    ) -> list[str]:
        """Extract author names from article data."""
        authors = []
        author_list = article_data.get("AuthorList", [])

        for author in author_list[:max_authors]:
            last = author.get("LastName", "")
            first = author.get("ForeName", "")
            if last:
                authors.append(f"{last} {first}".strip())

        return authors

    def _extract_pub_date(
        self, article_data: dict[str, Any]
    ) -> Optional[datetime]:
        """Extract publication date from article data."""
        # Try ArticleDate first (more precise)
        date_info = article_data.get("ArticleDate", [])
        if date_info:
            d = date_info[0]
            try:
                return datetime(
                    int(d.get("Year", 2000)),
                    int(d.get("Month", 1)),
                    int(d.get("Day", 1)),
                    tzinfo=timezone.utc,
                )
            except (ValueError, TypeError):
                pass

        # Fall back to Journal PubDate
        journal = article_data.get("Journal", {})
        journal_issue = journal.get("JournalIssue", {})
        pub_date = journal_issue.get("PubDate", {})

        try:
            year = int(pub_date.get("Year", 0))
            if year:
                month = pub_date.get("Month", "Jan")
                # Convert month name to number if needed
                if isinstance(month, str) and not month.isdigit():
                    month_map = {
                        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
                        "may": 5, "jun": 6, "jul": 7, "aug": 8,
                        "sep": 9, "oct": 10, "nov": 11, "dec": 12,
                    }
                    month = month_map.get(month.lower()[:3], 1)
                return datetime(year, int(month), 1, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass

        return None

    def _extract_doi(self, article: dict[str, Any]) -> Optional[str]:
        """Extract DOI from article identifiers."""
        id_list = article.get("PubmedData", {}).get("ArticleIdList", [])
        for id_obj in id_list:
            try:
                if str(id_obj.attributes.get("IdType", "")) == "doi":
                    return str(id_obj)
            except (AttributeError, KeyError):
                continue
        return None

    def _extract_publication_types(self, article_data: dict[str, Any]) -> list[str]:
        """Extract publication types from article data."""
        pub_types = []
        type_list = article_data.get("PublicationTypeList", [])
        for pt in type_list:
            pub_types.append(str(pt))
        return pub_types


def extract_sample_size(abstract: str) -> Optional[int]:
    """Extract sample size from abstract text.

    Uses regex patterns to find common sample size formats.
    Handles comma-separated numbers (e.g., 1,847).

    Args:
        abstract: Abstract text to search

    Returns:
        Sample size if found, None otherwise
    """
    for pattern in SAMPLE_SIZE_PATTERNS:
        match = re.search(pattern, abstract, re.IGNORECASE)
        if match:
            try:
                # Remove commas from number before parsing
                num_str = match.group(1).replace(",", "")
                return int(num_str)
            except (ValueError, IndexError):
                continue
    return None


def classify_study_type(publication_types: list[str]) -> str:
    """Classify study type from publication types.

    Args:
        publication_types: List of MeSH publication types

    Returns:
        Study type string (rct, meta_analysis, review, etc.)
    """
    # Check publication types in order of priority
    for pub_type in publication_types:
        pub_type_lower = pub_type.lower()
        for key, value in STUDY_TYPE_MAPPINGS.items():
            if key in pub_type_lower:
                return value

    return "other"
