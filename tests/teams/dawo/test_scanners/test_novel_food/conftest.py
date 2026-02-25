"""Shared fixtures for Novel Food Catalogue Monitor tests.

Story 6-2: Novel Food Catalogue Monitor.
"""

import json
import pytest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from core.regulatory.events import RegulatoryEventEmitter
from teams.dawo.scanners.novel_food.config import (
    SpeciesConfig,
    NovelFoodMonitorConfig,
)
from teams.dawo.scanners.novel_food.schemas import NovelFoodEntryRecord


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
def species_config_dawo():
    """Species config for DAWO products."""
    return (
        SpeciesConfig(
            latin_name="Hericium erinaceus",
            common_names=("Lion's Mane",),
            is_dawo_product=True,
        ),
        SpeciesConfig(
            latin_name="Inonotus obliquus",
            common_names=("Chaga",),
            is_dawo_product=True,
        ),
    )


@pytest.fixture
def novel_food_config(species_config_dawo):
    """Standard Novel Food monitor config for testing."""
    return NovelFoodMonitorConfig(
        search_url="https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search",
        portal_url="https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search",
        species=species_config_dawo,
    )


@pytest.fixture
def sample_json_response():
    """Mock JSON response from backend API for Hericium erinaceus."""
    return json.dumps([
        {
            "name": "Hericium erinaceus (Lion's Mane) - fruiting body",
            "novelFoodStatus": "Yes",
            "authorisationStatus": None,
            "historyOfConsumption": "No history of significant consumption",
            "memberStateComments": "DE: Novel food",
            "commissionComments": "Classified as novel food",
            "conditionsOfUse": None,
            "regulationReference": None,
            "unionListEntry": "No",
        },
        {
            "name": "Hericium erinaceus - extract",
            "novelFoodStatus": "Yes",
            "authorisationStatus": None,
            "historyOfConsumption": "No history of consumption as food supplement",
            "memberStateComments": "FR: Novel food",
            "commissionComments": None,
            "conditionsOfUse": None,
            "regulationReference": None,
            "unionListEntry": "No",
        },
    ]).encode("utf-8")


@pytest.fixture
def sample_html_response():
    """Mock HTML response from search page."""
    return b"""<html><body>
    <div class="search-result-item">
        <h3>Hericium erinaceus (Lion's Mane) - fruiting body</h3>
        <div class="field-novel-food-status">Yes</div>
        <div class="field-authorisation-status"></div>
        <div class="field-history">No history of significant consumption</div>
        <div class="field-member-state">DE: Novel food</div>
        <div class="field-commission">Classified as novel food</div>
        <div class="field-conditions"></div>
        <div class="field-regulation"></div>
        <div class="field-union-list">No</div>
    </div>
    </body></html>"""


@pytest.fixture
def sample_entry_records():
    """Sample NovelFoodEntryRecord list for testing."""
    return [
        NovelFoodEntryRecord(
            species_latin="Hericium erinaceus",
            species_common="Lion's Mane",
            entry_name="Hericium erinaceus (Lion's Mane) - fruiting body",
            novel_food_status="novel",
            authorization_status="not_applicable",
            history_of_consumption="No history of significant consumption",
            member_state_comments="DE: Novel food",
            commission_comments="Classified as novel food",
            union_list_entry="No",
        ),
        NovelFoodEntryRecord(
            species_latin="Hericium erinaceus",
            species_common="Lion's Mane",
            entry_name="Hericium erinaceus - extract",
            novel_food_status="novel",
            authorization_status="not_applicable",
            history_of_consumption="No history of consumption as food supplement",
            member_state_comments="FR: Novel food",
        ),
    ]


@pytest.fixture
def sample_entry_records_modified():
    """Modified entries for change detection tests."""
    return [
        NovelFoodEntryRecord(
            species_latin="Hericium erinaceus",
            species_common="Lion's Mane",
            entry_name="Hericium erinaceus (Lion's Mane) - fruiting body",
            novel_food_status="not_novel",  # CHANGED from novel
            authorization_status="not_applicable",
            history_of_consumption="No history of significant consumption",
            member_state_comments="DE: Not novel food (updated)",  # CHANGED
            commission_comments="Reclassified as not novel",  # CHANGED
            union_list_entry="No",
        ),
        # extract entry REMOVED
        # NEW entry added
        NovelFoodEntryRecord(
            species_latin="Hericium erinaceus",
            species_common="Lion's Mane",
            entry_name="Hericium erinaceus - mycelium",
            novel_food_status="novel",
            authorization_status="not_applicable",
        ),
    ]


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
    response.content = b'[{"name": "test"}]'
    response.status_code = 200
    response.raise_for_status = MagicMock()
    client.get.return_value = response
    return client


@pytest.fixture
def mock_event_emitter():
    """Mock RegulatoryEventEmitter."""
    return AsyncMock(spec=RegulatoryEventEmitter)
