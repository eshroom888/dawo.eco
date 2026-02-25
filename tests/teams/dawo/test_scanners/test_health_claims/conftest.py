"""Shared fixtures for health claims tests.

Story 6-1, Task 12: Test fixtures.
"""

import pytest
from datetime import datetime, UTC
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pandas as pd

from core.regulatory.events import RegulatoryEventEmitter
from teams.dawo.scanners.health_claims.config import HealthClaimsMonitorConfig
from teams.dawo.scanners.health_claims.schemas import ClaimChangeRecord


@dataclass
class MockRetryResult:
    """Mock for RetryResult."""
    success: bool = True
    response: object = None
    attempts: int = 1
    last_error: Optional[str] = None
    is_incomplete: bool = False
    operation_id: str = ""


@pytest.fixture
def sample_claims_df():
    """Sample EU Health Claims DataFrame for testing."""
    return pd.DataFrame({
        "claim_id": ["ID-001", "ID-002", "ID-003", "ID-004", "ID-005"],
        "claim_type": ["Article 13.1", "Article 13.1", "Article 13.1", "Article 14.1", "Article 13.1"],
        "substance": ["Beta-glucans", "Vitamin C", "Ganoderma lucidum", "Calcium", "Ashwagandha"],
        "health_relationship": [
            "Maintenance of normal blood cholesterol",
            "Protection of cells from oxidative stress",
            "Immune system support",
            "Bone health",
            "Stress reduction",
        ],
        "claim_text": [
            "Beta-glucans contribute to the maintenance of normal blood cholesterol levels",
            "Vitamin C contributes to the protection of cells from oxidative stress",
            "Ganoderma lucidum contributes to immune system support",
            "Calcium is needed for the maintenance of normal bones",
            "Ashwagandha helps with stress reduction",
        ],
        "conditions_of_use": [
            "3g per day",
            "80mg per day",
            "1g per day",
            "800mg per day",
            "300mg per day",
        ],
        "food_category": ["Food supplements", "Food supplements", "Food supplements", "Dairy", "Food supplements"],
        "status": ["Authorised", "Authorised", "On hold", "Authorised", "On hold"],
        "efsa_opinion": ["EFSA-Q-2009-00748", "EFSA-Q-2008-01159", None, "EFSA-Q-2008-01156", None],
        "commission_regulation": ["EU 432/2012", "EU 432/2012", None, "EU 432/2012", None],
        "date_of_entry": [
            datetime(2012, 5, 16),
            datetime(2012, 5, 16),
            datetime(2010, 1, 1),
            datetime(2012, 5, 16),
            datetime(2010, 1, 1),
        ],
        "last_update": [None, None, None, None, None],
        "restrictions": [None, None, None, None, None],
    })


@pytest.fixture
def sample_claims_df_modified(sample_claims_df):
    """Modified version of sample claims for change detection tests."""
    df = sample_claims_df.copy()
    # Modify status of ID-003 (Ganoderma) from On hold to Authorised
    df.loc[df["claim_id"] == "ID-003", "status"] = "Authorised"
    # Remove ID-005 (Ashwagandha)
    df = df[df["claim_id"] != "ID-005"].copy()
    # Add new claim ID-006
    new_row = pd.DataFrame({
        "claim_id": ["ID-006"],
        "claim_type": ["Article 13.1"],
        "substance": ["Rhodiola rosea"],
        "health_relationship": ["Mental performance"],
        "claim_text": ["Rhodiola rosea contributes to optimal mental performance"],
        "conditions_of_use": ["200mg per day"],
        "food_category": ["Food supplements"],
        "status": ["Authorised"],
        "efsa_opinion": [None],
        "commission_regulation": [None],
        "date_of_entry": [datetime(2026, 1, 1)],
        "last_update": [None],
        "restrictions": [None],
    })
    df = pd.concat([df, new_row], ignore_index=True)
    return df


@pytest.fixture
def health_claims_config():
    """Standard health claims config for testing."""
    return HealthClaimsMonitorConfig(
        source_url="https://data.europa.eu/data/datasets/eu-register",
        download_url="https://ec.europa.eu/food/claims/test.xls",
        mushroom_keywords=("beta-glucan", "ganoderma", "reishi"),
        adaptogen_keywords=("ashwagandha", "rhodiola"),
        vitamin_mineral_keywords=("vitamin c", "vitamin d", "calcium"),
    )


@pytest.fixture
def mock_retry_middleware():
    """Mock RetryMiddleware returning success."""
    retry = AsyncMock()
    retry.execute_with_retry.return_value = MockRetryResult(
        success=True,
        response=b"<test data>",
        attempts=1,
    )
    return retry


@pytest.fixture
def mock_retry_middleware_failure():
    """Mock RetryMiddleware returning failure."""
    retry = AsyncMock()
    retry.execute_with_retry.return_value = MockRetryResult(
        success=False,
        response=None,
        last_error="Connection timed out",
        is_incomplete=True,
    )
    return retry


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient."""
    client = AsyncMock()
    response = MagicMock()
    response.content = b"<test xls data>"
    response.status_code = 200
    response.raise_for_status = MagicMock()
    client.get.return_value = response
    return client


@pytest.fixture
def mock_event_emitter():
    """Mock RegulatoryEventEmitter."""
    emitter = AsyncMock(spec=RegulatoryEventEmitter)
    return emitter
