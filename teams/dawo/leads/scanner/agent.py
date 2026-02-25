"""B2B Lead Scanner Agent.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Main scanner agent that discovers potential B2B retail partners
by searching configured domains and filtering by relevance criteria.
"""

import logging
from datetime import datetime, UTC
from typing import Optional

from teams.dawo.leads.scanner.config import LeadScannerConfig
from teams.dawo.leads.scanner.schemas import RawLead, ScanResult
from teams.dawo.leads.scanner.tools import HunterClient, HunterAPIError


logger = logging.getLogger(__name__)


# Scanner constants
MIN_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_SCAN_LIMIT = 10


class B2BLeadScanner:
    """B2B Lead Research Scanner Agent.

    Discovers potential B2B retail partners by:
    1. Searching configured seed domains
    2. Filtering by industry relevance
    3. Applying confidence thresholds
    4. Outputting raw leads for harvesting

    Uses tier="scan" (maps to Haiku at runtime) for high-volume discovery.

    Accepts all dependencies via injection - NEVER loads config directly.
    """

    def __init__(
        self,
        config: LeadScannerConfig,
        hunter_client: HunterClient,
    ) -> None:
        """Initialize the scanner.

        Args:
            config: Scanner configuration
            hunter_client: Hunter.io API client
        """
        self._config = config
        self._hunter = hunter_client

    async def scan(self) -> ScanResult:
        """Execute a scan cycle to discover leads.

        Searches configured seed domains and filters results
        based on industry relevance and confidence thresholds.

        Returns:
            ScanResult with discovered leads and statistics

        Note:
            This method continues on partial failures (graceful degradation).
            Individual domain failures are logged but don't stop the scan.
        """
        logger.info("Starting B2B lead scan cycle")

        leads: list[RawLead] = []
        errors: list[str] = []
        domains_searched = 0

        seed_domains = self._config.get_search_domains()

        for domain in seed_domains:
            if len(leads) >= self._config.max_leads_per_scan:
                logger.info(
                    f"Reached max leads per scan ({self._config.max_leads_per_scan})"
                )
                break

            try:
                domain_leads = await self._scan_domain(domain)
                leads.extend(domain_leads)
                domains_searched += 1
                logger.debug(f"Found {len(domain_leads)} leads at {domain}")

            except HunterAPIError as e:
                error_msg = f"Failed to scan {domain}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
                # Continue to next domain (graceful degradation)
                continue

            except Exception as e:
                error_msg = f"Unexpected error scanning {domain}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue

        # Apply final filtering
        filtered_leads = self._filter_leads(leads)

        logger.info(
            f"Scan complete: {domains_searched} domains searched, "
            f"{len(filtered_leads)} leads found ({len(errors)} errors)"
        )

        return ScanResult(
            leads=filtered_leads,
            domains_searched=domains_searched,
            errors=errors,
        )

    async def _scan_domain(self, domain: str) -> list[RawLead]:
        """Scan a single domain for leads.

        Args:
            domain: Domain to search (e.g., "example.com")

        Returns:
            List of raw leads from this domain

        Raises:
            HunterAPIError: On API failure
        """
        response = await self._hunter.domain_search(
            domain=domain,
            limit=DEFAULT_SCAN_LIMIT,
        )

        leads: list[RawLead] = []

        # Check if domain has relevant company info
        company_name = response.get("organization") or response.get("company")
        country = response.get("country", "")

        # Check country relevance
        if country and not self._is_relevant_country(country):
            logger.debug(f"Skipping {domain}: country {country} not in target list")
            return leads

        # Create a raw lead for this company
        emails = response.get("emails", [])
        if emails:
            # Use the confidence of the best email
            best_email = max(emails, key=lambda e: e.get("confidence", 0))
            confidence = best_email.get("confidence", 0) / 100.0  # Convert to 0-1

            lead = RawLead(
                domain=domain,
                company_name=company_name,
                country=country,
                industry=response.get("industry"),
                source_url=f"https://{domain}",
                confidence=confidence,
                discovered_at=datetime.now(UTC),
            )
            leads.append(lead)

        return leads

    def _filter_leads(self, leads: list[RawLead]) -> list[RawLead]:
        """Apply filtering rules to leads.

        Args:
            leads: Raw leads to filter

        Returns:
            Filtered list of leads meeting criteria
        """
        filtered: list[RawLead] = []

        for lead in leads:
            # Check confidence threshold
            if lead.confidence < self._config.min_confidence:
                logger.debug(
                    f"Filtering out {lead.domain}: "
                    f"confidence {lead.confidence} < {self._config.min_confidence}"
                )
                continue

            # Check country relevance (if specified)
            if lead.country and not self._is_relevant_country(lead.country):
                logger.debug(
                    f"Filtering out {lead.domain}: "
                    f"country {lead.country} not in target list"
                )
                continue

            filtered.append(lead)

        # Sort by confidence (highest first)
        filtered.sort(key=lambda l: l.confidence, reverse=True)

        # Limit to max per scan
        return filtered[: self._config.max_leads_per_scan]

    def _is_relevant_country(self, country: str) -> bool:
        """Check if country is in target list.

        Args:
            country: Country name to check

        Returns:
            True if country is relevant, False otherwise
        """
        if not self._config.countries:
            # No country filter configured
            return True

        country_lower = country.lower()
        return any(
            target.lower() in country_lower or country_lower in target.lower()
            for target in self._config.countries
        )

    def _is_relevant_industry(self, industry: Optional[str]) -> bool:
        """Check if industry matches target industries.

        Args:
            industry: Industry string to check

        Returns:
            True if industry is relevant or not specified
        """
        if not industry or not self._config.industries:
            # No industry info or no filter - assume relevant
            return True

        industry_lower = industry.lower()
        return any(
            target.lower() in industry_lower
            for target in self._config.industries
        )
