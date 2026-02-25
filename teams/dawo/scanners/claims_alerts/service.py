"""Claims Alert Service.

Epic 6, Story 6-4, Task 5: Alert processing orchestrator.

Coordinates event filtering, batching, formatting, and sending.
Routes regulatory events through the alert pipeline:
1. Check enabled
2. Check relevance filter
3. Immediate send for CRITICAL/HIGH enforcement, batch others
4. On flush: format and send via Discord
5. On failure: queue for retry
"""

import logging
from typing import Protocol, runtime_checkable

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from integrations.discord import DiscordClientProtocol, DiscordEmbed
from teams.dawo.scanners.claims_alerts.batcher import ClaimsAlertBatcher
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig
from teams.dawo.scanners.claims_alerts.formatter import ClaimsAlertFormatter
from teams.dawo.scanners.claims_alerts.relevance_filter import DAWORelevanceFilter
from teams.dawo.scanners.claims_alerts.schemas import AlertResult, AlertStatus

logger = logging.getLogger(__name__)

# Event types + severities that bypass batching
_IMMEDIATE_SEND_TYPES = {
    RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
}
_IMMEDIATE_SEND_SEVERITIES = {"critical", "high"}


@runtime_checkable
class NotificationQueueProtocol(Protocol):
    """Protocol for notification queue interaction.

    Abstracts the queue backend (Redis/in-memory) for testability.
    """

    async def queue_failed(self, data: dict) -> None:
        """Queue a failed alert for retry."""
        ...

    async def retry_failed(self) -> int:
        """Process and retry failed notifications."""
        ...


class ClaimsAlertService:
    """Orchestrates regulatory event alerting.

    Coordinates filtering, batching, formatting, and sending of
    regulatory alerts to Discord.

    Attributes:
        _discord: Discord client for sending embeds
        _formatter: Formats events as Discord embeds
        _batcher: Batches events within time window
        _filter: Filters events by DAWO product relevance
        _queue: Notification queue for retry on failure
        _config: Alert configuration
    """

    def __init__(
        self,
        discord_client: DiscordClientProtocol,
        formatter: ClaimsAlertFormatter,
        batcher: ClaimsAlertBatcher,
        relevance_filter: DAWORelevanceFilter,
        notification_queue: NotificationQueueProtocol,
        config: ClaimsAlertConfig,
    ) -> None:
        """Initialize service with all dependencies.

        Args:
            discord_client: Discord client for sending alerts
            formatter: Event-to-embed formatter
            batcher: Event batcher for time-window grouping
            relevance_filter: DAWO product relevance filter
            notification_queue: Queue for retry on send failure
            config: Alert configuration
        """
        self._discord = discord_client
        self._formatter = formatter
        self._batcher = batcher
        self._filter = relevance_filter
        self._queue = notification_queue
        self._config = config

    async def handle_event(self, event: RegulatoryEvent) -> AlertResult:
        """Process a regulatory event for alerting.

        Args:
            event: Regulatory event to process

        Returns:
            AlertResult with processing status
        """
        # Check enabled
        if not self._config.enabled:
            logger.debug("Alerting disabled, skipping event %s", event.event_id)
            return AlertResult(status=AlertStatus.FILTERED, events_processed=1)

        # Check relevance
        if not self._filter.is_relevant(event):
            logger.debug(
                "Event %s filtered — not relevant to DAWO products",
                event.event_id,
            )
            return AlertResult(status=AlertStatus.FILTERED, events_processed=1)

        # Immediate send for enforcement with CRITICAL/HIGH severity
        if self._should_send_immediately(event):
            logger.info(
                "Immediate send for %s event (severity=%s)",
                event.event_type.value,
                event.severity,
            )
            embed = self._formatter.format_enforcement_alert(event)
            success = await self._send_alert(embed)
            if success:
                return AlertResult(status=AlertStatus.SENT, events_processed=1)
            else:
                await self._queue_for_retry(embed, "Discord send failed")
                return AlertResult(
                    status=AlertStatus.QUEUED_FOR_RETRY,
                    events_processed=1,
                    errors=["Discord send failed, queued for retry"],
                )

        # Batch non-urgent events
        should_flush = self._batcher.add_event(event)

        if should_flush:
            # Batch window expired — flush
            return await self._flush_batch()

        logger.debug(
            "Event %s batched (window active)", event.event_id,
        )
        return AlertResult(
            status=AlertStatus.BATCHED,
            events_processed=1,
            events_batched=1,
        )

    async def flush_pending(self) -> AlertResult:
        """Force-flush any pending batch.

        Used for shutdown/cleanup to ensure no events are lost.

        Returns:
            AlertResult with flush status
        """
        if not self._batcher.has_pending():
            return AlertResult(status=AlertStatus.FILTERED, events_processed=0)

        return await self._flush_batch()

    async def _flush_batch(self) -> AlertResult:
        """Flush the current batch and send as embed.

        Returns:
            AlertResult with send status
        """
        events = self._batcher.get_and_clear_batch()
        if not events:
            return AlertResult(status=AlertStatus.FILTERED, events_processed=0)

        # Format as single or batch embed
        if len(events) == 1:
            embed = self._formatter.format_claim_alert(events[0])
        else:
            embed = self._formatter.format_batch_alert(events)

        success = await self._send_alert(embed)
        if success:
            logger.info("Sent alert for %d events", len(events))
            return AlertResult(
                status=AlertStatus.SENT,
                events_processed=len(events),
            )
        else:
            await self._queue_for_retry(embed, "Discord send failed (batch)")
            return AlertResult(
                status=AlertStatus.QUEUED_FOR_RETRY,
                events_processed=len(events),
                errors=["Discord send failed, queued for retry"],
            )

    async def _send_alert(self, embed: DiscordEmbed) -> bool:
        """Send embed via Discord client with error handling.

        Args:
            embed: Discord embed to send

        Returns:
            True if sent successfully
        """
        try:
            return await self._discord.send_embed(embed)
        except Exception as e:
            logger.error("Failed to send Discord alert: %s", e)
            return False

    async def _queue_for_retry(self, embed: DiscordEmbed, error: str) -> None:
        """Queue a failed alert for retry.

        Args:
            embed: The embed that failed to send
            error: Error description
        """
        try:
            await self._queue.queue_failed({
                "embed": embed.to_dict(),
                "error": error,
                "webhook_url": self._config.webhook_url,
            })
            logger.info("Alert queued for retry: %s", error)
        except Exception as e:
            logger.error("Failed to queue alert for retry: %s", e)

    def _should_send_immediately(self, event: RegulatoryEvent) -> bool:
        """Check if event should bypass batcher and send immediately.

        Args:
            event: Regulatory event

        Returns:
            True if event should be sent immediately
        """
        if event.event_type in _IMMEDIATE_SEND_TYPES:
            return True
        if event.severity.lower() in _IMMEDIATE_SEND_SEVERITIES:
            return True
        return False


__all__ = [
    "ClaimsAlertService",
    "NotificationQueueProtocol",
]
