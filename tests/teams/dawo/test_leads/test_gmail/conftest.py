"""Test fixtures for Gmail API Integration.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Provides shared fixtures and mocks for Gmail testing.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.leads.gmail.client import GmailClient
from teams.dawo.leads.gmail.schemas import GmailSendResult
from teams.dawo.leads.gmail.config import GmailConfig, GmailRateLimitConfig
from core.leads.models import LeadStatus


@pytest.fixture
def gmail_config() -> GmailConfig:
    """Provide Gmail config for testing."""
    return GmailConfig(
        sender_email="sales@dawo.no",
        sender_name="DAWO Sales",
        company_address="Oslo, Norway",
    )


@pytest.fixture
def rate_config() -> GmailRateLimitConfig:
    """Provide rate limit config with high limits for tests."""
    return GmailRateLimitConfig(
        max_per_minute=100,
        max_per_day=1000,
        burst_size=10,
    )
