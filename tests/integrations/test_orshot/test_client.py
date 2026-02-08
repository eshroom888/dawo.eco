"""Unit tests for Orshot client."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.orshot.client import (
    OrshotClient,
    OrshotTemplate,
    GeneratedGraphic,
)
from teams.dawo.middleware.retry import RetryConfig, RetryResult


class TestOrshotClientInit:
    """Test OrshotClient initialization."""

    def test_init_requires_api_key(self):
        """OrshotClient requires api_key."""
        with pytest.raises(ValueError, match="api_key is required"):
            OrshotClient(api_key="")

    def test_init_with_valid_params(self, retry_config):
        """OrshotClient initializes with valid parameters."""
        client = OrshotClient(
            api_key="test_api_key_123",
            retry_config=retry_config,
        )
        assert client._api_key == "test_api_key_123"
        assert client._base_url == "https://api.orshot.com/v1"
        assert client._timeout == 60.0

    def test_init_with_custom_base_url(self):
        """OrshotClient accepts custom base URL."""
        client = OrshotClient(
            api_key="test_api_key_123",
            base_url="https://custom.orshot.com/api",
        )
        assert client._base_url == "https://custom.orshot.com/api"

    def test_init_with_custom_timeout(self):
        """OrshotClient accepts custom timeout."""
        client = OrshotClient(
            api_key="test_api_key_123",
            timeout=120.0,
        )
        assert client._timeout == 120.0


class TestOrshotClientListTemplates:
    """Test list_templates method."""

    @pytest.mark.asyncio
    async def test_list_templates_success(
        self, mock_http_client, retry_config, templates_list_response
    ):
        """Successfully list templates."""
        mock_http_client.get.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: templates_list_response),
            attempts=1,
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            templates = await client.list_templates()

        assert len(templates) == 2
        assert templates[0].id == "tpl_abc123"
        assert templates[0].name == "DAWO Instagram Feed"
        assert templates[0].dimensions == (1080, 1080)
        assert "headline" in templates[0].variables
        assert "product_name" in templates[0].variables

    @pytest.mark.asyncio
    async def test_list_templates_empty(self, mock_http_client, retry_config):
        """Return empty list when no templates exist."""
        empty_response = {"success": True, "data": []}
        mock_http_client.get.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: empty_response),
            attempts=1,
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            templates = await client.list_templates()

        assert templates == []

    @pytest.mark.asyncio
    async def test_list_templates_api_failure(self, mock_http_client, retry_config):
        """Return empty list on API failure (graceful degradation)."""
        mock_http_client.get.return_value = RetryResult(
            success=False,
            attempts=3,
            last_error="Connection refused",
            is_incomplete=True,
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            templates = await client.list_templates()

        assert templates == []


class TestOrshotClientGenerateGraphic:
    """Test generate_graphic method."""

    @pytest.mark.asyncio
    async def test_generate_graphic_success(
        self, mock_http_client, retry_config, generate_graphic_response
    ):
        """Successfully generate a graphic."""
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: generate_graphic_response),
            attempts=1,
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            graphic = await client.generate_graphic(
                template_id="tpl_abc123",
                variables={
                    "headline": "Naturens kraft",
                    "product_name": "Løvemanke Ekstrakt",
                },
            )

        assert graphic.id == "gen_789xyz"
        assert graphic.template_id == "tpl_abc123"
        assert graphic.image_url == "https://cdn.orshot.com/renders/gen_789xyz.png"
        assert graphic.variables_used == {
            "headline": "Naturens kraft",
            "product_name": "Løvemanke Ekstrakt",
        }

    @pytest.mark.asyncio
    async def test_generate_graphic_template_not_found(
        self, mock_http_client, retry_config, template_not_found_response
    ):
        """Raise error when template not found."""
        mock_response = MagicMock()
        mock_response.json.return_value = template_not_found_response
        mock_response.status_code = 404

        mock_http_client.post.return_value = RetryResult(
            success=False,
            response=mock_response,
            attempts=1,
            last_error="Template not found",
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            with pytest.raises(ValueError, match="Template.*not found"):
                await client.generate_graphic(
                    template_id="invalid_id",
                    variables={"headline": "Test"},
                )

    @pytest.mark.asyncio
    async def test_generate_graphic_api_failure(self, mock_http_client, retry_config):
        """Raise error on API failure."""
        mock_http_client.post.return_value = RetryResult(
            success=False,
            attempts=3,
            last_error="Server error",
            is_incomplete=True,
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            with pytest.raises(RuntimeError, match="Failed to generate graphic"):
                await client.generate_graphic(
                    template_id="tpl_abc123",
                    variables={"headline": "Test"},
                )


class TestOrshotClientDownloadGraphic:
    """Test download_graphic method."""

    @pytest.mark.asyncio
    async def test_download_graphic_success(
        self, mock_http_client, retry_config, sample_image_bytes, tmp_output_path
    ):
        """Successfully download a graphic."""
        mock_response = MagicMock()
        mock_response.content = sample_image_bytes

        mock_http_client.get.return_value = RetryResult(
            success=True,
            response=mock_response,
            attempts=1,
        )

        graphic = GeneratedGraphic(
            id="gen_789xyz",
            template_id="tpl_abc123",
            image_url="https://cdn.orshot.com/renders/gen_789xyz.png",
            local_path=None,
            variables_used={"headline": "Test"},
            created_at=datetime.now(timezone.utc),
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            result_path = await client.download_graphic(graphic, tmp_output_path)

        assert result_path == tmp_output_path
        assert tmp_output_path.exists()
        assert tmp_output_path.read_bytes() == sample_image_bytes

    @pytest.mark.asyncio
    async def test_download_graphic_creates_parent_dirs(
        self, mock_http_client, retry_config, sample_image_bytes, tmp_path
    ):
        """Download creates parent directories if needed."""
        nested_path = tmp_path / "nested" / "dirs" / "graphic.png"

        mock_response = MagicMock()
        mock_response.content = sample_image_bytes

        mock_http_client.get.return_value = RetryResult(
            success=True,
            response=mock_response,
            attempts=1,
        )

        graphic = GeneratedGraphic(
            id="gen_789xyz",
            template_id="tpl_abc123",
            image_url="https://cdn.orshot.com/renders/gen_789xyz.png",
            local_path=None,
            variables_used={},
            created_at=datetime.now(timezone.utc),
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            result_path = await client.download_graphic(graphic, nested_path)

        assert result_path == nested_path
        assert nested_path.exists()

    @pytest.mark.asyncio
    async def test_download_graphic_api_failure(
        self, mock_http_client, retry_config, tmp_output_path
    ):
        """Raise error on download failure."""
        mock_http_client.get.return_value = RetryResult(
            success=False,
            attempts=3,
            last_error="Download failed",
            is_incomplete=True,
        )

        graphic = GeneratedGraphic(
            id="gen_789xyz",
            template_id="tpl_abc123",
            image_url="https://cdn.orshot.com/renders/gen_789xyz.png",
            local_path=None,
            variables_used={},
            created_at=datetime.now(timezone.utc),
        )

        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = OrshotClient(
                api_key="test_api_key_123",
                retry_config=retry_config,
            )
            with pytest.raises(RuntimeError, match="Failed to download"):
                await client.download_graphic(graphic, tmp_output_path)


class TestOrshotClientTimeout:
    """Test request timeout handling."""

    def test_default_timeout_is_60_seconds(self):
        """Default timeout is 60 seconds per story requirements."""
        client = OrshotClient(api_key="test_key")
        assert client._timeout == 60.0

    def test_custom_timeout(self):
        """Custom timeout can be specified."""
        client = OrshotClient(api_key="test_key", timeout=30.0)
        assert client._timeout == 30.0


class TestOrshotClientContextManager:
    """Test async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_http_client, retry_config):
        """Client works as async context manager."""
        with patch(
            "integrations.orshot.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            async with OrshotClient(
                api_key="test_key", retry_config=retry_config
            ) as client:
                assert client is not None

        mock_http_client.close.assert_called_once()
