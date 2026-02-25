"""Mattilsynet monitor configuration.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 3: Config dataclasses and builder.

Frozen dataclasses for monitor configuration, injected via constructor.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedConfig:
    """Configuration for a single RSS/Atom feed.

    Attributes:
        name: Human-readable feed name
        url: Feed URL
        is_primary: Whether this is a primary feed
    """

    name: str
    url: str
    is_primary: bool = False


@dataclass(frozen=True)
class MonitoredPageConfig:
    """Configuration for a monitored page.

    Attributes:
        name: Human-readable page name
        url: Page URL
    """

    name: str
    url: str


@dataclass(frozen=True)
class MattilsynetMonitorConfig:
    """Configuration for the Mattilsynet regulatory monitor.

    Attributes:
        schedule_cron: Cron expression for scheduling (default daily 7 AM)
        request_delay_seconds: Delay between HTTP requests
        max_retries: Max retry attempts per request
        timeout_seconds: HTTP request timeout
        user_agent: User-Agent header value
        feeds: RSS/Atom feed configurations
        monitored_pages: Page monitoring configurations
        keywords_tier_1: High-priority Norwegian keywords
        keywords_tier_2: Product-specific keywords
        enforcement_keywords: Enforcement action keywords
    """

    schedule_cron: str = "0 7 * * *"
    request_delay_seconds: int = 5
    max_retries: int = 3
    timeout_seconds: int = 30
    user_agent: str = "DAWO-ECO-RegMonitor/1.0 (regulatory-compliance-monitoring)"
    feeds: tuple[FeedConfig, ...] = ()
    monitored_pages: tuple[MonitoredPageConfig, ...] = ()
    keywords_tier_1: tuple[str, ...] = ()
    keywords_tier_2: tuple[str, ...] = ()
    enforcement_keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        errors: list[str] = []
        if not self.feeds and not self.monitored_pages:
            errors.append("At least one feed or monitored page must be configured")
        if not self.keywords_tier_1:
            errors.append("keywords_tier_1 must not be empty")
        if errors:
            raise ValueError(f"Invalid MattilsynetMonitorConfig: {'; '.join(errors)}")


def build_mattilsynet_config(data: dict) -> MattilsynetMonitorConfig:
    """Build MattilsynetMonitorConfig from a JSON-loaded dict.

    Args:
        data: Dict loaded from config/dawo_mattilsynet.json

    Returns:
        Frozen MattilsynetMonitorConfig instance
    """
    monitor = data.get("monitor", {})

    feeds = tuple(
        FeedConfig(
            name=f["name"],
            url=f["url"],
            is_primary=f.get("is_primary", False),
        )
        for f in data.get("feeds", [])
    )

    monitored_pages = tuple(
        MonitoredPageConfig(name=p["name"], url=p["url"])
        for p in data.get("monitored_pages", [])
    )

    return MattilsynetMonitorConfig(
        schedule_cron=monitor.get("schedule_cron", "0 7 * * *"),
        request_delay_seconds=monitor.get("request_delay_seconds", 5),
        max_retries=monitor.get("max_retries", 3),
        timeout_seconds=monitor.get("timeout_seconds", 30),
        user_agent=monitor.get(
            "user_agent",
            "DAWO-ECO-RegMonitor/1.0 (regulatory-compliance-monitoring)",
        ),
        feeds=feeds,
        monitored_pages=monitored_pages,
        keywords_tier_1=tuple(data.get("keywords_tier_1", [])),
        keywords_tier_2=tuple(data.get("keywords_tier_2", [])),
        enforcement_keywords=tuple(data.get("enforcement_keywords", [])),
    )


__all__ = [
    "FeedConfig",
    "MattilsynetMonitorConfig",
    "MonitoredPageConfig",
    "build_mattilsynet_config",
]
