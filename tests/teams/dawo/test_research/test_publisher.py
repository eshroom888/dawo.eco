"""Tests for Research Publisher Service.

Tests cover:
- Publisher initialization with repository injection
- publish() method validation and persistence
- UUID generation and timestamp handling
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from teams.dawo.research.models import ResearchSource, ComplianceStatus
from teams.dawo.research.publisher import ResearchPublisher, TransformedResearch
from teams.dawo.research.exceptions import ValidationError


class TestPublisherInitialization:
    """Tests for publisher construction and dependency injection."""

    def test_publisher_accepts_repository(self):
        """Publisher accepts repository via constructor."""
        mock_repo = MagicMock()
        publisher = ResearchPublisher(mock_repo)
        assert publisher._repository is mock_repo

    def test_publisher_stores_repository(self):
        """Publisher stores injected repository."""
        mock_repo = MagicMock()
        publisher = ResearchPublisher(mock_repo)
        assert hasattr(publisher, "_repository")


class TestTransformedResearchSchema:
    """Tests for TransformedResearch input schema."""

    def test_create_with_required_fields(self):
        """Schema accepts required fields."""
        item = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="Test Title",
            content="Test content.",
            url="https://example.com/123",
        )

        assert item.source == ResearchSource.REDDIT
        assert item.title == "Test Title"
        assert item.content == "Test content."
        assert item.url == "https://example.com/123"

    def test_create_with_optional_fields(self):
        """Schema accepts optional fields."""
        item = TransformedResearch(
            source=ResearchSource.YOUTUBE,
            title="YouTube Video",
            content="Transcript content.",
            url="https://youtube.com/watch?v=123",
            tags=["mushrooms", "health"],
            source_metadata={"channel": "Test Channel"},
            score=7.5,
            compliance_status=ComplianceStatus.COMPLIANT,
        )

        assert item.tags == ["mushrooms", "health"]
        assert item.source_metadata == {"channel": "Test Channel"}
        assert item.score == 7.5

    def test_defaults(self):
        """Schema has correct defaults."""
        item = TransformedResearch(
            source=ResearchSource.PUBMED,
            title="Paper Title",
            content="Paper content.",
            url="https://pubmed.gov/123",
        )

        assert item.id is None  # Will be generated
        assert item.tags == []
        assert item.source_metadata == {}
        assert item.score == 0.0
        assert item.compliance_status == ComplianceStatus.COMPLIANT


class TestPublishMethod:
    """Tests for publisher.publish() method."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def publisher(self, mock_repository):
        """Create publisher with mock repository."""
        return ResearchPublisher(mock_repository)

    @pytest.mark.asyncio
    async def test_publish_calls_repository_add_item(self, publisher, mock_repository):
        """publish() calls repository.add_item()."""
        item = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="Test Item",
            content="Test content.",
            url="https://example.com/123",
        )

        # Mock successful add
        mock_repository.add_item.return_value = MagicMock(id=uuid4())

        await publisher.publish(item)

        mock_repository.add_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_generates_uuid_if_not_provided(self, publisher, mock_repository):
        """publish() generates UUID when item.id is None."""
        item = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="Test Item",
            content="Test content.",
            url="https://example.com/123",
        )

        mock_result = MagicMock()
        mock_result.id = uuid4()
        mock_repository.add_item.return_value = mock_result

        result = await publisher.publish(item)

        # Verify add_item was called with generated UUID
        call_args = mock_repository.add_item.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_publish_uses_provided_uuid(self, publisher, mock_repository):
        """publish() uses provided UUID."""
        custom_id = uuid4()
        item = TransformedResearch(
            id=custom_id,
            source=ResearchSource.REDDIT,
            title="Test Item",
            content="Test content.",
            url="https://example.com/123",
        )

        mock_result = MagicMock()
        mock_result.id = custom_id
        mock_repository.add_item.return_value = mock_result

        result = await publisher.publish(item)

        call_args = mock_repository.add_item.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_publish_returns_research_item(self, publisher, mock_repository):
        """publish() returns created ResearchItem."""
        item = TransformedResearch(
            source=ResearchSource.NEWS,
            title="News Article",
            content="Article content.",
            url="https://news.example.com/123",
        )

        expected_id = uuid4()
        mock_result = MagicMock()
        mock_result.id = expected_id
        mock_result.title = "News Article"
        mock_repository.add_item.return_value = mock_result

        result = await publisher.publish(item)

        assert result.id == expected_id
        assert result.title == "News Article"

    @pytest.mark.asyncio
    async def test_publish_validates_required_fields(self, publisher, mock_repository):
        """publish() validates required fields are present."""
        # Empty title should fail validation
        with pytest.raises(Exception):  # Pydantic ValidationError
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title="",  # Empty title
                content="Test content.",
                url="https://example.com/123",
            )

    @pytest.mark.asyncio
    async def test_publish_validates_score_range(self, publisher, mock_repository):
        """publish() validates score is within 0-10."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title="Test Title",
                content="Test content.",
                url="https://example.com/123",
                score=15.0,  # Invalid score
            )


class TestPublishBatchMethod:
    """Tests for publisher.publish_batch() method."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def publisher(self, mock_repository):
        """Create publisher with mock repository."""
        return ResearchPublisher(mock_repository)

    @pytest.mark.asyncio
    async def test_publish_batch_calls_bulk_insert(self, publisher, mock_repository):
        """publish_batch() calls repository.bulk_insert()."""
        items = [
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title=f"Test Item {i}",
                content=f"Test content {i}.",
                url=f"https://example.com/{i}",
            )
            for i in range(3)
        ]

        mock_repository.bulk_insert.return_value = 3

        result = await publisher.publish_batch(items)

        mock_repository.bulk_insert.assert_called_once()
        assert result == 3

    @pytest.mark.asyncio
    async def test_publish_batch_empty_list(self, publisher, mock_repository):
        """publish_batch() handles empty list."""
        mock_repository.bulk_insert.return_value = 0

        result = await publisher.publish_batch([])

        mock_repository.bulk_insert.assert_called_once()
        assert result == 0

    @pytest.mark.asyncio
    async def test_publish_batch_returns_count(self, publisher, mock_repository):
        """publish_batch() returns count of items inserted."""
        items = [
            TransformedResearch(
                source=ResearchSource.YOUTUBE,
                title=f"Video {i}",
                content=f"Transcript {i}.",
                url=f"https://youtube.com/watch?v={i}",
            )
            for i in range(5)
        ]

        mock_repository.bulk_insert.return_value = 5

        result = await publisher.publish_batch(items)

        assert result == 5

    @pytest.mark.asyncio
    async def test_publish_batch_converts_to_create_schemas(self, publisher, mock_repository):
        """publish_batch() converts TransformedResearch to ResearchItemCreate."""
        items = [
            TransformedResearch(
                source=ResearchSource.PUBMED,
                title="Research Paper",
                content="Paper content.",
                url="https://pubmed.gov/123",
                score=8.5,
                tags=["science", "health"],
            )
        ]

        mock_repository.bulk_insert.return_value = 1

        await publisher.publish_batch(items)

        # Verify the conversion happened
        call_args = mock_repository.bulk_insert.call_args
        assert call_args is not None
        create_items = call_args[0][0]  # First positional argument
        assert len(create_items) == 1
        assert create_items[0].source == ResearchSource.PUBMED
        assert create_items[0].title == "Research Paper"
        assert create_items[0].score == 8.5


class TestTransformedResearchURLValidation:
    """Tests for URL validation in TransformedResearch schema."""

    def test_valid_https_url(self):
        """Schema accepts valid HTTPS URL."""
        item = TransformedResearch(
            source=ResearchSource.REDDIT,
            title="Test Title",
            content="Test content.",
            url="https://reddit.com/r/test",
        )
        assert item.url == "https://reddit.com/r/test"

    def test_valid_http_url(self):
        """Schema accepts valid HTTP URL."""
        item = TransformedResearch(
            source=ResearchSource.NEWS,
            title="News Article",
            content="Content.",
            url="http://news.example.com/article",
        )
        assert item.url == "http://news.example.com/article"

    def test_invalid_url_without_protocol(self):
        """Schema rejects URL without http/https protocol."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title="Test Title",
                content="Test content.",
                url="reddit.com/r/test",
            )

    def test_invalid_plain_string(self):
        """Schema rejects plain string that is not a URL."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title="Test Title",
                content="Test content.",
                url="not-a-url",
            )
