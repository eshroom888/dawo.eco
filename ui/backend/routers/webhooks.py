"""FastAPI router for Shopify webhook endpoints.

Story 7-3, Task 6: Webhook endpoint + polling job.

POST /api/webhooks/shopify/orders-paid:
- Verifies HMAC signature (timing-safe)
- Returns 200 immediately (fire-and-forget)
- Processes attribution via asyncio.create_task()

poll_shopify_orders():
- Standalone async function for ARQ cron job
- Queries orders since last poll, processes unattributed orders
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from core.analytics.attribution_service import AttributionService

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/api/webhooks/shopify", tags=["webhooks"])


def _get_webhook_secret() -> str:
    """Get webhook secret from config.

    Overridden in tests.
    """
    from core.config import get_config

    return get_config().attribution.webhook_secret


async def _get_attribution_service() -> AttributionService:
    """Dependency injection placeholder for AttributionService.

    Overridden in application startup and tests.
    """
    raise NotImplementedError(
        "AttributionService dependency must be configured at application startup"
    )


async def _get_shopify_client():
    """Dependency injection placeholder for ShopifyClient.

    Overridden in application startup and tests.
    """
    raise NotImplementedError(
        "ShopifyClient dependency must be configured at application startup"
    )


def verify_shopify_hmac(body: bytes, signature: str, secret: str) -> bool:
    """Verify Shopify webhook HMAC-SHA256 signature.

    Task 6.1: CRITICAL — uses hmac.compare_digest() for timing-safe comparison.

    Args:
        body: Raw request body bytes
        signature: X-Shopify-Hmac-Sha256 header value
        secret: Webhook secret from config

    Returns:
        True if signature is valid
    """
    if not signature:
        return False

    computed = base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()

    return hmac.compare_digest(computed, signature)


async def _process_order_async(
    order_data: dict,
    service: AttributionService,
    client,
) -> None:
    """Fire-and-forget order processing.

    Task 6.2: Runs after webhook returns 200.

    Args:
        order_data: Raw order JSON from webhook
        service: AttributionService for attribution
        client: ShopifyClient for order lookup
    """
    try:
        order_gid = order_data.get("admin_graphql_api_id", "")
        if not order_gid:
            logger.warning("Webhook order has no admin_graphql_api_id")
            return

        # Fetch full order with customer journey data via GraphQL
        order = await client.get_order_by_id(order_gid)
        if order is None:
            logger.warning("Could not fetch order %s from GraphQL", order_gid)
            return

        result = await service.process_order(order)
        logger.info(
            "Webhook order %s processed: attributed=%s",
            order_gid,
            result.attributed,
        )
    except Exception as e:
        logger.warning("Failed to process webhook order: %s", e)


@webhook_router.post("/orders-paid")
async def handle_orders_paid(
    request: Request,
    service: AttributionService = Depends(_get_attribution_service),
    client=Depends(_get_shopify_client),
) -> dict:
    """Handle Shopify orders/paid webhook.

    Task 6.1: HMAC verification.
    Task 6.2: Fire-and-forget processing.

    Returns 200 immediately. Processing happens via asyncio.create_task().

    Returns:
        {"status": "accepted"} on success

    Raises:
        HTTPException: 401 if HMAC verification fails
    """
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-Sha256", "")
    secret = _get_webhook_secret()

    if not verify_shopify_hmac(body, signature, secret):
        logger.warning("Invalid Shopify webhook HMAC signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse order data
    try:
        order_data = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in webhook body")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Fire-and-forget: process attribution in background
    asyncio.create_task(
        _process_order_async(order_data, service, client)
    )

    return {"status": "accepted"}


async def poll_shopify_orders(
    shopify_client,
    attribution_service: AttributionService,
    hours_back: int = 2,
) -> dict:
    """Poll Shopify for recent orders and process attributions.

    Task 6.3: ARQ polling job as webhook fallback.
    Task 6.4: Called hourly via ARQ cron.

    Queries orders created since `hours_back` hours ago,
    processes any that haven't been attributed yet.

    Args:
        shopify_client: ShopifyClient for order queries
        attribution_service: AttributionService for processing
        hours_back: Hours to look back for orders

    Returns:
        Dict with succeeded, failed, error counts
    """
    try:
        since = datetime.now(UTC) - timedelta(hours=hours_back)
        orders = await shopify_client.get_orders_since(since)

        if not orders:
            logger.info("Polling: no new orders found")
            return {"succeeded": 0, "failed": 0, "error": None}

        result = await attribution_service.process_orders_batch(orders)

        logger.info(
            "Polling complete: %d/%d succeeded, %d failed",
            result.succeeded,
            result.total,
            result.failed,
        )

        return {
            "succeeded": result.succeeded,
            "failed": result.failed,
            "error": None,
        }

    except Exception as e:
        logger.warning("Polling failed: %s", e)
        return {"succeeded": 0, "failed": 0, "error": str(e)}


__all__ = [
    "webhook_router",
    "verify_shopify_hmac",
    "poll_shopify_orders",
]
