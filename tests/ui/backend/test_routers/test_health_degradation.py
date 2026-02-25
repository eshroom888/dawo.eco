"""Tests for extended health endpoint with degradation data.

Story 7-10, Task 7.2: Extended health endpoint tests.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from core.degradation.models import ServiceHealthStatus


class TestOverallHealthResponseFields:
    """Tests for OverallHealthResponse new fields."""

    def test_degraded_services_field_exists(self):
        """OverallHealthResponse has degraded_services field."""
        from ui.backend.routers.health import OverallHealthResponse
        from datetime import datetime

        response = OverallHealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            degraded_services=2,
            queued_operations=5,
        )
        assert response.degraded_services == 2
        assert response.queued_operations == 5

    def test_degraded_services_defaults_to_zero(self):
        """degraded_services defaults to 0."""
        from ui.backend.routers.health import OverallHealthResponse
        from datetime import datetime

        response = OverallHealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
        )
        assert response.degraded_services == 0
        assert response.queued_operations == 0

    def test_backward_compat_no_new_fields_required(self):
        """Existing code that doesn't pass new fields still works."""
        from ui.backend.routers.health import OverallHealthResponse
        from datetime import datetime

        # This should work without degraded_services/queued_operations
        response = OverallHealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            services={"instagram": {"healthy": True}},
        )
        assert response.status == "healthy"

    def test_services_health_endpoint_exists(self):
        """Router has /services endpoint."""
        from ui.backend.routers.health import router

        routes = [r.path for r in router.routes]
        assert "/services" in routes or any("/services" in str(r.path) for r in router.routes)
