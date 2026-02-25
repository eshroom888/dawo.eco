"""Tests for RegulatoryAlertSubscriber.

Story 6-4, Task 6: Event subscriber tests.
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.regulatory.events import (
    RegulatoryEvent,
    RegulatoryEventType,
    RegulatoryEventEmitter,
)
from teams.dawo.scanners.claims_alerts.schemas import AlertResult, AlertStatus
from teams.dawo.scanners.claims_alerts.subscriber import RegulatoryAlertSubscriber


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.handle_event = AsyncMock(
        return_value=AlertResult(status=AlertStatus.SENT, events_processed=1)
    )
    service.flush_pending = AsyncMock(
        return_value=AlertResult(status=AlertStatus.FILTERED, events_processed=0)
    )
    return service


@pytest.fixture
def emitter() -> RegulatoryEventEmitter:
    return RegulatoryEventEmitter()


@pytest.fixture
def subscriber(
    mock_service: AsyncMock,
    emitter: RegulatoryEventEmitter,
) -> RegulatoryAlertSubscriber:
    return RegulatoryAlertSubscriber(
        service=mock_service,
        event_emitter=emitter,
    )


class TestSubscriberStart:
    """Tests for start()."""

    @pytest.mark.asyncio
    async def test_receives_events_and_routes_to_service(
        self,
        subscriber: RegulatoryAlertSubscriber,
        emitter: RegulatoryEventEmitter,
        mock_service: AsyncMock,
    ) -> None:
        """Subscriber receives events and routes to service."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.NEW_CLAIM_APPROVED,
            substance="Chaga",
            severity="medium",
        )

        # Start subscriber in background
        task = asyncio.create_task(subscriber.start())

        # Allow subscription to register
        await asyncio.sleep(0.05)

        # Emit event
        await emitter.emit(event)

        # Allow processing
        await asyncio.sleep(0.05)

        # Stop subscriber
        await subscriber.stop()

        # Wait for task to finish
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.CancelledError:
            pass

        mock_service.handle_event.assert_called_once_with(event)


class TestSubscriberStop:
    """Tests for stop()."""

    @pytest.mark.asyncio
    async def test_flushes_pending_batch(
        self,
        subscriber: RegulatoryAlertSubscriber,
        mock_service: AsyncMock,
    ) -> None:
        """stop() flushes pending batch."""
        await subscriber.stop()
        mock_service.flush_pending.assert_called_once()
