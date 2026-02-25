"""Outreach Templates for B2B Email Generation.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides template management for outreach emails:
- OutreachTemplateRegistry: Template storage and retrieval
- Norwegian email templates for each lead type
- Template selection logging for performance tracking
"""

import logging
from typing import Optional
from uuid import UUID

from teams.dawo.leads.outreach.schemas import LeadType, OutreachTemplate


logger = logging.getLogger(__name__)


# Template definitions - Norwegian with warm, professional tone
# Following brand voice: warm, educational, Nordic simplicity, personal touch

HEALTH_STORE_TEMPLATE = OutreachTemplate(
    template_id="hs-intro-v1",
    lead_type=LeadType.HEALTH_STORE,
    subject_template="Samarbeid med DAWO - Funksjonelle sopp for {{business_focus}}",
    body_template="""Hei {{contact_name}},

{{personalization_opening}}

DAWO tilbyr premium funksjonelle sopp-ekstrakter som passer perfekt for butikker med fokus på naturlige helseprodukter.

{{product_recommendation}}

{{value_proposition}}

{{cta}}

Med vennlig hilsen,
DAWO Team""",
    cta_type="sample_offer",
)


GYM_FITNESS_TEMPLATE = OutreachTemplate(
    template_id="gf-intro-v1",
    lead_type=LeadType.GYM_FITNESS,
    subject_template="DAWO - Premium sopp-ekstrakter for deres treningssenter",
    body_template="""Hei {{contact_name}},

{{personalization_opening}}

Funksjonelle sopp som Lion's Mane og Cordyceps er populære blant aktive mennesker som søker naturlig støtte for fokus og utholdenhet.

{{product_recommendation}}

{{value_proposition}}

{{cta}}

Med vennlig hilsen,
DAWO Team""",
    cta_type="meeting_request",
)


ONLINE_RETAILER_TEMPLATE = OutreachTemplate(
    template_id="or-intro-v1",
    lead_type=LeadType.ONLINE_RETAILER,
    subject_template="DAWO produkter for deres nettbutikk",
    body_template="""Hei {{contact_name}},

{{personalization_opening}}

DAWO leverer funksjonelle sopp-ekstrakter med full sporbarhet - perfekt for nettbutikker som verdsetter kvalitet og transparens.

{{product_recommendation}}

{{value_proposition}}

{{cta}}

Med vennlig hilsen,
DAWO Team""",
    cta_type="catalog_request",
)


WELLNESS_CENTER_TEMPLATE = OutreachTemplate(
    template_id="wc-intro-v1",
    lead_type=LeadType.WELLNESS_CENTER,
    subject_template="Samarbeid med DAWO - Funksjonelle sopp for velvære",
    body_template="""Hei {{contact_name}},

{{personalization_opening}}

Våre funksjonelle sopp-ekstrakter passer utmerket for velværesentre som tilbyr holistiske helse- og velværetjenester.

{{product_recommendation}}

{{value_proposition}}

{{cta}}

Med vennlig hilsen,
DAWO Team""",
    cta_type="sample_offer",
)


SPECIALTY_GROCER_TEMPLATE = OutreachTemplate(
    template_id="sg-intro-v1",
    lead_type=LeadType.SPECIALTY_GROCER,
    subject_template="DAWO - Premium sopp for spesialbutikker",
    body_template="""Hei {{contact_name}},

{{personalization_opening}}

DAWO tilbyr premium funksjonelle sopp-produkter som passer perfekt for spesialbutikker med fokus på kvalitet og unike produkter.

{{product_recommendation}}

{{value_proposition}}

{{cta}}

Med vennlig hilsen,
DAWO Team""",
    cta_type="sample_offer",
)


GENERIC_TEMPLATE = OutreachTemplate(
    template_id="gen-intro-v1",
    lead_type=LeadType.GENERIC,
    subject_template="Mulighet for samarbeid - DAWO funksjonelle sopp",
    body_template="""Hei {{contact_name}},

{{personalization_opening}}

DAWO er en norsk leverandør av premium funksjonelle sopp-ekstrakter. Vi tror våre produkter kan være relevante for deres virksomhet.

{{product_recommendation}}

{{value_proposition}}

{{cta}}

Med vennlig hilsen,
DAWO Team""",
    cta_type="catalog_request",
)


class OutreachTemplateRegistry:
    """Registry for outreach email templates.

    Provides template storage, retrieval by lead type or ID,
    and selection logging for performance tracking.

    Templates are designed for Norwegian B2B outreach with:
    - Warm, professional tone
    - Personalization placeholders
    - Lead type-specific CTAs
    """

    def __init__(self) -> None:
        """Initialize the template registry with all templates."""
        self._templates: dict[LeadType, OutreachTemplate] = {
            LeadType.HEALTH_STORE: HEALTH_STORE_TEMPLATE,
            LeadType.GYM_FITNESS: GYM_FITNESS_TEMPLATE,
            LeadType.ONLINE_RETAILER: ONLINE_RETAILER_TEMPLATE,
            LeadType.WELLNESS_CENTER: WELLNESS_CENTER_TEMPLATE,
            LeadType.SPECIALTY_GROCER: SPECIALTY_GROCER_TEMPLATE,
            LeadType.GENERIC: GENERIC_TEMPLATE,
        }

        # Index by template ID for quick lookup
        self._templates_by_id: dict[str, OutreachTemplate] = {
            template.template_id: template
            for template in self._templates.values()
        }

    def get_template(self, lead_type: LeadType) -> OutreachTemplate:
        """Get template for a lead type.

        Args:
            lead_type: Type of lead to get template for

        Returns:
            OutreachTemplate for the specified lead type
        """
        return self._templates[lead_type]

    def get_template_by_id(self, template_id: str) -> Optional[OutreachTemplate]:
        """Get template by its ID.

        Args:
            template_id: Template identifier

        Returns:
            OutreachTemplate or None if not found
        """
        return self._templates_by_id.get(template_id)

    def list_all(self) -> list[OutreachTemplate]:
        """List all registered templates.

        Returns:
            List of all OutreachTemplate instances
        """
        return list(self._templates.values())

    def log_template_selection(self, template_id: str, lead_id: UUID) -> None:
        """Log template selection for performance tracking.

        Args:
            template_id: Selected template ID
            lead_id: UUID of the lead
        """
        logger.info(
            "Template selection logged",
            extra={
                "template_selection": {
                    "template_id": template_id,
                    "lead_id": str(lead_id),
                }
            }
        )
