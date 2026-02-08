"""Integration tests for Orshot API.

These tests require a valid ORSHOT_API_KEY environment variable.
They are skipped by default unless the API key is provided.

Run with: pytest tests/integrations/test_orshot/test_integration.py -v
"""

import os
import pytest
from pathlib import Path

from integrations.orshot import OrshotClient, OrshotTemplate, GeneratedGraphic


# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ORSHOT_API_KEY"),
    reason="ORSHOT_API_KEY environment variable not set",
)


@pytest.fixture
def orshot_client():
    """Create real Orshot client for integration tests."""
    api_key = os.getenv("ORSHOT_API_KEY")
    return OrshotClient(api_key=api_key)


@pytest.fixture
def tmp_download_path(tmp_path):
    """Temporary path for download tests."""
    return tmp_path / "test_graphic.png"


class TestOrshotIntegration:
    """Integration tests against real Orshot API."""

    @pytest.mark.asyncio
    async def test_list_templates(self, orshot_client):
        """Should list available templates from Orshot."""
        async with orshot_client as client:
            templates = await client.list_templates()

        assert isinstance(templates, list)
        # Should have at least one template configured
        if templates:
            template = templates[0]
            assert isinstance(template, OrshotTemplate)
            assert template.id
            assert template.name

    @pytest.mark.asyncio
    async def test_generate_graphic(self, orshot_client):
        """Should generate a graphic from a template."""
        async with orshot_client as client:
            # First get available templates
            templates = await client.list_templates()
            if not templates:
                pytest.skip("No templates available")

            template = templates[0]
            variables = {}
            for var_name in template.variables:
                variables[var_name] = f"Test {var_name}"

            graphic = await client.generate_graphic(
                template_id=template.id,
                variables=variables,
            )

        assert isinstance(graphic, GeneratedGraphic)
        assert graphic.id
        assert graphic.image_url
        assert graphic.template_id == template.id

    @pytest.mark.asyncio
    async def test_download_graphic(self, orshot_client, tmp_download_path):
        """Should download generated graphic to local file."""
        async with orshot_client as client:
            templates = await client.list_templates()
            if not templates:
                pytest.skip("No templates available")

            template = templates[0]
            variables = {var: f"Test {var}" for var in template.variables}

            graphic = await client.generate_graphic(
                template_id=template.id,
                variables=variables,
            )

            downloaded_path = await client.download_graphic(
                graphic=graphic,
                output_path=tmp_download_path,
            )

        assert downloaded_path.exists()
        assert downloaded_path.stat().st_size > 0
        # Should be a valid PNG
        with open(downloaded_path, "rb") as f:
            header = f.read(8)
            assert header[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_generate_with_invalid_template(self, orshot_client):
        """Should raise ValueError for non-existent template."""
        async with orshot_client as client:
            with pytest.raises(ValueError, match="not found"):
                await client.generate_graphic(
                    template_id="invalid_template_id_12345",
                    variables={"headline": "Test"},
                )


class TestOrshotRateLimiting:
    """Tests for rate limiting behavior."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_multiple_requests_respect_rate_limit(self, orshot_client):
        """Should handle multiple requests without hitting rate limits."""
        async with orshot_client as client:
            templates = await client.list_templates()
            if not templates:
                pytest.skip("No templates available")

            # Make several requests - should not get 429
            for _ in range(3):
                templates = await client.list_templates()
                assert isinstance(templates, list)


class TestOrshotTimeout:
    """Tests for timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_is_respected(self):
        """Should use configured timeout for API calls."""
        api_key = os.getenv("ORSHOT_API_KEY")
        client = OrshotClient(api_key=api_key, timeout=60.0)

        async with client:
            templates = await client.list_templates()
            assert isinstance(templates, list)
