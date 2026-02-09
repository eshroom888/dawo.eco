"""Publishing services for DAWO.ECO content pipeline.

Story 4-5: Instagram Graph API Auto-Publishing
Story 4-7: Discord Publish Notifications (PublishingService integration)

This module provides publishing services for automated content publishing
to social media platforms.

Services:
    - InstagramPublisher: Publishes content to Instagram via Graph API
    - PublishingService: Orchestrates publishing with notification hooks (Story 4-7)

Usage:
    from core.publishing import InstagramPublisher, PublishResult, PublishingService

    publisher = InstagramPublisher(instagram_client, retry_middleware)
    result = await publisher.publish(item)
    if result.success:
        print(f"Published: {result.instagram_post_id}")

    # With notifications (Story 4-7):
    service = PublishingService(publisher, notifier, event_emitter)
    result = await service.publish_approval_item(item, image_url)
"""

from core.publishing.instagram_publisher import (
    InstagramPublisher,
    InstagramPublisherProtocol,
    PublishResult,
)
from core.publishing.publishing_service import (
    PublishingService,
    PublishingServiceProtocol,
)
from core.publishing.metrics import (
    PublishMetrics,
    HealthStatus,
    PublishMetricsCollector,
    PublishMetricsCollectorProtocol,
    get_metrics_collector,
)
from core.publishing.events import (
    PublishEvent,
    PublishEventType,
    PublishEventEmitter,
    get_publish_events,
    publish_events,
)

__all__ = [
    # Publisher
    "InstagramPublisher",
    "InstagramPublisherProtocol",
    "PublishResult",
    # Publishing Service (Story 4-7)
    "PublishingService",
    "PublishingServiceProtocol",
    # Metrics
    "PublishMetrics",
    "HealthStatus",
    "PublishMetricsCollector",
    "PublishMetricsCollectorProtocol",
    "get_metrics_collector",
    # Events (Story 4-5, Task 3.6)
    "PublishEvent",
    "PublishEventType",
    "PublishEventEmitter",
    "get_publish_events",
    "publish_events",
]
