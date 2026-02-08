"""Test fixtures for Auto-Publish Eligibility Tagger tests.

Provides reusable fixtures for testing the auto-publish tagger
including pre-configured tagger instances and sample requests.
"""

import pytest
from datetime import datetime, timezone

from teams.dawo.generators.auto_publish_tagger import (
    AutoPublishTagger,
    AutoPublishStatisticsService,
    AutoPublishConfig,
    TaggingRequest,
    AutoPublishTag,
)


@pytest.fixture
def statistics_service() -> AutoPublishStatisticsService:
    """Fresh statistics service for each test."""
    return AutoPublishStatisticsService()


@pytest.fixture
def default_tagger(statistics_service: AutoPublishStatisticsService) -> AutoPublishTagger:
    """AutoPublishTagger with default configuration."""
    return AutoPublishTagger(
        statistics_service=statistics_service,
        config=AutoPublishConfig(),
        threshold=9.0,
    )


@pytest.fixture
def custom_threshold_tagger(statistics_service: AutoPublishStatisticsService) -> AutoPublishTagger:
    """AutoPublishTagger with custom threshold (8.0)."""
    return AutoPublishTagger(
        statistics_service=statistics_service,
        config=AutoPublishConfig(),
        threshold=8.0,
    )


@pytest.fixture
def enabled_config_tagger(statistics_service: AutoPublishStatisticsService) -> AutoPublishTagger:
    """AutoPublishTagger with auto-publish enabled for instagram_feed."""
    return AutoPublishTagger(
        statistics_service=statistics_service,
        config=AutoPublishConfig(instagram_feed_enabled=True),
        threshold=9.0,
    )


@pytest.fixture
def eligible_request() -> TaggingRequest:
    """Request that should be tagged WOULD_AUTO_PUBLISH."""
    return TaggingRequest(
        content_id="test-content-001",
        quality_score=9.5,
        compliance_status="COMPLIANT",
        content_type="instagram_feed",
    )


@pytest.fixture
def ineligible_score_request() -> TaggingRequest:
    """Request with low quality score."""
    return TaggingRequest(
        content_id="test-content-002",
        quality_score=8.5,
        compliance_status="COMPLIANT",
        content_type="instagram_feed",
    )


@pytest.fixture
def ineligible_compliance_request() -> TaggingRequest:
    """Request with non-compliant status."""
    return TaggingRequest(
        content_id="test-content-003",
        quality_score=9.5,
        compliance_status="WARNING",
        content_type="instagram_feed",
    )


@pytest.fixture
def boundary_eligible_request() -> TaggingRequest:
    """Request at exact threshold boundary (score = 9.0)."""
    return TaggingRequest(
        content_id="test-content-004",
        quality_score=9.0,
        compliance_status="COMPLIANT",
        content_type="instagram_feed",
    )


@pytest.fixture
def boundary_ineligible_request() -> TaggingRequest:
    """Request just below threshold (score = 8.9)."""
    return TaggingRequest(
        content_id="test-content-005",
        quality_score=8.9,
        compliance_status="COMPLIANT",
        content_type="instagram_feed",
    )
