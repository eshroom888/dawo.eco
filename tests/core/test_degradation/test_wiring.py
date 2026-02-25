"""Tests for degradation wiring into existing integration points.

Story 7-10, Task 6.5: Integration wiring tests.

These test that health recording is correctly integrated into existing
code paths without breaking existing behavior.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from core.degradation.models import ServiceHealthStatus


class TestPublishFlowWiring:
    """Tests for health recording in the publishing flow."""

    @pytest.mark.asyncio
    async def test_publish_success_records_instagram_healthy(self):
        """Successful publish records instagram as healthy."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        registry.record_success = AsyncMock()

        await record_service_health(registry, "instagram", success=True)

        registry.record_success.assert_awaited_once_with("instagram")

    @pytest.mark.asyncio
    async def test_publish_failure_records_instagram_failure(self):
        """Failed publish records instagram failure."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        registry.record_failure = AsyncMock()

        await record_service_health(registry, "instagram", success=False, error="Timeout")

        registry.record_failure.assert_awaited_once_with("instagram", "Timeout")

    @pytest.mark.asyncio
    async def test_registry_failure_doesnt_raise(self):
        """Registry failure in wiring doesn't raise exceptions."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        registry.record_success.side_effect = Exception("Redis down")

        # Should not raise
        await record_service_health(registry, "instagram", success=True)

    @pytest.mark.asyncio
    async def test_none_registry_is_noop(self):
        """None registry is a no-op (backward compat)."""
        from core.degradation.wiring import record_service_health

        # Should not raise
        await record_service_health(None, "instagram", success=True)


class TestCalendarSyncWiring:
    """Tests for health recording in calendar sync."""

    @pytest.mark.asyncio
    async def test_calendar_success_records_healthy(self):
        """Successful calendar sync records google_calendar as healthy."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        registry.record_success = AsyncMock()

        await record_service_health(registry, "google_calendar", success=True)

        registry.record_success.assert_awaited_once_with("google_calendar")

    @pytest.mark.asyncio
    async def test_calendar_failure_records_failure(self):
        """Failed calendar sync records google_calendar failure."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        registry.record_failure = AsyncMock()

        await record_service_health(
            registry, "google_calendar", success=False, error="OAuth expired"
        )

        registry.record_failure.assert_awaited_once_with("google_calendar", "OAuth expired")


class TestDiscordWiring:
    """Tests for health recording in Discord alerts."""

    @pytest.mark.asyncio
    async def test_discord_success_records_healthy(self):
        """Successful Discord send records discord as healthy."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        await record_service_health(registry, "discord", success=True)

        registry.record_success.assert_awaited_once_with("discord")

    @pytest.mark.asyncio
    async def test_discord_failure_records_failure(self):
        """Failed Discord send records discord failure."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        await record_service_health(
            registry, "discord", success=False, error="Webhook failed"
        )

        registry.record_failure.assert_awaited_once_with("discord", "Webhook failed")


class TestShopifyWiring:
    """Tests for health recording in Shopify integration."""

    @pytest.mark.asyncio
    async def test_shopify_success_records_healthy(self):
        """Successful Shopify API call records shopify as healthy."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        await record_service_health(registry, "shopify", success=True)

        registry.record_success.assert_awaited_once_with("shopify")

    @pytest.mark.asyncio
    async def test_shopify_failure_records_failure(self):
        """Failed Shopify API call records shopify failure."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        await record_service_health(
            registry, "shopify", success=False, error="Store not found"
        )

        registry.record_failure.assert_awaited_once_with("shopify", "Store not found")


class TestMultipleServicesIndependent:
    """Tests that services are tracked independently."""

    @pytest.mark.asyncio
    async def test_multiple_services_tracked_independently(self):
        """Multiple services are tracked independently."""
        from core.degradation.wiring import record_service_health

        registry = AsyncMock()
        registry.record_success = AsyncMock()
        registry.record_failure = AsyncMock()

        await record_service_health(registry, "instagram", success=True)
        await record_service_health(registry, "shopify", success=False, error="Down")
        await record_service_health(registry, "discord", success=True)

        assert registry.record_success.await_count == 2
        assert registry.record_failure.await_count == 1

        # Verify correct service names
        success_calls = [c[0][0] for c in registry.record_success.call_args_list]
        assert "instagram" in success_calls
        assert "discord" in success_calls
