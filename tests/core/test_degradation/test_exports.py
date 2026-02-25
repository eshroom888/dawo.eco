"""Tests for degradation package exports and registration.

Story 7-10, Task 8.3: Registration + export tests.
"""

import pytest


class TestPackageExports:
    """Tests that all public classes are importable from package."""

    def test_service_health_status_importable(self):
        """ServiceHealthStatus importable from core.degradation."""
        from core.degradation import ServiceHealthStatus
        assert ServiceHealthStatus is not None

    def test_recovery_result_importable(self):
        """RecoveryResult importable from core.degradation."""
        from core.degradation import RecoveryResult
        assert RecoveryResult is not None

    def test_service_health_registry_importable(self):
        """ServiceHealthRegistry importable from core.degradation."""
        from core.degradation import ServiceHealthRegistry
        assert ServiceHealthRegistry is not None

    def test_degradation_alert_service_importable(self):
        """DegradationAlertService importable from core.degradation."""
        from core.degradation import DegradationAlertService
        assert DegradationAlertService is not None

    def test_recovery_processor_importable(self):
        """RecoveryProcessor importable from core.degradation."""
        from core.degradation import RecoveryProcessor
        assert RecoveryProcessor is not None

    def test_record_service_health_importable(self):
        """record_service_health importable from core.degradation."""
        from core.degradation import record_service_health
        assert callable(record_service_health)


class TestAllExport:
    """Tests that __all__ is complete."""

    def test_all_includes_all_public_classes(self):
        """__all__ includes all public classes and functions."""
        from core.degradation import __all__

        expected = {
            "DegradationAlertService",
            "RecoveryProcessor",
            "RecoveryResult",
            "ServiceHealthRegistry",
            "ServiceHealthStatus",
            "record_service_health",
        }
        assert set(__all__) == expected


class TestTeamSpecRegistration:
    """Tests for team_spec.py registration."""

    def test_degradation_services_registered(self):
        """All degradation services are in SERVICES list."""
        from teams.dawo.team_spec import SERVICES

        service_names = {s.name for s in SERVICES}
        assert "service_health_registry" in service_names
        assert "recovery_processor" in service_names
        assert "degradation_alert_service" in service_names

    def test_no_registered_agent_for_degradation(self):
        """No degradation component uses RegisteredAgent (none use LLM)."""
        from teams.dawo.team_spec import AGENTS

        degradation_agents = [a for a in AGENTS if "degradation" in a.capabilities]
        assert len(degradation_agents) == 0

    def test_degradation_services_dont_require_session(self):
        """Degradation services don't require AsyncSession."""
        from teams.dawo.team_spec import SERVICES

        degradation_services = [s for s in SERVICES if "degradation" in s.capabilities]
        for s in degradation_services:
            assert s.requires_session is False, f"{s.name} should not require session"
