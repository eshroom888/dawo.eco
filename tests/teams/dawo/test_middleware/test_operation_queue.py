"""Tests for operation queue functionality (AC #2).

Tests verify:
- IncompleteOperation dataclass has required fields
- OperationQueue can queue operations for later retry
- OperationQueue can retrieve pending operations
- Redis integration (mocked)
"""

import pytest
from dataclasses import fields
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json

from teams.dawo.middleware import (
    IncompleteOperation,
    OperationQueue,
)


class TestIncompleteOperationDataclass:
    """Test IncompleteOperation dataclass structure."""

    def test_has_operation_id_field(self) -> None:
        """Should have operation_id field."""
        field_names = [f.name for f in fields(IncompleteOperation)]
        assert "operation_id" in field_names

    def test_has_context_field(self) -> None:
        """Should have context field."""
        field_names = [f.name for f in fields(IncompleteOperation)]
        assert "context" in field_names

    def test_has_payload_field(self) -> None:
        """Should have payload field."""
        field_names = [f.name for f in fields(IncompleteOperation)]
        assert "payload" in field_names

    def test_has_created_at_field(self) -> None:
        """Should have created_at field."""
        field_names = [f.name for f in fields(IncompleteOperation)]
        assert "created_at" in field_names

    def test_has_retry_count_field(self) -> None:
        """Should have retry_count field."""
        field_names = [f.name for f in fields(IncompleteOperation)]
        assert "retry_count" in field_names

    def test_creation_with_required_fields(self) -> None:
        """Should create IncompleteOperation with required fields."""
        now = datetime.now()
        op = IncompleteOperation(
            operation_id="op-123",
            context="instagram_publish",
            payload={"content_id": "abc"},
            created_at=now,
        )
        assert op.operation_id == "op-123"
        assert op.context == "instagram_publish"
        assert op.payload == {"content_id": "abc"}
        assert op.created_at == now
        assert op.retry_count == 0  # Default

    def test_optional_fields_have_defaults(self) -> None:
        """Optional fields should have sensible defaults."""
        op = IncompleteOperation(
            operation_id="op-456",
            context="discord_notify",
            payload={},
            created_at=datetime.now(),
        )
        assert op.retry_count == 0
        assert op.last_attempt is None
        assert op.last_error is None


class TestOperationQueueInit:
    """Test OperationQueue initialization."""

    def test_accepts_redis_client_via_injection(self) -> None:
        """Should accept Redis client via constructor injection."""
        mock_redis = MagicMock()
        queue = OperationQueue(mock_redis)
        assert queue is not None

    def test_uses_correct_queue_key(self) -> None:
        """Should use the correct Redis key for the queue."""
        mock_redis = MagicMock()
        queue = OperationQueue(mock_redis)
        assert queue.QUEUE_KEY == "dawo:incomplete_operations"


class TestQueueForRetry:
    """Test queue_for_retry method."""

    @pytest.mark.asyncio
    async def test_queues_operation_to_redis(self) -> None:
        """Should store operation in Redis hash."""
        mock_redis = AsyncMock()
        queue = OperationQueue(mock_redis)

        op = IncompleteOperation(
            operation_id="op-789",
            context="shopify_api",
            payload={"product_id": "123"},
            created_at=datetime(2026, 2, 6, 12, 0, 0),
        )

        result = await queue.queue_for_retry(op)

        assert result == "op-789"
        mock_redis.hset.assert_called_once()
        # Verify it was called with correct key and operation_id
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == "dawo:incomplete_operations"
        assert call_args[0][1] == "op-789"

    @pytest.mark.asyncio
    async def test_serializes_operation_to_json(self) -> None:
        """Should serialize operation as JSON."""
        mock_redis = AsyncMock()
        queue = OperationQueue(mock_redis)

        op = IncompleteOperation(
            operation_id="op-serialize",
            context="test",
            payload={"key": "value"},
            created_at=datetime(2026, 2, 6, 12, 0, 0),
        )

        await queue.queue_for_retry(op)

        # Get the JSON that was stored
        call_args = mock_redis.hset.call_args
        stored_json = call_args[0][2]
        stored_data = json.loads(stored_json)

        assert stored_data["operation_id"] == "op-serialize"
        assert stored_data["context"] == "test"
        assert stored_data["payload"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_returns_operation_id(self) -> None:
        """Should return the operation ID."""
        mock_redis = AsyncMock()
        queue = OperationQueue(mock_redis)

        op = IncompleteOperation(
            operation_id="op-return-test",
            context="test",
            payload={},
            created_at=datetime.now(),
        )

        result = await queue.queue_for_retry(op)
        assert result == "op-return-test"


class TestGetPendingOperations:
    """Test get_pending_operations method."""

    @pytest.mark.asyncio
    async def test_retrieves_all_pending_operations(self) -> None:
        """Should retrieve all operations from Redis hash."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            "op-1": json.dumps({
                "operation_id": "op-1",
                "context": "instagram",
                "payload": {},
                "created_at": "2026-02-06T12:00:00",
                "retry_count": 0,
                "last_attempt": None,
                "last_error": None,
            }),
            "op-2": json.dumps({
                "operation_id": "op-2",
                "context": "discord",
                "payload": {"msg": "test"},
                "created_at": "2026-02-06T13:00:00",
                "retry_count": 1,
                "last_attempt": "2026-02-06T13:30:00",
                "last_error": "Connection error",
            }),
        }

        queue = OperationQueue(mock_redis)
        operations = await queue.get_pending_operations()

        assert len(operations) == 2
        assert operations[0].operation_id in ["op-1", "op-2"]
        assert operations[1].operation_id in ["op-1", "op-2"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_operations(self) -> None:
        """Should return empty list when no pending operations."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {}

        queue = OperationQueue(mock_redis)
        operations = await queue.get_pending_operations()

        assert operations == []

    @pytest.mark.asyncio
    async def test_deserializes_operation_correctly(self) -> None:
        """Should deserialize JSON to IncompleteOperation."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            "op-test": json.dumps({
                "operation_id": "op-test",
                "context": "orshot_api",
                "payload": {"image": "data"},
                "created_at": "2026-02-06T14:00:00",
                "retry_count": 2,
                "last_attempt": "2026-02-06T14:30:00",
                "last_error": "Timeout",
            }),
        }

        queue = OperationQueue(mock_redis)
        operations = await queue.get_pending_operations()

        op = operations[0]
        assert op.operation_id == "op-test"
        assert op.context == "orshot_api"
        assert op.payload == {"image": "data"}
        assert op.retry_count == 2
        assert op.last_error == "Timeout"


class TestRemoveFromQueue:
    """Test remove_from_queue method."""

    @pytest.mark.asyncio
    async def test_removes_operation_from_redis(self) -> None:
        """Should remove operation from Redis hash."""
        mock_redis = AsyncMock()
        queue = OperationQueue(mock_redis)

        await queue.remove_from_queue("op-remove-test")

        mock_redis.hdel.assert_called_once_with(
            "dawo:incomplete_operations",
            "op-remove-test"
        )


class TestModuleExports:
    """Test module exports."""

    def test_incomplete_operation_exported(self) -> None:
        """IncompleteOperation should be importable from middleware."""
        from teams.dawo.middleware import IncompleteOperation
        assert IncompleteOperation is not None

    def test_operation_queue_exported(self) -> None:
        """OperationQueue should be importable from middleware."""
        from teams.dawo.middleware import OperationQueue
        assert OperationQueue is not None
