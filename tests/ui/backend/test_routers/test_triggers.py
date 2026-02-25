"""Tests for Manual Trigger router.

Story 7-7, Task 5.4: Router tests with mock service and ARQ pool.
Target: 18+ tests.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.scheduling.dtos import (
    TeamDTO,
    TeamTriggerResult,
    TriggerableAgentDTO,
    TriggerResult,
)
from ui.backend.routers.triggers import (
    get_arq_pool,
    get_trigger_service,
    router,
)


def _make_trigger_result(**overrides) -> TriggerResult:
    """Create a test TriggerResult."""
    defaults = {
        "agent_name": "health_claims_monitor",
        "status": "queued",
        "job_id": None,
        "triggered_at": datetime.now(UTC),
        "triggered_by": "operator",
        "message": "Agent triggered",
    }
    defaults.update(overrides)
    return TriggerResult(**defaults)


def _make_triggerable_agent(**overrides) -> TriggerableAgentDTO:
    """Create a test TriggerableAgentDTO."""
    defaults = {
        "agent_name": "health_claims_monitor",
        "display_name": "EU Health Claims Monitor",
    }
    defaults.update(overrides)
    return TriggerableAgentDTO(**defaults)


def _make_app(
    mock_service: AsyncMock,
    mock_pool: AsyncMock | None = None,
) -> FastAPI:
    """Create test app with trigger router and mocked dependencies."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_trigger_service] = lambda: mock_service

    if mock_pool is not None:
        app.dependency_overrides[get_arq_pool] = lambda: mock_pool

    return app


def _make_arq_pool() -> AsyncMock:
    """Create a mock ARQ pool that returns a job with job_id."""
    pool = AsyncMock()
    mock_job = MagicMock()
    mock_job.job_id = "test-job-123"
    pool.enqueue_job.return_value = mock_job
    return pool


class TestListTriggerableAgents:
    """Tests for GET /api/agents/triggerable."""

    def test_returns_all_agents_with_status(self):
        """Returns all triggerable agents."""
        mock_service = AsyncMock()
        mock_service.get_triggerable_agents.return_value = [
            _make_triggerable_agent(agent_name="health_claims_monitor"),
            _make_triggerable_agent(agent_name="novel_food_monitor", display_name="Novel Food"),
        ]

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/agents/triggerable")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["agents"]) == 2

    def test_empty_agent_list(self):
        """Returns empty list when no agents registered."""
        mock_service = AsyncMock()
        mock_service.get_triggerable_agents.return_value = []

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/agents/triggerable")

        assert response.status_code == 200
        assert response.json()["total_count"] == 0


class TestTriggerAgent:
    """Tests for POST /api/agents/{agent_name}/trigger."""

    def test_trigger_available_agent_returns_200(self):
        """Triggering an available agent returns 200 with job_id."""
        mock_service = AsyncMock()
        mock_service.trigger_agent.return_value = _make_trigger_result(status="queued")
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)
        response = client.post("/api/agents/health_claims_monitor/trigger")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["job_id"] == "test-job-123"

    def test_trigger_running_agent_returns_409(self):
        """Triggering a running agent without force returns 409."""
        mock_service = AsyncMock()
        mock_service.trigger_agent.return_value = _make_trigger_result(
            status="already_running",
            message="Agent is already running",
        )
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)
        response = client.post("/api/agents/health_claims_monitor/trigger")

        assert response.status_code == 409

    def test_trigger_running_agent_with_force_returns_200(self):
        """Triggering a running agent with force=true queues and returns 200."""
        mock_service = AsyncMock()
        mock_service.trigger_agent.return_value = _make_trigger_result(
            status="already_running",
        )
        mock_service.queue_after_current.return_value = _make_trigger_result(
            status="queued",
            message="Queued after current",
        )
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)
        response = client.post(
            "/api/agents/health_claims_monitor/trigger",
            json={"force": True},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "queued"

    def test_trigger_unknown_agent_returns_404(self):
        """Triggering an unknown agent returns 404."""
        mock_service = AsyncMock()
        mock_service.trigger_agent.return_value = _make_trigger_result(
            status="not_found",
            message="Agent not found",
        )
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)
        response = client.post("/api/agents/nonexistent_agent/trigger")

        assert response.status_code == 404

    def test_config_overrides_in_request(self):
        """Config overrides are passed to service."""
        mock_service = AsyncMock()
        mock_service.trigger_agent.return_value = _make_trigger_result(status="queued")
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)
        response = client.post(
            "/api/agents/health_claims_monitor/trigger",
            json={"config_overrides": {"keywords": ["mushroom"]}},
        )

        assert response.status_code == 200
        mock_service.trigger_agent.assert_called_once_with(
            "health_claims_monitor",
            triggered_by="operator",
            config_overrides={"keywords": ["mushroom"]},
        )

    def test_redis_unavailable_returns_503(self):
        """When Redis pool is not available, returns 503."""
        mock_service = AsyncMock()
        # Do NOT override get_arq_pool — let it raise

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_trigger_service] = lambda: mock_service
        # Simulate no arq_pool on app state
        app.state.arq_pool = None

        client = TestClient(app)
        response = client.post("/api/agents/health_claims_monitor/trigger")

        assert response.status_code == 503

    def test_path_validation_rejects_special_chars(self):
        """Path validation rejects agent names with special characters."""
        mock_service = AsyncMock()
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)

        response = client.post("/api/agents/bad-name!/trigger")
        assert response.status_code == 422


class TestQueueAgent:
    """Tests for POST /api/agents/{agent_name}/queue."""

    def test_queue_running_agent_returns_200(self):
        """Queueing a running agent returns 200."""
        mock_service = AsyncMock()
        mock_service.queue_after_current.return_value = _make_trigger_result(
            status="queued",
            message="Queued after current run",
        )

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.post("/api/agents/health_claims_monitor/queue")

        assert response.status_code == 200
        assert response.json()["status"] == "queued"

    def test_queue_unknown_agent_returns_404(self):
        """Queueing an unknown agent returns 404."""
        mock_service = AsyncMock()
        mock_service.queue_after_current.return_value = _make_trigger_result(
            status="not_found",
            message="Agent not found",
        )

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.post("/api/agents/nonexistent_agent/queue")

        assert response.status_code == 404

    def test_queue_non_running_agent_returns_400(self):
        """Queueing an agent that is not running returns 400."""
        mock_service = AsyncMock()
        mock_service.queue_after_current.return_value = _make_trigger_result(
            status="not_running",
            message="Agent is not currently running",
        )

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.post("/api/agents/health_claims_monitor/queue")

        assert response.status_code == 400


class TestListTeams:
    """Tests for GET /api/teams/."""

    def test_returns_all_teams(self):
        """Returns all defined teams."""
        mock_service = AsyncMock()
        mock_service.get_teams.return_value = [
            TeamDTO(
                team_name="regulatory_monitors",
                display_name="Regulatory Monitors",
                agents=["health_claims_monitor", "novel_food_monitor"],
                description="All regulatory agents",
            ),
        ]

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/teams/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 1
        assert data["teams"][0]["team_name"] == "regulatory_monitors"


class TestTriggerTeam:
    """Tests for POST /api/teams/{team_name}/trigger."""

    def test_trigger_team_returns_200(self):
        """Triggering a team returns 200 with per-agent results."""
        mock_service = AsyncMock()
        mock_service.trigger_team.return_value = TeamTriggerResult(
            team_name="regulatory_monitors",
            agent_results=[
                _make_trigger_result(agent_name="health_claims_monitor", status="queued"),
                _make_trigger_result(agent_name="novel_food_monitor", status="queued"),
            ],
            total=2,
            queued=2,
            skipped_running=0,
            failed=0,
        )
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)
        response = client.post("/api/teams/regulatory_monitors/trigger")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["queued"] == 2
        assert len(data["agent_results"]) == 2

    def test_trigger_unknown_team_returns_404(self):
        """Triggering an unknown team returns 404."""
        mock_service = AsyncMock()
        mock_service.trigger_team.return_value = TeamTriggerResult(
            team_name="nonexistent_team",
            agent_results=[],
            total=0,
            queued=0,
            skipped_running=0,
            failed=0,
        )
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)
        response = client.post("/api/teams/nonexistent_team/trigger")

        assert response.status_code == 404

    def test_trigger_team_enqueues_queued_agents_only(self):
        """Only queued agents get ARQ jobs enqueued."""
        mock_service = AsyncMock()
        mock_service.trigger_team.return_value = TeamTriggerResult(
            team_name="regulatory_monitors",
            agent_results=[
                _make_trigger_result(agent_name="health_claims_monitor", status="queued"),
                _make_trigger_result(agent_name="novel_food_monitor", status="already_running"),
            ],
            total=2,
            queued=1,
            skipped_running=1,
            failed=0,
        )
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)
        response = client.post("/api/teams/regulatory_monitors/trigger")

        assert response.status_code == 200
        # Only 1 enqueue call (for the queued agent)
        assert pool.enqueue_job.call_count == 1

    def test_trigger_team_redis_unavailable_returns_503(self):
        """When Redis pool is not available for team trigger, returns 503."""
        mock_service = AsyncMock()
        # Do NOT override get_arq_pool — let it raise
        mock_service.trigger_team.return_value = TeamTriggerResult(
            team_name="regulatory_monitors",
            agent_results=[
                _make_trigger_result(agent_name="health_claims_monitor", status="queued"),
            ],
            total=1,
            queued=1,
            skipped_running=0,
            failed=0,
        )

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_trigger_service] = lambda: mock_service
        app.state.arq_pool = None

        client = TestClient(app)
        response = client.post("/api/teams/regulatory_monitors/trigger")

        assert response.status_code == 503

    def test_team_name_path_validation_rejects_special_chars(self):
        """Path validation rejects team names with special characters."""
        mock_service = AsyncMock()
        pool = _make_arq_pool()

        app = _make_app(mock_service, pool)
        client = TestClient(app)

        response = client.post("/api/teams/bad-name!/trigger")
        assert response.status_code == 422
