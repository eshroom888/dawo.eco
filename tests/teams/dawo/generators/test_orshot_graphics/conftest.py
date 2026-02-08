"""Test fixtures for Orshot Graphics Generator tests."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from integrations.orshot import OrshotTemplate, GeneratedGraphic
from integrations.google_drive import DriveAsset, AssetType


@pytest.fixture
def mock_orshot_client():
    """Mock OrshotClient for renderer tests."""
    client = AsyncMock()
    client.list_templates.return_value = [
        OrshotTemplate(
            id="tpl_feed_123",
            name="DAWO Feed Post",
            canva_id="canva_abc",
            variables=["headline", "product_name", "date"],
            dimensions=(1080, 1080),
        ),
        OrshotTemplate(
            id="tpl_story_456",
            name="DAWO Story",
            canva_id="canva_def",
            variables=["headline"],
            dimensions=(1080, 1920),
        ),
    ]
    client.generate_graphic.return_value = GeneratedGraphic(
        id="gen_789",
        template_id="tpl_feed_123",
        image_url="https://cdn.orshot.com/renders/gen_789.png",
        local_path=None,
        variables_used={"headline": "Test", "product_name": "Løvemanke"},
        created_at=datetime.now(timezone.utc),
    )
    client.download_graphic.return_value = Path("/tmp/gen_789.png")
    return client


@pytest.fixture
def mock_drive_client():
    """Mock GoogleDriveClient for asset upload tests."""
    client = AsyncMock()
    client.upload_asset.return_value = DriveAsset(
        id="drive_abc123",
        name="20260207_orshot_wellness_abc12345.png",
        folder_id="folder_xyz",
        web_view_link="https://drive.google.com/file/d/drive_abc123",
        download_link="https://drive.google.com/uc?id=drive_abc123",
        mime_type="image/png",
        created_at=datetime.now(timezone.utc),
        metadata={"template_id": "tpl_feed_123"},
    )
    return client


@pytest.fixture
def mock_usage_tracker():
    """Mock OrshotUsageTracker."""
    tracker = AsyncMock()
    tracker.can_render.return_value = True
    tracker.get_usage.return_value = 100
    tracker.increment.return_value = (101, False, False)
    return tracker


@pytest.fixture
def mock_usage_tracker_warning():
    """Mock usage tracker at warning threshold (80%)."""
    tracker = AsyncMock()
    tracker.can_render.return_value = True
    tracker.get_usage.return_value = 2400
    tracker.increment.return_value = (2401, True, False)
    return tracker


@pytest.fixture
def mock_usage_tracker_exceeded():
    """Mock usage tracker at limit."""
    tracker = AsyncMock()
    tracker.can_render.return_value = False
    tracker.get_usage.return_value = 3000
    return tracker


@pytest.fixture
def sample_feed_request():
    """Sample render request for Instagram feed post."""
    from teams.dawo.generators.orshot_graphics import RenderRequest, ContentType

    return RenderRequest(
        content_id="content_123",
        content_type=ContentType.INSTAGRAM_FEED,
        headline="Naturens kraft i hver kapsel",
        product_name="Løvemanke Ekstrakt",
        date_display="Februar 2026",
        topic="wellness",
    )


@pytest.fixture
def sample_story_request():
    """Sample render request for Instagram story."""
    from teams.dawo.generators.orshot_graphics import RenderRequest, ContentType

    return RenderRequest(
        content_id="content_456",
        content_type=ContentType.INSTAGRAM_STORY,
        headline="Dagens tips",
        topic="lifestyle",
    )


@pytest.fixture
def sample_request_with_template():
    """Sample request with specific template ID."""
    from teams.dawo.generators.orshot_graphics import RenderRequest, ContentType

    return RenderRequest(
        content_id="content_789",
        content_type=ContentType.INSTAGRAM_FEED,
        headline="Test headline",
        topic="mushrooms",
        template_id="tpl_feed_123",
    )
