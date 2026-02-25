"""Lead Harvester for B2B Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Enriches raw leads with detailed company and contact information
from Hunter.io API.
"""

import logging
from datetime import datetime, UTC
from typing import Optional

from teams.dawo.leads.scanner.config import LeadScannerConfig
from teams.dawo.leads.scanner.schemas import (
    RawLead,
    HarvestedLead,
    HarvestedContact,
)
from teams.dawo.leads.scanner.tools import HunterClient, HunterAPIError


logger = logging.getLogger(__name__)


class LeadHarvester:
    """Enriches raw leads with Hunter.io data.

    For each raw lead, fetches:
    - Full company information
    - Contact emails with names and positions
    - Social profiles
    - Company size and industry

    Handles missing data gracefully - partial leads are still valuable.

    Accepts all dependencies via injection.
    """

    def __init__(
        self,
        config: LeadScannerConfig,
        hunter_client: HunterClient,
    ) -> None:
        """Initialize the harvester.

        Args:
            config: Scanner configuration
            hunter_client: Hunter.io API client
        """
        self._config = config
        self._hunter = hunter_client

    async def harvest(
        self,
        raw_leads: list[RawLead],
    ) -> list[HarvestedLead]:
        """Enrich raw leads with Hunter.io data.

        Args:
            raw_leads: List of raw leads from scanner

        Returns:
            List of harvested leads with enriched data

        Note:
            Continues on individual lead failures (graceful degradation).
            Failed leads are logged but don't stop processing.
        """
        logger.info(f"Harvesting {len(raw_leads)} leads")

        harvested: list[HarvestedLead] = []

        for raw_lead in raw_leads:
            try:
                enriched = await self._harvest_lead(raw_lead)
                if enriched:
                    harvested.append(enriched)
                    logger.debug(
                        f"Harvested {raw_lead.domain}: "
                        f"{len(enriched.contacts)} contacts"
                    )
            except HunterAPIError as e:
                logger.warning(f"Failed to harvest {raw_lead.domain}: {e}")
                # Continue to next lead (graceful degradation)
                continue
            except Exception as e:
                logger.error(f"Unexpected error harvesting {raw_lead.domain}: {e}")
                continue

        logger.info(f"Harvested {len(harvested)}/{len(raw_leads)} leads")
        return harvested

    async def _harvest_lead(self, raw_lead: RawLead) -> Optional[HarvestedLead]:
        """Harvest a single lead.

        Args:
            raw_lead: Raw lead to enrich

        Returns:
            HarvestedLead with enriched data, or None if no useful data

        Raises:
            HunterAPIError: On API failure
        """
        # Get domain search results for full company info
        response = await self._hunter.domain_search(
            domain=raw_lead.domain,
            limit=10,  # Get up to 10 contacts
        )

        # Extract company information
        company_name = (
            response.get("organization")
            or response.get("company")
            or raw_lead.company_name
        )

        if not company_name:
            logger.debug(f"Skipping {raw_lead.domain}: no company name found")
            return None

        # Extract contacts
        contacts = self._extract_contacts(response.get("emails", []))

        if not contacts:
            logger.debug(f"Skipping {raw_lead.domain}: no contacts found")
            return None

        # Build harvested lead
        return HarvestedLead(
            domain=raw_lead.domain,
            company_name=company_name,
            contacts=contacts,
            organization=response.get("organization"),
            country=response.get("country") or raw_lead.country,
            state=response.get("state"),
            city=response.get("city"),
            linkedin=response.get("linkedin"),
            twitter=response.get("twitter"),
            facebook=response.get("facebook"),
            phone=response.get("phone_number"),
            headcount=self._parse_headcount(response.get("headcount")),
            industry=response.get("industry") or raw_lead.industry,
            source_url=raw_lead.source_url,
            discovered_at=raw_lead.discovered_at,
            enriched_at=datetime.now(UTC),
        )

    def _extract_contacts(
        self,
        emails: list[dict],
    ) -> list[HarvestedContact]:
        """Extract and prioritize contacts from Hunter.io emails.

        Args:
            emails: List of email objects from Hunter.io

        Returns:
            List of HarvestedContact objects, sorted by priority
        """
        contacts: list[HarvestedContact] = []

        for email_data in emails:
            # Skip invalid or low-confidence emails
            confidence = email_data.get("confidence", 0) / 100.0
            if confidence < 0.5:
                continue

            contact = HarvestedContact(
                email=email_data.get("value", ""),
                first_name=email_data.get("first_name"),
                last_name=email_data.get("last_name"),
                position=email_data.get("position"),
                department=email_data.get("department"),
                linkedin=email_data.get("linkedin"),
                phone=email_data.get("phone_number"),
                confidence=confidence,
            )

            # Skip contacts without valid email
            if not contact.email or "@" not in contact.email:
                continue

            contacts.append(contact)

        # Sort by priority (decision-makers first, then by confidence)
        contacts.sort(
            key=lambda c: (
                self._get_position_priority(c.position),
                c.confidence,
            ),
            reverse=True,
        )

        return contacts

    def _get_position_priority(self, position: Optional[str]) -> int:
        """Get priority score for a job position.

        Higher scores indicate more desirable decision-makers.

        Args:
            position: Job title/position string

        Returns:
            Priority score (0-10)
        """
        if not position:
            return 0

        position_lower = position.lower()

        # Check preferred positions from config
        for idx, preferred in enumerate(self._config.preferred_positions):
            if preferred.lower() in position_lower:
                # Higher priority for earlier positions in list
                return 10 - idx

        return 0

    def _parse_headcount(self, headcount: Optional[str]) -> Optional[str]:
        """Parse and normalize headcount value.

        Args:
            headcount: Raw headcount string from Hunter.io

        Returns:
            Normalized headcount range or None
        """
        if not headcount:
            return None

        # Hunter.io returns ranges like "1-10", "11-50", etc.
        # Keep as-is for consistency with Lead model
        return str(headcount)
