"""Test fixtures for PubMed Scanner tests.

Provides mock objects and sample data for testing PubMed scanner components
without making actual API calls.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any


@pytest.fixture
def mock_entrez_search_response() -> dict[str, Any]:
    """Mock Entrez esearch response."""
    return {
        "IdList": ["12345678", "87654321", "11111111"],
        "Count": "3",
        "RetMax": "50",
    }


@pytest.fixture
def mock_pubmed_article() -> dict[str, Any]:
    """Mock parsed PubMed article."""
    return {
        "pmid": "12345678",
        "title": "Effects of Hericium erinaceus on Cognitive Function: A Randomized Controlled Trial",
        "abstract": (
            "Background: Lion's mane (Hericium erinaceus) has been studied for cognitive benefits. "
            "Methods: 77 participants were randomized to receive lion's mane extract (n=39) or "
            "placebo (n=38) for 12 weeks. Results: The treatment group showed significant "
            "improvement in cognitive function scores (p<0.05). Conclusion: Lion's mane "
            "supplementation may support cognitive function."
        ),
        "authors": ["Mori K", "Inatomi S", "Ouchi K"],
        "journal": "Phytotherapy Research",
        "pub_date": datetime.now(timezone.utc) - timedelta(days=30),
        "doi": "10.1002/ptr.12345",
        "publication_types": ["Randomized Controlled Trial"],
    }


@pytest.fixture
def mock_pubmed_article_meta_analysis() -> dict[str, Any]:
    """Mock parsed PubMed meta-analysis article."""
    return {
        "pmid": "87654321",
        "title": "Systematic Review: Adaptogenic Effects of Medicinal Mushrooms",
        "abstract": (
            "Objective: To systematically review the adaptogenic properties of medicinal mushrooms. "
            "Methods: A comprehensive literature search identified 25 relevant studies (n=1,847 participants). "
            "Results: Meta-analysis showed moderate evidence for stress reduction effects (SMD=-0.42, 95% CI: -0.58 to -0.26). "
            "Conclusion: Current evidence suggests potential adaptogenic benefits."
        ),
        "authors": ["Smith J", "Brown A", "Wilson C", "Davis R"],
        "journal": "Journal of Alternative Medicine",
        "pub_date": datetime.now(timezone.utc) - timedelta(days=15),
        "doi": "10.1080/jam.2026.12345",
        "publication_types": ["Meta-Analysis", "Systematic Review"],
    }


@pytest.fixture
def mock_pubmed_article_review() -> dict[str, Any]:
    """Mock parsed PubMed review article."""
    return {
        "pmid": "11111111",
        "title": "A Review of Cordyceps militaris: Bioactive Compounds and Potential Health Benefits",
        "abstract": (
            "This review examines the bioactive compounds in Cordyceps militaris, including "
            "cordycepin and polysaccharides. Current research suggests potential applications "
            "in supporting energy metabolism and immune function. Further clinical trials "
            "are needed to establish efficacy and safety."
        ),
        "authors": ["Zhang L", "Wang Y"],
        "journal": "Nutrients",
        "pub_date": datetime.now(timezone.utc) - timedelta(days=60),
        "doi": "10.3390/nu12345",
        "publication_types": ["Review"],
    }


@pytest.fixture
def scanner_config():
    """Test scanner configuration.

    Import deferred to allow tests to run before implementation.
    """
    from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

    return PubMedScannerConfig(
        email="test@example.com",
        api_key="test_api_key",
        search_queries=["lion's mane cognition", "Hericium erinaceus"],
        publication_type_filters=["Randomized Controlled Trial"],
        lookback_days=90,
        max_results_per_query=10,
    )


@pytest.fixture
def minimal_scanner_config():
    """Minimal test scanner configuration."""
    from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

    return PubMedScannerConfig(
        email="test@example.com",
    )


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Mock LLM client for testing LLM stages."""
    client = AsyncMock()
    client.generate = AsyncMock(return_value='{"compound_studied": "test", "effect_measured": "test"}')
    return client


@pytest.fixture
def mock_entrez():
    """Mock Biopython Entrez module."""
    with patch("Bio.Entrez") as mock:
        mock.email = None
        mock.api_key = None
        mock.tool = None
        yield mock


@pytest.fixture
def mock_retry_middleware() -> MagicMock:
    """Mock retry middleware for API calls."""
    middleware = MagicMock()
    return middleware


@pytest.fixture
def mock_eu_compliance_checker() -> AsyncMock:
    """Mock EU compliance checker from Story 1.2."""
    checker = AsyncMock()
    checker.check_content = AsyncMock(
        return_value=MagicMock(
            is_compliant=True,
            status="COMPLIANT",
            issues=[],
        )
    )
    return checker


@pytest.fixture
def mock_research_publisher() -> AsyncMock:
    """Mock research publisher from Story 2.1."""
    publisher = AsyncMock()
    publisher.publish = AsyncMock(return_value=MagicMock(id="test-uuid"))
    publisher.publish_batch = AsyncMock(return_value=[MagicMock(id=f"uuid-{i}") for i in range(3)])
    return publisher


@pytest.fixture
def mock_research_scorer() -> MagicMock:
    """Mock research item scorer from Story 2.2."""
    scorer = MagicMock()
    scorer.score = MagicMock(
        return_value=MagicMock(
            final_score=7.5,
            component_scores={"freshness": 1.0, "relevance": 3.0},
        )
    )
    return scorer
