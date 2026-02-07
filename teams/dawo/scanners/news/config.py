"""Configuration dataclasses for Industry News Scanner.

Provides configuration structures for:
    - FeedSource: Individual feed configuration
    - NewsFeedClientConfig: Feed client settings (timeouts)
    - NewsScannerConfig: Scanner behavior settings

Configuration is injected via constructor - NEVER loaded from files directly.
Team Builder is responsible for loading config and injecting it.

Usage:
    # Team Builder creates config from files
    scanner_config = NewsScannerConfig(
        feeds=[
            FeedSource("NutraIngredients", "https://...", is_tier_1=True),
        ],
        keywords=["mushrooms", "supplements"],
    )

    # Inject into scanner
    scanner = NewsScanner(scanner_config, feed_client)
"""

from dataclasses import dataclass, field


# Feed client constants
DEFAULT_FETCH_TIMEOUT = 30  # seconds
DEFAULT_MAX_RETRIES = 3

# Scanner defaults
DEFAULT_HOURS_BACK = 24

# Default keywords for news filtering (synced with config/dawo_news_scanner.json)
DEFAULT_KEYWORDS = [
    "functional mushrooms",
    "adaptogens",
    "supplements industry",
    "EU regulations",
    "health claims",
    "novel food",
    "Mattilsynet",
    "lion's mane",
    "chaga",
    "reishi",
    "cordyceps",
    "mushroom extract",
    "EC 1924/2006",
    "EFSA opinion",
]

# Content limits
MAX_SUMMARY_LENGTH = 10000


@dataclass(frozen=True)
class FeedSource:
    """News feed source configuration.

    Attributes:
        name: Display name of the feed
        url: RSS/Atom feed URL
        is_tier_1: Whether this is a high-reputation source (affects scoring)
    """

    name: str
    url: str
    is_tier_1: bool = False

    def __post_init__(self) -> None:
        """Validate feed source configuration."""
        if not self.name:
            raise ValueError("Feed name is required")
        if not self.url:
            raise ValueError("Feed URL is required")


def _default_feeds() -> list[FeedSource]:
    """Create default feed sources to avoid mutable default issues.

    Returns sensible defaults matching config/dawo_news_scanner.json.
    """
    return [
        FeedSource("NutraIngredients", "https://www.nutraingredients.com/rss/news", is_tier_1=True),
        FeedSource("Nutraceuticals World", "https://www.nutraceuticalsworld.com/rss/news", is_tier_1=True),
        FeedSource("FoodNavigator", "https://www.foodnavigator.com/rss/news", is_tier_1=True),
    ]


@dataclass(frozen=True)
class NewsFeedClientConfig:
    """Feed client configuration - timeouts and retries.

    Attributes:
        fetch_timeout: Timeout for HTTP requests in seconds
        max_retries: Maximum retry attempts for failed requests
    """

    fetch_timeout: int = DEFAULT_FETCH_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES

    def __post_init__(self) -> None:
        """Validate client configuration."""
        if self.fetch_timeout < 1:
            raise ValueError(f"fetch_timeout must be >= 1, got {self.fetch_timeout}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")


@dataclass
class NewsScannerConfig:
    """Scanner behavior configuration.

    Defines feeds, keywords, and filtering criteria for news discovery.
    Loaded from config/dawo_news_scanner.json by Team Builder.

    Attributes:
        feeds: List of feed sources to monitor
        keywords: Keywords for article filtering
        competitor_brands: Brand names to flag as competitor news
        hours_back: How many hours back to search
    """

    feeds: list[FeedSource] = field(default_factory=_default_feeds)
    keywords: list[str] = field(default_factory=lambda: DEFAULT_KEYWORDS.copy())
    competitor_brands: list[str] = field(default_factory=list)
    hours_back: int = DEFAULT_HOURS_BACK

    def __post_init__(self) -> None:
        """Validate configuration values."""
        errors = []

        if not self.feeds:
            errors.append("feeds list cannot be empty")
        if self.hours_back < 1:
            errors.append(f"hours_back must be >= 1, got {self.hours_back}")

        if errors:
            raise ValueError(f"Invalid NewsScannerConfig: {'; '.join(errors)}")
