"""Tests for Shopify webhook endpoint.

Story 7-3, Task 6.5: Webhook and polling job tests.

Tests:
- HMAC signature verification (valid, invalid, missing)
- Fire-and-forget order processing
- Polling job creation and scheduling
"""

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routers.webhooks import (
    webhook_router,
    verify_shopify_hmac,
    _get_attribution_service,
    _get_shopify_client,
)


def _make_app() -> FastAPI:
    """Create test app with webhook router."""
    app = FastAPI()
    app.include_router(webhook_router)
    return app


def _sign_payload(payload: bytes, secret: str) -> str:
    """Compute Shopify HMAC-SHA256 for a payload."""
    computed = base64.b64encode(
        hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    ).decode()
    return computed


class TestVerifyShopifyHmac:
    """Tests for HMAC verification function."""

    def test_valid_signature(self) -> None:
        secret = "test_secret_123"
        body = b'{"id": 12345}'
        signature = _sign_payload(body, secret)
        assert verify_shopify_hmac(body, signature, secret) is True

    def test_invalid_signature(self) -> None:
        secret = "test_secret_123"
        body = b'{"id": 12345}'
        assert verify_shopify_hmac(body, "invalid_signature", secret) is False

    def test_tampered_body(self) -> None:
        secret = "test_secret_123"
        body = b'{"id": 12345}'
        signature = _sign_payload(body, secret)
        tampered = b'{"id": 99999}'
        assert verify_shopify_hmac(tampered, signature, secret) is False

    def test_empty_signature(self) -> None:
        secret = "test_secret_123"
        body = b'{"id": 12345}'
        assert verify_shopify_hmac(body, "", secret) is False


class TestWebhookEndpoint:
    """Tests for POST /api/webhooks/shopify/orders-paid."""

    def test_valid_webhook_returns_200(self) -> None:
        app = _make_app()
        secret = "webhook_secret"
        payload = json.dumps({"id": 12345}).encode()
        signature = _sign_payload(payload, secret)

        mock_service = AsyncMock()
        mock_client = AsyncMock()

        app.dependency_overrides[_get_attribution_service] = lambda: mock_service
        app.dependency_overrides[_get_shopify_client] = lambda: mock_client

        with patch(
            "ui.backend.routers.webhooks._get_webhook_secret",
            return_value=secret,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/webhooks/shopify/orders-paid",
                content=payload,
                headers={
                    "X-Shopify-Hmac-Sha256": signature,
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_invalid_hmac_returns_401(self) -> None:
        app = _make_app()
        # Must override deps even for 401 — FastAPI resolves deps before handler
        mock_service = AsyncMock()
        mock_client = AsyncMock()
        app.dependency_overrides[_get_attribution_service] = lambda: mock_service
        app.dependency_overrides[_get_shopify_client] = lambda: mock_client

        with patch(
            "ui.backend.routers.webhooks._get_webhook_secret",
            return_value="webhook_secret",
        ):
            client = TestClient(app)
            response = client.post(
                "/api/webhooks/shopify/orders-paid",
                content=b'{"id": 12345}',
                headers={
                    "X-Shopify-Hmac-Sha256": "invalid_signature",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 401

    def test_missing_hmac_returns_401(self) -> None:
        app = _make_app()
        mock_service = AsyncMock()
        mock_client = AsyncMock()
        app.dependency_overrides[_get_attribution_service] = lambda: mock_service
        app.dependency_overrides[_get_shopify_client] = lambda: mock_client

        with patch(
            "ui.backend.routers.webhooks._get_webhook_secret",
            return_value="webhook_secret",
        ):
            client = TestClient(app)
            response = client.post(
                "/api/webhooks/shopify/orders-paid",
                content=b'{"id": 12345}',
                headers={"Content-Type": "application/json"},
            )

        assert response.status_code == 401


class TestPollingJob:
    """Tests for poll_shopify_orders ARQ job."""

    @pytest.mark.asyncio
    async def test_polls_and_processes_orders(self) -> None:
        from ui.backend.routers.webhooks import poll_shopify_orders

        mock_client = AsyncMock()
        mock_service = AsyncMock()
        mock_batch_result = MagicMock()
        mock_batch_result.succeeded = 3
        mock_batch_result.failed = 0
        mock_service.process_orders_batch.return_value = mock_batch_result

        mock_orders = [MagicMock(), MagicMock(), MagicMock()]
        mock_client.get_orders_since.return_value = mock_orders

        result = await poll_shopify_orders(
            shopify_client=mock_client,
            attribution_service=mock_service,
        )

        mock_client.get_orders_since.assert_awaited_once()
        mock_service.process_orders_batch.assert_awaited_once_with(mock_orders)
        assert result["succeeded"] == 3

    @pytest.mark.asyncio
    async def test_no_orders_found(self) -> None:
        from ui.backend.routers.webhooks import poll_shopify_orders

        mock_client = AsyncMock()
        mock_service = AsyncMock()
        mock_client.get_orders_since.return_value = []

        result = await poll_shopify_orders(
            shopify_client=mock_client,
            attribution_service=mock_service,
        )

        mock_service.process_orders_batch.assert_not_awaited()
        assert result["succeeded"] == 0

    @pytest.mark.asyncio
    async def test_handles_client_error(self) -> None:
        from ui.backend.routers.webhooks import poll_shopify_orders

        mock_client = AsyncMock()
        mock_service = AsyncMock()
        mock_client.get_orders_since.side_effect = Exception("API error")

        result = await poll_shopify_orders(
            shopify_client=mock_client,
            attribution_service=mock_service,
        )

        assert result["error"] is not None
