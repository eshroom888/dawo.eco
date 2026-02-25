"""Shared fixtures for claim extraction tests.

Story 6-6, Task 11: Common test fixtures.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.claim_extraction.config import (
    ClaimPattern,
    HealthClaimExtractionConfig,
)
from teams.dawo.scanners.claim_extraction.schemas import (
    ClaimExtractionResult,
    PatternMatch,
)


@pytest.fixture
def sample_config() -> HealthClaimExtractionConfig:
    """Standard test config with prohibited + borderline patterns."""
    return HealthClaimExtractionConfig(
        prohibited_patterns=(
            ClaimPattern(pattern="cures cancer", category="treatment", language="en"),
            ClaimPattern(pattern="prevents disease", category="prevention", language="en"),
        ),
        borderline_patterns=(
            ClaimPattern(pattern="boosts immunity", category="enhancement", language="en"),
            ClaimPattern(pattern="supports digestion", category="general_wellness", language="en"),
        ),
        batch_size=20,
        confidence_threshold=70,
        max_claims_per_content=10,
        use_llm=True,
    )


@pytest.fixture
def sample_pattern_match() -> PatternMatch:
    """Standard PatternMatch for reuse."""
    return PatternMatch(
        matched_text="boosts immunity",
        pattern="boosts immunity",
        category="enhancement",
        language="en",
        start_pos=12,
        end_pos=27,
        surrounding_context="product boosts immunity and c",
    )


@pytest.fixture
def sample_claim_result() -> ClaimExtractionResult:
    """Standard ClaimExtractionResult for reuse."""
    return ClaimExtractionResult(
        claim_text="boosts immunity",
        surrounding_context="product boosts immunity",
        claim_category="enhancement",
        confidence_score=90,
        language_detected="en",
        extraction_method="hybrid",
    )


@pytest.fixture
def make_mock_content():
    """Factory for mock CompetitorContent objects."""
    def _make(content_text: str = "Some content", has_health_language: bool = True):
        content = MagicMock()
        content.id = uuid4()
        content.content_text = content_text
        content.competitor_name = "TestCompetitor"
        content.source_type = "website"
        content.has_health_language = has_health_language
        content.extraction_status = "pending"
        return content
    return _make
