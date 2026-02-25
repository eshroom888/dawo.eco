"""Claims Alert configuration.

Epic 6, Story 6-4, Task 1: Claims alert config.

Frozen dataclass for claims alert settings.
Loaded from config/dawo_claims_alerts.json via core.config._load_json_config,
injected into components via Team Builder.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClaimsAlertConfig:
    """Configuration for claims activation alerts.

    Attributes:
        enabled: Whether alerting is active
        webhook_url: Discord webhook URL for regulatory alerts
        batch_window_seconds: Seconds to batch events before sending
        dashboard_url: URL to regulatory dashboard for embed links
        max_retry_attempts: Maximum retry attempts on send failure
        backoff_schedule: Retry delay schedule in seconds
        dawo_product_keywords: Keywords for DAWO product relevance matching
        severity_emoji_map: Severity level to Discord emoji mapping
    """

    enabled: bool = True
    webhook_url: str = ""
    batch_window_seconds: int = 300
    dashboard_url: str = ""
    max_retry_attempts: int = 5
    backoff_schedule: tuple[int, ...] = (60, 300, 900, 3600)
    dawo_product_keywords: tuple[str, ...] = ()
    severity_emoji_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate config on creation."""
        errors: list[str] = []
        if self.enabled and not self.webhook_url:
            errors.append("webhook_url must not be empty when enabled")
        if not self.dawo_product_keywords:
            errors.append("dawo_product_keywords must not be empty")
        if self.batch_window_seconds <= 0:
            errors.append("batch_window_seconds must be positive")
        if errors:
            raise ValueError(f"Invalid ClaimsAlertConfig: {'; '.join(errors)}")


def build_claims_alert_config(data: dict) -> ClaimsAlertConfig:
    """Build ClaimsAlertConfig from JSON config data.

    Args:
        data: Parsed JSON from config/dawo_claims_alerts.json

    Returns:
        Validated ClaimsAlertConfig instance
    """
    return ClaimsAlertConfig(
        enabled=data.get("enabled", True),
        webhook_url=data.get("webhook_url", ""),
        batch_window_seconds=data.get("batch_window_seconds", 300),
        dashboard_url=data.get("dashboard_url", ""),
        max_retry_attempts=data.get("max_retry_attempts", 5),
        backoff_schedule=tuple(data.get("backoff_schedule", [60, 300, 900, 3600])),
        dawo_product_keywords=tuple(data.get("dawo_product_keywords", [])),
        severity_emoji_map=data.get("severity_emoji_map", {}),
    )


__all__ = [
    "ClaimsAlertConfig",
    "build_claims_alert_config",
]
