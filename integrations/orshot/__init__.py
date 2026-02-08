"""Orshot integration module.

Provides branded graphics generation using Canva templates.

Components:
- OrshotClient: API client for Orshot graphics generation
- OrshotUsageTracker: Monthly usage tracking with Discord alerts
- OrshotRateLimiter: Token bucket rate limiting for API calls
"""

from integrations.orshot.client import (
    OrshotClient,
    OrshotClientProtocol,
    OrshotTemplate,
    GeneratedGraphic,
)
from integrations.orshot.usage import (
    OrshotUsageTracker,
    RedisClientProtocol,
    DiscordAlertProtocol,
)
from integrations.orshot.rate_limiter import (
    OrshotRateLimiter,
    RateLimitConfig,
)

__all__ = [
    # Client
    "OrshotClient",
    "OrshotClientProtocol",
    "OrshotTemplate",
    "GeneratedGraphic",
    # Usage tracking
    "OrshotUsageTracker",
    "RedisClientProtocol",
    "DiscordAlertProtocol",
    # Rate limiting
    "OrshotRateLimiter",
    "RateLimitConfig",
]
