"""Configuration dataclasses for YouTube Research Scanner.

Provides configuration structures for:
    - YouTubeClientConfig: API credentials for YouTube Data API v3
    - TranscriptConfig: Transcript extraction settings
    - YouTubeScannerConfig: Scanner behavior settings

Configuration is injected via constructor - NEVER loaded from files directly.
Team Builder is responsible for loading config and injecting it.

Usage:
    # Team Builder creates config from environment/files
    client_config = YouTubeClientConfig(
        api_key=os.environ["YOUTUBE_API_KEY"],
    )

    # Inject into client
    client = YouTubeClient(client_config, retry_middleware)
"""

from dataclasses import dataclass, field


# YouTube API quota constants
YOUTUBE_DAILY_QUOTA = 10000
SEARCH_QUOTA_COST = 100  # units per search call
VIDEO_QUOTA_COST = 1     # units per video in batch (max 50)

# Default scanner configuration
DEFAULT_SEARCH_QUERIES = [
    "mushroom supplements",
    "lion's mane benefits",
    "adaptogen reviews",
    "cordyceps supplement",
    "reishi mushroom health",
]

DEFAULT_MIN_VIEWS = 1000
DEFAULT_DAYS_BACK = 7
DEFAULT_MAX_VIDEOS_PER_QUERY = 50

# Transcript configuration
DEFAULT_PREFERRED_LANGUAGES = ["en", "en-US", "en-GB"]
DEFAULT_MAX_TRANSCRIPT_LENGTH = 50000

# Content limits
MAX_CONTENT_LENGTH = 10000

# Health/wellness channel keywords for prioritization
DEFAULT_HEALTH_CHANNEL_KEYWORDS = [
    "health",
    "science",
    "medical",
    "nutrition",
    "wellness",
    "doctor",
    "research",
]


@dataclass(frozen=True)
class YouTubeClientConfig:
    """YouTube API credentials configuration.

    Used for authenticating with YouTube Data API v3.
    API key must be provided - loaded from environment variables.

    NEVER hardcode credentials in code.

    Attributes:
        api_key: YouTube Data API v3 key

    Raises:
        ValueError: If API key is empty
    """

    api_key: str

    def __post_init__(self) -> None:
        """Validate that API key is provided."""
        if not self.api_key:
            raise ValueError("api_key is required for YouTube Data API")


@dataclass
class TranscriptConfig:
    """Transcript extraction configuration.

    Settings for extracting video transcripts via youtube-transcript-api.

    Attributes:
        preferred_languages: Language codes in preference order
        max_transcript_length: Maximum transcript length in characters
    """

    preferred_languages: list[str] = field(
        default_factory=lambda: DEFAULT_PREFERRED_LANGUAGES.copy()
    )
    max_transcript_length: int = DEFAULT_MAX_TRANSCRIPT_LENGTH


@dataclass
class YouTubeScannerConfig:
    """Scanner behavior configuration.

    Defines search queries, filtering criteria, and quotas
    for YouTube video discovery.

    Loaded from config/dawo_youtube_scanner.json by Team Builder.

    Attributes:
        search_queries: Keywords to search for
        min_views: Minimum view count to collect
        days_back: Number of days back to search
        max_videos_per_query: Limit per search query
        health_channel_keywords: Keywords for health channel prioritization
        transcript_config: Transcript extraction settings
    """

    search_queries: list[str] = field(
        default_factory=lambda: DEFAULT_SEARCH_QUERIES.copy()
    )
    min_views: int = DEFAULT_MIN_VIEWS
    days_back: int = DEFAULT_DAYS_BACK
    max_videos_per_query: int = DEFAULT_MAX_VIDEOS_PER_QUERY
    health_channel_keywords: list[str] = field(
        default_factory=lambda: DEFAULT_HEALTH_CHANNEL_KEYWORDS.copy()
    )
    transcript_config: TranscriptConfig = field(default_factory=TranscriptConfig)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        errors = []

        if not self.search_queries:
            errors.append("search_queries list cannot be empty")
        if self.min_views < 0:
            errors.append(f"min_views must be >= 0, got {self.min_views}")
        if self.days_back < 1:
            errors.append(f"days_back must be >= 1, got {self.days_back}")
        if self.max_videos_per_query < 1 or self.max_videos_per_query > 50:
            errors.append(
                f"max_videos_per_query must be 1-50, got {self.max_videos_per_query}"
            )

        if errors:
            raise ValueError(f"Invalid YouTubeScannerConfig: {'; '.join(errors)}")
