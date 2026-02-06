"""Retry middleware dataclasses and core structures.

This module provides the core retry configuration and result types
for the DAWO retry middleware system.

Architecture Compliance:
- Configuration is injected via constructor (NEVER loads files directly)
- Team Builder is responsible for loading config and injecting it
- Uses dataclasses for all configuration and result structures

Usage:
    config = RetryConfig(max_retries=3, base_delay=1.0)
    # Pass config to RetryMiddleware via constructor injection
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger(__name__)

# HTTP status codes that warrant retry
RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}

# Exceptions that warrant retry
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.NetworkError,
    asyncio.TimeoutError,
)


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior.

    Contains all settings needed for exponential backoff retry logic.
    Injected via constructor - NEVER load from files directly.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        timeout: Request timeout in seconds (default: 30.0)
        max_rate_limit_wait: Maximum wait for 429 rate limits (default: 300)

    Raises:
        ValueError: If any configuration value is invalid
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    timeout: float = 30.0
    max_rate_limit_wait: int = 300

    def __post_init__(self) -> None:
        """Validate configuration values on initialization."""
        errors = []

        if self.max_retries < 1:
            errors.append(f"max_retries must be >= 1, got {self.max_retries}")

        if self.base_delay <= 0:
            errors.append(f"base_delay must be > 0, got {self.base_delay}")

        if self.max_delay <= 0:
            errors.append(f"max_delay must be > 0, got {self.max_delay}")

        if self.backoff_multiplier < 1:
            errors.append(f"backoff_multiplier must be >= 1, got {self.backoff_multiplier}")

        if self.timeout <= 0:
            errors.append(f"timeout must be > 0, got {self.timeout}")

        if self.max_rate_limit_wait < 0:
            errors.append(f"max_rate_limit_wait must be >= 0, got {self.max_rate_limit_wait}")

        if self.base_delay > self.max_delay:
            errors.append(
                f"base_delay ({self.base_delay}) cannot exceed max_delay ({self.max_delay})"
            )

        if errors:
            raise ValueError(f"Invalid RetryConfig: {'; '.join(errors)}")


@dataclass
class RetryResult:
    """Result of a retry-wrapped operation.

    Supports graceful degradation - operations are marked `is_incomplete`
    rather than raising exceptions, allowing callers to continue.

    Attributes:
        success: True if operation succeeded
        response: Response data if successful
        attempts: Number of attempts made
        last_error: Error message from last failed attempt
        is_incomplete: True if exhausted retries (for graceful degradation)
        operation_id: ID for queued operations (if queued for later retry)
    """

    success: bool
    response: Optional[Any] = None
    attempts: int = 0
    last_error: Optional[str] = None
    is_incomplete: bool = False
    operation_id: Optional[str] = None


class RetryMiddleware:
    """Retry middleware with exponential backoff for external API calls.

    All external API calls MUST go through this middleware.
    Configuration is injected via constructor - NEVER loads files directly.

    Features:
    - Exponential backoff: 1s, 2s, 4s (configurable)
    - Jitter to prevent thundering herd (±10%)
    - Max delay cap
    - Rate limit (429) handling
    - Graceful degradation (returns is_incomplete, not exceptions)

    Usage:
        config = RetryConfig(max_retries=3, base_delay=1.0)
        middleware = RetryMiddleware(config)
        delay = middleware._calculate_delay(attempt=2)  # 2.0 seconds
    """

    def __init__(self, config: RetryConfig) -> None:
        """Initialize retry middleware with injected configuration.

        Args:
            config: RetryConfig with retry behavior settings
        """
        self._config = config

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter.

        Formula: base_delay * multiplier^(attempt-1)
        Then add jitter (±10%) to prevent thundering herd.
        Finally cap at max_delay.

        Args:
            attempt: The attempt number (1-indexed)

        Returns:
            Delay in seconds before next retry

        Example:
            attempt 1: 1s (base_delay)
            attempt 2: 2s (base_delay * 2^1)
            attempt 3: 4s (base_delay * 2^2)
        """
        base_delay = self._config.base_delay
        multiplier = self._config.backoff_multiplier
        max_delay = self._config.max_delay

        # Exponential backoff: base * multiplier^(attempt-1)
        delay = base_delay * (multiplier ** (attempt - 1))

        # Cap at max_delay
        delay = min(delay, max_delay)

        # Add jitter (±10%) to prevent thundering herd
        # random.random() returns [0, 1), so (random() * 2 - 1) gives [-1, 1)
        jitter = delay * 0.1 * (random.random() * 2 - 1)
        delay = delay + jitter

        return delay

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error warrants retry.

        Retryable errors:
        - HTTP 5xx (server errors)
        - HTTP 429 (rate limit - handled specially elsewhere)
        - Connection errors
        - Timeout errors

        Non-retryable errors:
        - HTTP 4xx (except 429) - client errors
        - Other exceptions

        Args:
            error: The exception that occurred

        Returns:
            True if the error should trigger a retry
        """
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in RETRYABLE_STATUS_CODES
        return isinstance(error, RETRYABLE_EXCEPTIONS)

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a 429 rate limit response."""
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code == 429
        return False

    def _parse_retry_after(self, retry_after: Optional[str]) -> int:
        """Parse Retry-After header value.

        Handles:
        - Seconds format: "120" (wait 120 seconds)
        - HTTP-date format: "Wed, 21 Oct 2015 07:28:00 GMT"

        Args:
            retry_after: The Retry-After header value, or None

        Returns:
            Wait duration in seconds, capped at max_rate_limit_wait
        """
        from datetime import datetime
        from email.utils import parsedate_to_datetime

        DEFAULT_RATE_LIMIT_WAIT = 60  # 1 minute default

        if retry_after is None:
            return DEFAULT_RATE_LIMIT_WAIT

        # Try parsing as seconds first (most common)
        try:
            wait_seconds = int(retry_after)
            return min(wait_seconds, self._config.max_rate_limit_wait)
        except ValueError:
            pass

        # Try parsing as HTTP-date format (RFC 7231)
        try:
            retry_date = parsedate_to_datetime(retry_after)
            now = datetime.now(retry_date.tzinfo)
            wait_seconds = (retry_date - now).total_seconds()

            # If date is in the past, use default
            if wait_seconds <= 0:
                return DEFAULT_RATE_LIMIT_WAIT

            return min(int(wait_seconds), self._config.max_rate_limit_wait)
        except (ValueError, TypeError):
            pass

        # Invalid format - use default
        return DEFAULT_RATE_LIMIT_WAIT

    async def execute_with_retry(
        self,
        operation: Callable[[], Any],
        context: str,
    ) -> RetryResult:
        """Execute an operation with retry logic.

        Implements exponential backoff with graceful degradation.
        Does NOT raise exceptions - returns RetryResult instead.

        Special handling for 429 rate limits:
        - Uses Retry-After header for wait duration
        - Does NOT count against max_retries

        Args:
            operation: Async callable to execute
            context: Description for logging (e.g., "instagram_publish")

        Returns:
            RetryResult with success/failure status and response data
        """
        last_error: Optional[str] = None
        attempt = 0
        total_calls = 0  # Track total calls including rate limit retries

        while attempt < self._config.max_retries:
            total_calls += 1

            try:
                response = await operation()
                return RetryResult(
                    success=True,
                    response=response,
                    attempts=attempt + 1,
                )

            except httpx.HTTPStatusError as e:
                last_error = str(e)

                # Special handling for 429 rate limit
                if self._is_rate_limit_error(e):
                    retry_after = e.response.headers.get("Retry-After")
                    wait_seconds = self._parse_retry_after(retry_after)
                    logger.warning(
                        f"[{context}] Rate limited (429). Waiting {wait_seconds}s "
                        f"(Retry-After: {retry_after}). NOT counting against retries."
                    )
                    await asyncio.sleep(wait_seconds)
                    # Do NOT increment attempt - 429 doesn't count
                    continue

                # Check if retryable
                if not self._is_retryable_error(e):
                    # Non-retryable error (4xx except 429)
                    logger.warning(
                        f"[{context}] Non-retryable error (HTTP {e.response.status_code}): {e}"
                    )
                    return RetryResult(
                        success=False,
                        attempts=attempt + 1,
                        last_error=last_error,
                        is_incomplete=False,  # Not incomplete, just failed
                    )

                # Retryable error (5xx) - increment attempt
                attempt += 1
                if attempt < self._config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"[{context}] Retry attempt {attempt}/{self._config.max_retries} "
                        f"after HTTP {e.response.status_code}. Waiting {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

            except RETRYABLE_EXCEPTIONS as e:
                last_error = str(e)
                attempt += 1

                if attempt < self._config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"[{context}] Retry attempt {attempt}/{self._config.max_retries} "
                        f"after {type(e).__name__}. Waiting {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

            except Exception as e:
                # Unexpected error - don't retry
                last_error = str(e)
                logger.error(f"[{context}] Unexpected error: {e}")
                return RetryResult(
                    success=False,
                    attempts=attempt + 1,
                    last_error=last_error,
                    is_incomplete=False,
                )

        # All retries exhausted - graceful degradation
        logger.error(
            f"[{context}] All {self._config.max_retries} retries exhausted. "
            f"Last error: {last_error}"
        )
        return RetryResult(
            success=False,
            attempts=self._config.max_retries,
            last_error=last_error,
            is_incomplete=True,  # Mark as incomplete for graceful degradation
        )


# =============================================================================
# CONFIG LOADING UTILITIES (for Team Builder use only)
# =============================================================================

import json
from pathlib import Path


def load_retry_config(config_path: Optional[Path] = None) -> dict:
    """Load retry configuration from JSON file.

    This function is for Team Builder use ONLY.
    Individual agents should NEVER call this directly.

    Args:
        config_path: Path to config file. Defaults to config/dawo_retry_config.json

    Returns:
        Raw config dict ready for get_retry_config_for_api

    Raises:
        FileNotFoundError: If config file does not exist
        json.JSONDecodeError: If config file is not valid JSON
    """
    if config_path is None:
        config_path = Path("config/dawo_retry_config.json")

    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Retry config not found at '{config_path}'. "
            f"Ensure config/dawo_retry_config.json exists in project root."
        )


def get_retry_config_for_api(raw_config: dict, api_name: str) -> RetryConfig:
    """Get RetryConfig for a specific API with overrides applied.

    Merges API-specific overrides with defaults to create RetryConfig.

    Args:
        raw_config: Raw config dict from load_retry_config
        api_name: API name (instagram, discord, orshot, shopify)

    Returns:
        RetryConfig with API-specific overrides applied
    """
    defaults = raw_config.get("default", {})
    overrides = raw_config.get("api_overrides", {}).get(api_name, {})

    # Merge: overrides take precedence over defaults
    merged = {**defaults, **overrides}

    return RetryConfig(
        max_retries=merged.get("max_retries", 3),
        base_delay=merged.get("base_delay", 1.0),
        max_delay=merged.get("max_delay", 60.0),
        backoff_multiplier=merged.get("backoff_multiplier", 2.0),
        timeout=merged.get("timeout", 30.0),
        max_rate_limit_wait=merged.get("max_rate_limit_wait", 300),
    )
