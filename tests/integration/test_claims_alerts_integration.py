"""Integration tests for claims alerts pipeline.

Story 6-4, Task 10: End-to-end integration tests.

Tests the full flow from event emission through to Discord send,
verifying all components work together correctly.
"""

import asyncio
from datetime import datetime, timedelta, UTC

import pytest
from unittest.mock import AsyncMock

from core.regulatory.events import (
    RegulatoryEvent,
    RegulatoryEventEmitter,
    RegulatoryEventType,
)
from integrations.discord import DiscordClientProtocol
from teams.dawo.scanners.claims_alerts.batcher import ClaimsAlertBatcher
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig
from teams.dawo.scanners.claims_alerts.formatter import ClaimsAlertFormatter
from teams.dawo.scanners.claims_alerts.relevance_filter import DAWORelevanceFilter
from teams.dawo.scanners.claims_alerts.schemas import AlertStatus
from teams.dawo.scanners.claims_alerts.service import ClaimsAlertService
from teams.dawo.scanners.claims_alerts.subscriber import RegulatoryAlertSubscriber


@pytest.fixture
def config() -> ClaimsAlertConfig:
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
def mock_discord() -> AsyncMock:
    client = AsyncMock(spec=DiscordClientProtocol)
    client.send_embed = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_queue() -> AsyncMock:
    queue = AsyncMock()
    queue.queue_failed = AsyncMock(return_value=None)
    return queue


@pytest.fixture
def service(
    config: ClaimsAlertConfig,
    mock_discord: AsyncMock,
    mock_queue: AsyncMock,
) -> ClaimsAlertService:
    return ClaimsAlertService(
        discord_client=mock_discord,
        formatter=ClaimsAlertFormatter(config=config),
        batcher=ClaimsAlertBatcher(config=config),
        relevance_filter=DAWORelevanceFilter(config=config),
        notification_queue=mock_queue,
        config=config,
    )


class TestFullFlowIntegration:
    """10.1: Full flow from event emission to Discord embed."""

    @pytest.mark.asyncio
    async def test_emit_event_subscriber_receives_service_processes_discord_sends(
        self,
        config: ClaimsAlertConfig,
        mock_discord: AsyncMock,
        mock_queue: AsyncMock,
    ) -> None:
        """Full pipeline: emit -> subscribe -> service -> format -> Discord."""
        emitter = RegulatoryEventEmitter()
        service = ClaimsAlertService(
            discord_client=mock_discord,
            formatter=ClaimsAlertFormatter(config=config),
            batcher=ClaimsAlertBatcher(config=config),
            relevance_filter=DAWORelevanceFilter(config=config),
            notification_queue=mock_queue,
            config=config,
        )
        subscriber = RegulatoryAlertSubscriber(
            service=service,
            event_emitter=emitter,
        )

        # Start subscriber
        task = asyncio.create_task(subscriber.start())
        await asyncio.sleep(0.05)

        # Emit a CRITICAL enforcement event (sends immediately)
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
            substance="Sopp supplement",
            severity="critical",
            data={
                "title": "Enforcement: supplement recall",
                "url": "https://mattilsynet.no/test",
                "category": "enforcement",
                "keywords_matched": ["sopp"],
            },
        )
        await emitter.emit(event)
        await asyncio.sleep(0.05)

        # Stop subscriber
        await subscriber.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.CancelledError:
            pass

        # Verify Discord received the embed
        mock_discord.send_embed.assert_called()
        sent_embed = mock_discord.send_embed.call_args[0][0]
        assert "ENFORCEMENT ACTION" in sent_embed.title


class TestBatchingIntegration:
    """10.2: Batching multiple events into single Discord call."""

    @pytest.mark.asyncio
    async def test_three_events_within_window_batch_to_single_call(
        self,
        service: ClaimsAlertService,
        mock_discord: AsyncMock,
    ) -> None:
        """3 events within batch window → single batch Discord call after flush."""
        events = [
            RegulatoryEvent(
                event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
                claim_id=f"CLAIM-{i}",
                substance="Reishi extract",
                severity="low",
                data={"claim_text": f"Claim update {i}"},
            )
            for i in range(3)
        ]

        for event in events:
            result = await service.handle_event(event)
            assert result.status == AlertStatus.BATCHED

        # No Discord calls yet (all batched)
        mock_discord.send_embed.assert_not_called()

        # Flush
        result = await service.flush_pending()
        assert result.status == AlertStatus.SENT
        assert result.events_processed == 3

        # Single Discord call with batch embed
        mock_discord.send_embed.assert_called_once()
        sent_embed = mock_discord.send_embed.call_args[0][0]
        assert "3" in sent_embed.title  # "3 Regulatory Updates Detected"


class TestEnforcementBypassIntegration:
    """10.3: Enforcement bypasses batcher."""

    @pytest.mark.asyncio
    async def test_critical_enforcement_sends_immediately(
        self,
        service: ClaimsAlertService,
        mock_discord: AsyncMock,
    ) -> None:
        """CRITICAL enforcement → immediate Discord call (no batching)."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
            substance="",
            severity="critical",
            data={
                "title": "Enforcement action",
                "url": "https://mattilsynet.no/test",
                "category": "enforcement",
            },
        )

        result = await service.handle_event(event)
        assert result.status == AlertStatus.SENT
        mock_discord.send_embed.assert_called_once()

        # Verify it was an enforcement embed (ERROR color)
        sent_embed = mock_discord.send_embed.call_args[0][0]
        assert "ENFORCEMENT" in sent_embed.title


class TestRelevanceFilteringIntegration:
    """10.4: Irrelevant events produce no Discord call."""

    @pytest.mark.asyncio
    async def test_irrelevant_event_no_discord_call(
        self,
        service: ClaimsAlertService,
        mock_discord: AsyncMock,
    ) -> None:
        """Irrelevant event → no Discord call."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            substance="Vitamin D3",
            severity="low",
            data={"claim_text": "Vitamin D contributes to calcium absorption"},
        )

        result = await service.handle_event(event)
        assert result.status == AlertStatus.FILTERED
        mock_discord.send_embed.assert_not_called()


class TestRetryOnFailureIntegration:
    """10.5: Discord failure → notification queue receives failed alert."""

    @pytest.mark.asyncio
    async def test_discord_failure_queues_for_retry(
        self,
        service: ClaimsAlertService,
        mock_discord: AsyncMock,
        mock_queue: AsyncMock,
    ) -> None:
        """Discord send failure → alert queued for retry."""
        mock_discord.send_embed.return_value = False

        event = RegulatoryEvent(
            event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
            substance="Chaga supplement",
            severity="critical",
            data={
                "title": "Enforcement: chaga supplement recall",
                "url": "https://mattilsynet.no/test",
                "category": "enforcement",
            },
        )

        result = await service.handle_event(event)
        assert result.status == AlertStatus.QUEUED_FOR_RETRY
        mock_queue.queue_failed.assert_called_once()

        # Verify queue received embed data
        queued_data = mock_queue.queue_failed.call_args[0][0]
        assert "embed" in queued_data
        assert "error" in queued_data
