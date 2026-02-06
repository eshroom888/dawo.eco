"""Tests for Research Pool Repository.

Tests cover:
- Repository initialization with session injection
- Query filters dataclass
- Repository method signatures and contracts

Note: Full integration tests require PostgreSQL database.
Unit tests use mocks to test repository logic independently.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from teams.dawo.research.models import ResearchSource, ComplianceStatus
from teams.dawo.research.repository import ResearchPoolRepository, ResearchQueryFilters
from teams.dawo.research.schemas import ResearchItemCreate
from teams.dawo.research.exceptions import ItemNotFoundError


class TestQueryFiltersDataclass:
    """Tests for ResearchQueryFilters dataclass."""

    def test_default_values(self):
        """Filters have sensible defaults."""
        filters = ResearchQueryFilters()

        assert filters.source is None
        assert filters.tags is None
        assert filters.min_score is None
        assert filters.max_score is None
        assert filters.start_date is None
        assert filters.end_date is None
        assert filters.compliance_status is None
        assert filters.limit == 50
        assert filters.offset == 0
        assert filters.sort_by == "score"

    def test_custom_values(self):
        """Filters accept custom values."""
        filters = ResearchQueryFilters(
            source=ResearchSource.REDDIT,
            min_score=5.0,
            max_score=9.0,
            limit=10,
            offset=20,
            sort_by="date",
        )

        assert filters.source == ResearchSource.REDDIT
        assert filters.min_score == 5.0
        assert filters.max_score == 9.0
        assert filters.limit == 10
        assert filters.offset == 20
        assert filters.sort_by == "date"

    def test_filters_with_tags(self):
        """Filters accept tags list."""
        filters = ResearchQueryFilters(
            tags=["lions_mane", "cognition"],
        )

        assert filters.tags == ["lions_mane", "cognition"]

    def test_filters_with_date_range(self):
        """Filters accept date range."""
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 12, 31, tzinfo=timezone.utc)

        filters = ResearchQueryFilters(
            start_date=start,
            end_date=end,
        )

        assert filters.start_date == start
        assert filters.end_date == end

    def test_filters_with_compliance_status(self):
        """Filters accept compliance status."""
        filters = ResearchQueryFilters(
            compliance_status=ComplianceStatus.WARNING,
        )

        assert filters.compliance_status == ComplianceStatus.WARNING


class TestRepositoryInitialization:
    """Tests for repository construction and session injection."""

    def test_repository_accepts_session(self):
        """Repository accepts async session via constructor."""
        mock_session = MagicMock()
        repo = ResearchPoolRepository(mock_session)
        assert repo._session is mock_session

    def test_repository_stores_session(self):
        """Repository stores injected session for operations."""
        mock_session = MagicMock()
        repo = ResearchPoolRepository(mock_session)
        assert hasattr(repo, "_session")


class TestRepositoryMethods:
    """Tests for repository method contracts using mocks."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository with mock session."""
        return ResearchPoolRepository(mock_session)

    @pytest.mark.asyncio
    async def test_add_item_calls_session_add(self, repository, mock_session):
        """add_item uses session.add for persistence."""
        item_data = ResearchItemCreate(
            source=ResearchSource.REDDIT,
            title="Test Title",
            content="Test content.",
            url="https://example.com/123",
        )

        # Mock successful commit
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await repository.add_item(item_data)

        # Verify session methods were called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_item_generates_uuid(self, repository, mock_session):
        """add_item generates UUID when not provided."""
        item_data = ResearchItemCreate(
            source=ResearchSource.REDDIT,
            title="Test Title",
            content="Test content.",
            url="https://example.com/123",
        )

        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await repository.add_item(item_data)

        assert result.id is not None

    @pytest.mark.asyncio
    async def test_add_item_uses_provided_uuid(self, repository, mock_session):
        """add_item uses provided UUID."""
        custom_id = uuid4()
        item_data = ResearchItemCreate(
            id=custom_id,
            source=ResearchSource.REDDIT,
            title="Test Title",
            content="Test content.",
            url="https://example.com/123",
        )

        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await repository.add_item(item_data)

        assert result.id == custom_id

    @pytest.mark.asyncio
    async def test_get_by_id_executes_select(self, repository, mock_session):
        """get_by_id executes select query."""
        item_id = uuid4()

        # Mock the execute and result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_id(item_id)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_executes_select(self, repository, mock_session):
        """query executes select with filters."""
        filters = ResearchQueryFilters(source=ResearchSource.REDDIT)

        # Mock the execute and result
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.query(filters)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_update_score_raises_for_missing_item(self, repository, mock_session):
        """update_score raises ItemNotFoundError when item doesn't exist."""
        item_id = uuid4()

        # Mock get_by_id returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ItemNotFoundError):
            await repository.update_score(item_id, 5.0)

    @pytest.mark.asyncio
    async def test_update_compliance_status_raises_for_missing_item(self, repository, mock_session):
        """update_compliance_status raises ItemNotFoundError when item doesn't exist."""
        item_id = uuid4()

        # Mock get_by_id returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ItemNotFoundError):
            await repository.update_compliance_status(item_id, ComplianceStatus.REJECTED)

    @pytest.mark.asyncio
    async def test_count_executes_count_query(self, repository, mock_session):
        """count executes count aggregation."""
        # Mock the execute and result
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count()

        mock_session.execute.assert_called_once()
        assert result == 42

    @pytest.mark.asyncio
    async def test_count_with_filters(self, repository, mock_session):
        """count applies filters."""
        filters = ResearchQueryFilters(source=ResearchSource.REDDIT)

        # Mock the execute and result
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count(filters)

        mock_session.execute.assert_called_once()
        assert result == 10


class TestResearchItemCreate:
    """Tests for ResearchItemCreate schema."""

    def test_create_with_required_fields(self):
        """Schema accepts required fields only."""
        item = ResearchItemCreate(
            source=ResearchSource.REDDIT,
            title="Test Title",
            content="Test content.",
            url="https://example.com/123",
        )

        assert item.source == ResearchSource.REDDIT
        assert item.title == "Test Title"
        assert item.content == "Test content."
        assert item.url == "https://example.com/123"

    def test_create_with_all_fields(self):
        """Schema accepts all fields."""
        item = ResearchItemCreate(
            id=uuid4(),
            source=ResearchSource.YOUTUBE,
            title="YouTube Video",
            content="Video transcript.",
            url="https://youtube.com/watch?v=123",
            tags=["mushrooms", "health"],
            source_metadata={"channel": "Test Channel"},
            score=7.5,
            compliance_status=ComplianceStatus.WARNING,
        )

        assert item.tags == ["mushrooms", "health"]
        assert item.source_metadata == {"channel": "Test Channel"}
        assert item.score == 7.5
        assert item.compliance_status == ComplianceStatus.WARNING

    def test_create_defaults(self):
        """Schema has correct defaults."""
        item = ResearchItemCreate(
            source=ResearchSource.PUBMED,
            title="Research Paper",
            content="Paper content.",
            url="https://pubmed.gov/123",
        )

        assert item.id is None  # Generated later
        assert item.tags == []
        assert item.source_metadata == {}
        assert item.score == 0.0
        assert item.compliance_status == ComplianceStatus.COMPLIANT

    def test_score_validation(self):
        """Schema validates score range (0-10)."""
        # Valid score
        item = ResearchItemCreate(
            source=ResearchSource.NEWS,
            title="News Article",
            content="Content.",
            url="https://news.example.com/123",
            score=10.0,
        )
        assert item.score == 10.0

        # Invalid score should raise
        with pytest.raises(Exception):  # Pydantic ValidationError
            ResearchItemCreate(
                source=ResearchSource.NEWS,
                title="News Article",
                content="Content.",
                url="https://news.example.com/123",
                score=15.0,  # Too high
            )


class TestSearchMethod:
    """Tests for repository search method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository with mock session."""
        return ResearchPoolRepository(mock_session)

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_empty_query(self, repository):
        """search returns empty list for empty query."""
        result = await repository.search("")
        assert result == []

        result = await repository.search("   ")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_executes_query(self, repository, mock_session):
        """search executes full-text search query."""
        # Mock the execute and result
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.search("lions mane cognition")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_search_with_filters(self, repository, mock_session):
        """search applies additional filters."""
        # Mock the execute and result
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        filters = ResearchQueryFilters(
            source=ResearchSource.PUBMED,
            min_score=5.0,
        )
        result = await repository.search("mushroom research", filters)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_search_respects_pagination(self, repository, mock_session):
        """search respects limit and offset from filters."""
        # Mock the execute and result
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        filters = ResearchQueryFilters(limit=10, offset=20)
        await repository.search("test query", filters)

        # Verify execute was called (pagination is applied in the SQL)
        mock_session.execute.assert_called_once()


class TestBulkInsertMethod:
    """Tests for repository bulk_insert method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository with mock session."""
        return ResearchPoolRepository(mock_session)

    @pytest.mark.asyncio
    async def test_bulk_insert_calls_add_all(self, repository, mock_session):
        """bulk_insert uses session.add_all for batch persistence."""
        items = [
            ResearchItemCreate(
                source=ResearchSource.REDDIT,
                title=f"Test Item {i}",
                content=f"Test content {i}.",
                url=f"https://example.com/{i}",
            )
            for i in range(3)
        ]

        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()

        result = await repository.bulk_insert(items)

        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result == 3

    @pytest.mark.asyncio
    async def test_bulk_insert_empty_list(self, repository, mock_session):
        """bulk_insert handles empty list."""
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()

        result = await repository.bulk_insert([])

        mock_session.add_all.assert_called_once()
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_insert_rolls_back_on_error(self, repository, mock_session):
        """bulk_insert rolls back transaction on database error."""
        from teams.dawo.research.exceptions import DatabaseError

        items = [
            ResearchItemCreate(
                source=ResearchSource.REDDIT,
                title="Test Item",
                content="Test content.",
                url="https://example.com/123",
            )
        ]

        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_session.rollback = AsyncMock()

        with pytest.raises(DatabaseError):
            await repository.bulk_insert(items)

        mock_session.rollback.assert_called_once()


class TestURLValidation:
    """Tests for URL validation in schemas."""

    def test_valid_https_url(self):
        """Schema accepts valid HTTPS URL."""
        item = ResearchItemCreate(
            source=ResearchSource.REDDIT,
            title="Test Title",
            content="Test content.",
            url="https://example.com/path?query=value",
        )
        assert item.url == "https://example.com/path?query=value"

    def test_valid_http_url(self):
        """Schema accepts valid HTTP URL."""
        item = ResearchItemCreate(
            source=ResearchSource.NEWS,
            title="News Article",
            content="Content.",
            url="http://news.example.com/article",
        )
        assert item.url == "http://news.example.com/article"

    def test_invalid_url_without_protocol(self):
        """Schema rejects URL without http/https protocol."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ResearchItemCreate(
                source=ResearchSource.REDDIT,
                title="Test Title",
                content="Test content.",
                url="example.com/path",
            )

    def test_invalid_url_with_ftp(self):
        """Schema rejects FTP URL."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ResearchItemCreate(
                source=ResearchSource.REDDIT,
                title="Test Title",
                content="Test content.",
                url="ftp://example.com/file",
            )

    def test_invalid_plain_string(self):
        """Schema rejects plain string that is not a URL."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ResearchItemCreate(
                source=ResearchSource.REDDIT,
                title="Test Title",
                content="Test content.",
                url="not-a-url",
            )


class TestDeleteMethod:
    """Tests for repository delete method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository with mock session."""
        return ResearchPoolRepository(mock_session)

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_found(self, repository, mock_session):
        """delete() returns True when item is deleted."""
        item_id = uuid4()

        # Mock successful delete
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        result = await repository.delete(item_id)

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self, repository, mock_session):
        """delete() returns False when item doesn't exist."""
        item_id = uuid4()

        # Mock delete with no rows affected
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        result = await repository.delete(item_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_rolls_back_on_error(self, repository, mock_session):
        """delete() rolls back transaction on database error."""
        from teams.dawo.research.exceptions import DatabaseError

        item_id = uuid4()

        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))
        mock_session.rollback = AsyncMock()

        with pytest.raises(DatabaseError):
            await repository.delete(item_id)

        mock_session.rollback.assert_called_once()


class TestUpdateItemMethod:
    """Tests for repository update_item method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository with mock session."""
        return ResearchPoolRepository(mock_session)

    @pytest.mark.asyncio
    async def test_update_item_returns_none_when_not_found(self, repository, mock_session):
        """update_item() returns None when item doesn't exist."""
        from teams.dawo.research.schemas import ResearchItemUpdate

        item_id = uuid4()
        updates = ResearchItemUpdate(title="New Title")

        # Mock get_by_id returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.update_item(item_id, updates)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_item_updates_title(self, repository, mock_session):
        """update_item() updates title field."""
        from teams.dawo.research.schemas import ResearchItemUpdate

        item_id = uuid4()
        updates = ResearchItemUpdate(title="Updated Title")

        # Mock get_by_id returning existing item
        existing_item = MagicMock()
        existing_item.id = item_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_item
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await repository.update_item(item_id, updates)

        # Verify update was called (execute called twice: once for select, once for update)
        assert mock_session.execute.call_count >= 1
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_item_returns_existing_when_no_changes(self, repository, mock_session):
        """update_item() returns existing item when no fields to update."""
        from teams.dawo.research.schemas import ResearchItemUpdate

        item_id = uuid4()
        updates = ResearchItemUpdate()  # No fields set

        # Mock get_by_id returning existing item
        existing_item = MagicMock()
        existing_item.id = item_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_item
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.update_item(item_id, updates)

        assert result is existing_item
        # commit should not be called when there's nothing to update
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_item_rolls_back_on_error(self, repository, mock_session):
        """update_item() rolls back transaction on database error."""
        from teams.dawo.research.schemas import ResearchItemUpdate
        from teams.dawo.research.exceptions import DatabaseError

        item_id = uuid4()
        updates = ResearchItemUpdate(title="New Title")

        # Mock get_by_id returning existing item
        existing_item = MagicMock()
        existing_item.id = item_id

        # First call returns item, second call (update) fails
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_item
        mock_session.execute = AsyncMock(side_effect=[mock_result, Exception("Database error")])
        mock_session.rollback = AsyncMock()

        with pytest.raises(DatabaseError):
            await repository.update_item(item_id, updates)

        mock_session.rollback.assert_called_once()
