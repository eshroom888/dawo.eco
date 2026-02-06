"""Integration helper for retry middleware pipeline.

This module provides a helper class that integrates all retry middleware
components together: RetryMiddleware, OperationQueue, and DiscordAlertManager.

Architecture Compliance:
- All dependencies injected via constructor
- Provides the full pipeline: retry → queue → alert
- Used by Team Builder to wire components together

Usage:
    from teams.dawo.middleware.integration import RetryPipeline

    pipeline = RetryPipeline(
        config=retry_config,
        operation_queue=queue,
        alert_manager=alert_manager,
    )
    result = await pipeline.execute("instagram_publish", api_call)
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Optional

from teams.dawo.middleware.retry import RetryConfig, RetryResult, RetryMiddleware
from teams.dawo.middleware.operation_queue import IncompleteOperation, OperationQueue
from teams.dawo.middleware.discord_alerts import DiscordAlertManager

logger = logging.getLogger(__name__)


class RetryPipeline:
    """Integrated retry pipeline with queuing and alerting.

    Combines RetryMiddleware, OperationQueue, and DiscordAlertManager
    into a single pipeline that:
    1. Executes operation with retry middleware
    2. On exhausted retries, queues for later retry
    3. Sends Discord alert for failures

    This is the recommended way to execute external API calls.
    """

    def __init__(
        self,
        config: RetryConfig,
        operation_queue: Optional[OperationQueue] = None,
        alert_manager: Optional[DiscordAlertManager] = None,
    ) -> None:
        """Initialize retry pipeline with injected dependencies.

        Args:
            config: RetryConfig for retry behavior
            operation_queue: Optional queue for incomplete operations
            alert_manager: Optional Discord alert manager
        """
        self._middleware = RetryMiddleware(config)
        self._queue = operation_queue
        self._alerts = alert_manager

    async def execute(
        self,
        context: str,
        operation: Callable[[], Any],
        payload: Optional[dict[str, Any]] = None,
    ) -> RetryResult:
        """Execute operation through the full retry pipeline.

        Pipeline flow:
        1. Execute with RetryMiddleware (exponential backoff)
        2. If incomplete → Queue for later retry (if queue available)
        3. If incomplete → Send Discord alert (if alerts available)

        Args:
            context: Operation context for logging (e.g., "instagram_publish")
            operation: Async callable to execute
            payload: Optional payload to store if queued (for later retry)

        Returns:
            RetryResult with success/failure status
        """
        # Step 1: Execute with retry middleware
        result = await self._middleware.execute_with_retry(operation, context)

        # Step 2 & 3: Handle incomplete operations
        if result.is_incomplete:
            operation_id = await self._handle_incomplete(
                context=context,
                result=result,
                payload=payload or {},
            )
            # Update result with operation_id if queued
            if operation_id:
                result.operation_id = operation_id

        return result

    async def _handle_incomplete(
        self,
        context: str,
        result: RetryResult,
        payload: dict[str, Any],
    ) -> Optional[str]:
        """Handle incomplete operation: queue and alert.

        Args:
            context: Operation context
            result: The incomplete RetryResult
            payload: Payload to store for later retry

        Returns:
            Operation ID if queued, None otherwise
        """
        operation_id: Optional[str] = None

        # Queue for later retry
        if self._queue is not None:
            try:
                operation = IncompleteOperation(
                    operation_id=str(uuid.uuid4()),
                    context=context,
                    payload=payload,
                    created_at=datetime.now(),
                    retry_count=0,
                    last_error=result.last_error,
                )
                operation_id = await self._queue.queue_for_retry(operation)
                logger.info(f"Queued incomplete operation: {operation_id}")
            except Exception as e:
                logger.warning(f"Failed to queue operation: {e}")

        # Send Discord alert
        if self._alerts is not None:
            try:
                await self._alerts.send_api_error_alert(
                    api_name=context.split("_")[0],  # Extract API name from context
                    error=result.last_error or "Unknown error",
                    attempts=result.attempts,
                    queued_for_retry=operation_id is not None,
                )
            except Exception as e:
                logger.warning(f"Failed to send Discord alert: {e}")

        return operation_id
