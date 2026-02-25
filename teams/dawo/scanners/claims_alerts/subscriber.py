"""Regulatory Alert Subscriber.

Epic 6, Story 6-4, Task 6: Subscribe to regulatory events and route to alert service.

Connects the RegulatoryEventEmitter (from Stories 6-1/6-2/6-3) to the
ClaimsAlertService for operator alerting via Discord.
"""

import asyncio
import logging

from core.regulatory.events import RegulatoryEventEmitter
from teams.dawo.scanners.claims_alerts.service import ClaimsAlertService

logger = logging.getLogger(__name__)


class RegulatoryAlertSubscriber:
    """Subscribes to regulatory events and routes to alert service.

    Manages the event loop subscription lifecycle, including graceful
    shutdown with batch flushing.

    Attributes:
        _service: Claims alert service for event processing
        _emitter: Regulatory event emitter for subscription
        _running: Whether subscriber is active
        _task: Background subscription task
    """

    def __init__(
        self,
        service: ClaimsAlertService,
        event_emitter: RegulatoryEventEmitter,
    ) -> None:
        """Initialize subscriber.

        Args:
            service: Claims alert service for event processing
            event_emitter: Regulatory event emitter for subscription
        """
        self._service = service
        self._emitter = event_emitter
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Subscribe to regulatory events and route to service.

        Subscribes to the event emitter's async generator and processes
        each event through the alert service. Runs until stop() is called.
        """
        self._running = True
        logger.info("RegulatoryAlertSubscriber started")

        try:
            async for event in self._emitter.subscribe():
                if not self._running:
                    break

                try:
                    result = await self._service.handle_event(event)
                    logger.info(
                        "Processed event %s -> %s",
                        event.event_type.value,
                        result.status.value,
                    )
                except Exception as e:
                    logger.error(
                        "Error processing event %s: %s",
                        event.event_id,
                        e,
                    )
                    # Continue — never crash the subscriber loop
        except asyncio.CancelledError:
            logger.info("Subscriber cancelled")
        except Exception as e:
            logger.error("Subscriber error: %s", e)
        finally:
            logger.info("RegulatoryAlertSubscriber stopped")

    async def stop(self) -> None:
        """Flush pending batch and stop subscriber.

        Ensures no events are lost by flushing the pending batch
        before shutting down.
        """
        self._running = False
        logger.info("Stopping RegulatoryAlertSubscriber, flushing pending batch")

        try:
            result = await self._service.flush_pending()
            if result.events_processed > 0:
                logger.info(
                    "Flushed %d pending events on shutdown",
                    result.events_processed,
                )
        except Exception as e:
            logger.error("Error flushing pending batch on shutdown: %s", e)

        # Cancel the background task if running
        if self._task and not self._task.done():
            self._task.cancel()


__all__ = [
    "RegulatoryAlertSubscriber",
]
