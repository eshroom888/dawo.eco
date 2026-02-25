"""Shared fixtures for claims alerts tests.

Story 6-4: Common test fixtures for regulatory alert testing.
"""

import pytest
from unittest.mock import AsyncMock

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from integrations.discord import DiscordClientProtocol
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig


@pytest.fixture
def alert_config() -> ClaimsAlertConfig:
    """Standard alert config for testing."""
    return ClaimsAlertConfig(
        enabled=True,
        webhook_url="https://discord.com/api/webhooks/test/test",
        batch_window_seconds=300,
        dashboard_url="https://app.imagoeco.com/dawo/regulatory",
        dawo_product_keywords=(
            "lion's mane", "chaga", "reishi", "cordyceps",
            "hericium", "inonotus", "ganoderma", "beta-glucan",
            "adaptogen", "functional mushroom", "sopp",
        ),
        severity_emoji_map={
            "critical": "red_circle",
            "high": "orange_circle",
            "medium": "yellow_circle",
            "low": "white_circle",
        },
    )


@pytest.fixture
def sample_new_claim_event() -> RegulatoryEvent:
    """Sample NEW_CLAIM_APPROVED event from Story 6-1."""
    return RegulatoryEvent(
        event_type=RegulatoryEventType.NEW_CLAIM_APPROVED,
        claim_id="CLAIM-2026-001",
        substance="Beta-glucans from Hericium erinaceus",
        old_status="",
        new_status="authorised",
        severity="high",
        data={
            "claim_text": "Beta-glucans contribute to normal immune function",
            "conditions_of_use": "3g per day",
            "product_categories": ["food supplement"],
            "approval_date": "2026-02-01",
        },
    )


@pytest.fixture
def sample_enforcement_event() -> RegulatoryEvent:
    """Sample MATTILSYNET_ENFORCEMENT_ACTION event from Story 6-3."""
    return RegulatoryEvent(
        event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
        claim_id="",
        substance="",
        severity="critical",
        data={
            "title": "Tilbakekalling: Soppekstrakt med ulovlige helsepastander",
            "url": "https://www.mattilsynet.no/varsler/tilbakekalling-soppekstrakt",
            "category": "enforcement",
            "keywords_matched": ["tilbakekalling", "helsepastander", "sopp"],
            "content_summary": "Mattilsynet har vedtatt tilbakekalling av et kosttilskudd.",
        },
    )


@pytest.fixture
def sample_irrelevant_event() -> RegulatoryEvent:
    """Event that does NOT relate to DAWO products."""
    return RegulatoryEvent(
        event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
        claim_id="CLAIM-9999",
        substance="Vitamin C",
        old_status="authorised",
        new_status="on_hold",
        severity="low",
        data={"claim_text": "Vitamin C contributes to normal immune function"},
    )


@pytest.fixture
def mock_discord_client() -> AsyncMock:
    """Mock Discord client."""
    client = AsyncMock(spec=DiscordClientProtocol)
    client.send_embed = AsyncMock(return_value=True)
    return client
