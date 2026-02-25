"""Health Claims Monitor configuration.

Epic 6, Story 6-1, Task 3: Health claims config.

Frozen dataclass for health claims monitor settings.
Loaded from config/dawo_health_claims.json via core.config._load_json_config,
injected into pipeline via Team Builder.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HealthClaimsMonitorConfig:
    """Configuration for the EU Health Claims Register monitor.

    Attributes:
        source_url: EU Open Data Portal dataset page URL
        download_url: Direct XLS download URL
        schedule_cron: Cron expression for monitoring schedule
        request_delay_seconds: Delay between HTTP requests
        max_retries: Maximum retry attempts for downloads
        mushroom_keywords: Keywords for mushroom substance matching
        adaptogen_keywords: Keywords for adaptogen substance matching
        vitamin_mineral_keywords: Keywords for vitamin/mineral matching
        alert_status_transitions: Status change transitions that trigger alerts
    """

    source_url: str = ""
    download_url: str = ""
    schedule_cron: str = "0 5 * * 0"
    request_delay_seconds: int = 5
    max_retries: int = 3
    mushroom_keywords: tuple[str, ...] = ()
    adaptogen_keywords: tuple[str, ...] = ()
    vitamin_mineral_keywords: tuple[str, ...] = ()
    alert_status_transitions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate config on creation."""
        errors: list[str] = []
        if not self.download_url:
            errors.append("download_url is required")
        if not self.mushroom_keywords and not self.adaptogen_keywords and not self.vitamin_mineral_keywords:
            errors.append("At least one keyword list must be non-empty")
        if self.request_delay_seconds < 0:
            errors.append("request_delay_seconds must be non-negative")
        if self.max_retries < 1:
            errors.append("max_retries must be at least 1")
        if errors:
            raise ValueError(f"Invalid HealthClaimsMonitorConfig: {'; '.join(errors)}")


def build_health_claims_config(data: dict) -> HealthClaimsMonitorConfig:
    """Build HealthClaimsMonitorConfig from JSON config data.

    Args:
        data: Parsed JSON from config/dawo_health_claims.json

    Returns:
        Validated HealthClaimsMonitorConfig instance
    """
    monitor = data.get("monitor", {})
    substances = data.get("substances", {})
    return HealthClaimsMonitorConfig(
        source_url=monitor.get("source_url", ""),
        download_url=monitor.get("download_url", ""),
        schedule_cron=monitor.get("schedule_cron", "0 5 * * 0"),
        request_delay_seconds=monitor.get("request_delay_seconds", 5),
        max_retries=monitor.get("max_retries", 3),
        mushroom_keywords=tuple(substances.get("mushroom", [])),
        adaptogen_keywords=tuple(substances.get("adaptogen", [])),
        vitamin_mineral_keywords=tuple(substances.get("vitamins_minerals", [])),
        alert_status_transitions=tuple(data.get("alert_on_status_change", [])),
    )


__all__ = [
    "HealthClaimsMonitorConfig",
    "build_health_claims_config",
]
