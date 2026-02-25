"""Tests for agent scheduling registration and exports.

Story 7-6, Task 9: Registration in team_spec.py and exports in __init__.py.
Target: 5+ tests.
"""

import pytest


class TestSchedulingExports:
    """Tests for core.scheduling.__init__.py exports."""

    def test_agent_schedule_model_exported(self):
        from core.scheduling import AgentSchedule
        assert AgentSchedule is not None

    def test_schedule_change_log_model_exported(self):
        from core.scheduling import ScheduleChangeLog
        assert ScheduleChangeLog is not None

    def test_repository_exported(self):
        from core.scheduling import AgentScheduleRepository
        assert AgentScheduleRepository is not None

    def test_service_exported(self):
        from core.scheduling import AgentScheduleService
        assert AgentScheduleService is not None

    def test_cron_utils_exported(self):
        from core.scheduling import (
            validate_cron_expression,
            cron_expr_to_arq_kwargs,
            calculate_next_run,
            cron_to_human_readable,
        )
        assert validate_cron_expression is not None
        assert cron_expr_to_arq_kwargs is not None
        assert calculate_next_run is not None
        assert cron_to_human_readable is not None

    def test_dtos_exported(self):
        from core.scheduling import (
            AgentScheduleDTO,
            ScheduleUpdateRequest,
            DependencyWarning,
        )
        assert AgentScheduleDTO is not None
        assert ScheduleUpdateRequest is not None
        assert DependencyWarning is not None

    def test_all_list_complete(self):
        import core.scheduling
        expected = [
            "AgentSchedule",
            "ScheduleChangeLog",
            "AgentScheduleRepository",
            "AgentScheduleService",
            "AgentScheduleDTO",
            "ScheduleUpdateRequest",
            "DependencyWarning",
            "validate_cron_expression",
            "cron_expr_to_arq_kwargs",
            "calculate_next_run",
            "cron_to_human_readable",
        ]
        for name in expected:
            assert name in core.scheduling.__all__, f"{name} missing from __all__"


class TestTeamSpecRegistration:
    """Tests for team_spec.py service registration."""

    def test_schedule_repository_registered(self):
        from teams.dawo.team_spec import SERVICES
        names = [s.name for s in SERVICES]
        assert "agent_schedule_repository" in names

    def test_schedule_service_registered(self):
        from teams.dawo.team_spec import SERVICES
        names = [s.name for s in SERVICES]
        assert "agent_schedule_service" in names

    def test_repository_requires_session(self):
        from teams.dawo.team_spec import SERVICES
        repo = next(s for s in SERVICES if s.name == "agent_schedule_repository")
        assert repo.requires_session is True

    def test_service_does_not_require_session(self):
        from teams.dawo.team_spec import SERVICES
        svc = next(s for s in SERVICES if s.name == "agent_schedule_service")
        assert svc.requires_session is False

    def test_repository_capabilities(self):
        from teams.dawo.team_spec import SERVICES
        repo = next(s for s in SERVICES if s.name == "agent_schedule_repository")
        assert "scheduling" in repo.capabilities
        assert "schedule_storage" in repo.capabilities

    def test_service_capabilities(self):
        from teams.dawo.team_spec import SERVICES
        svc = next(s for s in SERVICES if s.name == "agent_schedule_service")
        assert "scheduling" in svc.capabilities
        assert "schedule_management" in svc.capabilities
