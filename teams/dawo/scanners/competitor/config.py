"""Competitor Scanner Configuration.

Epic 6, Story 6-5, Task 1: Frozen dataclass config for competitor content scanning.

Config is injected via constructor — NEVER loaded from files directly.
JSON source: config/dawo_competitor_scanner.json
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class CompetitorConfig:
    """Individual competitor entry.

    Attributes:
        name: Competitor display name
        instagram_username: Instagram handle (without @), None if not monitored
        website_urls: Tuple of website URLs to scrape
        is_primary: Whether this is a primary competitor (higher priority)
    """

    name: str = ""
    instagram_username: Optional[str] = None
    website_urls: tuple[str, ...] = ()
    is_primary: bool = False


@dataclass(frozen=True)
class InstagramScanConfig:
    """Instagram scanning configuration.

    Attributes:
        enabled: Whether Instagram scanning is active
        scan_window_days: Number of days back to scan
        max_posts_per_competitor: Maximum posts to fetch per competitor
    """

    enabled: bool = True
    scan_window_days: int = 7
    max_posts_per_competitor: int = 25


@dataclass(frozen=True)
class WebsiteScanConfig:
    """Website scraping configuration.

    Attributes:
        enabled: Whether website scraping is active
        request_delay_seconds: Delay between requests to same domain
        max_pages_per_domain: Maximum pages to scrape per domain
    """

    enabled: bool = True
    request_delay_seconds: int = 5
    max_pages_per_domain: int = 20


@dataclass(frozen=True)
class CompetitorScannerConfig:
    """Top-level competitor scanner configuration.

    Validated in __post_init__: at least 1 competitor,
    non-empty keywords, positive delays.

    Attributes:
        enabled: Whether the scanner is active
        schedule_cron: Cron expression for scheduled execution
        competitors: Tuple of competitor configurations
        health_language_keywords: Keywords for health language pre-filter
        instagram: Instagram scanning sub-config
        websites: Website scraping sub-config
        request_delay_seconds: Global delay between API calls
        max_retries: Maximum retry attempts for failed requests
        timeout_seconds: Request timeout in seconds
        user_agent: User-Agent header for HTTP requests
    """

    enabled: bool = True
    schedule_cron: str = "0 3 * * *"
    competitors: tuple[CompetitorConfig, ...] = ()
    health_language_keywords: tuple[str, ...] = ()
    instagram: InstagramScanConfig = field(default_factory=InstagramScanConfig)
    websites: WebsiteScanConfig = field(default_factory=WebsiteScanConfig)
    request_delay_seconds: int = 3
    max_retries: int = 3
    timeout_seconds: int = 30
    user_agent: str = "DAWO-ECO-CompetitorMonitor/1.0 (+https://imagoeco.com/bot)"

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        errors: list[str] = []
        if not self.competitors:
            errors.append("At least one competitor must be configured")
        if not self.health_language_keywords:
            errors.append("health_language_keywords must not be empty")
        if self.request_delay_seconds < 0:
            errors.append("request_delay_seconds must be non-negative")
        if errors:
            raise ValueError(f"Invalid CompetitorScannerConfig: {'; '.join(errors)}")


def build_competitor_scanner_config(data: dict) -> CompetitorScannerConfig:
    """Build CompetitorScannerConfig from a JSON-parsed dict.

    Converts list fields to tuples for frozen dataclass compatibility.

    Args:
        data: Dictionary from JSON config file

    Returns:
        Validated CompetitorScannerConfig instance
    """
    competitors = tuple(
        CompetitorConfig(
            name=c.get("name", ""),
            instagram_username=c.get("instagram_username"),
            website_urls=tuple(c.get("website_urls", [])),
            is_primary=c.get("is_primary", False),
        )
        for c in data.get("competitors", [])
    )

    instagram_data = data.get("instagram", {})
    instagram = InstagramScanConfig(
        enabled=instagram_data.get("enabled", True),
        scan_window_days=instagram_data.get("scan_window_days", 7),
        max_posts_per_competitor=instagram_data.get("max_posts_per_competitor", 25),
    )

    websites_data = data.get("websites", {})
    websites = WebsiteScanConfig(
        enabled=websites_data.get("enabled", True),
        request_delay_seconds=websites_data.get("request_delay_seconds", 5),
        max_pages_per_domain=websites_data.get("max_pages_per_domain", 20),
    )

    return CompetitorScannerConfig(
        enabled=data.get("enabled", True),
        schedule_cron=data.get("schedule_cron", "0 3 * * *"),
        competitors=competitors,
        health_language_keywords=tuple(data.get("health_language_keywords", [])),
        instagram=instagram,
        websites=websites,
        request_delay_seconds=data.get("request_delay_seconds", 3),
        max_retries=data.get("max_retries", 3),
        timeout_seconds=data.get("timeout_seconds", 30),
        user_agent=data.get(
            "user_agent",
            "DAWO-ECO-CompetitorMonitor/1.0 (+https://imagoeco.com/bot)",
        ),
    )


__all__ = [
    "CompetitorConfig",
    "CompetitorScannerConfig",
    "InstagramScanConfig",
    "WebsiteScanConfig",
    "build_competitor_scanner_config",
]
