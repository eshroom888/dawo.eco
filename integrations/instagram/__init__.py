"""Instagram Graph API integration for publishing content.

This module provides an Instagram publishing client using the Graph API.
Supports single image posts with captions and hashtags.

Architecture Compliance:
- Configuration injected via constructor
- Async-first design with polling
- Graceful error handling
"""

from integrations.instagram.client import (
    InstagramPublishClient,
    InstagramPublishClientProtocol,
    PublishResult,
    ContainerStatus,
    InstagramPublishError,
)

__all__ = [
    "InstagramPublishClient",
    "InstagramPublishClientProtocol",
    "PublishResult",
    "ContainerStatus",
    "InstagramPublishError",
]
