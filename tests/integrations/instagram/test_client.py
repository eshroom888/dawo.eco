"""Tests for Instagram Graph API publishing client.

Tests cover:
- Container creation workflow
- Status polling with various outcomes
- Successful publishing
- Error handling for API failures
- Rate limiting awareness
- Media insights collection (Story 7-1)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from integrations.instagram.client import (
    InstagramPublishClient,
    InstagramPublishClientProtocol,
    PublishResult,
    ContainerStatus,
    InstagramPublishError,
    MediaInsightsResult,
)


class TestInstagramPublishClientInit:
    """Tests for InstagramPublishClient initialization."""

    def test_init_valid_credentials(self):
        """Should initialize with valid credentials."""
        client = InstagramPublishClient(
            access_token="valid_token",
            business_account_id="123456789",
        )
        assert client._access_token == "valid_token"
        assert client._business_account_id == "123456789"

    def test_init_empty_access_token_raises(self):
        """Should raise ValueError for empty access token."""
        with pytest.raises(ValueError, match="access_token is required"):
            InstagramPublishClient(
                access_token="",
                business_account_id="123456789",
            )

    def test_init_empty_business_account_id_raises(self):
        """Should raise ValueError for empty business account ID."""
        with pytest.raises(ValueError, match="business_account_id is required"):
            InstagramPublishClient(
                access_token="valid_token",
                business_account_id="",
            )

    def test_init_custom_timeout(self):
        """Should accept custom timeout value."""
        client = InstagramPublishClient(
            access_token="token",
            business_account_id="123",
            timeout=60.0,
        )
        assert client._timeout == 60.0

    def test_init_custom_poll_settings(self):
        """Should accept custom polling settings."""
        client = InstagramPublishClient(
            access_token="token",
            business_account_id="123",
            max_poll_attempts=10,
            poll_interval=1.0,
        )
        assert client._max_poll_attempts == 10
        assert client._poll_interval == 1.0


class TestInstagramPublishClientProtocol:
    """Tests for protocol compliance."""

    def test_client_implements_protocol(self):
        """Client should implement InstagramPublishClientProtocol."""
        client = InstagramPublishClient(
            access_token="token",
            business_account_id="123",
        )
        assert isinstance(client, InstagramPublishClientProtocol)


class TestContainerStatus:
    """Tests for ContainerStatus enum."""

    def test_all_status_values(self):
        """Should have all expected status values."""
        assert ContainerStatus.EXPIRED.value == "EXPIRED"
        assert ContainerStatus.ERROR.value == "ERROR"
        assert ContainerStatus.FINISHED.value == "FINISHED"
        assert ContainerStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert ContainerStatus.PUBLISHED.value == "PUBLISHED"


class TestPublishResult:
    """Tests for PublishResult dataclass."""

    def test_successful_result(self):
        """Should create successful result with media_id."""
        result = PublishResult(
            success=True,
            media_id="12345",
            container_id="67890",
        )
        assert result.success is True
        assert result.media_id == "12345"
        assert result.container_id == "67890"
        assert result.error_message is None

    def test_failed_result(self):
        """Should create failed result with error details."""
        result = PublishResult(
            success=False,
            error_message="Rate limit exceeded",
            error_code=4,
        )
        assert result.success is False
        assert result.media_id is None
        assert result.error_message == "Rate limit exceeded"
        assert result.error_code == 4

    def test_result_is_frozen(self):
        """Result should be immutable."""
        result = PublishResult(success=True, media_id="123")
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore


class TestInstagramPublishError:
    """Tests for InstagramPublishError exception."""

    def test_error_with_message_only(self):
        """Should create error with just message."""
        error = InstagramPublishError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.error_code is None
        assert error.error_subcode is None

    def test_error_with_codes(self):
        """Should store error codes."""
        error = InstagramPublishError(
            "Rate limited",
            error_code=4,
            error_subcode=123,
        )
        assert error.error_code == 4
        assert error.error_subcode == 123


class TestGetContainerStatus:
    """Tests for get_container_status method."""

    @pytest.fixture
    def client(self):
        """Create client instance."""
        return InstagramPublishClient(
            access_token="test_token",
            business_account_id="123456",
        )

    @pytest.mark.asyncio
    async def test_status_finished(self, client):
        """Should return FINISHED status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status_code": "FINISHED"}

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            status = await client.get_container_status("container_123")

        assert status == ContainerStatus.FINISHED

    @pytest.mark.asyncio
    async def test_status_in_progress(self, client):
        """Should return IN_PROGRESS status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status_code": "IN_PROGRESS"}

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            status = await client.get_container_status("container_123")

        assert status == ContainerStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_status_error(self, client):
        """Should return ERROR status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status_code": "ERROR"}

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            status = await client.get_container_status("container_123")

        assert status == ContainerStatus.ERROR

    @pytest.mark.asyncio
    async def test_status_api_error_raises(self, client):
        """Should raise InstagramPublishError on API error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid token",
                "code": 190,
            }
        }

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with pytest.raises(InstagramPublishError, match="Invalid token"):
                await client.get_container_status("container_123")


class TestCreateContainer:
    """Tests for _create_container method."""

    @pytest.fixture
    def client(self):
        """Create client instance."""
        return InstagramPublishClient(
            access_token="test_token",
            business_account_id="123456",
        )

    @pytest.mark.asyncio
    async def test_create_container_success(self, client):
        """Should return container ID on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "container_abc123"}

        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            container_id = await client._create_container(
                image_url="https://example.com/image.jpg",
                caption="Test caption #test",
            )

        assert container_id == "container_abc123"

    @pytest.mark.asyncio
    async def test_create_container_with_location(self, client):
        """Should include location_id when provided."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "container_123"}

        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await client._create_container(
                image_url="https://example.com/image.jpg",
                caption="Test",
                location_id="location_456",
            )

        # Verify location_id was included in request
        call_kwargs = mock_post.call_args.kwargs
        assert "location_456" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_create_container_no_id_raises(self, client):
        """Should raise if no container ID in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}

        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(InstagramPublishError, match="No container ID"):
                await client._create_container(
                    image_url="https://example.com/image.jpg",
                    caption="Test",
                )


class TestPublishContainer:
    """Tests for _publish_container method."""

    @pytest.fixture
    def client(self):
        """Create client instance."""
        return InstagramPublishClient(
            access_token="test_token",
            business_account_id="123456",
        )

    @pytest.mark.asyncio
    async def test_publish_container_success(self, client):
        """Should return media ID on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "media_xyz789"}

        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            media_id = await client._publish_container("container_123")

        assert media_id == "media_xyz789"

    @pytest.mark.asyncio
    async def test_publish_container_no_id_raises(self, client):
        """Should raise if no media ID in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}

        with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(InstagramPublishError, match="No media ID"):
                await client._publish_container("container_123")


class TestPublishImage:
    """Tests for publish_image method (full workflow)."""

    @pytest.fixture
    def client(self):
        """Create client instance with fast polling."""
        return InstagramPublishClient(
            access_token="test_token",
            business_account_id="123456",
            poll_interval=0.01,  # Fast for testing
            max_poll_attempts=3,
        )

    @pytest.mark.asyncio
    async def test_publish_image_success(self, client):
        """Should successfully publish image through full workflow."""
        with patch.object(
            client, "_create_container", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "container_123"

            with patch.object(
                client, "get_container_status", new_callable=AsyncMock
            ) as mock_status:
                mock_status.return_value = ContainerStatus.FINISHED

                with patch.object(
                    client, "_publish_container", new_callable=AsyncMock
                ) as mock_publish:
                    mock_publish.return_value = "media_456"

                    result = await client.publish_image(
                        image_url="https://example.com/image.jpg",
                        caption="Test caption",
                    )

        assert result.success is True
        assert result.media_id == "media_456"
        assert result.container_id == "container_123"

    @pytest.mark.asyncio
    async def test_publish_image_container_error(self, client):
        """Should handle container ERROR status."""
        with patch.object(
            client, "_create_container", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "container_123"

            with patch.object(
                client, "get_container_status", new_callable=AsyncMock
            ) as mock_status:
                mock_status.return_value = ContainerStatus.ERROR

                result = await client.publish_image(
                    image_url="https://example.com/image.jpg",
                    caption="Test",
                )

        assert result.success is False
        assert result.container_id == "container_123"
        assert "ERROR" in result.error_message

    @pytest.mark.asyncio
    async def test_publish_image_api_error(self, client):
        """Should handle API errors gracefully."""
        with patch.object(
            client, "_create_container", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = InstagramPublishError("Rate limited", error_code=4)

            result = await client.publish_image(
                image_url="https://example.com/image.jpg",
                caption="Test",
            )

        assert result.success is False
        assert "Rate limited" in result.error_message
        assert result.error_code == 4

    @pytest.mark.asyncio
    async def test_publish_image_timeout(self, client):
        """Should handle timeout errors gracefully."""
        with patch.object(
            client, "_create_container", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = httpx.TimeoutException("Connection timed out")

            result = await client.publish_image(
                image_url="https://example.com/image.jpg",
                caption="Test",
            )

        assert result.success is False
        assert "timed out" in result.error_message.lower()


class TestWaitForContainer:
    """Tests for _wait_for_container polling method."""

    @pytest.fixture
    def client(self):
        """Create client with fast polling."""
        return InstagramPublishClient(
            access_token="test_token",
            business_account_id="123456",
            poll_interval=0.01,
            max_poll_attempts=3,
        )

    @pytest.mark.asyncio
    async def test_wait_returns_immediately_on_finished(self, client):
        """Should return immediately when status is FINISHED."""
        with patch.object(
            client, "get_container_status", new_callable=AsyncMock
        ) as mock_status:
            mock_status.return_value = ContainerStatus.FINISHED

            status = await client._wait_for_container("container_123")

        assert status == ContainerStatus.FINISHED
        assert mock_status.call_count == 1

    @pytest.mark.asyncio
    async def test_wait_polls_until_finished(self, client):
        """Should poll until FINISHED."""
        with patch.object(
            client, "get_container_status", new_callable=AsyncMock
        ) as mock_status:
            # First two calls return IN_PROGRESS, third returns FINISHED
            mock_status.side_effect = [
                ContainerStatus.IN_PROGRESS,
                ContainerStatus.IN_PROGRESS,
                ContainerStatus.FINISHED,
            ]

            status = await client._wait_for_container("container_123")

        assert status == ContainerStatus.FINISHED
        assert mock_status.call_count == 3

    @pytest.mark.asyncio
    async def test_wait_returns_error_status(self, client):
        """Should return early on ERROR status."""
        with patch.object(
            client, "get_container_status", new_callable=AsyncMock
        ) as mock_status:
            mock_status.side_effect = [
                ContainerStatus.IN_PROGRESS,
                ContainerStatus.ERROR,
            ]

            status = await client._wait_for_container("container_123")

        assert status == ContainerStatus.ERROR
        assert mock_status.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_timeout_returns_in_progress(self, client):
        """Should return IN_PROGRESS when max attempts reached."""
        with patch.object(
            client, "get_container_status", new_callable=AsyncMock
        ) as mock_status:
            mock_status.return_value = ContainerStatus.IN_PROGRESS

            status = await client._wait_for_container("container_123")

        assert status == ContainerStatus.IN_PROGRESS
        assert mock_status.call_count == client._max_poll_attempts


class TestCheckError:
    """Tests for _check_error method."""

    @pytest.fixture
    def client(self):
        """Create client instance."""
        return InstagramPublishClient(
            access_token="test_token",
            business_account_id="123456",
        )

    def test_no_error_passes(self, client):
        """Should not raise when no error in data."""
        data = {"id": "123", "status": "ok"}
        client._check_error(data)  # Should not raise

    def test_error_raises_with_message(self, client):
        """Should raise with error message."""
        data = {
            "error": {
                "message": "Invalid access token",
                "code": 190,
            }
        }
        with pytest.raises(InstagramPublishError) as exc_info:
            client._check_error(data)

        assert "Invalid access token" in str(exc_info.value)
        assert exc_info.value.error_code == 190

    def test_error_raises_with_subcode(self, client):
        """Should include error subcode."""
        data = {
            "error": {
                "message": "Error",
                "code": 100,
                "error_subcode": 456,
            }
        }
        with pytest.raises(InstagramPublishError) as exc_info:
            client._check_error(data)

        assert exc_info.value.error_subcode == 456


class TestContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Should work as async context manager."""
        async with InstagramPublishClient(
            access_token="token",
            business_account_id="123",
        ) as client:
            assert isinstance(client, InstagramPublishClient)


# === Story 7-1: Media Insights Tests ===


class TestMediaInsightsResult:
    """Tests for MediaInsightsResult dataclass (Task 3.5)."""

    def test_create_with_all_fields(self):
        """Should create result with all metric fields."""
        result = MediaInsightsResult(
            success=True,
            media_id="17890012345678901",
            impressions=1000,
            reach=800,
            likes=200,
            comments=50,
            saved=30,
            shares=15,
            total_interactions=295,
        )
        assert result.success is True
        assert result.impressions == 1000
        assert result.plays is None
        assert result.avg_watch_time_ms is None

    def test_create_with_reel_metrics(self):
        """Should support reel-specific metrics (Task 3.2)."""
        result = MediaInsightsResult(
            success=True,
            media_id="17890012345678901",
            impressions=5000,
            reach=3000,
            likes=500,
            comments=80,
            saved=60,
            shares=40,
            total_interactions=680,
            plays=10000,
            avg_watch_time_ms=4500,
        )
        assert result.plays == 10000
        assert result.avg_watch_time_ms == 4500

    def test_failed_result(self):
        """Should create failed result with error."""
        result = MediaInsightsResult(
            success=False,
            media_id="17890012345678901",
            error_message="API error",
        )
        assert result.success is False
        assert result.error_message == "API error"
        assert result.impressions == 0

    def test_result_is_frozen(self):
        """Result should be immutable."""
        result = MediaInsightsResult(
            success=True,
            media_id="123",
        )
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore

    def test_raw_response_stored(self):
        """Should store raw API response for debugging."""
        raw = {"data": [{"name": "impressions", "values": [{"value": 100}]}]}
        result = MediaInsightsResult(
            success=True,
            media_id="123",
            raw_response=raw,
        )
        assert result.raw_response == raw


class TestGetMediaInsightsUpdated:
    """Tests for updated get_media_insights method (Task 3.1, 3.2, 3.5)."""

    @pytest.fixture
    def client(self):
        """Create client instance."""
        return InstagramPublishClient(
            access_token="test_token",
            business_account_id="123456",
        )

    @pytest.mark.asyncio
    async def test_insights_success_image_post(self, client):
        """Should return MediaInsightsResult with correct metrics (Task 3.1)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"name": "impressions", "values": [{"value": 1000}]},
                {"name": "reach", "values": [{"value": 800}]},
                {"name": "likes", "values": [{"value": 200}]},
                {"name": "comments", "values": [{"value": 50}]},
                {"name": "saved", "values": [{"value": 30}]},
                {"name": "shares", "values": [{"value": 15}]},
                {"name": "total_interactions", "values": [{"value": 295}]},
            ]
        }

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_media_insights("media_123")

        assert isinstance(result, MediaInsightsResult)
        assert result.success is True
        assert result.media_id == "media_123"
        assert result.impressions == 1000
        assert result.reach == 800
        assert result.likes == 200
        assert result.comments == 50
        assert result.saved == 30
        assert result.shares == 15
        assert result.total_interactions == 295
        assert result.plays is None
        assert result.avg_watch_time_ms is None

    @pytest.mark.asyncio
    async def test_insights_uses_correct_metrics(self, client):
        """Should request non-deprecated metrics (Task 3.1)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await client.get_media_insights("media_123")

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        metric_str = params.get("metric", "")
        # Must NOT contain deprecated 'engagement'
        assert "engagement" not in metric_str
        # Must contain total_interactions (replacement)
        assert "total_interactions" in metric_str

    @pytest.mark.asyncio
    async def test_insights_reel_metrics(self, client):
        """Should include reel metrics for VIDEO media type (Task 3.2)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"name": "impressions", "values": [{"value": 5000}]},
                {"name": "reach", "values": [{"value": 3000}]},
                {"name": "likes", "values": [{"value": 500}]},
                {"name": "comments", "values": [{"value": 80}]},
                {"name": "saved", "values": [{"value": 60}]},
                {"name": "shares", "values": [{"value": 40}]},
                {"name": "total_interactions", "values": [{"value": 680}]},
                {"name": "ig_reels_aggregated_all_plays_count", "values": [{"value": 10000}]},
                {"name": "ig_reels_avg_watch_time", "values": [{"value": 4500}]},
            ]
        }

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_media_insights("media_123", media_type="VIDEO")

        assert result.plays == 10000
        assert result.avg_watch_time_ms == 4500

    @pytest.mark.asyncio
    async def test_insights_api_error_returns_failed_result(self, client):
        """Should return failed MediaInsightsResult on API error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {
                "message": "Unsupported get request",
                "code": 100,
            }
        }

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_media_insights("media_123")

        assert isinstance(result, MediaInsightsResult)
        assert result.success is False
        assert "Unsupported get request" in result.error_message

    @pytest.mark.asyncio
    async def test_insights_timeout_returns_failed_result(self, client):
        """Should handle timeout gracefully."""
        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Connection timed out")
            result = await client.get_media_insights("media_123")

        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_insights_stores_raw_response(self, client):
        """Should include raw API response in result."""
        raw_data = {
            "data": [
                {"name": "impressions", "values": [{"value": 100}]},
                {"name": "reach", "values": [{"value": 80}]},
                {"name": "likes", "values": [{"value": 50}]},
                {"name": "comments", "values": [{"value": 10}]},
                {"name": "saved", "values": [{"value": 5}]},
                {"name": "shares", "values": [{"value": 3}]},
                {"name": "total_interactions", "values": [{"value": 68}]},
            ]
        }
        mock_response = MagicMock()
        mock_response.json.return_value = raw_data

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_media_insights("media_123")

        assert result.raw_response == raw_data

    @pytest.mark.asyncio
    async def test_insights_with_rate_limit_tracker(self, client):
        """Should count calls against rate limit tracker (Task 3.4)."""
        tracker = MagicMock()
        client._rate_limit_tracker = tracker

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}

        with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await client.get_media_insights("media_123")

        tracker.check_and_use.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_insights_protocol_has_method(self):
        """Task 3.3: get_media_insights should be in protocol."""
        assert hasattr(InstagramPublishClientProtocol, "get_media_insights")
