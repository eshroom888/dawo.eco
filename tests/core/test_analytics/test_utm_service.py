"""Tests for ShortLinkService.

Story 7-2, Task 3.9: Comprehensive tests for ShortLinkService.
Tests creation, collision handling, resolution, tracking, analytics.
"""

import asyncio
import hashlib
import re
from datetime import UTC, datetime
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.analytics.utm_models import LinkClick, ShortLink
from core.analytics.utm_service import ShortLinkService


@dataclass(frozen=True)
class FakeUTMConfig:
    """Minimal UTMConfig stand-in for testing."""

    short_link_base_url: str = "https://dawo.no"
    default_attribution_window_days: int = 30
    code_length: int = 8


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create mock UTMRepository."""
    repo = AsyncMock()
    repo.create_short_link = AsyncMock()
    repo.get_by_code = AsyncMock(return_value=None)
    repo.get_by_post_id = AsyncMock(return_value=[])
    repo.record_click = AsyncMock()
    repo.get_click_stats = AsyncMock(return_value={
        "total_clicks": 0, "unique_clicks": 0,
        "clicks_by_day": [], "device_breakdown": [],
    })
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def config() -> FakeUTMConfig:
    """Create test UTMConfig."""
    return FakeUTMConfig()


@pytest.fixture
def service(mock_repository: AsyncMock, config: FakeUTMConfig) -> ShortLinkService:
    """Create ShortLinkService with mocked dependencies."""
    return ShortLinkService(repository=mock_repository, config=config)


class TestCreateShortLink:
    """Tests for create_short_link method."""

    @pytest.mark.asyncio
    async def test_creates_link_with_utm_params(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Creates short link with correct UTM parameters."""
        from integrations.shopify.utm import UTMParams

        params = UTMParams(
            source="instagram", medium="post",
            campaign="feed_post", content="post123",
        )

        mock_repository.create_short_link.return_value = ShortLink(
            code="test1234",
            destination_url="https://dawo.no/product?utm_source=instagram",
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed_post",
            utm_content="post123",
            post_id="post123",
            source_type="instagram",
        )

        result = await service.create_short_link(
            destination_url="https://dawo.no/product",
            utm_params=params,
            post_id="post123",
            source_type="instagram",
        )

        mock_repository.create_short_link.assert_awaited_once()
        created_link = mock_repository.create_short_link.call_args[0][0]
        assert created_link.utm_source == "instagram"
        assert created_link.utm_medium == "post"
        assert created_link.utm_campaign == "feed_post"
        assert created_link.utm_content == "post123"
        assert created_link.post_id == "post123"

    @pytest.mark.asyncio
    async def test_generates_code_from_secrets(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Short code is generated using secrets.token_urlsafe(6)."""
        mock_repository.create_short_link.side_effect = lambda link: link

        from integrations.shopify.utm import UTMParams
        params = UTMParams(source="instagram", medium="post", campaign="c", content="x")

        with patch("core.analytics.utm_service.secrets") as mock_secrets:
            mock_secrets.token_urlsafe.return_value = "abcd1234"
            result = await service.create_short_link(
                destination_url="https://example.com",
                utm_params=params,
            )
            mock_secrets.token_urlsafe.assert_called_with(6)

    @pytest.mark.asyncio
    async def test_collision_retry_succeeds(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Retries code generation on collision (max 3 attempts)."""
        from integrations.shopify.utm import UTMParams
        params = UTMParams(source="ig", medium="p", campaign="c", content="x")

        # First call: code exists (collision), second: does not exist
        mock_repository.get_by_code.side_effect = [
            ShortLink(code="col1", destination_url="x", utm_source="ig",
                      utm_medium="p", utm_campaign="c", utm_content="x",
                      source_type="instagram"),
            None,
        ]
        mock_repository.create_short_link.side_effect = lambda link: link

        result = await service.create_short_link(
            destination_url="https://example.com",
            utm_params=params,
        )
        assert result is not None
        assert mock_repository.get_by_code.await_count == 2

    @pytest.mark.asyncio
    async def test_collision_exhaustion_raises(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Raises ValueError after 3 failed collision retries."""
        from integrations.shopify.utm import UTMParams
        params = UTMParams(source="ig", medium="p", campaign="c", content="x")

        # All 3 attempts collide
        existing = ShortLink(code="col", destination_url="x", utm_source="ig",
                             utm_medium="p", utm_campaign="c", utm_content="x",
                             source_type="instagram")
        mock_repository.get_by_code.return_value = existing

        with pytest.raises(ValueError, match="collision"):
            await service.create_short_link(
                destination_url="https://example.com",
                utm_params=params,
            )

    @pytest.mark.asyncio
    async def test_destination_url_includes_utm_params(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Destination URL has UTM parameters appended."""
        from integrations.shopify.utm import UTMParams
        params = UTMParams(source="instagram", medium="post",
                           campaign="feed_post", content="post123")

        mock_repository.create_short_link.side_effect = lambda link: link

        result = await service.create_short_link(
            destination_url="https://dawo.no/product",
            utm_params=params,
        )

        assert "utm_source=instagram" in result.destination_url
        assert "utm_campaign=feed_post" in result.destination_url


class TestResolveAndTrack:
    """Tests for resolve_and_track method."""

    @pytest.mark.asyncio
    async def test_returns_destination_url_when_found(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Returns destination URL when code is valid."""
        link = ShortLink(
            id=uuid4(), code="abc123",
            destination_url="https://dawo.no/product?utm_source=instagram",
            utm_source="ig", utm_medium="p", utm_campaign="c",
            utm_content="x", source_type="instagram",
        )
        mock_repository.get_by_code.return_value = link

        result = await service.resolve_and_track(
            code="abc123", ip="192.168.1.1",
            user_agent="Mozilla/5.0", referer="https://instagram.com",
        )

        assert result == "https://dawo.no/product?utm_source=instagram"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Returns None when code does not exist."""
        mock_repository.get_by_code.return_value = None

        result = await service.resolve_and_track(
            code="nonexistent", ip="192.168.1.1",
        )

        assert result is None
        mock_repository.record_click.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_records_click_with_hashed_ip(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Click records contain SHA-256 hashed IP, never raw IP."""
        link_id = uuid4()
        link = ShortLink(
            id=link_id, code="abc123",
            destination_url="https://example.com",
            utm_source="ig", utm_medium="p", utm_campaign="c",
            utm_content="x", source_type="instagram",
        )
        mock_repository.get_by_code.return_value = link

        raw_ip = "192.168.1.1"
        expected_hash = hashlib.sha256(raw_ip.encode()).hexdigest()

        await service.resolve_and_track(code="abc123", ip=raw_ip)
        await asyncio.sleep(0)  # Let fire-and-forget task complete

        mock_repository.record_click.assert_awaited_once()
        click = mock_repository.record_click.call_args[0][0]
        assert click.ip_hash == expected_hash
        assert raw_ip not in str(click.__dict__)  # GDPR: no raw IP anywhere

    @pytest.mark.asyncio
    async def test_records_click_with_device_type(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Click records include parsed device type."""
        link = ShortLink(
            id=uuid4(), code="abc123",
            destination_url="https://example.com",
            utm_source="ig", utm_medium="p", utm_campaign="c",
            utm_content="x", source_type="instagram",
        )
        mock_repository.get_by_code.return_value = link

        await service.resolve_and_track(
            code="abc123", ip="10.0.0.1",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        )
        await asyncio.sleep(0)  # Let fire-and-forget task complete

        click = mock_repository.record_click.call_args[0][0]
        assert click.device_type == "mobile"


class TestDeviceTypeParsing:
    """Tests for device type detection from user-agent."""

    def test_mobile_user_agent(self, service: ShortLinkService) -> None:
        """Detects mobile from iPhone user agent."""
        assert service._parse_device_type(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
        ) == "mobile"

    def test_android_mobile(self, service: ShortLinkService) -> None:
        """Detects mobile from Android user agent."""
        assert service._parse_device_type(
            "Mozilla/5.0 (Linux; Android 13; Pixel 7)"
        ) == "mobile"

    def test_desktop_user_agent(self, service: ShortLinkService) -> None:
        """Detects desktop from Windows user agent."""
        assert service._parse_device_type(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ) == "desktop"

    def test_tablet_ipad(self, service: ShortLinkService) -> None:
        """Detects tablet from iPad user agent."""
        assert service._parse_device_type(
            "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)"
        ) == "tablet"

    def test_bot_user_agent(self, service: ShortLinkService) -> None:
        """Detects bot from crawler user agent."""
        assert service._parse_device_type(
            "Googlebot/2.1 (+http://www.google.com/bot.html)"
        ) == "bot"

    def test_none_user_agent(self, service: ShortLinkService) -> None:
        """Returns None when user agent is None."""
        assert service._parse_device_type(None) is None

    def test_empty_user_agent(self, service: ShortLinkService) -> None:
        """Returns None when user agent is empty."""
        assert service._parse_device_type("") is None


class TestGetPostClickAnalytics:
    """Tests for get_post_click_analytics method."""

    @pytest.mark.asyncio
    async def test_returns_aggregated_analytics(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Returns ClickAnalytics with aggregated stats."""
        link_id = uuid4()
        mock_repository.get_by_post_id.return_value = [
            ShortLink(id=link_id, code="a1", destination_url="https://x.com",
                      utm_source="ig", utm_medium="p", utm_campaign="c",
                      utm_content="x", post_id="post1", source_type="instagram"),
        ]
        mock_repository.get_click_stats.return_value = {
            "total_clicks": 100,
            "unique_clicks": 75,
            "clicks_by_day": [{"day": "2026-02-20", "count": 50}],
            "device_breakdown": [{"device_type": "mobile", "count": 60}],
        }

        result = await service.get_post_click_analytics("post1")

        assert result.total_clicks == 100
        assert result.unique_clicks == 75

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_links(
        self, service: ShortLinkService, mock_repository: AsyncMock
    ) -> None:
        """Returns zero-value analytics when post has no links."""
        mock_repository.get_by_post_id.return_value = []

        result = await service.get_post_click_analytics("unknown_post")

        assert result.total_clicks == 0
        assert result.unique_clicks == 0


class TestIPHashing:
    """Tests for IP hashing (GDPR compliance)."""

    def test_ip_hash_is_sha256(self, service: ShortLinkService) -> None:
        """IP hashing uses SHA-256."""
        ip = "192.168.1.1"
        expected = hashlib.sha256(ip.encode()).hexdigest()
        assert service._hash_ip(ip) == expected

    def test_hash_is_deterministic(self, service: ShortLinkService) -> None:
        """Same IP always produces same hash."""
        ip = "10.0.0.1"
        assert service._hash_ip(ip) == service._hash_ip(ip)

    def test_hash_length_is_64(self, service: ShortLinkService) -> None:
        """SHA-256 hex digest is always 64 characters."""
        assert len(service._hash_ip("1.2.3.4")) == 64


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports(self) -> None:
        """utm_service module exports ShortLinkService."""
        from core.analytics import utm_service

        assert hasattr(utm_service, "__all__")
        assert "ShortLinkService" in utm_service.__all__
