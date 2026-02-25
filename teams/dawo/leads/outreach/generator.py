"""Outreach Draft Generator for B2B Emails.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides LLM-powered draft generation:
- OutreachDraftGenerator: Main generator class
- Template filling with personalization
- Word count validation
- Suggested send time calculation
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Any, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from teams.dawo.leads.outreach.schemas import LeadType, OutreachDraft, OutreachTemplate
from teams.dawo.leads.outreach.config import OutreachConfig
from teams.dawo.leads.outreach.personalization import PersonalizationEngine
from teams.dawo.leads.outreach.templates import OutreachTemplateRegistry


logger = logging.getLogger(__name__)


class LLMClientProtocol(Protocol):
    """Protocol for LLM client dependency injection."""

    async def generate(self, prompt: str) -> str:
        """Generate text from prompt."""
        ...


# Draft generation prompt template
DRAFT_GENERATION_PROMPT = """Generate a personalized B2B outreach email in Norwegian for DAWO mushroom supplements.

Template:
{template}

Lead information:
- Company: {company}
- Contact name: {contact_name}
- Business focus: {focus_areas}
- Personalization hooks: {hooks}
- Recommended products: {products}
- Value proposition: {value_prop}
- CTA: {cta}

Requirements:
1. Write in warm, professional Norwegian
2. Length: 150-250 words
3. Reference their specific business naturally
4. Avoid generic sales language
5. Educational tone, not pushy
6. End with clear but soft CTA
7. Keep the greeting "Hei {contact_name}," and sign-off "Med vennlig hilsen, DAWO Team"

Return ONLY the complete email body, nothing else.
"""


class OutreachDraftGenerator:
    """LLM-powered draft generator for outreach emails.

    Generates personalized email drafts using templates and LLM.
    Uses tier="generate" (Sonnet) for quality content generation.

    Accepts all dependencies via injection.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        personalization_engine: PersonalizationEngine,
        template_registry: OutreachTemplateRegistry,
        config: OutreachConfig,
    ) -> None:
        """Initialize the draft generator.

        Args:
            llm_client: LLM client for draft generation (injected)
            personalization_engine: Personalization engine (injected)
            template_registry: Template registry (injected)
            config: Outreach configuration (injected)
        """
        self._llm_client = llm_client
        self._personalization = personalization_engine
        self._templates = template_registry
        self._config = config

    async def generate(
        self,
        lead_id: UUID,
        contact_name: str,
        company: str,
        enrichment_data: dict[str, Any],
        lead_type: LeadType,
    ) -> OutreachDraft:
        """Generate a personalized outreach draft.

        Args:
            lead_id: UUID of the lead
            contact_name: Contact's first name
            company: Company name
            enrichment_data: Lead's enrichment data
            lead_type: Classified lead type

        Returns:
            OutreachDraft with generated content
        """
        # Get template for lead type
        template = self._templates.get_template(lead_type)

        # Extract personalization data
        hooks = self._personalization.extract_hooks(enrichment_data)
        products = self._personalization.select_products(enrichment_data)
        value_prop = self._personalization.generate_value_prop(enrichment_data, lead_type)
        cta = self._personalization.select_cta(lead_type)
        opening = self._personalization.format_opening(hooks)

        # Get business focus areas
        business_insights = enrichment_data.get("business_insights", {})
        focus_areas = business_insights.get("focus_areas", [])

        # Generate draft using LLM
        prompt = DRAFT_GENERATION_PROMPT.format(
            template=template.body_template,
            company=company,
            contact_name=contact_name,
            focus_areas=", ".join(focus_areas) if focus_areas else "naturlig helse",
            hooks="; ".join(hooks) if hooks else "Ingen spesifikke hooks",
            products=", ".join(products),
            value_prop=value_prop,
            cta=cta,
        )

        try:
            body = await self._llm_client.generate(prompt)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback to template-based generation
            body = self._generate_fallback(
                template, contact_name, opening, products, value_prop, cta
            )

        # Calculate metrics
        word_count = len(body.split())
        personalization_score = self.count_personalization_tokens(body, hooks, products)
        suggested_send_time = self._calculate_send_time()

        # Create subject line
        subject = template.subject_template.replace(
            "{{business_focus}}",
            focus_areas[0] if focus_areas else "naturlig helse"
        )

        return OutreachDraft(
            lead_id=lead_id,
            template_id=template.template_id,
            template_type=lead_type,
            subject=subject,
            body=body,
            word_count=word_count,
            personalization_hooks=hooks,
            personalization_score=personalization_score,
            suggested_send_time=suggested_send_time,
        )

    def _generate_fallback(
        self,
        template: OutreachTemplate,
        contact_name: str,
        opening: str,
        products: list[str],
        value_prop: str,
        cta: str,
    ) -> str:
        """Generate fallback draft without LLM.

        Args:
            template: Email template
            contact_name: Contact's first name
            opening: Personalized opening
            products: Recommended products
            value_prop: Value proposition
            cta: Call to action

        Returns:
            Generated email body
        """
        body = template.body_template
        body = body.replace("{{contact_name}}", contact_name)
        body = body.replace("{{personalization_opening}}", opening)
        body = body.replace("{{product_recommendation}}", f"Vi anbefaler spesielt {', '.join(products)}.")
        body = body.replace("{{value_proposition}}", value_prop)
        body = body.replace("{{cta}}", cta)

        return body

    def validate_word_count(self, text: str) -> bool:
        """Validate that text is within word count limits.

        Args:
            text: Text to validate

        Returns:
            True if word count is between 150-250
        """
        word_count = len(text.split())
        return self._config.min_word_count <= word_count <= self._config.max_word_count

    def count_personalization_tokens(
        self,
        draft: str,
        hooks: list[str],
        products: list[str],
    ) -> int:
        """Count personalization tokens in draft.

        Args:
            draft: Draft text to analyze
            hooks: List of personalization hooks
            products: List of product recommendations

        Returns:
            Number of personalization tokens found
        """
        count = 0
        draft_lower = draft.lower()

        # Count hooks mentioned
        for hook in hooks:
            if hook.lower() in draft_lower:
                count += 1

        # Count products mentioned
        for product in products:
            if product.lower() in draft_lower:
                count += 1

        return count

    def _calculate_send_time(self) -> datetime:
        """Calculate optimal send time for B2B outreach.

        Business hours: Tuesday-Thursday, 10 AM Norwegian time.
        Avoids Monday (busy) and Friday (winding down).

        Returns:
            Suggested send datetime
        """
        oslo_tz = ZoneInfo("Europe/Oslo")
        now = datetime.now(UTC).astimezone(oslo_tz)

        # Days until good day (Tuesday=1, Wednesday=2, Thursday=3)
        days_until_good_day = {
            0: 1,  # Mon -> Tue
            1: 0,  # Tue -> Tue (same day if before 11 AM)
            2: 0,  # Wed -> Wed
            3: 0,  # Thu -> Thu
            4: 4,  # Fri -> Tue
            5: 3,  # Sat -> Tue
            6: 2,  # Sun -> Tue
        }

        days_to_add = days_until_good_day[now.weekday()]
        target_date = now + timedelta(days=days_to_add)

        # Set time to 10:00 AM Oslo time
        target_time = target_date.replace(hour=10, minute=0, second=0, microsecond=0)

        # If today is a good day but past 11 AM, move to next good day
        if target_time <= now:
            target_time += timedelta(days=1)
            while target_time.weekday() not in (1, 2, 3):  # Tue, Wed, Thu
                target_time += timedelta(days=1)

        return target_time
