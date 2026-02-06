"""Operation queue for incomplete operations using Redis.

This module provides persistence for operations that fail after all
retries are exhausted, allowing them to be retried later.

Architecture Compliance:
- Redis client is injected via constructor (NEVER connect directly)
- Uses ARQ pattern for persistence across restarts
- Supports graceful degradation - queue failures don't stop the pipeline

Usage:
    redis_client = await get_redis()  # From Team Builder
    queue = OperationQueue(redis_client)
    await queue.queue_for_retry(operation)
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class RedisClientProtocol(Protocol):
    """Protocol defining the Redis client interface for OperationQueue.

    Any class implementing this protocol can be used as a Redis client.
    This allows for easy mocking and alternative implementations.
    """

    async def hset(self, name: str, key: str, value: str) -> Any:
        """Set hash field to value."""
        ...

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get value of hash field."""
        ...

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all fields and values in hash."""
        ...

    async def hdel(self, name: str, key: str) -> int:
        """Delete hash field."""
        ...


@dataclass
class IncompleteOperation:
    """Operation queued for later retry.

    Represents an API operation that failed after exhausting retries.
    Stored in Redis for later processing.

    Attributes:
        operation_id: Unique identifier for the operation
        context: Description (e.g., "instagram_publish", "discord_notification")
        payload: Serialized operation parameters
        created_at: When the operation was first attempted
        retry_count: Number of queue retries (separate from initial retries)
        last_attempt: When the queue last tried this operation
        last_error: Error from last queue retry attempt
    """

    operation_id: str
    context: str
    payload: dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    last_attempt: Optional[datetime] = None
    last_error: Optional[str] = None


class OperationQueue:
    """Queue for incomplete operations using Redis.

    Persists failed operations for later retry processing.
    Redis client is injected - NEVER connect directly.

    Attributes:
        QUEUE_KEY: Redis hash key for storing operations
    """

    QUEUE_KEY = "dawo:incomplete_operations"

    def __init__(self, redis_client: RedisClientProtocol) -> None:
        """Initialize queue with injected Redis client.

        Args:
            redis_client: Async Redis client implementing RedisClientProtocol
        """
        self._redis = redis_client

    async def queue_for_retry(self, operation: IncompleteOperation) -> str:
        """Add operation to retry queue.

        Args:
            operation: The incomplete operation to queue

        Returns:
            The operation ID
        """
        # Serialize operation to JSON
        data = asdict(operation)
        # Convert datetime to string for JSON serialization
        data["created_at"] = data["created_at"].isoformat() if data["created_at"] else None
        data["last_attempt"] = data["last_attempt"].isoformat() if data["last_attempt"] else None

        await self._redis.hset(
            self.QUEUE_KEY,
            operation.operation_id,
            json.dumps(data)
        )
        return operation.operation_id

    async def get_pending_operations(self) -> list[IncompleteOperation]:
        """Get all pending operations for retry processing.

        Returns:
            List of IncompleteOperation instances
        """
        raw_ops = await self._redis.hgetall(self.QUEUE_KEY)

        operations = []
        for data in raw_ops.values():
            op_dict = json.loads(data)
            # Convert datetime strings back to datetime objects
            op_dict["created_at"] = (
                datetime.fromisoformat(op_dict["created_at"])
                if op_dict["created_at"]
                else None
            )
            op_dict["last_attempt"] = (
                datetime.fromisoformat(op_dict["last_attempt"])
                if op_dict["last_attempt"]
                else None
            )
            operations.append(IncompleteOperation(**op_dict))

        return operations

    async def remove_from_queue(self, operation_id: str) -> None:
        """Remove an operation from the queue.

        Called after successful retry or manual intervention.

        Args:
            operation_id: The operation ID to remove
        """
        await self._redis.hdel(self.QUEUE_KEY, operation_id)

    async def update_operation(
        self,
        operation_id: str,
        retry_count: Optional[int] = None,
        last_attempt: Optional[datetime] = None,
        last_error: Optional[str] = None,
    ) -> Optional[IncompleteOperation]:
        """Update an existing operation in the queue.

        Retrieves the operation, updates specified fields, and saves it back.
        Used to track retry attempts and errors.

        Args:
            operation_id: The operation ID to update
            retry_count: New retry count (if provided)
            last_attempt: New last attempt time (if provided)
            last_error: New last error message (if provided)

        Returns:
            Updated IncompleteOperation, or None if not found
        """
        # Retrieve existing operation
        raw_data = await self._redis.hget(self.QUEUE_KEY, operation_id)
        if raw_data is None:
            return None

        op_dict = json.loads(raw_data)

        # Convert datetime strings back to objects
        op_dict["created_at"] = (
            datetime.fromisoformat(op_dict["created_at"])
            if op_dict["created_at"]
            else None
        )
        op_dict["last_attempt"] = (
            datetime.fromisoformat(op_dict["last_attempt"])
            if op_dict["last_attempt"]
            else None
        )

        # Apply updates
        if retry_count is not None:
            op_dict["retry_count"] = retry_count
        if last_attempt is not None:
            op_dict["last_attempt"] = last_attempt
        if last_error is not None:
            op_dict["last_error"] = last_error

        # Create updated operation
        updated_op = IncompleteOperation(**op_dict)

        # Save back to Redis
        await self.queue_for_retry(updated_op)

        return updated_op

    async def increment_retry(
        self,
        operation_id: str,
        error: Optional[str] = None,
    ) -> Optional[IncompleteOperation]:
        """Convenience method to increment retry count for an operation.

        Args:
            operation_id: The operation ID
            error: Optional error message from this attempt

        Returns:
            Updated IncompleteOperation, or None if not found
        """
        # Get current operation
        raw_data = await self._redis.hget(self.QUEUE_KEY, operation_id)
        if raw_data is None:
            return None

        op_dict = json.loads(raw_data)
        current_count = op_dict.get("retry_count", 0)

        return await self.update_operation(
            operation_id=operation_id,
            retry_count=current_count + 1,
            last_attempt=datetime.now(),
            last_error=error,
        )
