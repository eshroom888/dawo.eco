"""Tests for Gmail Rate Limiter.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 7: Send Rate Limiter
"""

import pytest
import time
from unittest.mock import patch

from teams.dawo.leads.gmail.rate_limiter import GmailRateLimiter
from teams.dawo.leads.gmail.config import GmailRateLimitConfig


@pytest.fixture
def rate_config() -> GmailRateLimitConfig:
    """Provide rate limit config for testing."""
    return GmailRateLimitConfig(
        max_per_minute=5,  # Low for testing
        max_per_day=50,
        burst_size=3,
    )


@pytest.fixture
def rate_limiter(rate_config: GmailRateLimitConfig) -> GmailRateLimiter:
    """Provide rate limiter instance."""
    return GmailRateLimiter(config=rate_config)


class TestAcquire:
    """Tests for token acquisition."""

    def test_acquire_when_empty(self, rate_limiter: GmailRateLimiter) -> None:
        """Test acquire succeeds when no sends have been made."""
        assert rate_limiter.acquire() is True

    def test_acquire_up_to_limit(self, rate_limiter: GmailRateLimiter) -> None:
        """Test acquire succeeds up to per-minute limit."""
        for _ in range(5):
            assert rate_limiter.acquire() is True

    def test_acquire_at_limit_fails(
        self, rate_limiter: GmailRateLimiter
    ) -> None:
        """Test acquire fails when per-minute limit is reached."""
        for _ in range(5):
            rate_limiter.acquire()

        assert rate_limiter.acquire() is False

    def test_acquire_after_daily_limit(self) -> None:
        """Test acquire fails when daily limit is reached."""
        config = GmailRateLimitConfig(
            max_per_minute=100,
            max_per_day=3,
        )
        limiter = GmailRateLimiter(config=config)

        for _ in range(3):
            assert limiter.acquire() is True

        assert limiter.acquire() is False


class TestWaitForSlot:
    """Tests for wait time calculation."""

    def test_wait_when_empty(self, rate_limiter: GmailRateLimiter) -> None:
        """Test no wait when slots available."""
        assert rate_limiter.wait_for_slot() == 0.0

    def test_wait_when_under_limit(
        self, rate_limiter: GmailRateLimiter
    ) -> None:
        """Test no wait when under per-minute limit."""
        rate_limiter.acquire()
        assert rate_limiter.wait_for_slot() == 0.0

    def test_wait_when_at_limit(self, rate_limiter: GmailRateLimiter) -> None:
        """Test positive wait when at per-minute limit."""
        for _ in range(5):
            rate_limiter.acquire()

        wait = rate_limiter.wait_for_slot()
        assert wait > 0.0
        assert wait <= 60.0


class TestGetStats:
    """Tests for rate limiter statistics."""

    def test_stats_empty(self, rate_limiter: GmailRateLimiter) -> None:
        """Test stats when no sends have been made."""
        stats = rate_limiter.get_stats()
        assert stats["sends_last_minute"] == 0
        assert stats["sends_today"] == 0
        assert stats["remaining_daily_quota"] == 50
        assert stats["max_per_minute"] == 5
        assert stats["max_per_day"] == 50

    def test_stats_after_sends(self, rate_limiter: GmailRateLimiter) -> None:
        """Test stats reflect send counts."""
        rate_limiter.acquire()
        rate_limiter.acquire()

        stats = rate_limiter.get_stats()
        assert stats["sends_last_minute"] == 2
        assert stats["sends_today"] == 2
        assert stats["remaining_daily_quota"] == 48


class TestDailyReset:
    """Tests for daily counter reset."""

    def test_daily_reset_on_new_day(self) -> None:
        """Test daily counter resets when date changes."""
        config = GmailRateLimitConfig(max_per_day=2)
        limiter = GmailRateLimiter(config=config)

        limiter.acquire()
        limiter.acquire()
        assert limiter.acquire() is False

        # Simulate date change
        limiter._daily_reset_date = "2020-01-01"
        assert limiter.acquire() is True


class TestTokenBucketAlgorithm:
    """Tests for the token bucket behavior."""

    def test_timestamps_expire_after_60s(self) -> None:
        """Test old timestamps are cleaned up."""
        config = GmailRateLimitConfig(max_per_minute=2, max_per_day=100)
        limiter = GmailRateLimiter(config=config)

        # Add old timestamps manually
        now = time.monotonic()
        limiter._send_timestamps.append(now - 70)  # 70s ago (expired)
        limiter._send_timestamps.append(now - 65)  # 65s ago (expired)

        # Should be able to acquire because old timestamps are cleaned
        assert limiter.acquire() is True
