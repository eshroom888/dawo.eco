"""Tests for Outreach configuration.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for outreach configuration dataclasses.
"""

import pytest

from teams.dawo.leads.outreach.config import (
    OutreachConfig,
    TemplateConfig,
    MIN_CONFIDENCE_THRESHOLD,
    MIN_WORD_COUNT,
    MAX_WORD_COUNT,
    MIN_PERSONALIZATION_TOKENS,
    DEFAULT_BATCH_SIZE,
)


class TestOutreachConfig:
    """Tests for OutreachConfig dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = OutreachConfig()

        assert config.min_confidence_threshold == MIN_CONFIDENCE_THRESHOLD
        assert config.min_word_count == MIN_WORD_COUNT
        assert config.max_word_count == MAX_WORD_COUNT
        assert config.min_personalization_tokens == MIN_PERSONALIZATION_TOKENS
        assert config.batch_size == DEFAULT_BATCH_SIZE

    def test_custom_values(self):
        """Should accept custom values."""
        config = OutreachConfig(
            min_confidence_threshold=7.0,
            min_word_count=160,
            max_word_count=240,
            min_personalization_tokens=3,
            batch_size=20,
        )

        assert config.min_confidence_threshold == 7.0
        assert config.min_word_count == 160
        assert config.max_word_count == 240
        assert config.min_personalization_tokens == 3
        assert config.batch_size == 20

    def test_schedule_defaults(self):
        """Should have scheduling configuration."""
        config = OutreachConfig()

        assert config.schedule_cron == "0 9 * * *"  # Daily 9 AM (after enrichment)
        assert config.schedule_timezone == "Europe/Oslo"


class TestTemplateConfig:
    """Tests for TemplateConfig dataclass."""

    def test_default_cta_options(self):
        """Should have default CTA options."""
        config = TemplateConfig()

        assert "meeting_request" in config.cta_options
        assert "sample_offer" in config.cta_options
        assert "catalog_request" in config.cta_options

    def test_default_value_propositions(self):
        """Should have Norwegian value propositions."""
        config = TemplateConfig()

        # Should have at least one value proposition
        assert len(config.value_propositions) > 0

        # Value propositions should be in Norwegian
        all_props = " ".join(config.value_propositions)
        # Check for common Norwegian words
        assert any(word in all_props.lower() for word in ["kvalitet", "norsk", "premium"])


class TestConstants:
    """Tests for module constants."""

    def test_word_count_range(self):
        """Word count range should match AC #2 (150-250)."""
        assert MIN_WORD_COUNT == 150
        assert MAX_WORD_COUNT == 250

    def test_min_personalization_tokens(self):
        """Should require at least 2 personalization tokens."""
        assert MIN_PERSONALIZATION_TOKENS == 2

    def test_confidence_threshold(self):
        """Should require confidence >= 6 for outreach."""
        assert MIN_CONFIDENCE_THRESHOLD == 6
