"""Tests for UTM repository.

Story 7-2, Task 2.5: Tests for UTMRepository methods.
Uses mock async session for all database interactions.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.analytics.utm_models import LinkClick, ShortLink
from core.analytics.utm_repository import UTMRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock async SQLAlchemy session."""
    session = AsyncMock()
    session.add = MagicMock()  # add() is synchronous
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> UTMRepository:
    """Create UTMRepository with mock session."""
    return UTMRepository(mock_session)


class TestCreateShortLink:
    """Tests for create_short_link method."""

    @pytest.mark.asyncio
    async def test_adds_to_session_and_flushes(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """create_short_link adds link to session and flushes."""
        link = ShortLink(
            code="abc123",
            destination_url="https://example.com?utm_source=instagram",
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed",
            utm_content="post123",
            source_type="instagram",
        )

        await repository.create_short_link(link)

        mock_session.add.assert_called_once_with(link)
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_the_link(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """create_short_link returns the added link."""
        link = ShortLink(
            code="abc123",
            destination_url="https://example.com",
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed",
            utm_content="post123",
            source_type="instagram",
        )

        result = await repository.create_short_link(link)
        assert result is link


class TestGetByCode:
    """Tests for get_by_code method."""

    @pytest.mark.asyncio
    async def test_returns_link_when_found(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_by_code returns ShortLink when code exists."""
        expected = ShortLink(code="abc123", destination_url="https://example.com",
                             utm_source="ig", utm_medium="p", utm_campaign="c",
                             utm_content="x", source_type="instagram")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_code("abc123")
        assert result is expected

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_by_code returns None when code does not exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_code("nonexistent")
        assert result is None


class TestGetByPostId:
    """Tests for get_by_post_id method."""

    @pytest.mark.asyncio
    async def test_returns_links_for_post(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_by_post_id returns all links for a post."""
        links = [
            ShortLink(code="a1", destination_url="https://a.com",
                      utm_source="ig", utm_medium="p", utm_campaign="c",
                      utm_content="x", post_id="post1", source_type="instagram"),
            ShortLink(code="a2", destination_url="https://b.com",
                      utm_source="ig", utm_medium="p", utm_campaign="c",
                      utm_content="y", post_id="post1", source_type="instagram"),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = links
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_post_id("post1")
        assert result == links
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_links(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_by_post_id returns empty list when post has no links."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_post_id("unknown_post")
        assert result == []


class TestRecordClick:
    """Tests for record_click method."""

    @pytest.mark.asyncio
    async def test_adds_click_and_flushes(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """record_click adds click to session and flushes."""
        click = LinkClick(
            short_link_id=uuid4(),
            clicked_at=datetime.now(UTC),
            ip_hash="a" * 64,
            device_type="mobile",
        )

        await repository.record_click(click)

        mock_session.add.assert_called_once_with(click)
        mock_session.flush.assert_awaited_once()


class TestGetClickStats:
    """Tests for get_click_stats method."""

    @pytest.mark.asyncio
    async def test_returns_aggregated_stats(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_click_stats returns total, unique, by_day, device_breakdown."""
        link_id = uuid4()

        # Mock total_clicks
        mock_total = MagicMock()
        mock_total.scalar_one.return_value = 42

        # Mock unique_clicks
        mock_unique = MagicMock()
        mock_unique.scalar_one.return_value = 30

        # Mock clicks_by_day
        mock_by_day = MagicMock()
        mock_by_day_rows = MagicMock()
        mock_by_day_rows.all.return_value = [
            MagicMock(day=datetime(2026, 2, 20, tzinfo=UTC).date(), count=10),
            MagicMock(day=datetime(2026, 2, 21, tzinfo=UTC).date(), count=15),
        ]
        mock_by_day.mappings.return_value = mock_by_day_rows

        # Mock device_breakdown
        mock_device = MagicMock()
        mock_device_rows = MagicMock()
        mock_device_rows.all.return_value = [
            MagicMock(device_type="mobile", count=25),
            MagicMock(device_type="desktop", count=17),
        ]
        mock_device.mappings.return_value = mock_device_rows

        mock_session.execute.side_effect = [
            mock_total, mock_unique, mock_by_day, mock_device
        ]

        stats = await repository.get_click_stats(link_id)

        assert stats["total_clicks"] == 42
        assert stats["unique_clicks"] == 30
        assert len(stats["clicks_by_day"]) == 2
        assert len(stats["device_breakdown"]) == 2


class TestGetClicksByPostId:
    """Tests for get_clicks_by_post method."""

    @pytest.mark.asyncio
    async def test_returns_clicks_for_post(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_clicks_by_post returns click records for a post's links."""
        clicks = [
            LinkClick(
                short_link_id=uuid4(),
                clicked_at=datetime.now(UTC),
                ip_hash="a" * 64,
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = clicks
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_clicks_by_post("post1")
        assert result == clicks


class TestGetClicksByPostIds:
    """Tests for get_clicks_by_post_ids batch method."""

    @pytest.mark.asyncio
    async def test_batch_returns_grouped_clicks(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_clicks_by_post_ids returns clicks grouped by post_id (no N+1)."""
        link1_id = uuid4()
        link2_id = uuid4()

        # First query returns links for both posts
        link1 = ShortLink(
            id=link1_id, code="a1", destination_url="https://a.com",
            utm_source="ig", utm_medium="p", utm_campaign="c",
            utm_content="x", post_id="post1", source_type="instagram",
        )
        link2 = ShortLink(
            id=link2_id, code="a2", destination_url="https://b.com",
            utm_source="ig", utm_medium="p", utm_campaign="c",
            utm_content="y", post_id="post2", source_type="instagram",
        )

        click1 = LinkClick(
            short_link_id=link1_id,
            clicked_at=datetime.now(UTC),
            ip_hash="a" * 64,
        )
        click2 = LinkClick(
            short_link_id=link2_id,
            clicked_at=datetime.now(UTC),
            ip_hash="b" * 64,
        )

        # Mock: first execute returns links, second returns clicks
        mock_links_result = MagicMock()
        mock_links_scalars = MagicMock()
        mock_links_scalars.all.return_value = [link1, link2]
        mock_links_result.scalars.return_value = mock_links_scalars

        mock_clicks_result = MagicMock()
        mock_clicks_scalars = MagicMock()
        mock_clicks_scalars.all.return_value = [click1, click2]
        mock_clicks_result.scalars.return_value = mock_clicks_scalars

        mock_session.execute.side_effect = [mock_links_result, mock_clicks_result]

        result = await repository.get_clicks_by_post_ids(["post1", "post2"])

        assert "post1" in result
        assert "post2" in result
        assert len(result["post1"]) == 1
        assert len(result["post2"]) == 1

    @pytest.mark.asyncio
    async def test_batch_empty_list_returns_empty_dict(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_clicks_by_post_ids with empty list returns empty dict."""
        result = await repository.get_clicks_by_post_ids([])
        assert result == {}
        mock_session.execute.assert_not_awaited()


class TestGetAggregateClickStats:
    """Tests for get_aggregate_click_stats method."""

    @pytest.mark.asyncio
    async def test_returns_aggregate_stats(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """get_aggregate_click_stats returns totals and averages."""
        mock_total = MagicMock()
        mock_total.scalar_one.return_value = 500

        mock_posts = MagicMock()
        mock_posts.scalar_one.return_value = 10

        mock_session.execute.side_effect = [mock_total, mock_posts]

        stats = await repository.get_aggregate_click_stats(days_back=30)

        assert stats["total_clicks"] == 500
        assert stats["unique_posts"] == 10
        assert stats["avg_clicks_per_post"] == 50.0

    @pytest.mark.asyncio
    async def test_returns_zero_avg_when_no_posts(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """Returns 0.0 avg when no posts have clicks."""
        mock_total = MagicMock()
        mock_total.scalar_one.return_value = 0

        mock_posts = MagicMock()
        mock_posts.scalar_one.return_value = 0

        mock_session.execute.side_effect = [mock_total, mock_posts]

        stats = await repository.get_aggregate_click_stats(days_back=7)

        assert stats["total_clicks"] == 0
        assert stats["unique_posts"] == 0
        assert stats["avg_clicks_per_post"] == 0.0


class TestCommit:
    """Tests for commit method."""

    @pytest.mark.asyncio
    async def test_commits_session(
        self, repository: UTMRepository, mock_session: AsyncMock
    ) -> None:
        """commit delegates to session.commit."""
        await repository.commit()
        mock_session.commit.assert_awaited_once()


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports(self) -> None:
        """utm_repository module exports UTMRepository."""
        from core.analytics import utm_repository

        assert hasattr(utm_repository, "__all__")
        assert "UTMRepository" in utm_repository.__all__
