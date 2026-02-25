"""Tests for RetryMiddleware health registry integration.

Story 7-10, Task 2.4: Middleware extension tests.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from teams.dawo.middleware.retry import RetryConfig, RetryMiddleware, RetryResult
from teams.dawo.middleware.http_client import RetryableHttpClient


@pytest.fixture
def config():
    """RetryConfig with fast settings for tests."""
    return RetryConfig(
        max_retries=2,
        base_delay=0.01,
        max_delay=0.02,
        backoff_multiplier=2.0,
        timeout=1.0,
    )


@pytest.fixture
def registry_mock():
    """Mock ServiceHealthRegistry."""
    mock = AsyncMock()
    mock.record_success = AsyncMock()
    mock.record_failure = AsyncMock()
    mock.get_status = AsyncMock()
    return mock


class TestRetryMiddlewareBackwardCompat:
    """RetryMiddleware works without registry (backward compat)."""

    @pytest.mark.asyncio
    async def test_works_without_registry(self, config):
        """RetryMiddleware works when no registry provided."""
        middleware = RetryMiddleware(config)

        async def success_op():
            return "ok"

        result = await middleware.execute_with_retry(success_op, "test")
        assert result.success is True
        assert result.response == "ok"

    @pytest.mark.asyncio
    async def test_none_registry_no_errors(self, config):
        """No errors when registry is None (default)."""
        middleware = RetryMiddleware(config, service_health_registry=None)

        async def success_op():
            return "ok"

        result = await middleware.execute_with_retry(success_op, "test")
        assert result.success is True


class TestRetryMiddlewareHealthRecording:
    """RetryMiddleware records health with registry."""

    @pytest.mark.asyncio
    async def test_records_success(self, config, registry_mock):
        """RetryMiddleware records success on successful API call."""
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        async def success_op():
            return "ok"

        result = await middleware.execute_with_retry(success_op, "instagram_get")
        assert result.success is True
        registry_mock.record_success.assert_awaited_once_with("instagram_get")

    @pytest.mark.asyncio
    async def test_records_failure_on_exhausted_retries(self, config, registry_mock):
        """RetryMiddleware records failure when retries exhausted (is_incomplete)."""
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        call_count = 0

        async def failing_op():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        result = await middleware.execute_with_retry(failing_op, "instagram_post")
        assert result.is_incomplete is True
        registry_mock.record_failure.assert_awaited()
        # Should record the last error
        args = registry_mock.record_failure.call_args
        assert args[0][0] == "instagram_post"

    @pytest.mark.asyncio
    async def test_records_failure_on_non_retryable_error(self, config, registry_mock):
        """RetryMiddleware records failure on non-retryable 4xx error."""
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        async def not_found_op():
            request = httpx.Request("GET", "https://api.example.com")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("Not Found", request=request, response=response)

        result = await middleware.execute_with_retry(not_found_op, "shopify_get")
        assert result.success is False
        assert result.is_incomplete is False
        registry_mock.record_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_registry_failure_doesnt_block(self, config, registry_mock):
        """Registry failure in record_success doesn't block the result."""
        registry_mock.record_success.side_effect = Exception("Redis down")
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        async def success_op():
            return "ok"

        result = await middleware.execute_with_retry(success_op, "test")
        assert result.success is True
        assert result.response == "ok"


class TestRetryMiddlewarePreCheck:
    """Pre-check optimization: skip API when unhealthy + cache available."""

    @pytest.mark.asyncio
    async def test_skips_api_when_unhealthy_and_cache_available(self, config, registry_mock):
        """When service is unhealthy AND cache_fallback provided, skip API call."""
        from core.degradation.models import ServiceHealthStatus

        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="shopify",
            status="unhealthy",
            consecutive_failures=15,
        )
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        api_called = False

        async def api_op():
            nonlocal api_called
            api_called = True
            return "fresh_data"

        result = await middleware.execute_with_retry(
            api_op, "shopify_get", cache_fallback="cached_product_data"
        )

        assert api_called is False
        assert result.success is True
        assert result.response == "cached_product_data"

    @pytest.mark.asyncio
    async def test_proceeds_when_unhealthy_but_no_cache(self, config, registry_mock):
        """When service is unhealthy but no cache_fallback, proceed with API call."""
        from core.degradation.models import ServiceHealthStatus

        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram",
            status="unhealthy",
            consecutive_failures=15,
        )
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        async def api_op():
            return "api_response"

        result = await middleware.execute_with_retry(api_op, "instagram_post")

        assert result.success is True
        assert result.response == "api_response"

    @pytest.mark.asyncio
    async def test_proceeds_when_degraded_with_cache(self, config, registry_mock):
        """When service is degraded (not unhealthy), proceed with API call even if cache exists."""
        from core.degradation.models import ServiceHealthStatus

        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="shopify",
            status="degraded",
            consecutive_failures=5,
        )
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        async def api_op():
            return "fresh_data"

        result = await middleware.execute_with_retry(
            api_op, "shopify_get", cache_fallback="cached_data"
        )

        assert result.success is True
        assert result.response == "fresh_data"

    @pytest.mark.asyncio
    async def test_proceeds_when_healthy_with_cache(self, config, registry_mock):
        """When service is healthy, always call API regardless of cache."""
        from core.degradation.models import ServiceHealthStatus

        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="shopify",
            status="healthy",
            consecutive_failures=0,
        )
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        async def api_op():
            return "fresh_data"

        result = await middleware.execute_with_retry(
            api_op, "shopify_get", cache_fallback="cached_data"
        )

        assert result.success is True
        assert result.response == "fresh_data"

    @pytest.mark.asyncio
    async def test_no_precheck_without_registry(self, config):
        """Without registry, no pre-check happens even with cache_fallback."""
        middleware = RetryMiddleware(config)

        async def api_op():
            return "fresh_data"

        result = await middleware.execute_with_retry(
            api_op, "shopify_get", cache_fallback="cached_data"
        )

        assert result.success is True
        assert result.response == "fresh_data"

    @pytest.mark.asyncio
    async def test_precheck_registry_failure_proceeds_with_api(self, config, registry_mock):
        """If registry.get_status fails during pre-check, proceed with API call."""
        registry_mock.get_status.side_effect = Exception("Redis down")
        middleware = RetryMiddleware(config, service_health_registry=registry_mock)

        async def api_op():
            return "fresh_data"

        result = await middleware.execute_with_retry(
            api_op, "shopify_get", cache_fallback="cached_data"
        )

        assert result.success is True
        assert result.response == "fresh_data"


class TestRetryableHttpClientRegistry:
    """RetryableHttpClient passes registry to middleware."""

    def test_accepts_registry_param(self, config, registry_mock):
        """RetryableHttpClient constructor accepts service_health_registry."""
        client = RetryableHttpClient(
            config,
            api_name="instagram",
            service_health_registry=registry_mock,
        )
        assert client._middleware._service_health_registry is registry_mock

    def test_registry_defaults_to_none(self, config):
        """RetryableHttpClient defaults registry to None."""
        client = RetryableHttpClient(config, api_name="instagram")
        assert client._middleware._service_health_registry is None
