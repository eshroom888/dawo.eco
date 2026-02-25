"""Tests for Manual Trigger Service registration and exports.

Story 7-7, Task 8.4: Registration in team_spec.py and exports in __init__.py.
Target: 5+ tests.
"""

import pytest


class TestManualTriggerServiceRegistration:
    """Tests for RegisteredService entry in team_spec.py."""

    def test_manual_trigger_service_in_services_list(self):
        """ManualTriggerService is registered as a service."""
        from teams.dawo.team_spec import SERVICES

        names = [s.name for s in SERVICES]
        assert "manual_trigger_service" in names

    def test_registered_with_correct_capabilities(self):
        """ManualTriggerService has expected capabilities."""
        from teams.dawo.team_spec import SERVICES

        service = next(s for s in SERVICES if s.name == "manual_trigger_service")
        assert "scheduling" in service.capabilities
        assert "manual_trigger" in service.capabilities
        assert "team_trigger" in service.capabilities

    def test_registered_without_session(self):
        """ManualTriggerService does not require session (receives repo via DI)."""
        from teams.dawo.team_spec import SERVICES

        service = next(s for s in SERVICES if s.name == "manual_trigger_service")
        assert service.requires_session is False

    def test_registered_service_class_is_correct(self):
        """ManualTriggerService service_class points to correct class."""
        from teams.dawo.team_spec import SERVICES
        from core.scheduling.manual_trigger_service import ManualTriggerService

        service = next(s for s in SERVICES if s.name == "manual_trigger_service")
        assert service.service_class is ManualTriggerService


class TestSchedulingModuleExports:
    """Tests for core.scheduling __init__.py exports."""

    def test_manual_trigger_service_exported(self):
        """ManualTriggerService importable from core.scheduling."""
        from core.scheduling import ManualTriggerService

        assert ManualTriggerService is not None

    def test_team_definitions_exported(self):
        """TEAM_DEFINITIONS importable from core.scheduling."""
        from core.scheduling import TEAM_DEFINITIONS

        assert isinstance(TEAM_DEFINITIONS, dict)

    def test_validate_team_definitions_exported(self):
        """validate_team_definitions importable from core.scheduling."""
        from core.scheduling import validate_team_definitions

        assert callable(validate_team_definitions)

    def test_pending_trigger_store_exported(self):
        """pending_trigger_store singleton importable from core.scheduling."""
        from core.scheduling import pending_trigger_store, PendingTriggerStore

        assert isinstance(pending_trigger_store, PendingTriggerStore)

    def test_trigger_dtos_exported(self):
        """All trigger DTOs importable from core.scheduling."""
        from core.scheduling import (
            TriggerResult,
            TeamTriggerResult,
            TriggerableAgentDTO,
            TeamDTO,
            PendingTrigger,
        )

        assert TriggerResult is not None
        assert TeamTriggerResult is not None
        assert TriggerableAgentDTO is not None
        assert TeamDTO is not None
        assert PendingTrigger is not None

    def test_all_exports_listed_in_dunder_all(self):
        """All manual trigger exports are in __all__."""
        import core.scheduling as mod

        expected = [
            "ManualTriggerService",
            "TEAM_DEFINITIONS",
            "validate_team_definitions",
            "PendingTriggerStore",
            "pending_trigger_store",
            "TriggerResult",
            "TeamTriggerResult",
            "TriggerableAgentDTO",
            "TeamDTO",
            "PendingTrigger",
        ]
        for name in expected:
            assert name in mod.__all__, f"'{name}' missing from core.scheduling.__all__"
