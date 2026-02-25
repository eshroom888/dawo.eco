"""Claims Alert Formatter.

Epic 6, Story 6-4, Task 2: Format regulatory events as Discord embeds.

Converts RegulatoryEvent objects into rich Discord embeds for operator alerts.
Handles single claim alerts, enforcement alerts, and batched summaries.
"""

import logging
from datetime import datetime, UTC

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from integrations.discord import DiscordEmbed, EmbedField, EmbedColor
from teams.dawo.scanners.claims_alerts.config import ClaimsAlertConfig

logger = logging.getLogger(__name__)

# Event types that represent new opportunities
_NEW_CLAIM_TYPES = {
    RegulatoryEventType.NEW_CLAIM_APPROVED,
    RegulatoryEventType.NOVEL_FOOD_NEW_ENTRY,
}

# Event types that represent enforcement actions
_ENFORCEMENT_TYPES = {
    RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION,
}


class ClaimsAlertFormatter:
    """Formats regulatory events as Discord embeds.

    Attributes:
        _config: Claims alert configuration
    """

    def __init__(self, config: ClaimsAlertConfig) -> None:
        """Initialize formatter with config.

        Args:
            config: Claims alert configuration
        """
        self._config = config

    def format_claim_alert(self, event: RegulatoryEvent) -> DiscordEmbed:
        """Format a single regulatory event as a Discord embed.

        Args:
            event: Regulatory event to format

        Returns:
            DiscordEmbed ready to send
        """
        color = self._determine_embed_color(event)
        emoji = self._config.severity_emoji_map.get(event.severity, "white_circle")
        title = self._build_title(event, emoji)
        description = event.data.get("claim_text", event.substance or "Regulatory update")

        fields: list[EmbedField] = []

        # Applicable products
        applicable = self._extract_applicable_products(event)
        if applicable:
            fields.append(EmbedField(name="Applicable Products", value=applicable, inline=True))

        # Usage conditions
        conditions = self._format_usage_conditions(event)
        if conditions:
            fields.append(EmbedField(name="Usage Conditions", value=conditions, inline=True))

        # Effective date
        effective_date = event.data.get("approval_date", "")
        if effective_date:
            fields.append(EmbedField(name="Effective Date", value=effective_date, inline=True))

        # Severity
        fields.append(EmbedField(name="Severity", value=f":{emoji}: {event.severity.upper()}", inline=True))

        # Source
        source = self._determine_source(event)
        fields.append(EmbedField(name="Source", value=source, inline=True))

        return DiscordEmbed(
            title=title,
            description=description,
            color=color,
            fields=fields,
            timestamp=event.timestamp.isoformat(),
        )

    def format_batch_alert(self, events: list[RegulatoryEvent]) -> DiscordEmbed:
        """Format multiple regulatory events as a batched summary embed.

        Args:
            events: List of regulatory events to batch

        Returns:
            DiscordEmbed with summary of all events
        """
        count = len(events)

        # Count by type
        new_claims = sum(1 for e in events if e.event_type in _NEW_CLAIM_TYPES)
        enforcement = sum(1 for e in events if e.event_type in _ENFORCEMENT_TYPES)
        status_changes = count - new_claims - enforcement

        description_parts: list[str] = []
        if new_claims > 0:
            description_parts.append(f"**{new_claims}** new claims")
        if status_changes > 0:
            description_parts.append(f"**{status_changes}** status changes")
        if enforcement > 0:
            description_parts.append(f"**{enforcement}** enforcement actions")
        description = " | ".join(description_parts) if description_parts else "Multiple regulatory updates"

        # One field per event, max 25 (Discord limit)
        fields: list[EmbedField] = []
        for event in events[:25]:
            emoji = self._config.severity_emoji_map.get(event.severity, "white_circle")
            event_title = self._short_title(event)
            claim_text = event.data.get("claim_text", event.substance or "Update")[:100]
            fields.append(EmbedField(
                name=f":{emoji}: {event_title}",
                value=claim_text,
                inline=True,
            ))

        footer = f"Review full details at {self._config.dashboard_url}" if self._config.dashboard_url else "DAWO Regulatory Alerts"

        return DiscordEmbed(
            title=f"{count} Regulatory Updates Detected",
            description=description,
            color=EmbedColor.INFO.value,
            fields=fields,
            footer_text=footer,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def format_enforcement_alert(self, event: RegulatoryEvent) -> DiscordEmbed:
        """Format a high-urgency enforcement action as a Discord embed.

        Args:
            event: Enforcement event (typically MATTILSYNET_ENFORCEMENT_ACTION)

        Returns:
            DiscordEmbed with ERROR color and urgency formatting
        """
        title_text = event.data.get("title", "Enforcement Action Detected")

        fields: list[EmbedField] = []

        # Source URL
        url = event.data.get("url", "")
        if url:
            fields.append(EmbedField(name="Source URL", value=url, inline=False))

        # Category
        category = event.data.get("category", "enforcement")
        fields.append(EmbedField(name="Category", value=category.title(), inline=True))

        # Keywords matched
        keywords = event.data.get("keywords_matched", [])
        if keywords:
            fields.append(EmbedField(name="Keywords Matched", value=", ".join(keywords), inline=True))

        # Potential impact (shown as field, not duplicated in description)
        summary = event.data.get("content_summary", "")
        if summary:
            fields.append(EmbedField(name="Potential Impact", value=summary[:500], inline=False))

        return DiscordEmbed(
            title=f"ENFORCEMENT ACTION: {title_text[:200]}",
            description=title_text[:500],
            color=EmbedColor.ERROR.value,
            fields=fields,
            timestamp=event.timestamp.isoformat(),
        )

    def _determine_embed_color(self, event: RegulatoryEvent) -> int:
        """Determine embed color based on event type and severity.

        Args:
            event: Regulatory event

        Returns:
            Integer color value for Discord embed
        """
        if event.event_type in _ENFORCEMENT_TYPES:
            return EmbedColor.ERROR.value
        if event.event_type in _NEW_CLAIM_TYPES:
            return EmbedColor.SUCCESS.value
        if event.severity in ("critical", "high"):
            return EmbedColor.WARNING.value
        return EmbedColor.INFO.value

    def _extract_applicable_products(self, event: RegulatoryEvent) -> str:
        """Match event content against DAWO product keywords.

        Args:
            event: Regulatory event to check

        Returns:
            Comma-separated matched product keywords, or empty string
        """
        parts = [event.substance]
        for v in event.data.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(item) for item in v)
        searchable = " ".join(parts).lower()

        matched = [
            kw for kw in self._config.dawo_product_keywords
            if kw.lower() in searchable
        ]
        return ", ".join(matched) if matched else ""

    def _format_usage_conditions(self, event: RegulatoryEvent) -> str:
        """Extract usage conditions from event data.

        Args:
            event: Regulatory event

        Returns:
            Usage conditions string, or empty string
        """
        conditions = event.data.get("conditions_of_use", "")
        if conditions:
            return str(conditions)

        # Check for product categories
        categories = event.data.get("product_categories", [])
        if categories:
            return f"Categories: {', '.join(categories)}"

        return ""

    def _build_title(self, event: RegulatoryEvent, emoji: str) -> str:
        """Build embed title based on event type.

        Args:
            event: Regulatory event
            emoji: Discord emoji name for severity

        Returns:
            Title string
        """
        if event.event_type in _NEW_CLAIM_TYPES:
            return f":{emoji}: New Approved Claim"
        if event.event_type in _ENFORCEMENT_TYPES:
            return f":{emoji}: Enforcement Action"
        return f":{emoji}: Regulatory Update"

    def _short_title(self, event: RegulatoryEvent) -> str:
        """Short title for batch embed fields.

        Args:
            event: Regulatory event

        Returns:
            Short descriptive title
        """
        if event.event_type in _NEW_CLAIM_TYPES:
            return "New Claim"
        if event.event_type in _ENFORCEMENT_TYPES:
            return "Enforcement"
        return "Status Change"

    def _determine_source(self, event: RegulatoryEvent) -> str:
        """Determine source label based on event type.

        Args:
            event: Regulatory event

        Returns:
            Source label string
        """
        source_map = {
            RegulatoryEventType.CLAIM_STATUS_CHANGED: "EU Health Claims Register",
            RegulatoryEventType.NEW_CLAIM_APPROVED: "EU Health Claims Register",
            RegulatoryEventType.CLAIM_REMOVED: "EU Health Claims Register",
            RegulatoryEventType.REGISTER_UPDATED: "EU Health Claims Register",
            RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED: "EU Novel Food Catalogue",
            RegulatoryEventType.NOVEL_FOOD_NEW_ENTRY: "EU Novel Food Catalogue",
            RegulatoryEventType.NOVEL_FOOD_ENTRY_REMOVED: "EU Novel Food Catalogue",
            RegulatoryEventType.NOVEL_FOOD_CATALOGUE_UPDATED: "EU Novel Food Catalogue",
            RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE: "Mattilsynet",
            RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION: "Mattilsynet",
            RegulatoryEventType.MATTILSYNET_PAGE_CHANGED: "Mattilsynet",
        }
        return source_map.get(event.event_type, "Unknown")


__all__ = [
    "ClaimsAlertFormatter",
]
