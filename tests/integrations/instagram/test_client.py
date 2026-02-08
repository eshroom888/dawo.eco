"""Tests for Instagram Graph API publishing client.

Tests cover:
- Container creation workflow
- Status polling with various outcomes
- Successful publishing
- Error handling for API failures
- Rate limiting awareness
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
