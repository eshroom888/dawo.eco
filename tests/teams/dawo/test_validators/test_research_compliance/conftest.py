"""Test fixtures for Research Compliance Validator tests.

Provides mocked dependencies and sample research items for testing.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.research import TransformedResearch, ResearchSource, ComplianceStatus
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ContentComplianceCheck,
    ComplianceResult,
    OverallStatus,
    ComplianceStatus as PhraseStatus,
)


@pytest.fixture
def mock_eu_compliance_checker() -> AsyncMock:
    """Mock EU Compliance Checker that returns COMPLIANT by default."""
    checker = AsyncMock(spec=EUComplianceChecker)
    checker.check_content = AsyncMock(
        return_value=ContentComplianceCheck(
            overall_status=OverallStatus.COMPLIANT,
            flagged_phrases=[],
            compliance_score=1.0,
            llm_enhanced=False,
        )
    )
    return checker


@pytest.fixture
def mock_checker_returns_warning() -> AsyncMock:
    """Mock EU Compliance Checker that returns WARNING."""
    checker = AsyncMock(spec=EUComplianceChecker)
    checker.check_content = AsyncMock(
        return_value=ContentComplianceCheck(
            overall_status=OverallStatus.WARNING,
            flagged_phrases=[
                ComplianceResult(
                    phrase="supports brain function",
                    status=PhraseStatus.BORDERLINE,
                    explanation="Function claim requires EFSA authorization",
                    regulation_reference="EC 1924/2006 Article 13",
                )
            ],
            compliance_score=0.9,
            llm_enhanced=False,
        )
    )
    return checker


@pytest.fixture
def mock_checker_returns_rejected() -> AsyncMock:
    """Mock EU Compliance Checker that returns REJECTED."""
    checker = AsyncMock(spec=EUComplianceChecker)
    checker.check_content = AsyncMock(
        return_value=ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[
                ComplianceResult(
                    phrase="cures brain fog",
                    status=PhraseStatus.PROHIBITED,
                    explanation="Cure claims are strictly prohibited",
                    regulation_reference="EC 1924/2006 Article 10",
                )
            ],
            compliance_score=0.7,
            llm_enhanced=False,
        )
    )
    return checker


@pytest.fixture
def sample_pubmed_research() -> TransformedResearch:
    """Sample PubMed research item with DOI and PMID."""
    return TransformedResearch(
        source=ResearchSource.PUBMED,
        title="Effects of Lion's Mane on Cognition: A Randomized Controlled Trial",
        content="This randomized controlled trial examined the cognitive effects of Hericium erinaceus supplementation. DOI: 10.1234/test.2024",
        url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        tags=["lions_mane", "cognition", "clinical_trial"],
        source_metadata={
            "doi": "10.1234/test.2024",
            "pmid": "12345678",
            "authors": ["Smith J", "Jones K"],
            "journal": "Journal of Functional Foods",
        },
        score=8.5,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_reddit_research() -> TransformedResearch:
    """Sample Reddit research item without scientific citation."""
    return TransformedResearch(
        source=ResearchSource.REDDIT,
        title="My experience with Lion's Mane",
        content="I've been taking lion's mane for 3 months and noticed improved focus. Not making any health claims, just my personal experience.",
        url="https://reddit.com/r/Nootropics/comments/abc123/my_experience",
        tags=["lions_mane", "user_experience"],
        source_metadata={
            "subreddit": "Nootropics",
            "author": "mushroom_fan",
            "upvotes": 150,
        },
        score=6.0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def research_with_prohibited_claims() -> TransformedResearch:
    """Research item containing prohibited health claims."""
    return TransformedResearch(
        source=ResearchSource.REDDIT,
        title="Lion's mane CURES brain fog!",
        content="I took lion's mane and it cured my brain fog completely. This treats anxiety too!",
        url="https://reddit.com/r/Nootropics/comments/xyz789/cures",
        tags=["lions_mane", "brain_fog"],
        source_metadata={
            "subreddit": "Nootropics",
            "author": "health_guru",
            "upvotes": 500,
        },
        score=5.0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def research_with_doi_and_claims() -> TransformedResearch:
    """Research with DOI citation AND prohibited claims (should be WARNING, not REJECTED)."""
    return TransformedResearch(
        source=ResearchSource.YOUTUBE,
        title="Study shows lion's mane treats cognitive decline",
        content="According to study 10.1016/j.jff.2024.001, lion's mane treats cognitive decline in elderly patients.",
        url="https://youtube.com/watch?v=abc123",
        tags=["lions_mane", "research", "cognitive"],
        source_metadata={
            "channel": "Health Research Channel",
            "views": 50000,
        },
        score=7.0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def research_with_borderline_claims() -> TransformedResearch:
    """Research with borderline claims (supports, promotes)."""
    return TransformedResearch(
        source=ResearchSource.NEWS,
        title="Functional mushrooms support immune health",
        content="Recent research suggests that functional mushrooms may support immune health and promote overall wellness.",
        url="https://healthnews.com/mushrooms-immune",
        tags=["functional_mushrooms", "immune_health"],
        source_metadata={
            "publisher": "Health News Daily",
            "publish_date": "2024-01-15",
        },
        score=6.5,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def research_batch(
    sample_pubmed_research: TransformedResearch,
    sample_reddit_research: TransformedResearch,
    research_with_prohibited_claims: TransformedResearch,
) -> list[TransformedResearch]:
    """Batch of research items with mixed compliance status."""
    return [
        sample_pubmed_research,
        sample_reddit_research,
        research_with_prohibited_claims,
    ]
