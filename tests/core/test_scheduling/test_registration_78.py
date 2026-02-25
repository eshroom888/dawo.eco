"""Tests for Story 7-8 registration and exports.

Story 7-8, Task 9: Verify all new components are exported
from core.scheduling and registered in team_spec.py.
Target: 7 tests.
"""

import pytest


class TestSchedulingExports:
    """Verify core.scheduling __init__.py exports for Story 7-8."""

    def test_agent_execution_log_model_exported(self) -> None:
        from core.scheduling import AgentExecutionLog

        assert AgentExecutionLog is not None

    def test_execution_log_repository_exported(self) -> None:
        from core.scheduling import ExecutionLogRepository

        assert ExecutionLogRepository is not None

    def test_execution_log_service_exported(self) -> None:
        from core.scheduling import ExecutionLogService

        assert ExecutionLogService is not None

    def test_execution_log_dtos_exported(self) -> None:
        from core.scheduling import (
            ExecutionLogDTO,
            ExecutionLogDetailDTO,
            DashboardSummaryDTO,
            ExecutionLogFilterDTO,
        )

        assert ExecutionLogDTO is not None
        assert ExecutionLogDetailDTO is not None
        assert DashboardSummaryDTO is not None
        assert ExecutionLogFilterDTO is not None

    def test_execution_events_exported(self) -> None:
        from core.scheduling import (
            ExecutionEvent,
            ExecutionEventType,
            ExecutionEventEmitter,
            get_execution_events,
            execution_events,
        )

        assert ExecutionEvent is not None
        assert ExecutionEventType is not None
        assert ExecutionEventEmitter is not None
        assert get_execution_events is not None
        assert execution_events is not None

    def test_log_capture_handler_exported(self) -> None:
        from core.scheduling import LogCaptureHandler

        assert LogCaptureHandler is not None


class TestTeamSpecRegistration:
    """Verify team_spec.py service registration for Story 7-8."""

    def test_execution_log_service_registered(self) -> None:
        from teams.dawo.team_spec import SERVICES

        service_names = [s.name for s in SERVICES]
        assert "execution_log_service" in service_names

    def test_execution_log_service_capabilities(self) -> None:
        from teams.dawo.team_spec import SERVICES

        service = next(s for s in SERVICES if s.name == "execution_log_service")
        assert "scheduling" in service.capabilities
        assert "execution_dashboard" in service.capabilities

    def test_execution_log_service_requires_no_session(self) -> None:
        """ExecutionLogService receives repos via injection, not session directly."""
        from teams.dawo.team_spec import SERVICES

        service = next(s for s in SERVICES if s.name == "execution_log_service")
        assert service.requires_session is False

    def test_execution_log_repository_registered(self) -> None:
        from teams.dawo.team_spec import SERVICES

        service_names = [s.name for s in SERVICES]
        assert "execution_log_repository" in service_names

    def test_execution_log_repository_requires_session(self) -> None:
        from teams.dawo.team_spec import SERVICES

        service = next(s for s in SERVICES if s.name == "execution_log_repository")
        assert service.requires_session is True
