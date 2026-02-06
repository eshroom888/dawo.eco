"""Shared fixtures for scoring tests.

Provides:
- Shared fixtures for test research items
- Configured scorer instances for integration tests

Note: pytest markers are registered in parent conftest.py (test_research/conftest.py)
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from teams.dawo.research.models import ResearchSource, ComplianceStatus
from teams.dawo.research.scoring import (
    ResearchItemScorer,
    ScoringConfig,
    RelevanceScorer,
    RelevanceConfig,
    RecencyScorer,
    RecencyConfig,
    SourceQualityScorer,
    SourceQualityConfig,
    EngagementScorer,
    EngagementConfig,
    ComplianceAdjuster,
)


# =============================================================================
# Scorer Fixtures
# =============================================================================

@pytest.fixture
def scoring_config() -> ScoringConfig:
    """Default scoring configuration."""
    return ScoringConfig()


@pytest.fixture
def relevance_scorer() -> RelevanceScorer:
    """Configured relevance scorer."""
    return RelevanceScorer(config=RelevanceConfig())


@pytest.fixture
def recency_scorer() -> RecencyScorer:
    """Configured recency scorer."""
    return RecencyScorer(config=RecencyConfig())


@pytest.fixture
def source_quality_scorer() -> SourceQualityScorer:
    """Configured source quality scorer."""
    return SourceQualityScorer(config=SourceQualityConfig())


@pytest.fixture
def engagement_scorer() -> EngagementScorer:
    """Configured engagement scorer."""
    return EngagementScorer(config=EngagementConfig())


@pytest.fixture
def compliance_adjuster() -> ComplianceAdjuster:
    """Configured compliance adjuster."""
    return ComplianceAdjuster()


@pytest.fixture
def full_scorer(
    scoring_config: ScoringConfig,
    relevance_scorer: RelevanceScorer,
    recency_scorer: RecencyScorer,
    source_quality_scorer: SourceQualityScorer,
    engagement_scorer: EngagementScorer,
    compliance_adjuster: ComplianceAdjuster,
) -> ResearchItemScorer:
    """Fully configured composite scorer for integration tests."""
    return ResearchItemScorer(
        config=scoring_config,
        relevance_scorer=relevance_scorer,
        recency_scorer=recency_scorer,
        source_quality_scorer=source_quality_scorer,
        engagement_scorer=engagement_scorer,
        compliance_adjuster=compliance_adjuster,
    )


# =============================================================================
# Research Item Fixtures (AC#2 and AC#3 examples)
# =============================================================================

@pytest.fixture
def pubmed_rct_item() -> dict:
    """PubMed RCT study - should score 8+ per AC#2.

    Represents a peer-reviewed randomized controlled trial about
    Lion's Mane mushroom effects on cognitive function.
    """
    return {
        "id": uuid4(),
        "source": ResearchSource.PUBMED.value,
        "title": "Randomized controlled trial of Lion's Mane (Hericium erinaceus) on cognitive function",
        "content": "This RCT examined the effects of Hericium erinaceus supplementation on cognitive performance, memory, and focus in healthy adults. Significant improvements were observed in the treatment group.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
        "tags": ["lions_mane", "cognition", "rct"],
        "source_metadata": {
            "pmid": "12345678",
            "doi": "10.1234/example",
            "study_type": "RCT",
            "sample_size": 50,
            "citation_count": 25,
        },
        "created_at": datetime.now(timezone.utc),
        "score": 0.0,
        "compliance_status": ComplianceStatus.COMPLIANT.value,
    }


@pytest.fixture
def reddit_high_engagement_item() -> dict:
    """High-engagement Reddit post - should score 4-6 per AC#3.

    Represents a popular Reddit post with unverified personal claims
    about Lion's Mane benefits. Good content opportunity but needs fact-checking.
    """
    return {
        "id": uuid4(),
        "source": ResearchSource.REDDIT.value,
        "title": "My experience with lion's mane for brain fog",
        "content": "Been taking lion's mane for 3 months and noticed significant improvements in focus and mental clarity.",
        "url": "https://reddit.com/r/Nootropics/comments/abc123",
        "tags": ["lions_mane", "personal_experience"],
        "source_metadata": {
            "subreddit": "Nootropics",
            "author": "user123",
            "upvotes": 150,
            "comment_count": 45,
        },
        "created_at": datetime.now(timezone.utc),
        "score": 0.0,
        "compliance_status": ComplianceStatus.WARNING.value,
    }


@pytest.fixture
def old_research_item() -> dict:
    """Research item older than 30 days - recency should be 0."""
    return {
        "id": uuid4(),
        "source": ResearchSource.PUBMED.value,
        "title": "Lion's mane study from last year",
        "content": "Hericium erinaceus research on cognition.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/old123",
        "tags": ["lions_mane", "cognition"],
        "source_metadata": {"study_type": "RCT"},
        "created_at": datetime.now(timezone.utc) - timedelta(days=60),
        "score": 0.0,
        "compliance_status": ComplianceStatus.COMPLIANT.value,
    }


@pytest.fixture
def rejected_item() -> dict:
    """Item with REJECTED compliance - should always score 0."""
    return {
        "id": uuid4(),
        "source": ResearchSource.PUBMED.value,
        "title": "Lion's mane cures everything",
        "content": "This study shows lion's mane fixes all health problems.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/fake123",
        "tags": ["lions_mane"],
        "source_metadata": {"study_type": "RCT", "citation_count": 100},
        "created_at": datetime.now(timezone.utc),
        "score": 0.0,
        "compliance_status": ComplianceStatus.REJECTED.value,
    }
