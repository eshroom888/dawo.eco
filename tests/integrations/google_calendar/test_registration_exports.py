"""Tests for calendar integration registration and exports.

Story 7-9, Task 9.3: Verify public exports and team_spec registration.
Target: 5+ tests.
"""

import pytest


class TestPackageExports:
    """Tests for integrations.google_calendar package exports."""

    def test_all_public_classes_importable(self):
        """All declared public classes are importable from the package."""
        from integrations.google_calendar import (
            CalendarAuthError,
            CalendarClient,
            CalendarClientProtocol,
            CalendarCredentialsManager,
            CalendarEventData,
            CalendarSyncError,
            CalendarSyncResult,
            CalendarSyncService,
            EventBuilder,
        )

        assert CalendarAuthError is not None
        assert CalendarClient is not None
        assert CalendarClientProtocol is not None
        assert CalendarCredentialsManager is not None
        assert CalendarEventData is not None
        assert CalendarSyncError is not None
        assert CalendarSyncResult is not None
        assert CalendarSyncService is not None
        assert EventBuilder is not None

    def test_all_exports_complete(self):
        """__all__ contains all expected public symbols."""
        from integrations.google_calendar import __all__

        expected = {
            "CalendarAuthError",
            "CalendarClient",
            "CalendarClientProtocol",
            "CalendarConfig",
            "CalendarCredentialsManager",
            "CalendarEventData",
            "CalendarSyncError",
            "CalendarSyncResult",
            "CalendarSyncService",
            "EventBuilder",
        }

        assert set(__all__) == expected

    def test_calendar_client_protocol_is_runtime_checkable(self):
        """CalendarClientProtocol has @runtime_checkable decorator."""
        from integrations.google_calendar import CalendarClientProtocol

        # runtime_checkable protocols support isinstance() checks
        assert hasattr(CalendarClientProtocol, "__protocol_attrs__") or hasattr(
            CalendarClientProtocol, "_is_runtime_protocol"
        )

    def test_calendar_client_implements_protocol(self):
        """CalendarClient satisfies CalendarClientProtocol."""
        from integrations.google_calendar import (
            CalendarClient,
            CalendarClientProtocol,
        )

        # Verify the client class has all protocol methods
        protocol_methods = {"ensure_calendar_exists", "create_event", "update_event", "delete_event"}
        client_methods = set(dir(CalendarClient))
        assert protocol_methods.issubset(client_methods)


class TestTeamSpecRegistration:
    """Tests for calendar service registration in team_spec."""

    def test_calendar_sync_service_registered(self):
        """CalendarSyncService is in SERVICES list as RegisteredService."""
        from teams.dawo.team_spec import SERVICES

        service_names = [s.name for s in SERVICES]
        assert "calendar_sync_service" in service_names

    def test_calendar_sync_service_is_registered_service(self):
        """Calendar sync uses RegisteredService (not RegisteredAgent)."""
        from teams.dawo.team_spec import SERVICES

        cal_service = next(
            s for s in SERVICES if s.name == "calendar_sync_service"
        )
        assert cal_service.requires_session is False

    def test_calendar_sync_service_capabilities(self):
        """Calendar sync service has correct capability tags."""
        from teams.dawo.team_spec import SERVICES

        cal_service = next(
            s for s in SERVICES if s.name == "calendar_sync_service"
        )
        assert "calendar" in cal_service.capabilities
        assert "content_sync" in cal_service.capabilities

    def test_calendar_sync_service_class_is_correct(self):
        """Registered service_class points to CalendarSyncService."""
        from integrations.google_calendar.sync_service import CalendarSyncService
        from teams.dawo.team_spec import SERVICES

        cal_service = next(
            s for s in SERVICES if s.name == "calendar_sync_service"
        )
        assert cal_service.service_class is CalendarSyncService
