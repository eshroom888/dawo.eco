"""Test fixtures for B2B Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Provides mock fixtures for Hunter.io API and pipeline components.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.leads.scanner.config import HunterClientConfig, LeadScannerConfig
from teams.dawo.leads.scanner.schemas import (
    RawLead,
    HarvestedLead,
    HarvestedContact,
    TransformedLead,
)
from teams.dawo.leads.scanner.tools import HunterClient


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def hunter_config() -> HunterClientConfig:
    """Hunter.io API configuration for testing."""
    return HunterClientConfig(
        api_key="test_api_key_123",
        base_url="https://api.hunter.io/v2",
        timeout_seconds=10,
        rate_limit_per_minute=60,
    )


@pytest.fixture
def scanner_config() -> LeadScannerConfig:
    """Lead scanner configuration for testing."""
    return LeadScannerConfig(
        industries=["health food store", "wellness retailer"],
        search_keywords=["helsekost", "organic shop"],
        countries=["Norway", "Sweden"],
        min_confidence=0.7,
        max_leads_per_scan=10,
        required_fields=["email", "company"],
        preferred_positions=["owner", "ceo", "manager"],
        rate_limit_per_minute=60,
    )


# ============================================================================
# Hunter.io API Response Fixtures
# ============================================================================


@pytest.fixture
def mock_hunter_domain_response() -> dict:
    """Mock Hunter.io domain-search response."""
    return {
        "domain": "example-health.no",
        "organization": "Example Health Store",
        "company": "Example Health Store AS",
        "country": "Norway",
        "state": None,
        "city": "Oslo",
        "industry": "Health Food",
        "linkedin": "https://linkedin.com/company/example-health",
        "twitter": "example_health",
        "facebook": "examplehealth",
        "phone_number": "+47 12345678",
        "headcount": "11-50",
        "emails": [
            {
                "value": "john.doe@example-health.no",
                "type": "personal",
                "confidence": 95,
                "first_name": "John",
                "last_name": "Doe",
                "position": "CEO",
                "department": "management",
                "linkedin": "https://linkedin.com/in/johndoe",
                "phone_number": "+47 98765432",
            },
            {
                "value": "jane.smith@example-health.no",
                "type": "personal",
                "confidence": 87,
                "first_name": "Jane",
                "last_name": "Smith",
                "position": "Purchasing Manager",
                "department": "operations",
                "linkedin": None,
                "phone_number": None,
            },
            {
                "value": "info@example-health.no",
                "type": "generic",
                "confidence": 40,
                "first_name": None,
                "last_name": None,
                "position": None,
                "department": None,
                "linkedin": None,
                "phone_number": None,
            },
        ],
    }


@pytest.fixture
def mock_hunter_empty_response() -> dict:
    """Mock Hunter.io response with no emails."""
    return {
        "domain": "no-emails.no",
        "organization": "No Emails Company",
        "country": "Norway",
        "emails": [],
    }


@pytest.fixture
def mock_hunter_low_confidence_response() -> dict:
    """Mock Hunter.io response with low confidence emails only."""
    return {
        "domain": "low-conf.no",
        "organization": "Low Confidence Inc",
        "country": "Norway",
        "emails": [
            {
                "value": "maybe@low-conf.no",
                "confidence": 30,
                "first_name": None,
                "last_name": None,
            },
        ],
    }


# ============================================================================
# Mock Client Fixtures
# ============================================================================


@pytest.fixture
def mock_hunter_client(mock_hunter_domain_response: dict) -> AsyncMock:
    """Mock HunterClient for testing without API calls."""
    client = AsyncMock(spec=HunterClient)
    client.domain_search.return_value = mock_hunter_domain_response
    client.email_finder.return_value = {
        "email": "found@example.com",
        "score": 90,
        "position": "Manager",
    }
    client.email_verifier.return_value = {
        "status": "valid",
        "result": "deliverable",
        "score": 95,
    }
    client.account_info.return_value = {
        "email": "test@company.com",
        "plan_name": "Starter",
        "requests": {
            "searches": {"used": 50, "available": 450},
        },
    }
    return client


# ============================================================================
# Data Model Fixtures
# ============================================================================


@pytest.fixture
def sample_raw_lead() -> RawLead:
    """Sample raw lead for testing."""
    return RawLead(
        domain="example-health.no",
        company_name="Example Health Store",
        country="Norway",
        industry="Health Food",
        source_url="https://example-health.no",
        confidence=0.95,
        discovered_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_raw_leads() -> list[RawLead]:
    """List of sample raw leads for testing."""
    return [
        RawLead(
            domain="health-shop.no",
            company_name="Health Shop AS",
            country="Norway",
            confidence=0.9,
        ),
        RawLead(
            domain="wellness-store.se",
            company_name="Wellness Store AB",
            country="Sweden",
            confidence=0.85,
        ),
        RawLead(
            domain="low-quality.no",
            company_name="Low Quality",
            country="Norway",
            confidence=0.5,  # Below threshold
        ),
    ]


@pytest.fixture
def sample_harvested_contact() -> HarvestedContact:
    """Sample harvested contact for testing."""
    return HarvestedContact(
        email="john.doe@example-health.no",
        first_name="John",
        last_name="Doe",
        position="CEO",
        department="management",
        linkedin="https://linkedin.com/in/johndoe",
        phone="+47 98765432",
        confidence=0.95,
    )


@pytest.fixture
def sample_harvested_lead(sample_harvested_contact: HarvestedContact) -> HarvestedLead:
    """Sample harvested lead for testing."""
    return HarvestedLead(
        domain="example-health.no",
        company_name="Example Health Store AS",
        contacts=[
            sample_harvested_contact,
            HarvestedContact(
                email="jane.smith@example-health.no",
                first_name="Jane",
                last_name="Smith",
                position="Purchasing Manager",
                confidence=0.87,
            ),
        ],
        organization="Example Health Store",
        country="Norway",
        city="Oslo",
        linkedin="https://linkedin.com/company/example-health",
        headcount="11-50",
        industry="Health Food",
    )


@pytest.fixture
def sample_harvested_leads(sample_harvested_lead: HarvestedLead) -> list[HarvestedLead]:
    """List of sample harvested leads for testing."""
    return [
        sample_harvested_lead,
        HarvestedLead(
            domain="wellness-store.se",
            company_name="Wellness Store AB",
            contacts=[
                HarvestedContact(
                    email="contact@wellness-store.se",
                    first_name="Erik",
                    last_name="Svensson",
                    position="Owner",
                    confidence=0.92,
                ),
            ],
            country="Sweden",
            industry="Wellness",
        ),
    ]


@pytest.fixture
def sample_transformed_lead() -> TransformedLead:
    """Sample transformed lead for testing."""
    return TransformedLead(
        email="john.doe@example-health.no",
        first_name="John",
        last_name="Doe",
        company="Example Health Store AS",
        job_title="CEO",
        website_url="https://example-health.no",
        linkedin_url="https://linkedin.com/in/johndoe",
        phone="+47 98765432",
        country="Norway",
        industry="Health Food",
        company_size="11-50",
        source="cold_research",
        status="new",
        score=0.0,
        enrichment_data={
            "source": "hunter.io",
            "confidence": 0.95,
        },
    )


@pytest.fixture
def sample_transformed_leads(sample_transformed_lead: TransformedLead) -> list[TransformedLead]:
    """List of sample transformed leads for testing."""
    return [
        sample_transformed_lead,
        TransformedLead(
            email="erik.svensson@wellness-store.se",
            first_name="Erik",
            last_name="Svensson",
            company="Wellness Store AB",
            job_title="Owner",
            country="Sweden",
        ),
    ]


# ============================================================================
# Repository Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_lead_repository() -> AsyncMock:
    """Mock LeadRepository for testing."""
    repo = AsyncMock()
    repo.get_lead_by_email.return_value = None  # No existing leads by default
    repo.get_leads_by_company.return_value = []  # No existing leads by default
    repo.bulk_create_leads.return_value = (2, [uuid4(), uuid4()])
    repo.create_lead.return_value = MagicMock(id=uuid4())
    return repo


@pytest.fixture
def mock_notification_service() -> AsyncMock:
    """Mock notification service for testing."""
    service = AsyncMock()
    service.send_alert.return_value = True
    return service
