"""Tests for ExecutionEventEmitter.

Story 7-8, Task 6.4: Event emitter tests.
Target: 10+ tests.
"""

import asyncio

import pytest

from core.scheduling.execution_events import (
    ExecutionEvent,
    ExecutionEventEmitter,
    ExecutionEventType,
    get_execution_events,
)


class TestExecutionEventType:
    """Tests for ExecutionEventType enum."""

    def test_started_value(self):
        """STARTED has expected string value."""
        assert ExecutionEventType.STARTED.value == "execution_started"

    def test_completed_value(self):
        """COMPLETED has expected string value."""
        assert ExecutionEventType.COMPLETED.value == "execution_completed"

    def test_failed_value(self):
        """FAILED has expected string value."""
        assert ExecutionEventType.FAILED.value == "execution_failed"


class TestExecutionEvent:
    """Tests for ExecutionEvent dataclass."""

    def test_create_with_required_fields(self):
        """Event created with required fields."""
        event = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            agent_name="health_claims_monitor",
            execution_id="test-id",
        )
        assert event.event_type == ExecutionEventType.STARTED
        assert event.agent_name == "health_claims_monitor"
        assert event.execution_id == "test-id"
        assert event.data == {}
        assert event.timestamp is not None
        assert event.event_id is not None

    def test_to_dict_serialization(self):
        """to_dict() produces JSON-serializable dict."""
        event = ExecutionEvent(
            event_type=ExecutionEventType.COMPLETED,
            agent_name="novel_food_monitor",
            execution_id="log-123",
            data={"items_processed": 42},
        )
        d = event.to_dict()
        assert d["event_type"] == "execution_completed"
        assert d["agent_name"] == "novel_food_monitor"
        assert d["execution_id"] == "log-123"
        assert d["data"]["items_processed"] == 42
        assert "timestamp" in d
        assert "event_id" in d

    def test_unique_event_ids(self):
        """Each event gets a unique event_id."""
        e1 = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            agent_name="a",
            execution_id="1",
        )
        e2 = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            agent_name="a",
            execution_id="1",
        )
        assert e1.event_id != e2.event_id


class TestExecutionEventEmitter:
    """Tests for ExecutionEventEmitter class."""

    @pytest.mark.asyncio
    async def test_emit_to_zero_subscribers(self):
        """Emit to zero subscribers succeeds without error."""
        emitter = ExecutionEventEmitter()
        event = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            agent_name="test",
            execution_id="1",
        )
        await emitter.emit(event)  # Should not raise

    @pytest.mark.asyncio
    async def test_emit_to_one_subscriber(self):
        """Emit delivers event to single subscriber."""
        emitter = ExecutionEventEmitter()
        received = []

        async def consumer():
            async for event in emitter.subscribe():
                received.append(event)
                break  # Only consume one

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.01)  # Let subscriber start

        event = ExecutionEvent(
            event_type=ExecutionEventType.COMPLETED,
            agent_name="test_agent",
            execution_id="log-1",
            data={"status": "success"},
        )
        await emitter.emit(event)
        await asyncio.sleep(0.01)  # Let consumer process

        assert len(received) == 1
        assert received[0].agent_name == "test_agent"
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_same_event(self):
        """Multiple subscribers all receive the same event."""
        emitter = ExecutionEventEmitter()
        received_1 = []
        received_2 = []

        async def consumer_1():
            async for event in emitter.subscribe():
                received_1.append(event)
                break

        async def consumer_2():
            async for event in emitter.subscribe():
                received_2.append(event)
                break

        t1 = asyncio.create_task(consumer_1())
        t2 = asyncio.create_task(consumer_2())
        await asyncio.sleep(0.01)

        event = ExecutionEvent(
            event_type=ExecutionEventType.FAILED,
            agent_name="failing_agent",
            execution_id="log-2",
        )
        await emitter.emit(event)
        await asyncio.sleep(0.01)

        assert len(received_1) == 1
        assert len(received_2) == 1
        assert received_1[0].execution_id == received_2[0].execution_id

        for t in [t1, t2]:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_queue_full_drops_event(self):
        """Full queue drops event without error."""
        emitter = ExecutionEventEmitter()
        emitter.MAX_QUEUE_SIZE = 2  # Small queue for test

        # Subscribe but don't consume
        sub_gen = emitter.subscribe()
        # Start the generator to register subscription
        task = asyncio.create_task(sub_gen.__anext__())
        await asyncio.sleep(0.01)

        # Fill the queue beyond capacity
        for i in range(5):
            event = ExecutionEvent(
                event_type=ExecutionEventType.STARTED,
                agent_name="agent",
                execution_id=f"log-{i}",
            )
            await emitter.emit(event)  # Should not raise even when full

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_max_subscribers_limit(self):
        """Rejects new subscribers when at max."""
        emitter = ExecutionEventEmitter()
        emitter.MAX_SUBSCRIBERS = 2

        tasks = []
        for _ in range(3):
            async def consume():
                async for event in emitter.subscribe():
                    break

            tasks.append(asyncio.create_task(consume()))

        await asyncio.sleep(0.01)
        # Third subscriber should be rejected — subscriber_count stays at 2
        assert emitter.subscriber_count <= 2

        for t in tasks:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

    def test_subscriber_count_initially_zero(self):
        """New emitter has zero subscribers."""
        emitter = ExecutionEventEmitter()
        assert emitter.subscriber_count == 0


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_execution_events_returns_same_instance(self):
        """get_execution_events returns same instance on repeated calls."""
        e1 = get_execution_events()
        e2 = get_execution_events()
        assert e1 is e2

    def test_singleton_is_execution_event_emitter(self):
        """Singleton is ExecutionEventEmitter instance."""
        e = get_execution_events()
        assert isinstance(e, ExecutionEventEmitter)
