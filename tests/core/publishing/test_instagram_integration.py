"""Integration tests for Instagram publishing.

Story 4-5, Task 9.3: Integration test full publish flow with test Instagram account.

IMPORTANT: These tests require a real Instagram Business Account configured.
They are skipped by default in CI/CD and should only be run manually against
a sandbox/test Instagram account.

Prerequisites:
1. Create a test Instagram Business Account
2. Set up Facebook App with Instagram Graph API access
3. Configure environment variables:
   - INSTAGRAM_TEST_ACCESS_TOKEN: Long-lived access token for test account
   - INSTAGRAM_TEST_ACCOUNT_ID: Business account ID
   - INSTAGRAM_INTEGRATION_TESTS: Set to "1" to enable these tests

To run these tests manually:
    INSTAGRAM_INTEGRATION_TESTS=1 \\
    INSTAGRAM_TEST_ACCESS_TOKEN=<token> \\
    INSTAGRAM_TEST_ACCOUNT_ID=<id> \\
    pytest tests/core/publishing/test_instagram_integration.py -v

NOTE: These tests will create real posts on Instagram. Use a dedicated test account.
"""

import os
import pytest
from datetime import datetime

# Check if integration tests are enabled
INTEGRATION_TESTS_ENABLED = os.environ.get("INSTAGRAM_INTEGRATION_TESTS") == "1"
SKIP_REASON = "Instagram integration tests disabled. Set INSTAGRAM_INTEGRATION_TESTS=1 to enable."


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_REASON)
class TestInstagramPublishingIntegration:
    """Integration tests for Instagram publishing flow.

    Story 4-5, Task 9.3: Full publish flow integration tests.

    These tests verify the complete publishing pipeline against
    a real Instagram API endpoint using a test account.
    """

    @pytest.fixture
    def test_credentials(self):
        """Get Instagram test credentials from environment."""
        access_token = os.environ.get("INSTAGRAM_TEST_ACCESS_TOKEN")
        account_id = os.environ.get("INSTAGRAM_TEST_ACCOUNT_ID")

        if not access_token or not account_id:
            pytest.skip("Instagram test credentials not configured")

        return {
            "access_token": access_token,
            "account_id": account_id,
        }

    @pytest.fixture
    def test_image_url(self):
        """Publicly accessible test image URL.

        This URL must be accessible by Instagram servers.
        Using a placeholder service for testing.
        """
        # Using a public placeholder image
        return "https://picsum.photos/1080/1080"

    @pytest.fixture
    def test_caption(self):
        """Test caption for integration tests."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return f"Integration test post - {timestamp} #dawotest #integrationtest"

    @pytest.mark.asyncio
    async def test_full_publish_flow(
        self,
        test_credentials,
        test_image_url,
        test_caption,
    ):
        """Test complete publish flow: container creation -> publish -> verify.

        This test:
        1. Creates an Instagram client with test credentials
        2. Creates a media container
        3. Waits for container to be ready
        4. Publishes the container
        5. Verifies the post was created
        6. Retrieves the permalink

        WARNING: This creates a real post on Instagram!
        """
        from integrations.instagram import InstagramPublishClient

        client = InstagramPublishClient(
            access_token=test_credentials["access_token"],
            business_account_id=test_credentials["account_id"],
        )

        try:
            result = await client.publish_image(
                image_url=test_image_url,
                caption=test_caption,
            )

            # Verify success
            assert result.success, f"Publish failed: {result.error_message}"
            assert result.media_id is not None
            assert result.container_id is not None

            # Get permalink
            permalink = await client.get_permalink(result.media_id)
            assert permalink is not None
            assert "instagram.com" in permalink

            print(f"Successfully published test post: {permalink}")

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_instagram_publisher_service(
        self,
        test_credentials,
        test_image_url,
    ):
        """Test InstagramPublisher service wrapper.

        Verifies the publisher service correctly wraps the client
        with retry middleware and returns proper PublishResult.
        """
        from core.publishing import InstagramPublisher, PublishResult
        from integrations.instagram import InstagramPublishClient
        from teams.dawo.middleware.retry import RetryMiddleware, RetryConfig

        client = InstagramPublishClient(
            access_token=test_credentials["access_token"],
            business_account_id=test_credentials["account_id"],
        )

        retry = RetryMiddleware(RetryConfig(max_retries=2, base_delay=1.0))
        publisher = InstagramPublisher(client, retry)

        try:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            result = await publisher.publish(
                image_url=test_image_url,
                caption=f"Publisher service test - {timestamp}",
                hashtags=["dawotest", "publishertest"],
            )

            assert isinstance(result, PublishResult)
            assert result.success, f"Publish failed: {result.error_message}"
            assert result.instagram_post_id is not None
            assert result.permalink is not None
            assert result.published_at is not None
            assert result.latency_seconds > 0

            print(f"Publisher service test succeeded: {result.permalink}")

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_publish_latency_under_30_seconds(
        self,
        test_credentials,
        test_image_url,
    ):
        """Verify publish completes within 30 second target (AC #2).

        Story 4-5, AC #2: Publish executes in < 30 seconds.
        """
        from core.publishing import InstagramPublisher
        from integrations.instagram import InstagramPublishClient
        from teams.dawo.middleware.retry import RetryMiddleware, RetryConfig

        client = InstagramPublishClient(
            access_token=test_credentials["access_token"],
            business_account_id=test_credentials["account_id"],
        )

        retry = RetryMiddleware(RetryConfig(max_retries=1, base_delay=0.5))
        publisher = InstagramPublisher(client, retry)

        try:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            result = await publisher.publish(
                image_url=test_image_url,
                caption=f"Latency test - {timestamp}",
            )

            assert result.success, f"Publish failed: {result.error_message}"
            assert result.latency_seconds < 30, (
                f"Publish took {result.latency_seconds}s, exceeds 30s target"
            )

            print(f"Publish completed in {result.latency_seconds:.2f}s")

        finally:
            await client.close()


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_REASON)
class TestInstagramErrorHandling:
    """Integration tests for error handling scenarios."""

    @pytest.fixture
    def test_credentials(self):
        """Get Instagram test credentials from environment."""
        access_token = os.environ.get("INSTAGRAM_TEST_ACCESS_TOKEN")
        account_id = os.environ.get("INSTAGRAM_TEST_ACCOUNT_ID")

        if not access_token or not account_id:
            pytest.skip("Instagram test credentials not configured")

        return {
            "access_token": access_token,
            "account_id": account_id,
        }

    @pytest.mark.asyncio
    async def test_invalid_image_url_fails_gracefully(self, test_credentials):
        """Test that invalid image URL returns error result, not exception."""
        from integrations.instagram import InstagramPublishClient

        client = InstagramPublishClient(
            access_token=test_credentials["access_token"],
            business_account_id=test_credentials["account_id"],
        )

        try:
            result = await client.publish_image(
                image_url="https://invalid-url-that-does-not-exist.com/image.jpg",
                caption="This should fail",
            )

            assert not result.success
            assert result.error_message is not None
            print(f"Expected failure: {result.error_message}")

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_invalid_token_returns_error(self):
        """Test that invalid access token returns error result."""
        from integrations.instagram import InstagramPublishClient

        client = InstagramPublishClient(
            access_token="invalid_token_12345",
            business_account_id="12345",
        )

        try:
            result = await client.publish_image(
                image_url="https://picsum.photos/1080/1080",
                caption="This should fail with auth error",
            )

            assert not result.success
            assert result.error_message is not None
            # Should be an auth-related error
            assert any(
                term in result.error_message.lower()
                for term in ["token", "auth", "access", "invalid"]
            )

        finally:
            await client.close()


# Marker for CI/CD to skip these tests
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires real API access)",
    )
