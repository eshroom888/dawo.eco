"""Tests for page change detector.

Epic 6, Story 6-3: Tasks 13.16-13.18.
"""

import hashlib

import pytest

from teams.dawo.scanners.mattilsynet.change_detector import PageChangeDetector


@pytest.fixture
def detector() -> PageChangeDetector:
    return PageChangeDetector()


class TestCheckPage:
    """Test check_page method."""

    def test_detects_change_when_hash_differs(self, detector: PageChangeDetector) -> None:
        content = "Updated content"
        old_hash = hashlib.sha256(b"Original content").hexdigest()
        result = detector.check_page("https://example.com", content, old_hash)
        assert result.changed is True
        assert result.content == content
        assert result.url == "https://example.com"

    def test_detects_no_change_when_hash_matches(self, detector: PageChangeDetector) -> None:
        content = "Same content"
        current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        result = detector.check_page("https://example.com", content, current_hash)
        assert result.changed is False
        assert result.content is None

    def test_first_run_no_previous_hash(self, detector: PageChangeDetector) -> None:
        content = "First time content"
        result = detector.check_page("https://example.com", content, None)
        assert result.changed is False
        assert result.content is None
        assert result.current_hash != ""

    def test_computes_sha256_hash(self, detector: PageChangeDetector) -> None:
        content = "Test content"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        result = detector.check_page("https://example.com", content, None)
        assert result.current_hash == expected

    def test_changed_content_is_returned(self, detector: PageChangeDetector) -> None:
        content = "New content"
        old_hash = hashlib.sha256(b"Old content").hexdigest()
        result = detector.check_page("https://example.com", content, old_hash)
        assert result.content == content
