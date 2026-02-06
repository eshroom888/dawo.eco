"""DAWO Retry Middleware Module.

Provides retry functionality with exponential backoff for external API calls.
All external API calls MUST go through this middleware.

Key Components:
- RetryConfig: Configuration dataclass for retry behavior
- RetryResult: Result dataclass supporting graceful degradation
- RetryPipeline: Integrated pipeline (retry + queue + alert)

Architecture Compliance:
- Configuration injected via constructor (Team Builder's responsibility)
- NEVER load config files directly in this module
- All external calls must use this middleware

Usage:
    from teams.dawo.middleware import RetryConfig, RetryResult, RetryPipeline

    config = RetryConfig(max_retries=3, base_delay=1.0)
    pipeline = RetryPipeline(config, queue, alerts)
    result = await pipeline.execute("instagram_publish", api_call)
"""

from teams.dawo.middleware.retry import (
    RetryConfig,
    RetryResult,
    RetryMiddleware,
    load_retry_config,
    get_retry_config_for_api,
)
from teams.dawo.middleware.operation_queue import (
    IncompleteOperation,
    OperationQueue,
    RedisClientProtocol,
)
from teams.dawo.middleware.discord_alerts import (
    DiscordAlertManager,
    DiscordClientProtocol,
)
from teams.dawo.middleware.http_client import RetryableHttpClient
from teams.dawo.middleware.integration import RetryPipeline

__all__ = [
    # Core retry types
    "RetryConfig",
    "RetryResult",
    "RetryMiddleware",
    "RetryableHttpClient",
    # Operation queue
    "IncompleteOperation",
    "OperationQueue",
    # Discord alerts
    "DiscordAlertManager",
    # Integration pipeline
    "RetryPipeline",
    # Config loading (Team Builder only)
    "load_retry_config",
    "get_retry_config_for_api",
    # Protocol types for dependency injection
    "RedisClientProtocol",
    "DiscordClientProtocol",
]
