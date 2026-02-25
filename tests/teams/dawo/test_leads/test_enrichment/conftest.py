"""Test fixtures for Lead Enrichment tests.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment

Provides reusable fixtures for enrichment module tests.
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def sample_lead_id():
    """Generate a sample lead UUID."""
    return uuid4()


@pytest.fixture
def sample_domain():
    """Sample domain for testing."""
    return "healthstore.no"


@pytest.fixture
def sample_company():
    """Sample company name."""
    return "Health Store AS"


@pytest.fixture
def sample_website_content():
    """Sample website HTML content."""
    return """
    <html>
    <head><title>Health Store - Premium Supplements</title></head>
    <body>
    <h1>Welcome to Health Store</h1>
    <p>We are Oslo's premier destination for organic health foods and supplements.</p>
    <p>Our product range includes lion's mane, reishi, and other functional mushrooms.</p>
    <p>We focus on organic, sustainable, and locally-sourced products.</p>
    </body>
    </html>
    """


@pytest.fixture
def sample_hunter_domain_response():
    """Sample Hunter.io domain search response."""
    return {
        "domain": "healthstore.no",
        "company": "Health Store AS",
        "organization": "Health Store AS",
        "country": "Norway",
        "emails": [
            {
                "value": "john@healthstore.no",
                "first_name": "John",
                "last_name": "Smith",
                "position": "CEO",
                "department": "management",
                "linkedin": "linkedin.com/in/johnsmith",
                "confidence": 95,
            },
            {
                "value": "contact@healthstore.no",
                "first_name": None,
                "last_name": None,
                "position": None,
                "department": "general",
                "linkedin": None,
                "confidence": 75,
            },
        ],
        "headcount": "11-50",
        "industry": "Retail - Health & Wellness",
    }


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for website requests."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for business analysis."""
    client = AsyncMock()
    return client


@pytest.fixture
def enrichment_config():
    """Sample enrichment configuration."""
    from teams.dawo.leads.enrichment.config import EnrichmentConfig

    return EnrichmentConfig(
        min_confidence_threshold=5.0,
        website_timeout_seconds=5,
        batch_size=10,
    )
