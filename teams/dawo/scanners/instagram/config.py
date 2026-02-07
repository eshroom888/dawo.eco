"""Configuration dataclasses for Instagram Trend Scanner.

Provides configuration structures for:
    - InstagramClientConfig: API credentials for Instagram Graph API
    - InstagramScannerConfig: Scanner behavior settings

Configuration is injected via constructor - NEVER loaded from files directly.
Team Builder is responsible for loading config and injecting it.

Usage:
    # Team Builder creates config from environment/files
    client_config = InstagramClientConfig(
        access_token=os.environ["INSTAGRAM_ACCESS_TOKEN"],
        business_account_id=os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"],
    )

    # Inject into client
    client = InstagramClient(client_config, retry_middleware)
"""

from dataclasses import dataclass, field


# Instagram Graph API constants
INSTAGRAM_RATE_LIMIT_PER_HOUR = 200  # Business account rate limit
INSTAGRAM_MAX_RESULTS_PER_CALL = 30  # Instagram API caps at 30

# Default scanner configuration
DEFAULT_HASHTAGS = [
    "lionsmane",
    "mushroomsupplements",
    "adaptogens",
    "biohacking",
    "functionalmushrooms",
]

DEFAULT_HOURS_BACK = 24
DEFAULT_MAX_POSTS_PER_HASHTAG = 25
DEFAULT_MAX_POSTS_PER_ACCOUNT = 10

# Content limits
MAX_CAPTION_LENGTH = 10000
MAX_CONTENT_LENGTH = 10000

# Health claim detection keywords (for pre-filtering)
HEALTH_CLAIM_INDICATORS = [
    "treat",
    "cure",
    "prevent",
    "boost",
    "enhance",
    "improve",
    "fight",
    "heal",
    "reduce",
    "increase",
    "support",
]


@dataclass(frozen=True)
class InstagramClientConfig:
    """Instagram API credentials configuration.

    Used for authenticating with Instagram Graph API.
    Requires a Business or Creator account with proper permissions.

    NEVER hardcode credentials in code - load from environment variables.

    Attributes:
        access_token: Instagram Graph API access token
        business_account_id: Instagram Business Account ID for API calls

    Raises:
        ValueError: If access token or business account ID is empty
    """

    access_token: str
    business_account_id: str

    def __post_init__(self) -> None:
        """Validate that credentials are provided."""
        if not self.access_token:
            raise ValueError("access_token is required for Instagram Graph API")
        if not self.business_account_id:
            raise ValueError("business_account_id is required for Instagram Graph API")


@dataclass
class InstagramScannerConfig:
    """Scanner behavior configuration.

    Defines hashtags, competitor accounts, and filtering criteria
    for Instagram content discovery.

    Loaded from config/dawo_instagram_scanner.json by Team Builder.

    Attributes:
        hashtags: Hashtags to monitor (without #)
        competitor_accounts: Instagram usernames to monitor (without @)
        hours_back: How many hours back to search
        max_posts_per_hashtag: Limit per hashtag search
        max_posts_per_account: Limit per competitor account
    """

    hashtags: list[str] = field(default_factory=lambda: DEFAULT_HASHTAGS.copy())
    competitor_accounts: list[str] = field(default_factory=list)
    hours_back: int = DEFAULT_HOURS_BACK
    max_posts_per_hashtag: int = DEFAULT_MAX_POSTS_PER_HASHTAG
    max_posts_per_account: int = DEFAULT_MAX_POSTS_PER_ACCOUNT

    def __post_init__(self) -> None:
        """Validate configuration values."""
        errors = []

        if not self.hashtags:
            errors.append("hashtags list cannot be empty")
        if self.hours_back < 1:
            errors.append(f"hours_back must be >= 1, got {self.hours_back}")
        if self.max_posts_per_hashtag < 1 or self.max_posts_per_hashtag > 30:
            errors.append(
                f"max_posts_per_hashtag must be 1-30, got {self.max_posts_per_hashtag}"
            )
        if self.max_posts_per_account < 1 or self.max_posts_per_account > 30:
            errors.append(
                f"max_posts_per_account must be 1-30, got {self.max_posts_per_account}"
            )

        if errors:
            raise ValueError(f"Invalid InstagramScannerConfig: {'; '.join(errors)}")
