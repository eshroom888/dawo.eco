"""Tests for redirect router endpoint.

Story 7-2, Task 4.7: Tests for GET /l/{code} redirect endpoint.
Tests 307 redirect, 404, async click tracking, IP extraction.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routers.redirect import redirect_router, _get_short_link_service


@pytest.fixture
def mock_service() -> AsyncMock:
    """Create mock ShortLinkService."""
    service = AsyncMock()
    service.resolve_and_track = AsyncMock()
    return service


@pytest.fixture
def app(mock_service: AsyncMock) -> FastAPI:
    """Create test FastAPI app with redirect router."""
    app = FastAPI()
    app.include_router(redirect_router)

    # Override dependency
    app.dependency_overrides[_get_short_link_service] = lambda: mock_service

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client that does NOT follow redirects."""
    return TestClient(app, follow_redirects=False)


class TestRedirectEndpoint:
    """Tests for GET /l/{code} endpoint."""

    def test_returns_307_redirect_for_valid_code(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Valid short code returns HTTP 307 Temporary Redirect."""
        mock_service.resolve_and_track.return_value = (
            "https://dawo.no/product?utm_source=instagram"
        )

        response = client.get("/l/abc123")

        assert response.status_code == 307
        assert response.headers["location"] == (
            "https://dawo.no/product?utm_source=instagram"
        )

    def test_returns_404_for_unknown_code(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Unknown short code returns HTTP 404."""
        mock_service.resolve_and_track.return_value = None

        response = client.get("/l/nonexistent")

        assert response.status_code == 404

    def test_passes_client_ip_to_service(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Client IP is extracted and passed to service."""
        mock_service.resolve_and_track.return_value = "https://example.com"

        client.get("/l/abc123")

        mock_service.resolve_and_track.assert_awaited_once()
        call_kwargs = mock_service.resolve_and_track.call_args
        # IP should be passed (testclient uses "testclient" or similar)
        assert call_kwargs.kwargs.get("ip") is not None or call_kwargs[1].get("ip") is not None

    def test_passes_user_agent_to_service(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """User-Agent header is forwarded to service."""
        mock_service.resolve_and_track.return_value = "https://example.com"

        client.get(
            "/l/abc123",
            headers={"User-Agent": "Mozilla/5.0 (iPhone)"},
        )

        call_kwargs = mock_service.resolve_and_track.call_args
        # Check both positional and keyword args
        all_args = {**dict(zip(["code", "ip", "user_agent", "referer"],
                               call_kwargs.args if call_kwargs.args else [])),
                    **call_kwargs.kwargs}
        assert "Mozilla/5.0 (iPhone)" in str(all_args)

    def test_passes_referer_to_service(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Referer header is forwarded to service."""
        mock_service.resolve_and_track.return_value = "https://example.com"

        client.get(
            "/l/abc123",
            headers={"Referer": "https://instagram.com"},
        )

        call_kwargs = mock_service.resolve_and_track.call_args
        all_args = {**dict(zip(["code", "ip", "user_agent", "referer"],
                               call_kwargs.args if call_kwargs.args else [])),
                    **call_kwargs.kwargs}
        assert "https://instagram.com" in str(all_args)

    def test_x_forwarded_for_takes_priority(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """X-Forwarded-For header is used over request.client.host."""
        mock_service.resolve_and_track.return_value = "https://example.com"

        client.get(
            "/l/abc123",
            headers={"X-Forwarded-For": "203.0.113.50, 70.41.3.18"},
        )

        call_kwargs = mock_service.resolve_and_track.call_args
        all_args = {**dict(zip(["code", "ip", "user_agent", "referer"],
                               call_kwargs.args if call_kwargs.args else [])),
                    **call_kwargs.kwargs}
        # First IP in X-Forwarded-For chain is the client
        assert "203.0.113.50" in str(all_args)


class TestRouterRegistration:
    """Tests for router registration."""

    def test_router_is_importable(self) -> None:
        """redirect_router is importable from module."""
        from ui.backend.routers.redirect import redirect_router
        assert redirect_router is not None

    def test_router_has_l_route(self) -> None:
        """Router has /l/{code} route."""
        routes = [r.path for r in redirect_router.routes]
        assert "/l/{code}" in routes


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports(self) -> None:
        """redirect module exports redirect_router."""
        from ui.backend.routers import redirect

        assert hasattr(redirect, "__all__")
        assert "redirect_router" in redirect.__all__
