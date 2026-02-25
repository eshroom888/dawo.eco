"""Tests for ClaimsAlertFormatter.

Story 6-4, Task 2: Alert formatter tests.
"""

import pytest

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from integrations.discord import DiscordEmbed, EmbedColor
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig
from teams.dawo.scanners.claims_alerts.formatter import ClaimsAlertFormatter


@pytest.fixture
def formatter(alert_config: ClaimsAlertConfig) -> ClaimsAlertFormatter:
    return ClaimsAlertFormatter(config=alert_config)


@pytest.fixture
def sample_new_claim_event() -> RegulatoryEvent:
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


class TestFormatClaimAlert:
    """Tests for format_claim_alert()."""

    def test_new_claim_approved_embed(
        self, formatter: ClaimsAlertFormatter, sample_new_claim_event: RegulatoryEvent
    ) -> None:
        """NEW_CLAIM_APPROVED event produces correct embed."""
        embed = formatter.format_claim_alert(sample_new_claim_event)
        assert isinstance(embed, DiscordEmbed)
        assert "New Approved Claim" in embed.title
        assert embed.color == EmbedColor.SUCCESS.value
        # Applicable products field matches config keywords (case-insensitive)
        applicable_fields = [f for f in embed.fields if f.name == "Applicable Products"]
        assert len(applicable_fields) == 1
        assert "hericium" in applicable_fields[0].value.lower()

    def test_claim_status_changed_embed(self, formatter: ClaimsAlertFormatter) -> None:
        """CLAIM_STATUS_CHANGED event produces correct embed."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            claim_id="CLAIM-001",
            substance="Reishi extract",
            old_status="on_hold",
            new_status="authorised",
            severity="medium",
            data={"claim_text": "Reishi supports vitality"},
        )
        embed = formatter.format_claim_alert(event)
        assert isinstance(embed, DiscordEmbed)
        assert "Regulatory Update" in embed.title

    def test_novel_food_status_changed_embed(self, formatter: ClaimsAlertFormatter) -> None:
        """NOVEL_FOOD_STATUS_CHANGED event produces correct embed."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED,
            claim_id="NF-001",
            substance="Cordyceps militaris",
            old_status="pending",
            new_status="authorised",
            severity="medium",
            data={"claim_text": "Novel food status change"},
        )
        embed = formatter.format_claim_alert(event)
        assert isinstance(embed, DiscordEmbed)


class TestFormatEnforcementAlert:
    """Tests for format_enforcement_alert()."""

    def test_enforcement_embed_has_error_color(
        self, formatter: ClaimsAlertFormatter, sample_enforcement_event: RegulatoryEvent
    ) -> None:
        """Enforcement alert has ERROR color."""
        embed = formatter.format_enforcement_alert(sample_enforcement_event)
        assert embed.color == EmbedColor.ERROR.value
        assert "ENFORCEMENT ACTION" in embed.title

    def test_enforcement_embed_includes_url_field(
        self, formatter: ClaimsAlertFormatter, sample_enforcement_event: RegulatoryEvent
    ) -> None:
        """Enforcement alert includes source URL field."""
        embed = formatter.format_enforcement_alert(sample_enforcement_event)
        url_fields = [f for f in embed.fields if f.name == "Source URL"]
        assert len(url_fields) == 1


class TestFormatBatchAlert:
    """Tests for format_batch_alert()."""

    def test_batch_alert_with_multiple_events(
        self, formatter: ClaimsAlertFormatter, sample_new_claim_event: RegulatoryEvent
    ) -> None:
        """Batch alert summarizes multiple events."""
        events = [sample_new_claim_event, sample_new_claim_event]
        embed = formatter.format_batch_alert(events)
        assert "2" in embed.title
        assert embed.footer_text is not None
        assert "regulatory" in embed.footer_text.lower() or "dashboard" in embed.footer_text.lower()

    def test_batch_alert_respects_25_field_limit(
        self, formatter: ClaimsAlertFormatter
    ) -> None:
        """Batch alert respects Discord's 25-field limit."""
        events = [
            RegulatoryEvent(
                event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
                claim_id=f"CLAIM-{i:03d}",
                substance=f"Substance {i}",
                severity="low",
                data={"claim_text": f"Claim text {i}"},
            )
            for i in range(30)
        ]
        embed = formatter.format_batch_alert(events)
        assert len(embed.fields) <= 25


class TestExtractApplicableProducts:
    """Tests for _extract_applicable_products()."""

    def test_matches_substance_keyword(
        self, formatter: ClaimsAlertFormatter, sample_new_claim_event: RegulatoryEvent
    ) -> None:
        """Matches DAWO product keyword in substance field."""
        result = formatter._extract_applicable_products(sample_new_claim_event)
        assert "hericium" in result.lower()

    def test_returns_empty_for_unrelated_substance(
        self, formatter: ClaimsAlertFormatter
    ) -> None:
        """Returns empty for unrelated substance."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.CLAIM_STATUS_CHANGED,
            substance="Vitamin C",
            severity="low",
        )
        result = formatter._extract_applicable_products(event)
        assert result == "" or result.lower() == "none"
