"""Tests for Reddit Scanner schema classes.

Tests:
    - RawRedditPost creation and validation
    - HarvestedPost creation
    - ValidatedResearch creation
    - ScanResult and PipelineResult dataclasses
    - PipelineStatus enum values
"""

import pytest
from datetime import datetime, timezone

from teams.dawo.scanners.reddit import (
    RawRedditPost,
    HarvestedPost,
    ScanResult,
    PipelineResult,
    PipelineStatus,
)
from teams.dawo.scanners.reddit.schemas import (
    ValidatedResearch,
    ScanStatistics,
    PipelineStatistics,
)


class TestRawRedditPost:
    """Tests for RawRedditPost Pydantic model."""

    def test_valid_creation(self) -> None:
        """Valid data should create RawRedditPost successfully."""
        post = RawRedditPost(
            id="abc123",
            subreddit="Nootropics",
            title="Test post",
            score=100,
            created_utc=1707177600.0,
            permalink="/r/Nootropics/comments/abc123/test/",
            is_self=True,
        )

        assert post.id == "abc123"
        assert post.subreddit == "Nootropics"
        assert post.title == "Test post"
        assert post.score == 100
        assert post.created_utc == 1707177600.0
        assert post.permalink == "/r/Nootropics/comments/abc123/test/"
        assert post.is_self is True

    def test_default_is_self(self) -> None:
        """is_self should default to True."""
        post = RawRedditPost(
            id="abc123",
            subreddit="Test",
            title="Test",
            score=10,
            created_utc=1707177600.0,
            permalink="/r/Test/comments/abc123/",
        )

        assert post.is_self is True

    def test_frozen_model(self) -> None:
        """RawRedditPost should be immutable (frozen)."""
        post = RawRedditPost(
            id="abc123",
            subreddit="Test",
            title="Test",
            score=10,
            created_utc=1707177600.0,
            permalink="/r/Test/comments/abc123/",
        )

        with pytest.raises(Exception):  # ValidationError for frozen model
            post.id = "new_id"


class TestHarvestedPost:
    """Tests for HarvestedPost Pydantic model."""

    def test_valid_creation(self) -> None:
        """Valid data should create HarvestedPost successfully."""
        post = HarvestedPost(
            id="abc123",
            subreddit="Nootropics",
            title="Test post",
            selftext="Post body content",
            author="testuser",
            score=100,
            upvote_ratio=0.95,
            num_comments=50,
            permalink="/r/Nootropics/comments/abc123/test/",
            url="https://reddit.com/r/Nootropics/comments/abc123/test/",
            created_utc=1707177600.0,
            is_self=True,
        )

        assert post.id == "abc123"
        assert post.selftext == "Post body content"
        assert post.author == "testuser"
        assert post.upvote_ratio == 0.95
        assert post.num_comments == 50

    def test_default_values(self) -> None:
        """Defaults should be applied for optional fields."""
        post = HarvestedPost(
            id="abc123",
            subreddit="Test",
            title="Test",
            author="user",
            score=10,
            permalink="/r/Test/comments/abc123/",
            url="https://reddit.com/r/Test/comments/abc123/",
            created_utc=1707177600.0,
        )

        assert post.selftext == ""
        assert post.upvote_ratio == 1.0
        assert post.num_comments == 0
        assert post.is_self is True


class TestValidatedResearch:
    """Tests for ValidatedResearch Pydantic model."""

    def test_valid_creation(self) -> None:
        """Valid data should create ValidatedResearch successfully."""
        item = ValidatedResearch(
            source="reddit",
            title="Test Research",
            content="Research content here",
            url="https://reddit.com/r/Test/comments/abc123/",
            tags=["lions_mane", "cognitive"],
            source_metadata={"subreddit": "Nootropics", "upvotes": 150},
            created_at=datetime.now(timezone.utc),
            compliance_status="COMPLIANT",
            score=7.5,
        )

        assert item.source == "reddit"
        assert item.title == "Test Research"
        assert item.compliance_status == "COMPLIANT"
        assert item.score == 7.5
        assert "lions_mane" in item.tags

    def test_default_values(self) -> None:
        """Defaults should be applied correctly."""
        item = ValidatedResearch(
            title="Test",
            content="Content",
            url="https://example.com/",
            created_at=datetime.now(timezone.utc),
        )

        assert item.source == "reddit"
        assert item.tags == []
        assert item.source_metadata == {}
        assert item.compliance_status == "COMPLIANT"
        assert item.score == 0.0

    def test_score_validation(self) -> None:
        """Score must be between 0 and 10."""
        with pytest.raises(Exception):  # ValidationError
            ValidatedResearch(
                title="Test",
                content="Content",
                url="https://example.com/",
                created_at=datetime.now(timezone.utc),
                score=15.0,  # Invalid - too high
            )


class TestScanStatistics:
    """Tests for ScanStatistics dataclass."""

    def test_default_values(self) -> None:
        """All statistics should default to 0."""
        stats = ScanStatistics()

        assert stats.subreddits_scanned == 0
        assert stats.keywords_searched == 0
        assert stats.total_posts_found == 0
        assert stats.posts_after_filter == 0
        assert stats.duplicates_removed == 0

    def test_custom_values(self) -> None:
        """Custom values should be accepted."""
        stats = ScanStatistics(
            subreddits_scanned=4,
            keywords_searched=7,
            total_posts_found=150,
            posts_after_filter=45,
            duplicates_removed=10,
        )

        assert stats.subreddits_scanned == 4
        assert stats.total_posts_found == 150


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_default_values(self) -> None:
        """Defaults should create empty result."""
        result = ScanResult()

        assert result.posts == []
        assert isinstance(result.statistics, ScanStatistics)
        assert result.errors == []

    def test_with_posts(self, raw_reddit_post) -> None:
        """Result should hold posts correctly."""
        result = ScanResult(
            posts=[raw_reddit_post],
            statistics=ScanStatistics(total_posts_found=1),
        )

        assert len(result.posts) == 1
        assert result.posts[0].id == "abc123"
        assert result.statistics.total_posts_found == 1


class TestPipelineStatus:
    """Tests for PipelineStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """All expected status values should exist."""
        assert PipelineStatus.COMPLETE == "COMPLETE"
        assert PipelineStatus.INCOMPLETE == "INCOMPLETE"
        assert PipelineStatus.PARTIAL == "PARTIAL"
        assert PipelineStatus.FAILED == "FAILED"

    def test_status_values_are_strings(self) -> None:
        """Status values should be string type."""
        assert isinstance(PipelineStatus.COMPLETE.value, str)


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_complete_result(self) -> None:
        """Complete pipeline result should have success status."""
        result = PipelineResult(
            status=PipelineStatus.COMPLETE,
            statistics=PipelineStatistics(
                total_found=100,
                harvested=95,
                transformed=95,
                validated=90,
                scored=90,
                published=85,
                failed=5,
            ),
        )

        assert result.status == PipelineStatus.COMPLETE
        assert result.statistics.published == 85
        assert result.error is None
        assert result.retry_scheduled is False

    def test_incomplete_result(self) -> None:
        """Incomplete result should have error and retry flag."""
        result = PipelineResult(
            status=PipelineStatus.INCOMPLETE,
            error="Reddit API unavailable",
            retry_scheduled=True,
        )

        assert result.status == PipelineStatus.INCOMPLETE
        assert result.error == "Reddit API unavailable"
        assert result.retry_scheduled is True
