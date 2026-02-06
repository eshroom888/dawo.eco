"""Tests for code review fixes.

Tests verify all issues found during code review are properly fixed:
- H1: Discord integration interface
- H2: PUT/DELETE/PATCH HTTP methods
- H3: RetryConfig validation
- M1: HTTP-date parsing in Retry-After
- M2: DiscordAlertManager cooldown injection
- M3: OperationQueue.update_operation
- M4: RetryPipeline integration
- L1: Protocol types
- L2: Error handling in __aexit__
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from teams.dawo.middleware import (
    RetryConfig,
    RetryResult,
    RetryMiddleware,
    RetryableHttpClient,
    IncompleteOperation,
    OperationQueue,
    DiscordAlertManager,
    RetryPipeline,
    RedisClientProtocol,
    DiscordClientProtocol,
)


# =============================================================================
# H1: Discord Integration Tests
# =============================================================================


class TestDiscordIntegration:
    """Test Discord integration interface (H1 fix)."""

    def test_discord_client_protocol_exists(self) -> None:
        """DiscordClientProtocol should be importable."""
        from integrations.discord import DiscordClientProtocol
        assert DiscordClientProtocol is not None

    def test_discord_webhook_client_exists(self) -> None:
        """DiscordWebhookClient should be importable."""
        from integrations.discord import DiscordWebhookClient
        assert DiscordWebhookClient is not None

    def test_discord_webhook_client_validates_url(self) -> None:
        """Should raise ValueError for invalid webhook URL."""
        from integrations.discord import DiscordWebhookClient

        with pytest.raises(ValueError, match="valid URL"):
            DiscordWebhookClient(webhook_url="")

        with pytest.raises(ValueError, match="valid URL"):
            DiscordWebhookClient(webhook_url="not-a-url")

    def test_discord_webhook_client_accepts_valid_url(self) -> None:
        """Should accept valid webhook URL."""
        from integrations.discord import DiscordWebhookClient

        client = DiscordWebhookClient(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        assert client is not None


# =============================================================================
# H2: PUT/DELETE/PATCH HTTP Methods Tests
# =============================================================================


class TestHttpClientMethods:
    """Test new HTTP methods in RetryableHttpClient (H2 fix)."""

    @pytest.fixture
    def client(self) -> RetryableHttpClient:
        """Create RetryableHttpClient with default config."""
        return RetryableHttpClient(RetryConfig(), api_name="test")

    @pytest.mark.asyncio
    async def test_put_method_exists(self, client: RetryableHttpClient) -> None:
        """PUT method should exist and work."""
        mock_response = httpx.Response(200, json={"updated": True})

        with patch.object(client._httpx_client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = mock_response
            result = await client.put("http://example.com/api/1", json={"name": "test"})

        assert result.success is True

    @pytest.mark.asyncio
    async def test_delete_method_exists(self, client: RetryableHttpClient) -> None:
        """DELETE method should exist and work."""
        mock_response = httpx.Response(204)

        with patch.object(client._httpx_client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = mock_response
            result = await client.delete("http://example.com/api/1")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_patch_method_exists(self, client: RetryableHttpClient) -> None:
        """PATCH method should exist and work."""
        mock_response = httpx.Response(200, json={"patched": True})

        with patch.object(client._httpx_client, "patch", new_callable=AsyncMock) as mock_patch:
            mock_patch.return_value = mock_response
            result = await client.patch("http://example.com/api/1", json={"field": "value"})

        assert result.success is True

    @pytest.mark.asyncio
    async def test_put_retries_on_5xx(self, client: RetryableHttpClient) -> None:
        """PUT should retry on 5xx errors."""
        call_count = 0

        async def mock_put(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = httpx.Response(500)
                response.request = httpx.Request("PUT", "http://test")
                raise httpx.HTTPStatusError("Server error", request=response.request, response=response)
            return httpx.Response(200)

        with patch.object(client._httpx_client, "put", side_effect=mock_put):
            with patch("asyncio.sleep", return_value=None):
                result = await client.put("http://example.com")

        assert result.success is True
        assert call_count == 2


# =============================================================================
# H3: RetryConfig Validation Tests
# =============================================================================


class TestRetryConfigValidation:
    """Test RetryConfig validation (H3 fix)."""

    def test_valid_config_creates_successfully(self) -> None:
        """Valid config should create without error."""
        config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            timeout=30.0,
            max_rate_limit_wait=300,
        )
        assert config.max_retries == 3

    def test_invalid_max_retries_raises_error(self) -> None:
        """max_retries < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="max_retries must be >= 1"):
            RetryConfig(max_retries=0)

        with pytest.raises(ValueError, match="max_retries must be >= 1"):
            RetryConfig(max_retries=-1)

    def test_invalid_base_delay_raises_error(self) -> None:
        """base_delay <= 0 should raise ValueError."""
        with pytest.raises(ValueError, match="base_delay must be > 0"):
            RetryConfig(base_delay=0)

        with pytest.raises(ValueError, match="base_delay must be > 0"):
            RetryConfig(base_delay=-1.0)

    def test_invalid_timeout_raises_error(self) -> None:
        """timeout <= 0 should raise ValueError."""
        with pytest.raises(ValueError, match="timeout must be > 0"):
            RetryConfig(timeout=0)

    def test_base_delay_exceeds_max_delay_raises_error(self) -> None:
        """base_delay > max_delay should raise ValueError."""
        with pytest.raises(ValueError, match="base_delay.*cannot exceed max_delay"):
            RetryConfig(base_delay=100.0, max_delay=10.0)

    def test_invalid_backoff_multiplier_raises_error(self) -> None:
        """backoff_multiplier < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="backoff_multiplier must be >= 1"):
            RetryConfig(backoff_multiplier=0.5)


# =============================================================================
# M1: HTTP-date Parsing Tests
# =============================================================================


class TestHttpDateParsing:
    """Test HTTP-date parsing in _parse_retry_after (M1 fix)."""

    @pytest.fixture
    def middleware(self) -> RetryMiddleware:
        """Create RetryMiddleware with default config."""
        return RetryMiddleware(RetryConfig())

    def test_parses_seconds_format(self, middleware: RetryMiddleware) -> None:
        """Should parse seconds format."""
        result = middleware._parse_retry_after("120")
        assert result == 120

    def test_parses_http_date_format(self, middleware: RetryMiddleware) -> None:
        """Should parse HTTP-date format."""
        from email.utils import format_datetime
        from datetime import timedelta

        # Create a date 60 seconds in the future
        future_date = datetime.now(timezone.utc) + timedelta(seconds=60)
        http_date = format_datetime(future_date, usegmt=True)

        result = middleware._parse_retry_after(http_date)

        # Should be approximately 60 seconds (allow some tolerance)
        assert 55 <= result <= 65

    def test_past_http_date_returns_default(self, middleware: RetryMiddleware) -> None:
        """HTTP-date in the past should return default."""
        # A date in the past
        past_date = "Wed, 21 Oct 2015 07:28:00 GMT"

        result = middleware._parse_retry_after(past_date)

        # Should return default (60 seconds)
        assert result == 60


# =============================================================================
# M2: DiscordAlertManager Cooldown Injection Tests
# =============================================================================


class TestDiscordAlertManagerCooldown:
    """Test DiscordAlertManager cooldown injection (M2 fix)."""

    def test_accepts_cooldown_via_constructor(self) -> None:
        """Should accept custom cooldown via constructor."""
        mock_discord = MagicMock()
        mock_redis = MagicMock()

        manager = DiscordAlertManager(
            mock_discord, mock_redis, cooldown_seconds=600
        )

        assert manager._cooldown == 600

    def test_uses_default_when_not_specified(self) -> None:
        """Should use default cooldown when not specified."""
        mock_discord = MagicMock()
        mock_redis = MagicMock()

        manager = DiscordAlertManager(mock_discord, mock_redis)

        assert manager._cooldown == 300  # Default

    @pytest.mark.asyncio
    async def test_uses_injected_cooldown_for_rate_limiting(self) -> None:
        """Should use injected cooldown value when setting rate limit."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False

        manager = DiscordAlertManager(
            mock_discord, mock_redis, cooldown_seconds=120
        )
        await manager.send_api_error_alert("test", "error", 3, True)

        # Verify setex was called with custom cooldown
        call_args = mock_redis.setex.call_args
        assert 120 in call_args[0]


# =============================================================================
# M3: OperationQueue.update_operation Tests
# =============================================================================


class TestOperationQueueUpdate:
    """Test OperationQueue.update_operation fix (M3 fix)."""

    @pytest.mark.asyncio
    async def test_update_operation_modifies_fields(self) -> None:
        """update_operation should modify specified fields."""
        import json

        mock_redis = AsyncMock()
        existing_op = {
            "operation_id": "op-123",
            "context": "test",
            "payload": {},
            "created_at": "2026-02-06T12:00:00",
            "retry_count": 0,
            "last_attempt": None,
            "last_error": None,
        }
        mock_redis.hget.return_value = json.dumps(existing_op)

        queue = OperationQueue(mock_redis)
        now = datetime.now()
        result = await queue.update_operation(
            operation_id="op-123",
            retry_count=5,
            last_attempt=now,
            last_error="New error",
        )

        assert result is not None
        assert result.retry_count == 5
        assert result.last_error == "New error"

    @pytest.mark.asyncio
    async def test_update_operation_returns_none_if_not_found(self) -> None:
        """update_operation should return None if operation not found."""
        mock_redis = AsyncMock()
        mock_redis.hget.return_value = None

        queue = OperationQueue(mock_redis)
        result = await queue.update_operation(
            operation_id="nonexistent",
            retry_count=1,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_increment_retry_increases_count(self) -> None:
        """increment_retry should increase retry_count by 1."""
        import json

        mock_redis = AsyncMock()
        existing_op = {
            "operation_id": "op-456",
            "context": "test",
            "payload": {},
            "created_at": "2026-02-06T12:00:00",
            "retry_count": 2,
            "last_attempt": None,
            "last_error": None,
        }
        mock_redis.hget.return_value = json.dumps(existing_op)

        queue = OperationQueue(mock_redis)
        result = await queue.increment_retry("op-456", error="Retry failed")

        assert result is not None
        assert result.retry_count == 3
        assert result.last_error == "Retry failed"


# =============================================================================
# M4: RetryPipeline Integration Tests
# =============================================================================


class TestRetryPipeline:
    """Test RetryPipeline integration (M4 fix)."""

    @pytest.mark.asyncio
    async def test_successful_operation_does_not_queue(self) -> None:
        """Successful operation should not be queued or alerted."""
        config = RetryConfig()
        mock_queue = AsyncMock()
        mock_alerts = AsyncMock()

        pipeline = RetryPipeline(config, mock_queue, mock_alerts)

        async def success_op():
            return {"data": "ok"}

        result = await pipeline.execute("test_context", success_op)

        assert result.success is True
        mock_queue.queue_for_retry.assert_not_called()
        mock_alerts.send_api_error_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_incomplete_operation_is_queued_and_alerted(self) -> None:
        """Incomplete operation should be queued and alerted."""
        config = RetryConfig()
        mock_queue = AsyncMock()
        mock_queue.queue_for_retry.return_value = "op-123"
        mock_alerts = AsyncMock()

        pipeline = RetryPipeline(config, mock_queue, mock_alerts)

        async def always_fails():
            response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
            raise httpx.HTTPStatusError("Server error", request=response.request, response=response)

        with patch("asyncio.sleep", return_value=None):
            result = await pipeline.execute("instagram_publish", always_fails, {"content": "test"})

        assert result.success is False
        assert result.is_incomplete is True
        mock_queue.queue_for_retry.assert_called_once()
        mock_alerts.send_api_error_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_works_without_queue(self) -> None:
        """Pipeline should work without queue (optional dependency)."""
        config = RetryConfig()
        mock_alerts = AsyncMock()

        pipeline = RetryPipeline(config, operation_queue=None, alert_manager=mock_alerts)

        async def always_fails():
            response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
            raise httpx.HTTPStatusError("Server error", request=response.request, response=response)

        with patch("asyncio.sleep", return_value=None):
            result = await pipeline.execute("test", always_fails)

        assert result.is_incomplete is True
        # Alert should still be called
        mock_alerts.send_api_error_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_works_without_alerts(self) -> None:
        """Pipeline should work without alerts (optional dependency)."""
        config = RetryConfig()
        mock_queue = AsyncMock()
        mock_queue.queue_for_retry.return_value = "op-123"

        pipeline = RetryPipeline(config, operation_queue=mock_queue, alert_manager=None)

        async def always_fails():
            response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
            raise httpx.HTTPStatusError("Server error", request=response.request, response=response)

        with patch("asyncio.sleep", return_value=None):
            result = await pipeline.execute("test", always_fails)

        assert result.is_incomplete is True
        # Queue should still be called
        mock_queue.queue_for_retry.assert_called_once()


# =============================================================================
# L1: Protocol Types Tests
# =============================================================================


class TestProtocolTypes:
    """Test Protocol types for dependency injection (L1 fix)."""

    def test_redis_client_protocol_exported(self) -> None:
        """RedisClientProtocol should be exported from middleware."""
        from teams.dawo.middleware import RedisClientProtocol
        assert RedisClientProtocol is not None

    def test_discord_client_protocol_exported(self) -> None:
        """DiscordClientProtocol should be exported from middleware."""
        from teams.dawo.middleware import DiscordClientProtocol
        assert DiscordClientProtocol is not None

    def test_mock_implements_redis_protocol(self) -> None:
        """Mock should be recognized as implementing RedisClientProtocol."""
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.hget = AsyncMock()
        mock_redis.hgetall = AsyncMock()
        mock_redis.hdel = AsyncMock()

        # Should be able to create OperationQueue with mock
        queue = OperationQueue(mock_redis)
        assert queue is not None


# =============================================================================
# L2: Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in __aexit__ (L2 fix)."""

    @pytest.mark.asyncio
    async def test_http_client_aexit_handles_close_error(self) -> None:
        """__aexit__ should handle errors when closing client."""
        config = RetryConfig()
        client = RetryableHttpClient(config, api_name="test")

        # Mock close to raise an error
        with patch.object(client, "close", side_effect=Exception("Close failed")):
            # Should not raise - should handle gracefully
            await client.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_http_client_context_manager_handles_close_error(self) -> None:
        """Context manager should handle close errors gracefully."""
        config = RetryConfig()

        async with RetryableHttpClient(config, api_name="test") as client:
            # Mock close to fail
            original_close = client.close

            async def failing_close():
                raise Exception("Close failed")

            client.close = failing_close

        # Should complete without raising
        assert True
