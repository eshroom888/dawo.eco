"""Tests for ClaimsAlertService.

Story 6-4, Task 5: Alert service tests.
"""

import pytest
from unittest.mock import AsyncMock

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from integrations.discord import DiscordClientProtocol, DiscordEmbed
from teams.dawo.scanners.claims_alerts.batcher import ClaimsAlertBatcher
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig
from teams.dawo.scanners.claims_alerts.formatter import ClaimsAlertFormatter
from teams.dawo.scanners.claims_alerts.relevance_filter import DAWORelevanceFilter
from teams.dawo.scanners.claims_alerts.schemas import AlertStatus
from teams.dawo.scanners.claims_alerts.service import ClaimsAlertService


@pytest.fixture
def mock_discord_client() -> AsyncMock:
    client = AsyncMock(spec=DiscordClientProtocol)
    client.send_embed = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_notification_queue() -> AsyncMock:
    queue = AsyncMock()
    queue.queue_failed = AsyncMock(return_value=None)
    return queue


@pytest.fixture
def service(
    alert_config: ClaimsAlertConfig,
    mock_discord_client: AsyncMock,
    mock_notification_queue: AsyncMock,
) -> ClaimsAlertService:
    formatter = ClaimsAlertFormatter(config=alert_config)
    batcher = ClaimsAlertBatcher(config=alert_config)
    relevance_filter = DAWORelevanceFilter(config=alert_config)
    return ClaimsAlertService(
        discord_client=mock_discord_client,
        formatter=formatter,
        batcher=batcher,
        relevance_filter=relevance_filter,
        notification_queue=mock_notification_queue,
        config=alert_config,
    )


@pytest.fixture
def relevant_high_event() -> RegulatoryEvent:
    return RegulatoryEvent(
        event_type=RegulatoryEventType.NEW_CLAIM_APPROVED,
        substance="Beta-glucans from Hericium erinaceus",
        severity="high",
        data={"claim_text": "Beta-glucans contribute to normal immune function"},
    )


@pytest.fixture
def irrelevant_event() -> RegulatoryEvent:
    return RegulatoryEvent(
        event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
        substance="Vitamin C",
        severity="low",
        data={"claim_text": "Vitamin C contributes to normal immune function"},
    )


@pytest.fixture
def critical_enforcement_event() -> RegulatoryEvent:
    return RegulatoryEvent(
        event_type=RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
        substance="Unknown",
        severity="critical",
        data={
            "title": "Enforcement action",
            "url": "https://mattilsynet.no/test",
            "category": "enforcement",
        },
    )


class TestHandleEvent:
    """Tests for handle_event()."""

    @pytest.mark.asyncio
    async def test_skips_irrelevant_events(
        self,
        service: ClaimsAlertService,
        irrelevant_event: RegulatoryEvent,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Skips irrelevant events (filtered)."""
        result = await service.handle_event(irrelevant_event)
        assert result.status == AlertStatus.FILTERED
        mock_discord_client.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_batches_non_urgent_events(
        self,
        service: ClaimsAlertService,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Batches non-urgent relevant events (medium severity, not enforcement)."""
        medium_event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            substance="Reishi extract",
            severity="medium",
            data={"claim_text": "Reishi extract status update"},
        )
        result = await service.handle_event(medium_event)
        assert result.status == AlertStatus.BATCHED
        mock_discord_client.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_immediately_for_critical_enforcement(
        self,
        service: ClaimsAlertService,
        critical_enforcement_event: RegulatoryEvent,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Sends immediately for CRITICAL enforcement."""
        result = await service.handle_event(critical_enforcement_event)
        assert result.status == AlertStatus.SENT
        mock_discord_client.send_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_queues_for_retry_on_discord_failure(
        self,
        service: ClaimsAlertService,
        critical_enforcement_event: RegulatoryEvent,
        mock_discord_client: AsyncMock,
        mock_notification_queue: AsyncMock,
    ) -> None:
        """Queues for retry when Discord send fails."""
        mock_discord_client.send_embed.return_value = False
        result = await service.handle_event(critical_enforcement_event)
        assert result.status == AlertStatus.QUEUED_FOR_RETRY
        mock_notification_queue.queue_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_disabled_config_returns_early(
        self,
        mock_discord_client: AsyncMock,
        mock_notification_queue: AsyncMock,
        relevant_high_event: RegulatoryEvent,
    ) -> None:
        """Disabled config returns early with FILTERED status."""
        config = ClaimsAlertConfig(
            enabled=False,
            webhook_url="",
            dawo_product_keywords=("chaga",),
        )
        formatter = ClaimsAlertFormatter(config=config)
        batcher = ClaimsAlertBatcher(config=config)
        relevance_filter = DAWORelevanceFilter(config=config)
        service = ClaimsAlertService(
            discord_client=mock_discord_client,
            formatter=formatter,
            batcher=batcher,
            relevance_filter=relevance_filter,
            notification_queue=mock_notification_queue,
            config=config,
        )
        result = await service.handle_event(relevant_high_event)
        assert result.status == AlertStatus.FILTERED
        mock_discord_client.send_embed.assert_not_called()


class TestFlushPending:
    """Tests for flush_pending()."""

    @pytest.mark.asyncio
    async def test_sends_batched_events(
        self,
        service: ClaimsAlertService,
        mock_discord_client: AsyncMock,
    ) -> None:
        """flush_pending sends batched events."""
        # Use medium-severity event so it gets batched (not sent immediately)
        medium_event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            substance="Reishi extract",
            severity="medium",
            data={"claim_text": "Reishi extract status changed"},
        )
        await service.handle_event(medium_event)
        mock_discord_client.send_embed.reset_mock()

        result = await service.flush_pending()
        assert result.status == AlertStatus.SENT
        mock_discord_client.send_embed.assert_called_once()
