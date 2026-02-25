"""Personalization Engine for Outreach Drafts.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides personalization extraction and content generation:
- PersonalizationEngine: Main engine class
- Hook extraction from enrichment data
- Product recommendation based on lead profile
- Value proposition generation
- CTA selection based on lead type
"""

import logging
from typing import Any

from teams.dawo.leads.outreach.schemas import LeadType
from teams.dawo.leads.outreach.config import OutreachConfig


logger = logging.getLogger(__name__)


# DAWO product catalog for recommendations
DAWO_PRODUCTS = {
    "lions_mane": {
        "name": "Lion's Mane Extract",
        "norwegian": "Lion's Mane Ekstrakt",
        "benefits": ["fokus", "kognitiv funksjon", "mental klarhet"],
        "categories": ["kosttilskudd", "nootropics", "kognitiv helse"],
    },
    "chaga": {
        "name": "Chaga Powder",
        "norwegian": "Chaga Pulver",
        "benefits": ["immunforsvar", "antioksidanter", "vitalitet"],
        "categories": ["kosttilskudd", "superfoods", "immunstøtte"],
    },
    "reishi": {
        "name": "Reishi Extract",
        "norwegian": "Reishi Ekstrakt",
        "benefits": ["avslapning", "søvn", "stressmestring"],
        "categories": ["kosttilskudd", "adaptogener", "velvære"],
    },
    "cordyceps": {
        "name": "Cordyceps Extract",
        "norwegian": "Cordyceps Ekstrakt",
        "benefits": ["energi", "utholdenhet", "treningsprestasjon"],
        "categories": ["kosttilskudd", "sports", "energi", "trening"],
    },
    "turkey_tail": {
        "name": "Turkey Tail Extract",
        "norwegian": "Turkey Tail Ekstrakt",
        "benefits": ["immunforsvar", "tarmhelse", "fordøyelse"],
        "categories": ["kosttilskudd", "immunstøtte", "tarmhelse"],
    },
}


# Value propositions by lead type (Norwegian)
VALUE_PROPOSITIONS = {
    LeadType.HEALTH_STORE: [
        "Premium norsk kvalitet med full sporbarhet fra jord til produkt",
        "Høykvalitets funksjonelle sopp-ekstrakter som kundene dine vil elske",
        "Bærekraftig produksjon med fokus på renhet og dokumentert kvalitet",
    ],
    LeadType.GYM_FITNESS: [
        "Naturlig støtte for prestasjon og restitusjon som deres medlemmer vil sette pris på",
        "Funksjonelle sopp for aktive mennesker - fokus, energi og utholdenhet",
        "Premium kosttilskudd som passer perfekt i deres treningssenters sortiment",
    ],
    LeadType.ONLINE_RETAILER: [
        "Premium produkter med sterk etterspørsel i det norske markedet",
        "Full produktinformasjon og markedsføringsmateriell for deres nettbutikk",
        "Attraktive marginer og pålitelig leveranse for netthandel",
    ],
    LeadType.WELLNESS_CENTER: [
        "Holistiske helseprodukter som utfyller deres velvære-tjenester",
        "Premium sopp-ekstrakter for klienter som verdsetter naturlig helse",
        "Produkter som forsterker deres helhetlige helsetilbud",
    ],
    LeadType.SPECIALTY_GROCER: [
        "Unike premium-produkter som skiller deres butikk fra konkurrentene",
        "Funksjonelle sopp av høyeste kvalitet for kresne kunder",
        "Spesialprodukter med historie og dokumentert kvalitet",
    ],
    LeadType.GENERIC: [
        "Premium norsk kvalitet med full sporbarhet",
        "Funksjonelle sopp-ekstrakter av høyeste kvalitet",
        "Bærekraftig produksjon med fokus på renhet",
    ],
}


# CTA options by lead type (Norwegian)
CTA_OPTIONS = {
    LeadType.HEALTH_STORE: "Vi sender gjerne et prøveprodukt så dere kan oppleve kvaliteten selv.",
    LeadType.GYM_FITNESS: "Kan vi ta en kort samtale for å diskutere hvordan DAWO kan styrke sortimentet deres?",
    LeadType.ONLINE_RETAILER: "Jeg legger ved vår produktkatalog - hvilke produkter ville være mest relevante for dere?",
    LeadType.WELLNESS_CENTER: "Vi sender gjerne prøveprodukter så dere kan vurdere kvaliteten for deres klienter.",
    LeadType.SPECIALTY_GROCER: "Vi sender gjerne et utvalg prøveprodukter for deres vurdering.",
    LeadType.GENERIC: "Kan vi diskutere hvordan DAWO-produkter kan passe for deres virksomhet?",
}


# Maximum limits
MAX_HOOKS = 5
MAX_PRODUCTS = 3


class PersonalizationEngine:
    """Engine for extracting and generating personalization content.

    Extracts personalization hooks from enrichment data and generates
    tailored content for outreach emails.

    Accepts config via dependency injection.
    """

    def __init__(self, config: OutreachConfig) -> None:
        """Initialize the personalization engine.

        Args:
            config: Outreach configuration (injected)
        """
        self._config = config

    def extract_hooks(self, enrichment_data: dict[str, Any]) -> list[str]:
        """Extract personalization hooks from enrichment data.

        Extracts hooks from the personalization_hooks field and formats
        them as natural language references.

        Args:
            enrichment_data: Lead's enrichment_data from database

        Returns:
            List of formatted personalization hook strings
        """
        hooks = enrichment_data.get("personalization_hooks", [])

        if not hooks:
            return []

        formatted_hooks = []
        for hook in hooks[:MAX_HOOKS]:  # Limit number of hooks
            if isinstance(hook, dict):
                detail = hook.get("detail", "")
                if detail:
                    formatted_hooks.append(detail)
            elif isinstance(hook, str):
                formatted_hooks.append(hook)

        return formatted_hooks

    def select_products(self, enrichment_data: dict[str, Any]) -> list[str]:
        """Select DAWO products based on lead's profile.

        Matches products to lead's product categories and customer base.

        Args:
            enrichment_data: Lead's enrichment_data from database

        Returns:
            List of recommended product names (Norwegian)
        """
        business_insights = enrichment_data.get("business_insights", {})
        lead_categories = business_insights.get("product_categories", [])

        if not lead_categories:
            # Default recommendations for unknown leads
            return ["Lion's Mane Ekstrakt", "Chaga Pulver"]

        # Match products to lead's categories
        matched_products = []
        for product_id, product_info in DAWO_PRODUCTS.items():
            product_categories = product_info.get("categories", [])

            # Check for category overlap
            for lead_cat in lead_categories:
                lead_cat_lower = lead_cat.lower()
                for prod_cat in product_categories:
                    if lead_cat_lower in prod_cat.lower() or prod_cat.lower() in lead_cat_lower:
                        matched_products.append(product_info["norwegian"])
                        break
                else:
                    continue
                break

        # Remove duplicates while preserving order
        seen = set()
        unique_products = []
        for product in matched_products:
            if product not in seen:
                seen.add(product)
                unique_products.append(product)

        # Return matched products or defaults
        if unique_products:
            return unique_products[:MAX_PRODUCTS]

        # Fallback to popular products
        return ["Lion's Mane Ekstrakt", "Cordyceps Ekstrakt"]

    def generate_value_prop(
        self,
        enrichment_data: dict[str, Any],
        lead_type: LeadType,
    ) -> str:
        """Generate a value proposition for the lead.

        Creates a specific value proposition based on the lead's
        market and lead type.

        Args:
            enrichment_data: Lead's enrichment_data from database
            lead_type: Classified lead type

        Returns:
            Norwegian value proposition string
        """
        propositions = VALUE_PROPOSITIONS.get(lead_type, VALUE_PROPOSITIONS[LeadType.GENERIC])

        # Select first proposition for now
        # Could be enhanced to select based on business insights
        business_insights = enrichment_data.get("business_insights", {})
        wellness_positioning = business_insights.get("wellness_positioning", "")

        # If strong wellness positioning, emphasize quality
        if wellness_positioning == "strong":
            return propositions[0]

        return propositions[0]

    def select_cta(self, lead_type: LeadType) -> str:
        """Select appropriate CTA based on lead type.

        Args:
            lead_type: Classified lead type

        Returns:
            Norwegian CTA string
        """
        return CTA_OPTIONS.get(lead_type, CTA_OPTIONS[LeadType.GENERIC])

    def format_opening(self, hooks: list[str]) -> str:
        """Format personalization hooks as an opening statement.

        Combines hooks into a natural language opening for the email.

        Args:
            hooks: List of personalization hook strings

        Returns:
            Formatted opening paragraph
        """
        if not hooks:
            return "Jeg kontakter dere angående et mulig samarbeid."

        if len(hooks) == 1:
            return f"Jeg la merke til at {hooks[0].lower()}. Det fikk meg til å tenke på et mulig samarbeid."

        # Combine multiple hooks
        first_hook = hooks[0]
        return f"Jeg la merke til at {first_hook.lower()}, og tenkte dette kunne være interessant for dere."
