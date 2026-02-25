"""Tests for UTM integration orchestrator.

Story 7-2, Task 6: Integration tests verifying UTM param flow.
Tests generate_post_short_link and build_short_link_url helper.
"""

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.analytics.utm_integration import generate_post_short_link
from integrations.shopify.utm import UTMParams


@dataclass(frozen=True)
class FakeUTMConfig:
    """Minimal UTMConfig for testing."""

    short_link_base_url: str = "https://dawo.no"
    default_attribution_window_days: int = 30
    code_length: int = 8


class TestBuildShortLinkUrl:
    """Tests for build_short_link_url helper in shopify/utm.py."""

    def test_builds_short_link_url(self) -> None:
        """Builds correct short link URL from base and code."""
        from integrations.shopify.utm import build_short_link_url

        result = build_short_link_url("https://dawo.no", "abc123")
        assert result == "https://dawo.no/l/abc123"

    def test_builds_with_trailing_slash(self) -> None:
        """Handles trailing slash in base URL."""
        from integrations.shopify.utm import build_short_link_url

        result = build_short_link_url("https://dawo.no/", "abc123")
        assert result == "https://dawo.no/l/abc123"


class TestGeneratePostShortLink:
    """Tests for generate_post_short_link orchestrator."""

    @pytest.mark.asyncio
    async def test_creates_link_with_correct_params(self) -> None:
        """Generates short link with correct UTM params for post."""
        from core.analytics.utm_models import ShortLink

        mock_service = AsyncMock()
        expected_link = ShortLink(
            code="test1234",
            destination_url="https://dawo.no/product?utm_source=instagram&utm_medium=post&utm_campaign=feed_post&utm_content=post123",
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed_post",
            utm_content="post123",
            post_id="post123",
            source_type="instagram",
        )
        mock_service.create_short_link.return_value = expected_link

        result = await generate_post_short_link(
            service=mock_service,
            post_id="post123",
            destination_url="https://dawo.no/product",
            content_type="feed_post",
        )

        assert result is expected_link
        mock_service.create_short_link.assert_awaited_once()

        # Verify UTM params
        call_kwargs = mock_service.create_short_link.call_args.kwargs
        utm = call_kwargs["utm_params"]
        assert utm.source == "instagram"
        assert utm.medium == "post"
        assert utm.campaign == "feed_post"
        assert utm.content == "post123"
        assert call_kwargs["post_id"] == "post123"

    @pytest.mark.asyncio
    async def test_uses_custom_source_type(self) -> None:
        """Supports custom source_type parameter."""
        from core.analytics.utm_models import ShortLink

        mock_service = AsyncMock()
        mock_service.create_short_link.return_value = ShortLink(
            code="x", destination_url="https://x.com",
            utm_source="facebook", utm_medium="post",
            utm_campaign="c", utm_content="x",
            post_id="p", source_type="facebook",
        )

        await generate_post_short_link(
            service=mock_service,
            post_id="p",
            destination_url="https://x.com",
            content_type="c",
            source_type="facebook",
        )

        call_kwargs = mock_service.create_short_link.call_args.kwargs
        assert call_kwargs["source_type"] == "facebook"

    @pytest.mark.asyncio
    async def test_full_flow_generate_store_redirect_track(self) -> None:
        """Integration: generate -> store -> resolve -> track."""
        from core.analytics.utm_models import ShortLink
        from core.analytics.utm_service import ShortLinkService

        mock_repo = AsyncMock()
        mock_config = FakeUTMConfig()

        # Simulate create
        created_link = ShortLink(
            id=uuid4(), code="test1234",
            destination_url="https://dawo.no/product?utm_source=instagram&utm_medium=post&utm_campaign=feed_post&utm_content=post123",
            utm_source="instagram", utm_medium="post",
            utm_campaign="feed_post", utm_content="post123",
            post_id="post123", source_type="instagram",
        )
        mock_repo.create_short_link.return_value = created_link
        mock_repo.get_by_code.side_effect = [None, created_link]  # First: no collision, then: resolve
        mock_repo.record_click = AsyncMock()

        service = ShortLinkService(repository=mock_repo, config=mock_config)

        # Step 1: Generate
        link = await generate_post_short_link(
            service=service,
            post_id="post123",
            destination_url="https://dawo.no/product",
            content_type="feed_post",
        )
        assert link.code is not None

        # Step 2: Resolve and track
        mock_repo.get_by_code.return_value = created_link
        dest = await service.resolve_and_track(
            code=link.code, ip="192.168.1.1",
            user_agent="Mozilla/5.0", referer="https://instagram.com",
        )
        await asyncio.sleep(0)  # Let fire-and-forget task complete

        assert dest is not None
        assert "utm_source=instagram" in dest
        mock_repo.record_click.assert_awaited_once()


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports(self) -> None:
        """utm_integration module exports generate_post_short_link."""
        from core.analytics import utm_integration

        assert hasattr(utm_integration, "__all__")
        assert "generate_post_short_link" in utm_integration.__all__
