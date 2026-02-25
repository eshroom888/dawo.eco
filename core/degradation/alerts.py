"""Degradation alert service for Discord notifications.

Story 7-10, Task 3.1: Rate-limited degradation alerts.

Sends alerts when services transition to degraded/unhealthy status,
recovery alerts when services come back, and periodic status summaries.

All methods are resilient — Discord/Redis failures return False, never raise.
Discord-about-Discord self-alert loops are prevented.

Usage:
    service = DegradationAlertService(config, registry, discord, redis)
    await service.on_service_degraded("instagram", "Timeout", 5, 3)
    await service.on_service_recovered("instagram", queued_count=3)
    await service.send_status_summary()
"""

import logging

from core.config import DegradationConfig

logger = logging.getLogger(__name__)

# Redis key prefix for degradation alert cooldowns
ALERT_COOLDOWN_PREFIX = "dawo:degradation_alert_cooldown"


class DegradationAlertService:
    """Rate-limited Discord alerting for service degradation.

    Wraps the existing DiscordAlertManager with degradation-specific
    behavior: severity-based formatting, cooldown enforcement, recovery
    alerts, and self-alert loop prevention.

    Attributes:
        _config: DegradationConfig with cooldown settings
        _registry: ServiceHealthRegistry for status queries
        _discord: DiscordAlertManager with send capabilities
        _redis: Async Redis client for cooldown tracking
    """

    def __init__(self, config: DegradationConfig, registry, discord, redis) -> None:
        """Initialize with injected dependencies.

        Args:
            config: DegradationConfig with alert_cooldown_seconds
            registry: ServiceHealthRegistry for status queries
            discord: Discord client with send_webhook method (DiscordClientProtocol)
            redis: Async Redis client for cooldown tracking
        """
        self._config = config
        self._registry = registry
        self._discord = discord
        self._redis = redis

    async def on_service_degraded(
        self,
        service_name: str,
        error: str,
        consecutive_failures: int,
        queued_count: int,
    ) -> bool:
        """Send alert when a service becomes degraded or unhealthy.

        Rate-limited: max 1 alert per service per alert_cooldown_seconds.
        Self-alert loop: if service_name is "discord", log locally instead.

        Args:
            service_name: Service that degraded (e.g., "instagram")
            error: Error message from the failure
            consecutive_failures: Current consecutive failure count
            queued_count: Number of queued operations for this service

        Returns:
            True if alert sent, False if cooldown/skipped/failed
        """
        # Prevent Discord-about-Discord self-alert loop
        if service_name == "discord":
            logger.warning(
                "Service '%s' is degraded (%d failures: %s) — cannot alert via Discord about Discord",
                service_name,
                consecutive_failures,
                error,
            )
            return False

        try:
            # Check cooldown
            cooldown_key = f"{ALERT_COOLDOWN_PREFIX}:{service_name}"
            if await self._redis.exists(cooldown_key):
                logger.debug("Degradation alert for %s is rate-limited, skipping", service_name)
                return False

            # Determine severity
            severity = "Unhealthy" if consecutive_failures >= self._config.unhealthy_threshold else "Degraded"
            emoji = "🔴" if severity == "Unhealthy" else "⚠️"

            message = self._format_degraded_alert(
                service_name, error, consecutive_failures, queued_count, severity, emoji
            )

            await self._discord.send_webhook(message)
            await self._redis.setex(cooldown_key, self._config.alert_cooldown_seconds, "1")

            logger.info("Sent degradation alert for %s (%s)", service_name, severity)
            return True

        except Exception as e:
            logger.warning("Failed to send degradation alert for %s: %s", service_name, e)
            return False

    async def on_service_recovered(self, service_name: str, queued_count: int) -> bool:
        """Send recovery alert when a service comes back online.

        Always sends (no cooldown) to ensure operators know about recovery.
        Self-alert loop: if service_name is "discord", skip.

        Args:
            service_name: Service that recovered
            queued_count: Number of queued operations to process

        Returns:
            True if alert sent, False if skipped/failed
        """
        # Prevent Discord-about-Discord self-alert loop
        if service_name == "discord":
            logger.info(
                "Service '%s' recovered — cannot send recovery alert via Discord about Discord",
                service_name,
            )
            return False

        try:
            message = self._format_recovery_alert(service_name, queued_count)
            await self._discord.send_webhook(message)

            logger.info("Sent recovery alert for %s", service_name)
            return True

        except Exception as e:
            logger.warning("Failed to send recovery alert for %s: %s", service_name, e)
            return False

    async def send_status_summary(self) -> bool:
        """Send aggregate status summary of all monitored services.

        Intended for periodic reporting (e.g., daily status digest).

        Returns:
            True if summary sent, False if failed
        """
        try:
            statuses = await self._registry.get_all_statuses()
            message = self._format_status_summary(statuses)
            await self._discord.send_webhook(message)

            logger.info("Sent status summary for %d services", len(statuses))
            return True

        except Exception as e:
            logger.warning("Failed to send status summary: %s", e)
            return False

    def _format_degraded_alert(
        self,
        service_name: str,
        error: str,
        consecutive_failures: int,
        queued_count: int,
        severity: str,
        emoji: str,
    ) -> str:
        """Format degradation alert message."""
        queued_line = f"\n• **Queued Operations:** {queued_count}" if queued_count > 0 else ""

        return f"""{emoji} **Service {severity}: {service_name.upper()}**

• **Error:** {error}
• **Consecutive Failures:** {consecutive_failures}{queued_line}

---
_DAWO Degradation Monitor_"""

    def _format_recovery_alert(self, service_name: str, queued_count: int) -> str:
        """Format recovery alert message."""
        queued_line = (
            f"\n• **Queued Operations:** {queued_count} (processing automatically)"
            if queued_count > 0
            else ""
        )

        return f"""✅ **Service Recovered: {service_name.upper()}**

• **Status:** Healthy{queued_line}

---
_DAWO Degradation Monitor_"""

    def _format_status_summary(self, statuses: list) -> str:
        """Format aggregate status summary message."""
        status_icons = {"healthy": "🟢", "degraded": "🟡", "unhealthy": "🔴"}

        lines = []
        for s in statuses:
            icon = status_icons.get(s.status, "⚪")
            detail = f" ({s.consecutive_failures} failures)" if s.consecutive_failures > 0 else ""
            lines.append(f"• {icon} **{s.service_name}**: {s.status}{detail}")

        services_text = "\n".join(lines) if lines else "• No monitored services"

        return f"""📊 **DAWO Service Health Summary**

{services_text}

---
_DAWO Degradation Monitor_"""
