"""Lead Transformer for B2B Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Transforms harvested leads into the format expected by the Lead model,
ready for database insertion.
"""

import logging
from typing import Optional

from teams.dawo.leads.scanner.config import LeadScannerConfig
from teams.dawo.leads.scanner.schemas import (
    HarvestedLead,
    HarvestedContact,
    TransformedLead,
)


logger = logging.getLogger(__name__)


# Transformer constants
MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 100


class LeadTransformer:
    """Transforms harvested leads to Lead model format.

    Maps HarvestedLead data to TransformedLead schema:
    - Selects best contact from harvested contacts
    - Normalizes and validates data
    - Prepares enrichment_data JSONB payload

    Accepts all dependencies via injection.
    """

    def __init__(self, config: LeadScannerConfig) -> None:
        """Initialize the transformer.

        Args:
            config: Scanner configuration
        """
        self._config = config

    def transform(
        self,
        harvested_leads: list[HarvestedLead],
    ) -> list[TransformedLead]:
        """Transform harvested leads to database format.

        Args:
            harvested_leads: List of harvested leads

        Returns:
            List of transformed leads ready for database

        Note:
            Invalid leads (missing required fields) are filtered out.
        """
        logger.info(f"Transforming {len(harvested_leads)} leads")

        transformed: list[TransformedLead] = []

        for harvested in harvested_leads:
            try:
                lead = self._transform_lead(harvested)
                if lead and self._validate_lead(lead):
                    transformed.append(lead)
                    logger.debug(f"Transformed lead: {lead.email}")
            except Exception as e:
                logger.warning(
                    f"Failed to transform lead {harvested.domain}: {e}"
                )
                continue

        logger.info(
            f"Transformed {len(transformed)}/{len(harvested_leads)} leads"
        )
        return transformed

    def _transform_lead(
        self,
        harvested: HarvestedLead,
    ) -> Optional[TransformedLead]:
        """Transform a single harvested lead.

        Args:
            harvested: Harvested lead with contacts

        Returns:
            TransformedLead or None if no valid contact
        """
        # Get best contact (primary_contact is already sorted by priority)
        contact = harvested.primary_contact
        if not contact:
            logger.debug(f"No valid contact for {harvested.domain}")
            return None

        # Extract and normalize names
        first_name = self._normalize_name(contact.first_name)
        last_name = self._normalize_name(contact.last_name)

        # Handle missing names
        if not first_name and not last_name:
            # Try to extract from email
            email_name = contact.email.split("@")[0]
            parts = email_name.replace(".", " ").replace("_", " ").split()
            if len(parts) >= 2:
                first_name = parts[0].title()
                last_name = parts[-1].title()
            elif len(parts) == 1:
                first_name = parts[0].title()
                last_name = "Unknown"
            else:
                first_name = "Unknown"
                last_name = "Contact"

        # Build enrichment data for JSONB storage
        enrichment_data = self._build_enrichment_data(harvested, contact)

        return TransformedLead(
            email=contact.email.lower().strip(),
            first_name=first_name,
            last_name=last_name,
            company=self._normalize_company_name(harvested.company_name),
            job_title=contact.position,
            website_url=f"https://{harvested.domain}",
            linkedin_url=contact.linkedin or harvested.linkedin,
            phone=contact.phone or harvested.phone,
            country=harvested.country,
            industry=harvested.industry,
            company_size=harvested.headcount,
            source="cold_research",
            status="new",
            score=0.0,  # Initial score, enrichment will add more
            enrichment_data=enrichment_data,
        )

    def _normalize_name(self, name: Optional[str]) -> str:
        """Normalize a person's name.

        Args:
            name: Raw name string

        Returns:
            Normalized name or empty string
        """
        if not name:
            return ""

        # Strip whitespace, title case
        normalized = name.strip().title()

        # Truncate if too long
        if len(normalized) > MAX_NAME_LENGTH:
            normalized = normalized[:MAX_NAME_LENGTH]

        return normalized

    def _normalize_company_name(self, company: str) -> str:
        """Normalize a company name.

        Args:
            company: Raw company name

        Returns:
            Normalized company name
        """
        if not company:
            return "Unknown Company"

        # Strip whitespace
        normalized = company.strip()

        # Remove multiple spaces
        while "  " in normalized:
            normalized = normalized.replace("  ", " ")

        return normalized

    def _build_enrichment_data(
        self,
        harvested: HarvestedLead,
        primary_contact: HarvestedContact,
    ) -> dict:
        """Build enrichment_data JSONB payload.

        Stores additional data from Hunter.io for future reference.

        Args:
            harvested: Full harvested lead data
            primary_contact: Selected primary contact

        Returns:
            Dict for JSONB storage
        """
        return {
            "source": "hunter.io",
            "discovered_at": harvested.discovered_at.isoformat(),
            "enriched_at": harvested.enriched_at.isoformat(),
            "confidence": primary_contact.confidence,
            "contact_count": len(harvested.contacts),
            "social_profiles": {
                "linkedin": harvested.linkedin,
                "twitter": harvested.twitter,
                "facebook": harvested.facebook,
            },
            "company_info": {
                "organization": harvested.organization,
                "city": harvested.city,
                "state": harvested.state,
                "headcount": harvested.headcount,
            },
            # Store other contacts for reference (not primary)
            "other_contacts": [
                {
                    "email": c.email,
                    "name": f"{c.first_name or ''} {c.last_name or ''}".strip(),
                    "position": c.position,
                    "confidence": c.confidence,
                }
                for c in harvested.contacts[1:5]  # Max 4 additional contacts
            ],
        }

    def _validate_lead(self, lead: TransformedLead) -> bool:
        """Validate a transformed lead has required fields.

        Args:
            lead: Lead to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required fields from config
        for field in self._config.required_fields:
            value = getattr(lead, field, None)
            if not value:
                logger.debug(f"Lead missing required field: {field}")
                return False

        # Validate email format
        if "@" not in lead.email:
            logger.debug(f"Invalid email format: {lead.email}")
            return False

        # Validate names have content
        if len(lead.first_name) < MIN_NAME_LENGTH:
            logger.debug(f"First name too short: {lead.first_name}")
            return False

        return True
