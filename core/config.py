"""Centralized Configuration Loader.

Epic 4 Tech Debt: Externalize rate limits and configurable values.

Loads configuration from JSON files in the config/ directory,
with environment variable interpolation support.

Usage:
    from core.config import get_config, RateLimits, NotificationConfig

    # Get rate limits
    limits = get_config().rate_limits
    quota = limits.instagram_api.quota_limit_per_hour

    # Get notification config
    notif = get_config().notifications
    cooldown = notif.approval.cooldown_minutes
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Config directory relative to project root
CONFIG_DIR = Path(__file__).parent.parent / "config"


def _interpolate_env_vars(value: Any) -> Any:
    """Replace ${VAR} patterns with environment variable values.

    Args:
        value: Value to interpolate (string, dict, or list)

    Returns:
        Value with environment variables replaced
    """
    if isinstance(value, str):
        # Match ${VAR} pattern
        pattern = re.compile(r"\$\{([^}]+)\}")
        matches = pattern.findall(value)
        for var in matches:
            env_value = os.environ.get(var, "")
            value = value.replace(f"${{{var}}}", env_value)
        return value
    elif isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_interpolate_env_vars(v) for v in value]
    return value


def _load_json_config(filename: str) -> dict:
    """Load and parse a JSON config file.

    Args:
        filename: Name of config file (e.g., "dawo_rate_limits.json")

    Returns:
        Parsed config dictionary with env vars interpolated
    """
    filepath = CONFIG_DIR / filename
    try:
        with open(filepath, encoding="utf-8") as f:
            config = json.load(f)
        return _interpolate_env_vars(config)
    except FileNotFoundError:
        logger.warning(f"Config file not found: {filepath}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return {}


# === Rate Limits Config ===


@dataclass(frozen=True)
class InstagramApiLimits:
    """Instagram API rate limits and thresholds."""

    quota_limit_per_hour: int = 200
    publish_timeout_seconds: int = 30
    max_caption_length: int = 2200
    max_hashtags: int = 30
    latency_target_seconds: float = 30.0
    success_rate_threshold: float = 99.0
    failure_threshold: int = 3
    metrics_window_size: int = 1000


@dataclass(frozen=True)
class WebSocketLimits:
    """WebSocket connection limits."""

    max_queue_size: int = 100
    max_subscribers: int = 100


@dataclass(frozen=True)
class NotificationLimits:
    """Notification rate limits."""

    cooldown_minutes: int = 60
    batch_window_minutes: int = 15
    daily_summary_hour: int = 22
    pending_queue_ttl_hours: int = 24
    max_retry_attempts: int = 5
    backoff_schedule_seconds: list[int] = field(
        default_factory=lambda: [60, 300, 900, 3600]
    )


@dataclass(frozen=True)
class DiscordWebhookLimits:
    """Discord webhook rate limits."""

    max_requests_per_second: int = 5
    burst_limit: int = 50
    reset_window_seconds: int = 60


@dataclass(frozen=True)
class SchedulingLimits:
    """Content scheduling limits."""

    max_posts_per_day: int = 10
    max_posts_per_slot: int = 1
    min_hours_between_posts: int = 2
    business_hours_start: int = 8
    business_hours_end: int = 22


@dataclass(frozen=True)
class GmailLimits:
    """Gmail API rate limits."""

    max_per_minute: int = 20
    max_per_day: int = 500
    burst_size: int = 5
    business_hours_start: int = 8
    business_hours_end: int = 17
    timezone: str = "Europe/Oslo"


@dataclass(frozen=True)
class RateLimits:
    """All rate limit configurations."""

    instagram_api: InstagramApiLimits = field(default_factory=InstagramApiLimits)
    websocket: WebSocketLimits = field(default_factory=WebSocketLimits)
    notifications: NotificationLimits = field(default_factory=NotificationLimits)
    discord_webhook: DiscordWebhookLimits = field(default_factory=DiscordWebhookLimits)
    scheduling: SchedulingLimits = field(default_factory=SchedulingLimits)
    gmail: GmailLimits = field(default_factory=GmailLimits)


# === Notification Config ===


@dataclass(frozen=True)
class ApprovalNotificationConfig:
    """Approval notification settings."""

    enabled: bool = True
    webhook_url: str = ""
    threshold: int = 5
    cooldown_minutes: int = 60
    dashboard_url: str = "http://localhost:3000/approval"


@dataclass(frozen=True)
class PublishNotificationConfig:
    """Publish notification settings."""

    enabled: bool = True
    webhook_url: str = ""
    batch_window_minutes: int = 15
    daily_summary_hour: int = 22
    dashboard_url: str = "http://localhost:3000/approval"
    success_notifications: bool = True
    failure_notifications: bool = True
    batch_notifications: bool = True
    daily_summary: bool = True


@dataclass(frozen=True)
class NotificationConfig:
    """All notification configurations."""

    approval: ApprovalNotificationConfig = field(
        default_factory=ApprovalNotificationConfig
    )
    publish: PublishNotificationConfig = field(
        default_factory=PublishNotificationConfig
    )


# === Retry Config ===


@dataclass(frozen=True)
class RetryDefaults:
    """Default retry settings."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    timeout: float = 30.0
    max_rate_limit_wait: int = 300


@dataclass(frozen=True)
class RetryConfig:
    """Retry configuration."""

    defaults: RetryDefaults = field(default_factory=RetryDefaults)
    api_overrides: dict = field(default_factory=dict)


# === Analytics Config (Story 7-1) ===


@dataclass(frozen=True)
class CollectionInterval:
    """A single metrics collection interval.

    Attributes:
        label: Snapshot label (e.g., "baseline", "24h", "48h", "7d")
        delay_hours: Hours after publish to collect metrics
    """

    label: str = "baseline"
    delay_hours: int = 1


@dataclass(frozen=True)
class AnalyticsConfig:
    """Analytics collection configuration.

    Story 7-1, Task 7.2: Frozen dataclass for analytics settings.

    Attributes:
        collection_intervals: List of intervals for metrics collection
        rate_limit_buffer: Calls to reserve for other operations
        retry_max_attempts: Max retry attempts for failed collections
        retry_base_delay: Base delay in seconds for retry backoff
        discord_channel: Discord webhook URL for analytics alerts
    """

    collection_intervals: tuple[CollectionInterval, ...] = (
        CollectionInterval("baseline", 1),
        CollectionInterval("24h", 24),
        CollectionInterval("48h", 48),
        CollectionInterval("7d", 168),
    )
    rate_limit_buffer: int = 10
    retry_max_attempts: int = 3
    retry_base_delay: float = 2.0
    discord_channel: str = ""


# === UTM Config (Story 7-2) ===


@dataclass(frozen=True)
class UTMConfig:
    """UTM click-through tracking configuration.

    Story 7-2, Task 7.2: Frozen dataclass for UTM settings.

    Attributes:
        short_link_base_url: Base URL for short links (e.g., "https://dawo.no")
        default_attribution_window_days: Days to keep attribution data
        code_length: Length of generated short codes
    """

    short_link_base_url: str = ""
    default_attribution_window_days: int = 30
    code_length: int = 8


# === Attribution Config (Story 7-3) ===


@dataclass(frozen=True)
class AttributionConfig:
    """Shopify sales attribution configuration.

    Story 7-3, Task 7.2: Frozen dataclass for attribution settings.

    Attributes:
        webhook_secret: Shopify webhook HMAC signing secret
        polling_interval_hours: Hours between fallback polling runs
        attribution_window_days: Days to keep attribution data
        max_touchpoints: Maximum customer journey moments to record
    """

    webhook_secret: str = ""
    polling_interval_hours: int = 1
    attribution_window_days: int = 30
    max_touchpoints: int = 50


# === Quality Scoring Config (Story 7-4) ===


@dataclass(frozen=True)
class CTRScale:
    """CTR-to-score mapping configuration.

    Story 7-4, Task 7.2: Configurable CTR scale.
    """

    max_ctr_pct: float = 5.0
    min_score: float = 1.0
    max_score: float = 10.0


@dataclass(frozen=True)
class ConversionScale:
    """Order-count-to-score mapping configuration.

    Story 7-4, Task 7.2: Configurable conversion scale.
    """

    max_orders: int = 5
    min_score: float = 2.0
    max_score: float = 10.0


@dataclass(frozen=True)
class QualityScoringConfig:
    """Post-publish quality scoring configuration.

    Story 7-4, Task 7.2: Frozen dataclass for scoring settings.

    Attributes:
        variance_threshold: Abs variance above this flags for review
        min_posts_for_correlation: Minimum posts before running correlation
        scoring_delay_days: Days after publish to compute score
        weights: Component weight mapping (must sum to 1.0)
        ctr_scale: CTR-to-score mapping parameters
        conversion_scale: Orders-to-score mapping parameters
    """

    variance_threshold: float = 3.0
    min_posts_for_correlation: int = 50
    scoring_delay_days: int = 7
    weights: dict = field(default_factory=lambda: {
        "engagement_vs_avg": 0.30,
        "reach_vs_avg": 0.20,
        "click_through_rate": 0.20,
        "conversions": 0.15,
        "comment_sentiment": 0.15,
    })
    ctr_scale: CTRScale = field(default_factory=CTRScale)
    conversion_scale: ConversionScale = field(default_factory=ConversionScale)


# === Feedback Loop Config (Story 7-5) ===


@dataclass(frozen=True)
class FeedbackLoopConfig:
    """Feedback loop configuration.

    Story 7-5, Task 6.1: Frozen dataclass for feedback loop settings.

    Attributes:
        min_posts_threshold: Minimum scored posts to run weekly analysis
        weight_change_threshold: Minimum weight delta to propose change
        min_hashtag_posts: Minimum posts per hashtag to qualify for ranking
        top_hashtags_limit: Maximum hashtags to return in analysis
        enabled: Whether the feedback loop job is active
    """

    min_posts_threshold: int = 100
    weight_change_threshold: float = 0.05
    min_hashtag_posts: int = 3
    top_hashtags_limit: int = 20
    enabled: bool = True


# === Agent Scheduler Config (Story 7-6) ===


@dataclass(frozen=True)
class AgentSchedulerConfig:
    """Agent scheduler configuration.

    Story 7-6, Task 6.1: Frozen dataclass for agent scheduler settings.

    Attributes:
        enabled: Whether the scheduler dispatcher is active
        check_interval_seconds: How often to check for due schedules
        max_concurrent_agents: Max agents running simultaneously
        default_timezone: Default timezone for new schedules
        seed_on_startup: Whether to seed defaults on first startup
    """

    enabled: bool = True
    check_interval_seconds: int = 60
    max_concurrent_agents: int = 5
    default_timezone: str = "UTC"
    seed_on_startup: bool = True


# === Degradation Config (Story 7-10) ===


@dataclass(frozen=True)
class DegradationConfig:
    """Graceful API degradation configuration.

    Story 7-10, Task 1.3: Frozen dataclass for degradation thresholds.

    Attributes:
        failure_threshold: Consecutive failures before marking degraded
        unhealthy_threshold: Consecutive failures before marking unhealthy
        recovery_check_interval_seconds: Seconds between recovery checks
        max_recovery_batch_size: Max items per recovery pass
        alert_cooldown_seconds: Min seconds between alerts per service
        stale_cache_ttl_hours: Hours before stale cache expires
        monitored_services: List of service names to monitor
    """

    failure_threshold: int = 3
    unhealthy_threshold: int = 10
    recovery_check_interval_seconds: int = 300
    max_recovery_batch_size: int = 20
    alert_cooldown_seconds: int = 300
    stale_cache_ttl_hours: int = 24
    monitored_services: tuple[str, ...] = (
        "instagram", "shopify", "discord", "google_calendar",
    )


# === Calendar Config (Story 7-9) ===


@dataclass(frozen=True)
class CalendarConfig:
    """Google Calendar sync configuration.

    Story 7-9, Task 1.2: Frozen dataclass for calendar settings.

    Attributes:
        token_path: Path to Calendar OAuth2 token file
        credentials_path: Path to Google OAuth2 client secrets file
        scopes: OAuth2 scopes for Calendar API
        calendar_name: Name of the dedicated DAWO calendar
        calendar_id: Google Calendar ID (populated at runtime)
        sync_enabled: Whether calendar sync is active
        dashboard_base_url: Base URL for dashboard content links
        color_ids: Map of status to Google Calendar color ID
        max_title_length: Maximum characters for event title
    """

    token_path: str = "credentials/calendar_token.json"
    credentials_path: str = "credentials/google-oauth.json"
    scopes: tuple[str, ...] = ("https://www.googleapis.com/auth/calendar",)
    calendar_name: str = "DAWO Content Schedule"
    calendar_id: str = ""
    sync_enabled: bool = True
    dashboard_base_url: str = ""
    color_ids: dict[str, str] = field(default_factory=lambda: {
        "scheduled": "10",
        "published": "9",
        "failed": "11",
    })
    max_title_length: int = 60


# === Main Config ===


@dataclass(frozen=True)
class Config:
    """Main configuration container."""

    rate_limits: RateLimits = field(default_factory=RateLimits)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)
    utm: UTMConfig = field(default_factory=UTMConfig)
    attribution: AttributionConfig = field(default_factory=AttributionConfig)
    quality_scoring: QualityScoringConfig = field(default_factory=QualityScoringConfig)
    feedback_loop: FeedbackLoopConfig = field(default_factory=FeedbackLoopConfig)
    agent_scheduler: AgentSchedulerConfig = field(default_factory=AgentSchedulerConfig)
    calendar: CalendarConfig = field(default_factory=CalendarConfig)
    degradation: DegradationConfig = field(default_factory=DegradationConfig)


def _build_rate_limits(data: dict) -> RateLimits:
    """Build RateLimits from config data."""
    return RateLimits(
        instagram_api=InstagramApiLimits(**data.get("instagram_api", {})),
        websocket=WebSocketLimits(**data.get("websocket", {})),
        notifications=NotificationLimits(
            **{
                k: v
                for k, v in data.get("notifications", {}).items()
                if k != "backoff_schedule_seconds"
            },
            backoff_schedule_seconds=data.get("notifications", {}).get(
                "backoff_schedule_seconds", [60, 300, 900, 3600]
            ),
        ),
        discord_webhook=DiscordWebhookLimits(**data.get("discord_webhook", {})),
        scheduling=SchedulingLimits(**data.get("scheduling", {})),
        gmail=_build_gmail_limits(data.get("gmail", {})),
    )


def _build_gmail_limits(data: dict) -> GmailLimits:
    """Build GmailLimits from config data."""
    bh = data.get("business_hours", {})
    return GmailLimits(
        max_per_minute=data.get("max_per_minute", 20),
        max_per_day=data.get("max_per_day", 500),
        burst_size=data.get("burst_size", 5),
        business_hours_start=bh.get("start", 8),
        business_hours_end=bh.get("end", 17),
        timezone=bh.get("timezone", "Europe/Oslo"),
    )


def _build_notification_config(data: dict) -> NotificationConfig:
    """Build NotificationConfig from config data."""
    return NotificationConfig(
        approval=ApprovalNotificationConfig(
            **data.get("approval_notifications", {})
        ),
        publish=PublishNotificationConfig(
            **data.get("publish_notifications", {})
        ),
    )


def _build_retry_config(data: dict) -> RetryConfig:
    """Build RetryConfig from config data."""
    return RetryConfig(
        defaults=RetryDefaults(**data.get("default", {})),
        api_overrides=data.get("api_overrides", {}),
    )


def _build_analytics_config(data: dict) -> AnalyticsConfig:
    """Build AnalyticsConfig from config data."""
    intervals_data = data.get("collection_intervals", [])
    intervals = tuple(
        CollectionInterval(
            label=i.get("label", "baseline"),
            delay_hours=i.get("delay_hours", 1),
        )
        for i in intervals_data
    ) if intervals_data else AnalyticsConfig.collection_intervals

    return AnalyticsConfig(
        collection_intervals=intervals,
        rate_limit_buffer=data.get("rate_limit_buffer", 10),
        retry_max_attempts=data.get("retry_max_attempts", 3),
        retry_base_delay=data.get("retry_base_delay", 2.0),
        discord_channel=data.get("discord_channel", ""),
    )


def _build_utm_config(data: dict) -> UTMConfig:
    """Build UTMConfig from config data.

    Story 7-2, Task 7.3: UTM config loader.
    """
    utm_data = data.get("utm_config", {})
    return UTMConfig(
        short_link_base_url=utm_data.get("short_link_base_url", ""),
        default_attribution_window_days=utm_data.get(
            "default_attribution_window_days", 30
        ),
        code_length=utm_data.get("code_length", 8),
    )


def _build_attribution_config(data: dict) -> AttributionConfig:
    """Build AttributionConfig from config data.

    Story 7-3, Task 7.3: Attribution config loader.
    """
    attr_data = data.get("attribution", {})
    return AttributionConfig(
        webhook_secret=attr_data.get("webhook_secret", ""),
        polling_interval_hours=attr_data.get("polling_interval_hours", 1),
        attribution_window_days=attr_data.get("attribution_window_days", 30),
        max_touchpoints=attr_data.get("max_touchpoints", 50),
    )


def _build_quality_scoring_config(data: dict) -> QualityScoringConfig:
    """Build QualityScoringConfig from config data.

    Story 7-4, Task 7.3: Quality scoring config loader.
    """
    qs_data = data.get("quality_scoring", {})
    ctr_data = qs_data.get("ctr_scale", {})
    conv_data = qs_data.get("conversion_scale", {})

    return QualityScoringConfig(
        variance_threshold=qs_data.get("variance_threshold", 3.0),
        min_posts_for_correlation=qs_data.get("min_posts_for_correlation", 50),
        scoring_delay_days=qs_data.get("scoring_delay_days", 7),
        weights=qs_data.get("weights", {
            "engagement_vs_avg": 0.30,
            "reach_vs_avg": 0.20,
            "click_through_rate": 0.20,
            "conversions": 0.15,
            "comment_sentiment": 0.15,
        }),
        ctr_scale=CTRScale(**ctr_data) if ctr_data else CTRScale(),
        conversion_scale=ConversionScale(**conv_data) if conv_data else ConversionScale(),
    )


def _build_feedback_loop_config(data: dict) -> FeedbackLoopConfig:
    """Build FeedbackLoopConfig from config data.

    Story 7-5, Task 6.1: Feedback loop config loader.
    """
    fl_data = data.get("feedback_loop", {})
    return FeedbackLoopConfig(
        min_posts_threshold=fl_data.get("min_posts_threshold", 100),
        weight_change_threshold=fl_data.get("weight_change_threshold", 0.05),
        min_hashtag_posts=fl_data.get("min_hashtag_posts", 3),
        top_hashtags_limit=fl_data.get("top_hashtags_limit", 20),
        enabled=fl_data.get("enabled", True),
    )


def _build_agent_scheduler_config(data: dict) -> AgentSchedulerConfig:
    """Build AgentSchedulerConfig from config data.

    Story 7-6, Task 6.1: Agent scheduler config loader.
    """
    sched_data = data.get("agent_scheduler", {})
    return AgentSchedulerConfig(
        enabled=sched_data.get("enabled", True),
        check_interval_seconds=sched_data.get("check_interval_seconds", 60),
        max_concurrent_agents=sched_data.get("max_concurrent_agents", 5),
        default_timezone=sched_data.get("default_timezone", "UTC"),
        seed_on_startup=sched_data.get("seed_on_startup", True),
    )


def _build_calendar_config(data: dict) -> CalendarConfig:
    """Build CalendarConfig from config data.

    Story 7-9, Task 1.2: Calendar config loader.
    """
    scopes_list = data.get("scopes", ["https://www.googleapis.com/auth/calendar"])
    return CalendarConfig(
        token_path=data.get("token_path", "credentials/calendar_token.json"),
        credentials_path=data.get("credentials_path", "credentials/google-oauth.json"),
        scopes=tuple(scopes_list),
        calendar_name=data.get("calendar_name", "DAWO Content Schedule"),
        calendar_id=data.get("calendar_id", ""),
        sync_enabled=data.get("sync_enabled", True),
        dashboard_base_url=data.get("dashboard_base_url", ""),
        color_ids=data.get("color_ids", {
            "scheduled": "10",
            "published": "9",
            "failed": "11",
        }),
        max_title_length=data.get("max_title_length", 60),
    )


def _build_degradation_config(data: dict) -> DegradationConfig:
    """Build DegradationConfig from config data.

    Story 7-10, Task 1.3: Degradation config loader.
    """
    services_list = data.get(
        "monitored_services",
        ["instagram", "shopify", "discord", "google_calendar"],
    )
    return DegradationConfig(
        failure_threshold=data.get("failure_threshold", 3),
        unhealthy_threshold=data.get("unhealthy_threshold", 10),
        recovery_check_interval_seconds=data.get("recovery_check_interval_seconds", 300),
        max_recovery_batch_size=data.get("max_recovery_batch_size", 20),
        alert_cooldown_seconds=data.get("alert_cooldown_seconds", 300),
        stale_cache_ttl_hours=data.get("stale_cache_ttl_hours", 24),
        monitored_services=tuple(services_list),
    )


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get the application configuration (cached).

    Loads configuration from JSON files on first call,
    returns cached instance on subsequent calls.

    Returns:
        Config instance with all settings
    """
    rate_limits_data = _load_json_config("dawo_rate_limits.json")
    notifications_data = _load_json_config("dawo_notifications.json")
    retry_data = _load_json_config("dawo_retry_config.json")
    analytics_data = _load_json_config("dawo_analytics.json")
    calendar_data = _load_json_config("dawo_calendar.json")
    degradation_data = _load_json_config("dawo_degradation.json")

    return Config(
        rate_limits=_build_rate_limits(rate_limits_data),
        notifications=_build_notification_config(notifications_data),
        retry=_build_retry_config(retry_data),
        analytics=_build_analytics_config(analytics_data),
        utm=_build_utm_config(analytics_data),
        attribution=_build_attribution_config(analytics_data),
        quality_scoring=_build_quality_scoring_config(analytics_data),
        feedback_loop=_build_feedback_loop_config(analytics_data),
        agent_scheduler=_build_agent_scheduler_config(analytics_data),
        calendar=_build_calendar_config(calendar_data),
        degradation=_build_degradation_config(degradation_data),
    )


def reload_config() -> Config:
    """Force reload configuration from files.

    Clears cache and reloads all config files.

    Returns:
        Fresh Config instance
    """
    get_config.cache_clear()
    return get_config()


__all__ = [
    "Config",
    "RateLimits",
    "InstagramApiLimits",
    "WebSocketLimits",
    "NotificationLimits",
    "DiscordWebhookLimits",
    "SchedulingLimits",
    "GmailLimits",
    "NotificationConfig",
    "ApprovalNotificationConfig",
    "PublishNotificationConfig",
    "RetryConfig",
    "RetryDefaults",
    "AnalyticsConfig",
    "CollectionInterval",
    "UTMConfig",
    "AttributionConfig",
    "QualityScoringConfig",
    "CTRScale",
    "ConversionScale",
    "FeedbackLoopConfig",
    "AgentSchedulerConfig",
    "CalendarConfig",
    "DegradationConfig",
    "get_config",
    "reload_config",
]
