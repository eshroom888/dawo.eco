"""Unit tests for OrshotRenderer agent."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from teams.dawo.generators.orshot_graphics import (
    OrshotRenderer,
    RenderRequest,
    RenderResult,
    ContentType,
)
from teams.dawo.generators.orshot_graphics.agent import UsageLimitExceeded
from integrations.orshot import OrshotTemplate, GeneratedGraphic


class TestOrshotRendererInit:
    """Test OrshotRenderer initialization."""

    def test_init_with_required_params(self, mock_orshot_client, mock_drive_client):
        """OrshotRenderer initializes with required parameters."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )
        assert renderer._orshot is mock_orshot_client
        assert renderer._drive is mock_drive_client
        assert renderer._usage_tracker is None

    def test_init_with_usage_tracker(
        self, mock_orshot_client, mock_drive_client, mock_usage_tracker
    ):
        """OrshotRenderer accepts optional usage tracker."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
            usage_tracker=mock_usage_tracker,
        )
        assert renderer._usage_tracker is mock_usage_tracker


class TestOrshotRendererRender:
    """Test render method."""

    @pytest.mark.asyncio
    async def test_render_success(
        self,
        mock_orshot_client,
        mock_drive_client,
        mock_usage_tracker,
        sample_feed_request,
    ):
        """Successfully render a graphic."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
            usage_tracker=mock_usage_tracker,
        )

        result = await renderer.render(sample_feed_request)

        assert result.success is True
        assert result.content_id == "content_123"
        assert result.template_id == "tpl_feed_123"
        assert result.template_name == "DAWO Feed Post"
        assert result.image_url == "https://cdn.orshot.com/renders/gen_789.png"
        assert result.dimensions == (1080, 1080)
        assert result.quality_score > 0
        assert result.usage_count == 101
        assert result.usage_warning is False

    @pytest.mark.asyncio
    async def test_render_without_usage_tracker(
        self,
        mock_orshot_client,
        mock_drive_client,
        sample_feed_request,
    ):
        """Render works without usage tracker."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(sample_feed_request)

        assert result.success is True
        assert result.usage_count == 0
        assert result.usage_warning is False

    @pytest.mark.asyncio
    async def test_render_with_specific_template(
        self,
        mock_orshot_client,
        mock_drive_client,
        sample_request_with_template,
    ):
        """Render uses specified template ID."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(sample_request_with_template)

        assert result.success is True
        assert result.template_id == "tpl_feed_123"

    @pytest.mark.asyncio
    async def test_render_auto_selects_template(
        self,
        mock_orshot_client,
        mock_drive_client,
        sample_story_request,
    ):
        """Render auto-selects template for story format."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(sample_story_request)

        assert result.success is True
        # Should select story template (1080x1920)
        assert result.template_id == "tpl_story_456"
        assert result.dimensions == (1080, 1920)

    @pytest.mark.asyncio
    async def test_render_usage_limit_exceeded(
        self,
        mock_orshot_client,
        mock_drive_client,
        mock_usage_tracker_exceeded,
        sample_feed_request,
    ):
        """Return failure when usage limit exceeded."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
            usage_tracker=mock_usage_tracker_exceeded,
        )

        result = await renderer.render(sample_feed_request)

        assert result.success is False
        assert "limit" in result.error_message.lower()
        # Should not have called generate_graphic
        mock_orshot_client.generate_graphic.assert_not_called()

    @pytest.mark.asyncio
    async def test_render_usage_warning(
        self,
        mock_orshot_client,
        mock_drive_client,
        mock_usage_tracker_warning,
        sample_feed_request,
    ):
        """Render with usage warning at 80% threshold."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
            usage_tracker=mock_usage_tracker_warning,
        )

        result = await renderer.render(sample_feed_request)

        assert result.success is True
        assert result.usage_warning is True
        assert result.usage_count == 2401

    @pytest.mark.asyncio
    async def test_render_no_templates_available(
        self,
        mock_orshot_client,
        mock_drive_client,
        sample_feed_request,
    ):
        """Return failure when no templates available."""
        mock_orshot_client.list_templates.return_value = []

        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(sample_feed_request)

        assert result.success is False
        assert "template" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_render_template_not_found(
        self,
        mock_orshot_client,
        mock_drive_client,
    ):
        """Return failure when specified template not found."""
        request = RenderRequest(
            content_id="content_xyz",
            content_type=ContentType.INSTAGRAM_FEED,
            headline="Test",
            topic="test",
            template_id="nonexistent_template",
        )

        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(request)

        assert result.success is False
        assert "template" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_render_drive_upload_failure_continues(
        self,
        mock_orshot_client,
        mock_drive_client,
        sample_feed_request,
    ):
        """Render continues when Drive upload fails (keeps local copy)."""
        mock_drive_client.upload_asset.side_effect = Exception("Drive error")

        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(sample_feed_request)

        assert result.success is True
        assert result.drive_url is None
        assert result.drive_file_id is None
        assert result.local_path is not None


class TestOrshotRendererQualityScoring:
    """Test quality score calculation."""

    @pytest.mark.asyncio
    async def test_quality_score_perfect(
        self,
        mock_orshot_client,
        mock_drive_client,
        sample_feed_request,
    ):
        """Perfect quality score when all conditions met."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(sample_feed_request)

        # Should be 10 with matching template and all variables
        assert result.quality_score >= 8.0

    @pytest.mark.asyncio
    async def test_quality_penalty_missing_variables(
        self,
        mock_orshot_client,
        mock_drive_client,
    ):
        """Quality penalty for missing required variables."""
        # Request without product_name
        request = RenderRequest(
            content_id="content_novar",
            content_type=ContentType.INSTAGRAM_FEED,
            headline="Test headline",
            topic="test",
            # product_name and date_display are missing
        )

        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(request)

        # Should have penalties for missing variables
        assert result.quality_score < 10.0

    @pytest.mark.asyncio
    async def test_quality_penalty_dimension_mismatch(
        self,
        mock_orshot_client,
        mock_drive_client,
    ):
        """Quality penalty when template dimensions don't match content type."""
        # Request story but templates only have feed dimensions
        mock_orshot_client.list_templates.return_value = [
            OrshotTemplate(
                id="tpl_wrong",
                name="Wrong Dimensions",
                canva_id="canva_wrong",
                variables=["headline"],
                dimensions=(800, 600),  # Wrong dimensions
            ),
        ]

        request = RenderRequest(
            content_id="content_dim",
            content_type=ContentType.INSTAGRAM_FEED,
            headline="Test",
            topic="test",
        )

        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        result = await renderer.render(request)

        # Should have penalties for dimension mismatch and resolution
        assert result.quality_score < 8.0


class TestOrshotRendererVariableInjection:
    """Test template variable building and sanitization."""

    @pytest.mark.asyncio
    async def test_variables_mapped_correctly(
        self,
        mock_orshot_client,
        mock_drive_client,
        sample_feed_request,
    ):
        """Variables are correctly mapped from request to template."""
        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        await renderer.render(sample_feed_request)

        # Check that generate_graphic was called with correct variables
        mock_orshot_client.generate_graphic.assert_called_once()
        call_args = mock_orshot_client.generate_graphic.call_args
        variables = call_args.kwargs["variables"]

        assert variables["headline"] == "Naturens kraft i hver kapsel"
        assert variables["product_name"] == "Løvemanke Ekstrakt"
        assert variables["date"] == "Februar 2026"

    @pytest.mark.asyncio
    async def test_long_text_is_truncated(
        self,
        mock_orshot_client,
        mock_drive_client,
    ):
        """Long text values are truncated to max length."""
        long_headline = "A" * 500  # Very long headline

        request = RenderRequest(
            content_id="content_long",
            content_type=ContentType.INSTAGRAM_FEED,
            headline=long_headline,
            topic="test",
        )

        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        await renderer.render(request)

        call_args = mock_orshot_client.generate_graphic.call_args
        variables = call_args.kwargs["variables"]

        # Headline should be truncated
        assert len(variables["headline"]) <= 203  # 200 + "..."

    @pytest.mark.asyncio
    async def test_only_template_variables_included(
        self,
        mock_orshot_client,
        mock_drive_client,
    ):
        """Only variables supported by template are included."""
        # Template only supports "headline"
        mock_orshot_client.list_templates.return_value = [
            OrshotTemplate(
                id="tpl_simple",
                name="Simple Template",
                canva_id="canva_simple",
                variables=["headline"],  # Only headline
                dimensions=(1080, 1080),
            ),
        ]

        request = RenderRequest(
            content_id="content_simple",
            content_type=ContentType.INSTAGRAM_FEED,
            headline="Test",
            product_name="Product",  # This should be ignored
            topic="test",
        )

        renderer = OrshotRenderer(
            orshot=mock_orshot_client,
            drive=mock_drive_client,
        )

        await renderer.render(request)

        call_args = mock_orshot_client.generate_graphic.call_args
        variables = call_args.kwargs["variables"]

        assert "headline" in variables
        assert "product_name" not in variables
