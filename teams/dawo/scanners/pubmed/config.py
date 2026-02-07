"""Configuration dataclasses for PubMed Scientific Research Scanner.

Provides configuration structures for:
    - EntrezConfig: NCBI Entrez E-utilities credentials
    - PubMedScannerConfig: Scanner behavior settings

Configuration is injected via constructor - NEVER loaded from files directly.
Team Builder is responsible for loading config and injecting it.

NCBI Policy Requirements:
    - Email is REQUIRED for all Entrez requests
    - API key is optional but increases rate limit (3 -> 10 req/sec)
    - Tool name should identify the application

Usage:
    # Team Builder creates config from files
    scanner_config = PubMedScannerConfig(
        email="researcher@company.com",
        api_key="optional_ncbi_key",
        search_queries=["lion's mane cognition"],
    )

    # Inject into scanner
    scanner = PubMedScanner(scanner_config, entrez_client)
"""

from dataclasses import dataclass, field


# NCBI rate limits per policy
RATE_LIMIT_NO_KEY = 3  # requests/second without API key
RATE_LIMIT_WITH_KEY = 10  # requests/second with API key

# Scanner defaults
DEFAULT_LOOKBACK_DAYS = 90  # Scientific publication cadence is slower
DEFAULT_MAX_RESULTS_PER_QUERY = 50
DEFAULT_BATCH_SIZE = 200  # NCBI efetch limit per request

# Default search queries for mushroom/adaptogen research
DEFAULT_SEARCH_QUERIES = [
    "lion's mane cognition",
    "lion's mane memory",
    "chaga antioxidant",
    "chaga immune",
    "reishi immune",
    "reishi sleep",
    "cordyceps performance",
    "cordyceps energy",
    "Hericium erinaceus",
    "Inonotus obliquus",
    "Ganoderma lucidum",
    "adaptogen stress",
    "functional mushroom supplement",
]

# Default publication type filters (high-evidence study types)
DEFAULT_PUBLICATION_TYPE_FILTERS = [
    "Randomized Controlled Trial",
    "Meta-Analysis",
    "Review",
    "Systematic Review",
]


@dataclass(frozen=True)
class EntrezConfig:
    """NCBI Entrez E-utilities configuration.

    Required by NCBI policy for all Entrez requests.

    Attributes:
        email: Contact email (REQUIRED by NCBI policy)
        api_key: NCBI API key (optional, increases rate limit)
    """

    email: str
    api_key: str | None = None

    def __post_init__(self) -> None:
        """Validate Entrez configuration."""
        if not self.email:
            raise ValueError("email is required by NCBI policy")


def _default_search_queries() -> list[str]:
    """Create default search queries list.

    Returns sensible defaults for mushroom/adaptogen research.
    Avoids mutable default argument issues.
    """
    return DEFAULT_SEARCH_QUERIES.copy()


def _default_publication_filters() -> list[str]:
    """Create default publication type filters.

    Returns high-evidence study types: RCT, Meta-Analysis, Review.
    """
    return DEFAULT_PUBLICATION_TYPE_FILTERS.copy()


@dataclass
class PubMedScannerConfig:
    """Scanner behavior configuration.

    Defines search queries, filters, and timing for PubMed research discovery.
    Loaded from config/dawo_pubmed_scanner.json by Team Builder.

    Attributes:
        email: Contact email for NCBI (REQUIRED by policy)
        api_key: Optional NCBI API key (increases rate limit)
        search_queries: Search terms for mushroom/adaptogen research
        publication_type_filters: Study types to include (RCT, Meta-Analysis, etc.)
        lookback_days: How many days back to search (default 90)
        max_results_per_query: Max results per search query
    """

    email: str
    api_key: str | None = None
    search_queries: list[str] = field(default_factory=_default_search_queries)
    publication_type_filters: list[str] = field(default_factory=_default_publication_filters)
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    max_results_per_query: int = DEFAULT_MAX_RESULTS_PER_QUERY

    def __post_init__(self) -> None:
        """Validate configuration values."""
        errors = []

        if not self.email:
            errors.append("email is required by NCBI policy")
        if self.lookback_days < 1:
            errors.append(f"lookback_days must be >= 1, got {self.lookback_days}")
        if self.max_results_per_query < 1:
            errors.append(
                f"max_results_per_query must be >= 1, got {self.max_results_per_query}"
            )

        if errors:
            raise ValueError(f"Invalid PubMedScannerConfig: {'; '.join(errors)}")

    def to_entrez_config(self) -> EntrezConfig:
        """Create EntrezConfig from scanner config.

        Returns:
            EntrezConfig with email and api_key from this config
        """
        return EntrezConfig(email=self.email, api_key=self.api_key)
