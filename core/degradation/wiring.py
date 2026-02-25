"""Health recording wiring helpers for existing integration points.

Story 7-10, Task 6: Centralized fire-and-forget health recording.

Provides a single helper function that existing code paths call to record
success/failure. The helper is resilient — None registry or exceptions
are swallowed. This prevents health recording from ever blocking
production operations.

Usage (in any integration point):
    from core.degradation.wiring import record_service_health

    await record_service_health(registry, "instagram", success=True)
    await record_service_health(registry, "shopify", success=False, error="Timeout")
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def record_service_health(
    registry,
    service_name: str,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Fire-and-forget health recording for any service.

    Args:
        registry: ServiceHealthRegistry or None (backward compat)
        service_name: Service name (e.g., "instagram", "shopify")
        success: Whether the operation succeeded
        error: Error message if failed
    """
    if registry is None:
        return

    try:
        if success:
            await registry.record_success(service_name)
        else:
            await registry.record_failure(service_name, error or "Unknown error")
    except Exception as e:
        logger.warning("Health recording failed for %s: %s", service_name, e)
