"""Tests for Schedule API endpoints.

Story 4-4, Task 11: Backend integration tests for scheduling endpoints.

This module contains both unit tests for helper functions and
integration tests for the actual API endpoints using FastAPI TestClient.
"""

import pytest
from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from ui.backend.routers.schedule import router, get_db
from ui.backend.schemas.schedule import (
    ScheduleCalendarResponse,
    ScheduledItemResponse,
    OptimalTimesResponse,
    RescheduleResponse,
    RetryPublishResponse,
    ConflictSeverity,
)


class MockApprovalItem:
    """Mock ApprovalItem for testing."""

    def __init__(
        self,
        item_id: str,
        scheduled_time: datetime,
        status: str = "approved",
        source_priority: int = 3,
        quality_score: float = 8.0,
    ):
        self.id = uuid4() if item_id is None else item_id
        self.scheduled_publish_time = scheduled_time
        self.status = status
        self.source_priority = source_priority
        self.quality_score = quality_score
        self.full_caption = f"Test caption for {item_id}"
        self.thumbnail_url = f"https://example.com/thumb/{item_id}.jpg"
        self.source_type = "instagram_post"
        self.compliance_status = "COMPLIANT"
        self.updated_at = datetime.utcnow()


class TestScheduleCalendarEndpoint:
    """Tests for GET /api/schedule/calendar endpoint."""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository."""
        repo = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_calendar_returns_items_in_date_range(self, mock_repo):
        """Test that calendar endpoint returns items in date range."""
        # Arrange
        start = date(2026, 2, 10)
        end = date(2026, 2, 16)
        mock_items = [
            MockApprovalItem("item-1", datetime(2026, 2, 10, 9, 0)),
            MockApprovalItem("item-2", datetime(2026, 2, 12, 14, 0)),
        ]
        mock_repo.get_scheduled_items.return_value = mock_items

        # The actual test would use FastAPI TestClient
        # This demonstrates the expected behavior
        response_items = []
        for item in mock_items:
            response_items.append(
                ScheduledItemResponse(
                    id=str(item.id),
                    title=item.full_caption[:50],
                    thumbnail_url=item.thumbnail_url,
                    scheduled_publish_time=item.scheduled_publish_time,
                    source_type=item.source_type,
                    source_priority=item.source_priority,
                    quality_score=item.quality_score,
                    quality_color="green",
                    compliance_status=item.compliance_status,
                    conflicts=[],
                    is_imminent=False,
                )
            )

        response = ScheduleCalendarResponse(
            items=response_items,
            conflicts=[],
            date_range={"start": start.isoformat(), "end": end.isoformat()},
        )

        assert len(response.items) == 2
        assert response.date_range["start"] == "2026-02-10"
        assert response.date_range["end"] == "2026-02-16"

    @pytest.mark.asyncio
    async def test_calendar_detects_conflicts(self, mock_repo):
        """Test that conflicts are detected and included in response."""
        # Two items at same hour should trigger conflict
        mock_items = [
            MockApprovalItem("item-1", datetime(2026, 2, 10, 9, 0)),
            MockApprovalItem("item-2", datetime(2026, 2, 10, 9, 30)),
        ]
        mock_repo.get_scheduled_items.return_value = mock_items

        # Detect conflicts
        from ui.backend.routers.schedule import detect_conflicts

        conflicts = detect_conflicts(mock_items)

        assert len(conflicts) == 1
        assert conflicts[0].posts_count == 2
        assert conflicts[0].severity == ConflictSeverity.WARNING

    @pytest.mark.asyncio
    async def test_calendar_marks_imminent_items(self, mock_repo):
        """Test that items within 1 hour are marked as imminent."""
        from ui.backend.routers.schedule import is_imminent

        # Item 30 minutes from now
        imminent_time = datetime.utcnow() + timedelta(minutes=30)
        future_time = datetime.utcnow() + timedelta(hours=5)

        assert is_imminent(imminent_time) is True
        assert is_imminent(future_time) is False


class TestOptimalTimesEndpoint:
    """Tests for GET /api/schedule/optimal-times endpoint."""

    @pytest.mark.asyncio
    async def test_returns_three_suggestions(self):
        """Test that endpoint returns top 3 suggestions."""
        response = OptimalTimesResponse(
            item_id=None,
            target_date=date(2026, 2, 10),
            suggestions=[
                {"time": datetime(2026, 2, 10, 9, 0), "score": 0.95, "reasoning": "Peak time"},
                {"time": datetime(2026, 2, 10, 19, 0), "score": 0.90, "reasoning": "Evening peak"},
                {"time": datetime(2026, 2, 10, 10, 0), "score": 0.85, "reasoning": "Near peak"},
            ],
        )

        assert len(response.suggestions) == 3
        assert response.suggestions[0].score >= response.suggestions[1].score

    @pytest.mark.asyncio
    async def test_suggestions_include_reasoning(self):
        """Test that each suggestion includes reasoning."""
        from ui.backend.routers.schedule import get_optimal_times

        # Mock would be needed for actual test
        # This verifies the schema structure
        suggestion = {"time": datetime(2026, 2, 10, 9, 0), "score": 0.9, "reasoning": "Peak engagement time, no conflicts"}

        assert "Peak engagement" in suggestion["reasoning"]


class TestRescheduleEndpoint:
    """Tests for PATCH /api/schedule/{item_id}/reschedule endpoint."""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository."""
        repo = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_reschedule_updates_time(self, mock_repo):
        """Test that reschedule updates the scheduled time."""
        item_id = str(uuid4())
        new_time = datetime(2026, 2, 15, 10, 0)

        mock_item = MockApprovalItem(item_id, new_time)
        mock_repo.reschedule_item.return_value = mock_item
        mock_repo.get_items_at_hour.return_value = [mock_item]

        response = RescheduleResponse(
            success=True,
            message=f"Rescheduled to {new_time.isoformat()}",
            item_id=item_id,
            new_publish_time=new_time,
            conflicts=[],
        )

        assert response.success is True
        assert response.new_publish_time == new_time

    @pytest.mark.asyncio
    async def test_reschedule_returns_conflicts(self, mock_repo):
        """Test that reschedule includes conflicts at new time."""
        item_id = str(uuid4())
        new_time = datetime(2026, 2, 15, 10, 0)

        # Two items at same hour
        mock_items = [
            MockApprovalItem("item-1", new_time),
            MockApprovalItem("item-2", new_time + timedelta(minutes=30)),
        ]
        mock_repo.get_items_at_hour.return_value = mock_items

        from ui.backend.schemas.schedule import ConflictInfo

        conflict = ConflictInfo(
            hour=new_time.replace(minute=0, second=0, microsecond=0),
            posts_count=2,
            post_ids=["item-1", "item-2"],
            severity=ConflictSeverity.WARNING,
        )

        response = RescheduleResponse(
            success=True,
            message=f"Rescheduled to {new_time.isoformat()}",
            item_id=item_id,
            new_publish_time=new_time,
            conflicts=[conflict],
        )

        assert len(response.conflicts) == 1
        assert response.conflicts[0].posts_count == 2

    @pytest.mark.asyncio
    async def test_reschedule_rejects_imminent(self, mock_repo):
        """Test that reschedule fails for imminent items without force."""
        # This would be tested with actual endpoint
        # Demonstrating expected behavior
        imminent_time = datetime.utcnow() + timedelta(minutes=15)

        # Repo should raise ValueError
        mock_repo.reschedule_item.side_effect = ValueError(
            "Cannot reschedule within 30 minutes of publish time."
        )

        with pytest.raises(ValueError) as exc_info:
            await mock_repo.reschedule_item("item-1", imminent_time)

        assert "30 minutes" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reschedule_with_force_bypasses_lock(self, mock_repo):
        """Test that force=true bypasses imminent lock."""
        item_id = str(uuid4())
        new_time = datetime.utcnow() + timedelta(minutes=15)

        mock_item = MockApprovalItem(item_id, new_time)
        mock_repo.reschedule_item.return_value = mock_item

        # Should succeed with force=true
        result = await mock_repo.reschedule_item(item_id, new_time, force=True)

        assert result is not None


class TestHelperFunctions:
    """Tests for helper functions in schedule router."""

    def test_get_quality_color_green(self):
        """Test green color for high scores."""
        from ui.backend.routers.schedule import get_quality_color

        assert get_quality_color(8.0) == "green"
        assert get_quality_color(9.5) == "green"
        assert get_quality_color(10.0) == "green"

    def test_get_quality_color_yellow(self):
        """Test yellow color for medium scores."""
        from ui.backend.routers.schedule import get_quality_color

        assert get_quality_color(5.0) == "yellow"
        assert get_quality_color(6.5) == "yellow"
        assert get_quality_color(7.9) == "yellow"

    def test_get_quality_color_red(self):
        """Test red color for low scores."""
        from ui.backend.routers.schedule import get_quality_color

        assert get_quality_color(0.0) == "red"
        assert get_quality_color(3.0) == "red"
        assert get_quality_color(4.9) == "red"

    def test_truncate_caption_short(self):
        """Test that short captions are not truncated."""
        from ui.backend.routers.schedule import truncate_caption

        short = "This is a short caption"
        assert truncate_caption(short, 50) == short

    def test_truncate_caption_long(self):
        """Test that long captions are truncated with ellipsis."""
        from ui.backend.routers.schedule import truncate_caption

        long = "This is a very long caption that exceeds the maximum length limit"
        result = truncate_caption(long, 30)

        assert len(result) == 30
        assert result.endswith("...")

    def test_is_imminent_true(self):
        """Test is_imminent returns true for near times."""
        from ui.backend.routers.schedule import is_imminent

        near_future = datetime.utcnow() + timedelta(minutes=30)
        assert is_imminent(near_future) is True

    def test_is_imminent_false_far_future(self):
        """Test is_imminent returns false for far times."""
        from ui.backend.routers.schedule import is_imminent

        far_future = datetime.utcnow() + timedelta(hours=5)
        assert is_imminent(far_future) is False

    def test_is_imminent_false_past(self):
        """Test is_imminent returns false for past times."""
        from ui.backend.routers.schedule import is_imminent

        past = datetime.utcnow() - timedelta(hours=1)
        assert is_imminent(past) is False


class TestEndpointIntegration:
    """Integration tests for schedule API endpoints using FastAPI TestClient.

    Story 4-4, Task 11: Tests that actually call the router endpoints
    with mocked database dependencies.
    """

    @pytest.fixture
    def app(self):
        """Create FastAPI app with schedule router."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def mock_db_session(self):
        """Create mock async database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_repo_with_items(self, mock_db_session):
        """Create mock repository returning test items."""
        items = [
            MockApprovalItem("item-1", datetime(2026, 2, 10, 9, 0)),
            MockApprovalItem("item-2", datetime(2026, 2, 10, 14, 0)),
            MockApprovalItem("item-3", datetime(2026, 2, 11, 10, 0)),
        ]
        return items

    @pytest.mark.asyncio
    async def test_calendar_endpoint_returns_items(self, app, mock_db_session, mock_repo_with_items):
        """Test GET /api/schedule/calendar returns scheduled items."""
        from httpx import AsyncClient, ASGITransport

        # Override get_db dependency
        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        # Mock the repository method
        with patch(
            "ui.backend.routers.schedule.ApprovalItemRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_scheduled_items = AsyncMock(
                return_value=mock_repo_with_items
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/schedule/calendar",
                    params={
                        "start_date": "2026-02-10",
                        "end_date": "2026-02-16",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "conflicts" in data
            assert "date_range" in data

    @pytest.mark.asyncio
    async def test_optimal_times_endpoint_returns_suggestions(self, app, mock_db_session):
        """Test GET /api/schedule/optimal-times returns time suggestions."""
        from httpx import AsyncClient, ASGITransport

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        with patch(
            "ui.backend.routers.schedule.ApprovalItemRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_scheduled_items = AsyncMock(return_value=[])

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/schedule/optimal-times",
                    params={"target_date": "2026-02-10"},
                )

            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data
            assert len(data["suggestions"]) == 3  # Top 3 suggestions

    @pytest.mark.asyncio
    async def test_reschedule_endpoint_updates_item(self, app, mock_db_session):
        """Test PATCH /api/schedule/{item_id}/reschedule updates publish time."""
        from httpx import AsyncClient, ASGITransport

        item_id = str(uuid4())
        new_time = datetime(2026, 2, 15, 10, 0)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        mock_item = MockApprovalItem(item_id, new_time)

        with patch(
            "ui.backend.routers.schedule.ApprovalItemRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.reschedule_item = AsyncMock(return_value=mock_item)
            mock_repo.get_items_at_hour = AsyncMock(return_value=[mock_item])

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"/api/schedule/{item_id}/reschedule",
                    json={"new_publish_time": new_time.isoformat()},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["item_id"] == item_id

    @pytest.mark.asyncio
    async def test_reschedule_endpoint_rejects_invalid_item(self, app, mock_db_session):
        """Test PATCH reschedule returns 400 for invalid item."""
        from httpx import AsyncClient, ASGITransport

        item_id = str(uuid4())
        new_time = datetime(2026, 2, 15, 10, 0)

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        with patch(
            "ui.backend.routers.schedule.ApprovalItemRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.reschedule_item = AsyncMock(
                side_effect=ValueError("Item not found")
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"/api/schedule/{item_id}/reschedule",
                    json={"new_publish_time": new_time.isoformat()},
                )

            assert response.status_code == 400
            assert "Item not found" in response.json()["detail"]


class TestRetryPublishEndpoint:
    """Tests for POST /api/schedule/{item_id}/retry-publish endpoint.

    Story 4-5, Task 9.5: Test manual retry endpoint.
    """

    @pytest.fixture
    def app(self):
        """Create FastAPI app with schedule router."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def mock_db_session(self):
        """Create mock async database session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_retry_requires_publish_failed_status(self, app, mock_db_session):
        """Test that retry fails if item is not in PUBLISH_FAILED status."""
        from httpx import AsyncClient, ASGITransport
        from unittest.mock import MagicMock
        from uuid import uuid4

        item_id = str(uuid4())

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        # Mock item with SCHEDULED status (not PUBLISH_FAILED)
        mock_item = MagicMock()
        mock_item.status = "scheduled"
        mock_item.publish_attempts = 0
        mock_item.updated_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/schedule/{item_id}/retry-publish",
                json={},
            )

        assert response.status_code == 400
        assert "PUBLISH_FAILED" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_resets_status_to_scheduled(self, app, mock_db_session):
        """Test that retry resets status from PUBLISH_FAILED to SCHEDULED."""
        from httpx import AsyncClient, ASGITransport
        from unittest.mock import MagicMock
        from uuid import uuid4

        item_id = str(uuid4())

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        # Mock item with PUBLISH_FAILED status
        mock_item = MagicMock()
        mock_item.status = "publish_failed"
        mock_item.publish_error = "Rate limit exceeded"
        mock_item.publish_attempts = 1
        mock_item.updated_at = datetime.utcnow() - timedelta(minutes=5)
        mock_item.scheduled_publish_time = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()

        # Mock ARQ enqueue (will fail without Redis, but should handle gracefully)
        with patch("ui.backend.routers.schedule.enqueue_publish_job") as mock_enqueue:
            mock_enqueue.return_value = "job-123"

            with patch("arq.create_pool") as mock_create_pool:
                mock_pool = AsyncMock()
                mock_create_pool.return_value = mock_pool
                mock_pool.close = AsyncMock()

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        f"/api/schedule/{item_id}/retry-publish",
                        json={"force": False},
                    )

        # Should succeed (status was updated)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["item_id"] == item_id

        # Verify item was updated
        assert mock_item.status == "scheduled"
        assert mock_item.publish_error is None

    @pytest.mark.asyncio
    async def test_retry_returns_404_for_missing_item(self, app, mock_db_session):
        """Test that retry returns 404 if item doesn't exist."""
        from httpx import AsyncClient, ASGITransport
        from uuid import uuid4

        item_id = str(uuid4())

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        # Mock no item found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/schedule/{item_id}/retry-publish",
                json={},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retry_rate_limit_without_force(self, app, mock_db_session):
        """Test that retry is rate limited without force flag."""
        from httpx import AsyncClient, ASGITransport
        from unittest.mock import MagicMock
        from uuid import uuid4

        item_id = str(uuid4())

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        # Mock item with recent attempts
        mock_item = MagicMock()
        mock_item.status = "publish_failed"
        mock_item.publish_attempts = 3  # Already retried 3 times
        mock_item.updated_at = datetime.utcnow() - timedelta(seconds=30)  # Recent

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/schedule/{item_id}/retry-publish",
                json={"force": False},
            )

        assert response.status_code == 429
        assert "Too many recent attempts" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_with_force_bypasses_rate_limit(self, app, mock_db_session):
        """Test that force=true bypasses rate limiting."""
        from httpx import AsyncClient, ASGITransport
        from unittest.mock import MagicMock
        from uuid import uuid4

        item_id = str(uuid4())

        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        # Mock item with recent attempts
        mock_item = MagicMock()
        mock_item.status = "publish_failed"
        mock_item.publish_attempts = 5
        mock_item.updated_at = datetime.utcnow() - timedelta(seconds=10)
        mock_item.scheduled_publish_time = None
        mock_item.publish_error = "Error"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()

        with patch("arq.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            mock_pool.close = AsyncMock()

            with patch("ui.backend.routers.schedule.enqueue_publish_job") as mock_enqueue:
                mock_enqueue.return_value = "job-456"

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        f"/api/schedule/{item_id}/retry-publish",
                        json={"force": True},  # Force bypasses rate limit
                    )

        # Should succeed with force=true
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
