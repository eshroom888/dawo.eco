"""Tests for RecoveryProcessor.

Story 7-10, Task 4.4: Recovery processing tests.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from core.config import DegradationConfig
from core.degradation.models import ServiceHealthStatus, RecoveryResult
from core.degradation.recovery import RecoveryProcessor
from teams.dawo.middleware.operation_queue import IncompleteOperation


@pytest.fixture
def config():
    """DegradationConfig with small batch for tests."""
    return DegradationConfig(max_recovery_batch_size=3)


@pytest.fixture
def registry_mock():
    """Mock ServiceHealthRegistry."""
    mock = AsyncMock()
    mock.get_status = AsyncMock()
    return mock


@pytest.fixture
def queue_mock():
    """Mock OperationQueue."""
    mock = AsyncMock()
    mock.get_operations_for_service = AsyncMock(return_value=[])
    mock.remove_from_queue = AsyncMock()
    return mock


@pytest.fixture
def job_enqueuer_mock():
    """Mock job enqueuer function."""
    return AsyncMock()


@pytest.fixture
def processor(config, registry_mock, queue_mock, job_enqueuer_mock):
    """RecoveryProcessor with all mocks."""
    return RecoveryProcessor(
        config=config,
        registry=registry_mock,
        queue=queue_mock,
        job_enqueuer=job_enqueuer_mock,
    )


def _make_operation(op_id: str, context: str) -> IncompleteOperation:
    """Helper to create test IncompleteOperation."""
    return IncompleteOperation(
        operation_id=op_id,
        context=context,
        payload={"test": True},
        created_at=datetime.now(UTC),
    )


class TestCheckAndRecover:
    """Tests for check_and_recover method."""

    @pytest.mark.asyncio
    async def test_processes_pending_operations_for_healthy_service(
        self, processor, registry_mock, queue_mock, job_enqueuer_mock
    ):
        """check_and_recover processes pending operations when service is healthy."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram", status="healthy"
        )
        queue_mock.get_operations_for_service.return_value = [
            _make_operation("op-1", "instagram_publish"),
            _make_operation("op-2", "instagram_metrics"),
        ]

        result = await processor.check_and_recover("instagram")

        assert result.service_name == "instagram"
        assert result.processed == 2
        assert result.remaining == 0
        assert result.errors == []
        assert job_enqueuer_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_skips_degraded_service(self, processor, registry_mock, job_enqueuer_mock):
        """check_and_recover skips services that are still degraded."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="shopify", status="degraded", consecutive_failures=5
        )

        result = await processor.check_and_recover("shopify")

        assert result.service_name == "shopify"
        assert result.processed == 0
        assert result.remaining == 0
        job_enqueuer_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_unhealthy_service(self, processor, registry_mock, job_enqueuer_mock):
        """check_and_recover skips services that are unhealthy."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram", status="unhealthy", consecutive_failures=15
        )

        result = await processor.check_and_recover("instagram")

        assert result.processed == 0
        job_enqueuer_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_respects_max_batch_size(
        self, processor, registry_mock, queue_mock, job_enqueuer_mock
    ):
        """check_and_recover processes at most max_recovery_batch_size operations."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram", status="healthy"
        )
        # 5 operations, but max_recovery_batch_size=3
        queue_mock.get_operations_for_service.return_value = [
            _make_operation(f"op-{i}", "instagram_publish") for i in range(5)
        ]

        result = await processor.check_and_recover("instagram")

        assert result.processed == 3
        assert result.remaining == 2
        assert job_enqueuer_mock.await_count == 3

    @pytest.mark.asyncio
    async def test_delegates_service_filtering_to_queue(
        self, processor, registry_mock, queue_mock, job_enqueuer_mock
    ):
        """check_and_recover delegates service filtering to OperationQueue."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram", status="healthy"
        )
        queue_mock.get_operations_for_service.return_value = [
            _make_operation("op-1", "instagram_publish"),
            _make_operation("op-3", "instagram_metrics"),
        ]

        result = await processor.check_and_recover("instagram")

        queue_mock.get_operations_for_service.assert_awaited_once_with("instagram")
        assert result.processed == 2
        assert result.remaining == 0
        assert job_enqueuer_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_removes_processed_operations(
        self, processor, registry_mock, queue_mock, job_enqueuer_mock
    ):
        """check_and_recover removes successfully enqueued operations from queue."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram", status="healthy"
        )
        queue_mock.get_operations_for_service.return_value = [
            _make_operation("op-1", "instagram_publish"),
        ]

        await processor.check_and_recover("instagram")

        queue_mock.remove_from_queue.assert_awaited_once_with("op-1")

    @pytest.mark.asyncio
    async def test_handles_enqueue_failure(
        self, processor, registry_mock, queue_mock, job_enqueuer_mock
    ):
        """check_and_recover records errors when job enqueue fails."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram", status="healthy"
        )
        queue_mock.get_operations_for_service.return_value = [
            _make_operation("op-1", "instagram_publish"),
            _make_operation("op-2", "instagram_metrics"),
        ]
        # First succeeds, second fails
        job_enqueuer_mock.side_effect = [None, Exception("ARQ connection lost")]

        result = await processor.check_and_recover("instagram")

        assert result.processed == 1
        assert len(result.errors) == 1
        assert "op-2" in result.errors[0]

    @pytest.mark.asyncio
    async def test_no_pending_operations(self, processor, registry_mock, queue_mock):
        """check_and_recover returns zero-result when no pending operations."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="discord", status="healthy"
        )
        queue_mock.get_operations_for_service.return_value = []

        result = await processor.check_and_recover("discord")

        assert result.processed == 0
        assert result.remaining == 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_returns_recovery_result_type(self, processor, registry_mock, queue_mock):
        """check_and_recover returns a RecoveryResult instance."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram", status="healthy"
        )

        result = await processor.check_and_recover("instagram")

        assert isinstance(result, RecoveryResult)


class TestProcessAllServices:
    """Tests for process_all_services method."""

    @pytest.mark.asyncio
    async def test_iterates_all_monitored_services(
        self, processor, registry_mock, queue_mock
    ):
        """process_all_services processes each monitored service."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="test", status="healthy"
        )
        queue_mock.get_operations_for_service.return_value = []

        results = await processor.process_all_services()

        assert len(results) == 4  # instagram, shopify, discord, google_calendar
        names = {r.service_name for r in results}
        assert names == {"instagram", "shopify", "discord", "google_calendar"}

    @pytest.mark.asyncio
    async def test_returns_list_of_recovery_results(
        self, processor, registry_mock, queue_mock
    ):
        """process_all_services returns list of RecoveryResult."""
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="test", status="healthy"
        )
        queue_mock.get_operations_for_service.return_value = []

        results = await processor.process_all_services()

        assert all(isinstance(r, RecoveryResult) for r in results)


class TestRecoveryResilience:
    """Tests that recovery failures don't raise."""

    @pytest.mark.asyncio
    async def test_registry_failure_returns_empty_result(
        self, processor, registry_mock
    ):
        """Registry failure in check_and_recover returns zero-result."""
        registry_mock.get_status.side_effect = Exception("Redis down")

        result = await processor.check_and_recover("instagram")

        assert result.processed == 0
        assert result.errors == []
