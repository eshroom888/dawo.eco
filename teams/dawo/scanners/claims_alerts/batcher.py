"""Claims Alert Batcher.

Epic 6, Story 6-4, Task 3: In-memory time-window batching.

Batches regulatory events within a configurable time window to avoid
spamming the Discord channel during monitoring cycles. Uses in-memory
storage since regulatory monitors run infrequently in the same process.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional

from core.regulatory.events import RegulatoryEvent
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig

logger = logging.getLogger(__name__)


class ClaimsAlertBatcher:
    """Batches regulatory events within a time window.

    Events are collected in memory and flushed when the batch window
    expires or when explicitly flushed (e.g., on shutdown).

    Attributes:
        _batch: List of pending events
        _batch_start: Timestamp when first event was added to current batch
        _window: Batch window duration
    """

    def __init__(self, config: ClaimsAlertConfig) -> None:
        """Initialize batcher with config.

        Args:
            config: Claims alert configuration
        """
        self._batch: list[RegulatoryEvent] = []
        self._batch_start: Optional[datetime] = None
        self._window = timedelta(seconds=config.batch_window_seconds)

    def add_event(self, event: RegulatoryEvent) -> bool:
        """Add event to batch.

        Args:
            event: Regulatory event to batch

        Returns:
            True if batch window has expired and should be flushed,
            False if event was added within the current window
        """
        now = datetime.now(UTC)

        # Check if window expired before adding
        window_expired = (
            self._batch_start is not None
            and (now - self._batch_start) >= self._window
        )

        # Add event to batch
        self._batch.append(event)

        # Start window on first event
        if self._batch_start is None:
            self._batch_start = now

        if window_expired:
            logger.debug(
                "Batch window expired with %d events, flush recommended",
                len(self._batch),
            )

        return window_expired

    def get_and_clear_batch(self) -> list[RegulatoryEvent]:
        """Return all batched events and reset state.

        Returns:
            List of all pending events (may be empty)
        """
        events = list(self._batch)
        self._batch.clear()
        self._batch_start = None
        logger.debug("Batch cleared, returned %d events", len(events))
        return events

    def has_pending(self) -> bool:
        """Check if batch has unflushed events.

        Returns:
            True if there are pending events
        """
        return len(self._batch) > 0

    def flush_if_expired(self) -> Optional[list[RegulatoryEvent]]:
        """Flush batch if window has expired.

        Returns:
            List of events if window expired, None if not expired or empty
        """
        if not self._batch:
            return None

        now = datetime.now(UTC)
        if self._batch_start is None:
            return None

        if (now - self._batch_start) >= self._window:
            logger.debug("Batch window expired, flushing %d events", len(self._batch))
            return self.get_and_clear_batch()

        return None


__all__ = [
    "ClaimsAlertBatcher",
]
