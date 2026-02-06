"""Tests for retry middleware dataclasses and basic structure.

Tests verify:
- RetryConfig dataclass has required fields (AC #1)
- RetryResult dataclass has required fields (AC #2)
- Config injection pattern, NOT direct file loading
- Validation of configuration values
- Exponential backoff delay calculation (AC #1)
"""

import pytest
from dataclasses import fields
from unittest.mock import patch

from teams.dawo.middleware import (
    RetryConfig,
    RetryResult,
    RetryMiddleware,
)


class TestRetryConfigDataclass:
    """Test RetryConfig dataclass structure (AC #1)."""

    def test_retryconfig_has_max_retries_field(self) -> None:
        """RetryConfig should have max_retries field."""
        field_names = [f.name for f in fields(RetryConfig)]
        assert "max_retries" in field_names

    def test_retryconfig_has_base_delay_field(self) -> None:
        """RetryConfig should have base_delay field."""
        field_names = [f.name for f in fields(RetryConfig)]
        assert "base_delay" in field_names

    def test_retryconfig_has_max_delay_field(self) -> None:
        """RetryConfig should have max_delay field."""
        field_names = [f.name for f in fields(RetryConfig)]
        assert "max_delay" in field_names

    def test_retryconfig_has_backoff_multiplier_field(self) -> None:
        """RetryConfig should have backoff_multiplier field."""
        field_names = [f.name for f in fields(RetryConfig)]
        assert "backoff_multiplier" in field_names

    def test_retryconfig_creation_with_valid_values(self) -> None:
        """Should create RetryConfig with valid values."""
        config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
        )
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0

    def test_retryconfig_has_timeout_field(self) -> None:
        """RetryConfig should have timeout field for request timeouts."""
        field_names = [f.name for f in fields(RetryConfig)]
        assert "timeout" in field_names

    def test_retryconfig_has_max_rate_limit_wait_field(self) -> None:
        """RetryConfig should have max_rate_limit_wait field."""
        field_names = [f.name for f in fields(RetryConfig)]
        assert "max_rate_limit_wait" in field_names

    def test_retryconfig_default_values(self) -> None:
        """RetryConfig should have sensible defaults matching AC #1."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.backoff_multiplier == 2.0


class TestRetryResultDataclass:
    """Test RetryResult dataclass structure (AC #2)."""

    def test_retryresult_has_success_field(self) -> None:
        """RetryResult should have success field."""
        field_names = [f.name for f in fields(RetryResult)]
        assert "success" in field_names

    def test_retryresult_has_response_field(self) -> None:
        """RetryResult should have response field."""
        field_names = [f.name for f in fields(RetryResult)]
        assert "response" in field_names

    def test_retryresult_has_attempts_field(self) -> None:
        """RetryResult should have attempts field."""
        field_names = [f.name for f in fields(RetryResult)]
        assert "attempts" in field_names

    def test_retryresult_has_last_error_field(self) -> None:
        """RetryResult should have last_error field."""
        field_names = [f.name for f in fields(RetryResult)]
        assert "last_error" in field_names

    def test_retryresult_has_is_incomplete_field(self) -> None:
        """RetryResult should have is_incomplete field for graceful degradation."""
        field_names = [f.name for f in fields(RetryResult)]
        assert "is_incomplete" in field_names

    def test_retryresult_has_operation_id_field(self) -> None:
        """RetryResult should have operation_id for queued operations."""
        field_names = [f.name for f in fields(RetryResult)]
        assert "operation_id" in field_names

    def test_retryresult_success_case(self) -> None:
        """Should create successful RetryResult."""
        result = RetryResult(
            success=True,
            response={"data": "test"},
            attempts=1,
        )
        assert result.success is True
        assert result.response == {"data": "test"}
        assert result.attempts == 1
        assert result.is_incomplete is False

    def test_retryresult_incomplete_case(self) -> None:
        """Should create incomplete RetryResult (AC #2 graceful degradation)."""
        result = RetryResult(
            success=False,
            attempts=3,
            last_error="Connection timeout",
            is_incomplete=True,
            operation_id="op-123",
        )
        assert result.success is False
        assert result.is_incomplete is True
        assert result.operation_id == "op-123"
        assert result.last_error == "Connection timeout"

    def test_retryresult_defaults(self) -> None:
        """RetryResult should have sensible defaults."""
        result = RetryResult(success=True)
        assert result.response is None
        assert result.attempts == 0
        assert result.last_error is None
        assert result.is_incomplete is False
        assert result.operation_id is None


class TestModuleExports:
    """Test that all required types are exported from __init__.py."""

    def test_retryconfig_is_exported(self) -> None:
        """RetryConfig should be importable from teams.dawo.middleware."""
        from teams.dawo.middleware import RetryConfig
        assert RetryConfig is not None

    def test_retryresult_is_exported(self) -> None:
        """RetryResult should be importable from teams.dawo.middleware."""
        from teams.dawo.middleware import RetryResult
        assert RetryResult is not None

    def test_retrymiddleware_is_exported(self) -> None:
        """RetryMiddleware should be importable from teams.dawo.middleware."""
        from teams.dawo.middleware import RetryMiddleware
        assert RetryMiddleware is not None


# =============================================================================
# EXPONENTIAL BACKOFF TESTS (Task 2)
# =============================================================================


@pytest.fixture
def default_config() -> RetryConfig:
    """Create default retry configuration."""
    return RetryConfig()


@pytest.fixture
def middleware(default_config: RetryConfig) -> RetryMiddleware:
    """Create RetryMiddleware with default config."""
    return RetryMiddleware(default_config)


class TestExponentialBackoff:
    """Test exponential backoff delay calculation (AC #1)."""

    def test_attempt_1_delay_is_base_delay(self, middleware: RetryMiddleware) -> None:
        """Attempt 1 should use base_delay (1s by default)."""
        # Mock random to return 0 (no jitter) for predictable testing
        with patch("random.random", return_value=0.5):  # 0.5 -> 0 jitter
            delay = middleware._calculate_delay(1)
        # With 0.5 random, jitter = delay * 0.1 * (0.5 * 2 - 1) = 0
        assert delay == pytest.approx(1.0, rel=0.15)  # Allow 15% for jitter

    def test_attempt_2_delay_is_2_seconds(self, middleware: RetryMiddleware) -> None:
        """Attempt 2 should be 2s (1 * 2^1)."""
        with patch("random.random", return_value=0.5):
            delay = middleware._calculate_delay(2)
        assert delay == pytest.approx(2.0, rel=0.15)

    def test_attempt_3_delay_is_4_seconds(self, middleware: RetryMiddleware) -> None:
        """Attempt 3 should be 4s (1 * 2^2)."""
        with patch("random.random", return_value=0.5):
            delay = middleware._calculate_delay(3)
        assert delay == pytest.approx(4.0, rel=0.15)

    def test_exponential_formula(self, middleware: RetryMiddleware) -> None:
        """Verify exponential formula: base_delay * multiplier^(attempt-1)."""
        with patch("random.random", return_value=0.5):
            delay_1 = middleware._calculate_delay(1)
            delay_2 = middleware._calculate_delay(2)
            delay_3 = middleware._calculate_delay(3)

        # delay_2 should be approximately 2 * delay_1
        assert delay_2 == pytest.approx(delay_1 * 2, rel=0.15)
        # delay_3 should be approximately 2 * delay_2
        assert delay_3 == pytest.approx(delay_2 * 2, rel=0.15)


class TestJitter:
    """Test jitter implementation to prevent thundering herd (AC #1)."""

    def test_jitter_adds_variation(self, middleware: RetryMiddleware) -> None:
        """Jitter should add variation to delays."""
        delays = []
        for _ in range(10):
            delay = middleware._calculate_delay(1)
            delays.append(delay)

        # With jitter, not all delays should be exactly the same
        unique_delays = set(round(d, 6) for d in delays)
        assert len(unique_delays) > 1, "Jitter should produce variation in delays"

    def test_jitter_within_10_percent(self, middleware: RetryMiddleware) -> None:
        """Jitter should be within ±10% of base delay."""
        base = 1.0  # default base_delay
        for _ in range(100):
            delay = middleware._calculate_delay(1)
            # Should be within 10% of base (0.9 to 1.1)
            assert 0.9 <= delay <= 1.1, f"Delay {delay} outside ±10% range"


class TestMaxDelayCap:
    """Test max_delay cap functionality (AC #1)."""

    def test_delay_capped_at_max_delay(self) -> None:
        """Delays should be capped at max_delay."""
        config = RetryConfig(
            base_delay=10.0,
            max_delay=15.0,
            backoff_multiplier=2.0,
        )
        middleware = RetryMiddleware(config)

        # Attempt 3: 10 * 2^2 = 40, but should be capped at 15
        with patch("random.random", return_value=0.5):
            delay = middleware._calculate_delay(3)

        # Should be capped at max_delay (with possible jitter)
        assert delay <= 15.0 * 1.1  # Allow 10% jitter above cap

    def test_delay_not_capped_below_max(self) -> None:
        """Delays below max_delay should not be capped."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=100.0,
            backoff_multiplier=2.0,
        )
        middleware = RetryMiddleware(config)

        # Attempt 3: 1 * 2^2 = 4, well below max_delay
        with patch("random.random", return_value=0.5):
            delay = middleware._calculate_delay(3)

        # Should be approximately 4 seconds
        assert delay == pytest.approx(4.0, rel=0.15)


class TestConfigInjectionForMiddleware:
    """Test dependency injection pattern for RetryMiddleware."""

    def test_middleware_accepts_config_via_constructor(
        self, default_config: RetryConfig
    ) -> None:
        """RetryMiddleware should accept config via constructor."""
        middleware = RetryMiddleware(default_config)
        assert middleware is not None

    def test_middleware_uses_injected_config(self) -> None:
        """Middleware should use values from injected config."""
        config = RetryConfig(
            base_delay=5.0,
            backoff_multiplier=3.0,
        )
        middleware = RetryMiddleware(config)

        # Attempt 2: 5 * 3^1 = 15
        with patch("random.random", return_value=0.5):
            delay = middleware._calculate_delay(2)

        assert delay == pytest.approx(15.0, rel=0.15)


# =============================================================================
# ASYNC RETRY EXECUTION TESTS (Task 3)
# =============================================================================

import asyncio
import logging


class TestExecuteWithRetry:
    """Test async execute_with_retry method (AC #1, #2)."""

    @pytest.mark.asyncio
    async def test_successful_operation_returns_success(
        self, middleware: RetryMiddleware
    ) -> None:
        """Successful operation should return success result."""
        async def success_op():
            return {"data": "test"}

        result = await middleware.execute_with_retry(success_op, "test_context")

        assert result.success is True
        assert result.response == {"data": "test"}
        assert result.attempts == 1
        assert result.is_incomplete is False

    @pytest.mark.asyncio
    async def test_retries_on_5xx_error(self, middleware: RetryMiddleware) -> None:
        """Should retry on 5xx HTTP errors."""
        import httpx

        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = httpx.Response(503, request=httpx.Request("GET", "http://test"))
                raise httpx.HTTPStatusError("Service unavailable", request=response.request, response=response)
            return {"success": True}

        # Mock sleep to speed up test
        with patch("asyncio.sleep", return_value=None):
            result = await middleware.execute_with_retry(failing_then_success, "test")

        assert result.success is True
        assert call_count == 3
        assert result.attempts == 3

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self, middleware: RetryMiddleware) -> None:
        """Should retry on connection errors."""
        import httpx

        call_count = 0

        async def connection_error_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            return {"connected": True}

        with patch("asyncio.sleep", return_value=None):
            result = await middleware.execute_with_retry(connection_error_then_success, "test")

        assert result.success is True
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self, middleware: RetryMiddleware) -> None:
        """Should retry on timeout errors."""
        import httpx

        call_count = 0

        async def timeout_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")
            return {"data": "ok"}

        with patch("asyncio.sleep", return_value=None):
            result = await middleware.execute_with_retry(timeout_then_success, "test")

        assert result.success is True
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_returns_incomplete(
        self, middleware: RetryMiddleware
    ) -> None:
        """After max retries, should return is_incomplete=True (AC #2)."""
        import httpx

        async def always_fails():
            response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
            raise httpx.HTTPStatusError("Server error", request=response.request, response=response)

        with patch("asyncio.sleep", return_value=None):
            result = await middleware.execute_with_retry(always_fails, "test")

        assert result.success is False
        assert result.is_incomplete is True
        assert result.attempts == 3  # max_retries default
        assert result.last_error is not None

    @pytest.mark.asyncio
    async def test_4xx_errors_not_retried(self, middleware: RetryMiddleware) -> None:
        """4xx errors (except 429) should NOT be retried."""
        import httpx

        call_count = 0

        async def bad_request():
            nonlocal call_count
            call_count += 1
            response = httpx.Response(400, request=httpx.Request("GET", "http://test"))
            raise httpx.HTTPStatusError("Bad request", request=response.request, response=response)

        result = await middleware.execute_with_retry(bad_request, "test")

        assert result.success is False
        assert call_count == 1  # No retries
        assert result.is_incomplete is False  # Not incomplete, just failed

    @pytest.mark.asyncio
    async def test_401_unauthorized_not_retried(self, middleware: RetryMiddleware) -> None:
        """401 errors should NOT be retried."""
        import httpx

        call_count = 0

        async def unauthorized():
            nonlocal call_count
            call_count += 1
            response = httpx.Response(401, request=httpx.Request("GET", "http://test"))
            raise httpx.HTTPStatusError("Unauthorized", request=response.request, response=response)

        result = await middleware.execute_with_retry(unauthorized, "test")

        assert result.success is False
        assert call_count == 1


class TestGracefulDegradation:
    """Test graceful degradation - callers can continue (AC #2)."""

    @pytest.mark.asyncio
    async def test_result_allows_caller_to_continue(
        self, middleware: RetryMiddleware
    ) -> None:
        """Result should allow caller to continue after failure."""
        import httpx

        async def always_fails():
            response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
            raise httpx.HTTPStatusError("Server error", request=response.request, response=response)

        with patch("asyncio.sleep", return_value=None):
            result = await middleware.execute_with_retry(always_fails, "instagram_publish")

        # Caller can check and continue
        if result.is_incomplete:
            # This is the graceful degradation pattern
            continued = True
        else:
            continued = False

        assert continued is True
        assert result.is_incomplete is True

    @pytest.mark.asyncio
    async def test_no_exception_raised_on_failure(
        self, middleware: RetryMiddleware
    ) -> None:
        """Should NOT raise exception on failure - return result instead."""
        import httpx

        async def always_fails():
            response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
            raise httpx.HTTPStatusError("Server error", request=response.request, response=response)

        # Should NOT raise - should return result
        with patch("asyncio.sleep", return_value=None):
            result = await middleware.execute_with_retry(always_fails, "test")

        assert isinstance(result, RetryResult)


class TestLogging:
    """Test logging of retry attempts (AC #1)."""

    @pytest.mark.asyncio
    async def test_logs_retry_attempts(
        self, middleware: RetryMiddleware, caplog
    ) -> None:
        """Should log each retry attempt with context."""
        import httpx

        call_count = 0

        async def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
                raise httpx.HTTPStatusError("Server error", request=response.request, response=response)
            return {"ok": True}

        with caplog.at_level(logging.WARNING):
            with patch("asyncio.sleep", return_value=None):
                await middleware.execute_with_retry(fails_twice, "instagram_api")

        # Check that retry attempts were logged
        log_text = caplog.text.lower()
        assert "retry" in log_text or "attempt" in log_text


# =============================================================================
# RATE LIMIT HANDLING TESTS (Task 4, AC #3)
# =============================================================================


class TestRateLimitHandling:
    """Test HTTP 429 rate limit handling (AC #3)."""

    @pytest.mark.asyncio
    async def test_429_waits_and_retries(self, middleware: RetryMiddleware) -> None:
        """Should wait for Retry-After duration on 429."""
        import httpx

        call_count = 0
        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        async def rate_limited_then_success():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = httpx.Response(
                    429,
                    request=httpx.Request("GET", "http://test"),
                    headers={"Retry-After": "5"}
                )
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            return {"success": True}

        with patch("asyncio.sleep", side_effect=mock_sleep):
            result = await middleware.execute_with_retry(rate_limited_then_success, "test")

        assert result.success is True
        assert call_count == 2
        # Should have waited for Retry-After duration
        assert 5 in sleep_calls or any(4.5 <= s <= 5.5 for s in sleep_calls)

    @pytest.mark.asyncio
    async def test_429_does_not_count_against_max_retries(
        self, middleware: RetryMiddleware
    ) -> None:
        """429 waits should NOT count against max_retries."""
        import httpx

        call_count = 0

        async def multiple_429_then_500():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # First 2 calls: rate limited (should not count)
                response = httpx.Response(
                    429,
                    request=httpx.Request("GET", "http://test"),
                    headers={"Retry-After": "1"}
                )
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            elif call_count <= 5:
                # Next 3 calls: server error (should count as retries)
                response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
                raise httpx.HTTPStatusError("Server error", request=response.request, response=response)
            return {"ok": True}

        with patch("asyncio.sleep", return_value=None):
            result = await middleware.execute_with_retry(multiple_429_then_500, "test")

        # Should have: 2 rate limits (not counted) + 3 retries (max) = 5 total calls
        assert call_count == 5
        assert result.is_incomplete is True

    @pytest.mark.asyncio
    async def test_retry_after_header_seconds_format(
        self, middleware: RetryMiddleware
    ) -> None:
        """Should parse Retry-After header in seconds format."""
        import httpx

        sleep_durations = []

        async def mock_sleep(seconds):
            sleep_durations.append(seconds)

        call_count = 0

        async def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = httpx.Response(
                    429,
                    request=httpx.Request("GET", "http://test"),
                    headers={"Retry-After": "60"}
                )
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            return {"ok": True}

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await middleware.execute_with_retry(rate_limited, "test")

        # Should have waited 60 seconds (from Retry-After header)
        assert any(55 <= d <= 65 for d in sleep_durations)

    @pytest.mark.asyncio
    async def test_rate_limit_wait_capped_at_max(self, middleware: RetryMiddleware) -> None:
        """Rate limit wait should be capped at max_rate_limit_wait (5 minutes)."""
        import httpx

        sleep_durations = []

        async def mock_sleep(seconds):
            sleep_durations.append(seconds)

        call_count = 0

        async def rate_limited_long_wait():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Retry-After of 10 minutes (600 seconds) - should be capped at 5 min (300s)
                response = httpx.Response(
                    429,
                    request=httpx.Request("GET", "http://test"),
                    headers={"Retry-After": "600"}
                )
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            return {"ok": True}

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await middleware.execute_with_retry(rate_limited_long_wait, "test")

        # Should be capped at max_rate_limit_wait (300 seconds by default)
        max_wait = middleware._config.max_rate_limit_wait
        assert all(d <= max_wait for d in sleep_durations)

    @pytest.mark.asyncio
    async def test_429_without_retry_after_uses_default(
        self, middleware: RetryMiddleware
    ) -> None:
        """429 without Retry-After header should use default wait."""
        import httpx

        sleep_durations = []

        async def mock_sleep(seconds):
            sleep_durations.append(seconds)

        call_count = 0

        async def rate_limited_no_header():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # No Retry-After header
                response = httpx.Response(
                    429,
                    request=httpx.Request("GET", "http://test"),
                )
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            return {"ok": True}

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await middleware.execute_with_retry(rate_limited_no_header, "test")

        # Should have waited with a default value (60 seconds as per story)
        assert len(sleep_durations) > 0
        assert any(50 <= d <= 70 for d in sleep_durations)  # Around 60s default


class TestParseRetryAfter:
    """Test _parse_retry_after helper method."""

    def test_parse_seconds_format(self, middleware: RetryMiddleware) -> None:
        """Should parse Retry-After in seconds format."""
        result = middleware._parse_retry_after("120")
        assert result == 120

    def test_parse_missing_header_returns_default(
        self, middleware: RetryMiddleware
    ) -> None:
        """Missing Retry-After should return default 60 seconds."""
        result = middleware._parse_retry_after(None)
        assert result == 60

    def test_parse_invalid_value_returns_default(
        self, middleware: RetryMiddleware
    ) -> None:
        """Invalid Retry-After value should return default."""
        result = middleware._parse_retry_after("not-a-number")
        assert result == 60

    def test_parse_capped_at_max(self, middleware: RetryMiddleware) -> None:
        """Parse should cap at max_rate_limit_wait."""
        max_wait = middleware._config.max_rate_limit_wait
        result = middleware._parse_retry_after("9999")
        assert result == max_wait
