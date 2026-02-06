"""Configuration dataclasses for Reddit Research Scanner.

Provides configuration structures for:
    - RedditClientConfig: API credentials for Reddit OAuth2
    - RedditScannerConfig: Scanner behavior settings

Configuration is injected via constructor - NEVER loaded from files directly.
Team Builder is responsible for loading config and injecting it.

Usage:
    # Team Builder creates config from environment/files
    client_config = RedditClientConfig(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        ...
    )

    # Inject into client
    client = RedditClient(client_config)
"""

from dataclasses import dataclass, field


# Constants for scanner configuration
DEFAULT_MIN_UPVOTES = 10
DEFAULT_TIME_FILTER = "day"
DEFAULT_MAX_POSTS_PER_SUBREDDIT = 100
DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE = 60
DEFAULT_USER_AGENT = "DAWO.ECO/1.0.0 (by /u/dawo_bot)"

# Default subreddits for mushroom/wellness research
DEFAULT_SUBREDDITS = [
    "Nootropics",
    "Supplements",
    "MushroomSupplements",
    "Biohackers",
]

# Default keywords for mushroom products
DEFAULT_KEYWORDS = [
    "lion's mane",
    "lions mane",
    "chaga",
    "reishi",
    "cordyceps",
    "shiitake",
    "maitake",
]

# Content limits
MAX_CONTENT_LENGTH = 10000


@dataclass(frozen=True)
class RedditClientConfig:
    """Reddit API credentials configuration.

    Used for OAuth2 authentication with Reddit API.
    All credentials must be provided - loaded from environment variables.

    NEVER hardcode credentials in code.

    Attributes:
        client_id: Reddit OAuth2 client ID
        client_secret: Reddit OAuth2 client secret
        username: Reddit account username
        password: Reddit account password
        user_agent: User-Agent header (must identify app)

    Raises:
        ValueError: If any required credential is empty
    """

    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str = DEFAULT_USER_AGENT

    def __post_init__(self) -> None:
        """Validate that all required credentials are provided."""
        errors = []

        if not self.client_id:
            errors.append("client_id is required")
        if not self.client_secret:
            errors.append("client_secret is required")
        if not self.username:
            errors.append("username is required")
        if not self.password:
            errors.append("password is required")
        if not self.user_agent:
            errors.append("user_agent is required")

        if errors:
            raise ValueError(f"Invalid RedditClientConfig: {'; '.join(errors)}")


@dataclass
class RedditScannerConfig:
    """Scanner behavior configuration.

    Defines which subreddits to scan, keywords to search for,
    and filtering criteria for collected posts.

    Loaded from config/dawo_reddit_scanner.json by Team Builder.

    Attributes:
        subreddits: List of subreddit names to scan (without r/)
        keywords: Search keywords for mushroom/wellness topics
        min_upvotes: Minimum score (upvotes - downvotes) to collect
        time_filter: Reddit time filter ("hour", "day", "week", "month", "year")
        max_posts_per_subreddit: Limit per subreddit-keyword combo
        rate_limit_requests_per_minute: API rate limit
    """

    subreddits: list[str] = field(default_factory=lambda: DEFAULT_SUBREDDITS.copy())
    keywords: list[str] = field(default_factory=lambda: DEFAULT_KEYWORDS.copy())
    min_upvotes: int = DEFAULT_MIN_UPVOTES
    time_filter: str = DEFAULT_TIME_FILTER
    max_posts_per_subreddit: int = DEFAULT_MAX_POSTS_PER_SUBREDDIT
    rate_limit_requests_per_minute: int = DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE

    def __post_init__(self) -> None:
        """Validate configuration values."""
        errors = []

        if not self.subreddits:
            errors.append("subreddits list cannot be empty")
        if not self.keywords:
            errors.append("keywords list cannot be empty")
        if self.min_upvotes < 0:
            errors.append(f"min_upvotes must be >= 0, got {self.min_upvotes}")
        if self.time_filter not in ("hour", "day", "week", "month", "year", "all"):
            errors.append(f"invalid time_filter: {self.time_filter}")
        if self.max_posts_per_subreddit < 1 or self.max_posts_per_subreddit > 100:
            errors.append(
                f"max_posts_per_subreddit must be 1-100, got {self.max_posts_per_subreddit}"
            )
        if self.rate_limit_requests_per_minute < 1:
            errors.append(
                f"rate_limit must be >= 1, got {self.rate_limit_requests_per_minute}"
            )

        if errors:
            raise ValueError(f"Invalid RedditScannerConfig: {'; '.join(errors)}")
