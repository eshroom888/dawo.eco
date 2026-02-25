"""Novel Food Monitor configuration.

Epic 6, Story 6-2: Novel Food Catalogue Monitor.

Frozen dataclass configuration for the Novel Food monitor,
loaded via constructor injection from JSON config.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpeciesConfig:
    """Configuration for a single monitored species.

    Attributes:
        latin_name: Latin species name (e.g., "Hericium erinaceus")
        common_names: Common names (e.g., ("Lion's Mane", "Yamabushitake"))
        is_dawo_product: Whether this species is a DAWO product (elevates severity)
    """

    latin_name: str
    common_names: tuple[str, ...] = ()
    is_dawo_product: bool = False


@dataclass(frozen=True)
class NovelFoodMonitorConfig:
    """Configuration for the Novel Food Catalogue Monitor.

    Validated in __post_init__. Requires non-empty search_url and species list.

    Attributes:
        search_url: Backend API URL for catalogue search
        portal_url: Public portal URL for the catalogue
        schedule_cron: Cron expression for scheduling (default: Sunday 5:30 AM)
        request_delay_seconds: Delay between HTTP requests (rate limiting)
        max_retries: Maximum retry attempts per request
        timeout_seconds: HTTP request timeout
        user_agent: User-Agent header for requests
        species: Tuple of species configurations to monitor
        alert_status_transitions: Status transitions that trigger alerts
    """

    search_url: str = ""
    portal_url: str = ""  # Reserved for HTML fallback if backend endpoint changes
    schedule_cron: str = "30 5 * * 0"
    request_delay_seconds: int = 10
    max_retries: int = 3
    timeout_seconds: int = 30
    user_agent: str = "DAWO-ECO-RegulatoryMonitor/1.0"
    species: tuple[SpeciesConfig, ...] = ()
    alert_status_transitions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        errors: list[str] = []
        if not self.search_url:
            errors.append("search_url is required")
        if not self.species:
            errors.append("At least one species must be configured")
        if errors:
            raise ValueError(f"Invalid config: {'; '.join(errors)}")


def build_novel_food_config(data: dict) -> NovelFoodMonitorConfig:
    """Build NovelFoodMonitorConfig from a JSON-loaded dict.

    Args:
        data: Dict with 'monitor' and 'species' sections.

    Returns:
        Validated NovelFoodMonitorConfig instance.
    """
    monitor = data.get("monitor", {})
    species_list = data.get("species", [])
    alert_transitions = data.get("alert_on_status_change", [])

    species_configs = tuple(
        SpeciesConfig(
            latin_name=s["latin_name"],
            common_names=tuple(s.get("common_names", [])),
            is_dawo_product=s.get("is_dawo_product", False),
        )
        for s in species_list
    )

    return NovelFoodMonitorConfig(
        search_url=monitor.get("search_url", ""),
        portal_url=monitor.get("portal_url", ""),
        schedule_cron=monitor.get("schedule_cron", "30 5 * * 0"),
        request_delay_seconds=monitor.get("request_delay_seconds", 10),
        max_retries=monitor.get("max_retries", 3),
        timeout_seconds=monitor.get("timeout_seconds", 30),
        user_agent=monitor.get("user_agent", "DAWO-ECO-RegulatoryMonitor/1.0"),
        species=species_configs,
        alert_status_transitions=tuple(alert_transitions),
    )


__all__ = [
    "SpeciesConfig",
    "NovelFoodMonitorConfig",
    "build_novel_food_config",
]
