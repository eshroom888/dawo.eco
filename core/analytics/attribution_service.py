"""Attribution service for matching Shopify orders to Instagram posts.

Epic 7, Story 7-3: Shopify Sales Attribution.
Task 4: AttributionService — core attribution logic.

Processes Shopify orders, extracts customer journey UTM data,
matches to posts via UTMRepository, and saves attributions.
Uses last-touch model (most recent visit) for revenue attribution,
records all touchpoints for analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Optional

from core.analytics.attribution_models import (
    AttributionType,
    OrderAttributionRecord,
    ShopifyOrderRecord,
)
from core.analytics.attribution_repository import AttributionRepository
from core.analytics.utm_repository import UTMRepository
from core.config import AttributionConfig
from integrations.shopify.orders import ShopifyOrder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttributionResult:
    """Result of processing a single order for attribution.

    Attributes:
        success: Whether processing completed without error
        order_gid: Shopify order global ID
        attributed: Whether the order was attributed to a post
        journey_ready: Whether customer journey data was available
        skipped: Whether the order was skipped (e.g., outside window)
        skip_reason: Reason for skipping
        error_message: Error description if failed
    """

    success: bool
    order_gid: str
    attributed: bool = False
    journey_ready: bool = True
    skipped: bool = False
    skip_reason: Optional[str] = None
    error_message: Optional[str] = None


@dataclass(frozen=True)
class BatchAttributionResult:
    """Result of batch order processing.

    Attributes:
        total: Total orders in batch
        succeeded: Orders processed successfully
        failed: Orders that failed processing
        errors: Dict mapping order GID to error message
    """

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: dict[str, str] = field(default_factory=dict)


class AttributionService:
    """Service for processing Shopify orders and creating attributions.

    Story 7-3, Task 4.1: Constructor injection pattern.

    Attributes:
        _attr_repo: Attribution repository for persistence
        _utm_repo: UTM repository for post matching
        _config: Attribution configuration
    """

    def __init__(
        self,
        attribution_repository: AttributionRepository,
        utm_repository: UTMRepository,
        config: AttributionConfig,
    ) -> None:
        """Initialize attribution service.

        Args:
            attribution_repository: Repository for orders/attributions
            utm_repository: Repository for UTM/short link lookups
            config: Attribution configuration
        """
        self._attr_repo = attribution_repository
        self._utm_repo = utm_repository
        self._config = config

    async def process_order(self, order: ShopifyOrder) -> AttributionResult:
        """Process a single order for attribution.

        Task 4.2: Core attribution logic.
        1. Check attribution window
        2. Save order record (idempotent upsert)
        3. Extract last-touch UTM content
        4. Match to post via UTMRepository
        5. Save attributions (last_touch + multi_touch)

        Args:
            order: ShopifyOrder DTO from Shopify GraphQL

        Returns:
            AttributionResult
        """
        # Task 4.4: Attribution window filtering
        cutoff = datetime.now(UTC) - timedelta(days=self._config.attribution_window_days)
        if order.created_at < cutoff:
            logger.info(
                "Order %s outside attribution window (%d days), skipping",
                order.id,
                self._config.attribution_window_days,
            )
            return AttributionResult(
                success=True,
                order_gid=order.id,
                skipped=True,
                skip_reason=f"Outside attribution window ({self._config.attribution_window_days} days)",
            )

        # Save order record (upsert)
        order_record = ShopifyOrderRecord(
            shopify_order_gid=order.id,
            order_name=order.name,
            total_price=order.total_price,
            currency=order.currency,
            customer_email=order.customer_email,
            line_items_json=[
                {
                    "title": item.title,
                    "product_id": item.product_id,
                    "variant_id": item.variant_id,
                    "product_handle": item.product_handle,
                    "quantity": item.quantity,
                    "price": str(item.price),
                }
                for item in order.line_items
            ],
            created_at=order.created_at,
            processed_at=order.created_at,
            customer_journey_ready=order.customer_journey_ready,
        )
        saved_order = await self._attr_repo.save_order(order_record)

        # Check if journey data is ready
        if not order.customer_journey_ready:
            logger.info("Order %s journey not ready, saved for retry", order.id)
            return AttributionResult(
                success=True,
                order_gid=order.id,
                journey_ready=False,
            )

        # Extract last-touch UTM content for attribution
        attribution = order.attribution
        if not attribution or not attribution.last_visit or not attribution.last_visit.utm_content:
            logger.debug("Order %s has no UTM attribution data", order.id)
            return AttributionResult(
                success=True,
                order_gid=order.id,
                attributed=False,
            )

        last_utm_content = attribution.last_visit.utm_content

        # Verify UTM content matches a known post
        matching_links = await self._utm_repo.get_by_post_id(last_utm_content)
        if not matching_links:
            logger.debug(
                "Order %s UTM content '%s' doesn't match any known post",
                order.id,
                last_utm_content,
            )
            return AttributionResult(
                success=True,
                order_gid=order.id,
                attributed=False,
            )

        # Create attributions
        attributions: list[OrderAttributionRecord] = []

        # Last-touch attribution (carries revenue)
        last_visit = attribution.last_visit
        attributions.append(OrderAttributionRecord(
            shopify_order_id=saved_order.id,
            post_id=last_utm_content,
            attribution_type=AttributionType.LAST_TOUCH.value,
            revenue_attributed=order.total_price,
            touchpoint_index=0,
            visit_occurred_at=last_visit.occurred_at,
            utm_source=last_visit.utm_source,
            utm_medium=last_visit.utm_medium,
            utm_campaign=last_visit.utm_campaign,
            utm_content=last_visit.utm_content,
        ))

        # Multi-touch recording (revenue=0 for non-last-touch)
        for idx, moment in enumerate(attribution.moments):
            if not moment.utm_content:
                continue
            # Skip if same as last-touch (already recorded)
            if (moment.occurred_at == last_visit.occurred_at
                    and moment.utm_content == last_visit.utm_content):
                continue
            # Verify this moment's UTM matches a known post
            moment_links = await self._utm_repo.get_by_post_id(moment.utm_content)
            if moment_links:
                attributions.append(OrderAttributionRecord(
                    shopify_order_id=saved_order.id,
                    post_id=moment.utm_content,
                    attribution_type=AttributionType.MULTI_TOUCH.value,
                    revenue_attributed=Decimal("0.00"),
                    touchpoint_index=idx + 1,
                    visit_occurred_at=moment.occurred_at,
                    utm_source=moment.utm_source,
                    utm_medium=moment.utm_medium,
                    utm_campaign=moment.utm_campaign,
                    utm_content=moment.utm_content,
                ))

        await self._attr_repo.save_attributions(attributions)

        logger.info(
            "Attributed order %s to post %s (%d touchpoints)",
            order.id,
            last_utm_content,
            len(attributions),
        )

        return AttributionResult(
            success=True,
            order_gid=order.id,
            attributed=True,
            journey_ready=True,
        )

    async def process_orders_batch(
        self, orders: list[ShopifyOrder]
    ) -> BatchAttributionResult:
        """Process multiple orders with partial failure handling.

        Task 4.3: Same pattern as InstagramMetricsCollector.collect_batch().

        Args:
            orders: List of ShopifyOrder DTOs

        Returns:
            BatchAttributionResult with counts and errors
        """
        if not orders:
            return BatchAttributionResult()

        succeeded = 0
        failed = 0
        errors: dict[str, str] = {}

        for order in orders:
            try:
                result = await self.process_order(order)
                if result.success:
                    succeeded += 1
                else:
                    failed += 1
                    errors[order.id] = result.error_message or "Unknown error"
            except Exception as e:
                failed += 1
                errors[order.id] = str(e)
                logger.warning("Failed to process order %s: %s", order.id, e)

        logger.info(
            "Batch attribution complete: %d/%d succeeded, %d failed",
            succeeded,
            len(orders),
            failed,
        )

        return BatchAttributionResult(
            total=len(orders),
            succeeded=succeeded,
            failed=failed,
            errors=errors,
        )


__all__ = [
    "AttributionResult",
    "AttributionService",
    "BatchAttributionResult",
]
