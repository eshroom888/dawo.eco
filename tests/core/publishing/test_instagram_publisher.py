"""Tests for InstagramPublisher service.

Story 4-5, Task 9.1-9.2: Unit tests for Instagram publishing.
Tests cover:
- Successful publish flow
- Container creation failure
- Publish step failure
- Caption truncation
- Hashtag limits
- Retry logic
- Error classification
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, patch

from core.publishing.instagram_publisher import (
    InstagramPublisher,
    PublishResult,
)
from integrations.instagram import PublishResult as InstagramPublishResult


class MockInstagramClient:
    """Mock Instagram client for testing."""

    def __init__(
        self,
        publish_success: bool = True,
        media_id: str = "17891234567890123",
        container_id: str = "container_123",
        permalink: str = "https://www.instagram.com/p/ABC123/",
        error_message: str = None,
    ):
        self.publish_success = publish_success
        self.media_id = media_id
        self.container_id = container_id
        self.permalink = permalink
        self.error_message = error_message
        self.publish_image_called = False
        self.last_caption = None

    async def publish_image(
        self,
        image_url: str,
        caption: str,
        location_id: str = None,
    ) -> InstagramPublishResult:
        """Mock publish_image method."""
        self.publish_image_called = True
        self.last_caption = caption

        if self.publish_success:
            return InstagramPublishResult(
                success=True,
                media_id=self.media_id,
                container_id=self.container_id,
            )
        else:
            return InstagramPublishResult(
                success=False,
                error_message=self.error_message or "Mock error",
            )

    async def get_permalink(self, media_id: str) -> str:
        """Mock get_permalink method."""
        return self.permalink


class MockRetryMiddleware:
    """Mock retry middleware that executes operation once."""

    async def execute_with_retry(self, operation, context: str):
        """Execute operation without retry logic."""
        try:
            response = await operation()
            # Check if response indicates failure (e.g., response.success is False)
            if hasattr(response, "success") and not response.success:
                return Mock(
                    success=False,
                    response=response,
                    attempts=1,
                    last_error=getattr(response, "error_message", "Operation failed"),
                )
            return Mock(
                success=True,
                response=response,
                attempts=1,
                last_error=None,
            )
        except Exception as e:
            return Mock(
                success=False,
                response=None,
                attempts=1,
                last_error=str(e),
            )


class TestInstagramPublisher:
    """Tests for InstagramPublisher service."""

    @pytest.fixture
    def mock_client(self):
        """Create a successful mock client."""
        return MockInstagramClient(publish_success=True)

    @pytest.fixture
    def mock_retry(self):
        """Create a mock retry middleware."""
        return MockRetryMiddleware()

    @pytest.fixture
    def publisher(self, mock_client, mock_retry):
        """Create a publisher with mocks."""
        return InstagramPublisher(mock_client, mock_retry)

    @pytest.mark.asyncio
    async def test_successful_publish(self, publisher, mock_client):
        """Test successful publish returns complete result."""
        result = await publisher.publish(
            image_url="https://example.com/image.jpg",
            caption="Test caption",
            hashtags=["test", "instagram"],
        )

        assert result.success is True
        assert result.instagram_post_id == mock_client.media_id
        assert result.permalink == mock_client.permalink
        assert result.published_at is not None
        assert result.error_message is None
        assert result.latency_seconds > 0
        assert mock_client.publish_image_called

    @pytest.mark.asyncio
    async def test_publish_without_hashtags(self, publisher, mock_client):
        """Test publish works without hashtags."""
        result = await publisher.publish(
            image_url="https://example.com/image.jpg",
            caption="Caption without hashtags",
        )

        assert result.success is True
        assert "#" not in mock_client.last_caption

    @pytest.mark.asyncio
    async def test_publish_with_hashtags(self, publisher, mock_client):
        """Test hashtags are appended to caption."""
        result = await publisher.publish(
            image_url="https://example.com/image.jpg",
            caption="Base caption",
            hashtags=["test", "instagram"],
        )

        assert result.success is True
        assert "#test" in mock_client.last_caption
        assert "#instagram" in mock_client.last_caption

    @pytest.mark.asyncio
    async def test_caption_truncation(self, publisher, mock_client):
        """Test long captions are truncated."""
        long_caption = "x" * 3000  # Exceeds 2200 limit

        result = await publisher.publish(
            image_url="https://example.com/image.jpg",
            caption=long_caption,
        )

        assert result.success is True
        assert len(mock_client.last_caption) <= 2200

    @pytest.mark.asyncio
    async def test_hashtag_limit(self, publisher, mock_client):
        """Test max 30 hashtags enforced."""
        many_hashtags = [f"tag{i}" for i in range(50)]  # 50 hashtags

        result = await publisher.publish(
            image_url="https://example.com/image.jpg",
            caption="Caption",
            hashtags=many_hashtags,
        )

        assert result.success is True
        # Count hashtags in caption
        hashtag_count = mock_client.last_caption.count("#")
        assert hashtag_count <= 30

    @pytest.mark.asyncio
    async def test_publish_failure(self, mock_retry):
        """Test publish failure returns error result."""
        failing_client = MockInstagramClient(
            publish_success=False,
            error_message="Container creation failed",
        )
        publisher = InstagramPublisher(failing_client, mock_retry)

        result = await publisher.publish(
            image_url="https://example.com/image.jpg",
            caption="Test",
        )

        assert result.success is False
        assert result.instagram_post_id is None
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_rate_limit_error_is_retryable(self, publisher):
        """Test rate limit errors allow retry."""
        error_msg = "Rate limit exceeded"
        is_retryable = publisher._is_retryable_error_message(error_msg)
        assert is_retryable is True

    @pytest.mark.asyncio
    async def test_invalid_token_not_retryable(self, publisher):
        """Test invalid token errors don't allow retry."""
        error_msg = "Invalid access token"
        is_retryable = publisher._is_retryable_error_message(error_msg)
        assert is_retryable is False

    @pytest.mark.asyncio
    async def test_invalid_media_not_retryable(self, publisher):
        """Test invalid media errors don't allow retry."""
        error_msg = "Invalid media URL"
        is_retryable = publisher._is_retryable_error_message(error_msg)
        assert is_retryable is False

    @pytest.mark.asyncio
    async def test_policy_violation_not_retryable(self, publisher):
        """Test policy violation errors don't allow retry."""
        error_msg = "Policy violation detected"
        is_retryable = publisher._is_retryable_error_message(error_msg)
        assert is_retryable is False

    @pytest.mark.asyncio
    async def test_server_error_is_retryable(self, publisher):
        """Test server errors allow retry."""
        error_msg = "Internal server error"
        is_retryable = publisher._is_retryable_error_message(error_msg)
        assert is_retryable is True

    def test_prepare_caption_no_hashtags(self, publisher):
        """Test caption preparation without hashtags."""
        caption = "Simple caption"
        result = publisher._prepare_caption(caption, None)
        assert result == caption

    def test_prepare_caption_with_hashtags(self, publisher):
        """Test caption preparation with hashtags."""
        caption = "Caption"
        hashtags = ["one", "two"]
        result = publisher._prepare_caption(caption, hashtags)
        assert result == "Caption #one #two"

    def test_prepare_caption_truncates_long_text(self, publisher):
        """Test caption truncation preserves hashtag space."""
        long_caption = "x" * 2200
        hashtags = ["tag"]
        result = publisher._prepare_caption(long_caption, hashtags)
        assert len(result) <= 2200
        assert "#tag" in result


class TestPublishResult:
    """Tests for PublishResult dataclass."""

    def test_success_result_defaults(self):
        """Test successful result has correct defaults."""
        result = PublishResult(
            success=True,
            instagram_post_id="123",
            permalink="https://instagram.com/p/123",
            published_at=datetime.now(UTC),
        )
        assert result.success is True
        assert result.error_message is None
        assert result.retry_allowed is True

    def test_failure_result(self):
        """Test failure result fields."""
        result = PublishResult(
            success=False,
            error_message="API error",
            retry_allowed=False,
        )
        assert result.success is False
        assert result.instagram_post_id is None
        assert result.error_message == "API error"
        assert result.retry_allowed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
