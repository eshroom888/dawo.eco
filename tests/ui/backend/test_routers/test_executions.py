"""Tests for Execution Dashboard API router.

Story 7-8, Task 7.4: Router tests.
Target: 15+ tests.
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.scheduling.dtos import (
    DashboardSummaryDTO,
    ExecutionLogDTO,
    ExecutionLogDetailDTO,
)
from core.scheduling.execution_log_service import ExecutionLogService
from core.scheduling.manual_trigger_service import ManualTriggerService
from ui.backend.routers.executions import (
    get_execution_service,
    get_trigger_service,
    router,
)


def _make_dto(**kwargs) -> ExecutionLogDTO:
    """Factory for test ExecutionLogDTO instances."""
    defaults = {
        "id": uuid4(),
        "agent_name": "test_agent",
        "display_name": "Test Agent",
        "started_at": datetime.now(UTC),
        "completed_at": None,
        "duration_seconds": None,
        "status": "running",
        "trigger_type": "scheduled",
        "triggered_by": "scheduler",
        "summary": None,
        "error_message": None,
        "error_traceback": None,
        "items_processed": 0,
        "has_log_output": False,
    }
    defaults.update(kwargs)
    return ExecutionLogDTO(**defaults)


def _make_detail_dto(**kwargs) -> ExecutionLogDetailDTO:
    """Factory for test ExecutionLogDetailDTO instances."""
    defaults = {
        "id": uuid4(),
        "agent_name": "test_agent",
        "display_name": "Test Agent",
        "started_at": datetime.now(UTC),
        "completed_at": datetime.now(UTC),
        "duration_seconds": 30.5,
        "status": "success",
        "trigger_type": "scheduled",
        "triggered_by": "scheduler",
        "summary": {"items_processed": 42},
        "error_message": None,
        "items_processed": 42,
        "has_log_output": True,
        "log_output": "Processing...\nDone.",
        "error_traceback": None,
    }
    defaults.update(kwargs)
    return ExecutionLogDetailDTO(**defaults)


@pytest.fixture
def mock_service():
    """Mock ExecutionLogService."""
    return AsyncMock(spec=ExecutionLogService)


@pytest.fixture
def mock_trigger_service():
    """Mock ManualTriggerService."""
    return AsyncMock(spec=ManualTriggerService)


@pytest.fixture
def client(mock_service, mock_trigger_service):
    """FastAPI test client with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_execution_service] = lambda: mock_service
    app.dependency_overrides[get_trigger_service] = lambda: mock_trigger_service

    return TestClient(app)


class TestDashboardSummary:
    """Tests for GET /api/executions/dashboard."""

    def test_returns_summary(self, client, mock_service):
        """Dashboard returns running, completions, failures, stats."""
        mock_service.get_dashboard_summary.return_value = DashboardSummaryDTO(
            running=[_make_dto(status="running")],
            recent_completions=[_make_dto(status="success")],
            recent_failures=[_make_dto(status="failed")],
            total_executions_24h=3,
            success_rate_24h=66.7,
            avg_duration_24h=30.0,
        )

        response = client.get("/api/executions/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert len(data["running"]) == 1
        assert len(data["recent_completions"]) == 1
        assert len(data["recent_failures"]) == 1
        assert data["total_executions_24h"] == 3
        assert data["success_rate_24h"] == 66.7
        assert data["avg_duration_24h"] == 30.0

    def test_empty_dashboard(self, client, mock_service):
        """Dashboard with no data returns empty lists and zero stats."""
        mock_service.get_dashboard_summary.return_value = DashboardSummaryDTO(
            running=[],
            recent_completions=[],
            recent_failures=[],
            total_executions_24h=0,
            success_rate_24h=0.0,
            avg_duration_24h=None,
        )

        response = client.get("/api/executions/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] == []
        assert data["total_executions_24h"] == 0


class TestListExecutions:
    """Tests for GET /api/executions/."""

    def test_no_filters(self, client, mock_service):
        """List with no filters returns paginated results."""
        dto = _make_dto(status="success")
        mock_service.get_filtered_executions.return_value = ([dto], 1)

        response = client.get("/api/executions/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["executions"]) == 1
        assert data["total_count"] == 1
        assert data["has_more"] is False

    def test_agent_name_filter(self, client, mock_service):
        """Filter by agent_name is passed to service."""
        mock_service.get_filtered_executions.return_value = ([], 0)

        response = client.get("/api/executions/?agent_name=health_claims_monitor")
        assert response.status_code == 200
        call_args = mock_service.get_filtered_executions.call_args
        assert call_args[0][0].agent_name == "health_claims_monitor"

    def test_status_filter(self, client, mock_service):
        """Filter by status is passed to service."""
        mock_service.get_filtered_executions.return_value = ([], 0)

        response = client.get("/api/executions/?status=failed")
        assert response.status_code == 200
        call_args = mock_service.get_filtered_executions.call_args
        assert call_args[0][0].status == "failed"

    def test_date_range_filter(self, client, mock_service):
        """Filter by date range is passed to service."""
        mock_service.get_filtered_executions.return_value = ([], 0)

        response = client.get(
            "/api/executions/?date_from=2026-02-01T00:00:00&date_to=2026-02-28T23:59:59"
        )
        assert response.status_code == 200
        call_args = mock_service.get_filtered_executions.call_args
        assert call_args[0][0].date_from is not None
        assert call_args[0][0].date_to is not None

    def test_combined_filters(self, client, mock_service):
        """Multiple filters are combined correctly."""
        mock_service.get_filtered_executions.return_value = ([], 0)

        response = client.get(
            "/api/executions/?agent_name=test_agent&status=success&trigger_type=manual"
        )
        assert response.status_code == 200
        filters = mock_service.get_filtered_executions.call_args[0][0]
        assert filters.agent_name == "test_agent"
        assert filters.status == "success"
        assert filters.trigger_type == "manual"

    def test_pagination_offset_limit(self, client, mock_service):
        """Offset and limit are passed through."""
        mock_service.get_filtered_executions.return_value = ([], 50)

        response = client.get("/api/executions/?limit=10&offset=20")
        assert response.status_code == 200
        filters = mock_service.get_filtered_executions.call_args[0][0]
        assert filters.limit == 10
        assert filters.offset == 20
        data = response.json()
        assert data["has_more"] is True  # 20 + 10 = 30 < 50

    def test_empty_results(self, client, mock_service):
        """Empty results return empty list and zero count."""
        mock_service.get_filtered_executions.return_value = ([], 0)

        response = client.get("/api/executions/")
        assert response.status_code == 200
        data = response.json()
        assert data["executions"] == []
        assert data["total_count"] == 0
        assert data["has_more"] is False


class TestExecutionDetail:
    """Tests for GET /api/executions/{execution_id}."""

    def test_returns_detail_with_log(self, client, mock_service):
        """Detail view includes log_output and error_traceback."""
        detail = _make_detail_dto()
        mock_service.get_execution_detail.return_value = detail

        response = client.get(f"/api/executions/{detail.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["log_output"] == "Processing...\nDone."
        assert data["has_log_output"] is True

    def test_not_found_returns_404(self, client, mock_service):
        """Non-existent execution returns 404."""
        mock_service.get_execution_detail.return_value = None

        response = client.get(f"/api/executions/{uuid4()}")
        assert response.status_code == 404

    def test_invalid_uuid_returns_422(self, client, mock_service):
        """Invalid UUID format returns 422."""
        response = client.get("/api/executions/not-a-uuid")
        assert response.status_code == 422


class TestRetryExecution:
    """Tests for POST /api/executions/{execution_id}/retry."""

    def test_retry_failed_execution(self, client, mock_service, mock_trigger_service):
        """Retry a failed execution delegates to ManualTriggerService."""
        detail = _make_detail_dto(status="failed", agent_name="health_claims_monitor")
        mock_service.get_execution_detail.return_value = detail

        trigger_result = MagicMock()
        trigger_result.agent_name = "health_claims_monitor"
        trigger_result.status = "queued"
        trigger_result.message = "Triggered"
        trigger_result.triggered_at = datetime.now(UTC)
        mock_trigger_service.trigger_agent.return_value = trigger_result

        response = client.post(f"/api/executions/{detail.id}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_name"] == "health_claims_monitor"
        assert data["status"] == "queued"
        mock_trigger_service.trigger_agent.assert_awaited_once_with(
            agent_name="health_claims_monitor",
            triggered_by="operator",
        )

    def test_retry_non_failed_returns_400(self, client, mock_service):
        """Cannot retry a non-failed execution."""
        detail = _make_detail_dto(status="success")
        mock_service.get_execution_detail.return_value = detail

        response = client.post(f"/api/executions/{detail.id}/retry")
        assert response.status_code == 400

    def test_retry_not_found_returns_404(self, client, mock_service):
        """Retry non-existent execution returns 404."""
        mock_service.get_execution_detail.return_value = None

        response = client.post(f"/api/executions/{uuid4()}/retry")
        assert response.status_code == 404

    def test_retry_invalid_uuid_returns_422(self, client, mock_service):
        """Invalid UUID format returns 422."""
        response = client.post("/api/executions/not-a-uuid/retry")
        assert response.status_code == 422

    def test_retry_incomplete_execution(self, client, mock_service, mock_trigger_service):
        """Can retry incomplete executions too."""
        detail = _make_detail_dto(status="incomplete")
        mock_service.get_execution_detail.return_value = detail

        trigger_result = MagicMock()
        trigger_result.agent_name = "test_agent"
        trigger_result.status = "queued"
        trigger_result.message = "Triggered"
        trigger_result.triggered_at = datetime.now(UTC)
        mock_trigger_service.trigger_agent.return_value = trigger_result

        response = client.post(f"/api/executions/{detail.id}/retry")
        assert response.status_code == 200
