"""Tests for ClaimsAlertBatcher.

Story 6-4, Task 3: Alert batcher tests.
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import patch

import pytest

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from teams.dawo.scanners.claims_alerts.batcher import ClaimsAlertBatcher
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig


@pytest.fixture
def batcher(alert_config: ClaimsAlertConfig) -> ClaimsAlertBatcher:
    return ClaimsAlertBatcher(config=alert_config)


@pytest.fixture
def sample_event() -> RegulatoryEvent:
    return RegulatoryEvent(
        event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
        claim_id="CLAIM-001",
        substance="Beta-glucans",
        severity="low",
    )


class TestAddEvent:
    """Tests for add_event()."""

    def test_returns_false_when_within_batch_window(
        self, batcher: ClaimsAlertBatcher, sample_event: RegulatoryEvent
    ) -> None:
        """add_event returns False when batch window hasn't expired."""
        result = batcher.add_event(sample_event)
        assert result is False

    def test_returns_true_when_batch_window_expired(
        self, batcher: ClaimsAlertBatcher, sample_event: RegulatoryEvent
    ) -> None:
        """add_event returns True when batch window has expired."""
        # Add first event — starts batch window
        batcher.add_event(sample_event)

        # Simulate time passing beyond batch window
        batcher._batch_start = datetime.now(UTC) - timedelta(seconds=301)

        # Add second event — window expired
        result = batcher.add_event(sample_event)
        assert result is True


class TestGetAndClearBatch:
    """Tests for get_and_clear_batch()."""

    def test_returns_all_events_and_resets(
        self, batcher: ClaimsAlertBatcher, sample_event: RegulatoryEvent
    ) -> None:
        """get_and_clear_batch returns events and resets state."""
        batcher.add_event(sample_event)
        batcher.add_event(sample_event)

        events = batcher.get_and_clear_batch()
        assert len(events) == 2
        assert batcher.has_pending() is False

    def test_returns_empty_list_when_no_events(
        self, batcher: ClaimsAlertBatcher
    ) -> None:
        """get_and_clear_batch returns empty list when no events."""
        events = batcher.get_and_clear_batch()
        assert events == []


class TestFlushIfExpired:
    """Tests for flush_if_expired()."""

    def test_returns_none_when_not_expired(
        self, batcher: ClaimsAlertBatcher, sample_event: RegulatoryEvent
    ) -> None:
        """flush_if_expired returns None when batch window hasn't expired."""
        batcher.add_event(sample_event)
        result = batcher.flush_if_expired()
        assert result is None

    def test_returns_events_when_expired(
        self, batcher: ClaimsAlertBatcher, sample_event: RegulatoryEvent
    ) -> None:
        """flush_if_expired returns events when batch window has expired."""
        batcher.add_event(sample_event)
        batcher._batch_start = datetime.now(UTC) - timedelta(seconds=301)
        result = batcher.flush_if_expired()
        assert result is not None
        assert len(result) == 1

    def test_returns_none_when_no_events(
        self, batcher: ClaimsAlertBatcher
    ) -> None:
        """flush_if_expired returns None when no pending events."""
        result = batcher.flush_if_expired()
        assert result is None


class TestHasPending:
    """Tests for has_pending()."""

    def test_no_pending_initially(self, batcher: ClaimsAlertBatcher) -> None:
        """No pending events initially."""
        assert batcher.has_pending() is False

    def test_pending_after_add(
        self, batcher: ClaimsAlertBatcher, sample_event: RegulatoryEvent
    ) -> None:
        """has_pending True after adding event."""
        batcher.add_event(sample_event)
        assert batcher.has_pending() is True
