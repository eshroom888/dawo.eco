"""Recovery processor for queued incomplete operations.

Story 7-10, Task 4.1: Automatic recovery processing.

When a service recovers (status returns to "healthy"), the processor
re-enqueues pending operations from the OperationQueue as ARQ jobs.

All methods are resilient — failures return zero-results, never raise.

Usage:
    processor = RecoveryProcessor(config, registry, queue, job_enqueuer)
    result = await processor.check_and_recover("instagram")
    results = await processor.process_all_services()
"""

import logging
from typing import Callable, Awaitable

from core.config import DegradationConfig
from core.degradation.models import RecoveryResult

logger = logging.getLogger(__name__)


class RecoveryProcessor:
    """Processes queued operations when services recover.

    Checks each monitored service's health status. If "healthy",
    re-enqueues pending operations (up to max_recovery_batch_size)
    via the provided job_enqueuer callable.

    Attributes:
        _config: DegradationConfig with batch size and service list
        _registry: ServiceHealthRegistry for status checks
        _queue: OperationQueue with pending operations
        _job_enqueuer: Async callable to re-enqueue an operation as ARQ job
    """

    def __init__(
        self,
        config: DegradationConfig,
        registry,
        queue,
        job_enqueuer: Callable[..., Awaitable],
    ) -> None:
        """Initialize with injected dependencies.

        Args:
            config: DegradationConfig with recovery settings
            registry: ServiceHealthRegistry for health status queries
            queue: OperationQueue with pending operations
            job_enqueuer: Async function to re-enqueue an operation (e.g., ARQ enqueue)
        """
        self._config = config
        self._registry = registry
        self._queue = queue
        self._job_enqueuer = job_enqueuer

    async def check_and_recover(self, service_name: str) -> RecoveryResult:
        """Check if a service is healthy and process its pending operations.

        Only processes operations whose context starts with the service_name.
        Processes up to max_recovery_batch_size operations per call.

        Args:
            service_name: Service to check and recover (e.g., "instagram")

        Returns:
            RecoveryResult with processed count, remaining count, and errors
        """
        try:
            status = await self._registry.get_status(service_name)

            if status.status != "healthy":
                logger.debug(
                    "Service %s is %s — skipping recovery",
                    service_name,
                    status.status,
                )
                return RecoveryResult(service_name=service_name)

            # Get pending operations for this service
            service_ops = await self._queue.get_operations_for_service(service_name)

            if not service_ops:
                return RecoveryResult(service_name=service_name)

            # Process up to max_recovery_batch_size
            batch = service_ops[: self._config.max_recovery_batch_size]
            remaining = len(service_ops) - len(batch)

            processed = 0
            errors = []

            for op in batch:
                try:
                    await self._job_enqueuer(op)
                    await self._queue.remove_from_queue(op.operation_id)
                    processed += 1
                except Exception as e:
                    error_msg = f"Failed to enqueue {op.operation_id}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

            if processed > 0:
                logger.info(
                    "Recovery for %s: processed=%d, remaining=%d, errors=%d",
                    service_name,
                    processed,
                    remaining,
                    len(errors),
                )

            return RecoveryResult(
                service_name=service_name,
                processed=processed,
                remaining=remaining,
                errors=errors,
            )

        except Exception as e:
            logger.warning("Recovery check failed for %s: %s", service_name, e)
            return RecoveryResult(service_name=service_name)

    async def process_all_services(self) -> list[RecoveryResult]:
        """Check and recover all monitored services.

        Returns:
            List of RecoveryResult for each monitored service
        """
        results = []
        for service_name in self._config.monitored_services:
            result = await self.check_and_recover(service_name)
            results.append(result)
        return results
